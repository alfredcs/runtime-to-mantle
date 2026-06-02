/* ============================================================================
   Mantle Studio — frontend controller.
   Loads /api/config, drives navigation, and runs the three live consoles by
   streaming NDJSON from the FastAPI backend into a shared Wire Inspector.
   No framework, no build step — works offline for live demos.
   ============================================================================ */
"use strict";

const $  = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const esc = (s) => String(s).replace(/[&<>"]/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

let CFG = null;                          // /api/config payload
const SEL = { triage: null, concierge: null, analyst: null };  // chosen model per console
const ACCENT = { chat_completions: "#3b82f6", responses: "#a855f7", messages: "#f0883e" };

/* ------------------------------------------------------------ tiny helpers */
function toast(msg) {
  const t = $("#toast");
  t.textContent = msg; t.classList.add("show");
  clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 2200);
}
const fmtUSD = (n) => n < 0.01 ? `$${n.toFixed(5)}` : `$${n.toFixed(4)}`;
const fmtMs  = (n) => n >= 1000 ? `${(n / 1000).toFixed(2)}s` : `${n}ms`;

/* markdown-lite: **bold**, `code`, ## head, > quote, - list, paragraphs */
function mdLite(src) {
  const lines = String(src).split("\n");
  let html = "", list = false;
  const inline = (t) => esc(t)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
  for (let raw of lines) {
    const l = raw.trimEnd();
    if (/^###?\s/.test(l)) { if (list) { html += "</ul>"; list = false; }
      const lvl = l.startsWith("###") ? 3 : 2;
      html += `<h${lvl}>${inline(l.replace(/^#+\s/, ""))}</h${lvl}>`; }
    else if (/^>\s?/.test(l)) { if (list) { html += "</ul>"; list = false; }
      html += `<blockquote>${inline(l.replace(/^>\s?/, ""))}</blockquote>`; }
    else if (/^[-*]\s/.test(l)) { if (!list) { html += "<ul>"; list = true; }
      html += `<li>${inline(l.replace(/^[-*]\s/, ""))}</li>`; }
    else if (l === "") { if (list) { html += "</ul>"; list = false; } }
    else { if (list) { html += "</ul>"; list = false; } html += `<p>${inline(l)}</p>`; }
  }
  if (list) html += "</ul>";
  return html;
}

/* JSON pretty-print + syntax highlight */
function hlJSON(obj) {
  const json = typeof obj === "string" ? obj : JSON.stringify(obj, null, 2);
  return esc(json)
    .replace(/&quot;(\w[\w\-.]*)&quot;(\s*:)/g, '<span class="j-key">&quot;$1&quot;</span>$2')
    .replace(/: &quot;(.*?)&quot;/g, ': <span class="j-str">&quot;$1&quot;</span>')
    .replace(/: (-?\d+\.?\d*)/g, ': <span class="j-num">$1</span>')
    .replace(/: (true|false)/g, ': <span class="j-bool">$1</span>')
    .replace(/: null/g, ': <span class="j-null">null</span>');
}

/* ---------------------------------------------------------------- NDJSON */
async function streamNDJSON(url, payload, onEvent) {
  const res = await fetch(url, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    let nl;
    while ((nl = buf.indexOf("\n")) >= 0) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      if (line) onEvent(JSON.parse(line));
    }
  }
  if (buf.trim()) onEvent(JSON.parse(buf.trim()));
}

