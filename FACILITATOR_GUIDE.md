# Facilitator Guide: Amazon Bedrock Runtime → Mantle Migration

## Workshop Overview

**What Participants Will Learn:** How to migrate production workloads from
Amazon Bedrock Runtime (`bedrock-runtime.{region}.amazonaws.com`,
`Converse` / `InvokeModel`) to Amazon Bedrock Mantle
(`bedrock-mantle.{region}.api.aws`, Chat Completions / Responses / Anthropic
Messages). By the end, they'll have run four labs against live Bedrock
Mantle in `us-east-1` and will have a migration checklist they can take
back to work.

**Learning Objectives:**

- Discover and call models across the three Mantle API surfaces.
- Authenticate to Mantle with SigV4 *and* Bearer tokens, including
  understanding the short- vs long-term key trade-offs.
- Migrate a Converse tool-loop to Chat Completions (including the
  `json.loads(arguments)` trap, `role:"tool"` turn-in, and finish-reason
  vocabulary changes).
- Stream responses and consume the three different event taxonomies.
- Use prefix caching (`cache_salt`) and the stateful Responses API
  (`previous_response_id`).
- Benchmark TTFT and tokens-per-second on their own account.
- Ship an end-to-end multi-model application backed by a public dataset.

**Target Audience:** AI / ML Engineers and Solutions Architects with 6+
months of Bedrock Runtime experience. Comfortable with Python and Jupyter
notebooks.

---

## Prerequisites

### Facilitator Preparation

- Walk through the full workshop yourself (budget ~2h) to understand the
  flow and catch account-specific issues.
- Pre-mint a Bearer token the morning of the event (`AWS_REGION=us-east-1
  python -c "from aws_bedrock_token_generator import provide_token;
  print(provide_token())"`) and confirm `GET /v1/models` returns results.
- Pre-run Lab 4 against the same account — the Hugging Face dataset
  download is ~70 MB and sometimes blocked by corporate egress.

### Service Requirements & Quotas

- **Services used:** Amazon Bedrock Mantle (Chat Completions, Responses,
  Anthropic Messages), Amazon Bedrock Runtime (for the migration diffs),
  IAM, STS, CloudTrail (optional).
- **Quota requirements:**
  - Mantle: default **10,000 RPM / account / Region** is sufficient for
    < 50 participants in one region.
  - Mantle Claude 4.7+: **10M input TPM, 2M output TPM** per account —
    shared across the room. For larger groups, open a quota increase
    ticket the week before.
- **Regions:** `us-east-1`. Do **not** swap to GovCloud — Mantle is not
  available there.
- **Large events:** For 100+ participants, split into two regions
  (`us-east-1` + `us-east-2`) to keep throttle risk low.
- **Account setup:** Every participant account needs
  `AmazonBedrockMantleInferenceAccess` attached to the Workshop-Studio
  runtime role. The Workshop Studio event template in this repo does this
  for you.

### Participant Prerequisites

- Comfortable with Python and Jupyter.
- Prior boto3 / Bedrock Runtime experience (6+ months).
- Modern browser.
- A laptop that can run Jupyter Lab (or an AWS-hosted SageMaker Studio
  notebook instance).

---

## Recommended Agenda

### Standard 2-Hour Format (4 labs × 30 min)

Prerequisites (IAM policies, model access, SageMaker notebook, repo
clone) are assumed done **before** the session — either by Workshop
Studio provisioning or via a pre-event setup page. If you need to run
setup live, budget another 15 minutes *before* the 2-hour window.

