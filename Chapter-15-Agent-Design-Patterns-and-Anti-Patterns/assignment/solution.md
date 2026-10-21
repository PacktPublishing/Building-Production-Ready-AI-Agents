# Exercise 4 Solution: Assignment Reference

## Problem
Design a pattern-driven architecture for a policy-constrained travel workflow and present it as a team-ready design brief.

## Scenario
- Traveler: sales lead attending partner meetings in Copenhagen (Aug 12-15).
- Constraints: total spend <= 2200 USD, hotel <= 320 USD/night, prefer flights arriving before 14:00 local time.
- Policy rule: any itinerary above 1800 USD requires explicit manager approval before booking.
- Reliability rule: if booking tools fail, return a partial plan with clear status.

## What is required

- Provide a short architecture decision note (what you chose, why, and tradeoffs).
- Include a failure table with at least three anti-pattern risks and mitigations.
- Specify guardrails (input validation, confirmation tiers, fallback behavior).
- Define evaluation dimensions now and defer numeric pass/fail thresholds to Chapter 16.
- Add production notes for Chapter 17 (budgets, rollback, human checkpoints).

## Solution

**Architecture decision**

For this workflow, we choose an orchestrator + specialists pattern. The request has clear constraints (budget ceiling, hotel cap, arrival-time preference, and approval threshold), so centralized control is more important than open-ended autonomy. In practice, one orchestrator handles routing and policy checks while focused specialists handle retrieval, pricing analysis, and execution. The small orchestration overhead is worth the gain in consistency, auditability, and policy enforcement.

In plain English: one part of the system coordinates the flow, and smaller focused parts do specific jobs. That gives you better control and makes behavior easier to explain when something goes wrong.

**Failure table (risk -> symptom -> mitigation)**

| Risk | Symptom | Mitigation |
|---|---|---|
| Unbounded autonomy | Planner keeps looping and costs rise without better output. | Hard iteration and token limits, plus explicit stop reasons. |
| Tool roulette | Similar requests use different tool paths and produce inconsistent results. | Deterministic routing contract with input validation and tool eligibility checks. |
| Hidden state coupling | A small change in one step causes unexpected behavior in another step. | Explicit state contracts and immutable handoffs between steps. |
| Evaluation last | Team debates quality late because success measures were never defined early. | Define what to measure in this chapter, then set numeric pass/fail thresholds in Chapter 16. |

**Guardrails in this design**

- Input and policy validation first: reject malformed requests or policy violations before planning or tool calls.
- Deterministic routing contract: use a versioned routing table so the same request shape follows the same tool path.
- Tiered confirmation for side effects:
  - Tier 0 read-only actions auto-approve.
  - Tier 1 low-risk writes require rule checks.
  - Tier 2 high-risk writes require human approval.
- Fallback and containment: on repeated planner or tool failures, return a deterministic partial result with explicit status.
- Idempotency for writes: booking/payment calls include idempotency keys to prevent duplicate side effects during retries.
- Degraded-mode safety: policy checks and approval gates remain mandatory even on fallback paths.

In plain English: identical requests should follow the same path, retries should not create duplicate bookings, and safety checks must stay on even when the system is in fallback mode.

**Evaluation checklist (what to measure now, thresholds in Chapter 16)**

- Completion rate
- Unsafe action rate
- Tool error rate
- Latency per task
- Cost per task
- Policy-compliance pass rate

Note: this chapter defines measurement dimensions. Numeric pass/fail thresholds are set in Chapter 16.

**Production readiness notes**

- Runtime limits: define acceptable ranges for response time, token usage, and spend.
- Rollback/kill switch: include a clear mechanism to stop side-effecting actions if unsafe behavior is detected.
- Human checkpoints: require explicit approval at the policy threshold before final booking.
- Operational traceability: keep route, policy, and execution logs connected by a shared correlation ID.

In plain English: know your safety stop button, know when a person must approve, and keep enough logs to explain every major decision.

**How it plays out in this Copenhagen scenario**

The workflow starts by collecting flight and hotel options that satisfy date and arrival constraints. It then applies budget and policy checks before any booking action. If the best itinerary exceeds 1800 USD, execution pauses for manager approval. If a booking API fails, retries are bounded and the system returns partial status (for example, confirmed flight options with pending hotel booking) instead of failing silently.
