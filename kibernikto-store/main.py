import asyncio
import logging
import textwrap
import datetime

from kibernikto.bots.ai_settings import AI_SETTINGS
from kibernikto.utils.environment import configure_logger
from openai import AsyncOpenAI
from runners import run_visitor_conversation, run_auditor_conversation, run_customer_conversation
from erc3 import ERC3


async def main():
    # Create shared OpenAI client for all agents
    client = AsyncOpenAI()
    core = ERC3()

    # Start session with metadata
    timestamp_suffix = int(datetime.datetime.now().timestamp()) % 1000000
    res = core.start_session(
        benchmark="store",
        workspace="kibernikto",
        name=f"kibernikto agents",
        architecture="Kibernikto agents chat, request preprocess"
    )

    status = core.session_status(res.session_id)
    print(f"Session has {len(status.tasks)} tasks")

    for task in status.tasks:
        print("=" * 40)
        print(f"Starting Task: {task.task_id} ({task.spec_id}): {task.task_text}")

        # start the task
        core.start_task(task)
        if task.spec_id != 'soda_pack_optimizer' and 1==2:
            print(f"Skipping task {task.spec_id}")
            skipped = core.complete_task(task)
            continue

        try:
            # Run visitor-store conversation with shared client
            await run_customer_conversation(AI_SETTINGS.OPENAI_API_MODEL, core, task, client=client)
        except Exception as e:
            print(f"Error running agent: {e}")
            import traceback
            traceback.print_exc()
        result = core.complete_task(task)
        if result.eval:
            explain = textwrap.indent(result.eval.logs, "  ")
            print(f"\nSCORE: {result.eval.score}\n{explain}\n")

    core.submit_session(res.session_id)


if __name__ == "__main__":
    configure_logger()

    logger = logging.getLogger('kibernikto')
    logger.setLevel(logging.DEBUG)

    logger = logging.getLogger('urllib3')
    logger.setLevel(logging.ERROR)

    asyncio.run(main())
