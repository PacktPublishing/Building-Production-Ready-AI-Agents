/**
 * IT Support Triage System — Kanban Pipeline UI
 *
 * Flow: Inbox → Being Analyzed → Triaged
 * Each ticket moves through the columns individually.
 */

const API_BASE = "/api";

const SAMPLES = [
    { id: "T-001", sender: "alice@company.com", message: "My laptop won't turn on after the latest Windows update. I've tried holding the power button for 30 seconds but nothing happens. I have a client presentation in 2 hours!" },
    { id: "T-002", sender: "bob@company.com", message: "I can't access the shared drive. It keeps saying 'access denied'. I was able to access it yesterday. My colleague sitting next to me can still access it fine." },
    { id: "T-003", sender: "carol@company.com", message: "I received a suspicious email from what looks like our CEO asking me to wire $50,000 to a new vendor. The email address looks slightly different from the real one. Should I report this?" },
    { id: "T-004", sender: "dave@company.com", message: "The internet keeps dropping every 10 minutes across the entire 3rd floor. Multiple people are affected and we can't join video calls. This started after maintenance last night." },
    { id: "T-005", sender: "eve@company.com", message: "Outlook stopped syncing this morning. I haven't received any emails since 8 AM. I've tried restarting Outlook and clearing the cache but it didn't help. I'm expecting an important contract today." },
    { id: "T-006", sender: "frank@company.com", message: "My computer has become extremely slow since IT installed the new antivirus software yesterday. Applications take 2-3 minutes to open and it freezes constantly. I can barely work." },
];

let ticketIdCounter = 100;

// Per-ticket timers: ticketId -> { start, interval }
const activeTimers = {};

// ─── Initialization ───────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
    checkHealth();
    updateAllCounts();
});

async function checkHealth() {
    const statusEl = document.getElementById("connection-status");
    const modelEl = document.getElementById("model-name");
    try {
        const resp = await fetch(`${API_BASE}/health`);
        const data = await resp.json();
        if (data.ollama_connected) {
            statusEl.textContent = "✅ Connected";
            statusEl.className = "status-indicator connected";
        } else {
            statusEl.textContent = "⚠️ Ollama disconnected";
            statusEl.className = "status-indicator disconnected";
        }
        modelEl.textContent = data.model || "";
    } catch {
        statusEl.textContent = "❌ API unavailable";
        statusEl.className = "status-indicator disconnected";
        modelEl.textContent = "";
    }
}

// ─── Inbox Management ────────────────────────────────────────────

function addToInbox(ticket) {
    const list = document.getElementById("inbox-list");

    // Remove empty state if present
    const empty = list.querySelector(".empty-state");
    if (empty) empty.remove();

    const card = document.createElement("div");
    card.className = "inbox-card";
    card.id = `inbox-${ticket.id}`;
    card.dataset.ticketId = ticket.id;
    card.dataset.sender = ticket.sender;
    card.dataset.message = ticket.message;

    card.innerHTML = `
        <div class="inbox-card-header">
            <span class="inbox-card-id">${esc(ticket.id)}</span>
            <span class="inbox-card-sender">${esc(ticket.sender)}</span>
        </div>
        <div class="inbox-card-message">${esc(ticket.message)}</div>
        <div class="inbox-card-actions">
            <button class="btn btn-analyze" onclick="analyzeTicket('${esc(ticket.id)}')">
                🔍 Analyze
            </button>
        </div>
    `;

    list.appendChild(card);
    updateAllCounts();
}

function loadAllSamples() {
    // Only add samples not already in any column
    for (const sample of SAMPLES) {
        if (!document.getElementById(`inbox-${sample.id}`) &&
            !document.getElementById(`analyzing-${sample.id}`) &&
            !document.getElementById(`triaged-${sample.id}`)) {
            addToInbox(sample);
        }
    }
}

function addCustomTicket() {
    document.getElementById("modal-overlay").classList.remove("hidden");
    document.getElementById("modal-sender").value = "";
    document.getElementById("modal-message").value = "";
    setTimeout(() => document.getElementById("modal-sender").focus(), 100);
}

function closeModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById("modal-overlay").classList.add("hidden");
}

function submitCustomTicket() {
    const sender = document.getElementById("modal-sender").value.trim() || "unknown";
    const message = document.getElementById("modal-message").value.trim();
    if (!message) return;

    ticketIdCounter++;
    addToInbox({ id: `T-${ticketIdCounter}`, sender, message });
    closeModal();
}

// ─── Analyze: Move Inbox → Analyzing → Triaged ──────────────────