/* ============================================================== boot */
async function boot() {
  CFG = await (await fetch("/api/config")).json();

  // endpoint host + mode badge + stats
  const host = CFG.host_template.replace("{region}", CFG.default_region);
  $("#endpointHost").textContent = host;
  $("#diagramHost").textContent  = host;
  $("#statModels").textContent   = CFG.models.length;
  $("#statRegions").textContent  = CFG.regions.length;

  const badge = $("#modeBadge");
  badge.textContent = CFG.mode;
  badge.className = "mode-badge " + CFG.mode.toLowerCase();
  badge.title = CFG.mode === "LIVE"
    ? "Calling the real bedrock-mantle endpoint."
    : "Simulated responses (no AWS credentials). Set MANTLE_LIVE=1 + a Bearer token for LIVE.";

  // region select
  const rs = $("#regionSelect");
  rs.innerHTML = CFG.regions.map((r) => `<option ${r === CFG.default_region ? "selected" : ""}>${r}</option>`).join("");
  rs.onchange = () => {
    const h = CFG.host_template.replace("{region}", rs.value);
    $("#endpointHost").textContent = h; $("#diagramHost").textContent = h;
    toast(`Endpoint region → ${rs.value}`);
  };
  const region = () => rs.value;

  // default model per console: prefer the one that best showcases the surface
  const pick = (surface, flag) =>
    (flag && CFG.models.find((m) => m.surfaces.includes(surface) && m.flags.includes(flag)))
    || CFG.models.find((m) => m.surfaces.includes(surface));
  SEL.triage    = pick("chat_completions").id;
  SEL.concierge = pick("responses", "responses").id;   // flagship w/ server-side tools
  SEL.analyst   = pick("messages", "thinking").id;      // frontier reasoning w/ thinking

  buildNav(); buildSurfaceCards(); buildDiff();
  buildModelPills(); buildChips();
  buildEconomics(); buildValueView();

  wireTriage(region); wireConcierge(region); wireAnalyst(region); wireCompare(region);

  // hero CTA + surface-card jumps
  $$("[data-goto]").forEach((b) => b.onclick = () => go(b.dataset.goto));
}

/* ------------------------------------------------------------------ nav */
function go(view) {
  $$(".nav-item").forEach((n) => n.classList.toggle("active", n.dataset.view === view));
  $$(".view").forEach((v) => v.classList.toggle("active", v.id === `view-${view}`));
  $("#view").scrollTop = 0; window.scrollTo(0, 0);
}
function buildNav() { $$(".nav-item").forEach((n) => n.onclick = () => go(n.dataset.view)); }

/* -------------------------------------------------- overview surface cards */
function buildSurfaceCards() {
  const order = ["chat_completions", "responses", "messages"];
  $("#surfaceCards").innerHTML = order.map((k) => {
    const s = CFG.surfaces[k];
    const tags = [
      s.stateful ? `<span class="sc-tag stateful">stateful</span>`
                 : `<span class="sc-tag">stateless</span>`,
      s.mantle_only ? `<span class="sc-tag only">Mantle-only</span>` : "",
      `<span class="sc-tag">${s.spec}</span>`,
    ].join("");
    return `<div class="surface-card" style="--accent:${s.accent}" data-goto="${s.console.toLowerCase()}">
      <div class="sc-spec">Stage · ${s.console}</div>
      <h4>${s.name}</h4>
      <div class="sc-path">POST ${s.path}</div>
      <p>${s.best_for}</p>
      <div class="sc-tags">${tags}</div>
    </div>`;
  }).join("");
  $$("#surfaceCards .surface-card").forEach((c) => c.onclick = () => go(c.dataset.goto));
}

/* ----------------------------------------------- overview before/after diff */
function buildDiff() {
  const before =
`import boto3
client = boto3.client(
    "bedrock-runtime",
    region_name="us-east-1")

resp = client.converse(
  modelId="anthropic.claude-...",
  messages=[{"role":"user",
    "content":[{"text": msg}]}],
)
out = resp["output"]["message"]`;
  const after =
`from openai import OpenAI
client = OpenAI(
  base_url="https://bedrock-mantle."
    "us-east-1.api.aws/v1",
  api_key=os.environ["MANTLE_KEY"])

resp = client.chat.completions.create(
  model="openai.gpt-oss-120b",
  messages=[{"role":"user",
    "content": msg}],
)
out = resp.choices[0].message`;
  const mark = (code, terms) => {
    let h = esc(code);
    terms.forEach((t) => { h = h.replace(esc(t), `<span class="hl">${esc(t)}</span>`); });
    return h;
  };
  $("#codeBefore").innerHTML = mark(before, ['"bedrock-runtime"', "client.converse", '"output"']);
  $("#codeAfter").innerHTML  = mark(after, ['base_url=', "chat.completions.create", "choices[0]"]);
}

