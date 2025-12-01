from erc3 import TaskInfo, ERC3, StoreClient
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI
from typing import Literal
from openai._types import NOT_GIVEN
from pydantic import BaseModel

from ..base import ERC3Agent
from .tools import (
    list_products_toolbox,
    set_basket_state_toolbox,
    view_basket_toolbox,
    add_product_to_basket_toolbox,
    remove_item_from_basket_toolbox,
    apply_coupon_toolbox,
    remove_coupon_toolbox,
    check_should_continue_toolbox,
    reset_depth,
    increment_depth, get_depth,
)

SYSTEM_PROMPT_TEMPLATE = """
You are an online store assistant helping customers prepare their shopping basket.

**Your Final Responses To User Must Be:**
a. Success: "BASKET_READY: [brief confirmation of what's in basket]" -- when basket matches the request
b. Failure: "TASK_IMPOSSIBLE: [reason]" -- when request cannot be fulfilled
c. Continue: "TASK_CONTINUE: [explanation]" -- need more time to complete request, provide the current state and plans. 

**Guidelines**
- Use list_products to browse available products. If next_offset is returned, more products are available.
- Current basket state is automatically provided to you before each decision. You can see items, quantities, prices, applied coupons, and totals.
- Products are identified by SKU (not name). Always use the SKU from list_products when adding items.
- Use check_should_continue every 5 steps to avoid getting stuck in loops. If warned about recursion depth, wrap up immediately.
- use set_basket_state to make the basket look as u want.

**Coupons**
- Only one coupon can be active at a time!! 
- Applying a new coupon replaces the current one!! 
- If you have additional coupon info, check different combinations of coupons and products/quantities to see which ones work best.
- Always try to use the best available coupon.
- One coupon gives a discount on all products in the basket 
- There is no any coupons except provided! If no coupons provided nothing should be applied! Never invent coupons!

**Request Verbiage**
- Be careful with interpretation of the request: 'a lot' or 'many' can mean 2 or more, not gigantic amounts!
- 
- Ignore coupon names meanings and be impartial in your decisions. 

Customer Request: {task_text}

**Follow the Plan**
[pseudocode]
search for needed products
if coupons:
    check if there are any rules about when each coupon can be applied
    if there are rules:
        understand the rules!
    check how each coupon works with products
    if dependent coupons:
        check if different product amounts/configurations affect coupons
    apply best most discount coupon with best product configuration
else:
    add products to basket
signal BASKET_READY | TASK_IMPOSSIBLE | TASK_CONTINUE
"""


class StoreAgent(ERC3Agent):
    label: str = 'store_agent'
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
        # Increment depth counter before making call
        increment_depth()

        # Get current basket state
        basket_state = self.retrieve_basket_state()

        # Inject basket state as system message
        messages_to_send = list(full_prompt)
        system_state = {
            'role': 'system',
            'content': basket_state
        }
        messages_to_send.append(system_state)

        iter = get_depth()
        if iter > self.full_config.tool_call_hole_deepness - 4:
            print("ATTENTION: Recursion depth exceeded!")
            messages_to_send.append({
                'role': 'system',
                'content': "Tool call deepness exceeded! You are inside yrself for too long! "
                           "Stop calling tools! "
                           "Return current results of your work to the user immediately and ask for continuation!!!"
            })
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
        tool_call_hole_deepness=20,
        max_messages=200,
        temperature=0.1,
        # model="x-ai/grok-4-fast",
        # model="openai/gpt-5",
        model="google/gemini-2.5-flash-preview-09-2025",
        # model="anthropic/claude-haiku-4.5",
        tools=[
            list_products_toolbox,
            # view_basket_toolbox,  # Commented out - basket state is automatically injected as system message
            set_basket_state_toolbox,
            # add_product_to_basket_toolbox,
            # remove_item_from_basket_toolbox,
            # evaluate_coupons_toolbox,
            # apply_coupon_toolbox,
            # remove_coupon_toolbox,
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