async function analyzeTicket(ticketId) {
    const inboxCard = document.getElementById(`inbox-${ticketId}`);
    if (!inboxCard) return;

    const ticket = {
        id: inboxCard.dataset.ticketId,
        sender: inboxCard.dataset.sender,
        message: inboxCard.dataset.message,
    };

    // Remove from inbox
    inboxCard.remove();

    // Add to analyzing column
    const analyzingList = document.getElementById("analyzing-list");
    const empty = analyzingList.querySelector(".empty-state");
    if (empty) empty.remove();

    const card = document.createElement("div");
    card.className = "analyzing-card";
    card.id = `analyzing-${ticket.id}`;
    card.innerHTML = `
        <div class="analyzing-card-header">
            <span class="analyzing-card-id">${esc(ticket.id)}</span>
            <span class="analyzing-badge">
                <span class="pulse-dot"></span> Analyzing
                <span class="analyzing-timer" id="timer-${ticket.id}">0s</span>
            </span>
        </div>
        <div class="analyzing-card-message">"${esc(truncate(ticket.message, 100))}"</div>
    `;
    analyzingList.appendChild(card);
    updateAllCounts();

    // Start per-ticket timer
    const start = Date.now();
    activeTimers[ticket.id] = setInterval(() => {
        const el = document.getElementById(`timer-${ticket.id}`);
        if (el) el.textContent = `${Math.round((Date.now() - start) / 1000)}s`;
    }, 250);

    // Call API (non-blocking — other tickets stay interactive)
    try {
        const resp = await fetch(`${API_BASE}/triage/stream`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ tickets: [ticket] }),
        });

        if (!resp.ok) {
            throw new Error(`Server error: ${resp.status}`);
        }

        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";

            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const payload = line.slice(6).trim();
                if (payload === "[DONE]") continue;

                try {
                    const event = JSON.parse(payload);
                    moveToTriaged(ticket.id, event.result);
                } catch { /* skip */ }
            }
        }
    } catch (err) {
        // On error, move to triaged with error state
        moveToTriaged(ticket.id, {
            ticket_id: ticket.id,
            category: "Other",
            priority: "medium",
            summary: `Error: ${err.message}`,
            recommended_actions: ["Escalate to L2 Support"],
            reasoning: "Triage failed due to a system error.",
        });
    }
}

function moveToTriaged(ticketId, result) {
    // Stop timer
    if (activeTimers[ticketId]) {
        clearInterval(activeTimers[ticketId]);
        delete activeTimers[ticketId];
    }

    // Remove analyzing card
    const analyzingCard = document.getElementById(`analyzing-${ticketId}`);
    if (analyzingCard) analyzingCard.remove();

    // Add to triaged column
    const triagedList = document.getElementById("triaged-list");
    const empty = triagedList.querySelector(".empty-state");
    if (empty) empty.remove();

    const actionsHtml = result.recommended_actions
        .map((a) => `<li class="action-tag">${esc(a)}</li>`)
        .join("");

    const card = document.createElement("div");
    card.className = `triaged-card priority-${result.priority}`;
    card.id = `triaged-${ticketId}`;

    card.innerHTML = `
        <div class="triaged-card-header">
            <span class="triaged-card-id">${esc(result.ticket_id)}</span>
            <div class="triaged-badges">
                <span class="badge badge-${result.priority}">${esc(result.priority)}</span>
                <span class="badge badge-category">${esc(result.category)}</span>
            </div>
        </div>
        <div class="triaged-card-body">
            <div class="triaged-section">
                <div class="triaged-section-title">Summary</div>
                <p>${esc(result.summary)}</p>
            </div>
            <div class="triaged-section">
                <div class="triaged-section-title">Recommended Actions</div>
                <ul class="action-list">${actionsHtml}</ul>
            </div>
            <div class="triaged-section">
                <div class="triaged-section-title">Reasoning</div>
                <p>${esc(result.reasoning)}</p>
            </div>
        </div>
    `;

    // Insert sorted by priority (critical first)
    const order = { critical: 0, high: 1, medium: 2, low: 3 };
    const newPri = order[result.priority] ?? 4;
    let inserted = false;

    for (const existing of triagedList.children) {
        const cls = [...existing.classList].find((c) => c.startsWith("priority-"));
        const existPri = cls ? order[cls.replace("priority-", "")] ?? 4 : 4;
        if (newPri < existPri) {
            triagedList.insertBefore(card, existing);
            inserted = true;
            break;
        }
    }

    if (!inserted) triagedList.appendChild(card);
    updateAllCounts();
}

// ─── Counts ──────────────────────────────────────────────────────

function updateAllCounts() {
    const inbox = document.getElementById("inbox-list").querySelectorAll(".inbox-card").length;
    const analyzing = document.getElementById("analyzing-list").querySelectorAll(".analyzing-card").length;
    const triaged = document.getElementById("triaged-list").querySelectorAll(".triaged-card").length;

    document.getElementById("inbox-count").textContent = inbox;
    document.getElementById("analyzing-count").textContent = analyzing;
    document.getElementById("triaged-count").textContent = triaged;

    // Show empty states
    showEmptyState("inbox-list", inbox, "📥", "Add tickets or load samples");
    showEmptyState("analyzing-list", analyzing, "⏳", "Click Analyze on a ticket");
    showEmptyState("triaged-list", triaged, "📋", "Results will appear here");
}

function showEmptyState(listId, count, emoji, text) {
    const list = document.getElementById(listId);
    const existing = list.querySelector(".empty-state");
    if (count === 0 && !existing) {
        const el = document.createElement("div");
        el.className = "empty-state";
        el.innerHTML = `<span class="emoji">${emoji}</span>${text}`;
        list.appendChild(el);
    } else if (count > 0 && existing) {
        existing.remove();
    }
}

// ─── Helpers ─────────────────────────────────────────────────────

function esc(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, max) {
    return str.length > max ? str.slice(0, max) + "…" : str;
}