/* ----------------------------------------------------------- model pills */
function buildModelPills() {
  const render = (container, surface, selKey) => {
    const list = CFG.models.filter((m) => m.surfaces.includes(surface));
    container.innerHTML = list.map((m) => {
      const p = CFG.providers[m.provider] || { color: "#888" };
      const on = SEL[selKey] === m.id;
      return `<button class="mpill ${on ? "active" : ""}" data-id="${m.id}"
        style="--prov:${p.color}" title="${esc(m.blurb)} · in $${m.price_in}/M · out $${m.price_out}/M">
        <span class="pdot"></span>${esc(m.label)}
        <span class="pctx">${m.ctx}</span></button>`;
    }).join("");
    $$(".mpill", container).forEach((b) => b.onclick = () => {
      SEL[selKey] = b.dataset.id;
      $$(".mpill", container).forEach((x) => x.classList.toggle("active", x === b));
      if (selKey === "triage") buildEconomics();
    });
  };
  render($("#triageModels"),    "chat_completions", "triage");
  render($("#conciergeModels"), "responses",        "concierge");
  render($("#analystModels"),   "messages",         "analyst");
}

/* ----------------------------------------------------------- prompt chips */
function buildChips() {
  const fill = (el, arr, target) => {
    el.innerHTML = arr.map((p) => `<button class="chip">${esc(p.length > 64 ? p.slice(0, 61) + "…" : p)}</button>`).join("");
    $$(".chip", el).forEach((c, i) => c.onclick = () => { target.value = arr[i]; target.focus(); });
  };
  fill($("#triageChips"),    CFG.sample_prompts.triage,    $("#triageInput"));
  fill($("#conciergeChips"), CFG.sample_prompts.concierge, $("#conciergeInput"));
  $("#triageInput").value  = CFG.sample_prompts.triage[0];
  $("#analystInput").value = CFG.sample_prompts.analyst[0];
}

/* =====================================================================
   WIRE INSPECTOR — shared renderer driven by a per-console state object.
   state = {surface, wire, tools[], answerText, response, metrics, savings, tab}
   ===================================================================== */
function newWire(surface) {
  return { surface, wire: null, tools: [], answerText: "", response: null,
           metrics: null, savings: null, tab: "request" };
}

function renderWire(container, st) {
  const s = CFG.surfaces[st.surface];
  const accent = ACCENT[st.surface];
  if (!st.wire) {
    container.innerHTML = `<div class="wire-empty"><div class="we-ic">⌁</div>
      Send a request to inspect the exact HTTP call on the wire.</div>`;
    return;
  }
  const w = st.wire;
  const tab = (id, label) => `<button class="wire-tab ${st.tab === id ? "active" : ""}" data-tab="${id}">${label}</button>`;

  let body = "";
  if (st.tab === "request") {
    const hdrs = Object.entries(w.headers).map(([k, v]) =>
      `<div><span class="hdr-k">${esc(k)}</span>: <span class="hdr-v">${esc(v)}</span></div>`).join("");
    body = `<div class="wire-line"><span class="http-method" style="background:${accent}">POST</span>
        <span class="http-url">${esc(w.url)}</span></div>
      <div class="auth-pill">auth · ${esc(w.auth_style)}</div>
      <div class="wire-section">Headers</div>${hdrs}
      <div class="wire-section">Body</div><pre>${hlJSON(w.body)}</pre>`;
  } else if (st.tab === "curl") {
    body = `<pre>${esc(w.curl)}</pre>`;
  } else if (st.tab === "response") {
    body = st.response
      ? `<pre>${hlJSON(st.response)}</pre>`
      : `<div class="wire-empty">Awaiting response…</div>`;
  }

  // tool calls (responses surface)
  const toolsHtml = st.tools.length ? `<div class="wire-section">Server-side tool calls</div>` +
    st.tools.map((t) => `<div class="tool-call">
      <div class="tc-name">⚙ ${esc(t.name)}</div>
      <div class="tc-arg">args: ${esc(JSON.stringify(t.arguments))}</div>
      <div class="tc-res">${esc(typeof t.result === "string" ? t.result : JSON.stringify(t.result, null, 2))}</div>
    </div>`).join("") : "";

  // stateful savings meter (responses)
  let savingsHtml = "";
  if (st.savings) {
    const { sent, would } = st.savings;
    const pct = Math.min(100, (would ? would : 1) / Math.max(would, 1) * 100);
    savingsHtml = `<div class="savings">
      Stateful turn: client sent <b>${sent}</b> message${sent === 1 ? "" : "s"};
      a stateless API would have re-sent <b>${would}</b>.
      <div class="bars2">
        <div class="b2 send"><div class="lbl">Stateless re-send</div><div class="track"><div class="fill" style="width:${pct}%"></div></div></div>
        <div class="b2 skip"><div class="lbl">Responses (this)</div><div class="track"><div class="fill" style="width:${Math.min(100, sent / Math.max(would, 1) * 100)}%"></div></div></div>
      </div></div>`;
  }

  const metricsHtml = st.metrics ? `<div class="metrics">
      <div class="metric"><div class="mk">Input tok</div><div class="mv">${st.metrics.input_tokens}</div></div>
      <div class="metric"><div class="mk">Output tok</div><div class="mv">${st.metrics.output_tokens}</div></div>
      <div class="metric"><div class="mk">Est. cost</div><div class="mv cost">${fmtUSD(st.metrics.cost_usd)}</div></div>
      <div class="metric"><div class="mk">Latency ${st.metrics.live ? "· LIVE" : ""}</div><div class="mv ${st.metrics.live ? "live" : ""}">${fmtMs(st.metrics.latency_ms)}</div></div>
    </div>` : "";

  container.innerHTML = `
    <div class="wire-head"><span class="wt" style="color:${accent}">⌁ Wire Inspector</span>
      <span class="wsub">${esc(s.name)} · ${esc(w.path)}</span></div>
    <div class="wire-tabs">${tab("request", "Request")}${tab("curl", "cURL")}${tab("response", "Response")}</div>
    <div class="wire-body">${savingsHtml}${toolsHtml}${body}</div>
    ${metricsHtml}`;

  $$(".wire-tab", container).forEach((b) => b.onclick = () => { st.tab = b.dataset.tab; renderWire(container, st); });
}

