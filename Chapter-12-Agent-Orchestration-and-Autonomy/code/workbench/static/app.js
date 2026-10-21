const blockCatalog = [
  { id: "collect_intent", label: "Collect Intent" },
  { id: "policy_check", label: "Policy Check" },
  { id: "flight_search", label: "Flight Search" },
  { id: "hotel_search", label: "Hotel Search" },
  { id: "insurance_quote", label: "Insurance Quote" },
  { id: "approval_gate", label: "Approval Gate" },
  { id: "blocked_end", label: "Blocked End" },
  { id: "booking", label: "Booking" },
];

const strategyOrder = {
  sequential: ["flow"],
  parallel: ["intake", "fanout", "finalize"],
  routed: ["intake", "data_collection", "approval", "blocked", "finalize"],
};

const promptEl = document.getElementById("prompt");
const strategyEl = document.getElementById("strategy");
const approvalLimitEl = document.getElementById("approvalLimit");
const blockedLimitEl = document.getElementById("blockedLimit");
const flightQuoteEl = document.getElementById("flightQuote");
const hotelQuoteEl = document.getElementById("hotelQuote");
const insuranceQuoteEl = document.getElementById("insuranceQuote");
const approvalDecisionEl = document.getElementById("approvalDecision");
const runBtn = document.getElementById("runBtn");
const resetBlocksBtn = document.getElementById("resetBlocks");

const paletteEl = document.getElementById("palette");
const canvasEl = document.getElementById("canvas");

const routePill = document.getElementById("routePill");
const questionPill = document.getElementById("questionPill");
const questionsEl = document.getElementById("questions");
const eventsEl = document.getElementById("events");
const narrationEl = document.getElementById("narration");
const executionOutcomeEl = document.getElementById("executionOutcome");
const itineraryListEl = document.getElementById("itineraryList");
const serviceResponsesEl = document.getElementById("serviceResponses");

const currentStepEl = document.getElementById("currentStep");
const ranStepsEl = document.getElementById("ranSteps");
const pendingStepsEl = document.getElementById("pendingSteps");

const approvalModalEl = document.getElementById("approvalModal");
const approveBtn = document.getElementById("approveBtn");
const denyBtn = document.getElementById("denyBtn");
const approvalReasonEl = document.getElementById("approvalReason");
const approvalBudgetEl = document.getElementById("approvalBudget");
const approvalLimitsEl = document.getElementById("approvalLimits");
const approvalEstimateEl = document.getElementById("approvalEstimate");
const approvalWillRunEl = document.getElementById("approvalWillRun");

const itineraryModalEl = document.getElementById("itineraryModal");
const closeItineraryBtn = document.getElementById("closeItineraryBtn");
const itineraryRouteNoteEl = document.getElementById("itineraryRouteNote");
const itineraryDestinationEl = document.getElementById("itineraryDestination");
const itineraryMonthEl = document.getElementById("itineraryMonth");
const itineraryTravelersEl = document.getElementById("itineraryTravelers");
const itineraryBookedItemsEl = document.getElementById("itineraryBookedItems");

const blockedModalEl = document.getElementById("blockedModal");
const blockedReasonEl = document.getElementById("blockedReason");
const closeBlockedBtn = document.getElementById("closeBlockedBtn");

let state = {
  unplaced: new Set(blockCatalog.map((b) => b.id)),
  placed: {},
};

let nodeElements = new Map();
let nodeResponseElements = new Map();
let progressTimer = null;
let pendingApprovalPayload = null;
let activeSocket = null;
let liveServiceResponses = [];
let preserveProgressForRun = false;

const executionState = {
  current: null,
  ran: [],
  pending: [],
};

function labelFor(blockId) {
  return blockCatalog.find((b) => b.id === blockId)?.label || blockId;
}

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n));
}

function toOptionalInt(value) {
  if (!value || value.trim() === "") {
    return null;
  }
  const n = Number.parseInt(value, 10);
  return Number.isNaN(n) ? null : n;
}

function canvasMetrics() {
  const rect = canvasEl.getBoundingClientRect();
  return {
    width: rect.width,
    height: rect.height,
  };
}

