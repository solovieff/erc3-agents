from erc3 import store, ApiException
from kibernikto.interactors.tools import Toolbox


async def list_products(offset: int = 0, limit: int = 50, max_pages: int = 5) -> str:
    """Browse available products in the store, automatically fetching multiple pages"""
    from . import _store_client
    import re
    import json
    
    print(f"[TOOL] list_products(offset={offset}, limit={limit}, max_pages={max_pages})")
    
    all_products = []
    current_offset = offset
    actual_limit = limit
    pages_fetched = 0
    
    for page_num in range(max_pages):
        try:
            result = _store_client.dispatch(store.Req_ListProducts(offset=current_offset, limit=actual_limit))
            
            # Add products from this page
            all_products.extend(result.products)
            pages_fetched += 1
            
            print(f"[TOOL] ✓ Page {page_num + 1}: Got {len(result.products)} products (total: {len(all_products)})")
            
            # Check if there are more pages
            if result.next_offset is None:
                print(f"[TOOL] ✓ No more pages, fetched {pages_fetched} page(s)")
                break
            
            # Continue to next page
            current_offset = result.next_offset
            
        except ApiException as e:
            error_msg = f"Error: {e.api_error.error} - {e.detail}"
            
            # Check if error is about page limit exceeded (only on first attempt)
            if page_num == 0 and "page limit exceeded" in error_msg.lower():
                # Try to extract the actual limit from error message like "50 > 3"
                match = re.search(r'(\d+)\s*>\s*(\d+)', error_msg)
                if match:
                    actual_limit = int(match.group(2))
                    print(f"[TOOL] ⚠ Limit {limit} exceeded, adjusting to limit={actual_limit}")
                    # Retry this page with correct limit
                    continue
            
            # Check if error is about invalid pagination (offset beyond available products)
            if "invalid pagination" in error_msg.lower():
                print(f"[TOOL] ⚠ Page {page_num + 1}: Reached end of products")
                # This means we've exhausted all products, stop pagination
                break
            
            # Other errors
            print(f"[TOOL] ✗ list_products error on page {page_num + 1}: {error_msg}")
            if pages_fetched == 0:
                # No pages fetched yet, return error
                return error_msg
            else:
                # Return what we have so far
                break
    
    # Format response similar to API response
    response = {
        "products": [{
            "sku": p.sku,
            "name": p.name,
            "available": p.available,
            "price": p.price
        } for p in all_products],
        "total_fetched": len(all_products),
        "pages_fetched": pages_fetched
    }
    
    output = json.dumps(response)
    print(f"[TOOL] ✓ list_products complete: {len(all_products)} products from {pages_fetched} page(s)")
    return output


def list_products_tool():
    return {
        "type": "function",
        "function": {
            "name": "list_products",
            "description": "Browse available products in the store. Automatically fetches up to 5 pages to get more products in one call. Returns all products with SKUs, names, prices, and availability.",
            "parameters": {
                "type": "object",
                "properties": {
                    "offset": {
                        "type": "integer",
                        "description": "Pagination offset. Use 0 for first page, then use next_offset from previous response.",
                        "default": 0
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of products to return per page. Will auto-adjust if exceeds API limit.",
                        "default": 50
                    },
                    "max_pages": {
                        "type": "integer",
                        "description": "Maximum number of pages to fetch automatically (default: 5).",
                        "default": 5
                    }
                },
                "required": []
            }
        }
    }


list_products_toolbox = Toolbox(
    function_name="list_products",
    definition=list_products_tool(),
    implementation=list_products
)
