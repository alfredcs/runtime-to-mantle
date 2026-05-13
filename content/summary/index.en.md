---
title: "Summary"
weight: 99
---

# Summary

## What you built

Across four labs you:

- Authenticated to Bedrock Mantle with both SigV4 and Bearer tokens.
- Called `openai.gpt-oss-120b`, `anthropic.claude-opus-4-7`, and
  `anthropic.claude-haiku-4-5` through their correct Mantle surfaces.
- Streamed responses on three different event taxonomies.
- Ran tool-calling loops on Chat Completions and Anthropic Messages,
  including the `json.loads()` trap that bites every migration.
- Used prefix caching and the stateful Responses API.
- Migrated a Converse tool loop to Chat Completions line-by-line.
- Benchmarked TTFT and tokens-per-second runtime-vs-Mantle on your own
  account.
- Shipped an end-to-end multi-model router backed by a public dataset,
  with a cost-comparison framing to justify it to leadership.

## Migration checklist — "am I ready to flip the flag?"

- [ ] IAM: `AmazonBedrockMantleInferenceAccess` on app roles; audit any
      `bedrock:*` statements for missing `bedrock-mantle:*` counterparts.
- [ ] Tokens: short-term Bearer in prod, long-term keys in CI only;
      Secrets Manager + rotation Lambda for the latter.
- [ ] CloudTrail: event selector for `bedrock-mantle.amazonaws.com` added
      to every trail that previously captured `bedrock.amazonaws.com`.
- [ ] Guardrails: out-of-band `ApplyGuardrail` in the wrapper (or an
      equivalent policy engine); CI check that no Mantle call includes
      `guardrailConfig`.
- [ ] Tool loops: every `tool_calls[].function.arguments` goes through
      `json.loads()`; results go back as `role:"tool"` with a string
      `content`.
- [ ] Streaming: `stream_options={"include_usage": True}` on Chat
      Completions; explicit handlers for reasoning deltas on Responses.
- [ ] Perf: p50/p95 TTFT within 20% of runtime baseline; p99 end-to-end
      latency within 30%.
- [ ] Rollback: feature-flag-controlled fallback to runtime for every
      migrated workload; rollback tested end-to-end.

## What we did *not* cover (and where to go next)

- **Server-side tools** on the Responses API (`type: "mcp"` with a Lambda
  `connector_id`) — touched on in Lab 2.2 but not wired end-to-end.
  See the Bedrock AgentCore workshop.
- **Fine-tuning** on Mantle (`CreateFineTuningJob`, `/v1/files`) — not
  covered; see the Mantle Migration Playbook §5 and §14.
- **Embeddings** — **not on Mantle**. Keep using `amazon.titan-embed-text-v2`
  or `cohere.embed-*` on `bedrock-runtime`.
- **Images / audio / realtime** — not on Mantle. Nova Canvas, Nova Reel,
  Nova Sonic stay on `bedrock-runtime`.
- **Batch inference** — not on Mantle. Use `StartAsyncInvoke` on runtime
  or fan-out via SQS/Lambda for Mantle.

## References

- [Amazon Bedrock Mantle overview](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [Mantle IAM actions / resources / condition keys](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrockpoweredbyawsmantle.html)
- [`AmazonBedrockMantleInferenceAccess` managed policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonBedrockMantleInferenceAccess.html)
- [`aws-bedrock-token-generator` on PyPI](https://pypi.org/project/aws-bedrock-token-generator/)
- [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Hugging Face `gbharti/finance-alpaca`](https://huggingface.co/datasets/gbharti/finance-alpaca)