function defaultPosition(strategy, blockId, index) {
  const { width, height } = canvasMetrics();

  if (strategy === "sequential") {
    return { x: width * 0.5, y: 80 + index * 66 };
  }

  if (strategy === "parallel") {
    const topRow = {
      collect_intent: { x: width * 0.5, y: 85 },
      policy_check: { x: width * 0.5, y: 155 },
    };
    const fanout = {
      flight_search: { x: width * 0.25, y: height * 0.48 },
      hotel_search: { x: width * 0.5, y: height * 0.48 },
      insurance_quote: { x: width * 0.75, y: height * 0.48 },
    };
    const final = {
      approval_gate: { x: width * 0.5, y: height * 0.72 },
      booking: { x: width * 0.5, y: height * 0.82 },
    };
    return topRow[blockId] || fanout[blockId] || final[blockId] || { x: width * 0.5, y: 90 + index * 60 };
  }

  const intake = {
    collect_intent: { x: width * 0.5, y: 85 },
    policy_check: { x: width * 0.5, y: 160 },
  };
  const dataCollection = {
    flight_search: { x: width * 0.23, y: height * 0.5 },
    hotel_search: { x: width * 0.23, y: height * 0.62 },
    insurance_quote: { x: width * 0.23, y: height * 0.74 },
  };
  const approval = {
    approval_gate: { x: width * 0.5, y: height * 0.56 },
    booking: { x: width * 0.5, y: height * 0.86 },
  };
  const blocked = {
    blocked_end: { x: width * 0.78, y: height * 0.56 },
  };
  return intake[blockId] || dataCollection[blockId] || approval[blockId] || blocked[blockId] || { x: width * 0.8, y: height * 0.56 };
}

function clearProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

function resetExecutionState() {
  clearProgressTimer();
  executionState.current = null;
  executionState.ran = [];
  executionState.pending = selectedBlocks();
  updateStatusPanel();
  applyNodeColors();
}

function resetCanvas() {
  state = {
    unplaced: new Set(blockCatalog.map((b) => b.id)),
    placed: {},
  };

  const strategy = strategyEl.value;
  const defaults =
    strategy === "routed"
      ? [
          "collect_intent",
          "policy_check",
          "flight_search",
          "hotel_search",
          "insurance_quote",
          "approval_gate",
          "blocked_end",
          "booking",
        ]
      : [
          "collect_intent",
          "policy_check",
          "flight_search",
          "hotel_search",
          "insurance_quote",
          "approval_gate",
          "booking",
        ];

  defaults.forEach((blockId, index) => {
    const pos = defaultPosition(strategy, blockId, index);
    state.unplaced.delete(blockId);
    state.placed[blockId] = {
      x: pos.x,
      y: pos.y,
    };
  });

  render();
  resetExecutionState();
}

function renderPalette() {
  paletteEl.innerHTML = "";

  const sorted = [...state.unplaced].sort((a, b) => labelFor(a).localeCompare(labelFor(b)));
  for (const blockId of sorted) {
    const chip = document.createElement("div");
    chip.className = "node state-pending";
    chip.style.position = "static";
    chip.style.transform = "none";
    chip.style.minWidth = "unset";
    chip.draggable = true;
    chip.textContent = labelFor(blockId);

    chip.addEventListener("dragstart", (event) => {
      event.dataTransfer.setData("text/block-id", blockId);
      event.dataTransfer.effectAllowed = "move";
    });

    paletteEl.appendChild(chip);
  }
}

