---
title: "Lab 3 — Migration from Bedrock Runtime"
weight: 50
---

# Lab 3 — Migration from Bedrock Runtime to Mantle

**Notebooks:**

- `src/lab3/01_api_sdk_diff.ipynb`
- `src/lab3/02_auth_security_migration.ipynb`
- `src/lab3/03_tools_and_caching_migration.ipynb`
- `src/lab3/04_perf_eval.ipynb`

**Duration:** ~30 min total · **Level:** L300 · **Lab 3 of 4**

## Why this lab

This is the lab that actually maps to production work. If you have
Converse / InvokeModel code running today, this is the lab that walks you
through what every call site has to become.

## What you'll cover

### 3.1 API / SDK call differences

- Same prompt, three calls: Converse, Chat Completions, Anthropic Messages.
- A single table showing every field-name change.
- A minimal `NormalizedReply` adapter so downstream code doesn't care
  which surface produced the reply.

### 3.2 Authentication and security

- IAM policy swap: `bedrock:*` → `bedrock-mantle:*`.
- Short-term vs long-term Bearer tokens; SigV4 on Mantle still works.
- CloudTrail event selectors for the new service prefix.
- Guardrails — why `guardrailConfig` vanished, and what to replace it with.

### 3.3 Tools and caching

- Port a working Converse tool loop to Chat Completions line-by-line.
- The six things that change: schema wrapper, `toolChoice` vocab,
  `stopReason`, `json.loads()` arguments, `role:"tool"` turn-in,
  rich-content flattening.
- `additionalModelRequestFields` → `extra_body`.

### 3.4 Performance evaluation

- TTFT and tokens-per-second for Mantle Chat Completions vs runtime
  ConverseStream, head-to-head.
- Mantle vs Runtime API performance and accuracy comparison
- Statistical gotchas — cold starts, diurnal variance, apples-to-apples
  model selection.
- Optional matplotlib histogram.

## Pre-reqs

Lab 1 complete (Lab 2 helpful but not required). You also need access to
at least one runtime Converse-capable model — `anthropic.claude-haiku-4-5`,
`mistral.mistral-large-2407-v1:0`, or
`anthropic.claude-3-5-haiku-20241022-v1:0` all work; the notebooks try
them in order and skip gracefully if none are available.

## Open the notebooks

```bash
jupyter lab src/lab3/
```
