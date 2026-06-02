# Mantle Studio

**One endpoint, three APIs, zero rewrites** — an interactive demo of the Amazon
Bedrock **Mantle** unified inference endpoint (`bedrock-mantle.{region}.api.aws`).

A single host, key and SDK reach a multi-vendor model catalog through three API
*styles*. This demo lets a technical **and** business audience feel the
difference by walking one realistic customer-support story across all three:

| Stage | Surface | Path | Why this surface |
|------|---------|------|------------------|
| ① **Triage** | Chat Completions *(OpenAI-compatible)* | `/v1/chat/completions` | Stateless, low-latency, high-volume classification. You own the history. |
| ② **Concierge** | Responses API *(OpenAI-compatible, Mantle-only)* | `/v1/responses` | **Stateful** — server keeps the conversation (`previous_response_id`) and runs the tool loop. |
| ③ **Analyst** | Messages API *(Anthropic-native)* | `/anthropic/v1/messages` | Typed content (images), **visible thinking**, full Claude fidelity. |

The storyline: **Northwind Outfitters**, an outdoor-gear retailer, runs its AI
customer-experience platform on Mantle. A customer's tent pole snaps on first
setup — watch the same incident flow through triage → concierge → analyst.

---

## Run it

```bash
cd mantle-demo
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
# open http://127.0.0.1:8000
```

That's it. The demo runs in **DEMO mode** by default — no AWS account, no
network, no credentials. Responses are produced by a scenario-aware mock engine
shaped *exactly* like the real provider bodies (believable tokens, latency and
cost), so it's bullet-proof in front of a live audience and works offline.

> The Responses-API statefulness is **genuine**, not faked: the mock keeps real
> server-side conversation state keyed by `previous_response_id`. Turn 2+ sends
> **no transcript** — only the pointer — and the server still remembers.

---

## What to show (suggested 5-minute flow)

1. **Overview** — the single endpoint fans out to three paths; read the
   `bedrock-runtime` → `bedrock-mantle` migration diff (the punchline).
2. **Triage** — paste an angry message; get structured JSON (intent, sentiment,
   priority, routing) and a per-model **cost bar chart** for the same task.
3. **Concierge** — send 2–3 turns. Open the **Wire Inspector** on turn 2: the
   request body carries `previous_response_id` and **no transcript**. Tools
   (`get_order`, `get_policy`) run server-side.
4. **Analyst** — escalate the case with the attached photo. Watch **extended
   thinking** stream, then a structured resolution. Note the `x-api-key` auth.
5. **Compare** — one prompt, three surfaces, side by side + a capability table.
6. **Business value** — illustrative KPIs and cost-per-1,000-calls economics.

Every console has a live **Wire Inspector** showing the exact HTTP request
(method, URL, headers, JSON body, equivalent `curl`), the response, and metrics.
The per-surface **auth-header difference** is faithful: OpenAI surfaces use
`Authorization: Bearer …`; the Anthropic Messages surface uses `x-api-key` +
`anthropic-version`.

---

## LIVE mode (optional — call the real endpoint)

```bash
pip install aws-bedrock-token-generator   # short-term Bearer from your IAM session
export MANTLE_LIVE=1
# auth, any one of:
export AWS_BEARER_TOKEN_BEDROCK="<bearer token>"   # explicit token, OR
#   rely on aws-bedrock-token-generator + your AWS credentials
uvicorn app:app --port 8000
```

The badge in the top bar flips to **LIVE** when `MANTLE_LIVE=1` *and* a token is
obtainable. LIVE calls the real `bedrock-mantle` endpoint and **falls back to the
mock on any error** — the demo never breaks. The Compare view always uses the
mock so the side-by-side is instant and deterministic.

Switch region from the top-bar selector; the host updates to
`bedrock-mantle.{region}.api.aws` across the UI.

---

## Architecture

```
app.py            FastAPI: one route per surface, NDJSON streaming, DEMO/LIVE switch
mantle_client.py  build_request() (exact wire object) + call_live() (real HTTP)
mock_engine.py    scenario-aware mock; REAL server-side state for Responses
scenarios.py      Northwind data + the server-side "tools" (order/product/policy)
config.py         model catalog, 3 surfaces, 13 regions, illustrative pricing
static/           index.html · styles.css · app.js  (vanilla, no build step)
```

**Event protocol** (NDJSON, one JSON object per line, browser reads via
`fetch` + `ReadableStream`):

```
{"type":"request", "wire":{…}}        the exact HTTP call (Wire Inspector)
{"type":"tool", …}                    server-side tool call (Responses only)
{"type":"thinking_delta", "text":…}   extended thinking (Messages only)
{"type":"delta", "text":…}            streamed answer tokens
{"type":"done", "response":…, "metrics":…}
```

---

## Honest caveats

- **Pricing is illustrative**, clearly labelled in the UI — not an AWS quote.
- The mock's "intelligence" is deterministic keyword routing over the Northwind
  data. The point is the **API surfaces and the business framing**, not a model.
- Mantle complements, not replaces, `bedrock-runtime`. The Business-value view
  lists when to keep runtime (Nova/Titan/Llama/Cohere, Batch, bidirectional
  speech, GovCloud, native Guardrails/KB/Agents/Flows). Most enterprises run a
  **hybrid**.
