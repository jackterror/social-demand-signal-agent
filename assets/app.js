const state = {setup: null, data: null, families: []};
const PLATFORMS = ["reddit", "twitter", "tiktok", "youtube", "facebook", "linkedin", "instagram", "threads"];
const el = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value ?? "").replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);

async function api(path, options = {}) {
  const mutation = options.method && options.method !== "GET";
  const headers = mutation ? {"Content-Type": "application/json", "X-SDSA-Request": "local"} : {};
  const response = await fetch(path, {...options, headers: {...headers, ...(options.headers || {})}});
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || `Request failed: ${response.status}`);
  return payload;
}

const lines = (id) => el(id).value.split("\n").map((item) => item.trim()).filter(Boolean);
const value = (id) => el(id).value.trim();
const numberValue = (id) => Number.parseInt(el(id).value, 10) || 0;
const cleanValue = (input) => String(input || "").toLowerCase().startsWith("replace with") ? "" : String(input || "");
const show = (node, visible) => node.classList.toggle("hidden", !visible);

function switchView(name) {
  document.querySelectorAll(".tab").forEach((tab) => tab.classList.toggle("active", tab.dataset.view === name));
  document.querySelectorAll(".view").forEach((view) => view.classList.toggle("active", view.id === `${name}-view`));
  if (name !== "setup") loadState();
}

function renderPlatforms(selected = []) {
  el("platform-options").innerHTML = PLATFORMS.map((platform) => `<label class="check-option"><input type="checkbox" value="${platform}" ${selected.includes(platform) ? "checked" : ""}><span>${platform}</span></label>`).join("");
}

function addFamily(family = {}) {
  const fragment = el("family-template").content.cloneNode(true);
  const row = fragment.querySelector(".family-row");
  row.querySelector('[data-family-field="name"]').value = cleanValue(family.name);
  row.querySelector('[data-family-field="signals"]').value = (family.signals || []).join("\n");
  row.querySelector('[data-family-field="hypothesis_a"]').value = cleanValue(family.hypothesis_a);
  row.querySelector('[data-family-field="hypothesis_b"]').value = cleanValue(family.hypothesis_b);
  row.querySelector(".remove-family").addEventListener("click", () => {
    row.remove();
    if (!el("family-list").children.length) addFamily();
    updatePreview();
  });
  row.querySelectorAll("input, textarea").forEach((input) => input.addEventListener("input", updatePreview));
  el("family-list").appendChild(row);
}

function populateForm(profile) {
  const company = profile.company || {};
  const audience = profile.audience || {};
  const offer = profile.offer || {};
  const voice = profile.voice || {};
  const claims = profile.claims || {};
  const safety = profile.safety || {};
  const listening = profile.listening || {};
  const experiment = profile.experiment || {};
  const fields = {
    "company-input": company.name, "industry-input": company.industry, "product-input": company.product,
    "description-input": company.description, "website-input": company.website, "audience-input": audience.description,
    "pain-input": (audience.pain_points || []).join("\n"), "intent-input": (audience.intent_signals || []).join("\n"),
    "queries-input": (listening.queries || []).join("\n"), "freshness-input": listening.freshness_minutes || 60,
    "max-items-input": listening.max_items || 50, "offer-input": offer.summary, "cta-input": offer.cta_url,
    "voice-input": (voice.attributes || []).join("\n"), "disclosure-input": profile.disclosure,
    "approved-input": (claims.approved || []).join("\n"), "forbidden-input": (claims.forbidden || []).join("\n"),
    "exclusions-input": (safety.exclusions || []).join("\n"), "escalations-input": (safety.escalation_terms || []).join("\n"),
    "frequency-input": safety.max_responses_per_author_24h || 1, "primary-input": experiment.primary_event || "qualified_action",
    "guardrail-input": experiment.guardrail_event || "negative_feedback", "sample-input": experiment.minimum_sample_size || 30,
  };
  for (const [id, content] of Object.entries(fields)) el(id).value = cleanValue(content);
  renderPlatforms(listening.platforms || []);
  el("family-list").replaceChildren();
  for (const family of profile.response_families || [{}]) addFamily(family);
  updatePreview();
}

