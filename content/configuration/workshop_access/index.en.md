---
title: "1. Workshop Access"
weight: 21
---

# Workshop Access

Follow the instructions given by the workshop instructor to log in to the
AWS account provisioned for this event. **Do NOT use your personal or
business account** — the pre-built IAM role and SageMaker notebook
instance are in the event account only.

## Join the event

1. Open [https://catalog.us-east-1.prod.workshops.aws/join](https://catalog.us-east-1.prod.workshops.aws/join)
   or the one-click join link provided by your event operator.
2. Click **Email One-Time Password (OTP)**.
3. Enter your email address and click **Send passcode**.
4. Check your mailbox, copy the one-time password, paste it back, and
   click **Sign in**.
5. Review the terms and conditions, then click **Join event**.

## Open the AWS console

After joining you'll land on the event dashboard. On the left navigation
panel, under **AWS account access**, click **Open AWS console**. A new
browser tab opens logged in to the temporary account.

::alert[Make sure you're in the **US East (N. Virginia) / us-east-1**
region before proceeding. The region selector is in the top-right of the
AWS console header.]

## Verify your identity

Open a terminal (you'll use this later, or skip it for now) and run:

```bash
aws sts get-caller-identity
```

You should see an `Arn` starting with
`arn:aws:sts::<account>:assumed-role/WorkshopStudio.../` — that's the
event-provisioned role that the next step depends on.

**Next:** [2. IAM Permissions](../iam_permissions/).
