from __future__ import annotations
import json
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


# ------------------------------------------------------------------
# Concrete schema for the *input* basket description
# ------------------------------------------------------------------
class BasketItem(BaseModel):
    sku: str
    quantity: int = Field(ge=1)
    price: float = Field(ge=0)  # audit only – not sent to API


class BasketBlueprint(BaseModel):
    items: List[BasketItem]
    coupon: Optional[str] = None


# ------------------------------------------------------------------
# Concrete schema for the *output*
# ------------------------------------------------------------------
class SetBasketResult(BaseModel):
    status: Literal["SUCCESS", "FAILURE"]
    message: str
    basket_before: dict  # JSON-serialised snapshot
    basket_after: dict  # JSON-serialised snapshot


# ------------------------------------------------------------------
# Helper: empty the basket completely
# ------------------------------------------------------------------
def _clear_basket() -> None:
    from . import _store_client
    """Remove every item and any coupon.  Raises ApiException on failure."""
    current = _store_client.dispatch(store.Req_ViewBasket())
    if not current.items:
        return
    for line in current.items:
        _store_client.dispatch(
            store.Req_RemoveItemFromBasket(sku=line.sku, quantity=line.quantity)
        )
    if current.coupon:
        _store_client.dispatch(store.Req_RemoveCoupon())


# ------------------------------------------------------------------
# Tool entry point
# ------------------------------------------------------------------
async def set_basket_state(new_basket: dict) -> str:
    """
    Atomically replace the live basket with the supplied state.
    Returns a JSON-encoded SetBasketResult.
    """
    from . import _store_client
    print(f"[TOOL] set_basket_state({new_basket})")

    # 1. Parse & validate -------------------------------------------------
    try:
        blueprint = BasketBlueprint.model_validate(new_basket)
    except Exception as e:
        return SetBasketResult(
            status="FAILURE",
            message=f"Invalid input schema: {e}",
            basket_before={},
            basket_after={},
        ).model_dump_json()

    # 2. Snapshot original basket ----------------------------------------
    try:
        original_snapshot = _store_client.dispatch(store.Req_ViewBasket())
    except ApiException as e:
        return SetBasketResult(
            status="FAILURE",
            message=f"Unable to read original basket: {e.detail}",
            basket_before={},
            basket_after={},
        ).model_dump_json()

    # 3. Critical section: swap basket -----------------------------------
    try:
        # 3a. blank slate
        _clear_basket()

        # 3b. add requested items
        for it in blueprint.items:
            _store_client.dispatch(
                store.Req_AddProductToBasket(sku=it.sku, quantity=it.quantity)
            )

        # 3c. apply coupon (if any)
        if blueprint.coupon:
            _store_client.dispatch(store.Req_ApplyCoupon(coupon=blueprint.coupon))

    except ApiException as e:
        # rollback not possible – we already cleared.  Caller must retry.
        return SetBasketResult(
            status="FAILURE",
            message=f"Failed while building new basket: {e.detail}",
            basket_before=json.loads(
                original_snapshot.model_dump_json(exclude_none=True, exclude_unset=True)
            ),
            basket_after={},  # unknown – we crashed
        ).model_dump_json()

    # 4. Snapshot new basket ---------------------------------------------
    try:
        new_snapshot = _store_client.dispatch(store.Req_ViewBasket())
    except ApiException as e:
        return SetBasketResult(
            status="FAILURE",
            message=f"New basket built but cannot read it back: {e.detail}",
            basket_before=json.loads(
                original_snapshot.model_dump_json(exclude_none=True, exclude_unset=True)
            ),
            basket_after={},
        ).model_dump_json()

    # 5. Success ----------------------------------------------------------
    return SetBasketResult(
        status="SUCCESS",
        message="Basket state replaced successfully",
        basket_before=json.loads(
            original_snapshot.model_dump_json(exclude_none=True, exclude_unset=True)
        ),
        basket_after=json.loads(
            new_snapshot.model_dump_json(exclude_none=True, exclude_unset=True)
        ),
    ).model_dump_json()


# ------------------------------------------------------------------
# Toolbox wiring
# ------------------------------------------------------------------
def set_basket_state_tool():
    return {
        "type": "function",
        "function": {
            "name": "set_basket_state",
            "description": (
                "Atomically replaces the entire basket with the provided state "
                "(items, quantities, coupon)."
                "Example: set_basket_state(new_basket={'items': [{'sku': 'SKU1', 'quantity': 2, price: 123.45},{'sku': 'SKU2', 'quantity': 1, price: 432.45}], coupon: 'COUPON1'})"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "new_basket": BasketBlueprint.model_json_schema(),
                },
                "required": ["new_basket"],
            },
        }
    }


set_basket_state_toolbox = Toolbox(
    function_name="set_basket_state",
    definition=set_basket_state_tool(),
    implementation=set_basket_state,
)