function strategyGuides(strategy) {
  const { width, height } = canvasMetrics();

  if (strategy === "sequential") {
    return {
      labels: [
        { text: "START", x: width * 0.5, y: 30 },
        { text: "END", x: width * 0.5, y: height - 24 },
      ],
      lines: [{ kind: "vertical", x: width * 0.5, y: 52, w: 0, h: height - 88 }],
    };
  }

  if (strategy === "parallel") {
    return {
      labels: [
        { text: "START", x: width * 0.5, y: 28 },
        { text: "FORK", x: width * 0.5, y: height * 0.34 },
        { text: "JOIN", x: width * 0.5, y: height * 0.63 },
        { text: "END", x: width * 0.5, y: height - 24 },
      ],
      lines: [
        { kind: "vertical", x: width * 0.5, y: 46, w: 0, h: height * 0.25 },
        { kind: "horizontal", x: width * 0.2, y: height * 0.41, w: width * 0.6, h: 0 },
        { kind: "horizontal", x: width * 0.2, y: height * 0.56, w: width * 0.6, h: 0 },
        { kind: "vertical", x: width * 0.5, y: height * 0.66, w: 0, h: height * 0.27 },
      ],
    };
  }

  return {
    labels: [
      { text: "START", x: width * 0.5, y: 28 },
      { text: "ROUTE", x: width * 0.5, y: height * 0.3 },
      { text: "DATA COLLECTION", x: width * 0.22, y: height * 0.4 },
      { text: "APPROVAL GATE", x: width * 0.5, y: height * 0.4 },
      { text: "BLOCKED", x: width * 0.78, y: height * 0.4 },
      { text: "BOOKING", x: width * 0.5, y: height * 0.82 },
    ],
    lines: [
      { kind: "vertical", x: width * 0.5, y: 44, w: 0, h: height * 0.23 },
      { kind: "horizontal", x: width * 0.22, y: height * 0.36, w: width * 0.56, h: 0 },
      { kind: "vertical", x: width * 0.22, y: height * 0.37, w: 0, h: height * 0.56 },
      { kind: "vertical", x: width * 0.5, y: height * 0.37, w: 0, h: height * 0.4 },
      { kind: "vertical", x: width * 0.78, y: height * 0.37, w: 0, h: height * 0.28 },
      { kind: "horizontal", x: width * 0.22, y: height * 0.79, w: width * 0.28, h: 0 },
    ],
  };
}

function renderGuides() {
  const guides = strategyGuides(strategyEl.value);

  guides.lines.forEach((line) => {
    const el = document.createElement("div");
    el.className = `guide-line ${line.kind}`;
    el.style.left = `${line.x}px`;
    el.style.top = `${line.y}px`;
    el.style.width = `${line.w}px`;
    el.style.height = `${line.h}px`;
    canvasEl.appendChild(el);
  });

  guides.labels.forEach((label) => {
    const el = document.createElement("div");
    el.className = "guide-label";
    el.textContent = label.text;
    el.style.left = `${label.x}px`;
    el.style.top = `${label.y}px`;
    canvasEl.appendChild(el);
  });
}

function beginDragNode(nodeEl, blockId, event) {
  event.preventDefault();
  const rect = canvasEl.getBoundingClientRect();
  const nodeRect = nodeEl.getBoundingClientRect();

  const offsetX = event.clientX - nodeRect.left;
  const offsetY = event.clientY - nodeRect.top;
  let lastPointerX = event.clientX;
  let lastPointerY = event.clientY;

  nodeEl.classList.add("dragging");

  function updatePaletteHover(clientX, clientY) {
    const paletteRect = paletteEl.getBoundingClientRect();
    const insidePalette =
      clientX >= paletteRect.left &&
      clientX <= paletteRect.right &&
      clientY >= paletteRect.top &&
      clientY <= paletteRect.bottom;

    paletteEl.classList.toggle("is-over", insidePalette);
    return insidePalette;
  }

  function onMove(moveEvent) {
    lastPointerX = moveEvent.clientX;
    lastPointerY = moveEvent.clientY;

    const x = clamp(moveEvent.clientX - rect.left - offsetX + nodeRect.width / 2, 80, rect.width - 80);
    const y = clamp(moveEvent.clientY - rect.top - offsetY + nodeRect.height / 2, 40, rect.height - 30);

    state.placed[blockId] = { x, y };
    nodeEl.style.left = `${x}px`;
    nodeEl.style.top = `${y}px`;

    updatePaletteHover(moveEvent.clientX, moveEvent.clientY);
  }

  function onUp() {
    const droppedInPalette = updatePaletteHover(lastPointerX, lastPointerY);

    nodeEl.classList.remove("dragging");
    paletteEl.classList.remove("is-over");

    if (droppedInPalette) {
      delete state.placed[blockId];
      state.unplaced.add(blockId);
      render();
      resetExecutionState();
    }

    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  }

  window.addEventListener("pointermove", onMove);
  window.addEventListener("pointerup", onUp);
}

