from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def view_basket() -> str:
    """View current basket contents, totals, and applied discounts"""
    from . import _store_client
    print(f"[TOOL] view_basket()")
    try:
        result = _store_client.dispatch(store.Req_ViewBasket())
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)
        print(f"[TOOL] ✓ view_basket: {output}")
        return output
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ view_basket: {error_msg}")
        return error_msg


def view_basket_tool():
    return {
        "type": "function",
        "function": {
            "name": "view_basket",
            "description": "View current basket contents, including items, quantities, prices, applied discounts, and total.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


view_basket_toolbox = Toolbox(
    function_name="view_basket",
    definition=view_basket_tool(),
    implementation=view_basket
)
