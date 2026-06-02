"""
Static configuration for the Mantle Studio demo: the model catalog, the three
API surfaces exposed by the single bedrock-mantle endpoint, supported regions,
and *illustrative* per-token pricing used for the business-value math.

Sources distilled from the AWS Bedrock Mantle docs and the user's own
"Mantle Migration Playbook" (model IDs, regions, paths, auth headers).
Pricing numbers are ILLUSTRATIVE list prices for demonstration only — they are
clearly labelled as such in the UI and are not authoritative AWS pricing.
"""

# ---------------------------------------------------------------------------
# The single entry point. Every surface below is reached through THIS host,
# differing only by path. This is the whole point of the demo.
# ---------------------------------------------------------------------------
MANTLE_HOST_TEMPLATE = "bedrock-mantle.{region}.api.aws"

# 13 regions where the bedrock-mantle endpoint is available (Playbook-corrected).
REGIONS = [
    "us-east-1", "us-east-2", "us-west-2",
    "eu-central-1", "eu-west-1", "eu-west-2", "eu-south-1", "eu-north-1",
    "ap-northeast-1", "ap-south-1", "ap-southeast-2", "ap-southeast-3",
    "sa-east-1",
]
DEFAULT_REGION = "us-east-1"

# ---------------------------------------------------------------------------
# The three API surfaces — one host, three paths.
# ---------------------------------------------------------------------------
SURFACES = {
    "chat_completions": {
        "key": "chat_completions",
        "name": "Chat Completions",
        "spec": "OpenAI-compatible",
        "path": "/v1/chat/completions",
        "stateful": False,
        "mantle_only": False,
        "tagline": "Stateless · low-latency · full client control of history",
        "auth_header": "Authorization: Bearer <token>",
        "extra_headers": [],
        "best_for": "High-volume, text-focused tasks: classification, routing, "
                    "summarization, extraction. You manage the message history.",
        "console": "Triage",
        "accent": "#3b82f6",
    },
    "responses": {
        "key": "responses",
        "name": "Responses API",
        "spec": "OpenAI-compatible",
        "path": "/v1/responses",
        "stateful": True,
        "mantle_only": True,
        "tagline": "Stateful · server-side memory & tools · agentic",
        "auth_header": "Authorization: Bearer <token>",
        "extra_headers": [],
        "best_for": "Multi-turn agents. The server remembers the conversation "
                    "(previous_response_id) and can run the whole tool loop for you.",
        "console": "Concierge",
        "accent": "#a855f7",
    },
    "messages": {
        "key": "messages",
        "name": "Messages API",
        "spec": "Anthropic-native",
        "path": "/anthropic/v1/messages",
        "stateful": False,
        "mantle_only": False,
        "tagline": "Anthropic-native · typed content · extended thinking",
        "auth_header": "x-api-key: <token>",
        "extra_headers": ["anthropic-version: 2023-06-01"],
        "best_for": "Claude-native workloads needing rich typed content "
                    "(images/documents), tool_use blocks and visible thinking.",
        "console": "Analyst",
        "accent": "#f0883e",
    },
}

# ---------------------------------------------------------------------------
# Provider palette for model pills.
# ---------------------------------------------------------------------------
PROVIDERS = {
    "openai":     {"label": "OpenAI",    "color": "#10a37f"},
    "anthropic":  {"label": "Anthropic", "color": "#d97757"},
    "deepseek":   {"label": "DeepSeek",  "color": "#4d6bfe"},
    "qwen":       {"label": "Qwen",      "color": "#7c5cff"},
    "zai":        {"label": "Z.AI",      "color": "#14b8a6"},
    "mistral":    {"label": "Mistral",   "color": "#fa520f"},
    "minimax":    {"label": "MiniMax",   "color": "#ff5a76"},
    "moonshotai": {"label": "Moonshot",  "color": "#2563eb"},
    "google":     {"label": "Google",    "color": "#ea4335"},
}

