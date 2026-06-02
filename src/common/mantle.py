"""
Shared Mantle client helpers used by the workshop notebooks.

Two client styles are supported by Amazon Bedrock Mantle:

    * OpenAI SDK          -> /v1/chat/completions, /v1/responses, /v1/models
    * Anthropic SDK       -> /anthropic/v1/messages

The workshop labs import these helpers so each notebook doesn't have to
re-implement region/token plumbing.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from aws_bedrock_token_generator import provide_token
from anthropic import AnthropicBedrockMantle
from openai import OpenAI


def _resolve_region(region: str | None) -> str:
    """Explicit argument wins; fall back to env; final fallback us-east-1."""
    return region or os.environ.get("AWS_REGION") or "us-east-1"


@dataclass(frozen=True)
class MantleConfig:
    region: str = "us-east-1"

    @property
    def openai_base_url(self) -> str:
        return f"https://bedrock-mantle.{self.region}.api.aws/v1"

    @property
    def anthropic_base_url(self) -> str:
        # The Anthropic SDK appends /v1/messages itself.
        return f"https://bedrock-mantle.{self.region}.api.aws/anthropic"


def bearer_token(region: str | None = None) -> str:
    """
    Mint a short-term (<= 12h) Bedrock Bearer token scoped to ``region``.

    The token inherits the caller's IAM permissions; it is safe to cache for
    the life of a notebook kernel. The explicit ``region`` argument wins over
    any pre-existing ``AWS_REGION`` env var — the token generator reads the
    env, so we must overwrite it (not use ``setdefault``).
    """
    region = _resolve_region(region)
    os.environ["AWS_REGION"] = region
    os.environ["AWS_DEFAULT_REGION"] = region
    return provide_token()


def openai_client(region: str | None = None, api_key: str | None = None) -> OpenAI:
    """Return an ``openai.OpenAI`` instance pointed at Mantle."""
    region = _resolve_region(region)
    cfg = MantleConfig(region=region)
    return OpenAI(base_url=cfg.openai_base_url, api_key=api_key or bearer_token(region))


def anthropic_client(region: str | None = None) -> AnthropicBedrockMantle:
    """Return an ``AnthropicBedrockMantle`` client for ``/anthropic/v1/messages``."""
    return AnthropicBedrockMantle(aws_region=_resolve_region(region))


# Model IDs used in the workshop (mirror the playbook Programmatic Access tables).
GPT_OSS_120B = "openai.gpt-oss-120b"
GPT_OSS_20B = "openai.gpt-oss-20b"
GPT_5_4 = "openai.gpt-5.4"
CLAUDE_OPUS_47 = "anthropic.claude-opus-4-7"
CLAUDE_HAIKU_45 = "anthropic.claude-haiku-4-5"
