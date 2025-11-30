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


# Import toolbox
from .checkout_basket import checkout_basket_toolbox

# Export
__all__ = [
    'checkout_basket_toolbox',
    'set_store_context',
]