| Time | Duration | Activity | Key Focus & Tips |
|------|----------|----------|------------------|
| 0:00–0:30 | 30 min | **Lab 1 — Fundamentals** | Three surfaces + two auth models + the response-shape table. Confirm every participant sees a list from `GET /v1/models` before moving on. |
| 0:30–1:00 | 30 min | **Lab 2 — Advanced Features** (three sub-notebooks ×10 min each) | 2.1 streaming → 2.2 tool calling (the `json.loads(arguments)` trap) → 2.3 caching + stateful. |
| 1:00–1:30 | 30 min | **Lab 3 — Migration** (four sub-notebooks ×7-8 min each) | 3.1 side-by-side diff → 3.2 IAM / auth migration → 3.3 tool-loop diff → 3.4 perf eval. |
| 1:30–2:00 | 30 min | **Lab 4 — Financial Analyzer** | Full multi-LLM router over the HuggingFace finance-alpaca dataset. Land on the cost-framing message at the end. |

**Pacing tips:**

- **Lab 1** is the slowest because everyone's still settling in. Don't
  rush it — the mental model it establishes is load-bearing.
- **Lab 2.2 (tool calling)** is the one that's most likely to overrun
  because the `json.loads()` step trips people up. If you're short on
  time, do the Chat Completions demo live and let the Anthropic one run
  as a post-workshop exercise.
- **Lab 3.4 (perf eval)** is the easiest to cut if you're behind. The
  numbers are nice-to-have, not load-bearing for the migration message.
- **Lab 4** can skip the "production hardening checklist" cell if
  you're over time — it's a read-only checklist, not a runnable demo.

**Longer format?** Insert a 15-minute break between Lab 2 and Lab 3, and
extend each lab by ~10 minutes to land at a 2h 45m delivery. The
notebooks have enough depth to fill the time.

---

## Delivery Tips

### Setup & Environment

- Start provisioning 10 min early. The first `GET /v1/models` call on a
  fresh IAM role sometimes takes 30–60 s because the role is still
  propagating.
- Have a backup account with model access already granted — if one
  participant's account has a model-access lag, pair them temporarily.
- Confirm `AWS_REGION=us-east-1` is exported in everyone's shell before
  the first token is minted. This single env var causes 80% of 401s.

**Regional notes:**

- `us-east-1` is the primary. `us-east-2` and `us-west-2` also work for
  everything in this workshop.
- Avoid `us-west-1`, GovCloud, and `ap-northeast-2/3`, `ap-southeast-1`,
  `ca-*`, `me-*`, `af-*`, `il-*`, `mx-*` — Mantle is not there.

### Facilitation Strategies

**What works well:**

- Explain the three-surface mental model **before** anyone opens a
  notebook. Once it's anchored, the rest of the workshop reinforces it.
- When showing Lab 3's "one table to rule them all", keep it visible on a
  second screen for the rest of the workshop. Participants keep referring
  back to it.
- Have everyone run the first `bearer_token()` call at the same time —
  seeing 40 green cells at once is a great confidence-builder.

**Common mistakes:**

- Don't mix up `bedrock-mantle` (IAM prefix, hostname, managed policy)
  with `bedrock` (SigV4 service name, long-term key creation service
  name). Both coexist on purpose — explain this once, loudly.
- Don't let anyone try to reach Claude Opus 4.7 through
  `/v1/chat/completions` — it's only on `/anthropic/v1/messages`.

**Mixed skill levels:**

- Beginners: pair with an experienced participant during Lab 2.2 and
  Lab 3.3.
- Advanced: point them to the optional challenges at the bottom of Lab 4
  (server-side MCP Lambda tool, runtime-vs-Mantle shadow test).

---

## Troubleshooting

### Top Issues

#### 1. "401 invalid_api_key: Credential should be scoped to a valid region"

:::alert{type="warning"}
Most common issue. The Bearer token was minted in a different region than
the Mantle endpoint.
:::

**Cause:** `AWS_REGION` was set (or left) to something other than
`us-east-1` when `provide_token()` was called.

**Fix:**

```bash
export AWS_REGION=us-east-1
export AWS_DEFAULT_REGION=us-east-1
# Then re-mint and retry.
```

#### 2. "401 access_denied: not authorized to perform bedrock-mantle:ListModels"

**Cause:** The IAM principal is missing Mantle permissions.

**Fix:**

