# Lab 4 — End-to-End: Financial Filings Analyzer

**Notebook:** `01_end_to_end_financial_analyzer.ipynb`
**Duration:** ~30 min · **Level:** L300 · **Lab 4 of 4**

## Goals

Ship a production-shaped application on Mantle:

- **Multi-LLM routing** — Claude Haiku 4.5 (classification), gpt-oss-120b
  (tool-calling metric lookup), Claude Opus 4.7 (thematic narrative).
- **Public dataset** — Hugging Face `gbharti/finance-alpaca` as a stand-in
  for an enterprise data lake.
- **Stateful conversations** — thread management keyed by session ID.
- **Bearer-token auth** — minted with `aws-bedrock-token-generator`.
- **Business-value framing** — cost comparison vs. "always route to the
  frontier model".

## Prerequisites

Same as Lab 1, plus:

- Network access to `huggingface.co` (or a local copy of the dataset).
- Enough TPM headroom for Opus 4.7 — the notebook runs ~5 Opus calls.
