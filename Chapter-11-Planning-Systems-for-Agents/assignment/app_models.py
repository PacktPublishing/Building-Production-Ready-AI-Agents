from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from pydantic import BaseModel, Field


@dataclass
class PizzaState:
    size: str | None = None
    crust: str | None = None
    toppings: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    address: str | None = None
    payment_method: str | None = None
    approved_eta_override: bool = False
    confirmed: bool = False
    review_rejected: bool = False
    order_id: str | None = None


@dataclass
class BagelState:
    bread_type: str | None = None
    filling: str | None = None
    extras: list[str] = field(default_factory=list)
    allergies: list[str] = field(default_factory=list)
    address: str | None = None
    payment_method: str | None = None
    approved_eta_override: bool = False
    confirmed: bool = False
    review_rejected: bool = False
    order_id: str | None = None


@dataclass
class PlanStep:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class StepResult:
    status: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


class ChatRequest(BaseModel):
    session_id: str | None = None
    message: str = Field(min_length=1)
    flow: str = "pizza"


class ChatResponse(BaseModel):
    session_id: str
    flow: str
    reply: str
    state: dict[str, Any]
    trace: list[dict[str, Any]]


class PizzaExtraction(BaseModel):
    size: Literal["small", "medium", "large"] | None = None
    crust: Literal["thin", "thick", "gluten-free", "stuffed"] | None = None
    add_toppings: list[str] = Field(default_factory=list)
    replace_toppings: list[str] = Field(default_factory=list)
    remove_toppings: list[str] = Field(default_factory=list)
    address: str | None = None
    payment_method: Literal["card", "cash", "swish", "paypal"] | None = None
    confirmed: bool | None = None
    approved_eta_override: bool | None = None
    review_rejected: bool | None = None
    allergies: list[str] = Field(default_factory=list)


class BagelExtraction(BaseModel):
    bread_type: Literal["sesame", "plain", "everything", "whole wheat", "poppy seed"] | None = None
    filling: Literal["cream cheese", "roast beef", "turkey", "salmon", "avocado", "ham"] | None = None
    add_extras: list[str] = Field(default_factory=list)
    replace_extras: list[str] = Field(default_factory=list)
    remove_extras: list[str] = Field(default_factory=list)
    address: str | None = None
    payment_method: Literal["card", "cash", "swish", "paypal"] | None = None
    confirmed: bool | None = None
    approved_eta_override: bool | None = None
    review_rejected: bool | None = None
    allergies: list[str] = Field(default_factory=list)


class Session:
    def __init__(self, flow: str = "pizza") -> None:
        self.flow = flow
        self.state: PizzaState | BagelState = PizzaState() if flow == "pizza" else BagelState()
        self.trace: list[dict[str, Any]] = []
