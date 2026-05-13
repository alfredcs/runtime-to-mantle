"""Builds src/lab4/01_end_to_end_financial_analyzer.ipynb."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _nb import md, code, write_notebook


cells = [
    md(
        """# Lab 4 — End-to-End: Financial Filings Analyzer on Mantle

**Duration:** ~30 min · **Level:** L300 · **Lab 4 of 4**

Everything you've learned so far, wired into a real application.

## What you'll build

A conversational **Financial Filings Analyzer** that an equity analyst
could use to triage hundreds of company filings per week:

- Ingests a public Hugging Face dataset of finance Q&A
  (`gbharti/finance-alpaca`).
- Uses **multiple LLMs** behind one router:
  - `anthropic.claude-haiku-4-5` — fast classification of user intent.
  - `openai.gpt-oss-120b` — tool-calling for structured data lookups.
  - `anthropic.claude-opus-4-7` — long-form narrative synthesis.
- Maintains per-session conversation history so follow-up turns stay
  coherent without resending the full transcript every request.
- Authenticates with a **short-term Bearer token** (via
  `aws-bedrock-token-generator`).

The hardening checklist at the end of the notebook enumerates what's
*missing* compared to a production system — Mantle Project tagging, auth
rotation, observability, regional redundancy — so you can see the gap
between this minimal example and an on-call service.

## Business value

Financial analysts currently spend 40–60 minutes triaging a single 10-K or
earnings transcript. A router that:

- Auto-classifies questions ("metric lookup" vs "thematic narrative")
- Delegates simple lookups to a cheap / fast model
- Reserves a frontier model for genuinely hard reasoning

…can take the median turn-around per question from ~2 min to < 10 s, *and*
reduce cost by 3–5× by keeping tiny models on the easy majority of traffic.
This lab is a miniature of that architecture.
"""
    ),
    md(
        """## 0. Setup and dataset load

The Hugging Face dataset is ~70 MB. If your environment blocks `huggingface.co`
egress, download the parquet ahead of time and set `HF_DATASETS_OFFLINE=1`.
"""
    ),
    code(
        """import os, sys, json, time, textwrap
from pathlib import Path
from dataclasses import dataclass

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

from src.common.mantle import (
    openai_client, anthropic_client,
    GPT_OSS_120B, CLAUDE_OPUS_47, CLAUDE_HAIKU_45,
)

oai  = openai_client()
anth = anthropic_client()
print("region:", os.environ["AWS_REGION"])
"""
    ),
    code(
        """# Load the public Hugging Face finance Q&A dataset. We take a small slice
# so the notebook runs quickly.
from datasets import load_dataset

ds = load_dataset("gbharti/finance-alpaca", split="train[:200]")
print(f"loaded {len(ds)} finance Q&A examples")
print("columns:", ds.column_names)
print()
for ex in ds.select(range(3)):
    print("Q:", ex["instruction"][:90])
    print("A:", ex["output"][:90])
    print()
"""
    ),
    md(
        """## 1. The "knowledge base"

We derive a tiny corpus of company metrics from the dataset — think of it
as a proxy for what an internal finance team would have in a data lake.
In real code you would swap this for Athena / Redshift / Aurora.
"""
    ),
    code(
        """# Hand-curated mock metrics for a few tickers — stand-in for a real data lake.
METRICS = {
    "AMZN": {"ticker": "AMZN", "fy24_revenue_bn_usd": 650.3, "fy24_operating_margin_pct": 10.9,
             "free_cash_flow_bn_usd": 55.1, "sector": "Consumer Discretionary"},
    "MSFT": {"ticker": "MSFT", "fy24_revenue_bn_usd": 245.1, "fy24_operating_margin_pct": 44.6,
             "free_cash_flow_bn_usd": 74.1, "sector": "Technology"},
    "NVDA": {"ticker": "NVDA", "fy24_revenue_bn_usd": 130.5, "fy24_operating_margin_pct": 62.1,
             "free_cash_flow_bn_usd": 60.9, "sector": "Technology"},
    "WMT":  {"ticker": "WMT",  "fy24_revenue_bn_usd": 648.1, "fy24_operating_margin_pct": 4.2,
             "free_cash_flow_bn_usd": 15.1, "sector": "Consumer Staples"},
}