function renderPlacedNodes() {
  nodeElements = new Map();
  nodeResponseElements = new Map();
  const ids = Object.keys(state.placed);
  for (const blockId of ids) {
    const pos = state.placed[blockId];
    const node = document.createElement("div");
    node.className = "node state-pending";
    node.dataset.blockId = blockId;

    const label = document.createElement("span");
    label.className = "node-label";
    label.textContent = labelFor(blockId);

    const response = document.createElement("div");
    response.className = "node-response";

    node.appendChild(label);
    node.appendChild(response);

    node.style.left = `${pos.x}px`;
    node.style.top = `${pos.y}px`;

    node.addEventListener("pointerdown", (event) => beginDragNode(node, blockId, event));
    node.addEventListener("dblclick", () => {
      delete state.placed[blockId];
      state.unplaced.add(blockId);
      render();
      resetExecutionState();
    });

    nodeElements.set(blockId, node);
    nodeResponseElements.set(blockId, response);
    canvasEl.appendChild(node);
  }

  refreshNodeResponseLabels();
}

function setupDropTargets() {
  paletteEl.addEventListener("dragover", (event) => {
    event.preventDefault();
    paletteEl.classList.add("is-over");
  });

  paletteEl.addEventListener("dragleave", () => {
    paletteEl.classList.remove("is-over");
  });

  paletteEl.addEventListener("drop", (event) => {
    event.preventDefault();
    paletteEl.classList.remove("is-over");
    const blockId = event.dataTransfer.getData("text/block-id");
    if (!blockId) {
      return;
    }
    delete state.placed[blockId];
    state.unplaced.add(blockId);
    render();
    resetExecutionState();
  });

  canvasEl.addEventListener("dragover", (event) => {
    event.preventDefault();
    canvasEl.classList.add("is-over");
  });

  canvasEl.addEventListener("dragleave", () => {
    canvasEl.classList.remove("is-over");
  });

  canvasEl.addEventListener("drop", (event) => {
    event.preventDefault();
    canvasEl.classList.remove("is-over");

    const blockId = event.dataTransfer.getData("text/block-id");
    if (!blockId) {
      return;
    }

    const rect = canvasEl.getBoundingClientRect();
    const x = clamp(event.clientX - rect.left, 80, rect.width - 80);
    const y = clamp(event.clientY - rect.top, 38, rect.height - 30);

    state.unplaced.delete(blockId);
    state.placed[blockId] = { x, y };
    render();
    resetExecutionState();
  });
}

function stageForPosition(strategy, pos) {
  const { width, height } = canvasMetrics();

  if (strategy === "sequential") {
    return "flow";
  }

  if (strategy === "parallel") {
    if (pos.y < height * 0.34) {
      return "intake";
    }
    if (pos.y < height * 0.64) {
      return "fanout";
    }
    return "finalize";
  }

  if (pos.y < height * 0.36) {
    return "intake";
  }
  if (pos.y > height * 0.78) {
    return "finalize";
  }
  if (pos.x < width * 0.4) {
    return "data_collection";
  }
  if (pos.x < width * 0.67) {
    return "approval";
  }
  return "blocked";
}

function selectedBlocks() {
  const strategy = strategyEl.value;
  const order = strategyOrder[strategy] || [];

  const buckets = {
    flow: [],
    intake: [],
    fanout: [],
    finalize: [],
    data_collection: [],
    approval: [],
    blocked: [],
  };

  Object.entries(state.placed).forEach(([blockId, pos]) => {
    const stage = stageForPosition(strategy, pos);
    if (!buckets[stage]) {
      return;
    }
    buckets[stage].push({ blockId, x: pos.x, y: pos.y });
  });

  const out = [];
  order.forEach((stage) => {
    const sorted = buckets[stage].sort((a, b) => {
      if (stage === "fanout") {
        return a.x - b.x || a.y - b.y;
      }
      return a.y - b.y || a.x - b.x;
    });
    sorted.forEach((item) => out.push(item.blockId));
  });

  return out;
}

function extractVisitedBlocks(events) {
  const out = [];
  for (const event of events) {
    if (event.step === "flow") {
      const match = /Entered block:\s*([a-z_]+)/i.exec(event.message || "");
      if (match && match[1]) {
        out.push(match[1]);
      }
    }
  }
  return out;
}

