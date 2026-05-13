---
title: "Lab 1 — Mantle Fundamentals"
weight: 30
---

# Lab 1 — Mantle Fundamentals

**Notebook:** `src/lab1/01_mantle_fundamentals.ipynb`
**Duration:** ~30 min · **Level:** L200 · **Lab 1 of 4**

## Why this lab

This is the mental model the rest of the workshop sits on top of. Skip it
and the later labs will feel like three unrelated APIs — work through it
and they become three well-understood surfaces.

## You will

- Run `GET /v1/models` with both the OpenAI SDK (Bearer) and `requests` +
  SigV4 to prove they return the same list.
- Call `openai.gpt-oss-120b` through `/v1/chat/completions`.
- Call `anthropic.claude-opus-4-7` through `/anthropic/v1/messages`.
- See the field-name differences between Chat Completions, Responses API,
  and Anthropic Messages laid out in one table.
- Learn why `max_tokens` is a **reservation**, not just a safety net.
- Read about short-term vs long-term Bearer tokens and when to use each.
- Understand the Projects primitive and the default project ARN.

## What's different from runtime

| Concept | Runtime | Mantle |
|---|---|---|
| Model-listing API | `ListFoundationModels` | `GET /v1/models` (OpenAI-style) |
| Auth | SigV4 only | SigV4 **or** Bearer |
| System prompt | `system=[{text:…}]` | role `"system"` (CC) / `system: "..."` (Anthropic) |
| Claude endpoint | `InvokeModel` or `Converse` | `/anthropic/v1/messages` |

## Open the notebook

```bash
jupyter lab src/lab1/01_mantle_fundamentals.ipynb
```
