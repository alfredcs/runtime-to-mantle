"""Builds the four notebooks in src/lab3/."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _nb import md, code, write_notebook


# ---------------------------------------------------------------------------
# Lab 3.1 — API/SDK call differences
# ---------------------------------------------------------------------------

diff_cells = [
    md(
        """# Lab 3.1 — API/SDK Call Differences (Runtime vs Mantle)

**Duration:** ~8 min · **Level:** L300 · **Lab 3 of 4 — part 1/4**

You're here because you have production code that calls **Amazon Bedrock
Runtime** (`bedrock-runtime.{region}.amazonaws.com`) — most likely via the
`Converse` or `InvokeModel` operations — and you need to migrate those call
sites to **Mantle** (`bedrock-mantle.{region}.api.aws`).

This notebook runs the *same prompt* through:

1. `bedrock-runtime` `Converse` — the source of truth you're migrating from.
2. Mantle **Chat Completions** — the most common target for
   `gpt-oss`, Mistral, GLM, Qwen, MiniMax, DeepSeek, …
3. Mantle **Anthropic Messages** — the target for Claude Opus 4.7 /
   Haiku 4.5 / Mythos.

After you see the three shapes side-by-side, you'll know exactly which
response fields change and where.

> **Prerequisite:** your account must have **both** runtime model access
> (`mistral.mistral-large-2407-v1:0` or a similar Converse-capable model —
> we fall back gracefully if absent) *and* Mantle access to
> `openai.gpt-oss-120b` + `anthropic.claude-opus-4-7`.
"""
    ),
    code(
        """import os, sys, json
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

import boto3
from botocore.exceptions import ClientError
from src.common.mantle import (
    openai_client, anthropic_client,
    GPT_OSS_120B, CLAUDE_OPUS_47,
)

runtime = boto3.client("bedrock-runtime", region_name=os.environ["AWS_REGION"])
mantle_oai = openai_client()
mantle_anth = anthropic_client()

PROMPT = "In three words, what is AWS Nitro?"
print("ready")
"""
    ),
    md(
        """## 1. Before — `bedrock-runtime` Converse

Converse is the unified chat API on the legacy endpoint. Key shapes:

- `messages=[{role, content:[{text: "..."}]}]` (a list of **content blocks**,
  not a plain string).
- `system=[{text: "..."}]` as a sibling field.
- `inferenceConfig={"maxTokens": ..., "temperature": ..., "topP": ...}`.
- Response at `output.message.content[0].text`.
- Token counts at `usage.inputTokens` / `usage.outputTokens`.
- `stopReason ∈ {end_turn, tool_use, max_tokens, stop_sequence, guardrail_intervened, content_filtered}`.
"""
    ),
    code(
        """# Use a stable Claude on runtime as the source baseline. If your account
# doesn't have this model, substitute any Converse-capable model ID.
RUNTIME_MODEL_CANDIDATES = [
    "anthropic.claude-haiku-4-5",
    "anthropic.claude-opus-4-7",                 # some accounts route Opus 4.7 here too
    "mistral.mistral-large-2407-v1:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",  # broadly-accessible fallback
]

runtime_resp = None
chosen = None
for mid in RUNTIME_MODEL_CANDIDATES:
    try:
        runtime_resp = runtime.converse(
            modelId=mid,
            system=[{"text": "Answer in exactly three words."}],
            messages=[{"role": "user", "content": [{"text": PROMPT}]}],
            inferenceConfig={"maxTokens": 40, "temperature": 0.2, "topP": 0.9},
        )
        chosen = mid
        break
    except ClientError as e:
        print(f"  {mid}: {e.response['Error']['Code']}")
        continue

if runtime_resp is None:
    print("⚠️  No Converse-capable model available — skipping runtime baseline.")
else:
    print(f"used runtime model: {chosen}")
    text = runtime_resp["output"]["message"]["content"][0]["text"]
    u = runtime_resp["usage"]
    print(f"text         : {text!r}")
    print(f"inputTokens  : {u['inputTokens']}")
    print(f"outputTokens : {u['outputTokens']}")
    print(f"stopReason   : {runtime_resp['stopReason']}")
"""
    ),
    md(
        """## 2. After — Mantle **Chat Completions**

