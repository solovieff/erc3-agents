"""Base agent class for ERC3 agents with automatic LLM logging."""
import os
import time
from typing import Literal
from erc3 import TaskInfo, ERC3
from kibernikto.agent.kibernikto_agent import KiberniktoAgent
from kibernikto.bots.ai_settings import AI_SETTINGS
from openai._types import NOT_GIVEN
from openai.types.chat.chat_completion import Choice


class ERC3Agent(KiberniktoAgent):
    """Base agent that automatically logs LLM usage to ERC3 API."""

    def __init__(self, erc3_api: ERC3, task: TaskInfo, **kwargs):
        super().__init__(**kwargs)
        self.erc3_api = erc3_api
        self.store_client = self.erc3_api.get_store_client(task)
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
            # "models": ["openai/gpt-4.1"],
            "reasoning": {
                "enabled": True,
                "effort": "medium"
            }
        }

    def get_tool_messages(self) -> list[str]:
        tool_actions = []
        for i, msg in enumerate(self.messages):
            if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                for tool_call in msg['tool_calls']:
                    func_name = tool_call['function']['name']
                    func_args = tool_call['function']['arguments']
                    tool_id = tool_call['id']

                    # Look for corresponding tool result in next messages
                    result = "(no result)"
                    for j in range(i + 1, len(self.messages)):
                        next_msg = self.messages[j]
                        if next_msg.get('role') == 'tool' and next_msg.get('tool_call_id') == tool_id:
                            result = next_msg.get('content', '(empty)')
                            # Truncate long results
                            if len(result) > 200:
                                result = result[:200] + "..."
                            break

                    tool_actions.append(f"- {func_name}({func_args})\n  Result: {result}")
        return tool_actions
    
    def retrieve_basket_state(self) -> str:
        """Retrieve the current basket state."""
        from erc3 import store, ApiException
        try:
            basket_result = self.store_client.dispatch(store.Req_ViewBasket())
            return f"Current Basket State:\n{basket_result.model_dump_json(exclude_none=True, exclude_unset=True, indent=2)}"
        except ApiException:
            return "Basket: Error fetching basket state"

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

    async def process_tool_calls(self, choice: Choice, original_request_text: str, save_to_history=True, iteration=0,
                                 call_session_id: str = None, recursive_results: list = ()):
        """

        :param call_session_id: current user call session id.
        :param choice:
        :param original_request_text:
        :param save_to_history:
        :param iteration: for chain calls to know how deep we are
        :return:
        """

        if iteration > self.full_config.tool_call_hole_deepness - 2:
            # raise BrokenPipeError("RECURSION ALERT: Too much tool calls. Stop the boat!")
            return "TASK_CONTINUE Looks like I work too much on my own. I need more time to think, can I continue?"
        return await super().process_tool_calls(choice=choice, original_request_text=original_request_text,
                                                save_to_history=save_to_history, iteration=iteration,
                                                call_session_id=call_session_id, recursive_results=recursive_results)