# ---------------------------------------------------------------------------
# Model catalog. `surfaces` lists which of the three API styles the model is
# reachable through. Prices are per 1M tokens, ILLUSTRATIVE.
# Model IDs use the Playbook-correct Mantle form ({provider}.{model}, no :v1:0).
# ---------------------------------------------------------------------------
MODELS = [
    {"id": "openai.gpt-oss-20b",  "provider": "openai", "label": "GPT-OSS 20B",
     "surfaces": ["chat_completions", "responses"], "ctx": "128K",
     "price_in": 0.07, "price_out": 0.30,
     "blurb": "Small, fast, cheap. Ideal for high-volume triage.", "flags": []},
    {"id": "openai.gpt-oss-120b", "provider": "openai", "label": "GPT-OSS 120B",
     "surfaces": ["chat_completions", "responses"], "ctx": "128K",
     "price_in": 0.15, "price_out": 0.60,
     "blurb": "Flagship open-weight. Server-side tools via Responses.", "flags": ["responses"]},
    {"id": "openai.gpt-5.4", "provider": "openai", "label": "GPT-5.4",
     "surfaces": ["responses"], "ctx": "400K",
     "price_in": 1.25, "price_out": 10.00,
     "blurb": "Frontier OpenAI. Stateful agentic concierge via Responses.", "flags": ["responses"]},
    {"id": "anthropic.claude-haiku-4-5", "provider": "anthropic", "label": "Claude Haiku 4.5",
     "surfaces": ["messages"], "ctx": "200K",
     "price_in": 1.00, "price_out": 5.00,
     "blurb": "Fast Claude. Messages API, typed content, thinking.", "flags": []},
    {"id": "anthropic.claude-opus-4-7", "provider": "anthropic", "label": "Claude Opus 4.7",
     "surfaces": ["messages"], "ctx": "200K",
     "price_in": 15.00, "price_out": 75.00,
     "blurb": "Frontier reasoning. Deep case analysis.", "flags": ["thinking"]},
    {"id": "deepseek.v3.2", "provider": "deepseek", "label": "DeepSeek V3.2",
     "surfaces": ["chat_completions"], "ctx": "128K",
     "price_in": 0.28, "price_out": 0.42,
     "blurb": "Strong open-weight reasoner, low cost.", "flags": []},
    {"id": "qwen.qwen3-235b-a22b-2507", "provider": "qwen", "label": "Qwen3 235B",
     "surfaces": ["chat_completions"], "ctx": "256K",
     "price_in": 0.20, "price_out": 0.60,
     "blurb": "Widest open-weight catalog on Mantle.", "flags": []},
    {"id": "zai.glm-4-7", "provider": "zai", "label": "GLM 4.7",
     "surfaces": ["chat_completions"], "ctx": "128K",
     "price_in": 0.30, "price_out": 0.90,
     "blurb": "Z.AI GLM — agentic + tool use.", "flags": []},
    {"id": "minimax.minimax-m2.5", "provider": "minimax", "label": "MiniMax M2.5",
     "surfaces": ["chat_completions"], "ctx": "200K",
     "price_in": 0.30, "price_out": 1.20,
     "blurb": "Tool use is Mantle-only for this model.", "flags": []},
    {"id": "moonshotai.kimi-k2-thinking", "provider": "moonshotai", "label": "Kimi K2 Thinking",
     "surfaces": ["chat_completions"], "ctx": "256K",
     "price_in": 0.60, "price_out": 2.50,
     "blurb": "Long-horizon agentic reasoning.", "flags": []},
    {"id": "mistral.mistral-large-3-675b-instruct", "provider": "mistral", "label": "Mistral Large 3",
     "surfaces": ["chat_completions"], "ctx": "256K",
     "price_in": 2.00, "price_out": 6.00,
     "blurb": "EU-built flagship. (Prefix is mistral., not mistralai.)", "flags": []},
]

MODELS_BY_ID = {m["id"]: m for m in MODELS}


def host_for(region: str) -> str:
    return MANTLE_HOST_TEMPLATE.format(region=region or DEFAULT_REGION)


def public_config() -> dict:
    """Everything the frontend needs to render the catalog and wire views."""
    return {
        "host_template": MANTLE_HOST_TEMPLATE,
        "regions": REGIONS,
        "default_region": DEFAULT_REGION,
        "surfaces": SURFACES,
        "providers": PROVIDERS,
        "models": MODELS,
    }
