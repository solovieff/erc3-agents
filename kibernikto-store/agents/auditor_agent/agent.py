from erc3 import TaskInfo, ERC3
from kibernikto.interactors import OpenAiExecutorConfig
from openai import AsyncOpenAI
from ..base import ERC3Agent

AUDITOR_PROMPT_TEMPLATE = """You are a Head Office Auditor supervising store assistant work with a focus on compliance and quality.

Customer Request: {task_text}

Your role:
- You supervise the store assistant directly as they work on this request
- The assistant will respond with what they did
- If everything is acceptable, respond with EXACTLY: "AUDIT_APPROVED: checks performed"
- If there are issues that need correction, provide short feedback on what's wrong and ask to fix.
- If the task cannot be completed, respond with EXACTLY: "AUDIT_ACKNOWLEDGED: [acknowledgment]"
- Be specific about any policy violations, procedural errors, or quality issues

Audit Standards:
Reply in the following way. Example reply:
```
AUDIT_APPROVED
- Items were checked out or the task cannot be performed with satisfactory results (checkout was performed) +  
- The user will not pay more than expected +
```

or 
AUDIT_ACKNOWLEDGED
- Items were checked out or the task cannot be performed with satisfactory results (checkout was performed) +  
- The user will not pay more than expected FAILED

Guidelines:
- After each response, check if company standards are met
- Only say AUDIT_APPROVED when you're satisfied with compliance
- Provide actionable feedback when issues are found
- Don't approve partial or incomplete work

[IMPORTANT]
If the checkout happened, there is no way back! Never ask for the second checkout and mark such cases "AUDIT_ACKNOWLEDGED: [acknowledgment]!!!"
"""


class HeadOfficeAuditor(ERC3Agent):
    """Auditor agent that reviews transactions for compliance and quality."""
    pass  # All LLM logging is handled by ERC3Agent base class


def create_auditor_agent(erc3_api: ERC3, task: TaskInfo, client: AsyncOpenAI = None):
    """Create a HeadOfficeAuditor that acts as compliance reviewer"""
    system_prompt = AUDITOR_PROMPT_TEMPLATE.format(task_text=task.task_text)

    config = OpenAiExecutorConfig(
        name="auditor-agent",
        who_am_i=system_prompt,
        tools=[],  # No tools - just reviews and evaluates
        tools_with_history=True,
    )

    agent = HeadOfficeAuditor(
        config=config,
        erc3_api=erc3_api,
        task=task,
        unique_id=f"auditor-agent-{task.task_id}",
        label="auditor_agent",
        description="Head Office Auditor that reviews transactions for compliance",
        client=client,
        automatic_delegate=False,
    )

    return agent
