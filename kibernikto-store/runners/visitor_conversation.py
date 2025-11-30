"""Visitor conversation runner - wrapper for conversation orchestrator."""
from erc3 import TaskInfo, ERC3
from openai import AsyncOpenAI
from conversation import run_visitor_conversation as _run_visitor


async def run_visitor_conversation(model: str, api: ERC3, task: TaskInfo, client: AsyncOpenAI = None, max_turns: int = 10):
    """Run a visitor-store conversation where Visitor supervises Store Agent."""
    return await _run_visitor(
        model=model,
        api=api,
        task=task,
        client=client,
        max_turns=max_turns
    )
