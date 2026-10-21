import os

import httpx
import pytest

from main import OllamaClient, PizzaState


def _is_ollama_reachable(host: str) -> bool:
    try:
        with httpx.Client(timeout=2.0) as client:
            response = client.get(f"{host}/api/tags")
            return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="module")
def live_client():
    host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
    if not _is_ollama_reachable(host):
        pytest.skip(f"Ollama is not reachable at {host}")
    return OllamaClient()


@pytest.mark.integration
def test_llm_extracts_core_order_fields(live_client):
    state = PizzaState()
    message = (
        "I'd like a medium thin crust pizza with olives and paprika, "
        "deliver to 10 Main St, NY, and pay by card."
    )

    updates, meta = live_client.extract_order_update(message, state)

    assert meta.get("mode") == "llm"
    assert meta.get("success") is True
    assert updates.get("size") == "medium"
    assert updates.get("crust") == "thin"
    assert updates.get("payment_method") == "card"
    assert "olives" in updates.get("add_toppings", [])
    assert "paprika" in updates.get("add_toppings", [])
    assert "10 Main St" in updates.get("address", "")


@pytest.mark.integration
def test_llm_extracts_replace_and_remove_toppings(live_client):
    state = PizzaState(toppings=["olives", "ham"]) 

    replace_updates, replace_meta = live_client.extract_order_update(
        "Change toppings to mushrooms and onions", state
    )
    assert replace_meta.get("success") is True
    assert sorted(replace_updates.get("replace_toppings", [])) == ["mushrooms", "onions"]

    remove_updates, remove_meta = live_client.extract_order_update("Remove onions", state)
    assert remove_meta.get("success") is True
    assert remove_updates.get("remove_toppings") == ["onions"]