function updateStatusPanel() {
  currentStepEl.textContent = executionState.current ? labelFor(executionState.current) : "-";

  ranStepsEl.innerHTML = "";
  executionState.ran.forEach((blockId) => {
    const li = document.createElement("li");
    li.textContent = labelFor(blockId);
    ranStepsEl.appendChild(li);
  });

  pendingStepsEl.innerHTML = "";
  executionState.pending.forEach((blockId) => {
    const li = document.createElement("li");
    li.textContent = labelFor(blockId);
    pendingStepsEl.appendChild(li);
  });
}

function applyNodeColors() {
  nodeElements.forEach((nodeEl, blockId) => {
    nodeEl.classList.remove("state-pending", "state-done", "state-active");

    if (executionState.current === blockId) {
      nodeEl.classList.add("state-active");
      return;
    }

    if (executionState.ran.includes(blockId)) {
      nodeEl.classList.add("state-done");
      return;
    }

    nodeEl.classList.add("state-pending");
  });
}

function setExecutionProgress(current, ran, pending) {
  executionState.current = current;
  executionState.ran = [...ran];
  executionState.pending = [...pending];
  updateStatusPanel();
  applyNodeColors();
}

function closeActiveSocket() {
  if (activeSocket) {
    try {
      activeSocket.close();
    } catch {
      // Ignore cleanup failures when replacing runs.
    }
    activeSocket = null;
  }
}

function applySimulationResult(data) {
  routePill.textContent = `route: ${data.route}`;
  questionPill.textContent = `questions: ${data.questions.length}`;

  questionsEl.innerHTML = "";
  for (const question of data.questions) {
    const li = document.createElement("li");
    li.textContent = question;
    questionsEl.appendChild(li);
  }

  eventsEl.innerHTML = "";
  for (const event of data.events) {
    const row = document.createElement("div");
    row.className = "event";
    row.innerHTML = `<strong>${event.step}</strong><div>${event.message}</div>`;
    eventsEl.appendChild(row);
  }

  narrationEl.textContent = data.narration || "No narration.";
  renderExecutionOutcome(data);
  renderServiceResponses(data);
  hydrateQuoteOverridesFromResult(data);
}

function renderServiceResponses(data) {
  serviceResponsesEl.innerHTML = "";
  const results = Array.isArray(data.block_results) ? data.block_results : [];

  if (results.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No service responses for this run.";
    serviceResponsesEl.appendChild(li);
    return;
  }

  results.forEach((item) => {
    const blockId = item.block;
    const response = item.response || {};
    const status = item.status || "done";
    const li = document.createElement("li");
    li.textContent = `${labelFor(blockId)} [${status}]: ${formatBlockResponse(blockId, response)}`;
    serviceResponsesEl.appendChild(li);
  });
}

function upsertLiveServiceResponse(item) {
  if (!item || !item.block) {
    return;
  }

  const idx = liveServiceResponses.findIndex((r) => r.block === item.block);
  if (idx >= 0) {
    liveServiceResponses[idx] = item;
  } else {
    liveServiceResponses.push(item);
  }

  applyNodeResponseLabel(item.block, item);
  renderServiceResponses({ block_results: liveServiceResponses });
}

function formatNodeResponse(blockId, response, status) {
  if (blockId === "flight_search" || blockId === "hotel_search" || blockId === "insurance_quote") {
    return `$${response.quote ?? "-"}`;
  }
  if (blockId === "approval_gate") {
    if (response.approved === true) {
      return "approved=true";
    }
    if (response.approved === false) {
      return "approved=false";
    }
    return "approved=pending";
  }
  if (blockId === "booking") {
    return response.executed ? `executed: $${response.total ?? "-"}` : `skipped: ${response.reason ?? status}`;
  }
  if (blockId === "blocked_end") {
    return "blocked";
  }
  if (blockId === "policy_check") {
    return `route=${response.route ?? "-"}`;
  }
  return Object.entries(response)
    .slice(0, 1)
    .map(([k, v]) => `${k}=${v == null ? "null" : v}`)
    .join(", ");
}

function applyNodeResponseLabel(blockId, item) {
  const responseEl = nodeResponseElements.get(blockId);
  if (!responseEl) {
    return;
  }

  const status = item?.status || "done";
  const response = item?.response || {};
  const text = formatNodeResponse(blockId, response, status);

  if (!text) {
    responseEl.textContent = "";
    responseEl.classList.remove("has-value");
    return;
  }

  responseEl.textContent = text;
  responseEl.title = formatBlockResponse(blockId, response);
  responseEl.classList.add("has-value");
}

