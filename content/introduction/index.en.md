---
title : "Introduction"
weight : 10
---

# Introduction

## What is Amazon Bedrock Mantle?

**Bedrock Mantle** (service prefix `bedrock-mantle`, endpoint
`bedrock-mantle.{region}.api.aws`) is Amazon Bedrock's next-generation
distributed inference engine. It coexists with the legacy
`bedrock-runtime` endpoint but introduces:

- **Three OpenAI-/Anthropic-native API surfaces** instead of Bedrock's
  per-provider `InvokeModel` + the `Converse` unifier.
- **Bearer-token auth** alongside SigV4 — friendlier for OpenAI-SDK
  callers; SigV4 still works on every surface.
- **Projects** as first-class IAM / cost / quota primitives.
- A **zero-operator-access (ZOA)** security architecture modeled after Nitro.
- **Server-side tool execution** via MCP Lambdas on the Responses API.
- **Mantle-only models**: Claude Opus 4.7, Claude Mythos Preview,
  gpt-oss-120b / 20b, Qwen3, GLM 4.7, MiniMax M2.5, DeepSeek V3.2,
  Kimi K2 Thinking, Mistral Large 3, and more.

## When to migrate (and when not to)

**Migrate to Mantle when you need:**

- OpenAI SDK compatibility.
- Server-side tool use (Lambda / MCP, AgentCore Gateway).
- Stateful Responses API conversations.
- Simpler Bearer-token auth for developer workflows.
- Access to Mantle-only models.

**Keep `bedrock-runtime` when you need:**

- Amazon Nova / Titan, Meta Llama, Cohere, AI21, Stability, TwelveLabs,
  older Mistral / Writer models.
- Batch inference (`StartAsyncInvoke`).
- Bidirectional streaming (speech — e.g. Nova Sonic).
- GovCloud.
- Native Guardrails / Knowledge Bases / Agents / Flows integration.

**In practice, most enterprises land on a hybrid deployment:** route
Mantle-compatible traffic to Mantle behind a provider abstraction; keep
`bedrock-runtime` for everything else; retire `bedrock-runtime` only after
every production model path has a Mantle replacement.

## Workshop learning outcomes

By the end of the four labs you will be able to:

1. Authenticate to Mantle with SigV4 *and* Bearer tokens.
2. Call `gpt-oss-120b`, `Claude Opus 4.7`, and `Claude Haiku 4.5` through
   their correct Mantle surfaces.
3. Migrate a Converse tool-loop (incl. `json.loads()` arguments,
   `role:"tool"` messages, `finish_reason`) to Chat Completions.
4. Measure and compare TTFT / tokens-per-second between Runtime and Mantle.
5. Ship an end-to-end multi-model application backed by a public dataset.

## Target audience

- AI Engineers, ML Engineers, Solutions Architects.
- 6+ months of hands-on Bedrock Runtime experience.
- Comfortable reading Python and Jupyter notebooks.
- Some familiarity with OpenAI or Anthropic SDKs is helpful.
