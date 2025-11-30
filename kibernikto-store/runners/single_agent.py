"""Single agent runner - Store Agent only."""
from erc3 import TaskInfo, ERC3
from openai import AsyncOpenAI
from agents.store_agent import create_store_agent, set_store_context


async def run_single_agent(model: str, api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Run only the Store Agent (no Visitor supervision)."""
    # Set up store context
    store_client = api.get_store_client(task)
    set_store_context(store_client, api, task)
    
    # Create agent with task-specific system prompt and shared client
    agent = create_store_agent(erc3_api=api, task=task, client=client)
    
    # Run agent with task (task text is already in system prompt)
    print(f"Running single agent for task: {task.task_text}")
    
    result = await agent.query(
        effort_level=5,
        call_session_id=task.task_id
    )
    
    print(f"Agent result: {result}")
    
    return result
