---
title: "Lab 4 — Real-World Use Case"
weight: 60
---

# Lab 4 — End-to-End: Financial Filings Analyzer

**Notebook:** `src/lab4/01_end_to_end_financial_analyzer.ipynb`
**Duration:** ~30 min · **Level:** L300 · **Lab 4 of 4**

## Why this lab

Everything you learned so far, wired into a real application shape — and
tied to a business outcome you could actually defend in a leadership
review.

## The use case

Equity analysts spend 40–60 minutes triaging a single 10-K or earnings
transcript. Most of the questions they ask are either:

1. **Metric lookups** — "What was AMZN's FY24 revenue?"
2. **Thematic analysis** — "How does MSFT's AI positioning compare to
   NVDA's?"
3. **General finance FAQ** — "When do equity options expire?"

Sending *everything* to a frontier model like Claude Opus 4.7 works, but
costs 4× more than needed because the easy 70% of questions don't need
frontier reasoning.

## The architecture

A three-model router:

| Intent | Model | Surface |
|---|---|---|
| `metric_lookup` | `openai.gpt-oss-120b` | Chat Completions + `get_metric` tool |
| `thematic_analysis` | `anthropic.claude-opus-4-7` | Anthropic Messages |
| `faq` | `anthropic.claude-haiku-4-5` | Anthropic Messages + RAG over HF dataset |

Intent classification runs on **Haiku 4.5** (cheap + fast).

## What you'll see

- A real Hugging Face dataset (`gbharti/finance-alpaca`) loaded and used
  as a stand-in for an enterprise knowledge base.
- Short-term Bearer-token auth.
- A multi-turn conversation with local session state.
- A tool-calling loop wired to a mock financial data lake.
- A cost-comparison framing that justifies the router architecture.

## What you won't see (but should add in production)

The notebook's final cell lists a hardening checklist:

- Token rotation.
- Mantle Project tagging for cost attribution.
- Guardrails on ingress / egress.
- Structured telemetry per turn.
- Regional failover.
- SLO targets per intent.

## Pre-reqs

Labs 1–3 complete. Network egress to `huggingface.co`. Enough Opus 4.7
TPM headroom for ~5 calls.

## Open the notebook

```bash
jupyter lab src/lab4/01_end_to_end_financial_analyzer.ipynb
```
