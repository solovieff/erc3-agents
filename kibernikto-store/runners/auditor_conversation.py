"""Auditor conversation runner - wrapper for conversation orchestrator."""
from erc3 import TaskInfo, ERC3
from openai import AsyncOpenAI
from conversation import run_auditor_conversation as _run_auditor


async def run_auditor_conversation(model: str, api: ERC3, task: TaskInfo, client: AsyncOpenAI = None, max_turns: int = 10):
    """Run a two-agent conversation where Auditor supervises Store Agent (more strict than Visitor)."""
    return await _run_auditor(
        model=model,
        api=api,
        task=task,
        client=client,
        max_turns=max_turns
    )
