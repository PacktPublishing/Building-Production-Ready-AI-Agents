# Exercise 2 Running Solution: Autonomy Levels and Approval Gates (CLI)

This solution guide runs the autonomy exercise entirely from the command line. The objective is to keep workflow shape stable while changing only decision authority and then compare pause behavior.

## Start the app

From this folder, install dependencies and start the API server:

```bash
cd Chapter-12-Agent-Orchestration-and-Autonomy/code/autonomy
uv sync
uv run uvicorn app:app --port 8013
```

Leave that running in one terminal. Use a second terminal for API calls.

## Helper: pipe a session through its checkpoints

The session pauses on manual checkpoints. Define this PowerShell function once in your second terminal. It accepts the session object returned by the create request, then keeps approving each pending step until the run finishes:

```powershell
function Complete-AutonomySession {
  param(
    [Parameter(Mandatory, ValueFromPipelineByPropertyName)]
    [string]$session_id
  )

  process {
    while ($true) {
      $state = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8013/api/sessions/$session_id"
      if ($state.status -eq "completed") {
        $state | ConvertTo-Json -Depth 8
        break
      }

      if ($state.status -eq "awaiting_manual") {
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8013/api/sessions/$session_id/manual" -ContentType "application/json" -Body '{"approve": true, "note": "cli-approve"}' | Out-Null
      }
      else {
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8013/api/sessions/$session_id/advance" | Out-Null
      }
    }
  }
}
```

What this helper does:

- PowerShell binds the response object's `session_id` property to the function parameter.
- The loop reads the current state before choosing the next API call.
- A manual pause is approved explicitly; any other nonterminal state advances normally.
- The completed session is printed as JSON so you can inspect its final state and event history.

## Pass 1: all manual checks ON

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8013/api/sessions" -ContentType "application/json" -Body '{"target_profit":300,"starting_cash":5000,"max_cycles":12,"manual_quote_check":true,"manual_risk_check":true,"manual_trade_approval":true}' | Complete-AutonomySession
```

Expected outcome: more pauses across quote, risk, and trade approval checkpoints.

## Pass 2: mixed authority

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8013/api/sessions" -ContentType "application/json" -Body '{"target_profit":300,"starting_cash":5000,"max_cycles":12,"manual_quote_check":false,"manual_risk_check":true,"manual_trade_approval":true}' | Complete-AutonomySession
```

Expected outcome: fewer pauses than pass 1 while trade approval is still enforced.

## Pass 3: higher autonomy within policy

```powershell
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8013/api/sessions" -ContentType "application/json" -Body '{"target_profit":300,"starting_cash":5000,"max_cycles":12,"manual_quote_check":false,"manual_risk_check":false,"manual_trade_approval":true}' | Complete-AutonomySession
```

Expected outcome: pause count drops again, but high-impact trade actions still require manual approval.

## Confidence checklist

- Workflow stages remain the same.
- Only authority settings change.
- Trade approval remains protected.

If your three runs show that pattern, your autonomy policy controls are working as intended.
