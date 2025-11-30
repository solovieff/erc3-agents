from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox

confirmation_needed = True


async def checkout_basket() -> str:
    global confirmation_needed
    """Complete the purchase and checkout the basket"""
    from . import _store_client
    print(f"[TOOL] checkout_basket()")
    if confirmation_needed is True:
        confirmation_needed = False
        #raise Exception(
        #    "Please carefully review the basket contents before proceeding and probably recheck! Did you do everything according to the request? Don't u violate one of the request terms? If yes, run this tool again!")
    else:
        # resetting
        confirmation_needed = True
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
            "description": "Complete the purchase and checkout the basket. Only call this when you are certain the task is complete.",
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