Shape changes:

- `messages=[{role, content: str}]` — plain strings, not content blocks.
- No `system` field; the system message is just `role: "system"` in
  `messages`.
- Top-level `max_tokens`, `temperature`, `top_p` (not nested).
- Response at `choices[0].message.content` — a plain string.
- Tokens at `usage.prompt_tokens` / `usage.completion_tokens`.
- `finish_reason ∈ {stop, tool_calls, length, content_filter}`. (The
  legacy `function_call` value is only emitted by the deprecated
  single-function API, not the current `tools`-style calls.)
"""
    ),
    code(
        """cc = mantle_oai.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[
        {"role": "system", "content": "Answer in exactly three words."},
        {"role": "user",   "content": PROMPT},
    ],
    max_tokens=40,
    temperature=0.2,
    top_p=0.9,
)
text = cc.choices[0].message.content
print(f"text              : {text!r}")
print(f"prompt_tokens     : {cc.usage.prompt_tokens}")
print(f"completion_tokens : {cc.usage.completion_tokens}")
print(f"finish_reason     : {cc.choices[0].finish_reason}")
"""
    ),
    md(
        """## 3. After — Mantle **Anthropic Messages**

Shape changes (vs Converse):

- `system="..."` is a *string*, not a list of content blocks.
- `messages=[{role, content: str_or_blocks}]` — strings are fine for plain
  text; blocks (`[{type:"text", ...}]`) are required for images / docs.
- Top-level `max_tokens` (not nested).
- Response at `content[0].text`.
- Tokens at `usage.input_tokens` / `usage.output_tokens`.
- `stop_reason ∈ {end_turn, tool_use, max_tokens, stop_sequence, refusal}`.
"""
    ),
    code(
        """msg = mantle_anth.messages.create(
    model=CLAUDE_OPUS_47,
    max_tokens=40,
    system="Answer in exactly three words.",
    messages=[{"role": "user", "content": PROMPT}],
    # Opus 4.7: NO temperature / top_p / top_k.
)
print(f"text         : {msg.content[0].text!r}")
print(f"input_tokens : {msg.usage.input_tokens}")
print(f"output_tokens: {msg.usage.output_tokens}")
print(f"stop_reason  : {msg.stop_reason}")
"""
    ),
    md(
        """## 4. The "one table to rule them all"

| Concept | Converse (runtime) | Chat Completions (Mantle) | Anthropic Messages (Mantle) |
|---|---|---|---|
| Messages container | `messages: [{role, content:[{text}]}]` | `messages: [{role, content: "str"}]` | `messages: [{role, content: "str" or [...]}]` |
| System prompt | `system: [{text:"..."}]` | `role:"system"` message | `system: "..."` (sibling) |
| Max output tokens | `inferenceConfig.maxTokens` | `max_tokens` | `max_tokens` |
| Temperature | `inferenceConfig.temperature` | `temperature` | `temperature` |
| Top-p | `inferenceConfig.topP` | `top_p` | `top_p` |
| Provider-extra params | `additionalModelRequestFields` | `extra_body` | native fields (`thinking`) |
| Primary text | `output.message.content[0].text` | `choices[0].message.content` | `content[0].text` |
| Input tokens | `usage.inputTokens` | `usage.prompt_tokens` | `usage.input_tokens` |
| Output tokens | `usage.outputTokens` | `usage.completion_tokens` | `usage.output_tokens` |
| Stop reason | `stopReason` | `finish_reason` | `stop_reason` |

If you only memorise one thing from this lab: **every response field name
changes across the three surfaces.** Build a provider-abstraction layer
that normalises them or you'll debug this forever.
"""
    ),
    md(
        """## 5. A minimal provider abstraction

A rough shape you can grow into production:
"""
    ),
    code(
        """from dataclasses import dataclass

@dataclass
class NormalizedReply:
    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    surface: str           # "converse" / "chat_completions" / "messages"

def from_converse(r) -> NormalizedReply:
    return NormalizedReply(
        text=r["output"]["message"]["content"][0]["text"],
        input_tokens=r["usage"]["inputTokens"],
        output_tokens=r["usage"]["outputTokens"],
        stop_reason=r["stopReason"],
        surface="converse",
    )