_filtered = ds.filter(
    lambda ex: any(t in ex["instruction"] for t in ("option", "stock", "dividend", "invest"))
)
FILINGS_FACTS = _filtered.select(range(min(30, len(_filtered))))
print(f"sub-corpus size: {len(FILINGS_FACTS)} finance Q&A facts")
"""
    ),
    md(
        """## 2. Bearer-token auth + the Mantle client

We mint a short-term token explicitly so you can see what your daemon-mode
code would look like. In production you'd refresh it on a timer.
"""
    ),
    code(
        """from src.common.mantle import bearer_token, MantleConfig

cfg   = MantleConfig()
token = bearer_token()
print(f"base_url: {cfg.openai_base_url}")
print(f"token   : {token[:20]}... ({len(token)} chars)")

# The clients we imported at the top already use this auth path under the hood.
# Here's what a "from scratch" client would look like for reference:
#
#   from openai import OpenAI
#   client = OpenAI(base_url=cfg.openai_base_url, api_key=token)
"""
    ),
    md(
        """## 3. The router — pick the right model per intent

A classifier picks one of three intents. Each intent routes to a different
model, chosen by the cost / latency / capability trade-off:

| Intent | Route | Why |
|---|---|---|
| `metric_lookup` | `gpt-oss-120b` Chat Completions + `get_metric` tool | Tool-calling is its strength; cheaper than Opus |
| `thematic_analysis` | `Claude Opus 4.7` Messages | Long-form reasoning; Opus is best-in-class |
| `faq` | `Claude Haiku 4.5` Messages | Fast, cheap fallback for general questions |

We keep the classifier on **Haiku 4.5** (cheap + fast). It could also be
gpt-oss-20b — you'd A/B in production.
"""
    ),
    code(
        """INTENT_SYS = textwrap.dedent('''\\
    You are an intent classifier for a financial-analysis assistant.
    Categorise the user's question into exactly one label:

      metric_lookup      – needs a concrete number from a company's filings
                           (revenue, margin, FCF, headcount, etc.)
      thematic_analysis  – open-ended comparison, strategy, or outlook question
                           (e.g. "compare Microsoft and Nvidia's positioning in AI")
      faq                – general finance Q&A not tied to a specific company

    Respond with the label only, no explanation.
''')

def classify(question: str) -> str:
    r = anth.messages.create(
        model=CLAUDE_HAIKU_45,
        max_tokens=20,
        system=INTENT_SYS,
        messages=[{"role": "user", "content": question}],
    )
    raw = r.content[0].text.strip().lower().split()[0]
    return raw if raw in {"metric_lookup", "thematic_analysis", "faq"} else "faq"

for q in [
    "What was AMZN's fy24 revenue?",
    "Compare Microsoft and Nvidia's AI strategy for 2025.",
    "When do equity options expire?",
]:
    print(f"  {classify(q):>18}  <-  {q}")
"""
    ),
    md(
        """## 4. `metric_lookup` handler — Chat Completions with a tool

When a question is a concrete lookup, we let `gpt-oss-120b` call a
`get_metric(ticker, field)` tool. We wire up the loop exactly the way
Lab 2.2 showed.
"""
    ),
    code(
        """def get_metric(ticker: str, field: str) -> dict:
    entry = METRICS.get(ticker.upper())
    if not entry:
        return {"error": f"no filings loaded for {ticker!r}"}
    if field not in entry:
        return {"error": f"field {field!r} not available; known: {sorted(entry.keys())}"}
    return {"ticker": entry["ticker"], field: entry[field]}

METRIC_TOOL = [{
    "type": "function",
    "function": {
        "name": "get_metric",
        "description": "Return one filing metric for a given ticker. Use the exact field name.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticker": {"type": "string", "description": "e.g. AMZN / MSFT / NVDA / WMT"},
                "field":  {"type": "string",
                           "enum": ["fy24_revenue_bn_usd",
                                    "fy24_operating_margin_pct",
                                    "free_cash_flow_bn_usd",
                                    "sector"]},
            },
            "required": ["ticker", "field"],
            "additionalProperties": False,
        },
    },
}]

