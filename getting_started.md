# Getting Started

This guide takes you from a blank laptop to "Lab 1 Cell 1 runs green" in
roughly 15 minutes. Every step below is **required** — skipping any of them
will cause one of the labs to fail with a confusing error.

---

## 1. Clone the repo and install Python dependencies

```bash
git clone https://github.com/alfredcs/runtime-to-mantle.git
cd runtime-to-mantle

# Use a fresh virtualenv so workshop pins don't collide with other projects.
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

Supported Python versions: **3.10+**. The labs are tested on 3.10 and 3.12.

---

## 2. Provision AWS access for Amazon Bedrock Mantle

You need three things:

1. An **IAM principal** (user or role) whose credentials your laptop can use.
2. An **IAM policy** that grants Mantle permissions.
3. **Model access** to the models used by the labs.

### 2.1 Attach the Mantle inference policy

The fastest route is to attach the AWS-managed policy:

```bash
# Replace <role-name> with the IAM role your laptop / notebook uses.
aws iam attach-role-policy \
    --role-name  <role-name> \
    --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess
```

That policy grants the actions the workshop needs: `CreateInference`,
`GetInference`, `CancelInference`, `GetModel`, `ListModels`, `GetProject`,
`ListProjects`, and `CallWithBearerToken`.

If you prefer a least-privilege custom policy, the playbook's §9.2 shows a
minimal inline policy that is equivalent.

> **`AmazonBedrockFullAccess` is not enough.** The `bedrock:*` policy does not
> grant any `bedrock-mantle:*` actions — Mantle is a separate IAM namespace.

### 2.2 Enable the models used in the labs

In the Bedrock console → **Model access**, make sure the following are
**Access granted** in `us-east-1`:

- `openai.gpt-oss-120b`
- `openai.gpt-oss-20b`
- `anthropic.claude-opus-4-7`
- `anthropic.claude-haiku-4-5`

(The notebooks will surface a clear error if any of these are missing.)

### 2.3 Configure credentials locally

```bash
aws configure
# AWS Access Key ID:     <your key>
# AWS Secret Access Key: <your secret>
# Default region name:   us-east-1       ← important
# Default output format: json
```

If you already have a profile, just point to it:

```bash
export AWS_PROFILE=your-profile
export AWS_REGION=us-east-1
```

> **Region matters.** Bearer tokens issued with
> `aws-bedrock-token-generator` are **region-scoped**. A token minted while
> `AWS_REGION=us-west-2` will be rejected by the `us-east-1` endpoint with a
> 401 (`Credential should be scoped to a valid region`). Always set
> `AWS_REGION=us-east-1` before minting a token unless you know the endpoint
> you're calling.

### 2.4 Smoke-test the connection

```bash
AWS_REGION=us-east-1 python3 - <<'PY'
import os
# Overwrite any stale region the user's shell may have exported.
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
from aws_bedrock_token_generator import provide_token
from openai import OpenAI

client = OpenAI(
    base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
    api_key=provide_token(),
)
print([m.id for m in client.models.list().data][:10])
PY
```

Expected output: a list of model IDs, starting with the `openai.*` and
`anthropic.*` prefixes you granted access to in §2.2.

If you get a **401 `access_denied`** mentioning `bedrock-mantle:ListModels`,
go back to §2.1 — the managed policy isn't attached yet.

---

## 3. Hugging Face access (Lab 4 only)

Lab 4 downloads the [`gbharti/finance-alpaca`](https://huggingface.co/datasets/gbharti/finance-alpaca)
dataset. It's public, so you can usually fetch it anonymously. If you hit a
rate limit, create a free account and authenticate:

```bash
pip install huggingface_hub            # already in requirements.txt
huggingface-cli login                  # paste your token (read-only is fine)
```

---

## 4. Launch Jupyter

```bash
jupyter lab src/
```

Then open each notebook in order:

1. `src/lab1/01_mantle_fundamentals.ipynb`
2. `src/lab2/01_streaming.ipynb`
3. `src/lab2/02_tool_calling.ipynb`
4. `src/lab2/03_caching_and_stateful.ipynb`
5. `src/lab3/01_api_sdk_diff.ipynb`
6. `src/lab3/02_auth_security_migration.ipynb`
7. `src/lab3/03_tools_and_caching_migration.ipynb`
8. `src/lab3/04_perf_eval.ipynb`
9. `src/lab4/01_end_to_end_financial_analyzer.ipynb`

Each notebook has a "Before you begin" cell that verifies your credentials
and prints the region it will use.

---

## 5. (Optional) Run everything non-interactively

The `scripts/validate_notebooks.sh` helper runs every notebook end-to-end and
fails loudly if any cell errors. It's what the workshop authors use in CI.

```bash
bash scripts/validate_notebooks.sh
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `401 invalid_api_key` with `Credential should be scoped to a valid region` | Your Bearer token was minted in a different region than the endpoint | `export AWS_REGION=us-east-1` before calling `provide_token()` |
| `401 access_denied` `bedrock-mantle:ListModels` | IAM principal is missing Mantle permissions | Attach `AmazonBedrockMantleInferenceAccess` (§2.1) |
| `model 'anthropic.claude-opus-4-7' not found` | Model access not granted in this region | Enable access in the Bedrock console (§2.2) |
| `openai.BadRequestError: temperature is not supported` when calling Opus 4.7 | Claude Opus 4.7 rejects `temperature`, `top_p`, `top_k` **on both endpoints** | Strip those fields for `anthropic.claude-opus-4-7` (the workshop helpers do this automatically) |
| `ModuleNotFoundError: aws_bedrock_token_generator` | Dependencies not installed | `pip install -r requirements.txt` inside the activated venv |
| `botocore.exceptions.NoCredentialsError` | AWS credentials not configured | `aws configure` or `export AWS_PROFILE=...` |
| Lab 4 hangs on dataset download | Slow HF mirror | `HF_HUB_ENABLE_HF_TRANSFER=1` or pre-download offline |

If you're still stuck, open an issue on the workshop repo with the full
traceback and the output of `aws sts get-caller-identity`.