/* ============================================================ TRIAGE */
function wireTriage(region) {
  const wireEl = $("#triageWire");
  let st = newWire("chat_completions");
  renderWire(wireEl, st);

  $("#triageSend").onclick = async () => {
    const msg = $("#triageInput").value.trim();
    if (!msg) return toast("Type or pick a message first.");
    const btn = $("#triageSend"); btn.disabled = true; btn.textContent = "Classifying…";
    st = newWire("chat_completions");
    $("#triageResult").classList.add("hidden");
    let parsed = null, streamed = "";
    try {
      await streamNDJSON("/api/triage", { message: msg, model: SEL.triage, region: region() }, (ev) => {
        if (ev.type === "request") { st.wire = ev.wire; renderWire(wireEl, st); }
        else if (ev.type === "delta") { streamed += ev.text; }
        else if (ev.type === "notice") { toast(ev.text); }
        else if (ev.type === "done") {
          st.response = ev.response; st.metrics = ev.metrics; st.tab = "response";
          parsed = ev.parsed; renderWire(wireEl, st);
        }
      });
      if (parsed) renderTriage(parsed);
    } catch (e) { toast("Request failed: " + e.message); }
    finally { btn.disabled = false; btn.textContent = "Classify & route →"; }
  };
}

function renderTriage(p) {
  const sentClass = (p.sentiment || "").includes("frust") ? "frustrated"
    : (p.sentiment || "").includes("pos") ? "positive" : "neutral";
  const prioClass = (p.priority || "").startsWith("P1") ? "p1" : "neutral";
  const cell = (k, v, cls = "") => `<div class="tg-cell"><div class="k">${k}</div>
    <div class="v">${cls ? `<span class="badge ${cls}">${esc(v)}</span>` : esc(v)}</div></div>`;
  const ent = p.entities && Object.keys(p.entities).length
    ? Object.entries(p.entities).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(", ") : v}`).join(" · ")
    : "—";
  $("#triageGrid").innerHTML =
    cell("Intent", p.intent) +
    cell("Sentiment", p.sentiment, sentClass) +
    cell("Priority", p.priority, prioClass) +
    cell("Queue", p.queue) +
    cell("Entities", ent) +
    cell("Summary", p.summary);
  $("#triageMacro").innerHTML = `<b>Suggested macro</b> → ${esc(p.suggested_macro || "—")}`;
  $("#triageResult").classList.remove("hidden");
}

/* per-model cost economics for the current triage message */
function buildEconomics() {
  const sample = ($("#triageInput") && $("#triageInput").value) || CFG.sample_prompts.triage[0];
  const inTok = Math.max(1, Math.round((sample.length + 220) / 4)); // + system prompt
  const outTok = 90;
  const rows = CFG.models.filter((m) => m.surfaces.includes("chat_completions")).map((m) => {
    const cost = inTok / 1e6 * m.price_in + outTok / 1e6 * m.price_out;
    return { m, cost };
  }).sort((a, b) => a.cost - b.cost);
  const max = Math.max(...rows.map((r) => r.cost)) || 1;
  $("#modelEcon").innerHTML = rows.map((r, i) => {
    const p = CFG.providers[r.m.provider] || { color: "#888" };
    return `<div class="econ-row ${i === 0 ? "cheapest" : ""}">
      <div class="em"><span class="pdot" style="background:${p.color};width:7px;height:7px;border-radius:50%"></span>${esc(r.m.label)}</div>
      <div><div class="econ-bar" style="width:${Math.max(4, r.cost / max * 100)}%"></div></div>
      <div class="ev">${fmtUSD(r.cost)}${i === 0 ? " ✓" : ""}</div>
    </div>`;
  }).join("");
}

/* ============================================================ CONCIERGE */
function wireConcierge(region) {
  const wireEl = $("#conciergeWire");
  let st = newWire("responses");
  let prevId = null, turn = 0;
  renderWire(wireEl, st);

  const reset = () => {
    prevId = null; turn = 0;
    $("#thread").innerHTML = "";
    $("#memoryBanner").classList.add("hidden");
    st = newWire("responses"); renderWire(wireEl, st);
    buildConciergeChips();
    toast("Conversation reset — server state cleared.");
  };
  $("#conciergeReset").onclick = reset;

  function buildConciergeChips() {
    const arr = CFG.sample_prompts.concierge;
    const next = Math.min(turn, arr.length - 1);
    $("#conciergeChips").innerHTML = arr.map((p, i) =>
      `<button class="chip" data-i="${i}" ${i === next ? 'style="border-color:var(--resp);color:#d9b8ff"' : ""}>${esc(p.length > 70 ? p.slice(0, 67) + "…" : p)}</button>`).join("");
    $$(".chip", $("#conciergeChips")).forEach((c) => c.onclick = () => { $("#conciergeInput").value = arr[+c.dataset.i]; $("#conciergeInput").focus(); });
  }
  buildConciergeChips();
  if (!$("#conciergeInput").value) $("#conciergeInput").value = CFG.sample_prompts.concierge[0];

  const send = async () => {
    const input = $("#conciergeInput").value.trim();
    if (!input) return toast("Type a message first.");
    const btn = $("#conciergeSend"); btn.disabled = true; btn.textContent = "…";
    turn += 1;
    addBubble("user", input);
    $("#conciergeInput").value = "";
    st = newWire("responses");
    let answer = "", asstBubble = null;
    try {
      await streamNDJSON("/api/concierge",
        { input, model: SEL.concierge, region: region(), previous_response_id: prevId, turn }, (ev) => {
        if (ev.type === "request") {
          st.wire = ev.wire;
          st.savings = { sent: ev.responses_sent, would: ev.stateless_would_send };
          renderWire(wireEl, st);
        } else if (ev.type === "tool") {
          st.tools.push({ name: ev.name, arguments: ev.arguments, result: ev.result });
          renderWire(wireEl, st);
        } else if (ev.type === "delta") {
          answer += ev.text;
          if (!asstBubble) asstBubble = addBubble("assistant", "");
          asstBubble.innerHTML = mdLite(answer);
          $("#thread").scrollTop = $("#thread").scrollHeight;
        } else if (ev.type === "notice") { toast(ev.text); }
        else if (ev.type === "done") {
          prevId = ev.response_id; st.response = ev.response; st.metrics = ev.metrics;
          renderWire(wireEl, st);
          showMemory(ev.memory_used, prevId, turn);
        }
      });
    } catch (e) { toast("Request failed: " + e.message); }
    finally { btn.disabled = false; btn.textContent = "Send"; buildConciergeChips(); }
  };
  $("#conciergeSend").onclick = send;
  $("#conciergeInput").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
  });

  function addBubble(role, text) {
    const d = document.createElement("div");
    d.className = `bubble ${role}`;
    d.innerHTML = role === "assistant" ? mdLite(text) : esc(text);
    $("#thread").appendChild(d);
    $("#thread").scrollTop = $("#thread").scrollHeight;
    return d;
  }
  function showMemory(used, rid, turn) {
    const b = $("#memoryBanner");
    if (turn >= 2 && rid) {
      const facts = (used && used.length) ? used.map((u) => `<code>${esc(u)}</code>`).join(" · ") : "prior turns";
      b.innerHTML = `<b>Server remembered:</b> ${facts}. This turn's request carried
        <b>no transcript</b> — just <code>previous_response_id=${esc(rid.slice(0, 16))}…</code>`;
      b.classList.remove("hidden");
    }
  }
}

/* ============================================================ ANALYST */
function wireAnalyst(region) {
  const wireEl = $("#analystWire");
  let st = newWire("messages");
  renderWire(wireEl, st);

  $("#thinkingToggle").onclick = () => {
    const body = $("#thinkingBody");
    const hidden = body.style.display === "none";
    body.style.display = hidden ? "" : "none";
    $("#thinkingToggle").textContent = hidden ? "hide" : "show";
  };

  $("#analystSend").onclick = async () => {
    const prompt = $("#analystInput").value.trim() || CFG.sample_prompts.analyst[0];
    const btn = $("#analystSend"); btn.disabled = true; btn.textContent = "Analyzing…";
    st = newWire("messages");
    $("#thinkingPanel").classList.add("hidden");
    $("#analystAnswer").classList.add("hidden");
    let thinking = "", answer = "";
    $("#thinkingBody").textContent = ""; $("#analystAnswer").innerHTML = "";
    try {
      await streamNDJSON("/api/analyst", { prompt, model: SEL.analyst, region: region() }, (ev) => {
        if (ev.type === "request") { st.wire = ev.wire; renderWire(wireEl, st); }
        else if (ev.type === "thinking_delta") {
          thinking += ev.text;
          $("#thinkingPanel").classList.remove("hidden");
          $("#thinkingBody").textContent = thinking;
        } else if (ev.type === "thinking_done") { /* keep panel */ }
        else if (ev.type === "delta") {
          answer += ev.text;
          $("#analystAnswer").classList.remove("hidden");
          $("#analystAnswer").innerHTML = mdLite(answer);
        } else if (ev.type === "notice") { toast(ev.text); }
        else if (ev.type === "done") {
          st.response = ev.response; st.metrics = ev.metrics; st.tab = "response";
          renderWire(wireEl, st);
        }
      });
    } catch (e) { toast("Request failed: " + e.message); }
    finally { btn.disabled = false; btn.textContent = "Analyze case →"; }
  };
}

/* ============================================================ COMPARE */
function wireCompare(region) {
  $("#compareRun").onclick = async () => {
    const prompt = $("#compareInput").value.trim();
    if (!prompt) return toast("Enter a prompt to compare.");
    const btn = $("#compareRun"); btn.disabled = true; btn.textContent = "Running…";
    try {
      const data = await (await fetch("/api/compare", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, region: region() }),
      })).json();
      renderCompare(data.surfaces);
    } catch (e) { toast("Compare failed: " + e.message); }
    finally { btn.disabled = false; btn.textContent = "Run all three →"; }
  };
}

function renderCompare(surfaces) {
  $("#compareCols").innerHTML = surfaces.map((s) => {
    const meta = s.meta, accent = meta.accent;
    const bodyPreview = JSON.stringify(s.wire.body, null, 1);
    return `<div class="cmp-col" style="--accent:${accent}">
      <div class="cmp-col-head">
        <div class="cspec">${esc(meta.spec)}</div>
        <h4>${esc(meta.name)}</h4>
        <div class="cpath">POST ${esc(meta.path)}</div>
      </div>
      <div class="cmp-col-body">
        <div class="cmp-req">${esc(bodyPreview.length > 600 ? bodyPreview.slice(0, 600) + "\n…" : bodyPreview)}</div>
        <div class="cmp-ans">${mdLite(s.text.length > 360 ? s.text.slice(0, 360) + "…" : s.text)}</div>
      </div>
      <div class="cmp-col-foot">
        <span class="cmp-stat"><b>${s.metrics.input_tokens}</b> in</span>
        <span class="cmp-stat"><b>${s.metrics.output_tokens}</b> out</span>
        <span class="cmp-stat"><b>${fmtUSD(s.metrics.cost_usd)}</b></span>
        <span class="cmp-stat"><b>${fmtMs(s.metrics.latency_ms)}</b></span>
      </div></div>`;
  }).join("");

  const yn = (b) => b ? `<span class="yes">● yes</span>` : `<span class="no">○ no</span>`;
  const rows = [
    ["Auth header", (s) => `<code>${esc(s.meta.auth_header)}</code>`],
    ["Stateful (server memory)", (s) => yn(s.meta.stateful)],
    ["Server-side tool loop", (s) => yn(s.surface === "responses")],
    ["Typed content / images", (s) => yn(s.surface === "messages")],
    ["Visible thinking", (s) => yn(s.surface === "messages")],
    ["Mantle-exclusive", (s) => yn(s.meta.mantle_only)],
    ["You manage history", (s) => yn(!s.meta.stateful)],
  ];
  const head = `<tr><th>Capability</th>${surfaces.map((s) => `<th style="color:${s.meta.accent}">${esc(s.meta.name)}</th>`).join("")}</tr>`;
  const body = rows.map(([label, fn]) =>
    `<tr><td>${label}</td>${surfaces.map((s) => `<td>${fn(s)}</td>`).join("")}</tr>`).join("");
  $("#cmpTable").innerHTML = head + body;
}

/* ============================================================ VALUE */
function buildValueView() {
  // KPIs (illustrative, mid-size retailer @ ~50k contacts/mo)
  const kpis = [
    { v: "68%", l: "auto-resolved or pre-triaged", s: "Stage ① + ② before a human is involved" },
    { v: "~9×", l: "cheaper triage", s: "GPT-OSS 20B vs a frontier model, same task" },
    { v: "0", l: "transcripts re-sent on turn 2+", s: "Responses keeps state server-side" },
    { v: "0.5–1 day", l: "to migrate a call site", s: "base_url + key + model-ID" },
  ];
  $("#kpis").innerHTML = kpis.map((k) =>
    `<div class="kpi"><div class="kv">${k.v}</div><div class="kl">${k.l}</div><div class="ks">${k.s}</div></div>`).join("");

  // cost per 1,000 triage calls across the catalog (illustrative)
  const inTok = 120, outTok = 90, N = 1000;
  const rows = CFG.models.filter((m) => m.surfaces.includes("chat_completions")).map((m) => ({
    m, cost: N * (inTok / 1e6 * m.price_in + outTok / 1e6 * m.price_out),
  })).sort((a, b) => a.cost - b.cost);
  const max = Math.max(...rows.map((r) => r.cost)) || 1;
  $("#costChart").innerHTML = rows.map((r, i) => {
    const p = CFG.providers[r.m.provider] || { color: "#888" };
    return `<div class="bar-row ${i === 0 ? "best" : ""}">
      <div class="bl"><span class="pdot" style="background:${p.color};width:7px;height:7px;border-radius:50%"></span>${esc(r.m.label)}</div>
      <div class="bar-track"><div class="bar-fill" style="width:${Math.max(3, r.cost / max * 100)}%"></div></div>
      <div class="bv">$${r.cost.toFixed(2)}${i === 0 ? " ✓" : ""}</div></div>`;
  }).join("");

  // right-tool recap
  const recap = [
    ["chat_completions", "①", "Triage every message", "Stateless, cheap, fast. Classify & route at volume — you own the history."],
    ["responses", "②", "Concierge with memory", "Server keeps state + runs tools. Multi-turn agent, no transcript replay."],
    ["messages", "③", "Analyst on hard cases", "Anthropic-native typed content (photos) + visible thinking for the human agent."],
  ];
  $("#surfaceRecap").innerHTML = recap.map(([k, ic, t, p]) =>
    `<div class="recap-row" style="--accent:${CFG.surfaces[k].accent}">
      <div class="ri">${ic}</div>
      <div class="rt"><b>${t}</b><p>${p}</p></div></div>`).join("");
}

/* ---------------------------------------------------------------- start */
boot().catch((e) => { console.error(e); toast("Failed to load config: " + e.message); });
