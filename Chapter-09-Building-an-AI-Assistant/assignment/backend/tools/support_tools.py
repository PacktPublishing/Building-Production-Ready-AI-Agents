from __future__ import annotations

from backend.schemas import ActionType, ToolName, ToolResult


KEYWORDS_NETWORK = ("wifi", "internet", "network", "zoom", "offline", "latency")
KEYWORDS_ACCOUNT = ("password", "login", "sign in", "access", "locked out")


def select_tool(message: str) -> ToolName:
    text = message.lower()
    if any(keyword in text for keyword in KEYWORDS_NETWORK):
        return ToolName.NETWORK_DIAGNOSTIC
    if any(keyword in text for keyword in KEYWORDS_ACCOUNT):
        return ToolName.ACCOUNT_LOOKUP
    return ToolName.GENERAL_GUIDANCE


def run_tool(tool_name: ToolName, message: str) -> ToolResult:
    text = message.lower()

    if tool_name == ToolName.NETWORK_DIAGNOSTIC:
        if "drop" in text or "unstable" in text:
            return ToolResult(
                tool_name=tool_name,
                output="Detected signs of an unstable local network. Suggested next step is a simulated network service restart.",
                requires_confirmation=True,
                action_type=ActionType.RESTART_NETWORK,
                action_label="Restart network service",
            )
        return ToolResult(
            tool_name=tool_name,
            output="Network symptoms detected. Start with router, VPN, and connectivity checks.",
        )

    if tool_name == ToolName.ACCOUNT_LOOKUP:
        return ToolResult(
            tool_name=tool_name,
            output="Account issue detected. Recommend checking password reset status and access group membership.",
        )

    return ToolResult(
        tool_name=tool_name,
        output="No special tool was needed. Provide general troubleshooting guidance.",
    )


def execute_confirmed_action(action_type: ActionType) -> str:
    if action_type == ActionType.RESTART_NETWORK:
        return "Simulated action complete: network service restart queued successfully."
    return "No action was executed."
