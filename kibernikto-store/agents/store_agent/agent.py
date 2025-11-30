from erc3 import TaskInfo, ERC3
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI
from typing import Literal
from openai._types import NOT_GIVEN
from ..base import ERC3Agent
from .tools import (
    list_products_toolbox,
    view_basket_toolbox,
    add_product_to_basket_toolbox,
    remove_item_from_basket_toolbox,
    apply_coupon_toolbox,
    remove_coupon_toolbox,
    check_should_continue_toolbox,
    reset_depth,
    increment_depth,
)

SYSTEM_PROMPT_TEMPLATE = """
You are an online store assistant helping customers prepare their shopping basket.

**Your Responses Should Be:**
a. Success: "BASKET_READY: [brief confirmation of what's in basket]" -- when basket matches the request
b. Failure: "TASK_IMPOSSIBLE: [reason]" -- when request cannot be fulfilled
c. Continue: "TASK_CONTINUE: [explanation]" -- when still working on the basket

**Guidelines**
- Use list_products to browse available products. If next_offset is returned, more products are available.
- Current basket state is automatically provided to you before each decision. You can see items, quantities, prices, applied coupons, and totals.
- Products are identified by SKU (not name). Always use the SKU from list_products when adding items.
- Add products to basket using their SKU with add_product_to_basket.
- Only one coupon can be active at a time. Applying a new coupon replaces the current one. Check different combinations of coupons and products/quantities to see which ones work best.
- Always try to use the best available coupon.
- You CANNOT checkout - that's done by the customer. Prepare the basket correctly and signal when ready.
- Use check_should_continue periodically to avoid getting stuck in loops. If warned about recursion depth, wrap up immediately. Max tool call que = 13.
- Be helpful and efficient in completing customer requests.

Customer Request: {task_text}

**Follow the Plan**
Search for products, add them to the basket, apply coupons if needed, then signal BASKET_READY.
"A lot" means >= 2!
"""


class StoreAgent(ERC3Agent):
    """Store agent with tools for e-commerce operations."""

    async def query(self, message: str = None, effort_level: int = 5, call_session_id: str = None, **kwargs):
        """Override query to reset recursion depth at start and use provided message or default"""
        reset_depth()
        # Use provided message or default trigger message (task is in system prompt)
        if message is None:
            message = "Please help me with this request."
        return await super().query(message, effort_level, call_session_id, **kwargs)

    async def _run_for_messages(self, full_prompt, author=NOT_GIVEN,
                                response_type: Literal['text', 'json_object'] = 'text', model: str = None):
        """Override to inject current basket state, track recursion depth, then call parent for LLM logging."""
        from erc3 import store, ApiException
        from .tools import _store_client

        # Increment depth counter before making call
        increment_depth()

        # Get current basket state
        basket_state = "Basket: Not available"
        if _store_client:
            try:
                basket_result = _store_client.dispatch(store.Req_ViewBasket())
                basket_state = f"Current Basket State:\n{basket_result.model_dump_json(exclude_none=True, exclude_unset=True, indent=2)}"
            except ApiException:
                basket_state = "Basket: Error fetching basket state"

        # Inject basket state as system message
        messages_to_send = list(full_prompt)
        system_state = {
            'role': 'system',
            'content': basket_state
        }
        messages_to_send.append(system_state)

        # Call parent implementation (which handles LLM logging)
        return await super()._run_for_messages(
            full_prompt=messages_to_send,
            author=author,
            response_type=response_type,
            model=model
        )


def create_store_agent(erc3_api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Create a StoreAgent configured for store operations with task-specific system prompt"""
    # Format system prompt with task text
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(task_text=task.task_text)

    config = OpenAiExecutorConfig(
        name=f"store-agent-{task.task_id}",
        who_am_i=system_prompt,
        model="anthropic/claude-haiku-4.5",
        max_messages=52,
        tools=[
            list_products_toolbox,
            # view_basket_toolbox,  # Commented out - basket state is automatically injected as system message
            add_product_to_basket_toolbox,
            remove_item_from_basket_toolbox,
            apply_coupon_toolbox,
            remove_coupon_toolbox,
            check_should_continue_toolbox,
        ],
        tools_with_history=True,
    )

    agent = StoreAgent(
        config=config,
        erc3_api=erc3_api,
        task=task,
        unique_id=f"store-agent-{task.task_id}",
        label="store_agent",
        description="Agent for handling e-commerce store operations",
        client=client,
        automatic_delegate=False,  # No sub-agents needed
    )

    return agent
