"""State management for LLM-based ReAct agent"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class AgentState:
    """Tracks agent state across cycles"""
    observation: str = ""
    reasoning: str = ""
    actions_taken: list = field(default_factory=list)  # List of {action, tool, result}
    history: list = field(default_factory=list)  # Full action history
    timestamp: str = ""
    
    def record_action(self, tool: str, action: str, result: Any):
        """Record an action taken"""
        entry = {
            "tool": tool,
            "action": action,
            "result": str(result),
            "timestamp": datetime.now().isoformat()
        }
        self.actions_taken.append(entry)
        self.history.append(entry)
    
    def get_formatted_history(self) -> str:
        """Get formatted history for LLM context"""
        if not self.history:
            return "No prior actions."
        
        formatted = "Past Actions:\n"
        for i, entry in enumerate(self.history[-5:], 1):  # Last 5 actions
            formatted += f"{i}. [{entry['tool']}] {entry['action']} -> {entry['result']}\n"
        return formatted
    
    def wipe_cycle(self):
        """Clear cycle state, keep history"""
        self.observation = ""
        self.reasoning = ""
        self.actions_taken = []
        self.timestamp = ""
    
    def __str__(self):
        output = "\n" + "="*70 + "\n"
        output += f"AGENT STATE - {self.timestamp}\n"
        output += "="*70 + "\n"
        if self.observation:
            output += f"[OBSERVATION]\n{self.observation}\n\n"
        if self.reasoning:
            output += f"[REASONING]\n{self.reasoning}\n\n"
        if self.actions_taken:
            output += f"[ACTIONS TAKEN]\n"
            for action in self.actions_taken:
                output += f"  • {action['tool']}: {action['action']}\n"
                output += f"    Result: {action['result']}\n"
        output += "="*70 + "\n"
        return output
