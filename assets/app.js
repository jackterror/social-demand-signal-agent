const state = { data: null };

const el = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {"Content-Type": "application/json"}, ...options});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
  return payload;
}

function badge(text, tone = "") {
  return `<span class="badge ${escapeHtml(tone)}">${escapeHtml(text)}</span>`;
}

function renderSummary(summary) {
  for (const key of ["total", "reviewable", "drafted", "approved", "escalated"]) {
    el(`metric-${key}`).textContent = summary[key] ?? 0;
  }
}

function addAction(container, label, className, handler) {
  const button = document.createElement("button");
  button.className = `button ${className}`;
  button.textContent = label;
  button.addEventListener("click", handler);
  container.appendChild(button);
}

async function review(signal, decision, body) {
  await api("/api/review", {method: "POST", body: JSON.stringify({signal_id: signal.id, decision, final_body: body})});
  await loadState();
}

async function recordEvent(signal, eventType) {
  await api("/api/event", {method: "POST", body: JSON.stringify({signal_id: signal.id, event_type: eventType, data_label: "reviewer_entered"})});
  await loadState();
}

function renderSignal(signal) {
  const fragment = el("signal-template").content.cloneNode(true);
  const article = fragment.querySelector(".signal");
  const badges = fragment.querySelector(".badges");
  badges.innerHTML = badge(signal.platform) + badge(signal.route, signal.route) + badge(signal.agent_status);
  const link = fragment.querySelector(".source-link");
  if (signal.source_url) link.href = signal.source_url;
  else link.classList.add("hidden");
  fragment.querySelector(".signal-text").textContent = signal.text;
  fragment.querySelector(".author").textContent = `@${signal.author}`;
  fragment.querySelector(".family").textContent = signal.message_family;
  fragment.querySelector(".score").textContent = `score ${Math.round(signal.relevance_score * 100)}%`;
  fragment.querySelector(".data-label").textContent = signal.data_label;

  const actions = fragment.querySelector(".actions");
  const decisionNote = fragment.querySelector(".decision-note");
  if (signal.decision) decisionNote.textContent = `Reviewer decision: ${signal.decision}`;

  if (signal.route === "review" && signal.drafts && signal.drafts[signal.assigned_variant]) {
    const panel = fragment.querySelector(".draft-panel");
    panel.classList.remove("hidden");
    const assigned = signal.drafts[signal.assigned_variant];
    const alternateKey = signal.assigned_variant === "a" ? "b" : "a";
    const alternate = signal.drafts[alternateKey];
    fragment.querySelector(".assigned-variant").textContent = signal.assigned_variant;
    const textarea = fragment.querySelector(".draft-body");
    textarea.value = signal.final_body || assigned.body;
    fragment.querySelector(".alternate-copy").textContent = alternate ? `Variant ${alternateKey.toUpperCase()}: ${alternate.body}` : "No alternate draft.";
    fragment.querySelector(".rationale").textContent = assigned.rationale;
    addAction(actions, "Approve assigned", "approve", () => review(signal, "approved", textarea.value));
    addAction(actions, "Reject", "reject", () => review(signal, "rejected", ""));
    addAction(actions, "Escalate", "escalate", () => review(signal, "escalated", ""));
  } else if (signal.route === "escalate") {
    addAction(actions, "Confirm escalation", "escalate", () => review(signal, "escalated", ""));
  }

  if (signal.decision === "approved") {
    addAction(actions, "Posted", "event", () => recordEvent(signal, "posted"));
    addAction(actions, state.data.profile.primary_event, "event", () => recordEvent(signal, state.data.profile.primary_event));
    addAction(actions, state.data.profile.guardrail_event, "reject", () => recordEvent(signal, state.data.profile.guardrail_event));
  }
  return article;
}

function renderQueue(signals) {
  const queue = el("queue");
  queue.replaceChildren();
  if (!signals.length) {
    queue.innerHTML = '<div class="empty">No signals in the current workspace.</div>';
    return;
  }
  for (const signal of signals) queue.appendChild(renderSignal(signal));
}

function renderExperiments(experiments) {
  const body = el("experiment-body");
  if (!experiments.length) {
    body.innerHTML = '<tr><td colspan="9">No observed exposures yet.</td></tr>';
    return;
  }
  body.innerHTML = experiments.map((item) => {
    const a = item.variants.a || {exposures: 0, conversion_rate: 0};
    const b = item.variants.b || {exposures: 0, conversion_rate: 0};
    return `<tr><td>${escapeHtml(item.message_family)}</td><td>${escapeHtml(item.platform)}</td><td>${escapeHtml(item.status)}</td><td>${a.exposures}</td><td>${(a.conversion_rate * 100).toFixed(1)}%</td><td>${b.exposures}</td><td>${(b.conversion_rate * 100).toFixed(1)}%</td><td>${escapeHtml(item.directional_leader)}</td><td>${escapeHtml(item.winner || "none")}</td></tr>`;
  }).join("");
}

async function loadState() {
  try {
    el("error-banner").classList.add("hidden");
    state.data = await api("/api/state");
    el("company-name").textContent = `${state.data.profile.company} Review`;
    el("primary-event").textContent = `Goal: ${state.data.profile.primary_event}`;
    el("guardrail-event").textContent = `Guardrail: ${state.data.profile.guardrail_event}`;
    renderSummary(state.data.summary);
    renderQueue(state.data.signals);
    renderExperiments(state.data.experiments);
  } catch (error) {
    el("error-banner").textContent = error.message;
    el("error-banner").classList.remove("hidden");
  }
}

for (const tab of document.querySelectorAll(".tab")) {
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((item) => item.classList.toggle("active", item === tab));
    document.querySelectorAll(".view").forEach((view) => view.classList.remove("active"));
    el(`${tab.dataset.view}-view`).classList.add("active");
  });
}

el("refresh-button").addEventListener("click", loadState);
el("collect-button").addEventListener("click", async () => {
  const status = el("control-status");
  status.textContent = "Collecting";
  try {
    const result = await api("/api/collect", {method: "POST", body: JSON.stringify({provider: el("provider-select").value, source: el("source-input").value})});
    status.textContent = `${result.stored} signal(s) stored`;
    await loadState();
  } catch (error) {
    status.textContent = error.message;
  }
});
el("export-button").addEventListener("click", async () => {
  const status = el("control-status");
  try {
    const result = await api("/api/export", {method: "POST", body: "{}"});
    status.textContent = `${result.exported} signal(s) exported`;
  } catch (error) {
    status.textContent = error.message;
  }
});
loadState();
