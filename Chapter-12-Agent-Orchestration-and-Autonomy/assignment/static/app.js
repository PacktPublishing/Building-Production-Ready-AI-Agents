const state = {
  sessionId: null,
};

const sessionMeta = document.getElementById("sessionMeta");
const statusMeta = document.getElementById("statusMeta");
const responseBox = document.getElementById("responseBox");
const stateBox = document.getElementById("stateBox");
const traceBox = document.getElementById("traceBox");
const messageInput = document.getElementById("messageInput");

function render(payload) {
  state.sessionId = payload.session_id;
  sessionMeta.textContent = `Session: ${payload.session_id}`;
  statusMeta.textContent = `Status: ${payload.status}`;
  responseBox.textContent = payload.message;
  stateBox.textContent = JSON.stringify(payload.state, null, 2);
  traceBox.innerHTML = payload.trace
    .slice()
    .reverse()
    .map((event) => `
      <div class="trace-item">
        <div><strong>${event.step}</strong></div>
        <div class="meta">${event.ts}</div>
        <div>${event.message}</div>
        <pre>${JSON.stringify(event.data, null, 2)}</pre>
      </div>
    `)
    .join("");
}

async function callJson(url, payload = null) {
  const response = await fetch(url, {
    method: payload ? "POST" : "GET",
    headers: payload ? { "Content-Type": "application/json" } : undefined,
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.detail || "Request failed");
  }
  return response.json();
}

async function requireSession() {
  if (state.sessionId) {
    return state.sessionId;
  }
  const payload = await callJson("/api/session", {});
  render(payload);
  return payload.session_id;
}

document.getElementById("newSession").addEventListener("click", async () => {
  const payload = await callJson("/api/session", {});
  render(payload);
});

document.getElementById("sendMessage").addEventListener("click", async () => {
  const sessionId = await requireSession();
  const payload = await callJson("/api/chat", {
    session_id: sessionId,
    message: messageInput.value,
  });
  render(payload);
});

document.getElementById("approve").addEventListener("click", async () => {
  const sessionId = await requireSession();
  const payload = await callJson("/api/approval", {
    session_id: sessionId,
    approve: true,
  });
  render(payload);
});

document.getElementById("deny").addEventListener("click", async () => {
  const sessionId = await requireSession();
  const payload = await callJson("/api/approval", {
    session_id: sessionId,
    approve: false,
  });
  render(payload);
});

document.getElementById("resume").addEventListener("click", async () => {
  const sessionId = await requireSession();
  const payload = await callJson("/api/resume", {
    session_id: sessionId,
  });
  render(payload);
});