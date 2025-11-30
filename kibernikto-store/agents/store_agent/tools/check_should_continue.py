from kibernikto.interactors.tools import Toolbox

# Global recursion depth tracking
_recursion_depth = 0
_max_depth = 15


def set_max_recursion_depth(depth: int):
    """Set maximum recursion depth before warning"""
    global _max_depth
    _max_depth = depth


def increment_depth():
    """Increment recursion depth counter"""
    global _recursion_depth
    _recursion_depth += 1


def reset_depth():
    """Reset recursion depth counter"""
    global _recursion_depth
    _recursion_depth = 0


def get_depth():
    """Get current recursion depth"""
    return _recursion_depth


async def check_should_continue() -> str:
    """Check if the agent should continue making tool calls or wrap up"""
    global _recursion_depth, _max_depth
    
    print(f"[TOOL] check_should_continue() - depth: {_recursion_depth}/{_max_depth}")
    
    if _recursion_depth >= _max_depth:
        msg = f"WARNING: You have made {_recursion_depth} tool calls. You are approaching recursion limit. Please wrap up your current task and provide a final response or use checkout_basket if the task is complete."
        print(f"[TOOL] ⚠ check_should_continue: {msg}")
        return msg
    else:
        remaining = _max_depth - _recursion_depth
        msg = f"OK: You have {remaining} tool calls remaining before you should wrap up."
        print(f"[TOOL] ✓ check_should_continue: {msg}")
        return msg


def check_should_continue_tool():
    return {
        "type": "function",
        "function": {
            "name": "check_should_continue",
            "description": "Check if you should continue making tool calls or wrap up. Use this periodically to avoid getting stuck in loops.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


check_should_continue_toolbox = Toolbox(
    function_name="check_should_continue",
    definition=check_should_continue_tool(),
    implementation=check_should_continue
)
