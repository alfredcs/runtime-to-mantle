# Amazon Bedrock Runtime → Bedrock Mantle Migration Workshop

Hands-on labs for AI Engineers (L200–L300) who are moving production workloads
from **Amazon Bedrock Runtime** (`bedrock-runtime.{region}.amazonaws.com`,
`Converse` / `InvokeModel`) to **Amazon Bedrock Mantle**
(`bedrock-mantle.{region}.api.aws`, OpenAI-compatible + Anthropic-native surfaces).

This workshop is based on the internal
[*Amazon Bedrock Runtime To Bedrock Mantle Migration Playbook*](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html).

---

## What you'll build

| Lab | What it covers | Where |
|---|---|---|
| **Lab 1 — Mantle Fundamentals** | List models, call `gpt-oss-120b` via Chat Completions, call `Claude Opus 4.7` via Messages, authenticate with SigV4 **and** Bearer tokens, construct prompts, reserve tokens, understand Projects | `src/lab1/01_mantle_fundamentals.ipynb` |
| **Lab 2 — Advanced Mantle Features** | SSE streaming (Chat Completions & Responses), tool / function calling, prompt-prefix caching, stateful `Responses` API, Anthropic `Messages` API | `src/lab2/` |
| **Lab 3 — Migration from `bedrock-runtime`** | Converse → Chat Completions & Messages side-by-side, IAM policy migration, `additionalModelRequestFields` → `extra_body`, tool-loop diff, TTFT / tokens-per-second benchmark | `src/lab3/` |
| **Lab 4 — Real-world Use Case** | End-to-end **Financial Filings Analyzer**: multi-LLM routing (Haiku 4.5 + gpt-oss-120b + Opus 4.7), per-session conversation history, Bearer-token auth, public HuggingFace `gbharti/finance-alpaca` dataset | `src/lab4/01_end_to_end_financial_analyzer.ipynb` |

---

## Learning objectives

By the end of this workshop you will be able to:

1. **Distinguish** the Mantle surfaces (`/v1/chat/completions`, `/v1/responses`,
   `/anthropic/v1/messages`) from the legacy Bedrock Runtime APIs
   (`Converse`, `InvokeModel`).
2. **Authenticate** to Mantle with both SigV4 (pure IAM) and Bearer tokens
   (short-term, minted from your IAM session).
3. **Migrate** a Converse-based tool-calling loop to Chat Completions,
   including the `json.loads(arguments)` step and the new `role: "tool"`
   message shape.
4. **Stream** responses on all three Mantle surfaces and consume the
   different SSE event taxonomies.
5. **Apply** prompt-prefix caching (`cache_salt`) and Responses API
   statefulness (`previous_response_id`) where they help.
6. **Understand** Mantle's Projects primitive as the cost / quota / IAM
   boundary (Reservations are covered conceptually only).
7. **Ship** an end-to-end application that combines multiple models behind a
   single abstraction, using a public dataset.

---

## Target audience

- AI Engineers, ML Engineers, and Solutions Architects with **6+ months** of
  experience on Bedrock Runtime.
- Comfortable with Python, `boto3`, and Jupyter notebooks.
- Familiar with OpenAI or Anthropic SDKs at a basic level (helpful, not required).

---

## Prerequisites

- **AWS account** with Bedrock Mantle access in **`us-east-1`**
  ([region coverage](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)).
- IAM principal with the AWS-managed **`AmazonBedrockMantleInferenceAccess`**
  policy attached (covers `CreateInference`, `GetModel`, `ListModels`,
  `CallWithBearerToken`). See `getting_started.md` §2 for the exact steps.
- **Python 3.10+** and `pip`. (`conda` also works.)
- **`Claude Opus 4.7`** and **`openai.gpt-oss-120b`** entitlements on the
  target account.
- Internet egress from your notebook host to
  `bedrock-mantle.us-east-1.api.aws` and `huggingface.co`.

See `getting_started.md` for a click-through setup that takes ~15 minutes.

---

## Repo layout

```text
.
├── README.md                         ← this file
├── getting_started.md                ← setup instructions (IAM, Python, tokens, HF)
├── requirements.txt                  ← pinned Python deps for all labs
├── contentspec.yaml                  ← Workshop Studio version spec
├── FACILITATOR_GUIDE.md              ← instructor notes (template)
├── static/                           ← images / scripts hosted with the workshop
├── content/                          ← Workshop Studio narrative pages (one per lab)
│   ├── index.en.md
│   ├── introduction/
│   ├── prerequisites/
│   ├── configuration/
│   ├── lab1/ … lab4/
│   └── summary/
├── scripts/
│   └── validate_notebooks.sh         ← runs each notebook end-to-end
└── src/
    ├── common/                       ← shared Mantle client + SigV4 helper
    ├── lab1/
    ├── lab2/
    ├── lab3/
    └── lab4/
```

---

## Run the labs

```bash
git clone https://github.com/alfredcs/runtime-to-mantle.git
cd runtime-to-mantle
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# One-time IAM / credential setup — see getting_started.md §2
aws configure            # or use an existing profile with Mantle access
export AWS_REGION=us-east-1

jupyter lab src/
```

Open the lab notebooks in order (`lab1` → `lab2` → `lab3` → `lab4`). Each
notebook is self-contained and annotates every step.

---

## Related resources

- [Amazon Bedrock Mantle overview](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [Mantle IAM actions / resources / condition keys](https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazonbedrockpoweredbyawsmantle.html)
- [`aws-bedrock-token-generator` on PyPI](https://pypi.org/project/aws-bedrock-token-generator/)
- [Anthropic Python SDK (Bedrock Mantle client)](https://github.com/anthropics/anthropic-sdk-python)
- [OpenAI Python SDK](https://github.com/openai/openai-python)

---

## Feedback

Open an issue with what worked, what didn't, and what you'd like to see next.
