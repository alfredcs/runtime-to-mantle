---
title: "2. IAM Permissions"
weight: 22
---

# IAM Permissions

This workshop talks to **three** services — Bedrock Mantle, Bedrock
Runtime (for the migration diffs in Lab 3), and SageMaker — so the role
your notebook runs under needs permissions for all three.

::alert[If you're running through Workshop Studio, the event role is
already provisioned with most of these permissions. The steps below are
shown so you (a) understand what's attached, and (b) can reproduce the
setup in your own account after the event.]

## AWS-managed policies

Attach all three to the notebook execution role. From the IAM console or
the CLI:

```bash
ROLE=<your-sagemaker-execution-role>

aws iam attach-role-policy --role-name $ROLE \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockMantleInferenceAccess

aws iam attach-role-policy --role-name $ROLE \
  --policy-arn arn:aws:iam::aws:policy/AmazonBedrockFullAccess

aws iam attach-role-policy --role-name $ROLE \
  --policy-arn arn:aws:iam::aws:policy/AmazonSageMakerFullAccess
```

| Policy | Why we need it |
|---|---|
| `AmazonBedrockMantleInferenceAccess` | Lets the notebook call `/v1/models`, `/v1/chat/completions`, `/v1/responses`, `/anthropic/v1/messages` — the Mantle surfaces. Covers `CreateInference`, `GetModel`, `ListModels`, `CallWithBearerToken`. |
| `AmazonBedrockFullAccess` | Lab 3.1 / 3.3 / 3.4 call the legacy **Bedrock Runtime** endpoint (`Converse`, `ConverseStream`, `ApplyGuardrail`) for the migration comparison. |
| `AmazonSageMakerFullAccess` | Lets the notebook instance itself start, access S3, and mount its ephemeral disk. |

## Minimum Mantle actions the labs exercise

If you prefer a custom inline policy instead of the managed one, the
smallest viable set for this workshop is:

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
      "Resource": "arn:aws:bedrock-mantle:*:*:project/*"
    },
    {
      "Sid": "MantleCallWithBearerToken",
      "Effect": "Allow",
      "Action": "bedrock-mantle:CallWithBearerToken",
      "Resource": "*"
    },
    {
      "Sid": "RuntimeForMigrationCompare",
      "Effect": "Allow",
      "Action": [
        "bedrock:Converse",
        "bedrock:ConverseStream",
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:ApplyGuardrail",
        "bedrock:ListFoundationModels"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    }
  ]
}
```

> `CallWithBearerToken` is a permission-only action and **must** be on
> `Resource: "*"` — project-scoping does not apply to it. This mirrors
> the structure of the AWS-managed `AmazonBedrockMantleInferenceAccess`.

## Verify the permissions stuck

From the AWS CloudShell or a local terminal (whichever you'll use to
smoke-test later):

```bash
AWS_REGION=us-east-1 python3 - <<'PY'
from aws_bedrock_token_generator import provide_token
from openai import OpenAI
c = OpenAI(base_url="https://bedrock-mantle.us-east-1.api.aws/v1",
           api_key=provide_token())
print([m.id for m in c.models.list().data][:5])
PY
```

If you see five model IDs, the IAM side is green. If you get
`401 access_denied` on `bedrock-mantle:ListModels`, re-check that
`AmazonBedrockMantleInferenceAccess` is attached.

**Next:** [3. Amazon Bedrock Mantle Access](../bedrock_mantle_access/).
