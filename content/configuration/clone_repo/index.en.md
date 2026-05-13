---
title: "5. Clone the Repository"
weight: 25
---

# Clone the Workshop Repository

The workshop code lives at
[**alfredcs/runtime-to-mantle** on GitHub](https://github.com/alfredcs/runtime-to-mantle).
Clone it into your SageMaker JupyterLab session.

## Open a terminal in JupyterLab

From the JupyterLab launcher (**File → New → Terminal**, or the
**Terminal** tile on the launcher page), run:

```bash
cd ~/SageMaker
git clone https://github.com/alfredcs/runtime-to-mantle.git
cd runtime-to-mantle
```

> The `~/SageMaker` directory is persistent across notebook-instance
> stops/starts. Anything outside it (e.g. `~/`) is ephemeral and will be
> wiped when the instance is restarted.

## Install the Python dependencies

Still in the terminal:

```bash
pip install -q -r requirements.txt
```

This pins:

- `openai >= 1.50.0`
- `anthropic[bedrock] >= 0.40.0`
- `aws-bedrock-token-generator >= 0.2.0`
- `boto3 >= 1.40.0`
- `datasets`, `huggingface_hub` (Lab 4 dataset)
- `pandas`, `matplotlib`, `tabulate` (Lab 3.4 perf eval)

Install takes ~60 seconds on a fresh instance.

## Pin the region

The region you set here flows into every Bearer token minted during the
labs. **Set it before you open any notebook:**

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
```

(JupyterLab notebook kernels inherit the terminal env they were launched
from. If you start a kernel before setting this, restart it after.)

## Smoke test

Quick one-liner to confirm the whole chain works:

```bash
AWS_REGION=us-east-1 python3 - <<'PY'
import os
os.environ["AWS_REGION"] = "us-east-1"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
from aws_bedrock_token_generator import provide_token
from openai import OpenAI
c = OpenAI(base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
           api_key=provide_token())
print([m.id for m in c.models.list().data][:5])
PY
```

Expected: a list of five model IDs. If anything else, cross-check
[IAM Permissions](../iam_permissions/) and [Bedrock Mantle Access](../bedrock_mantle_access/).

## Open the first lab

In the JupyterLab file browser on the left, navigate to
`runtime-to-mantle/src/lab1/` and double-click
`01_mantle_fundamentals.ipynb`. When prompted, select the
**`conda_python3`** kernel.

**Next:** [Lab 1 — Mantle Fundamentals](../../lab1/).
