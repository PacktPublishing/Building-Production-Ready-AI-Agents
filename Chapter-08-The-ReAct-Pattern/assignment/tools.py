"""Tool definitions and implementations"""
import json
from typing import Callable, Dict, Any


# ============================================================================
# TOOL REGISTRY
# ============================================================================

class Tool:
    """Represents a tool that an LLM can call"""
    def __init__(self, name: str, description: str, fn: Callable, params: Dict[str, Any]):
        self.name = name
        self.description = description
        self.fn = fn
        self.params = params  # Parameter schema
    
    def to_dict(self):
        """Convert to dict for LLM context"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params
        }
    
    def call(self, **kwargs) -> str:
        """Call the tool with arguments"""
        return self.fn(**kwargs)


class ToolRegistry:
    """Registry for managing tools"""
    def __init__(self, tools: list = None):
        self.tools = {tool.name: tool for tool in (tools or [])}
    
    def get_tool(self, name: str) -> Tool:
        """Get a tool by name"""
        return self.tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """Check if tool exists"""
        return name in self.tools
    
    def call_tool(self, name: str, **kwargs) -> str:
        """Call a tool and return result"""
        if not self.has_tool(name):
            return f"Error: Tool '{name}' not found"
        tool = self.get_tool(name)
        try:
            return tool.call(**kwargs)
        except Exception as e:
            return f"Error calling {name}: {str(e)}"
    
    def get_tools_description(self) -> str:
        """Get formatted list of tools for LLM prompt"""
        desc = "Available Tools:\n"
        for name, tool in self.tools.items():
            desc += f"\n- {tool.name}: {tool.description}\n"
            if tool.params.get("properties"):
                desc += f"  Parameters: {json.dumps(tool.params['properties'], indent=2)}\n"
        return desc
