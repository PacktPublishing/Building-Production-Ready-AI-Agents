import ollama
import random
import json
import inspect
import os
import sys
from dataclasses import dataclass, field


USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None


class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    AGENT = "\033[96m"   # cyan
    TOOL = "\033[93m"    # yellow
    PLAN = "\033[95m"    # magenta
    FINAL = "\033[92m"   # green


def _style(text, color):
    if not USE_COLOR:
        return text
    return f"{color}{text}{C.RESET}"


def log_agent(text):
    print(_style(f"🤖 [AGENT] {text}", C.AGENT))


def log_tool(text):
    print(_style(f"🛠️ [TOOL] {text}", C.TOOL))


def log_plan(text):
    print(_style(f"🧠 [LLM PLAN] {text}", C.PLAN))


def log_final(text):
    print(_style(f"✅ [LLM FINAL] {text}", C.FINAL))


def log_final_header(text):
    print(_style(f"✅ [LLM FINAL STREAM] {text}", C.FINAL))


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: dict
    fn: callable
    aliases: list[str] = field(default_factory=list)

    def to_ollama_tool(self):
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class LLM:
    def __init__(self, model="llama3.1:latest", tools=None):
        self.model = model
        self.tools = tools or []
        self.ollama_tools = self._build_ollama_tools()

    def _build_ollama_tools(self):
        return [tool.to_ollama_tool() for tool in self.tools]

    def generate(self, messages):
        response = ollama.chat(
            model=self.model,
            messages=messages,
            tools=self.ollama_tools,
        )
        return response["message"]

    def generate_stream(self, messages, use_tools=False):
        stream = ollama.chat(
            model=self.model,
            messages=messages,
            tools=self.ollama_tools if use_tools else None,
            stream=True,
        )
        for chunk in stream:
            content = chunk.get("message", {}).get("content", "")
            if content:
                yield content


