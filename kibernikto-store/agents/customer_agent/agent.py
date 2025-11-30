import traceback

from erc3 import TaskInfo, ERC3, store, ApiException
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI
from typing import Literal
from openai._types import NOT_GIVEN
from ..base import ERC3Agent
from .tools import checkout_basket_toolbox

SYSTEM_PROMPT_TEMPLATE = """You are a customer of OnlineStore interacting with a store assistant.
As a good customer u never want to pay more than u planned!

Your goal is: {task_text}

Your role:
- You've asked the store assistant to prepare your shopping basket
- Evaluate whether the store assistant has correctly fulfilled your request
- Current basket state is automatically provided to you before each decision
- If the basket looks correct, call checkout_basket to complete the purchase and respond with "TASK_COMPLETE: [confirmation]"
- If something is wrong, provide the detailed feedback to the store assistant so they can fix it
- If the request cannot be fulfilled, respond with "TASK_IMPOSSIBLE: [reason]"


Guidelines:
- You can give feedback to the store assistant
- You can checkout when satisfied using the checkout_basket tool
- Only approve checkout when basket exactly matches what was requested
- Only approve checkout if discounts work as expected
- Only one coupon can be active at a time. Applying a new coupon replaces the current one. 
Check different combinations of coupons and products/quantities to see which ones work best.
Check if the store assistant did not miss any opportunities to reduce prices or quantities.
- Checkout = finish

You stand your ground: you don't buy less than you wanted (if exact numbers are known), you don't pay more!
"""


class CustomerAgent(ERC3Agent):
    """Customer agent that supervises store agent and can checkout."""

    async def _run_for_messages(self, full_prompt, author=NOT_GIVEN,
                                response_type: Literal['text', 'json_object'] = 'text', model: str = None):
        """Override to inject current basket state before each decision."""
        from .tools import _store_client

        # Get current basket state
        basket_state = "Basket: Not available"
        if _store_client:
            try:
                basket_result = _store_client.dispatch(store.Req_ViewBasket())
                basket_state = f"Current Basket State:\n{basket_result.model_dump_json(exclude_none=True, exclude_unset=True, indent=2)}"
            except ApiException:
                traceback.print_exc()
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


def create_customer_agent(erc3_api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Create a CustomerAgent configured as supervisor with checkout capability"""
    # Format system prompt with task text
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(task_text=task.task_text)

    config = OpenAiExecutorConfig(
        name=f"customer-agent-{task.task_id}",
        model="anthropic/claude-haiku-4.5",
        max_messages=52,
        who_am_i=system_prompt,
        tools=[
            checkout_basket_toolbox,
        ],
        tools_with_history=True,
    )

    agent = CustomerAgent(
        config=config,
        erc3_api=erc3_api,
        task=task,
        unique_id=f"customer-agent-{task.task_id}",
        label="customer_agent",
        description="Customer agent that supervises store assistant and can checkout",
        client=client,
        automatic_delegate=False,
    )

    return agent
