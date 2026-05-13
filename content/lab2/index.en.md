---
title: "Lab 2 — Advanced Mantle Features"
weight: 40
---

# Lab 2 — Advanced Mantle Features

**Notebooks:**

- `src/lab2/01_streaming.ipynb`
- `src/lab2/02_tool_calling.ipynb`
- `src/lab2/03_caching_and_stateful.ipynb`

**Duration:** ~30 min total · **Level:** L300 · **Lab 2 of 4**

## Why this lab

"Hello world" is easy on every API. Real Mantle applications add
**streaming**, **tools**, **caching**, and **statefulness** — and every one
of those features is shaped differently on each Mantle surface. This lab
gives you reusable patterns for all three.

## What you'll cover

### 2.1 Streaming

- Accumulate `delta.content` fragments on Chat Completions.
- Consume typed events (`response.output_text.delta`,
  `response.completed`) on the Responses API.
- Use the Anthropic SDK's `.text_stream` accumulator on Messages.
- See the event-taxonomy cheat sheet side-by-side.

### 2.2 Tool / function calling

- Full tool loop on Chat Completions with the `json.loads(arguments)` step
  that trips everybody up.
- Same loop on Anthropic Messages — arguments arrive parsed; tool results
  go in a `user` message with `tool_result` blocks.
- Preview of server-side tool execution via MCP Lambda (Responses API,
  Mantle-only).

### 2.3 Caching and statefulness

- Prefix-cache affinity with `extra_body.cache_salt`, with a measurable
  TTFT before/after.
- Multi-turn threads with `previous_response_id` on the Responses API.
- `cache_control: ephemeral` on the Anthropic Messages path.

## Pre-reqs

Lab 1 complete. Same IAM policy and model access.

## Open the notebooks

```bash
jupyter lab src/lab2/
```
