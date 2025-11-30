from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def remove_coupon() -> str | dict:
    """Remove the currently applied coupon"""
    from . import _store_client
    print(f"[TOOL] remove_coupon()")
    try:
        result = _store_client.dispatch(store.Req_RemoveCoupon())
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)
        print(f"[TOOL] ✓ remove_coupon: {output}")
        basket_result = _store_client.dispatch(store.Req_ViewBasket())
        result_dict = {
            'updated_basket': basket_result.model_dump_json(exclude_none=True, exclude_unset=True),
            'output': output
        }
        return result_dict
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ remove_coupon: {error_msg}")
        return error_msg


def remove_coupon_tool():
    return {
        "type": "function",
        "function": {
            "name": "remove_coupon",
            "description": "Remove the currently applied coupon from the basket.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


remove_coupon_toolbox = Toolbox(
    function_name="remove_coupon",
    definition=remove_coupon_tool(),
    implementation=remove_coupon
)
