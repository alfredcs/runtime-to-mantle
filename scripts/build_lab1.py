"""Builds src/lab1/01_mantle_fundamentals.ipynb."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _nb import md, code, write_notebook


cells = [
    md(
        """# Lab 1 — Amazon Bedrock Mantle Fundamentals

**Duration:** ~30 min · **Level:** L200 · **Lab 1 of 4**

This notebook is the *entry point* to Amazon Bedrock Mantle. By the end, you
will have:

1. Listed the models available in your region with `GET /v1/models`.
2. Called `openai.gpt-oss-120b` through the **Chat Completions API**.
3. Called `anthropic.claude-opus-4-7` through the **Anthropic Messages API**.
4. Authenticated both ways — **SigV4** (pure IAM) and **Bearer token**
   (short-term, minted from your IAM session).
5. Constructed prompts with system messages and token budgets, and reserved
   output tokens with `max_tokens` / `max_output_tokens`.

This is the mental model you will reuse for the rest of the workshop:

```
┌─────────────────────────────────────────────────────────────────────┐
│            https://bedrock-mantle.{region}.api.aws                  │
├─────────────────────────────────────────────────────────────────────┤
│  /v1/models              ── GET         ── OpenAI SDK               │
│  /v1/chat/completions    ── POST        ── OpenAI SDK (all models)  │
│  /v1/responses           ── POST / GET  ── OpenAI SDK (stateful)    │
│  /anthropic/v1/messages  ── POST        ── Anthropic SDK (Claude)   │
└─────────────────────────────────────────────────────────────────────┘
```

> **If you hit `401 access_denied` on any cell below, see `getting_started.md`
> §2 — the `AmazonBedrockMantleInferenceAccess` managed policy is probably
> not attached to your IAM principal.**
"""
    ),
    md(
        """## 0. Before you begin

Run the next cell once. It:

- Reads `AWS_REGION` from your environment (falling back to `us-east-1`)
  and pins `AWS_DEFAULT_REGION` to match. Mantle has 13 supported regions;
  this workshop is tested in `us-east-1`.
- Verifies your AWS credentials.
- Imports the shared helpers under `src/common/`.

If any of these fail, **stop** and fix the environment before moving on —
every other lab depends on this working.
"""
    ),
    code(
        """import os
import sys
from pathlib import Path

# Make ``src/common/`` importable from any lab notebook.
ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

# Mantle is region-scoped. Bearer tokens minted in one region are rejected
# by the endpoint of another region, so we pin this before importing anything
# that talks to Mantle.
os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

import boto3

sts = boto3.client("sts")
identity = sts.get_caller_identity()
print("Region :", os.environ["AWS_REGION"])
print("Account:", identity["Account"])
print("Caller :", identity["Arn"])
"""
    ),
    md(
        """## 1. List available models

Mantle exposes an OpenAI-compatible **Models** endpoint at `GET /v1/models`.
This is the single source of truth for *which* models your account can call
on the Mantle endpoint in this region.

We call it two ways:

- Using the `openai` SDK with a **Bearer token** (the path you'll use for the
  rest of the workshop).
- Using `requests` + SigV4 (shows what the raw call looks like for services
  that need pure IAM, e.g. Go backends without a token-generator library).
"""
    ),
    code(
        """# 1a. OpenAI SDK + Bearer token (recommended for Python notebooks)
from src.common.mantle import openai_client, bearer_token

client = openai_client()                    # region picked from AWS_REGION
token = bearer_token()                      # short-lived, up to 12h

# Show the token shape (first 20 chars only) so you know what one looks like
# without leaking the full token into the notebook output.
print("Bearer token (prefix):", token[:20] + "...")
print("                length:", len(token))
"""
    ),
    code(
        """models = client.models.list()
ids = sorted({m.id for m in models.data})
print(f"Mantle exposes {len(ids)} model IDs in {os.environ['AWS_REGION']}:")
for mid in ids:
    print(" -", mid)
"""
    ),
    code(
        """# 1b. Same call via SigV4 — no bearer token needed.
# This is the pattern a Go service (no token-generator library) would use.
import requests, json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

creds = boto3.Session().get_credentials().get_frozen_credentials()
region = os.environ["AWS_REGION"]

url = f"https://bedrock-mantle.{region}.api.aws/v1/models"
req = AWSRequest(method="GET", url=url, data=b"")
# NOTE: the SigV4 service name is "bedrock" even though the IAM service prefix
# on Mantle is "bedrock-mantle". This is intentional and documented.
SigV4Auth(creds, "bedrock", region).add_auth(req)

resp = requests.get(url, headers=dict(req.headers.items()), timeout=30)
resp.raise_for_status()
sigv4_ids = sorted({m["id"] for m in resp.json()["data"]})
print("SigV4 call returned", len(sigv4_ids), "models (should match the Bearer call above).")
assert sigv4_ids == ids, "Bearer and SigV4 should return the same model list"
print("OK — SigV4 and Bearer agree.")
"""
    ),
    md(
        """### What just happened

