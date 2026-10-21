from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PlanStep:
    description: str
    tool: str
    params: Dict[str, str]


@dataclass
class Plan:
    steps: list[PlanStep]
    service_name: str


@dataclass
class StepResult:
    description: str
    tool: str
    success: bool
    message: str
    details: Optional[Dict[str, object]] = None


@dataclass
class RunMetrics:
    steps_attempted: int = 0
    steps_succeeded: int = 0
    steps_failed: int = 0
    retry_count: int = 0
    replan_count: int = 0
    approval_prompts: int = 0
    approval_granted: int = 0

    def success_rate(self) -> float:
        if self.steps_attempted == 0:
            return 0.0
        return (self.steps_succeeded / self.steps_attempted) * 100.0


@dataclass
class StepPolicy:
    max_retries: int = 0
    requires_approval: bool = False
    approval_prompt: str = ""
