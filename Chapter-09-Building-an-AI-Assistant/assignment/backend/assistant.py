from __future__ import annotations

from backend.memory.short_term import ShortTermMemoryStore
from backend.schemas import ActionType, AssistantResponse, SessionStateResponse
from backend.tools.support_tools import execute_confirmed_action, run_tool, select_tool
from backend.utils.llm_client import LLMClient, LLMClientError


class Assistant:
    def __init__(self, llm: LLMClient, memory: ShortTermMemoryStore) -> None:
        self._llm = llm
        self._memory = memory

    @property
    def model_name(self) -> str:
        return self._llm.model_name

    async def check_health(self) -> bool:
        return await self._llm.check_connection()

    def handle_message(self, session_id: str, message: str) -> AssistantResponse:
        session = self._memory.get_or_create(session_id)
        session.add_user_message(message)

        tool_name = select_tool(message)
        tool_result = run_tool(tool_name, message)
        memory_summary = session.summary_text()
        used_memory = len(session.messages) > 1

        if tool_result.requires_confirmation:
            session.pending_action = tool_result.action_type
            session.pending_action_label = tool_result.action_label
            reply = (
                f"I found a next step using {tool_name.value}. {tool_result.output} "
                f"Please confirm before I continue with: {tool_result.action_label}."
            )
        else:
            reply = self._compose_reply(message=message, tool_output=tool_result.output, memory_summary=memory_summary)

        session.add_assistant_message(reply)
        return AssistantResponse(
            reply=reply,
            selected_tool=tool_name,
            tool_output=tool_result.output,
            used_memory=used_memory,
            needs_confirmation=tool_result.requires_confirmation,
            pending_action=tool_result.action_type,
            pending_action_label=tool_result.action_label,
            session_summary=session.summary_text(),
        )

    def confirm_action(self, session_id: str, approve: bool) -> AssistantResponse:
        session = self._memory.get_or_create(session_id)
        action = session.pending_action
        action_label = session.pending_action_label

        if action == ActionType.NONE:
            reply = "There is no pending action to confirm right now."
            session.add_assistant_message(reply)
            return AssistantResponse(
                reply=reply,
                selected_tool="general_guidance",
                tool_output="No pending action.",
                used_memory=True,
                session_summary=session.summary_text(),
            )

        if approve:
            action_result = execute_confirmed_action(action)
            reply = f"Confirmed. {action_result}"
        else:
            reply = f"Understood. I canceled the pending action: {action_label}."
            action_result = "Action canceled by user."

        session.pending_action = ActionType.NONE
        session.pending_action_label = None
        session.add_assistant_message(reply)

        return AssistantResponse(
            reply=reply,
            selected_tool="general_guidance",
            tool_output=action_result,
            used_memory=True,
            session_summary=session.summary_text(),
        )

    def session_state(self, session_id: str) -> SessionStateResponse:
        session = self._memory.get_or_create(session_id)
        return SessionStateResponse(
            session_id=session_id,
            messages=session.messages,
            pending_action=session.pending_action,
            pending_action_label=session.pending_action_label,
        )

    def _compose_reply(self, *, message: str, tool_output: str, memory_summary: str) -> str:
        system_prompt = (
            "You are a concise IT support assistant. Use the tool output as evidence. "
            "If memory summary is present, use it to connect the reply to prior context. "
            "Keep the answer to 3 short paragraphs max."
        )
        user_prompt = (
            f"User message: {message}\n"
            f"Tool output: {tool_output}\n"
            f"Memory summary: {memory_summary}"
        )
        try:
            return self._llm.answer(system_prompt, user_prompt)
        except LLMClientError:
            return f"Here is the current assessment: {tool_output}"
