from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def remove_item_from_basket(sku: str, quantity: int) -> str | dict:
    """Remove a product from the basket"""
    from . import _store_client
    print(f"[TOOL] remove_item_from_basket(sku='{sku}', quantity={quantity})")
    try:
        result = _store_client.dispatch(
            store.Req_RemoveItemFromBasket(sku=sku, quantity=quantity)
        )
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)
        basket_result = _store_client.dispatch(store.Req_ViewBasket())
        result_dict = {
            'updated_basket': basket_result.model_dump_json(exclude_none=True, exclude_unset=True),
            'output': output,
            'sku': sku
        }
        print(f"[TOOL] ✓ remove_item_from_basket: {output}")
        return result_dict
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ remove_item_from_basket: {error_msg}")
        return error_msg


def remove_item_from_basket_tool():
    return {
        "type": "function",
        "function": {
            "name": "remove_item_from_basket",
            "description": "Remove a specific quantity of a product from the basket. Must specify exact quantity to remove.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "SKU of the product to remove"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity to remove (required, must be positive)"
                    }
                },
                "required": ["sku", "quantity"]
            }
        }
    }


remove_item_from_basket_toolbox = Toolbox(
    function_name="remove_item_from_basket",
    definition=remove_item_from_basket_tool(),
    implementation=remove_item_from_basket
)
