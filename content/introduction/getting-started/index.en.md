---
title: "Getting Started"
weight: 11
---

# Getting Started

This page is a quick summary. For the full click-through setup, open the
**Configuration** section in the left navigation — it walks you through
each step with screenshots.

## The short version (Workshop Studio attendees)

1. **Join the event** at
   [catalog.us-east-1.prod.workshops.aws/join](https://catalog.us-east-1.prod.workshops.aws/join)
   using the OTP sent by your instructor.
2. **Open AWS console** from the event dashboard.
3. Confirm you're in **`us-east-1`** (top-right region selector).
4. Navigate to **Amazon SageMaker AI → Notebooks**, open the
   pre-provisioned notebook, and click **Open JupyterLab**.
5. In a JupyterLab terminal, clone and install:

   ```bash
   cd ~/SageMaker
   git clone https://github.com/alfredcs/runtime-to-mantle.git
   cd runtime-to-mantle
   pip install -q -r requirements.txt
   export AWS_REGION=us-east-1 AWS_DEFAULT_REGION=us-east-1
   ```
6. Open `src/lab1/01_mantle_fundamentals.ipynb` and select the
   **`conda_python3`** kernel.

## The self-paced version (your own AWS account)

You're responsible for:

- Creating an IAM role with the three managed policies listed in
  [Configuration → IAM Permissions](../../configuration/iam_permissions/).
- Enabling model access for the four models listed in
  [Configuration → Bedrock Mantle Access](../../configuration/bedrock_mantle_access/).
- Launching a SageMaker AI notebook instance (or running locally with
  `aws configure`).
- Cloning and installing as shown above.

Plan ~15 minutes for self-paced setup, most of which is waiting for IAM
propagation and model-access approval.

## What if something breaks?

The repo's `getting_started.md` has a full troubleshooting matrix
(region mismatches, 401s, missing model access, etc.). The Configuration
pages also call out the most common failure modes inline.
