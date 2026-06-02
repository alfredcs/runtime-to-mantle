"""QA test for the two scoped Concierge changes.

  1. openai.gpt-5.4 is offered on the Concierge (Responses) stage, in addition
     to the existing gpt-oss models.
  2. The Responses surface uses BEDROCK_MANTLE_URL for its endpoint when set.

Run: python qa_test.py   (DEMO mode; no AWS creds needed)
"""
import json
import os

# Clean baseline — _base_url reads BEDROCK_MANTLE_URL lazily at call time.
os.environ.pop("BEDROCK_MANTLE_URL", None)

import config
from mantle_client import build_request

results = []


def check(name, cond):
    results.append((name, bool(cond)))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}")


# 1) Catalog: gpt-5.4 exists, reachable via Responses, priced.
m = config.MODELS_BY_ID.get("openai.gpt-5.4")
check("gpt-5.4 present in catalog", m is not None)
check("gpt-5.4 reachable via Responses surface", bool(m) and "responses" in m["surfaces"])
check("gpt-5.4 has illustrative pricing", bool(m) and m["price_in"] > 0 and m["price_out"] > 0)

# 2) Concierge stage == models carrying the responses surface; gpt-5.4 joins gpt-oss.
concierge = [x["id"] for x in config.MODELS if "responses" in x["surfaces"]]
check("Concierge still offers gpt-oss-20b", "openai.gpt-oss-20b" in concierge)
check("Concierge still offers gpt-oss-120b", "openai.gpt-oss-120b" in concierge)
check("Concierge now offers gpt-5.4", "openai.gpt-5.4" in concierge)

# 3) Default endpoint host (no override).
w = build_request("responses", "us-east-1", "openai.gpt-5.4", {"x": 1})
check("Responses default host",
      w["url"] == "https://bedrock-mantle.us-east-1.api.aws/v1/responses")

# 4) BEDROCK_MANTLE_URL overrides the Responses endpoint only.
os.environ["BEDROCK_MANTLE_URL"] = "https://my-mantle.example.com"
w = build_request("responses", "us-east-1", "openai.gpt-5.4", {"x": 1})
check("Responses honors BEDROCK_MANTLE_URL",
      w["url"] == "https://my-mantle.example.com/v1/responses")
cc = build_request("chat_completions", "us-east-1", "openai.gpt-oss-20b", {"x": 1})
check("Chat Completions ignores the override",
      cc["url"] == "https://bedrock-mantle.us-east-1.api.aws/v1/chat/completions")

# 5) Trailing /v1 (OpenAI base_url form) is trimmed so the path appends cleanly.
os.environ["BEDROCK_MANTLE_URL"] = "https://my-mantle.example.com/v1/"
w = build_request("responses", "eu-west-1", "openai.gpt-5.4", {"x": 1})
check("Override trims a trailing /v1",
      w["url"] == "https://my-mantle.example.com/v1/responses")

# 6) End-to-end through the app (DEMO mode).
from fastapi.testclient import TestClient
import app as app_module

client = TestClient(app_module.app)

cfg = client.get("/api/config").json()
check("/api/config advertises gpt-5.4",
      "openai.gpt-5.4" in [x["id"] for x in cfg["models"]])

r = client.post("/api/concierge", json={
    "input": "Hi, I'm Dana and my tent pole snapped.",
    "model": "openai.gpt-5.4", "turn": 1})
check("/api/concierge returns 200", r.status_code == 200)

events = [json.loads(line) for line in r.text.splitlines() if line.strip()]
req = next((e for e in events if e["type"] == "request"), None)
done = next((e for e in events if e["type"] == "done"), None)
check("/api/concierge streamed request + done", req is not None and done is not None)
check("/api/concierge wire uses the override URL",
      bool(req) and req["wire"]["url"] == "https://my-mantle.example.com/v1/responses")
check("/api/concierge metrics report gpt-5.4",
      bool(done) and done["metrics"]["model"] == "openai.gpt-5.4")
check("/api/concierge cost computed for gpt-5.4",
      bool(done) and done["metrics"]["cost_usd"] > 0)

os.environ.pop("BEDROCK_MANTLE_URL", None)
n_pass = sum(1 for _, ok in results if ok)
print(f"\n{n_pass}/{len(results)} checks passed")
raise SystemExit(0 if n_pass == len(results) else 1)
