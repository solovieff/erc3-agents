from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def checkout_basket() -> str:
    """Complete the purchase and checkout the basket"""
    from . import _store_client
    print(f"[TOOL] checkout_basket()")
    try:
        result = _store_client.dispatch(store.Req_CheckoutBasket())
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)
        print(f"[TOOL] ✓ checkout_basket: {output}")
        return output
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ checkout_basket: {error_msg}")
        return error_msg


def checkout_basket_tool():
    return {
        "type": "function",
        "function": {
            "name": "checkout_basket",
            "description": "Complete the purchase and checkout the basket. Only call this when you are certain the task is complete, basket is correct, u get the discounts u wanted",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


checkout_basket_toolbox = Toolbox(
    function_name="checkout_basket",
    definition=checkout_basket_tool(),
    implementation=checkout_basket
)
