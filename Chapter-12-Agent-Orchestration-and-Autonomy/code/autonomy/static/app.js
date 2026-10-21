const state = {
  sessionId: null,
  session: null,
};

const $ = (id) => document.getElementById(id);

function money(value) {
  if (typeof value !== "number") return "-";
  return `$${value.toFixed(2)}`;
}

function readConfig() {
  return {
    target_profit: Number($("target-profit").value),
    starting_cash: Number($("starting-cash").value),
    max_cycles: Number($("max-cycles").value),
    manual_quote_check: $("manual-quote").checked,
    manual_risk_check: $("manual-risk").checked,
    manual_trade_approval: $("manual-trade").checked,
  };
}

function renderEvents(events) {
  const root = $("events");
  if (!events || events.length === 0) {
    root.innerHTML = "<div class='event'>No events yet.</div>";
    return;
  }

  root.innerHTML = events
    .map(
      (e) =>
        `<div class="event"><span class="step">${e.step}</span> ${e.message} <span style="color:#6a8594">(${new Date(e.ts).toLocaleTimeString()})</span></div>`,
    )
    .join("");

  root.scrollTop = root.scrollHeight;
}

function renderSession(session) {
  state.session = session;

  $("status").textContent = session.status;
  $("status").className = `status ${session.status}`;
  $("cycle").textContent = `${session.cycle}/${session.max_cycles}`;
  $("price").textContent = money(session.price);
  $("action").textContent = session.current_action || "-";
  $("profit").textContent = money(session.profit);
  $("net-worth").textContent = money(session.net_worth);
  $("pending").textContent = session.pending_step || "none";
  $("risk").textContent = session.current_risk || "-";
  $("reason").textContent = `${session.current_reason || ""} ${session.current_risk_note || ""}`.trim();

  renderEvents(session.events);
}

async function postJson(url, payload) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await res.json();
  if (!res.ok) {
    throw new Error(body.detail || "Request failed");
  }
  return body;
}

async function startSession() {
  try {
    const body = await postJson("/api/sessions", readConfig());
    state.sessionId = body.session_id;
    renderSession(body);
  } catch (error) {
    alert(error.message);
  }
}

async function advanceSession() {
  if (!state.sessionId) {
    alert("Start a session first.");
    return;
  }

  try {
    const body = await postJson(`/api/sessions/${state.sessionId}/advance`, {});
    renderSession(body);
  } catch (error) {
    alert(error.message);
  }
}

async function manualDecision(approve) {
  if (!state.sessionId) {
    alert("Start a session first.");
    return;
  }

  if (!state.session || state.session.status !== "awaiting_manual") {
    alert("No manual checkpoint is currently pending.");
    return;
  }

  try {
    const body = await postJson(`/api/sessions/${state.sessionId}/manual`, {
      approve,
      note: approve ? "Approved from UI" : "Rejected from UI",
    });
    renderSession(body);
  } catch (error) {
    alert(error.message);
  }
}

$("start-btn").addEventListener("click", startSession);
$("advance-btn").addEventListener("click", advanceSession);
$("approve-btn").addEventListener("click", () => manualDecision(true));
$("reject-btn").addEventListener("click", () => manualDecision(false));