class ReActAgent:
    def __init__(self, tools, model="llama3.1:latest"):
        self.tools = tools
        self.model = model
        self.llm = LLM(model, tools=tools)
        self.tool_map = self._build_tool_map()

    def _build_tool_map(self):
        tool_map = {}
        for tool in self.tools:
            tool_map[tool.name] = tool
            for alias in tool.aliases:
                tool_map[alias] = tool
        return tool_map

    def parse_tool_calls(self, message):
        structured_calls = message.get("tool_calls", [])

        # Some models return a mix of real structured tool calls and extra
        # pseudo tool-call JSON inside the text body. Keep both so we do not
        # drop actionable calls like a follow-up buy/sell request.
        content = message.get("content", "")
        parsed_calls = []
        for obj in self._extract_json_objects(content):
            if not isinstance(obj, dict):
                continue

            name = obj.get("name") or obj.get("tool")
            params = obj.get("parameters") or obj.get("params") or {}
            if name:
                parsed_calls.append(
                    {
                        "function": {
                            "name": name,
                            "arguments": params,
                        }
                    }
                )

        if structured_calls and parsed_calls:
            merged_calls = []
            seen = set()

            for tool_call in [*structured_calls, *parsed_calls]:
                fn_block = tool_call.get("function", {})
                tool_name = fn_block.get("name")
                tool_params = fn_block.get("arguments", {})
                if isinstance(tool_params, str):
                    try:
                        tool_params = json.loads(tool_params)
                    except json.JSONDecodeError:
                        tool_params = {}

                dedupe_key = (
                    tool_name,
                    json.dumps(tool_params, sort_keys=True, default=str),
                )
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)
                merged_calls.append(tool_call)

            return merged_calls, "structured+fallback-text-json"

        if structured_calls:
            return structured_calls, "structured"

        if parsed_calls:
            return parsed_calls, "fallback-text-json"
        return [], "none"

    def _extract_json_objects(self, text):
        """Extract potential JSON objects from free-form model text.

        This supports multiline JSON blocks and ignores non-JSON text.
        """
        objects = []
        start = None
        depth = 0

        for idx, ch in enumerate(text):
            if ch == "{":
                if depth == 0:
                    start = idx
                depth += 1
            elif ch == "}" and depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    candidate = text[start:idx + 1].strip()
                    start = None
                    try:
                        objects.append(json.loads(candidate))
                    except json.JSONDecodeError:
                        continue

        return objects

    def get_tool_by_name(self, tool_name):
        tool = self.tool_map.get(tool_name)
        if tool:
            return tool
        raise ValueError(f"Tool '{tool_name}' not found")

    def _build_policy_summary(self, symbol="AAPL", cycle_log=None, starting_cash=None, starting_shares=None):
        price = PORTFOLIO_STATE["last_price"].get(symbol)
        balance = round(PORTFOLIO_STATE["cash_balance"], 2)
        holdings = PORTFOLIO_STATE["holdings"].get(symbol, 0)
        cycle_log = cycle_log or []

        summary_lines = []
        summary_lines.append("Cycle recap:")
        if cycle_log:
            for idx, entry in enumerate(cycle_log, 1):
                summary_lines.append(
                    f"{idx}. {entry['tool']}({entry['params']}) -> {entry['result']}"
                )
        else:
            summary_lines.append("No tool calls were executed in this cycle.")

        if starting_cash is not None and starting_shares is not None:
            cash_delta = round(balance - starting_cash, 2)
            share_delta = holdings - starting_shares
            summary_lines.append("")
            summary_lines.append("Net position change:")
            summary_lines.append(
                f"Cash: ${starting_cash} -> ${balance} (delta: ${cash_delta})"
            )
            summary_lines.append(
                f"{symbol} shares: {starting_shares} -> {holdings} (delta: {share_delta})"
            )

            if share_delta > 0:
                summary_lines.append("Cycle outcome: BUY")
            elif share_delta < 0:
                summary_lines.append("Cycle outcome: SELL")
            else:
                summary_lines.append("Cycle outcome: HOLD")

        summary_lines.append("")
        summary_lines.append("Policy check:")

        if price is None:
            summary_lines.append(
                "No recent price available yet. Call get_stock_price first to make a policy decision."
            )
            return "\n".join(summary_lines)

        if price < 400:
            affordable_shares = int(balance // price)
            if affordable_shares > 0:
                summary_lines.append(
                    f"Policy decision: BUY. {symbol} price is ${price} (below $400). "
                    f"Cash balance is ${balance}, so up to {affordable_shares} share(s) are affordable."
                )
                return "\n".join(summary_lines)
            summary_lines.append(
                f"Policy decision: BUY, but insufficient cash. {symbol} price is ${price} (below $400), "
                f"cash balance is ${balance}."
            )
            return "\n".join(summary_lines)

        if price > 450:
            if holdings > 0:
                summary_lines.append(
                    f"Policy decision: SELL. {symbol} price is ${price} (above $450), "
                    f"current holdings: {holdings} share(s)."
                )
                return "\n".join(summary_lines)
            summary_lines.append(
                f"Policy decision: SELL signal, but no holdings. {symbol} price is ${price} (above $450)."
            )
            return "\n".join(summary_lines)

        summary_lines.append(
            f"Policy decision: HOLD. {symbol} price is ${price}, which is between $400 and $450. "
            f"Cash balance: ${balance}, holdings: {holdings} share(s)."
        )
        return "\n".join(summary_lines)

    def _stream_plain_text(self, text):
        if USE_COLOR:
            print(C.FINAL, end="")
        for token in text:
            print(token, end="", flush=True)
        if USE_COLOR:
            print(C.RESET, end="")
        print()

    def run_agent_loop(self, observations):
        for observation in observations:
            print()
            log_agent("Starting new observation cycle")
            cycle_log = []
            starting_cash = round(PORTFOLIO_STATE["cash_balance"], 2)
            starting_shares = PORTFOLIO_STATE["holdings"].get("AAPL", 0)
            summary_printed = False
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a financial ReAct agent. Use tool calls when data is needed. "
                        "Always check stock price and balance before deciding to buy or sell. "
                        "Do not ask for permission to proceed. Execute required tool calls immediately. "
                        "If a tool is needed, call it instead of describing it."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Please analyze the situation and decide what actions to take. "
                        "Use the available tools.\n"
                        f"{observation}"
                    ),
                },
            ]

            max_steps = 5
            for step in range(max_steps):
                print()
                log_agent(f"Step {step + 1}/{max_steps}: asking LLM what to do next")
                message = self.llm.generate(messages)
                reasoning = message.get("content", "")

                tool_calls, parse_source = self.parse_tool_calls(message)
                if not tool_calls:
                    log_agent(
                        "LLM requested no tool calls. Using deterministic policy-checked final summary."
                    )
                    print()
                    log_final_header("Deterministic summary")
                    self._stream_plain_text(
                        self._build_policy_summary(
                            "AAPL",
                            cycle_log=cycle_log,
                            starting_cash=starting_cash,
                            starting_shares=starting_shares,
                        )
                    )
                    summary_printed = True
                    break

                if reasoning:
                    log_plan(reasoning)
                log_agent(
                    f"LLM requested {len(tool_calls)} tool call(s) "
                    f"(source: {parse_source}). Executing now."
                )

                # Record the assistant turn once, then attach tool results.
                messages.append(
                    {
                        "role": "assistant",
                        "content": reasoning,
                        "tool_calls": tool_calls,
                    }
                )

                for tool_call in tool_calls:
                    fn_block = tool_call.get("function", {})
                    tool_name = fn_block.get("name")
                    tool_params = fn_block.get("arguments", {})
                    if isinstance(tool_params, str):
                        try:
                            tool_params = json.loads(tool_params)
                        except json.JSONDecodeError:
                            tool_params = {}

                    try:
                        tool_def = self.get_tool_by_name(tool_name)
                    except ValueError as ex:
                        error_msg = str(ex)
                        log_agent(f"Skipping unknown tool call: {error_msg}")
                        messages.append(
                            {
                                "role": "tool",
                                "name": tool_name or "unknown_tool",
                                "content": f"Tool error: {error_msg}",
                            }
                        )
                        continue
                    # Ignore unexpected args hallucinated by the model.
                    signature = inspect.signature(tool_def.fn)
                    allowed_params = set(signature.parameters.keys())
                    safe_params = {
                        k: v for k, v in tool_params.items() if k in allowed_params
                    }
                    dropped = [k for k in tool_params.keys() if k not in allowed_params]
                    log_agent(
                        f"Calling tool '{tool_name}' "
                        f"with raw params={tool_params} filtered_params={safe_params}"
                    )
                    if dropped:
                        log_agent(f"Ignored unsupported params for {tool_name}: {dropped}")
                    tool_result = tool_def.fn(**safe_params)
                    log_tool(f"{tool_name}({safe_params}) -> {tool_result}")
                    cycle_log.append(
                        {
                            "tool": tool_name,
                            "params": safe_params,
                            "result": str(tool_result),
                        }
                    )

                    messages.append(
                        {
                            "role": "tool",
                            "name": tool_name,
                            "content": str(tool_result),
                        }
                    )

                # If we used the final step on tool execution, force one final
                # model turn so the agent can conclude using the latest tool results.
                if step == max_steps - 1:
                    log_agent("Reached step limit after tool execution. Requesting final response.")
                    final_message = self.llm.generate(messages)
                    final_reasoning = final_message.get("content", "")
                    if final_reasoning:
                        log_final(final_reasoning)

            if not summary_printed:
                print()
                log_final_header("Deterministic summary")
                self._stream_plain_text(
                    self._build_policy_summary(
                        "AAPL",
                        cycle_log=cycle_log,
                        starting_cash=starting_cash,
                        starting_shares=starting_shares,
                    )
                )


