---
title: "3. Amazon Bedrock Mantle Access"
weight: 23
---

# Amazon Bedrock Mantle Access

::alert[Make sure you are in the **US East (N. Virginia) / us-east-1**
region before proceeding.]

## Enable model access

1. In the AWS Management Console, use the search box at the top to
   search for **Amazon Bedrock**. Click the first result.

2. In the Bedrock console, from the left navigation, click
   **Model access** (under **Bedrock configurations**).

3. Click **Manage model access** (top right).

4. Check the following models — the four models this workshop exercises
   plus one migration-compare baseline:

   | Model | Used in |
   |---|---|
   | `openai.gpt-oss-120b` | Lab 1, 2, 3, 4 |
   | `openai.gpt-oss-20b` | Lab 1 (model listing), 4 (optional fallback) |
   | `anthropic.claude-opus-4-7` | Lab 1, 2, 3, 4 |
   | `anthropic.claude-haiku-4-5` | Lab 2, 3, 4 |
   | `anthropic.claude-3-5-haiku` | Lab 3.1 / 3.3 / 3.4 runtime Converse baseline (fallback) |

5. Scroll down and click **Next**, review, then **Submit**.

6. Most models show **Access granted** within a minute or two. Claude
   family access may take up to 2 minutes — refresh the page if it still
   shows **In progress**.

## Verify on the Mantle endpoint

Claude Opus 4.7 and `gpt-oss-120b` are reached through the Mantle
endpoint, **not** the legacy Bedrock Runtime endpoint. You can confirm
both are reachable with a single listing call:

```bash
AWS_REGION=us-east-1 aws bedrock-mantle list-models \
    --endpoint-url https://bedrock-mantle.us-east-1.api.aws \
    --output table 2>/dev/null \
  || echo "If the CLI doesn't have bedrock-mantle commands yet, use the Python smoke test from the IAM Permissions page instead."
```

You should see the four model IDs from the table above in the listing.

## Expected quota (Mantle)

This workshop uses < 1% of default quota, but for context:

- **RPM:** 10,000 / account / Region, shared across all Mantle models.
- **Claude 4.7+ TPM:** 10M input + 2M output / min (tracked separately).
- **Other models' TPM:** gated by RPM cap + fair-share queuing — no hard
  TPM limit.

**Next:** [4. Amazon SageMaker AI Notebook](../sagemaker_access/).