def from_chat_completions(r) -> NormalizedReply:
    return NormalizedReply(
        text=r.choices[0].message.content,
        input_tokens=r.usage.prompt_tokens,
        output_tokens=r.usage.completion_tokens,
        stop_reason=r.choices[0].finish_reason,
        surface="chat_completions",
    )

def from_messages(r) -> NormalizedReply:
    return NormalizedReply(
        text=next((b.text for b in r.content if b.type == "text"), ""),
        input_tokens=r.usage.input_tokens,
        output_tokens=r.usage.output_tokens,
        stop_reason=r.stop_reason,
        surface="messages",
    )

normalized = [
    from_chat_completions(cc),
    from_messages(msg),
]
if runtime_resp is not None:
    normalized.insert(0, from_converse(runtime_resp))

for n in normalized:
    print(f"[{n.surface:>18}] in={n.input_tokens} out={n.output_tokens} stop={n.stop_reason} text={n.text!r}")
"""
    ),
    md(
        """## 6. What's next

The remaining Lab 3 notebooks go deep on each migration axis:

- `02_auth_security_migration.ipynb` — IAM policies, Bearer tokens, CloudTrail.
- `03_tools_and_caching_migration.ipynb` — Converse tool loop → Chat
  Completions tool loop, and caching diffs.
- `04_perf_eval.ipynb` — a runnable TTFT / tokens-per-second benchmark.
"""
    ),
]


# ---------------------------------------------------------------------------
# Lab 3.2 — Auth + security migration
# ---------------------------------------------------------------------------

auth_cells = [
    md(
        """# Lab 3.2 — Authentication and Security Migration

**Duration:** ~7 min · **Level:** L300 · **Lab 3 of 4 — part 2/4**

Migrating the auth layer is where most teams get surprised. Key changes:

1. **IAM service prefix flips from `bedrock` to `bedrock-mantle`.**
   `AmazonBedrockFullAccess` does **not** grant Mantle access.
2. **Bearer tokens are added alongside SigV4.** They don't replace SigV4 —
   they sit next to it, with their own IAM, rotation, and CloudTrail story.
3. **Project ARNs** become a first-class IAM resource.
4. **Guardrails** are no longer a native request field — you call
   `ApplyGuardrail` separately or use `extra_headers`.

This notebook walks you through each change with runnable snippets.
"""
    ),
    code(
        """import os, sys, json
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

import boto3
sts = boto3.client("sts")
iam = boto3.client("iam")
identity = sts.get_caller_identity()
print("caller:", identity["Arn"])
"""
    ),
    md(
        """## 1. IAM policy — Before

