let sessionId = null;

const messages = document.getElementById("messages");
const stateView = document.getElementById("state");
const traceView = document.getElementById("trace");
const composer = document.getElementById("composer");
const messageInput = document.getElementById("message");
const sendButton = composer.querySelector("button");
const flowSelect = document.getElementById("flow");
const chatTitle = document.getElementById("chat-title");

function addBubble(text, cls) {
  const div = document.createElement("div");
  div.className = `bubble ${cls}`;
  div.textContent = text;
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

function addPendingBubble() {
  const div = document.createElement("div");
  div.className = "bubble agent pending";
  div.innerHTML = '<span class="pending-row"><span class="spinner"></span><span>Working on your order...</span></span>';
  messages.appendChild(div);
  messages.scrollTop = messages.scrollHeight;
  return div;
}

async function sendMessage(text) {
  const pendingBubble = addPendingBubble();
  sendButton.disabled = true;
  messageInput.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: sessionId, message: text, flow: flowSelect.value }),
    });
    if (!response.ok) {
      throw new Error(`Request failed: ${response.status}`);
    }
    const data = await response.json();
    sessionId = data.session_id;
    stateView.textContent = JSON.stringify(data.state, null, 2);
    traceView.textContent = JSON.stringify(data.trace, null, 2);
    addBubble(data.reply, "agent");
  } finally {
    pendingBubble.remove();
  }
}

function addFlowIntro() {
  const flow = flowSelect.value;
  if (flow === "bagel") {
    chatTitle.textContent = "Bagel Ordering Agent (Planner / Executor / Monitor)";
    messageInput.placeholder = "Type your order request, e.g. sesame with cream cheese and smoked salmon";
    addBubble(
      "Hi, you are in the bagel workflow. Share bread type, filling, and extras. You can also include address and payment in the same message.",
      "agent"
    );
    return;
  }

  chatTitle.textContent = "Pizza Ordering Agent (Planner / Executor / Monitor)";
  messageInput.placeholder = "Type your order request, e.g. medium thin crust with olives";
  addBubble(
    "Hi, you are in the pizza workflow. Please share: size, crust, and toppings. "
    + "You can also include address and payment in the same message. "
    + "Example: medium thin crust with mushrooms, address is 10 Main St, NY, pay by card.",
    "agent"
  );
}

flowSelect.addEventListener("change", () => {
  sessionId = null;
  messages.innerHTML = "";
  stateView.textContent = "{}";
  traceView.textContent = "[]";
  addFlowIntro();
});

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;

  addBubble(text, "user");
  messageInput.value = "";

  try {
    await sendMessage(text);
  } catch (error) {
    addBubble(`Error: ${error.message}`, "agent");
  } finally {
    sendButton.disabled = false;
    messageInput.disabled = false;
    messageInput.focus();
  }
});

(async () => {
  addFlowIntro();
})();
