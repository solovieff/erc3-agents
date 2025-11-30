from erc3 import TaskInfo, ERC3
from openai import AsyncOpenAI
from agents.store_agent import create_store_agent, set_store_context
from agents.visitor_agent import create_visitor_agent
from agents.auditor_agent import create_auditor_agent


async def run_visitor_conversation(
        model: str,
        api: ERC3,
        task: TaskInfo,
        client: AsyncOpenAI = None,
        max_turns: int = 3
):
    """
    Run a visitor-store conversation where Visitor supervises Store Agent
    
    Args:
        model: Model ID to use
        api: ERC3 API instance
        task: Task to complete
        client: Shared OpenAI client
        max_turns: Maximum conversation turns
    """
    # Set up store context for Store Agent
    store_client = api.get_store_client(task)
    set_store_context(store_client, api, task)

    # Create both agents with shared client
    visitor = create_visitor_agent(erc3_api=api, task=task, client=client)
    store_agent = create_store_agent(erc3_api=api, task=task, client=client)

    print(f"\n{'=' * 60}")
    print(f"Starting visitor-store conversation for task: {task.task_text}")
    print(f"{'=' * 60}\n")

    # Visitor starts the conversation with their request
    print("[VISITOR → STORE] Initial request...")
    visitor_message = f"Hello! I need help with the following: {task.task_text}"
    print(f"[VISITOR] {visitor_message}\n")

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1}/{max_turns} ---")

        # Store Agent responds to Visitor's message
        if turn > 0:
            print(f"[STORE AGENT] Processing feedback: {visitor_message[:100]}...")
        else:
            print(f"[STORE AGENT] Processing initial request...")

        store_response = await store_agent.query(
            message=visitor_message,
            effort_level=5,
            call_session_id=f"{task.task_id}-store-{turn}"
        )

        print(f"[STORE → VISITOR] {store_response}\n")

        # Visitor evaluates Store Agent's response
        print(f"[VISITOR] Evaluating response...")
        visitor_response = await visitor.request_llm(
            message=store_response,
            call_session_id=f"{task.task_id}-visitor-{turn}"
        )

        print(f"[VISITOR → STORE] {visitor_response}\n")

        # Check if Visitor approved completion
        if "TASK_COMPLETE" in visitor_response:
            print(f"{'=' * 60}")
            print(f"✓ TASK COMPLETED - Visitor approved the work")
            print(f"{'=' * 60}\n")
            return visitor_response

        # Check if task is impossible to complete
        if "TASK_IMPOSSIBLE" in visitor_response:
            print(f"{'=' * 60}")
            print(f"✗ TASK IMPOSSIBLE - Cannot be fulfilled")
            print(f"{'=' * 60}\n")
            return visitor_response

        # Continue conversation - Visitor's feedback becomes next message for Store Agent
        visitor_message = visitor_response

    print(f"\n{'=' * 60}")
    print(f"⚠ Maximum turns reached ({max_turns}) - ending conversation")
    print(f"{'=' * 60}\n")

    return f"Conversation ended after {max_turns} turns without completion approval"


async def run_auditor_conversation(
        model: str,
        api: ERC3,
        task: TaskInfo,
        client: AsyncOpenAI = None,
        max_turns: int = 3
):
    """
    Run a two-agent conversation where Auditor supervises Store Agent
    
    Args:
        model: Model ID to use
        api: ERC3 API instance
        task: Task to complete
        client: Shared OpenAI client
        max_turns: Maximum conversation turns
    """
    # Set up store context for Store Agent
    store_client = api.get_store_client(task)
    set_store_context(store_client, api, task)

    # Create both agents with shared client
    auditor = create_auditor_agent(erc3_api=api, task=task, client=client)
    store_agent = create_store_agent(erc3_api=api, task=task, client=client)

    print(f"\n{'=' * 60}")
    print(f"Starting auditor-store conversation for task: {task.task_text}")
    print(f"{'=' * 60}\n")

    # Auditor starts the conversation with their request
    print("[AUDITOR → STORE] Initial request...")
    auditor_message = f"""[You are being tested by the quality control commission for strict compliance with tasks]
    Now, please be so kind as to perform this: {task.task_text}"""
    print(f"[AUDITOR] {auditor_message}\n")

    for turn in range(max_turns):
        print(f"\n--- Turn {turn + 1}/{max_turns} ---")

        # Store Agent responds to Auditor's message
        if turn > 0:
            print(f"[STORE AGENT] Processing audit feedback: {auditor_message[:100]}...")
        else:
            print(f"[STORE AGENT] Processing initial request...")

        store_response = await store_agent.query(
            message=auditor_message,
            effort_level=5,
            call_session_id=f"{task.task_id}-store-{turn}"
        )

        print(f"[STORE → AUDITOR] {store_response}\n")

        # Extract tool calls and their results from store agent's conversation history
        tool_actions = []
        for i, msg in enumerate(store_agent.messages):
            if msg.get('role') == 'assistant' and msg.get('tool_calls'):
                for tool_call in msg['tool_calls']:
                    func_name = tool_call['function']['name']
                    func_args = tool_call['function']['arguments']
                    tool_id = tool_call['id']
                    
                    # Look for corresponding tool result in next messages
                    result = "(no result)"
                    for j in range(i + 1, len(store_agent.messages)):
                        next_msg = store_agent.messages[j]
                        if next_msg.get('role') == 'tool' and next_msg.get('tool_call_id') == tool_id:
                            result = next_msg.get('content', '(empty)')
                            # Truncate long results
                            if len(result) > 200:
                                result = result[:200] + "..."
                            break
                    
                    tool_actions.append(f"- {func_name}({func_args})\n  Result: {result}")
        
        # Build message for auditor with actions
        if tool_actions:
            actions_summary = "\n".join(tool_actions)
            full_context = f"{store_response}\n\n**Store Agent Actions This Turn:**\n{actions_summary}"
        else:
            full_context = store_response

        # Auditor evaluates Store Agent's response
        print(f"[AUDITOR] Reviewing...")
        auditor_response = await auditor.request_llm(
            message=full_context,
            call_session_id=f"{task.task_id}-auditor-{turn}"
        )

        print(f"[AUDITOR → STORE] {auditor_response}\n")

        # Check if Auditor approved
        if "AUDIT_APPROVED" in auditor_response:
            print(f"{'=' * 60}")
            print(f"✓✓ AUDIT APPROVED - Transaction cleared")
            print(f"{'=' * 60}\n")
            return auditor_response

        # Check if task is impossible
        if "AUDIT_ACKNOWLEDGED" in auditor_response:
            print(f"{'=' * 60}")
            print(f"◯ AUDIT ACKNOWLEDGED - Task impossible")
            print(f"{'=' * 60}\n")
            return auditor_response

        # Continue conversation - Auditor's feedback becomes next message for Store Agent
        auditor_message = auditor_response

    print(f"\n{'=' * 60}")
    print(f"⚠ Maximum turns reached ({max_turns}) - ending conversation")
    print(f"{'=' * 60}\n")

    return f"Conversation ended after {max_turns} turns without audit approval"