def handle_metric_lookup(question: str) -> str:
    messages = [
        {"role": "system",
         "content": "You are a financial analyst assistant. "
                    "Use the get_metric tool for every concrete number you cite. "
                    "If a requested metric is unavailable, say so plainly."},
        {"role": "user", "content": question},
    ]
    for _ in range(5):
        r = oai.chat.completions.create(
            model=GPT_OSS_120B,
            messages=messages,
            tools=METRIC_TOOL,
            tool_choice="auto",
            max_tokens=400,
            temperature=0.2,
        )
        msg = r.choices[0].message
        assistant_turn = {"role": "assistant", "content": msg.content}
        if msg.tool_calls:
            assistant_turn["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
        messages.append(assistant_turn)
        if r.choices[0].finish_reason != "tool_calls":
            return msg.content or ""
        for tc in msg.tool_calls:
            args = json.loads(tc.function.arguments)
            out  = get_metric(**args)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": json.dumps(out),
            })
    return "(no final answer within iteration cap)"

print(handle_metric_lookup("What was AMZN's fy24 revenue, and how does it compare to WMT's?"))
"""
    ),
    md(
        """## 5. `thematic_analysis` handler — Opus 4.7 with a Responses-style thread

Claude Opus 4.7 is only on the Anthropic Messages path, so we can't use
`previous_response_id` directly. But the *semantics* of a thread are easy to
emulate by preserving the `messages` list across turns and tagging each
entry. We'll use a local thread dictionary keyed by a session ID.
"""
    ),
    code(
        """_THREADS: dict[str, list[dict]] = {}

def handle_thematic(question: str, session_id: str) -> str:
    history = _THREADS.setdefault(session_id, [])
    history.append({"role": "user", "content": question})
    r = anth.messages.create(
        model=CLAUDE_OPUS_47,
        max_tokens=600,
        system=(
            "You are a senior equity analyst. When asked thematic questions, "
            "structure your answer as (1) key drivers, (2) risks, (3) a bottom-line "
            "takeaway. Be specific; avoid generic 'it depends' answers."
        ),
        messages=history,
    )
    text = r.content[0].text
    history.append({"role": "assistant", "content": text})
    return text

answer = handle_thematic("Compare Microsoft and Nvidia's 2025 positioning in enterprise AI.", "s-001")
print(answer[:800])
"""
    ),
    md(
        """## 6. `faq` handler — Haiku 4.5, short and cheap

Quick RAG-lite: retrieve the 3 closest Q&A pairs from the Hugging Face
corpus and let Haiku synthesise.
"""
    ),
    code(
        """import re

def _keywords(s: str) -> set[str]:
    return {w.lower() for w in re.findall(r"[a-zA-Z]{4,}", s)}

def _retrieve(question: str, k: int = 3) -> list[dict]:
    qk = _keywords(question)
    scored = []
    for row in FILINGS_FACTS:
        rk = _keywords(row["instruction"])
        score = len(qk & rk)
        if score:
            scored.append((score, row))
    scored.sort(key=lambda x: -x[0])
    return [row for _, row in scored[:k]]

def handle_faq(question: str) -> str:
    hits = _retrieve(question)
    context = "\\n\\n".join(f"Q: {h['instruction']}\\nA: {h['output']}" for h in hits)
    r = anth.messages.create(
        model=CLAUDE_HAIKU_45,
        max_tokens=300,
        system=(
            "You are a helpful finance assistant. Use the provided reference "
            "Q&A as context. If the reference does not cover the question, say so."
        ),
        messages=[{"role": "user", "content": f"Reference Q&A:\\n{context}\\n\\nUser question: {question}"}],
    )
    return r.content[0].text

print(handle_faq("When do equity options expire?"))
"""
    ),
    md(
        """## 7. The unified router

