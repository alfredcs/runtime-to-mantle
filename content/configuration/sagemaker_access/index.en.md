---
title: "4. Amazon SageMaker AI Notebook"
weight: 24
---

# Amazon SageMaker AI Notebook Access

Amazon SageMaker AI Notebook Instances are managed Jupyter environments
with the AWS SDKs, `boto3`, and Python pre-installed. The Workshop Studio
event has already provisioned an instance for you — you just need to
open it.

## Open JupyterLab

1. In the AWS console, confirm you're in **US East (N. Virginia) /
   us-east-1** (top-right region selector).

2. Search for **Amazon SageMaker AI** in the top search bar. Click the
   service.

3. From the left navigation, click **Notebooks** → **Notebook
   instances**.

4. A notebook instance is pre-provisioned (name will look like
   `mantle-workshop-nb-<random>`). If its **Status** is **Stopped**,
   click **Start** and wait ~2 minutes for **InService**.

5. When **Status** shows **InService**, click **Open JupyterLab** (under
   **Actions** on the right side of the row).

6. A new browser tab opens in JupyterLab.

## Recommended instance type

The pre-provisioned instance is `ml.t3.medium` (2 vCPU, 4 GB RAM). That's
plenty for this workshop — you're running thin notebook code that calls
remote APIs, not training models locally. If you're running this outside
Workshop Studio and creating your own notebook, `ml.t3.medium` is still
the right pick.

## Kernel selection

When you open the first notebook, JupyterLab will prompt you for a
kernel. Pick **`conda_python3`** (Python 3.10 or newer). The notebooks
`pip install` any missing dependencies in their first cell.

::alert[If the `conda_python3` kernel is unavailable, `python3` will also
work. Avoid the `PyTorch` / `TensorFlow` kernels — they add ~30 s of
unused imports to every cell.]

## Region check

The notebook instance runs in whatever region it was provisioned in. The
first cell of every lab prints the region explicitly — verify it says
`us-east-1`.

**Next:** [5. Clone the Repository](../clone_repo/).
