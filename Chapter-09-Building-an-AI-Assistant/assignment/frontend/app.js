const sessionId = "demo-session";
const healthPill = document.getElementById("health-pill");
const modelPill = document.getElementById("model-pill");
const toolBadge = document.getElementById("tool-badge");
const responseContent = document.getElementById("response-content");
const memoryContent = document.getElementById("memory-content");
const memoryFlag = document.getElementById("memory-flag");
const confirmationBox = document.getElementById("confirmation-box");
const confirmationText = document.getElementById("confirmation-text");
const messageInput = document.getElementById("message-input");

async function refreshHealth() {
    const response = await fetch("/api/health");
    const data = await response.json();
    healthPill.textContent = data.ollama_connected ? "Ollama ready" : "Ollama unavailable";
    healthPill.className = `pill ${data.ollama_connected ? "pill-success" : "pill-danger"}`;
    modelPill.textContent = data.model;
}

async function refreshSession() {
    const response = await fetch(`/api/session/${sessionId}`);
    const data = await response.json();
    memoryContent.innerHTML = "";

    if (data.messages.length === 0) {
        memoryContent.textContent = "No messages yet.";
        memoryFlag.textContent = "Empty";
        return;
    }

    memoryFlag.textContent = `${data.messages.length} messages`;
    for (const message of data.messages) {
        const item = document.createElement("div");
        item.className = `memory-item memory-${message.role}`;
        item.innerHTML = `<strong>${message.role}</strong><p>${escapeHtml(message.content)}</p>`;
        memoryContent.appendChild(item);
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) {
        return;
    }

    responseContent.textContent = "Thinking...";
    const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message }),
    });
    const data = await response.json();

    responseContent.innerHTML = `
        <p>${escapeHtml(data.reply)}</p>
        <div class="evidence-block">
            <div><strong>Tool</strong>: ${escapeHtml(data.selected_tool)}</div>
            <div><strong>Output</strong>: ${escapeHtml(data.tool_output)}</div>
        </div>
    `;
    toolBadge.textContent = data.selected_tool;
    memoryFlag.textContent = data.used_memory ? "Used memory" : "Fresh turn";

    if (data.needs_confirmation) {
        confirmationText.textContent = data.pending_action_label;
        confirmationBox.classList.remove("hidden");
    } else {
        confirmationBox.classList.add("hidden");
    }

    messageInput.value = "";
    await refreshSession();
}

async function sendConfirmation(approve) {
    const response = await fetch("/api/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, approve }),
    });
    const data = await response.json();
    responseContent.innerHTML = `<p>${escapeHtml(data.reply)}</p><div class="evidence-block"><div><strong>Output</strong>: ${escapeHtml(data.tool_output)}</div></div>`;
    confirmationBox.classList.add("hidden");
    await refreshSession();
}

function escapeHtml(value) {
    const div = document.createElement("div");
    div.textContent = value;
    return div.innerHTML;
}

document.getElementById("send-button").addEventListener("click", sendMessage);
document.getElementById("approve-button").addEventListener("click", () => sendConfirmation(true));
document.getElementById("reject-button").addEventListener("click", () => sendConfirmation(false));

for (const button of document.querySelectorAll("[data-sample]")) {
    button.addEventListener("click", () => {
        messageInput.value = button.dataset.sample;
    });
}

refreshHealth();
refreshSession();