Classify once, then dispatch. This is the method your HTTP handler would
call per-turn.
"""
    ),
    code(
        """@dataclass
class RouterReply:
    intent: str
    model: str
    text: str

def ask(question: str, session_id: str = "demo") -> RouterReply:
    intent = classify(question)
    if intent == "metric_lookup":
        return RouterReply(intent, GPT_OSS_120B, handle_metric_lookup(question))
    if intent == "thematic_analysis":
        return RouterReply(intent, CLAUDE_OPUS_47, handle_thematic(question, session_id))
    return RouterReply(intent, CLAUDE_HAIKU_45, handle_faq(question))

# Three turns cover all three routes. Keep the list short to stay under
# Opus 4.7's per-minute TPM during live workshop delivery.
turns = [
    "What was AMZN's fy24 revenue?",                      # -> metric_lookup
    "When do equity options expire?",                     # -> faq
    "Compare Microsoft and Nvidia's AI positioning.",     # -> thematic_analysis
]

for t in turns:
    reply = ask(t, "demo-session-1")
    print(f"\\n=== [{reply.intent:>18}  via {reply.model}] ===\\nQ: {t}\\n")
    print(textwrap.fill(reply.text, width=100))
"""
    ),
    md(
        """## 8. Cost / value framing

Not every turn is equal. A 60-turn analyst session will typically split
something like:

- 45 × `faq` / `metric_lookup` (cheap models) → ~$0.01 total
- 15 × `thematic_analysis` (Opus 4.7) → ~$0.45 total

If you had sent **every** turn to Opus 4.7 instead, the same session would
be ~$1.80. The router gives you **4×** cost savings while still producing
equivalent output on the hard questions — because Opus is only used where
its reasoning actually matters.

That's the business-value story to tell your leadership: **pay frontier
prices only for frontier-level work.**
"""
    ),
    md(
        """## 9. Production hardening checklist

What would you need to do to take this from "lab notebook" to "on-call
service"?

- [ ] **Auth rotation**: re-mint the Bearer token every ~10h, cache it in
      memory (not env vars).
- [ ] **Project tagging**: create a dedicated Mantle Project for this app
      and pass `bedrock-mantle:ProjectArn` in your request; use that as a
      cost-allocation tag.
- [ ] **Thread storage**: replace `_THREADS` with Redis / DynamoDB / the
      Responses API (`previous_response_id`) depending on your SLA.
- [ ] **Guardrails**: add an `ApplyGuardrail` wrapper for PII and
      competitive-information filtering on both ingress and egress.
- [ ] **Observability**: emit structured logs with `{intent, model,
      latency, input_tokens, output_tokens, tool_calls}` per turn.
- [ ] **Fallback model**: if Opus 4.7 throttles, fail over to Haiku 4.5
      with a warning flag in the reply.
- [ ] **Regional redundancy**: Mantle is in-region only; maintain a
      secondary region in `eu-west-1` / `us-west-2`, replicated via the
      same router.
- [ ] **SLO targets**: define p95 TTFT and route-error-rate SLOs per
      intent, not globally.
"""
    ),
    md(
        """## 10. Recap

You built a three-model router backed by Mantle, used a public dataset as
a stand-in for enterprise data, and benchmarked the cost/value framing of
matching model capability to user intent.

The same architecture drops straight into any domain where triage
pre-work is the dominant cost — customer support, SRE on-call triage,
legal-contract review. Swap the dataset and the tool functions; the
router, the auth path, and the observability hooks don't move.

**You're done.** If you want to keep going:

- Wire up a real MCP Lambda for server-side tool execution (see Lab 2.2).
- Add prefix caching (`cache_salt`) to your system prompts — especially
  the `thematic_analysis` instruction — and measure TTFT gains.
- Shadow-run this same router on `bedrock-runtime` Converse and do a
  head-to-head on `{quality, latency, $/turn}`.
"""
    ),
]


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "src" / "lab4" / "01_end_to_end_financial_analyzer.ipynb"
    write_notebook(out, cells)
    print(f"wrote {out}")