function refreshNodeResponseLabels() {
  liveServiceResponses.forEach((item) => {
    applyNodeResponseLabel(item.block, item);
  });
}

function clearNodeResponseLabels() {
  nodeResponseElements.forEach((responseEl) => {
    responseEl.textContent = "";
    responseEl.title = "";
    responseEl.classList.remove("has-value");
  });
}

function formatBlockResponse(blockId, response) {
  if (blockId === "flight_search" || blockId === "hotel_search" || blockId === "insurance_quote") {
    return `quote=${response.quote ?? "-"} ${response.currency ?? "USD"} (source=${response.source ?? "estimated"})`;
  }

  if (blockId === "approval_gate") {
    const approved =
      response.approved === true ? "true" : response.approved === false ? "false" : "null";
    return `decision=${response.decision ?? "pending"}, approved=${approved}`;
  }

  if (blockId === "booking") {
    if (response.executed) {
      return `executed=true, total=${response.total ?? "-"}`;
    }
    return `executed=false, reason=${response.reason ?? "not provided"}`;
  }

  if (blockId === "blocked_end") {
    return `blocked=${response.blocked === true ? "true" : "false"}, reason=${response.reason ?? "not provided"}`;
  }

  const pairs = Object.entries(response)
    .map(([k, v]) => `${k}=${v == null ? "null" : v}`)
    .join(", ");
  return pairs || "no response payload";
}

function hydrateQuoteOverridesFromResult(data) {
  const components = data.quote_components || {};
  if (!flightQuoteEl.value && components.flight_search != null) {
    flightQuoteEl.value = `${components.flight_search}`;
  }
  if (!hotelQuoteEl.value && components.hotel_search != null) {
    hotelQuoteEl.value = `${components.hotel_search}`;
  }
  if (!insuranceQuoteEl.value && components.insurance_quote != null) {
    insuranceQuoteEl.value = `${components.insurance_quote}`;
  }
}

async function prefillQuoteOverridesFromService() {
  const payload = {
    prompt: promptEl.value,
    strategy: "routed",
    blocks: selectedBlocks(),
    approval_limit: toOptionalInt(approvalLimitEl.value),
    blocked_limit: toOptionalInt(blockedLimitEl.value),
    flight_quote: null,
    hotel_quote: null,
    insurance_quote: null,
    approval_decision: null,
  };

  try {
    const response = await fetch("/api/simulate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return;
    }
    const data = await response.json();
    hydrateQuoteOverridesFromResult(data);
  } catch {
    // Ignore prefill failures and keep inputs editable.
  }
}

function renderExecutionOutcome(data) {
  const outcome = data.execution_outcome || "no_execution";
  const itinerary = data.itinerary;

  itineraryListEl.innerHTML = "";

  if (outcome === "booking_executed" && itinerary) {
    executionOutcomeEl.className = "result-ok";
    executionOutcomeEl.textContent = "Booking executed. Itinerary created.";

    closeBlockedModal();
    openItineraryModal(itinerary, data.route);

    const items = [
      `Destination: ${itinerary.destination ?? "-"}`,
      `Month: ${itinerary.month ?? "-"}`,
      `Travelers: ${itinerary.travelers ?? "-"}`,
      `Flight quote: ${itinerary.flight ?? "-"}`,
      `Hotel quote: ${itinerary.hotel ?? "-"}`,
      `Insurance quote: ${itinerary.insurance ?? "-"}`,
      `Total: ${itinerary.total ?? "-"}`,
    ];
    items.forEach((text) => {
      const li = document.createElement("li");
      li.textContent = text;
      itineraryListEl.appendChild(li);
    });
    return;
  }

  executionOutcomeEl.className = "result-warn";
  if (outcome === "awaiting_human_approval") {
    executionOutcomeEl.textContent = "Awaiting approval. No booking side effects executed yet.";
    return;
  }
  if (outcome === "denied_no_execution") {
    executionOutcomeEl.textContent = "Approval denied. No booking was made.";
    return;
  }
  if (outcome === "blocked_no_execution") {
    executionOutcomeEl.textContent = "Blocked by policy. No booking was made.";
    openBlockedModal(data.route_reason || "Blocked by policy.");
    return;
  }
  executionOutcomeEl.textContent = "No execution performed.";
}

