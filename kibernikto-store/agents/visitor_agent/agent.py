from erc3 import TaskInfo, ERC3
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI
from ..base import ERC3Agent


VISITOR_PROMPT_TEMPLATE = """You are a customer visiting OnlineStore with a specific request.

Your Request: {task_text}

Your role:
- You started with a request to the store assistant
- The assistant will respond with what they did
- You must evaluate if your request was fulfilled correctly
- If satisfied, respond with EXACTLY: "TASK_COMPLETE: [brief confirmation]"
- If the request CANNOT be fulfilled (e.g., product unavailable, insufficient stock), respond with EXACTLY: "TASK_IMPOSSIBLE: [reason]"
- If not satisfied but task is still possible, provide clear feedback on what's wrong or missing
- Be specific about any issues (wrong items, wrong quantities, missing steps, etc.)
- You can see the store assistant's actions and their explanations

Guidelines:
- Start by clearly stating your request
- After each response, check if it matches what you asked for
- Only say TASK_COMPLETE when you're truly satisfied
- Only say TASK_IMPOSSIBLE when the request truly cannot be fulfilled (not just on first try)
- Be reasonable - if the assistant did what you asked, approve it
- Don't approve if they did something different from your request
"""


class VisitorAgent(ERC3Agent):
    """Visitor agent that supervises store agent work and evaluates completion."""
    pass  # All LLM logging is handled by ERC3Agent base class


def create_visitor_agent(erc3_api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Create a VisitorAgent that acts as customer/supervisor"""
    system_prompt = VISITOR_PROMPT_TEMPLATE.format(task_text=task.task_text)
    
    config = OpenAiExecutorConfig(
        name="visitor-agent",
        who_am_i=system_prompt,
        tools=[],  # No tools - just evaluates responses
        tools_with_history=True,
    )
    
    agent = VisitorAgent(
        config=config,
        erc3_api=erc3_api,
        task=task,
        unique_id=f"visitor-agent-{task.task_id}",
        label="visitor_agent",
        description="Customer agent that evaluates store assistant work",
        client=client,
        automatic_delegate=False,
    )
    
    return agent
