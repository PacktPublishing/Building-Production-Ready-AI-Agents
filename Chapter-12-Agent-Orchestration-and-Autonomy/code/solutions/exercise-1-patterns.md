# Exercise 1 Running Solution: Orchestration Patterns

This solution guide gives you a reproducible run for the patterns exercise. The goal is to help you build confidence by running the same request across strategies and confirming that behavior changes for the right reasons.

Use this from the Chapter 12 code folder:

```bash
cd Chapter-12-Agent-Orchestration-and-Autonomy/code
uv sync
```

Run all three pattern scripts with the same request so differences are caused by orchestration only:

```bash
uv run sequential.py --request "Book a trip to Tokyo next month with budget 1800 for 1 traveler"
uv run parallel.py --request "Book a trip to Tokyo next month with budget 1800 for 1 traveler"
uv run routed.py --request "Book a trip to Tokyo next month with budget 1800 for 1 traveler" --approval-limit 1200 --blocked-limit 2500
```

What to verify after each run:

- Sequential: stages execute one after another.
- Parallel: independent option gathering happens together.
- Routed: quote collection happens before route decision, then route is approved, approval, or blocked.

Now verify the same scenario visually in the workbench:

```bash
cd workbench
uv sync
uv run uvicorn app:app --reload --port 8012
```

Open <http://127.0.0.1:8012/> and run the same request with sequential, parallel, and routed selected.

Use this confidence checklist:

- The user-facing question order changes by strategy.
- Policy timing changes in routed mode.
- Approval prompts happen before booking side effects.

Mini extension (expected behavior):

```bash
cd ..
uv run routed.py --request "Book a trip to Tokyo next month with budget 1800 for 1 traveler" --approval-limit 900 --blocked-limit 2500
```

With a lower approval limit, the same request should enter approval more often. That confirms routing sensitivity to policy thresholds.
