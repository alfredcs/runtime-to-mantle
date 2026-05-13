---
title: "Prerequisites"
weight: 15
---

# Prerequisites

## Attendee checklist

- A PC with a modern web browser (Chrome or Firefox recommended).
- Basic comfort with Python and Jupyter notebooks.
- 6+ months of hands-on Amazon Bedrock Runtime experience (you know what
  `Converse` / `InvokeModel` look like).
- Helpful (not required): prior use of the OpenAI or Anthropic SDK.

## What the event account needs

If you're running this in a Workshop Studio event, your instructor has
already provisioned all of this for you. For self-paced delivery in your
own AWS account:

- An IAM role / user with:
  - `AmazonBedrockMantleInferenceAccess`
  - `AmazonBedrockFullAccess`
  - `AmazonSageMakerFullAccess`
- **Model access** granted in `us-east-1` for:
  - `openai.gpt-oss-120b`
  - `openai.gpt-oss-20b`
  - `anthropic.claude-opus-4-7`
  - `anthropic.claude-haiku-4-5`
- A SageMaker AI Notebook Instance (`ml.t3.medium` is sufficient).
- Internet egress to `bedrock-mantle.us-east-1.api.aws` and
  `huggingface.co`.

The **Configuration** section (next in the navigation) walks you through
provisioning each of these step by step.

## Target audience

AI Engineers, ML Engineers, and Solutions Architects who have a
production workload on Bedrock Runtime and are evaluating migration to
Bedrock Mantle.

## Region

This workshop is tested in **`us-east-1`** (N. Virginia). Mantle is
region-scoped and Bearer tokens are minted per-region — using any other
region will cause spurious 401s. Stay in `us-east-1` for the duration
of the workshop.

## Time to complete

Approximately **2 hours** across four labs of 30 minutes each.

## Cost

No cost when run through an instructor-led Workshop Studio event. If
self-hosted, expect < $1 of Bedrock Mantle inference cost per attendee,
plus normal SageMaker notebook-instance pricing for the runtime (~$0.05
per hour on `ml.t3.medium`).