function openBlockedModal(reason) {
  blockedReasonEl.textContent = reason || "Blocked by policy.";
  blockedModalEl.classList.add("open");
}

function closeBlockedModal() {
  blockedModalEl.classList.remove("open");
}

function openItineraryModal(itinerary, route) {
  itineraryRouteNoteEl.textContent =
    route === "approved"
      ? "Booking executed on the approved path (directly or after approval gate)."
      : "Booking executed by selected route.";

  itineraryDestinationEl.textContent = itinerary.destination ?? "-";
  itineraryMonthEl.textContent = itinerary.month ?? "-";
  itineraryTravelersEl.textContent = `${itinerary.travelers ?? "-"}`;

  itineraryBookedItemsEl.innerHTML = "";
  const items = [
    { label: "Flight", value: itinerary.flight },
    { label: "Hotel", value: itinerary.hotel },
    { label: "Insurance", value: itinerary.insurance },
    { label: "Total", value: itinerary.total },
  ];

  items.forEach(({ label, value }) => {
    const li = document.createElement("li");
    if (value == null) {
      li.textContent = `${label}: not booked`;
    } else {
      li.textContent = `${label}: ${value}`;
    }
    itineraryBookedItemsEl.appendChild(li);
  });

  itineraryModalEl.classList.add("open");
}

function closeItineraryModal() {
  itineraryModalEl.classList.remove("open");
}

function openApprovalModal(payload, context = null) {
  pendingApprovalPayload = payload;

  const ctx = context || {};
  const reason = ctx.reason || "This run reached an approval gate before side effects.";
  approvalReasonEl.textContent = reason;

  approvalBudgetEl.textContent = ctx.budget != null ? `${ctx.budget}` : "not provided";
  approvalLimitsEl.textContent = `approval > ${ctx.approval_limit ?? "-"}, block > ${ctx.blocked_limit ?? "-"}`;
  approvalEstimateEl.textContent = ctx.estimated_total ? `${ctx.estimated_total}` : "not estimated";

  approvalWillRunEl.innerHTML = "";
  const willRun = Array.isArray(ctx.will_run_blocks) ? ctx.will_run_blocks : [];
  if (willRun.length === 0) {
    const li = document.createElement("li");
    li.textContent = "No additional execution blocks are configured after approval.";
    approvalWillRunEl.appendChild(li);
  } else {
    willRun.forEach((blockId) => {
      const li = document.createElement("li");
      li.textContent = labelFor(blockId);
      approvalWillRunEl.appendChild(li);
    });
  }

  approvalModalEl.classList.add("open");
}

function closeApprovalModal() {
  approvalModalEl.classList.remove("open");
}

