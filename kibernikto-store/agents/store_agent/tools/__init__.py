# Global store client reference - will be set during agent execution
_store_client = None
_erc3_api = None
_current_task = None


def set_store_context(store_client, erc3_api, task):
    """Set the store client context for tool execution"""
    global _store_client, _erc3_api, _current_task
    _store_client = store_client
    _erc3_api = erc3_api
    _current_task = task


# Import all toolboxes
from .list_products import list_products_toolbox
from .view_basket import view_basket_toolbox
from .add_product_to_basket import add_product_to_basket_toolbox
from .remove_item_from_basket import remove_item_from_basket_toolbox
from .apply_coupon import apply_coupon_toolbox
from .remove_coupon import remove_coupon_toolbox
from .checkout_basket import checkout_basket_toolbox
from .set_basket_state import set_basket_state_toolbox
from .check_should_continue import (
    check_should_continue_toolbox,
    reset_depth,
    increment_depth,
    get_depth,
    set_max_recursion_depth,
)

# Export all tools
__all__ = [
    'list_products_toolbox',
    'set_basket_state_toolbox',
    'view_basket_toolbox',
    'add_product_to_basket_toolbox',
    'remove_item_from_basket_toolbox',
    'apply_coupon_toolbox',
    'remove_coupon_toolbox',
    'checkout_basket_toolbox',
    'check_should_continue_toolbox',
    'set_store_context',
    'reset_depth',
    'increment_depth',
    'get_depth',
    'set_max_recursion_depth',
    '_store_client'
]
