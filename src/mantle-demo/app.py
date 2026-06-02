"""
Mantle Studio — FastAPI backend.

Serves the single-page UI and exposes one route per Mantle surface. Each route
streams newline-delimited JSON (NDJSON) events to the browser:

    {"type":"request", ...wire...}      # the exact HTTP call (Wire Inspector)
    {"type":"tool", ...}                # server-side tool calls (Responses only)
    {"type":"thinking_delta", ...}      # extended thinking (Messages only)
    {"type":"delta", "text": ...}       # streamed answer tokens
    {"type":"done", "response": ...,    # final provider-shaped body + metrics
                    "metrics": ...}

DEMO mode (default) answers from mock_engine. LIVE mode (MANTLE_LIVE=1 + creds)
calls the real bedrock-mantle endpoint and falls back to the mock on any error.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import mock_engine as mock
import scenarios as S
from config import DEFAULT_REGION, MODELS_BY_ID, SURFACES, public_config
from mantle_client import build_request, call_live

STATIC = Path(__file__).parent / "static"
LIVE_REQUESTED = os.environ.get("MANTLE_LIVE", "").lower() in ("1", "true", "yes")

app = FastAPI(title="Mantle Studio")


def creds_detected() -> bool:
    if any(os.environ.get(v) for v in ("AWS_BEARER_TOKEN_BEDROCK", "MANTLE_API_KEY", "OPENAI_API_KEY")):
        return True
    try:
        import aws_bedrock_token_generator  # noqa: F401
        return True
    except Exception:
        return False


def mode() -> str:
    return "LIVE" if (LIVE_REQUESTED and creds_detected()) else "DEMO"


# --------------------------------------------------------------------------- helpers
def ndjson(obj: dict) -> bytes:
    return (json.dumps(obj) + "\n").encode()


async def stream_words(text: str, kind: str = "delta", chunk: int = 3, delay: float = 0.022):
    """Yield NDJSON delta events, a few words at a time, to animate streaming."""
    words = text.split(" ")
    for i in range(0, len(words), chunk):
        piece = " ".join(words[i:i + chunk])
        if i + chunk < len(words):
            piece += " "
        yield ndjson({"type": kind, "text": piece})
        await asyncio.sleep(delay)


def metrics(model_id: str, in_tok: int, out_tok: int, started: float, live: bool) -> dict:
    return {
        "model": model_id,
        "input_tokens": in_tok,
        "output_tokens": out_tok,
        "total_tokens": in_tok + out_tok,
        "cost_usd": mock.cost_usd(model_id, in_tok, out_tok),
        "latency_ms": int((time.time() - started) * 1000) if live
        else mock.latency_ms(model_id, out_tok),
        "live": live,
    }


# --------------------------------------------------------------------------- request models
class TriageReq(BaseModel):
    message: str
    model: str = "openai.gpt-oss-20b"
    region: str = DEFAULT_REGION


class ConciergeReq(BaseModel):
    input: str
    model: str = "openai.gpt-oss-120b"
    region: str = DEFAULT_REGION
    previous_response_id: str | None = None
    turn: int = 1


class AnalystReq(BaseModel):
    prompt: str
    model: str = "anthropic.claude-opus-4-7"
    region: str = DEFAULT_REGION


class CompareReq(BaseModel):
    prompt: str
    region: str = DEFAULT_REGION


# --------------------------------------------------------------------------- body builders
TRIAGE_SYSTEM = ("You are Northwind Outfitters' support triage classifier. Classify the "
                 "customer message and respond with ONLY a JSON object containing: intent, "
                 "sentiment, priority, queue, entities, summary, suggested_macro.")

CONCIERGE_INSTRUCTIONS = ("You are Aria, Northwind Outfitters' customer concierge. Be warm and "
                          "concise. Use the provided tools to look up orders, search products and "
                          "cite policy. Resolve the customer's issue end to end.")

ANALYST_SYSTEM = ("You are a senior support analyst assisting a human agent. Read the case file "
                  "(including any attached photo), reason carefully, then produce a structured "
                  "resolution: classification, root cause, entitlement, a ready-to-send reply, "
                  "and next steps. Cite the correct policy.")

# A realistic (truncated) base64 image block — demonstrates Messages typed content.
_TRUNCATED_JPEG = "/9j/4AAQSkZJRgABAQEAYABgAAD…(truncated customer photo bytes)…2Q=="


def triage_body(req: TriageReq) -> dict:
    return {
        "model": req.model,
        "messages": [
            {"role": "system", "content": TRIAGE_SYSTEM},
            {"role": "user", "content": req.message},
        ],
        "max_tokens": 300,
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }


def concierge_body(req: ConciergeReq) -> dict:
    body: dict = {
        "model": req.model,
        "input": [{"role": "user", "content": req.input}],
        "tools": S.TOOL_SCHEMAS,
        "store": True,
    }
    if req.previous_response_id:
        # The turn-2+ payload: NO transcript. Just the new turn + the pointer.
        body["previous_response_id"] = req.previous_response_id
    else:
        body["instructions"] = CONCIERGE_INSTRUCTIONS
    return body


def analyst_body(req: AnalystReq) -> dict:
    return {
        "model": req.model,
        "max_tokens": 1024,
        "system": ANALYST_SYSTEM,
        "thinking": {"type": "enabled", "budget_tokens": 1024},
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": req.prompt
                    + "\n\nCASE FILE: order NW-100423 — Cirrus 2P, delivered 2026-05-26, "
                      "customer reports snapped pole on first setup."},
                {"type": "image", "source": {"type": "base64",
                                              "media_type": "image/jpeg",
                                              "data": _TRUNCATED_JPEG}},
            ],
        }],
    }


# --------------------------------------------------------------------------- routes
@app.get("/api/config")
def api_config():
    cfg = public_config()
    cfg["mode"] = mode()
    cfg["live_requested"] = LIVE_REQUESTED
    cfg["creds_detected"] = creds_detected()
    cfg["company"] = S.COMPANY
    cfg["customer"] = S.CUSTOMER
    cfg["products"] = S.PRODUCTS
    cfg["orders"] = S.ORDERS
    cfg["sample_prompts"] = S.SAMPLE_PROMPTS
    return JSONResponse(cfg)


@app.post("/api/triage")
async def api_triage(req: TriageReq):
    body = triage_body(req)
    wire = build_request("chat_completions", req.region, req.model, body, live=mode() == "LIVE")

    async def gen():
        started = time.time()
        yield ndjson({"type": "request", "surface": "chat_completions", "wire": wire})
        live = mode() == "LIVE"
        content = None
        if live:
            try:
                resp = await call_live("chat_completions", req.region, body)
                content = resp["choices"][0]["message"]["content"]
                in_tok = resp.get("usage", {}).get("prompt_tokens") or mock.estimate_tokens(json.dumps(body))
                out_tok = resp.get("usage", {}).get("completion_tokens") or mock.estimate_tokens(content)
            except Exception as e:  # graceful fallback
                yield ndjson({"type": "notice", "text": f"LIVE call failed ({e}); showing simulated response."})
                live = False
        if not live:
            parsed = mock.triage(req.message)
            content = json.dumps(parsed, indent=2)
            in_tok = mock.estimate_tokens(json.dumps(body))
            out_tok = mock.estimate_tokens(content)
            resp = mock.chat_completion_response(req.model, content, in_tok, out_tok)

        async for ev in stream_words(content, chunk=4, delay=0.012):
            yield ev
        m = metrics(req.model, in_tok, out_tok, started, live)
        try:
            parsed_out = json.loads(content)
        except Exception:
            parsed_out = None
        yield ndjson({"type": "done", "response": resp, "metrics": m, "parsed": parsed_out})

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/concierge")
async def api_concierge(req: ConciergeReq):
    body = concierge_body(req)
    wire = build_request("responses", req.region, req.model, body, live=mode() == "LIVE")

    async def gen():
        started = time.time()
        # How many messages a *stateless* API would have had to resend this turn.
        stateless_would_send = max(1, (req.turn - 1) * 2 + 1)
        yield ndjson({"type": "request", "surface": "responses", "wire": wire,
                      "stateless_would_send": stateless_would_send,
                      "responses_sent": 1})
        live = mode() == "LIVE"
        ans = None
        if live:
            try:
                resp = await call_live("responses", req.region, body)
                text = resp.get("output_text") or _walk_output_text(resp)
                tool_events = _walk_tool_calls(resp)
                rid = resp.get("id")
                in_tok = resp.get("usage", {}).get("input_tokens") or mock.estimate_tokens(json.dumps(body))
                out_tok = resp.get("usage", {}).get("output_tokens") or mock.estimate_tokens(text)
                ans = {"id": rid, "memory_used": [], "history_len": None}
            except Exception as e:
                yield ndjson({"type": "notice", "text": f"LIVE call failed ({e}); showing simulated response."})
                live = False
        if not live:
            ans = mock.concierge(req.input, req.previous_response_id)
            text, tool_events, rid = ans["text"], ans["tool_events"], ans["id"]
            in_tok = mock.estimate_tokens(json.dumps(body))
            out_tok = mock.estimate_tokens(text)
            resp = mock.responses_response(req.model, rid, text, tool_events,
                                           req.previous_response_id, in_tok, out_tok)

        for ev in tool_events:
            yield ndjson({"type": "tool", "name": ev["name"],
                          "arguments": ev["arguments"], "result": ev["result"]})
            await asyncio.sleep(0.28)
        async for ev in stream_words(text, chunk=3, delay=0.02):
            yield ev
        m = metrics(req.model, in_tok, out_tok, started, live)
        yield ndjson({"type": "done", "response": resp, "metrics": m,
                      "response_id": rid,
                      "memory_used": ans.get("memory_used", []),
                      "history_len": ans.get("history_len")})

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/analyst")
async def api_analyst(req: AnalystReq):
    body = analyst_body(req)
    wire = build_request("messages", req.region, req.model, body, live=mode() == "LIVE")

    async def gen():
        started = time.time()
        yield ndjson({"type": "request", "surface": "messages", "wire": wire})
        live = mode() == "LIVE"
        thinking = text = None
        if live:
            try:
                resp = await call_live("messages", req.region, body)
                thinking = _join_blocks(resp, "thinking", "thinking")
                text = _join_blocks(resp, "text", "text")
                in_tok = resp.get("usage", {}).get("input_tokens") or mock.estimate_tokens(json.dumps(body))
                out_tok = resp.get("usage", {}).get("output_tokens") or mock.estimate_tokens(text)
            except Exception as e:
                yield ndjson({"type": "notice", "text": f"LIVE call failed ({e}); showing simulated response."})
                live = False
        if not live:
            ans = mock.analyst(req.prompt)
            thinking, text = ans["thinking"], ans["text"]
            in_tok = mock.estimate_tokens(json.dumps(body))
            out_tok = mock.estimate_tokens(thinking + text)
            resp = mock.messages_response(req.model, thinking, text, in_tok, out_tok)

        if thinking:
            async for ev in stream_words(thinking, kind="thinking_delta", chunk=4, delay=0.01):
                yield ev
            yield ndjson({"type": "thinking_done"})
        async for ev in stream_words(text, chunk=3, delay=0.018):
            yield ev
        m = metrics(req.model, in_tok, out_tok, started, live)
        yield ndjson({"type": "done", "response": resp, "metrics": m})

    return StreamingResponse(gen(), media_type="application/x-ndjson")


@app.post("/api/compare")
async def api_compare(req: CompareReq):
    """Run the same prompt through all three surfaces (non-streaming) for the
    side-by-side view. Always uses the mock so the comparison is instant and
    deterministic regardless of mode."""
    out = []

    # 1) Chat Completions
    cc_model = "openai.gpt-oss-120b"
    cc_body = triage_body(TriageReq(message=req.prompt, model=cc_model, region=req.region))
    parsed = mock.triage(req.prompt)
    cc_text = json.dumps(parsed, indent=2)
    out.append(_compare_entry("chat_completions", req.region, cc_model, cc_body, cc_text,
                              mock.chat_completion_response(cc_model, cc_text,
                                                            mock.estimate_tokens(json.dumps(cc_body)),
                                                            mock.estimate_tokens(cc_text))))

    # 2) Responses
    r_model = "openai.gpt-oss-120b"
    r_body = concierge_body(ConciergeReq(input=req.prompt, model=r_model, region=req.region))
    ans = mock.concierge(req.prompt, None)
    r_resp = mock.responses_response(r_model, ans["id"], ans["text"], ans["tool_events"], None,
                                     mock.estimate_tokens(json.dumps(r_body)),
                                     mock.estimate_tokens(ans["text"]))
    out.append(_compare_entry("responses", req.region, r_model, r_body, ans["text"], r_resp))

    # 3) Messages
    m_model = "anthropic.claude-opus-4-7"
    m_body = analyst_body(AnalystReq(prompt=req.prompt, model=m_model, region=req.region))
    a = mock.analyst(req.prompt)
    m_resp = mock.messages_response(m_model, a["thinking"], a["text"],
                                    mock.estimate_tokens(json.dumps(m_body)),
                                    mock.estimate_tokens(a["thinking"] + a["text"]))
    out.append(_compare_entry("messages", req.region, m_model, m_body, a["text"], m_resp))

    return JSONResponse({"surfaces": out})


def _compare_entry(skey, region, model, body, text, resp):
    wire = build_request(skey, region, model, body)
    in_tok = mock.estimate_tokens(json.dumps(body))
    out_tok = mock.estimate_tokens(text)
    return {"surface": skey, "meta": SURFACES[skey], "wire": wire, "response": resp,
            "text": text, "metrics": {"input_tokens": in_tok, "output_tokens": out_tok,
                                       "cost_usd": mock.cost_usd(model, in_tok, out_tok),
                                       "latency_ms": mock.latency_ms(model, out_tok)}}


# ---- helpers for parsing real LIVE responses ----
def _walk_output_text(resp: dict) -> str:
    for item in resp.get("output", []):
        if item.get("type") == "message":
            for c in item.get("content", []):
                if c.get("type") in ("output_text", "text"):
                    return c.get("text", "")
    return ""


def _walk_tool_calls(resp: dict) -> list:
    evs = []
    for item in resp.get("output", []):
        if item.get("type") in ("function_call", "tool_call"):
            try:
                args = json.loads(item.get("arguments", "{}"))
            except Exception:
                args = {}
            evs.append({"name": item.get("name"), "arguments": args, "result": "(executed server-side)"})
    return evs


def _join_blocks(resp: dict, block_type: str, field: str) -> str:
    return "".join(c.get(field, "") for c in resp.get("content", []) if c.get("type") == block_type)


# --------------------------------------------------------------------------- static
@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


app.mount("/", StaticFiles(directory=STATIC), name="static")