async function runSimulation(approvalDecisionOverride = null, options = {}) {
  const preserveProgress = options.preserveProgress === true;
  preserveProgressForRun = preserveProgress;
  closeActiveSocket();
  closeItineraryModal();
  closeBlockedModal();
  runBtn.disabled = true;
  runBtn.textContent = "Running live...";

  const payload = {
    prompt: promptEl.value,
    strategy: strategyEl.value,
    blocks: selectedBlocks(),
    approval_limit: toOptionalInt(approvalLimitEl.value),
    blocked_limit: toOptionalInt(blockedLimitEl.value),
    flight_quote: toOptionalInt(flightQuoteEl.value),
    hotel_quote: toOptionalInt(hotelQuoteEl.value),
    insurance_quote: toOptionalInt(insuranceQuoteEl.value),
    approval_decision: approvalDecisionOverride || approvalDecisionEl.value || null,
  };

  const blockOrder = payload.blocks;
  if (!preserveProgress) {
    liveServiceResponses = [];
    serviceResponsesEl.innerHTML = "";
    clearNodeResponseLabels();
    executionState.ran = [];
    executionState.current = null;
    executionState.pending = [...blockOrder];
  } else {
    executionState.current = null;
    executionState.pending = blockOrder.filter((b) => !executionState.ran.includes(b));
  }
  updateStatusPanel();
  applyNodeColors();

  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws/simulate`;
  const socket = new WebSocket(wsUrl);
  activeSocket = socket;

  socket.onopen = () => {
    socket.send(JSON.stringify(payload));
  };

  socket.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);

    if (msg.type === "run_started") {
      routePill.textContent = `route: ${msg.route}`;
      return;
    }

    if (msg.type === "step") {
      const blockId = msg.block;
      if (!executionState.ran.includes(blockId)) {
        executionState.ran.push(blockId);
      }
      executionState.current = blockId;
      executionState.pending = blockOrder.filter((b) => !executionState.ran.includes(b));
      updateStatusPanel();
      applyNodeColors();
      if (msg.block_result) {
        upsertLiveServiceResponse(msg.block_result);
      }
      return;
    }

    if (msg.type === "awaiting_approval") {
      runBtn.disabled = false;
      runBtn.textContent = "Run Simulation";
      executionState.current = "approval_gate";
      if (!executionState.ran.includes("approval_gate")) {
        executionState.ran.push("approval_gate");
      }
      executionState.pending = blockOrder.filter((b) => !executionState.ran.includes(b));
      updateStatusPanel();
      applyNodeColors();
      const approvalResults = Array.isArray(msg.block_results) ? msg.block_results : [];
      approvalResults.forEach((item) => upsertLiveServiceResponse(item));
      openApprovalModal(payload, msg.approval_context || null);
      return;
    }

    if (msg.type === "finalizing") {
      runBtn.disabled = true;
      runBtn.textContent = "Finalizing summary...";
      return;
    }

    if (msg.type === "result") {
      const data = msg.payload;
      applySimulationResult(data);
      executionState.current = null;
      const visited = extractVisitedBlocks(data.events);
      if (preserveProgressForRun) {
        executionState.ran = [...new Set([...executionState.ran, ...visited])];
      } else {
        executionState.ran = [...new Set(visited)];
      }
      executionState.pending = blockOrder.filter((b) => !executionState.ran.includes(b));
      updateStatusPanel();
      applyNodeColors();
      runBtn.disabled = false;
      runBtn.textContent = "Run Simulation";
      preserveProgressForRun = false;
      return;
    }

    if (msg.type === "error") {
      eventsEl.innerHTML = `<div class="event"><strong>error</strong><div>${msg.message}</div></div>`;
      runBtn.disabled = false;
      runBtn.textContent = "Run Simulation";
      executionState.current = null;
      updateStatusPanel();
      applyNodeColors();
    }
  };

  socket.onerror = () => {
    eventsEl.innerHTML = `<div class="event"><strong>error</strong><div>WebSocket connection failed.</div></div>`;
    runBtn.disabled = false;
    runBtn.textContent = "Run Simulation";
    executionState.current = null;
    updateStatusPanel();
    applyNodeColors();
  };

  socket.onclose = () => {
    if (activeSocket === socket) {
      activeSocket = null;
    }
    runBtn.disabled = false;
    runBtn.textContent = "Run Simulation";
    preserveProgressForRun = false;
  };
}

function render() {
  renderPalette();
  canvasEl.innerHTML = "";
  renderGuides();
  renderPlacedNodes();
  applyNodeColors();
}

function setApprovalDecisionAndRun(decision) {
  closeApprovalModal();
  approvalDecisionEl.value = "";
  pendingApprovalPayload = null;
  runSimulation(decision, { preserveProgress: true });
}

approveBtn.addEventListener("click", () => setApprovalDecisionAndRun("approve"));
denyBtn.addEventListener("click", () => setApprovalDecisionAndRun("deny"));
closeItineraryBtn.addEventListener("click", closeItineraryModal);
closeBlockedBtn.addEventListener("click", closeBlockedModal);

itineraryModalEl.addEventListener("click", (event) => {
  if (event.target === itineraryModalEl) {
    closeItineraryModal();
  }
});

blockedModalEl.addEventListener("click", (event) => {
  if (event.target === blockedModalEl) {
    closeBlockedModal();
  }
});

strategyEl.addEventListener("change", resetCanvas);
resetBlocksBtn.addEventListener("click", resetCanvas);
runBtn.addEventListener("click", () => runSimulation());

setupDropTargets();
resetCanvas();
prefillQuoteOverridesFromService();

promptEl.addEventListener("change", () => prefillQuoteOverridesFromService());
approvalLimitEl.addEventListener("change", () => prefillQuoteOverridesFromService());
blockedLimitEl.addEventListener("change", () => prefillQuoteOverridesFromService());