A typical runtime policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream",
      "bedrock:Converse",
      "bedrock:ConverseStream"
    ],
    "Resource": "arn:aws:bedrock:us-east-1::foundation-model/*"
  }]
}
```

Every `Action` is under the `bedrock:` prefix. Resource ARNs target
`foundation-model/*`.
"""
    ),
    md(
        """## 1b. IAM policy — After (Mantle)

The Mantle equivalent. Note the service prefix (`bedrock-mantle`), the
new resource shape (`project/*`), and `CallWithBearerToken` — a permission-only
action that has to be on `Resource: "*"`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "MantleInference",
      "Effect": "Allow",
      "Action": [
        "bedrock-mantle:CreateInference",
        "bedrock-mantle:GetInference",
        "bedrock-mantle:CancelInference",
        "bedrock-mantle:GetModel",
        "bedrock-mantle:ListModels",
        "bedrock-mantle:GetProject",
        "bedrock-mantle:ListProjects"
      ],
      "Resource": "arn:aws:bedrock-mantle:*:*:project/*",
      "Condition": {
        "StringEquals": {
          "bedrock-mantle:Model": [
            "openai.gpt-oss-120b",
            "anthropic.claude-opus-4-7",
            "anthropic.claude-haiku-4-5"
          ]
        }
      }
    },
    {
      "Sid": "MantleCallWithBearerToken",
      "Effect": "Allow",
      "Action": "bedrock-mantle:CallWithBearerToken",
      "Resource": "*"
    }
  ]
}
```

The `bedrock-mantle:Model` condition key lets you list *exactly* which
models this role may invoke — a much finer grain than runtime's
`foundation-model/*` wildcard.
"""
    ),
    code(
        """# Who am I? List the policies attached to my current principal so we can
# see whether we already have AmazonBedrockMantleInferenceAccess.
arn = identity["Arn"]

def my_role_name():
    # role-ARN shape: arn:aws:sts::<acct>:assumed-role/<role-name>/<session>
    if "assumed-role" in arn:
        return arn.split("/")[1]
    return None

rname = my_role_name()
if rname:
    try:
        attached = iam.list_attached_role_policies(RoleName=rname)["AttachedPolicies"]
        inline   = iam.list_role_policies(RoleName=rname)["PolicyNames"]
        print(f"role: {rname}")
        print("  attached:", [p["PolicyName"] for p in attached])
        print("  inline  :", inline)
    except Exception as e:
        print(f"(skipping IAM lookup: {e})")
else:
    print("not an assumed-role — skipping IAM lookup")
"""
    ),
    md(
        """## 2. The three auth modes side-by-side

| Mode | Who issues | Lifetime | Typical workload | Pitfall |
|---|---|---|---|---|
| **SigV4 (runtime path)** | STS/IAM | Session (usually < 1h) | boto3 callers today | None — keep using it for runtime |
| **SigV4 (Mantle path)** | STS/IAM | Session | Go services, Lambdas that sign every call | SigV4 service name stays `bedrock`, **not** `bedrock-mantle` |
| **Short-term Bearer** | `aws-bedrock-token-generator` (from caller's IAM session) | ≤ 12 h | OpenAI SDK callers, notebooks | Region-scoped. Mint in the wrong region → 401 |
| **Long-term Bedrock API key** | `aws iam create-service-specific-credential --service-name bedrock.amazonaws.com` | Configurable (`--credential-age-days`) | CI, daemons | Creates a **dedicated IAM user** per key → governance sprawl |

The key is to **pick one per environment** and enforce it with an SCP.
Don't let one codebase mix short-term tokens, long-term keys, and SigV4 on
the same request path — your CloudTrail becomes impossible to reason about.
"""
    ),
    md(
        """## 3. Cold-side test: can I actually hit Mantle?

This is the one-liner that surfaces most permission issues. If it prints
a non-empty list, you're good. If it raises `AccessDeniedException` on
`bedrock-mantle:ListModels`, re-read §1b.
"""
    ),
    code(
        """from src.common.mantle import openai_client

mc = openai_client()
model_ids = [m.id for m in mc.models.list().data]
print(f"I can see {len(model_ids)} models.")
print("sample:", model_ids[:5])
"""
    ),
    md(
        """## 4. Guardrails — the hidden migration

On runtime, you attach a guardrail with a *first-class* request field:

```python
runtime.converse(
    modelId="...",
    messages=[...],
    guardrailConfig={"guardrailIdentifier": "..", "guardrailVersion": "1"},
)
```

On Mantle, there is **no `guardrailConfig` field**. You have three options:

1. **Out-of-band**: call `boto3.client("bedrock-runtime").apply_guardrail(…)`
   before / after your Mantle call. Two network round-trips per turn, but
   zero Mantle-side changes.
2. **`extra_body` / `extra_headers`**: some Mantle deployments expose
   guardrail IDs through provider-extension fields. Verify per model card.
3. **Wrap your client.** Put Mantle behind an adapter that owns the
   guardrail lifecycle. This is what most enterprises do in production.

The cell below demonstrates option 1.
"""
    ),
    code(
        """# Illustrative. Supply a real guardrail ID to make this actually call AWS.
GUARDRAIL_ID = "REPLACE_ME"
TEXT = "Is drug X effective for disease Y? (user input)"

runtime_client = boto3.client("bedrock-runtime")
if GUARDRAIL_ID == "REPLACE_ME":
    print("(set GUARDRAIL_ID to a real guardrail in your account to run this cell.)")
else:
    gr = runtime_client.apply_guardrail(
        guardrailIdentifier=GUARDRAIL_ID,
        guardrailVersion="DRAFT",
        source="INPUT",
        content=[{"text": {"text": TEXT}}],
    )
    if gr["action"] == "GUARDRAIL_INTERVENED":
        print("blocked by guardrail:", gr["outputs"][0]["text"]["text"])
    else:
        print("allowed — call Mantle here")
"""
    ),
    md(
        """## 5. CloudTrail

Mantle emits its own events. A few things to remember:

- Event source: `bedrock-mantle.amazonaws.com`.
- **Add a new Event Selector** to your existing trails — they don't
  auto-extend to the new service.
- Every Bearer-token call logs the originating principal under
  `userIdentity.arn` (short-term) or the dedicated IAM user (long-term).
- If a Bearer-token call 401s on the **client** side, you won't see a
  CloudTrail event at all (the request didn't make it to the service).
- `CallWithBearerToken` is what you'll most commonly see `AccessDenied` on
  during rollouts. Add a CloudWatch metric filter for it.

Add this metric filter to flag noisy auth issues:

```bash
aws logs put-metric-filter \\
  --log-group-name /aws/cloudtrail/your-trail \\
  --filter-name MantleBearerAccessDenied \\
  --filter-pattern '{ $.eventName = "CallWithBearerToken" && $.errorCode = "AccessDenied*" }' \\
  --metric-transformations \\
      metricName=MantleBearerAccessDenied,metricNamespace=YourOrg/Mantle,metricValue=1
```
"""
    ),
    md(
        """## 6. Migration checklist

- [ ] Decide policy strategy: AWS-managed (`AmazonBedrockMantleInferenceAccess`)
      vs custom inline. Default to managed for app roles, custom for admin.
- [ ] Decide key strategy: short-term Bearer in prod, long-term key in CI.
- [ ] Store long-term keys in Secrets Manager; rotate via Lambda.
- [ ] Add CloudTrail event selectors for `bedrock-mantle` events.
- [ ] Replace `guardrailConfig` with out-of-band `ApplyGuardrail` (or a
      wrapper).
- [ ] Add SCPs to restrict which accounts / regions can use Mantle.
- [ ] Verify VPC endpoint availability
      (`com.amazonaws.{region}.bedrock-mantle` — **verify** service name
      against latest docs per your region).
"""
    ),
]


# ---------------------------------------------------------------------------
# Lab 3.3 — Tool + caching migration
# ---------------------------------------------------------------------------

tool_mig_cells = [
    md(
        """# Lab 3.3 — Tool Loops and Caching: Converse → Mantle

**Duration:** ~8 min · **Level:** L300 · **Lab 3 of 4 — part 3/4**

We'll take a full working Converse tool loop and migrate it, step by step,
to Mantle Chat Completions. The goal is a diff you can copy into your own
codebase.
"""
    ),
    code(
        """import os, sys, json
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

import boto3
from src.common.mantle import openai_client, GPT_OSS_120B

runtime = boto3.client("bedrock-runtime")
mantle  = openai_client()

# Mini "tool" shared across both runs.
_PRICES = {"p1": 899, "p2": 1199, "p3": 2399}
def get_price(product_id: str) -> dict:
    if product_id not in _PRICES:
        return {"error": f"unknown product {product_id!r}"}
    return {"product_id": product_id, "usd": _PRICES[product_id]}
"""
    ),
    md(
        """## 1. Before — Converse tool loop

Converse shape:

- Tools declared under `toolConfig.tools[].toolSpec`.
- `toolChoice={"auto": {}}` / `{"any": {}}` / `{"tool": {"name": "..."}}`.
- Tool calls arrive as `toolUse` blocks with **`input`** already a dict.
- Tool results go back in a `user` message as `toolResult` blocks.
- Loop terminates when `stopReason != "tool_use"`.
"""
    ),
    code(
        """CONVERSE_MODEL_CANDIDATES = [
    "anthropic.claude-haiku-4-5",
    "mistral.mistral-large-2407-v1:0",
    "anthropic.claude-3-5-haiku-20241022-v1:0",
]

converse_messages = [{
    "role": "user",
    "content": [{"text": "What do products p1 and p3 cost?"}]
}]

converse_ok = False
for cand in CONVERSE_MODEL_CANDIDATES:
    try:
        for _ in range(5):
            r = runtime.converse(
                modelId=cand,
                messages=converse_messages,
                toolConfig={
                    "tools": [{
                        "toolSpec": {
                            "name": "get_price",
                            "description": "Look up a product's USD price.",
                            "inputSchema": {"json": {
                                "type": "object",
                                "properties": {"product_id": {"type": "string"}},
                                "required": ["product_id"],
                            }},
                        }
                    }],
                    "toolChoice": {"auto": {}},
                },
                inferenceConfig={"maxTokens": 400, "temperature": 0.2},
            )
            assistant = r["output"]["message"]
            converse_messages.append(assistant)
            if r["stopReason"] != "tool_use":
                text = next((b["text"] for b in assistant["content"] if "text" in b), "")
                print(f"[{cand}] final:", text)
                converse_ok = True
                break
            results = []
            for b in assistant["content"]:
                if "toolUse" not in b:
                    continue
                tu = b["toolUse"]
                out = get_price(**tu["input"])   # input is already a dict
                results.append({"toolResult": {
                    "toolUseId": tu["toolUseId"],
                    "content": [{"json": out}],
                    "status": "success",
                }})
            converse_messages.append({"role": "user", "content": results})
        if converse_ok:
            break
    except Exception as e:
        print(f"  {cand}: {e.__class__.__name__}")

if not converse_ok:
    print("⚠️  No Converse model available — skipping baseline.")
"""
    ),
    md(
        """## 2. After — Chat Completions tool loop

Spot the diff:

- Tool wrapper changes (`toolSpec` → `function`).
- `tool_choice` vocabulary changes (`{"any": {}}` → `"required"`).
- **`tool_calls[].function.arguments` is a JSON string** — you must
  `json.loads()` it.
- Tool results go back as a `role: "tool"` message with `tool_call_id`
  and **string** content.
- Loop terminates when `finish_reason != "tool_calls"`.
"""
    ),
    code(
        """cc_tools = [{
    "type": "function",
    "function": {
        "name": "get_price",
        "description": "Look up a product's USD price.",
        "parameters": {
            "type": "object",
            "properties": {"product_id": {"type": "string"}},
            "required": ["product_id"],
            "additionalProperties": False,
        },
    },
}]

cc_messages = [{"role": "user", "content": "What do products p1 and p3 cost?"}]

for _ in range(5):
    r = mantle.chat.completions.create(
        model=GPT_OSS_120B,
        messages=cc_messages,
        tools=cc_tools,
        tool_choice="auto",
        max_tokens=400,
        temperature=0.2,
    )
    msg = r.choices[0].message
    assistant_turn = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        assistant_turn["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
    cc_messages.append(assistant_turn)
    if r.choices[0].finish_reason != "tool_calls":
        print("final:", msg.content)
        break
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)     # STRING → dict
        out  = get_price(**args)
        cc_messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(out),              # STRING
        })
else:
    print(f"loop hit iteration cap without terminating")
"""
    ),
    md(
        """## 3. The migration diff — line-by-line

| Converse line | Chat Completions replacement |
|---|---|
| `toolConfig={"tools":[...], "toolChoice":{"auto":{}}}` | `tools=[...], tool_choice="auto"` |
| `"toolSpec": {"inputSchema": {"json": {...}}}` | `"function": {"parameters": {...}}` |
| `{"toolChoice": {"any": {}}}` | `tool_choice="required"` |
| `{"toolChoice": {"tool": {"name": "x"}}}` | `tool_choice={"type":"function","function":{"name":"x"}}` |
| `stopReason == "tool_use"` | `finish_reason == "tool_calls"` |
| `toolUse["input"]` (dict) | `json.loads(tc.function.arguments)` (string → dict) |
| `{"toolResult":{"toolUseId":…,"content":[{"json":…}]}}` in a **user** msg | `{"role":"tool","tool_call_id":…,"content": json.dumps(…)}` |
| Rich content blocks (image/doc/JSON) in tool results | **String only** — lossy; serialize carefully |

Keep this table open when you're migrating a codebase. Every row is a
place where the compiler won't save you — behaviour will silently differ.
"""
    ),
    md(
        """## 4. Caching — `additionalModelRequestFields` → `extra_body`

Converse uses `additionalModelRequestFields` to pass provider-specific
extensions. On Mantle, the equivalent is `extra_body`. Example:
"""
    ),
    code(
        """# Before (Converse, illustrative — don't run unless your model supports it):
#
# runtime.converse(
#     modelId="anthropic.claude-sonnet-4-20250514-v1:0",
#     ...,
#     additionalModelRequestFields={"thinking": {"type": "enabled", "budget_tokens": 1024}},
# )

# After (Mantle Chat Completions):
r = mantle.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[{"role": "user", "content": "Pick a number and explain."}],
    max_tokens=60,
    extra_body={
        "cache_salt": "migration-demo-v1",      # prefix-cache affinity hint
        # Other provider-extension fields go here. Availability is per-model;
        # verify against the model card before committing to a flag. Examples:
        #   "thinking": {"type": "adaptive"}      # Claude extended thinking
        #   "reasoning": {"effort": "medium"}    # OpenAI reasoning models
    },
)
print(r.choices[0].message.content.strip())
"""
    ),
    md(
        """## 5. Checklist

When you touch a Converse tool loop in production code, do this *in order*:

- [ ] Build a local unit test against the **current** Converse shape — lock
      it in as the baseline.
- [ ] Migrate the schema wrapper.
- [ ] Migrate the `toolChoice` → `tool_choice` mapping.
- [ ] Add `json.loads()` around every `tool_calls[].function.arguments`.
- [ ] Switch the tool-result message to `role:"tool"` + `tool_call_id`.
- [ ] Flatten rich tool-result content to strings.
- [ ] Update the loop termination predicate.
- [ ] Migrate `additionalModelRequestFields` → `extra_body`.
- [ ] Re-run the unit test — should still pass (same output given same input).
- [ ] Shadow-run the new loop against prod traffic for 48 h before cutover.
"""
    ),
]


# ---------------------------------------------------------------------------
# Lab 3.4 — Perf eval (TTFT / tokens/s)
# ---------------------------------------------------------------------------

perf_cells = [
    md(
        """# Lab 3.4 — Performance Evaluation: Runtime vs Mantle

**Duration:** ~7 min · **Level:** L300 · **Lab 3 of 4 — part 4/4**

We measure:

1. **TTFT (time-to-first-token)** — how long before the first visible byte.
2. **Tokens per second** — streaming throughput in the middle of the stream.
3. **End-to-end latency** for the full streamed completion.

This notebook is intentionally small — 10 samples per endpoint — so it
finishes in under a minute. For a real migration, increase `N_SAMPLES`
to 500+ per model × region and collect p50 / p95 / p99 per the playbook §8.
"""
    ),
    code(
        """import os, sys, time, statistics
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

import boto3
from src.common.mantle import openai_client, GPT_OSS_120B

runtime = boto3.client("bedrock-runtime")
mantle  = openai_client()

N_SAMPLES = 10
PROMPT = "Write a single 40-word paragraph about the AWS Nitro hypervisor."
MAX_OUT = 80
"""
    ),
    md(
        """## 1. Benchmark helper — Mantle Chat Completions (streaming)

Returns `(ttft_seconds, tokens_per_second, total_seconds)`.
"""
    ),
    code(
        """def bench_mantle_chat(model: str) -> tuple[float, float, float]:
    t0 = time.time()
    ttft = None
    frags = 0
    stream = mantle.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        max_tokens=MAX_OUT,
        stream=True,
        stream_options={"include_usage": True},
    )
    last = t0
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content:
            if ttft is None:
                ttft = time.time() - t0
            frags += 1
            last = time.time()
    total = time.time() - t0
    stream_dur = max(last - (t0 + (ttft or 0)), 1e-6)
    tps = frags / stream_dur
    return ttft or 0.0, tps, total
"""
    ),
    md(
        """## 2. Benchmark helper — Runtime ConverseStream

The runtime path yields structured `contentBlockDelta` events. We count each
`text` delta as a "fragment" — it's apples-to-apples with Mantle's
`delta.content` fragments for ordering / count purposes.
"""
    ),
    code(
        """def bench_runtime_converse_stream(model: str) -> tuple[float, float, float]:
    t0 = time.time()
    ttft = None
    frags = 0
    resp = runtime.converse_stream(
        modelId=model,
        messages=[{"role": "user", "content": [{"text": PROMPT}]}],
        inferenceConfig={"maxTokens": MAX_OUT, "temperature": 0.2},
    )
    last = t0
    for event in resp["stream"]:
        if "contentBlockDelta" in event:
            delta = event["contentBlockDelta"].get("delta", {})
            if "text" in delta:
                if ttft is None:
                    ttft = time.time() - t0
                frags += 1
                last = time.time()
    total = time.time() - t0
    stream_dur = max(last - (t0 + (ttft or 0)), 1e-6)
    tps = frags / stream_dur
    return ttft or 0.0, tps, total
"""
    ),
    md(
        """## 3. Run the samples

This takes ~30 seconds. If you're in a latency-sensitive environment, you
may want to run this cell a few times before capturing numbers (to let
connections warm up).
"""
    ),
    code(
        """def stats(name, samples):
    ttfts = [s[0] for s in samples if s[0] > 0]
    tpss  = [s[1] for s in samples if s[1] > 0]
    tot   = [s[2] for s in samples]

    def pct(xs, p):
        if not xs:
            return float("nan")
        if len(xs) == 1:
            return xs[0]
        return statistics.quantiles(xs, n=100)[p-1]

    print(f"{name:>30}  ttft p50={pct(ttfts,50):.2f}s  p95={pct(ttfts,95):.2f}s"
          f"  tps p50={pct(tpss,50):.1f}  total p50={pct(tot,50):.2f}s"
          f"  (n={len(samples)})")

mantle_samples = [bench_mantle_chat(GPT_OSS_120B) for _ in range(N_SAMPLES)]
stats("mantle chat_completions", mantle_samples)

# Try a runtime model that your account is very likely to have.
CANDIDATES = ["anthropic.claude-haiku-4-5",
              "anthropic.claude-3-5-haiku-20241022-v1:0"]
runtime_samples = None
for cand in CANDIDATES:
    try:
        runtime_samples = [bench_runtime_converse_stream(cand) for _ in range(N_SAMPLES)]
        stats(f"runtime {cand}", runtime_samples)
        break
    except Exception as e:
        print(f"  skipping {cand}: {e.__class__.__name__}")

if runtime_samples is None:
    print("⚠️  No runtime model available — Mantle-only numbers above.")
"""
    ),
    md(
        """## 4. Interpreting the numbers

- **TTFT dominates perceived latency.** A 1.5 s TTFT on a chat UX feels
  sluggish even if tokens/sec is fast afterwards.
- **Cold starts matter.** First call to any region is slower; most benchmarks
  exclude the first 2-3 samples.
- **Apples-to-apples requires the same model family.** Different model sizes
  produce different tokens/sec — don't compare a 20B to a 120B.
- **TPS drift over stream length.** Some models are front-loaded (fast first,
  slower later). Long completions should be sampled at p50 across sentences.

For a statistically meaningful comparison per the playbook §8:

- ≥ 500 samples per (model, region, endpoint) tuple.
- Capture p50 / p95 / p99 TTFT + total.
- Separate samples by hour-of-day (diurnal load matters on shared fleets).
- Include throttle / error rates next to latency.
"""
    ),
    md(
        """## 5. A simple plot (optional)

If matplotlib is installed, plot the TTFT distributions.
"""
    ),
    code(
        """try:
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6, 3.5))
    bins = 10
    ax.hist([s[0] for s in mantle_samples], bins=bins, alpha=0.6, label="Mantle CC")
    if runtime_samples:
        ax.hist([s[0] for s in runtime_samples], bins=bins, alpha=0.6, label="Runtime Converse")
    ax.set_xlabel("TTFT (s)")
    ax.set_ylabel("count")
    ax.set_title(f"TTFT distribution (n={N_SAMPLES})")
    ax.legend()
    fig.tight_layout()
    plt.show()
except ModuleNotFoundError:
    print("install matplotlib to plot: pip install matplotlib")
"""
    ),
]


if __name__ == "__main__":
    root = Path(__file__).parent.parent / "src" / "lab3"
    write_notebook(root / "01_api_sdk_diff.ipynb", diff_cells)
    write_notebook(root / "02_auth_security_migration.ipynb", auth_cells)
    write_notebook(root / "03_tools_and_caching_migration.ipynb", tool_mig_cells)
    write_notebook(root / "04_perf_eval.ipynb", perf_cells)
    print("wrote lab3 notebooks")
