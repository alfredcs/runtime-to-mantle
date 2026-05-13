# Lab 3 — Migration from Bedrock Runtime to Mantle

**Notebooks:**

| # | File | Topic |
|---|---|---|
| 3.1 | `01_api_sdk_diff.ipynb` | Converse vs Chat Completions vs Anthropic Messages — three shapes, one prompt |
| 3.2 | `02_auth_security_migration.ipynb` | IAM policy swap, Bearer tokens, CloudTrail, guardrails |
| 3.3 | `03_tools_and_caching_migration.ipynb` | Converse tool loop → Mantle tool loop, `additionalModelRequestFields` → `extra_body` |
| 3.4 | `04_perf_eval.ipynb` | TTFT and tokens/sec head-to-head |

**Duration:** ~30 min total (4 × ~7-8 min) · **Level:** L300 · **Lab 3 of 4**

## Goals

- Have a mental model for what changes *in every call site* when you move
  off Converse.
- Ship a correct, tested migration of a tool-loop.
- Produce a p50/p95 TTFT comparison on your own account.
- Leave with a migration checklist you can paste into a runbook.

## Prerequisites

Same as Lab 1, plus:

- Access to at least one runtime Converse-capable model (the notebooks
  fall back gracefully if absent — e.g. `anthropic.claude-haiku-4-5`,
  `mistral.mistral-large-2407-v1:0`, or
  `anthropic.claude-3-5-haiku-20241022-v1:0` — any of these work).
- Enough quota headroom to run ~20 samples per endpoint for the perf lab.
