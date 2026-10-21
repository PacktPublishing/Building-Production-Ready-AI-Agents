"""Stock trading domain tools for the LLM ReAct agent."""
import random

from tools import Tool


def get_current_price(stock_symbol: str = "MSFT") -> float:
    """Get the current price for a stock symbol."""
    base = 425.0
    fluctuation = random.uniform(-20, 20)
    return base + fluctuation


def check_balance() -> float:
    """Get current cash balance - placeholder."""
    return 5000.0


def buy_stock(shares: int) -> str:
    """Buy N shares of MSFT."""
    price = get_current_price()
    cost = shares * price
    return f"Bought {shares} shares at ${price:.2f}. Total cost: ${cost:.2f}"


def sell_stock(shares: int) -> str:
    """Sell N shares of MSFT."""
    price = get_current_price()
    revenue = shares * price
    return f"Sold {shares} shares at ${price:.2f}. Total revenue: ${revenue:.2f}"


def check_holdings(stock_symbol: str = "MSFT") -> str:
    """Check current stock holdings - placeholder."""
    return f"You currently hold 25 shares of {stock_symbol}"


STOCK_TOOLS = [
    Tool(
        name="get_current_price",
        description="Get the current price of a stock",
        fn=get_current_price,
        params={
            "type": "object",
            "properties": {
                "stock_symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol, for example MSFT",
                }
            },
            "required": [],
        },
    ),
    Tool(
        name="check_balance",
        description="Check your current cash balance",
        fn=check_balance,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="buy_stock",
        description="Buy shares of MSFT stock",
        fn=buy_stock,
        params={
            "type": "object",
            "properties": {
                "shares": {"type": "integer", "description": "Number of shares to buy"}
            },
            "required": ["shares"],
        },
    ),
    Tool(
        name="sell_stock",
        description="Sell shares of MSFT stock",
        fn=sell_stock,
        params={
            "type": "object",
            "properties": {
                "shares": {"type": "integer", "description": "Number of shares to sell"}
            },
            "required": ["shares"],
        },
    ),
    Tool(
        name="check_holdings",
        description="Check how many shares of a stock you currently hold",
        fn=check_holdings,
        params={
            "type": "object",
            "properties": {
                "stock_symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol, for example MSFT",
                }
            },
            "required": [],
        },
    ),
]


STOCK_OBSERVATIONS = [
    (
        "You are a stock trading agent. Your goal is to make good trading decisions. "
        "Check the current price of MSFT and your balance. If the price is below 400, "
        "you should buy. If the price is above 450, you should sell."
    ),
    "The market has changed. Check the current situation and decide if you should take any actions.",
]
