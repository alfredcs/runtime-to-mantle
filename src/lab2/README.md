# Lab 2 — Advanced Mantle Features

**Notebooks:**

| # | File | Topic |
|---|---|---|
| 2.1 | `01_streaming.ipynb` | SSE streaming on Chat Completions, Responses, Messages |
| 2.2 | `02_tool_calling.ipynb` | Tool / function calling on every Mantle surface |
| 2.3 | `03_caching_and_stateful.ipynb` | Prefix caching + Responses API statefulness + Anthropic `cache_control` |

**Duration:** ~30 min total (3 × ~10 min) · **Level:** L300 · **Lab 2 of 4**

## Goals

- Build a reliable streaming accumulator for each surface.
- Run a full tool-loop on Chat Completions *and* Anthropic Messages,
  including the `json.loads()` trap on OpenAI-compatible surfaces.
- Use Mantle's prefix-caching affinity (`cache_salt`) for measurable
  TTFT wins.
- Thread a multi-turn conversation with the Responses API via
  `previous_response_id`.

## Prerequisites

Same as Lab 1, plus matplotlib for the optional perf plot.