function collectFamilies() {
  return [...document.querySelectorAll(".family-row")].map((row) => ({
    name: row.querySelector('[data-family-field="name"]').value.trim(),
    signals: row.querySelector('[data-family-field="signals"]').value.split("\n").map((item) => item.trim()).filter(Boolean),
    hypothesis_a: row.querySelector('[data-family-field="hypothesis_a"]').value.trim(),
    hypothesis_b: row.querySelector('[data-family-field="hypothesis_b"]').value.trim(),
  }));
}

function profileFromForm() {
  return {
    schema_version: 2, profile_status: "setup",
    company: {name: value("company-input"), industry: value("industry-input"), product: value("product-input"), description: value("description-input"), website: value("website-input")},
    audience: {description: value("audience-input"), pain_points: lines("pain-input"), intent_signals: lines("intent-input")},
    offer: {summary: value("offer-input"), cta_url: value("cta-input")},
    voice: {attributes: lines("voice-input")}, disclosure: value("disclosure-input"),
    claims: {approved: lines("approved-input"), forbidden: lines("forbidden-input")},
    safety: {exclusions: lines("exclusions-input"), escalation_terms: lines("escalations-input"), max_responses_per_author_24h: numberValue("frequency-input")},
    listening: {queries: lines("queries-input"), platforms: [...document.querySelectorAll('#platform-options input:checked')].map((input) => input.value), freshness_minutes: numberValue("freshness-input"), max_items: numberValue("max-items-input")},
    response_families: collectFamilies(),
    experiment: {primary_event: value("primary-input"), guardrail_event: value("guardrail-input"), minimum_sample_size: numberValue("sample-input")},
  };
}

