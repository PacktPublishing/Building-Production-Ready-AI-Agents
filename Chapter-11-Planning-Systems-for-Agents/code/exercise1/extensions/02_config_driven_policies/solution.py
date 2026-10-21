"""Where to put this:
- Keep helper function in `extensions/.../solution.py` or move to `main.py`
- Call `apply_policies_from_json(...)` from `main.py` after `Executor` is created
- Policy data stays in `extensions/02_config_driven_policies/policy.json`
"""

import json
from pathlib import Path
import sys

# Keep this bootstrap only if you run this file directly.
sys.path.append(str(Path(__file__).resolve().parents[2]))

from executor import Executor
from models import StepPolicy


# Place this function in `main.py` (or `extensions_setup.py`) and call it
# right after creating `executor` in run_demo().
def apply_policies_from_json(executor: Executor, policy_path: str) -> None:
    payload = json.loads(Path(policy_path).read_text(encoding="utf-8"))

    for tool_name, config in payload.items():
        existing_handler = executor.tool_handlers.get(tool_name)
        if existing_handler is None:
            continue
        executor.register_tool_handler(
            tool_name=tool_name,
            handler=existing_handler,
            policy=StepPolicy(
                max_retries=int(config.get("max_retries", 0)),
                requires_approval=bool(config.get("requires_approval", False)),
                approval_prompt=str(config.get("approval_prompt", "")),
            ),
        )
