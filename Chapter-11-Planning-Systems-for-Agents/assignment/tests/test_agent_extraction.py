import pytest
from main import BagelAgent, BagelState, PizzaAgent, PizzaState, Session


class StubLLM:
    def __init__(self, updates=None, success=False, error="stub failure"):
        self._updates = updates or {}
        self._success = success
        self._error = error

    def extract_order_update(self, message, state):
        return self._updates, {
            "mode": "llm",
            "success": self._success,
            "error": self._error,
            "raw_response": "{}",
            "normalized_updates": self._updates,
        }

    def extract_bagel_update(self, message, state):
        return self._updates, {
            "mode": "llm",
            "success": self._success,
            "error": self._error,
            "raw_response": "{}",
            "normalized_updates": self._updates,
        }

    def rewrite_reply(self, raw_reply):
        return raw_reply


def build_agent_with_stub(updates=None, success=False, error="stub failure"):
    agent = PizzaAgent()
    stub = StubLLM(updates=updates, success=success, error=error)
    agent.llm = stub
    agent.planner.llm = stub
    agent.planner.enable_fallback = True
    return agent


def build_bagel_agent_with_stub(updates=None, success=False, error="stub failure"):
    agent = BagelAgent()
    stub = StubLLM(updates=updates, success=success, error=error)
    agent.llm = stub
    agent.planner.llm = stub
    agent.planner.enable_fallback = True
    return agent


@pytest.fixture
def session():
    return Session()


def test_fallback_handles_crust_without_size(session):
    agent = build_agent_with_stub()

    reply = agent.run_turn(session, "thin")

    assert session.state.crust == "thin"
    assert session.state.size is None
    assert "pizza size" in reply.lower()
    assert "could not extract the pizza size" not in reply.lower()


def test_fallback_captures_multiple_fields_without_size(session):
    agent = build_agent_with_stub()

    reply = agent.run_turn(session, "thin crust, paprika, onion, pay with card")

    assert session.state.size is None
    assert session.state.crust == "thin"
    assert session.state.payment_method == "card"
    assert "paprika" in session.state.toppings
    assert "onions" in session.state.toppings
    assert "i captured" in reply.lower()
    assert "what pizza size" in reply.lower()


def test_fallback_handles_size(session):
    agent = build_agent_with_stub()

    reply = agent.run_turn(session, "medium")

    assert session.state.size == "medium"
    assert "what crust" in reply.lower()


def test_clarification_when_no_fields_can_be_extracted(session):
    agent = build_agent_with_stub()

    reply = agent.run_turn(session, "blabla")

    assert "could not extract the pizza size" in reply.lower()
    assert session.trace[-1]["next_step"] == "clarify_extraction"


def test_llm_updates_still_used_when_available(session):
    agent = build_agent_with_stub(updates={"size": "large"}, success=True, error=None)

    reply = agent.run_turn(session, "anything")

    assert session.state.size == "large"
    assert "what crust" in reply.lower()


def test_build_plan_orders_missing_fields_and_payment_last():
    agent = build_agent_with_stub()
    state = PizzaState()

    plan = agent.planner.build_plan(state)

    assert [step.name for step in plan] == [
        "ask_size",
        "ask_crust",
        "ask_toppings",
        "ask_address",
        "ask_payment",
    ]


def test_build_plan_keeps_payment_last_with_partial_state():
    agent = build_agent_with_stub()
    state = PizzaState(size="medium")

    plan = agent.planner.build_plan(state)

    assert [step.name for step in plan] == [
        "ask_crust",
        "ask_toppings",
        "ask_address",
        "ask_payment",
    ]


def test_bagel_fallback_accepts_standalone_address_after_extras():
    agent = build_bagel_agent_with_stub()
    session = Session(flow="bagel")
    session.state = BagelState(
        bread_type="sesame",
        filling="roast beef",
        extras=["onion"],
    )

    reply = agent.run_turn(session, "10 Main St, NY")

    assert session.state.address == "10 Main St, Ny"
    assert "how would you like to pay" in reply.lower()


def test_bagel_uses_circuit_breaker_fallback_when_llm_unavailable():
    agent = build_bagel_agent_with_stub(success=False, error="No response from extractor")
    agent.planner.enable_fallback = False
    session = Session(flow="bagel")

    reply = agent.run_turn(session, "everything bagel with roast beef")

    assert session.state.bread_type == "everything"
    assert session.state.filling == "roast beef"
    assert "any extras" in reply.lower()