function clientErrors(profile) {
  const errors = [];
  const required = [
    [profile.company.name, "Company name"], [profile.company.industry, "Industry"], [profile.company.product, "Product or service"],
    [profile.company.description, "Company description"], [profile.company.website, "Company website"], [profile.audience.description, "Target audience"],
    [profile.offer.summary, "Offer"], [profile.offer.cta_url, "CTA destination"], [profile.disclosure, "Affiliation disclosure"],
  ];
  for (const [content, label] of required) if (!content) errors.push(`${label} is required.`);
  const lists = [[profile.audience.pain_points, "Pain points"], [profile.audience.intent_signals, "Intent signals"], [profile.listening.queries, "Search queries"], [profile.listening.platforms, "Platforms"], [profile.voice.attributes, "Voice attributes"], [profile.claims.approved, "Approved claims"], [profile.claims.forbidden, "Forbidden claims"], [profile.safety.exclusions, "Exclusions"], [profile.safety.escalation_terms, "Escalation terms"]];
  for (const [items, label] of lists) if (!items.length) errors.push(`${label} needs at least one entry.`);
  for (const [url, label] of [[profile.company.website, "Company website"], [profile.offer.cta_url, "CTA destination"]]) if (url && !/^https?:\/\//.test(url)) errors.push(`${label} must start with http:// or https://.`);
  if (!profile.response_families.length || profile.response_families.some((family) => !family.name || !family.signals.length || !family.hypothesis_a || !family.hypothesis_b)) errors.push("Every message family needs a name, routing phrase, and two hypotheses.");
  if (profile.experiment.primary_event === profile.experiment.guardrail_event) errors.push("Conversion and guardrail events must be different.");
  return errors;
}

function renderValidation(errors) {
  const summary = el("setup-errors");
  if (!errors.length) { show(summary, false); return; }
  summary.innerHTML = `<strong>Setup needs attention</strong><ul>${errors.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
  show(summary, true);
  summary.focus();
}

function updatePreview() {
  const profile = profileFromForm();
  const preview = [
    ["Company", profile.company.name || "Not set"], ["Audience", profile.audience.description || "Not set"],
    ["Queries", profile.listening.queries.length], ["Platforms", profile.listening.platforms.join(", ") || "Not set"],
    ["Freshness", `${profile.listening.freshness_minutes || 0} minutes`], ["Excluded contexts", profile.safety.exclusions.length],
  ];
  el("setup-preview").innerHTML = preview.map(([label, content]) => `<div><span>${escapeHtml(label)}</span><strong>${escapeHtml(content)}</strong></div>`).join("");
}

function statusTone(node, ready, label) {
  node.textContent = label;
  node.classList.toggle("ready", ready);
  node.classList.toggle("not-ready", !ready);
}

function updateCollectAvailability() {
  if (!state.setup) return;
  const provider = el("provider-select").value;
  const readiness = state.setup.readiness;
  const demo = readiness.profile_status === "demo";
  const enabled = provider === "socialcrawl" ? readiness.ready_to_listen : provider === "json" ? readiness.profile_ready : demo;
  el("collect-button").disabled = !enabled;
  show(document.querySelector(".source-field"), provider === "json");
}

function renderSetup(payload, populate = true) {
  state.setup = payload;
  const readiness = payload.readiness;
  const demo = readiness.profile_status === "demo";
  statusTone(el("profile-readiness"), readiness.profile_ready || demo, demo ? "Demo loaded" : readiness.profile_ready ? "Ready" : "Needs setup");
  statusTone(el("provider-readiness"), readiness.provider_ready, readiness.provider_ready ? "Configured" : "Missing key");
  statusTone(el("listening-readiness"), readiness.ready_to_listen, readiness.ready_to_listen ? "Ready" : "Blocked");
  const provider = payload.provider;
  el("provider-state").textContent = provider.connection_state.replace("_", " ");
  el("provider-state").className = `status-text ${provider.connection_state === "connected" ? "ready" : provider.connection_state === "failed" ? "not-ready" : ""}`;
  el("get-key-link").href = provider.signup_url;
  el("provider-docs-link").href = provider.docs_url;
  el("remove-key-button").disabled = !provider.credential_configured || provider.credential_source === "process";
  el("test-key-button").disabled = !provider.credential_configured;
  const completed = readiness.profile_ready ? 100 : Math.max(5, 100 - (readiness.errors.length * 4) - (readiness.placeholder_count * 3));
  el("setup-progress").value = Math.max(0, Math.min(100, completed));
  el("setup-progress-label").textContent = demo ? "Fixture demo profile" : readiness.profile_ready ? "Company profile complete" : `${readiness.errors.length + readiness.placeholder_count} setup item(s) remain`;
  const canOpenWorkspace = demo || readiness.profile_ready;
  document.querySelectorAll('.tab[data-view="queue"], .tab[data-view="experiments"]').forEach((tab) => { tab.disabled = !canOpenWorkspace; });
  el("provider-select").value = demo ? "fixture" : "socialcrawl";
  updateCollectAvailability();
  el("company-name").textContent = cleanValue(payload.profile.company?.name) || "Set up your listening";
  if (populate) populateForm(payload.profile);
}

async function loadSetup(populate = true) {
  try {
    const payload = await api("/api/setup");
    renderSetup(payload, populate);
    if (payload.readiness.profile_status === "setup") switchView("setup");
    return payload;
  } catch (error) {
    showError(error.message);
    return null;
  }
}

async function saveSetup(complete) {
  const profile = profileFromForm();
  const errors = complete ? clientErrors(profile) : [];
  renderValidation(errors);
  if (errors.length) return;
  const message = el("setup-message");
  message.textContent = complete ? "Validating setup" : "Saving progress";
  try {
    const result = await api("/api/setup/save", {method: "POST", body: JSON.stringify({profile, complete})});
    renderSetup(result.setup, false);
    message.textContent = complete ? "Setup complete. Live listening is available when the provider is configured." : "Progress saved.";
  } catch (error) {
    renderValidation([error.message]);
    message.textContent = "Setup was not saved.";
  }
}

function showError(message) {
  el("error-banner").textContent = message;
  show(el("error-banner"), true);
}

function clearError() { show(el("error-banner"), false); }
function badge(text, tone = "") { return `<span class="badge ${escapeHtml(tone)}">${escapeHtml(text)}</span>`; }
function renderSummary(summary) { for (const key of ["total", "reviewable", "drafted", "approved", "escalated"]) el(`metric-${key}`).textContent = summary[key] ?? 0; }
function addAction(container, label, className, handler) { const button = document.createElement("button"); button.className = `button ${className}`; button.textContent = label; button.addEventListener("click", handler); container.appendChild(button); }
async function review(signal, decision, body) { await api("/api/review", {method: "POST", body: JSON.stringify({signal_id: signal.id, decision, final_body: body})}); await loadState(); }
async function recordEvent(signal, eventType) { await api("/api/event", {method: "POST", body: JSON.stringify({signal_id: signal.id, event_type: eventType, data_label: "reviewer_entered"})}); await loadState(); }

function renderSignal(signal) {
  const fragment = el("signal-template").content.cloneNode(true);
  const article = fragment.querySelector(".signal");
  fragment.querySelector(".badges").innerHTML = badge(signal.platform) + badge(signal.route, signal.route) + badge(signal.agent_status);
  const link = fragment.querySelector(".source-link");
  if (signal.source_url) link.href = signal.source_url; else link.classList.add("hidden");
  fragment.querySelector(".signal-text").textContent = signal.text;
  fragment.querySelector(".author").textContent = `@${signal.author}`;
  fragment.querySelector(".family").textContent = signal.message_family;
  fragment.querySelector(".score").textContent = `score ${Math.round(signal.relevance_score * 100)}%`;
  fragment.querySelector(".data-label").textContent = signal.data_label;
  const actions = fragment.querySelector(".actions");
  if (signal.decision) fragment.querySelector(".decision-note").textContent = `Reviewer decision: ${signal.decision}`;
  if (signal.route === "review" && signal.drafts && signal.drafts[signal.assigned_variant]) {
    const panel = fragment.querySelector(".draft-panel"); panel.classList.remove("hidden");
    const assigned = signal.drafts[signal.assigned_variant]; const alternateKey = signal.assigned_variant === "a" ? "b" : "a"; const alternate = signal.drafts[alternateKey];
    fragment.querySelector(".assigned-variant").textContent = signal.assigned_variant;
    const textarea = fragment.querySelector(".draft-body"); textarea.value = signal.final_body || assigned.body;
    fragment.querySelector(".alternate-copy").textContent = alternate ? `Variant ${alternateKey.toUpperCase()}: ${alternate.body}` : "No alternate draft.";
    fragment.querySelector(".rationale").textContent = assigned.rationale;
    addAction(actions, "Approve assigned", "approve", () => review(signal, "approved", textarea.value));
    addAction(actions, "Reject", "reject", () => review(signal, "rejected", ""));
    addAction(actions, "Escalate", "escalate", () => review(signal, "escalated", ""));
  } else if (signal.route === "escalate") addAction(actions, "Confirm escalation", "escalate", () => review(signal, "escalated", ""));
  if (signal.decision === "approved") {
    addAction(actions, "Posted", "event", () => recordEvent(signal, "posted"));
    addAction(actions, state.data.profile.primary_event, "event", () => recordEvent(signal, state.data.profile.primary_event));
    addAction(actions, state.data.profile.guardrail_event, "reject", () => recordEvent(signal, state.data.profile.guardrail_event));
  }
  return article;
}

function renderQueue(signals) { const queue = el("queue"); queue.replaceChildren(); if (!signals.length) { queue.innerHTML = '<div class="empty">No signals in the current workspace.</div>'; return; } for (const signal of signals) queue.appendChild(renderSignal(signal)); }
function renderExperiments(experiments) {
  const body = el("experiment-body");
  if (!experiments.length) { body.innerHTML = '<tr><td colspan="9">No observed exposures yet.</td></tr>'; return; }
  body.innerHTML = experiments.map((item) => { const a = item.variants.a || {exposures: 0, conversion_rate: 0}; const b = item.variants.b || {exposures: 0, conversion_rate: 0}; return `<tr><td>${escapeHtml(item.message_family)}</td><td>${escapeHtml(item.platform)}</td><td>${escapeHtml(item.status)}</td><td>${a.exposures}</td><td>${(a.conversion_rate * 100).toFixed(1)}%</td><td>${b.exposures}</td><td>${(b.conversion_rate * 100).toFixed(1)}%</td><td>${escapeHtml(item.directional_leader)}</td><td>${escapeHtml(item.winner || "none")}</td></tr>`; }).join("");
}

async function loadState() {
  clearError();
  try {
    state.data = await api("/api/state");
    el("company-name").textContent = `${state.data.profile.company} Listening`;
    el("primary-event").textContent = `Goal: ${state.data.profile.primary_event}`;
    el("guardrail-event").textContent = `Guardrail: ${state.data.profile.guardrail_event}`;
    renderSummary(state.data.summary); renderQueue(state.data.signals); renderExperiments(state.data.experiments);
  } catch (error) { showError(error.message); }
}

async function credentialAction(action) {
  const message = el("provider-message");
  try {
    const apiKey = action === "save" ? value("api-key-input") : "";
    const result = await api("/api/credential", {method: "POST", body: JSON.stringify({action, api_key: apiKey})});
    el("api-key-input").value = ""; message.textContent = action === "save" ? "Credential saved locally." : "Saved credential removed.";
    await loadSetup(false); return result;
  } catch (error) { message.textContent = error.message; return null; }
}

document.querySelectorAll(".tab").forEach((tab) => tab.addEventListener("click", () => { if (!tab.disabled) switchView(tab.dataset.view); }));
el("setup-form").addEventListener("input", updatePreview);
el("setup-form").addEventListener("submit", (event) => { event.preventDefault(); saveSetup(true); });
el("save-progress-button").addEventListener("click", () => saveSetup(false));
el("add-family-button").addEventListener("click", () => addFamily());
el("save-key-button").addEventListener("click", () => credentialAction("save"));
el("remove-key-button").addEventListener("click", () => credentialAction("remove"));
el("test-key-button").addEventListener("click", async () => { const message = el("provider-message"); message.textContent = "Testing connection"; try { const result = await api("/api/provider/test", {method: "POST", body: "{}"}); message.textContent = result.message; await loadSetup(false); } catch (error) { message.textContent = error.message; await loadSetup(false); } });
el("export-profile-button").addEventListener("click", () => { const profile = profileFromForm(); const blob = new Blob([JSON.stringify(profile, null, 2) + "\n"], {type: "application/json"}); const link = document.createElement("a"); link.href = URL.createObjectURL(blob); link.download = "social-listening-company-profile.json"; link.click(); URL.revokeObjectURL(link.href); });
el("import-profile-button").addEventListener("click", () => el("import-profile-file").click());
el("import-profile-file").addEventListener("change", async () => { const file = el("import-profile-file").files[0]; if (!file) return; try { const profile = JSON.parse(await file.text()); populateForm(profile); await saveSetup(false); } catch (error) { renderValidation([`Profile import failed: ${error.message}`]); } finally { el("import-profile-file").value = ""; } });
el("load-demo-button").addEventListener("click", async () => { try { await api("/api/reset/demo", {method: "POST", body: "{}"}); await loadSetup(); await loadState(); switchView("queue"); } catch (error) { showError(error.message); } });
el("reset-setup-button").addEventListener("click", async () => { if (!window.confirm("Reset the company setup? A local profile backup will be kept.")) return; try { await api("/api/reset/setup", {method: "POST", body: "{}"}); await loadSetup(); switchView("setup"); } catch (error) { showError(error.message); } });
el("refresh-button").addEventListener("click", loadState);
el("provider-select").addEventListener("change", updateCollectAvailability);
el("collect-button").addEventListener("click", async () => { const status = el("control-status"); status.textContent = "Collecting"; try { const result = await api("/api/collect", {method: "POST", body: JSON.stringify({provider: el("provider-select").value, source: el("source-input").value})}); status.textContent = `${result.stored} signal(s) stored`; await loadState(); } catch (error) { status.textContent = error.message; } });
el("export-button").addEventListener("click", async () => { const status = el("control-status"); try { const result = await api("/api/export", {method: "POST", body: "{}"}); status.textContent = `${result.exported} signal(s) exported`; } catch (error) { status.textContent = error.message; } });
loadSetup();
