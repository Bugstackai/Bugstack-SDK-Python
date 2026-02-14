"""Basic BugStack SDK usage example."""

import bugstack

# Initialize the SDK
bugstack.init(
    api_key="bs_live_your_api_key_here",
    environment="production",
    auto_fix=True,
    debug=True,  # See SDK activity in console
)

# Manual exception capture
try:
    result = 1 / 0
except Exception as e:
    bugstack.capture_exception(e)

# Capture from except block (auto-detects current exception)
try:
    int("not a number")
except ValueError:
    bugstack.capture_exception()

# With metadata
try:
    raise RuntimeError("something went wrong")
except RuntimeError as e:
    bugstack.capture_exception(e, metadata={"user_id": "42", "action": "checkout"})
