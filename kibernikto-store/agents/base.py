"""Base agent class for ERC3 agents with automatic LLM logging."""
import os
import time
from typing import Literal
from erc3 import TaskInfo, ERC3
from kibernikto.agent.kibernikto_agent import KiberniktoAgent
from kibernikto.bots.ai_settings import AI_SETTINGS
from openai._types import NOT_GIVEN


class ERC3Agent(KiberniktoAgent):
    """Base agent that automatically logs LLM usage to ERC3 API."""

    def __init__(self, erc3_api: ERC3, task: TaskInfo, **kwargs):
        super().__init__(**kwargs)
        self.erc3_api = erc3_api
        self.task = task

    @property
    def default_headers(self):
        http_address = os.getenv("HTTP_ADDRESS", "https://erc.timetoact-group.at")
        return {
            "X-Title": f"{AI_SETTINGS.OPENAI_INSTANCE_ID}:{self.label}",
            "HTTP-Referer": http_address
        }

    @property
    def extra_body(self):
        # fallback model
        return {
            #"models": ["openai/gpt-4.1"],
            "reasoning": {
                "enabled": True,
                "effort": "medium"
            }
        }

    async def _run_for_messages(self, full_prompt, author=NOT_GIVEN,
                                response_type: Literal['text', 'json_object'] = 'text', model: str = None):
        """Override to log LLM usage to ERC3 API."""
        started = time.time()

        # Call parent implementation
        choice, usage_dict = await super()._run_for_messages(
            full_prompt=full_prompt,
            author=author,
            response_type=response_type,
            model=model
        )

        # Log to ERC3 API
        duration = time.time() - started
        if usage_dict:
            from openai.types import CompletionUsage
            usage = CompletionUsage(
                prompt_tokens=usage_dict.get('prompt_tokens', 0),
                completion_tokens=usage_dict.get('completion_tokens', 0),
                total_tokens=usage_dict.get('total_tokens', 0)
            )

            self.erc3_api.log_llm(
                task_id=self.task.task_id,
                model=model or self.model,
                duration_sec=duration,
                usage=usage,
            )

        return choice, usage_dict
