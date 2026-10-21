"""Blackjack domain tools for the LLM ReAct agent."""
import random

from tools import Tool


BLACKJACK_STATE = {
    "hand": [],
    "is_round_active": False,
}


def _draw_card_value() -> int:
    """Draw a simplified blackjack card value (1-11, face cards as 10)."""
    card_pool = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11]
    return random.choice(card_pool)


def _hand_total(hand: list[int]) -> int:
    """Compute best blackjack total with Ace adjustment."""
    total = sum(hand)
    aces_as_eleven = hand.count(11)

    while total > 21 and aces_as_eleven > 0:
        total -= 10
        aces_as_eleven -= 1

    return total


def start_round() -> str:
    """Start a new blackjack round with two cards."""
    BLACKJACK_STATE["hand"] = [_draw_card_value(), _draw_card_value()]
    BLACKJACK_STATE["is_round_active"] = True
    total = _hand_total(BLACKJACK_STATE["hand"])
    return f"Round started. Hand: {BLACKJACK_STATE['hand']}, total: {total}"


def get_hand_status() -> str:
    """Return current hand and total."""
    hand = BLACKJACK_STATE["hand"]
    if not hand:
        return "No active hand. Use start_round first."

    total = _hand_total(hand)
    return f"Current hand: {hand}, total: {total}"


def draw_card() -> str:
    """Draw one card and return updated hand status."""
    if not BLACKJACK_STATE["is_round_active"]:
        return "No active round. Use start_round first."

    card = _draw_card_value()
    BLACKJACK_STATE["hand"].append(card)
    total = _hand_total(BLACKJACK_STATE["hand"])

    if total > 21:
        BLACKJACK_STATE["is_round_active"] = False
        return f"Drew {card}. Hand: {BLACKJACK_STATE['hand']}, total: {total} (bust)"

    return f"Drew {card}. Hand: {BLACKJACK_STATE['hand']}, total: {total}"


def hold_hand(hand_index: int | None = None, **kwargs) -> str:
    """Stop drawing and hold current hand.

    Accepts optional/extra args to tolerate LLM-generated parameters.
    """
    if not BLACKJACK_STATE["hand"]:
        return "No active hand. Use start_round first."

    total = _hand_total(BLACKJACK_STATE["hand"])
    BLACKJACK_STATE["is_round_active"] = False
    return f"Holding hand: {BLACKJACK_STATE['hand']}, final total: {total}"


BLACKJACK_TOOLS = [
    Tool(
        name="start_round",
        description="Start a new blackjack round and get two initial cards",
        fn=start_round,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_hand_status",
        description="Get current blackjack hand and total",
        fn=get_hand_status,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="draw_card",
        description="Draw one blackjack card",
        fn=draw_card,
        params={"type": "object", "properties": {}},
    ),
    Tool(
        name="hold_hand",
        description="Stop drawing cards and hold current hand",
        fn=hold_hand,
        params={
            "type": "object",
            "properties": {
                "hand_index": {
                    "type": "integer",
                    "description": "Optional hand index (ignored in single-hand mode)",
                }
            },
        },
    ),
]


BLACKJACK_OBSERVATIONS = [
    (
        "You are a blackjack agent. Follow this strict policy: draw for totals below 17, "
        "hold on 17 or above. You must use tools only. Start by calling start_round, then call "
        "get_hand_status. If total is below 17, call draw_card and then get_hand_status again. "
        "Repeat until total is 17 or more, then call hold_hand."
    ),
    (
        "Play another round with the same policy: start_round, then repeatedly draw_card while total < 17, "
        "checking get_hand_status after each draw, and finally hold_hand when total >= 17."
    ),
]