Both calls landed at the same `GET /v1/models` endpoint. The only
difference is *how* the request was authenticated:

| Path | Auth header | Where the identity comes from |
|---|---|---|
| OpenAI SDK | `Authorization: Bearer <token>` | `aws-bedrock-token-generator` derives a short-term token from your IAM session |
| `requests` + `SigV4Auth` | `Authorization: AWS4-HMAC-SHA256 …` | Your IAM access key / secret / session |

Pick whichever fits your runtime: **Bearer** is friendliest for OpenAI-SDK
code, **SigV4** is friendliest for services that already sign every AWS call
(e.g. Go, long-running daemons, Lambda with IAM roles).
"""
    ),
    md(
        """## 2. Call `gpt-oss-120b` via Chat Completions

The Chat Completions surface is OpenAI-native at `/v1/chat/completions`.
For the most common case, you construct a `messages=[…]` array and a
`max_tokens` budget and you're done.
"""
    ),
    code(
        """from src.common.mantle import GPT_OSS_120B

resp = client.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[
        {"role": "system", "content": "You are a concise AWS trainer. Reply in <= 40 words."},
        {"role": "user",   "content": "Explain what Amazon Bedrock Mantle is, and why it exists."},
    ],
    max_tokens=200,
    temperature=0.2,
)

print("--- response ---")
print(resp.choices[0].message.content.strip())
print()
print("--- usage ---")
print(f"prompt_tokens     = {resp.usage.prompt_tokens}")
print(f"completion_tokens = {resp.usage.completion_tokens}")
print(f"finish_reason     = {resp.choices[0].finish_reason}")
"""
    ),
    md(
        """### Token budgeting — why `max_tokens` matters

`max_tokens` is not just a safety net; it is the *reservation* Mantle uses to
schedule your request on the distributed inference engine. Two practical
consequences:

- **Set it as low as your use case allows.** An overly generous `max_tokens`
  reserves capacity you may not spend, but still counts against the
  **Output TPM** pool for Claude 4.7+ (2M/min on Mantle, separate from input,
  no burndown).
- **Check `finish_reason`.** If it's `length`, the model stopped because it
  hit `max_tokens`. Raise the budget (or rephrase the prompt).

The cell below shows both cases.
"""
    ),
    code(
        """short = client.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[{"role": "user", "content": "Write a 500-word essay about Nitro."}],
    max_tokens=40,           # deliberately too small — watch finish_reason
    temperature=0.2,
)
print("finish_reason:", short.choices[0].finish_reason)   # expect: length
print("completion   :", repr(short.choices[0].message.content[:120]))
"""
    ),
    md(
        """## 3. Call `Claude Opus 4.7` via the Anthropic Messages API

Claude Opus 4.7 is **only** exposed on the Anthropic-native path at
`/anthropic/v1/messages`. Do **not** try to reach it through
`/v1/chat/completions` — that surface is OpenAI-compatible and Claude is not
listed there.

The Anthropic SDK ships a first-party client for this path:
`AnthropicBedrockMantle`. It handles auth (SigV4 *or* the
`AWS_BEARER_TOKEN_BEDROCK` env var) and the Anthropic-style URL for you.
"""
    ),
    code(
        """from src.common.mantle import anthropic_client, CLAUDE_OPUS_47

anth = anthropic_client()

msg = anth.messages.create(
    model=CLAUDE_OPUS_47,
    max_tokens=300,
    system="You are a concise AWS trainer. Reply in <= 40 words.",
    messages=[
        {"role": "user", "content": "Explain Amazon Bedrock Mantle in plain English."}
    ],
    # NOTE: Opus 4.7 rejects temperature/top_p/top_k — do NOT include them here.
)

print("--- response ---")
print(msg.content[0].text.strip())
print()
print("--- usage ---")
print(f"input_tokens  = {msg.usage.input_tokens}")
print(f"output_tokens = {msg.usage.output_tokens}")
print(f"stop_reason   = {msg.stop_reason}")
"""
    ),
    md(
        """### Claude Opus 4.7's parameter quirks

Opus 4.7 is unusually strict about which parameters it accepts:

- **Rejects** `temperature`, `top_p`, `top_k` — even when `thinking` is off.
  Sending them returns `400`. Steer behaviour through prompting instead.
