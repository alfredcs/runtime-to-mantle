---
title: "Amazon Bedrock Runtime → Mantle Migration"
weight: 0
---

# Amazon Bedrock Runtime → Bedrock Mantle Migration

Welcome! This workshop takes AI Engineers (L200–L300) from *"I have a
Bedrock Runtime application in production"* to *"I've migrated the parts
that make sense to Bedrock Mantle, and I know why I kept the rest."*

## Why this workshop

Amazon Bedrock Mantle is Amazon Bedrock's next-generation distributed
inference engine. It exposes three API surfaces:

- **OpenAI-compatible Chat Completions** at `/v1/chat/completions`
- **OpenAI-compatible Responses** (stateful, server-side tools) at `/v1/responses`
- **Anthropic-native Messages** at `/anthropic/v1/messages`

It is **not** a drop-in replacement for Bedrock Runtime — the endpoint,
the auth model, the IAM service prefix, model IDs, response shapes,
streaming event taxonomy, and tool-calling semantics all change. This
workshop walks you through each change with runnable notebooks.

## What you'll build

Four labs of increasing depth, culminating in an end-to-end multi-model
application driven by a public Hugging Face dataset.

| Lab | Duration | Focus |
|---|---|---|
| 1 — Fundamentals | 30 min | List models, call gpt-oss-120b and Claude Opus 4.7, auth |
| 2 — Advanced features | 85 min | Streaming, tool calling, prefix caching, Responses statefulness |
| 3 — Migration | 2 h | Converse → Mantle side-by-side, IAM, tool loops, perf benchmark |
| 4 — Real-world app | 60 min | Financial Filings Analyzer with multi-LLM routing |

## How to use this workshop

Start with **Prerequisites** and **Configuration** (top of the nav) to
provision AWS access and install Python deps. Then work through the labs
in order — each one builds on concepts from the prior one.

Every lab is a Jupyter notebook under `src/labN/`; Workshop Studio pages
frame *why* each lab matters.