- Attach `arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess` to
  the role.
- Wait 10–30 s for IAM propagation, then retry.

#### 3. "model 'anthropic.claude-opus-4-7' not found"

**Cause:** Model access not granted in this region for this account.

**Fix:** Bedrock console → Model access → enable Opus 4.7.

#### 4. "temperature is not supported" on Claude Opus 4.7

**Cause:** Opus 4.7 rejects `temperature`, `top_p`, `top_k` on *both*
endpoints.

**Fix:** Remove those fields from the request. The workshop helpers do
not strip them automatically; Lab 3.2 discusses an adapter pattern.

#### 5. "ModuleNotFoundError: aws_bedrock_token_generator"

**Cause:** Participant forgot to `pip install -r requirements.txt` inside
their venv.

**Fix:** Activate the venv and re-install.

#### 6. Hugging Face dataset download hangs (Lab 4)

**Cause:** Corporate proxy blocking `huggingface.co`.

**Fix:** Pre-download the parquet in a helper step before the event, or
set `HF_DATASETS_OFFLINE=1` and ship a local copy of the dataset on
disk.

### Service Limits & Quotas

:::expand{header="Service quota issues during delivery"}

- **10,000 RPM Mantle cap (shared across all models)**: if you see a
  spike of 429s across the room during Lab 3.4 (perf eval) or Lab 4
  (multi-model router), you're hitting the shared cap. Pause for 60 s and
  resume.
- **Claude Opus 4.7 output TPM (2M)**: in a room of > 50 running Lab 4,
  you may throttle. Tell participants to cap `max_tokens=200` or skip to
  the next cell.

:::

### When Nothing Works

- Check CloudTrail for `bedrock-mantle.amazonaws.com` events; most 401s
  will show up there with clear `errorCode`.
- Confirm the role the participant's notebook is running under actually
  matches what you think it is (`aws sts get-caller-identity`).
- If all else fails, have them use a facilitator backup account with the
  managed policy pre-attached.

---

## Resources

### For Facilitators

- **Source code:** this repo (`src/`, `content/`).
- **Reference playbook:** *Amazon Bedrock Runtime To Bedrock Mantle
  Migration Playbook* (internal) — Section mappings are listed in each
  lab.
- **Support channel:** `#bedrock-mantle-workshop` (Slack).

### For Participants (share after the event)

- [Amazon Bedrock Mantle overview](https://docs.aws.amazon.com/bedrock/latest/userguide/bedrock-mantle.html)
- [`AmazonBedrockMantleInferenceAccess` managed policy](https://docs.aws.amazon.com/aws-managed-policy/latest/reference/AmazonBedrockMantleInferenceAccess.html)
- [`aws-bedrock-token-generator`](https://pypi.org/project/aws-bedrock-token-generator/)
- [OpenAI Python SDK](https://github.com/openai/openai-python)
- [Anthropic Python SDK (Bedrock Mantle client)](https://github.com/anthropics/anthropic-sdk-python)

---

## Post-Event Actions

- Terminate the Workshop Studio event to trigger automatic cleanup.
- Collect feedback (short survey: `1-5 confidence before` / `after`, open
  field for "biggest confusion").
- Update this guide if you found new issues — the next facilitator will
  thank you.

---

## Additional Notes

- Uses **preview-stage** Mantle APIs — behaviour may change. Always
  re-verify model IDs against the model card's Programmatic Access table
  before delivering.
- This workshop does **not** cover fine-tuning, embeddings, image/audio
  models, batch inference, or the OpenAI Realtime API — all are explicitly
  out of scope for Mantle today.

---

## Need Help?

- Improve this guide: PR to this repo.
- Workshop Studio support: Atlas Agent from the UI, or
  `#workshop-studio-interest` on Slack.
- Authoring docs: [Workshop Studio Facilitator Guide Documentation](https://catalog.workshops.aws/docs/en-US/create-a-workshop/authoring-a-workshop/facilitator-guide)
