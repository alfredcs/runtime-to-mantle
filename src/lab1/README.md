# Lab 1 — Amazon Bedrock Mantle Fundamentals

**Notebook:** `01_mantle_fundamentals.ipynb`
**Duration:** ~30 min · **Level:** L200 · **Lab 1 of 4**

## Goals

- Discover available models via `GET /v1/models`.
- Call `openai.gpt-oss-120b` through Chat Completions.
- Call `anthropic.claude-opus-4-7` through the Anthropic Messages API.
- Authenticate with both **SigV4** (pure IAM) and **Bearer tokens**
  (short-lived, minted by `aws-bedrock-token-generator`).
- Understand `max_tokens` as a reservation primitive on the distributed
  inference engine.

## Prerequisites

- Python deps from `../../requirements.txt` installed.
- IAM principal with the `AmazonBedrockMantleInferenceAccess` AWS-managed
  policy (see `../../getting_started.md` §2).
- Model access granted for `openai.gpt-oss-120b`, `anthropic.claude-opus-4-7`
  in `us-east-1`.

## Run it

```bash
cd src/lab1
jupyter lab 01_mantle_fundamentals.ipynb
```