def get_stock_price(symbol="AAPL"):
    base_price = 420.0
    price = round(base_price + random.uniform(-30, 30), 2)
    PORTFOLIO_STATE["last_price"][symbol] = price
    return price


def check_balance():
    return round(PORTFOLIO_STATE["cash_balance"], 2)


def buy_stock(symbol="AAPL", shares=1):
    try:
        shares = int(shares)
    except (TypeError, ValueError):
        return f"Invalid share count: {shares}"

    if shares <= 0:
        return f"Invalid share count: {shares}"

    price = PORTFOLIO_STATE["last_price"].get(symbol)
    if price is None:
        price = get_stock_price(symbol)

    cost = round(price * shares, 2)
    if cost > PORTFOLIO_STATE["cash_balance"]:
        return (
            f"Insufficient balance. Need ${cost}, "
            f"have ${round(PORTFOLIO_STATE['cash_balance'], 2)}"
        )

    PORTFOLIO_STATE["cash_balance"] -= cost
    PORTFOLIO_STATE["holdings"][symbol] = PORTFOLIO_STATE["holdings"].get(symbol, 0) + shares

    return (
        f"Bought {shares} shares of {symbol} at ${price}. "
        f"Cost: ${cost}. New balance: ${round(PORTFOLIO_STATE['cash_balance'], 2)}"
    )


def sell_stock(symbol="AAPL", shares=1):
    try:
        shares = int(shares)
    except (TypeError, ValueError):
        return f"Invalid share count: {shares}"

    if shares <= 0:
        return f"Invalid share count: {shares}"

    owned = PORTFOLIO_STATE["holdings"].get(symbol, 0)
    if shares > owned:
        return f"Not enough shares to sell. Requested {shares}, owned {owned}"

    price = PORTFOLIO_STATE["last_price"].get(symbol)
    if price is None:
        price = get_stock_price(symbol)

    revenue = round(price * shares, 2)
    PORTFOLIO_STATE["holdings"][symbol] = owned - shares
    PORTFOLIO_STATE["cash_balance"] += revenue

    return (
        f"Sold {shares} shares of {symbol} at ${price}. "
        f"Revenue: ${revenue}. New balance: ${round(PORTFOLIO_STATE['cash_balance'], 2)}"
    )


PORTFOLIO_STATE = {
    "cash_balance": 5000.0,
    "holdings": {"AAPL": 0},
    "last_price": {},
}


tools = [
    ToolDefinition(
        name="get_stock_price",
        description="Get the current stock price for a symbol",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"}
            },
        },
        fn=get_stock_price,
        aliases=["price", "get_price"],
    ),
    ToolDefinition(
        name="check_balance",
        description="Check the available cash balance",
        parameters={"type": "object", "properties": {}},
        fn=check_balance,
        aliases=["get_balance", "balance"],
    ),
    ToolDefinition(
        name="buy_stock",
        description="Buy stock shares",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "shares": {"type": "integer", "description": "Number of shares to buy"},
            },
        },
        fn=buy_stock,
    ),
    ToolDefinition(
        name="sell_stock",
        description="Sell stock shares",
        parameters={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Stock ticker symbol"},
                "shares": {"type": "integer", "description": "Number of shares to sell"},
            },
        },
        fn=sell_stock,
    ),
]

if __name__ == "__main__":
    GOAL = "You are a financial agent. Your goal is to manage a stock portfolio. Check the current price of AAPL and your balance. If the price is below 400, you should buy. If the price is above 450, you should sell."

    agent = ReActAgent(tools=tools, model="llama3.1:latest")
    agent.run_agent_loop(observations=[GOAL])