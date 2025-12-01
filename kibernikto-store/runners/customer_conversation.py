"""Customer conversation runner."""
from erc3 import TaskInfo, ERC3, StoreClient
from openai import AsyncOpenAI
from pydantic import BaseModel

from agents import ERC3Agent
from agents.store_agent import create_store_agent
from agents.store_agent import set_store_context as set_store_agent_context
from agents.customer_agent import create_customer_agent
from agents.customer_agent import set_store_context as set_customer_context


async def run_customer_conversation(model: str, api: ERC3, task: TaskInfo, client: AsyncOpenAI = None,
                                    max_turns: int = 10):
    """
    Run a customer-store conversation where Customer supervises Store Agent and can checkout
    
    Args:
        model: Model ID to use
        api: ERC3 API instance
        task: Task to complete
        client: Shared OpenAI client
        max_turns: Maximum conversation turns
    """
    # Set up store context for Store and Customer Agents
    store_client: StoreClient = api.get_store_client(task)
    set_store_agent_context(store_client, api, task)
    set_customer_context(store_client, api, task)

    # Create both agents with shared client
    customer, first_request = create_customer_agent(erc3_api=api, task=task, client=client)
    store_agent = create_store_agent(erc3_api=api, task=task, client=client)

    print(f"\n{'=' * 60}")
    print(f"Starting customer-store conversation for task: {task.task_text}")
    print(f"{'=' * 60}\n")

    # Customer starts the conversation with their request
    print("[CUSTOMER → STORE] Initial request...")
    customer_message = f"{task.task_text}"
    customer_message = first_request
    print(f"[CUSTOMER] {customer_message}\n")

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1}/{max_turns} ---")

        # Store Agent responds to Customer's message
        if turn > 0:
            print(f"[STORE AGENT] Processing customer feedback: {customer_message[:100]}...")
        else:
            print(f"[STORE AGENT] Processing initial request {customer_message[:100]}...")

        store_response = await store_agent.query(
            message=customer_message,
            effort_level=5,
            call_session_id=f"{task.task_id}-store-{turn}"
        )

        print(f"[STORE → CUSTOMER] {store_response}\n")

        # Customer evaluates Store Agent's response (can use checkout tool)
        print(f"[CUSTOMER] Evaluating response...")

        # Add store agent's message to customer's conversation
        if turn == 0:
            customer.messages.append({"role": "user", "content": "Hi what can I do for you today?"})
            customer.messages.append({"role": "assistant", "content": customer_message})

        store_tools = store_agent.get_tool_messages()
        # Customer responds (potentially using checkout tool)
        customer_response = await customer.query(
            message=f"[Online store actions logs]\n {store_tools}. \n\nReponse: {store_response}",
            effort_level=5,
            call_session_id=f"{task.task_id}-customer-{turn}"
        )

        print(f"[CUSTOMER → STORE] {customer_response}\n")

        # Check if Customer completed checkout
        if "TASK_COMPLETE" in customer_response:
            print(f"{'=' * 60}")
            print(f"✓✓ TASK COMPLETED - Customer checked out successfully")
            print(f"{'=' * 60}\n")
            last_tool = customer.get_tool_messages()[-1] if customer.get_tool_messages() else None
            checked_out = last_tool is not None and 'checkout_basket' in last_tool
            if not checked_out:
                customer_response = await customer.query(
                    message=f"You forgot to checkout your basket! Do it and mark TASK_COMPLETE!",
                    effort_level=5,
                    call_session_id=f"{task.task_id}-customer-{turn}"
                )
                if "TASK_COMPLETE" in customer_response:
                    return customer_response
            else:
                return customer_response

        # Check if task is impossible to complete
        if "TASK_IMPOSSIBLE" in customer_response:
            print(f"{'=' * 60}")
            print(f"✗ TASK IMPOSSIBLE - Cannot be fulfilled")
            print(f"{'=' * 60}\n")
            return customer_response

        # Continue conversation - Customer's feedback becomes next message for Store Agent
        customer_message = customer_response

    print(f"\n{'=' * 60}")
    print(f"⚠ Maximum turns reached ({max_turns}) - ending conversation")
    print(f"{'=' * 60}\n")

    return f"Conversation ended after {max_turns} turns without completion"
