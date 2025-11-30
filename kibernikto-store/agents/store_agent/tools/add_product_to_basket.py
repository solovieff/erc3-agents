from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def add_product_to_basket(sku: str, quantity: int) -> str | dict:
    """Add a product to the basket"""
    from . import _store_client
    print(f"[TOOL] add_product_to_basket(sku='{sku}', quantity={quantity})")
    try:
        result = _store_client.dispatch(
            store.Req_AddProductToBasket(sku=sku, quantity=quantity)
        )
        output = result.model_dump_json(exclude_none=True, exclude_unset=True)

        basket_result = _store_client.dispatch(store.Req_ViewBasket())
        result_dict = {
            'updated_basket': basket_result.model_dump_json(exclude_none=True, exclude_unset=True),
            'output': output
        }
        print(f"[TOOL] ✓ add_product_to_basket: {output}")
        return result_dict
    except ApiException as e:
        error_msg = f"Error: {e.api_error.error} - {e.detail}"
        print(f"[TOOL] ✗ add_product_to_basket: {error_msg}")
        return error_msg


def add_product_to_basket_tool():
    return {
        "type": "function",
        "function": {
            "name": "add_product_to_basket",
            "description": "Add a product to the basket with specified quantity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "sku": {
                        "type": "string",
                        "description": "SKU of the product to add (from list_products)"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity to add (must be positive)"
                    }
                },
                "required": ["sku", "quantity"]
            }
        }
    }


add_product_to_basket_toolbox = Toolbox(
    function_name="add_product_to_basket",
    definition=add_product_to_basket_tool(),
    implementation=add_product_to_basket
)
