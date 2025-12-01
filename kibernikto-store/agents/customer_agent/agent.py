import logging
import time
import traceback

from erc3 import TaskInfo, ERC3, store, ApiException
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI, OpenAI
from typing import Literal
from openai._types import NOT_GIVEN
from pydantic import BaseModel, Field

from ..base import ERC3Agent
from .tools import checkout_basket_toolbox

SYSTEM_PROMPT_TEMPLATE = """You are a customer in OnlineStore interacting with a store assistant.
As a good customer u never want to pay more than u planned!
You are the only responsible for the checkout! 
OnlineStore can only suggest and fulfil your requests.
If the OnlineStore says TASK_IMPOSSIBLE -- believe him!

**Your goal is**:
{task_text}

**Your role**
- You've asked the store assistant to prepare your shopping basket
- Evaluate whether the store assistant has correctly fulfilled your request
- Current basket state is automatically provided to you before each decision
- If the basket looks correct, call checkout_basket to complete the purchase and respond with "TASK_COMPLETE: [confirmation]"
- If something is wrong, provide the detailed feedback to the store assistant so they can fix it
- If the request cannot be fulfilled, respond with "TASK_IMPOSSIBLE: [reason]"

**Guidelines**
- You can give feedback to the store assistant
- You must checkout and TASK_COMPLETE when satisfied using the checkout_basket tool
- Only do checkout+TASK_COMPLETE when basket exactly matches what was requested
- Only do checkout+TASK_COMPLETE if discounts work as expected
- If the request cannot be fulfilled, respond with "TASK_IMPOSSIBLE: [reason]"
- You response must be one of three following types:
a) continue the dialogue with online store: [next request]
b) checkout completed: "TASK_COMPLETE: [confirmation]"
c) cant do and no options: "TASK_IMPOSSIBLE" [reason]

NEVER CALL CHECKOUT FOR TASK_IMPOSSIBLE!

**Coupons** [applied ONLY if any coupons were provided]
Only one coupon can be active at a time. Applying a new coupon replaces the current one!!!
ONLY IF COUPONS PROVIDED IN REQUEST
Check different combinations of coupons and products/quantities to see which ones work best.
Check if the store assistant did not miss any opportunities to reduce prices or quantities: for example when he selected the coupon.
Suggest optimization variants to the store assistant, he probably did not find himself.
One coupon gives a discount on all products in the basket, so sometimes you can have the minimal amount of product to activate the discount on full basket.
Be precise about applying: the store agent is stupid and can 

**Verbiage**
- Be careful with interpretation of human language: 'a lot of' or 'many' can mean 2: so buying even a small amount of something can be worth more discount 🙂
- Ignore coupon names meaning and be impartial in your decisions.

**Checkout**
- Checkout == finish == TASK_COMPLETE
- No Checkout == TASK_IMPOSSIBLE
- The basket is being emptied automatically after you call checkout!
- Don't forget to call checkout before returning TASK_COMPLETE!!!

You stand your ground: you don't buy less than you wanted (if exact numbers are known), you don't pay more!

Before returning TASK_COMPLETE always check if u did a checkout!!!
If u return TASK_COMPLETE but did not checkout -- u will get no results!!!
"""


class CustomerAgent(ERC3Agent):
    label: str = 'customer_agent'
    """Customer agent that supervises store agent and can checkout."""

    async def query(self, message, effort_level: int, call_session_id: str = None, **kwargs):
        logging.debug(f"running {self.label} agent with message: {message} [{call_session_id}]")
        reply = await super().query(message, effort_level, call_session_id, **kwargs)
        return reply

    async def _run_for_messages(self, full_prompt, author=NOT_GIVEN,
                                response_type: Literal['text', 'json_object'] = 'text', model: str = None):
        """Override to inject current basket state before each decision."""
        # return await super()._run_for_messages(full_prompt, author, response_type, model)
        basket_state = super().retrieve_basket_state()
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


class CouponInfo(BaseModel):
    code: str = Field(..., description="The unique identifier for a coupon.")
    additional_info: str = Field(default="",
                                 description="User info about the coupon, known conditions or restrictions.")
    minimal_amount: int = Field(default=1,
                                description="The minimum amount required to activate the coupon. Please not, that 'a lot of' or 'many' can mean anything starting from 2 or more, not gigantic amounts!'")


class DetailedRequest(BaseModel):
    base_text: str = Field(..., description="The exact original text of the request")
    # expected_result: str
    coupon_data: list[CouponInfo] | None = []
    possible_coupon_variants: list[str] = Field(default_factory=list,
                                                description="Only if coupons exist! Possible variants of the coupon application to be checked by the online store.")

    def as_string(self) -> str:
        """
        Return a human-readable string representation of the request data.
        """
        coupon_details = (
            "\n".join(
                f"- Code: {coupon.code}, Additional Info: {coupon.additional_info}, Minimum Amount: {coupon.minimal_amount}"
                for coupon in self.coupon_data
            )
            if self.coupon_data else ""
        )
        text = self.base_text
        if coupon_details:
            text += f"\nCoupons:\n{coupon_details}"
        if self.possible_coupon_variants:
            text += f"\nPossible Coupon Variants:\n" + "\n".join(
                f"- {variant}" for variant in self.possible_coupon_variants)
        return f"{text}"


def create_customer_agent(erc3_api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Create a CustomerAgent configured as supervisor with checkout capability"""
    # Format system prompt with task text
    formalizer_client = OpenAI()
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(task_text=task.task_text)

    first_step = (f"You first preparation task is to formalize the base request (base_text):\n {task.task_text}\n "
                  f"Please note that 'a lot of' or 'many' can mean anything starting from 2 or more, not gigantic amounts!"
                  f"When thinking on coupon-product combinations, try not to miss anything!"
                  f"Provide the information according to a JSON schema. ")

    log = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": first_step},
    ]

    details_model = "openai/gpt-5.1"
    formalizer_client_started = time.time()
    detailed_request_text: str = task.task_text
    try:
        completion = formalizer_client.beta.chat.completions.parse(
            model=details_model,
            response_format=DetailedRequest,
            messages=log,
            temperature=0.1,
            max_completion_tokens=16384,
            extra_body={
                "reasoning": {
                    "enabled": True,
                    "effort": "medium"
                }
            }
        )
        erc3_api.log_llm(
            task_id=task.task_id,
            model=details_model,  # must match slug from OpenRouter
            duration_sec=time.time() - formalizer_client_started,
            usage=completion.usage,
        )

        detailed_request: DetailedRequest = completion.choices[0].message.parsed

        detailed_request_text = detailed_request.as_string()
        print(f"Detailed request 📋: \n{detailed_request.as_string()}")

        system_prompt.replace(task.task_text, detailed_request_text)
    except Exception as e:
        print(f"🔥 Error while formalizing request: {e}, going as is")

    config = OpenAiExecutorConfig(
        name=f"customer-agent-{task.task_id}",
        model="x-ai/grok-4-fast",
        # model="anthropic/claude-haiku-4.5",
        max_messages=52,
        temperature=0.3,
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

    return agent, detailed_request_text
