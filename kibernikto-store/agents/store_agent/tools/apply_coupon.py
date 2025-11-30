from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def apply_coupon(coupon: str):
    """Apply a coupon code to get a discount. Only one coupon can be active at a time."""
    from . import _store_client
    print(f"[TOOL] apply_coupon(coupon='{coupon}')")
    try:
        result = _store_client.dispatch(
            store.Req_ApplyCoupon(coupon=coupon)
        )
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)

        basket_result = _store_client.dispatch(store.Req_ViewBasket())
        result_dict = {
            'updated_basket': basket_result.model_dump_json(exclude_none=True, exclude_unset=True),
            'output': output,
            'coupon': coupon
        }
        print(f"[TOOL] ✓ apply_coupon: {result_dict}")
        return result_dict
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ apply_coupon: {error_msg}")
        return error_msg


def apply_coupon_tool():
    return {
        "type": "function",
        "function": {
            "name": "apply_coupon",
            "description": "Apply a coupon code for a discount. Only one coupon can be active at a time - applying a new one replaces the current one.",
            "parameters": {
                "type": "object",
                "properties": {
                    "coupon": {
                        "type": "string",
                        "description": "The coupon code to apply"
                    }
                },
                "required": ["coupon"]
            }
        }
    }


apply_coupon_toolbox = Toolbox(
    function_name="apply_coupon",
    definition=apply_coupon_tool(),
    implementation=apply_coupon
)
