from __future__ import annotations
import json
import copy
from typing import List, Optional, Dict, Any
from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox
from . import _store_client   # same shared client the other tools use


# ------------------------------------------------------------------
# Helper: tiny dataclass-like dict to keep totals tidy
# ------------------------------------------------------------------
class _Totals:
    def __init__(self, sub: float, disc: float, grand: float):
        self.subtotal = sub
        self.discount = disc
        self.grand_total = grand

    def to_dict(self) -> Dict[str, float]:
        return {
            "subtotal": self.subtotal,
            "discount": self.discount,
            "grand_total": self.grand_total,
        }


# ------------------------------------------------------------------
# Core logic
# ------------------------------------------------------------------
async def evaluate_coupons(
        skus: List[str],
        coupons: List[str],
        quantities: Optional[List[int]] = None,
) -> str:
    """
    Evaluate how *each* coupon affects *every* requested product/quantity mix.
    The live basket is restored to its original state before returning.
    Returns a JSON string:
    {
      "basket_before": { ...original snapshot... },
      "results": {
        "<coupon>": {
          "<sku>x<qty>": { "subtotal":..., "discount":..., "grand_total":... }
        }
      },
      "basket_after": { ...should match basket_before... }
    }
    """
    print(f"[TOOL] evaluate_coupons(skus={skus}, coupons={coupons}, qty={quantities})")

    if not skus or not coupons:
        return json.dumps({"error": "skus and coupons lists must be non-empty"})

    if quantities is None:
        quantities = [1] * len(skus)
    if len(quantities) != len(skus):
        return json.dumps({"error": "quantities list length must match skus"})

    # 1. Snapshot original basket ---------------------------------
    try:
        original_basket = _store_client.dispatch(store.Req_ViewBasket())
    except ApiException as e:
        return json.dumps({"error": f"Unable to read basket: {e.detail}"})

    # 2. Prepare clean working basket -----------------------------
    #    We reset by removing everything that is currently inside.
    for line in original_basket.items:
        try:
            _store_client.dispatch(
                store.Req_RemoveItemFromBasket(sku=line.sku, quantity=line.quantity)
            )
        except ApiException:
            pass   # ignore race conditions / already gone

    report: Dict[str, Any] = {"results": {}}

    # 3. Iterate every product combination ------------------------
    for sku, qty in zip(skus, quantities):
        combo_key = f"{sku}x{qty}"

        # 3a. Add products for this combination
        try:
            _store_client.dispatch(store.Req_AddProductToBasket(sku=sku, quantity=qty))
        except ApiException as e:
            # If a SKU is invalid we skip the whole combo
            for c in coupons:
                report["results"].setdefault(c, {})[combo_key] = {
                    "error": f"Unable to add {sku}: {e.detail}"
                }
            continue

        # 3b. Test every coupon
        for coupon in coupons:
            # Start fresh for this coupon (remove any previous)
            try:
                _store_client.dispatch(store.Req_RemoveCoupon())
            except ApiException:
                pass

            totals: _Totals
            try:
                _store_client.dispatch(store.Req_ApplyCoupon(coupon=coupon))
                basket = _store_client.dispatch(store.Req_ViewBasket())

                sub = basket.subtotal
                disc = sub - basket.total  # total is after discount
                totals = _Totals(sub, disc, basket.total)

            except ApiException as e:
                totals = _Totals(0.0, 0.0, 0.0)
                # Still record the error inside the dict
                report["results"].setdefault(coupon, {})[combo_key] = {
                    "error": f"Coupon {coupon}: {e.detail}"
                }
                continue

            report["results"].setdefault(coupon, {})[combo_key] = totals.to_dict()

        # 3c. Clean combo: remove items & coupon
        try:
            _store_client.dispatch(store.Req_RemoveItemFromBasket(sku=sku, quantity=qty))
            _store_client.dispatch(store.Req_RemoveCoupon())
        except ApiException:
            pass

    # 4. Restore original basket exactly --------------------------
    #    Re-add original items
    for line in original_basket.items:
        try:
            _store_client.dispatch(
                store.Req_AddProductToBasket(sku=line.sku, quantity=line.quantity)
            )
        except ApiException:
            pass   # best effort
    #    Re-apply original coupon (if any)
    if original_basket.applied_coupon:
        try:
            _store_client.dispatch(
                store.Req_ApplyCoupon(coupon=original_basket.applied_coupon)
            )
        except ApiException:
            pass

    # 5. Final snapshot & return ----------------------------------
    final_basket = _store_client.dispatch(store.Req_ViewBasket())
    report["basket_before"] = json.loads(
        original_basket.model_dump_json(exclude_none=True, exclude_unset=True)
    )
    report["basket_after"] = json.loads(
        final_basket.model_dump_json(exclude_none=True, exclude_unset=True)
    )

    print(f"[TOOL] ✓ evaluate_coupons complete")
    return json.dumps(report, ensure_ascii=False, indent=2)


# ------------------------------------------------------------------
# Toolbox wiring (unchanged from previous sketch)
# ------------------------------------------------------------------
def evaluate_coupons_tool():
    return {
        "type": "function",
        "function": {
            "name": "evaluate_coupons",
            "description": (
                "For a given list of products and coupons, compute how each "
                "coupon impacts every product combination (basket subtotal, "
                "discount, grand total).  The basket is restored to its "
                "original state after evaluation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "skus": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Product SKUs to include in the evaluation",
                    },
                    "coupons": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Coupon codes to test",
                    },
                    "quantities": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "description": (
                            "Optional parallel list of quantities for each SKU. "
                            "Defaults to 1 for every SKU if omitted."
                        ),
                    },
                },
                "required": ["skus", "coupons"],
            },
        }
    }


evaluate_coupons_toolbox = Toolbox(
    function_name="evaluate_coupons",
    definition=evaluate_coupons_tool(),
    implementation=evaluate_coupons,
)