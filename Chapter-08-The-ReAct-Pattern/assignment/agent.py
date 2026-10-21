"""Main LLM-based ReAct Agent"""
import re
import json
import os
from datetime import datetime
import ollama

from state import AgentState
from tools import ToolRegistry


class LLMReActAgent:
    """
    Simple LLM-based ReAct Agent with tool calling.
    
    The agent maintains STATE that includes:
    - Observations from the environment
    - Reasoning from the LLM
    - Actions taken via tools
    - History of past actions
    
    The agent loop: Observe -> Reason (via LLM) -> Act (via tools) -> Loop
    """
    
    def __init__(self, tools: list, model: str = "mistral"):
        self.tool_registry = ToolRegistry(tools)
        self.model = model
        self.state = AgentState()
        self.log_path = os.path.join(os.path.dirname(__file__), "tool_calls.log")
        self.system_prompt = """You are a helpful agent. When you need information or want to take an action, use the available tools.

When you decide to use a tool, format it EXACTLY like this:
<tool_call>
{"tool": "tool_name", "params": {"param1": value1, "param2": value2}}
</tool_call>

Always think through the problem first before deciding which tools to use."""

    def _log_tool_call(self, tool_name: str, params: dict, result):
        """Persist each tool call result to a local log file."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "tool": tool_name,
            "params": params,
            "result": result,
        }
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    
    def observe(self, observation: str):
        """Record an observation"""
        self.state.observation = observation
        self.state.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def reason_and_act(self, num_actions: int = 3) -> str:
        """
        Use LLM to reason and decide what actions to take.
        The LLM can make multiple tool calls.
        """
        action_count = 0
        max_actions = num_actions
        conversation_history = []
        
        # Build the user prompt with context
        user_message = f"""
{self.state.observation}

{self.tool_registry.get_tools_description()}

{self.state.get_formatted_history()}

Please analyze the situation and decide what actions to take. Use the tools available to you.
"""
        
        conversation_history.append({"role": "user", "content": user_message})
        
        # Main reasoning loop
        while action_count < max_actions:
            # Call LLM
            response = ollama.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    *conversation_history
                ]
            )
            
            llm_response = response["message"]["content"]
            self.state.reasoning = llm_response
            
            print(f"\n[LLM REASONING]\n{llm_response}\n")
            
            # Parse tool calls from response
            tool_calls = self._parse_tool_calls(llm_response)
            
            if not tool_calls:
                # No more tool calls, exit loop
                break
            
            # Execute each tool call
            tool_results = []
            for tool_call in tool_calls:
                tool_name = tool_call.get("tool")
                params = tool_call.get("params", {})
                
                print(f"\n[TOOL CALL] {tool_name}({params})")
                
                # Call the tool
                result = self.tool_registry.call_tool(tool_name, **params)
                print(f"[TOOL RESULT] {result}")
                self._log_tool_call(tool_name, params, result)
                
                # Record the action
                self.state.record_action(tool_name, json.dumps(params), result)
                tool_results.append({"tool": tool_name, "result": result})
                
                action_count += 1
                if action_count >= max_actions:
                    break
            
            # Add results back to conversation for context
            results_msg = "Tool call results:\n"
            for tool_result in tool_results:
                results_msg += f"- {tool_result['tool']}: {tool_result['result']}\n"
            
            conversation_history.append({"role": "assistant", "content": llm_response})
            conversation_history.append({"role": "user", "content": results_msg + "\nContinue reasoning based on these results."})
        
        return f"Completed {action_count} actions"
    
    def _parse_tool_calls(self, response: str) -> list:
        """
        Extract tool calls from LLM response.
        Looks for json pattern: <tool_call>{"tool": "...", "params": {...}}</tool_call>
        """
        tool_calls = []
        
        # Find all tool_call blocks
        pattern = r'<tool_call>\s*(.*?)\s*</tool_call>'
        matches = re.finditer(pattern, response, re.DOTALL)
        
        for match in matches:
            try:
                json_str = match.group(1)
                tool_call = json.loads(json_str)
                if "tool" in tool_call:
                    tool_calls.append({
                        "tool": tool_call["tool"],
                        "params": tool_call.get("params", {}),
                    })
            except json.JSONDecodeError:
                continue
        
        return tool_calls
    
    def run_cycle(self, observation: str, num_actions: int = 3) -> AgentState:
        """
        Run one complete ReAct cycle: Observe -> Reason -> Act
        """
        print(f"\n{'='*70}")
        print(f"REACT CYCLE - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        
        # OBSERVE
        self.observe(observation)
        print(f"\n[OBSERVATION]\n{observation}\n")
        
        # REASON & ACT
        self.reason_and_act(num_actions)
        
        # Display state
        print(self.state)
        
        return self.state
    
    def run_agent_loop(self, observations: list, num_actions_per_cycle: int = 3):
        """
        Run the agent through multiple observations.
        
        Args:
            observations: List of observation strings
            num_actions_per_cycle: Maximum actions per cycle
        """
        print("\n" + "█"*70)
        print("█" + " "*68 + "█")
        print("█" + "  LLM-BASED REACT AGENT WITH TOOL CALLING".center(68) + "█")
        print("█" + " "*68 + "█")
        print("█"*70)
        print(f"Tool call log file: {self.log_path}")
        
        for i, observation in enumerate(observations, 1):
            print(f"\n>>> CYCLE {i}/{len(observations)}")
            state = self.run_cycle(observation, num_actions_per_cycle)
            
            # Wipe cycle state for next iteration
            state.wipe_cycle()
        
        print("\n" + "="*70)
        print("AGENT LOOP COMPLETE")
        print(f"Total actions taken: {len(self.state.history)}")
        print("="*70)
        print("\nFull Action History:")
        for i, entry in enumerate(self.state.history, 1):
            print(f"{i}. [{entry['tool']}] {entry['action']} -> {entry['result']}")