- **`thinking.type: "adaptive"`** is the only supported thinking mode
  (Opus 4.5 / 4.6's `enabled` + `budget_tokens` shape is rejected).

The workshop's shared helper `src/common/mantle.py` does **not** silently
strip these fields; it's your application's job to remember. Lab 3 shows an
adapter pattern that does the stripping automatically.
"""
    ),
    md(
        """## 4. Side-by-side — same prompt, three surfaces

Same question, three Mantle paths. You should see answers of comparable
quality but in three structurally different envelopes.
"""
    ),
    code(
        """PROMPT = "In one sentence, what is the difference between a runtime and a mantle?"

# Chat Completions — gpt-oss-120b
cc = client.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[{"role": "user", "content": PROMPT}],
    max_tokens=80,
)

# Responses API — gpt-oss-120b (stateful-ready)
rs = client.responses.create(
    model=GPT_OSS_120B,
    input=PROMPT,
    max_output_tokens=80,
)

# Anthropic Messages — Claude Opus 4.7
ms = anth.messages.create(
    model=CLAUDE_OPUS_47,
    max_tokens=120,
    messages=[{"role": "user", "content": PROMPT}],
)

print("Chat Completions (gpt-oss-120b):")
print(" ", cc.choices[0].message.content.strip(), "\\n")

print("Responses API   (gpt-oss-120b):")
print(" ", rs.output_text.strip(), "\\n")

print("Messages        (Claude Opus 4.7):")
print(" ", ms.content[0].text.strip())
"""
    ),
    md(
        """### Where the data lives in each response

| Surface | Primary text | Input tokens | Output tokens | Stop reason |
|---|---|---|---|---|
| Chat Completions | `choices[0].message.content` | `usage.prompt_tokens` | `usage.completion_tokens` | `choices[0].finish_reason` |
| Responses API | `output_text` (or walk `output[]`) | `usage.input_tokens` | `usage.output_tokens` | walk `output[]` + `incomplete_details` |
| Anthropic Messages | `content[0].text` | `usage.input_tokens` | `usage.output_tokens` | `stop_reason` |

This is the single biggest source of migration pain when you port code from
Converse — the *shape* of the response object is different on every surface.
We'll lean on this table for the rest of the workshop.
"""
    ),
    md(
        """## 5. Authenticating long-term workloads

You've seen two auth paths: **SigV4** (pure IAM) and **short-term Bearer
tokens** (minted on demand, ≤ 12 h, inherits caller IAM).

There is a third path — **long-term Bedrock API keys** — used for CI,
daemons, or any workload that cannot safely call
`aws-bedrock-token-generator` periodically. These keys:

- Are created with `aws iam create-service-specific-credential
  --service-name bedrock.amazonaws.com`.
- Provision a **dedicated IAM user** per key (they're not minted against
  your own session).
- Rotate via `--credential-age-days` instead of STS expiry.

Because they create IAM users, treat them the way you treat real IAM access
keys: **store in Secrets Manager, rotate on a schedule, never commit**.

We do **not** create one in this notebook — they leave a durable footprint
you have to clean up. The CLI for reference:

```bash
aws iam create-service-specific-credential \\
    --user-name    <iam-user> \\
    --service-name bedrock.amazonaws.com \\
    --credential-age-days 90
```
"""
    ),
    md(
        """## 6. Projects and the cost-attribution model

Mantle replaces Bedrock Runtime's *Inference Profiles* with a **Projects**
primitive, exposed at `/v1/organization/projects`. A project is:

- An IAM-scoped *container* for inference calls (tag via
  `bedrock-mantle:ProjectArn` condition key).
- A cost-attribution boundary (Cost Explorer groups usage by project ARN).
- A quota boundary (you can place a per-project RPM / TPM throttle).

The default project ARN is `arn:aws:bedrock-mantle:{region}:{account}:project/default`
— calls without an explicit project ARN land there. Lab 4 shows how to
reference an application-scoped project for cost isolation.
"""
    ),
    md(
        """## 7. Recap

- Mantle is a single endpoint (`bedrock-mantle.{region}.api.aws`) with three
  surfaces: `/v1/chat/completions`, `/v1/responses`, `/anthropic/v1/messages`.
- You can reach every surface with **SigV4** or **Bearer tokens**. The
  OpenAI SDK only supports Bearer; the Anthropic SDK supports both.
- Region matters — tokens are region-scoped. Always pin `AWS_REGION` before
  minting one.
- Each surface has its own response envelope. Plan for three-way branching
  on `content`, `usage`, and `stop_reason` if you call more than one.
- `max_tokens` is a *reservation* that counts against Mantle's TPM
  (Claude 4.7+ output side). Pick it deliberately.
- Projects are Mantle's cost / quota / IAM boundary. Default is `/default`.

**Next:** Lab 2 covers streaming, tool calling, prefix caching, and a first
look at stateful conversations on the Responses API.
"""
    ),
]


if __name__ == "__main__":
    out = Path(__file__).parent.parent / "src" / "lab1" / "01_mantle_fundamentals.ipynb"
    write_notebook(out, cells)
    print(f"wrote {out}")
