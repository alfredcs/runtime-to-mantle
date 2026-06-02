"""
The mock engine. It makes the demo bullet-proof for live audiences: when no AWS
credentials / Mantle access are present (the default), this produces realistic,
scenario-aware answers shaped EXACTLY like the real provider responses, with
believable token counts, latency and cost.

Crucially it implements *real* server-side conversation state for the Responses
surface (keyed by response id, chained via previous_response_id) — so the
"the server remembers, the client doesn't re-send history" story is genuine,
not faked.

The "intelligence" is deterministic keyword routing over the Northwind data in
scenarios.py. It's intentionally simple; the point is the API surfaces and the
business framing, not a real model.
"""
from __future__ import annotations

import json
import re
import time
import uuid

import scenarios as S
from config import MODELS_BY_ID


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:24]}"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    # ~4 chars/token is a serviceable approximation for the demo.
    return max(1, round(len(text) / 4))


def cost_usd(model_id: str, in_tok: int, out_tok: int) -> float:
    m = MODELS_BY_ID.get(model_id)
    if not m:
        return 0.0
    return round(in_tok / 1e6 * m["price_in"] + out_tok / 1e6 * m["price_out"], 6)


def latency_ms(model_id: str, out_tok: int) -> int:
    """Believable latency: small/cheap models are faster per token."""
    m = MODELS_BY_ID.get(model_id, {})
    pout = m.get("price_out", 1.0)
    per_tok = 4.5 + min(pout, 75) * 0.12   # ms per output token, scales w/ tier
    base = 180 + (60 if m.get("provider") == "anthropic" else 0)
    return int(base + out_tok * per_tok)


# ===========================================================================
# Surface 1 — Chat Completions  (Triage: stateless classification)
# ===========================================================================
def triage(message: str) -> dict:
    m = (message or "").lower()

    def has(*words):
        return any(w in m for w in words)

    if has("snap", "broke", "broken", "defect", "tore", "ripped", "unacceptable", "failed"):
        parsed = {"intent": "warranty_claim", "sentiment": "frustrated",
                  "priority": "P1 - high", "queue": "Gear Warranty",
                  "entities": _entities(m),
                  "summary": "Customer reports a defective/broken item and is upset.",
                  "suggested_macro": "WARRANTY_DEFECT_APOLOGY_PLUS_REPLACEMENT"}
    elif has("stock", "back in", "restock", "available", "when will", "eta"):
        parsed = {"intent": "stock_inquiry", "sentiment": "neutral",
                  "priority": "P3 - medium", "queue": "Sales",
                  "entities": _entities(m),
                  "summary": "Customer asking about availability / restock date.",
                  "suggested_macro": "BACKORDER_ETA_WITH_NOTIFY_OPTION"}
    elif has("return", "refund", "label", "where", "track", "status", "delivered"):
        parsed = {"intent": "order_status_or_return", "sentiment": "neutral",
                  "priority": "P2 - medium", "queue": "Order Support",
                  "entities": _entities(m),
                  "summary": "Customer asking about an order status or a return/label.",
                  "suggested_macro": "ORDER_LOOKUP_THEN_RETURN_LABEL"}
    elif has("thank", "amazing", "love", "great", "awesome", "warm", "perfect", "happy"):
        parsed = {"intent": "praise_feedback", "sentiment": "positive",
                  "priority": "P4 - low", "queue": "Voice of Customer",
                  "entities": _entities(m),
                  "summary": "Positive feedback / product praise.",
                  "suggested_macro": "THANK_CUSTOMER_INVITE_REVIEW"}
    else:
        parsed = {"intent": "general_question", "sentiment": "neutral",
                  "priority": "P3 - medium", "queue": "General",
                  "entities": _entities(m),
                  "summary": "General inquiry; route to first-available agent.",
                  "suggested_macro": "GENERAL_GREETING"}
    return parsed


def _entities(m: str) -> dict:
    ent = {}
    order = re.search(r"nw-?\d{5,6}", m)
    if order:
        ent["order_id"] = order.group(0).upper().replace("NW", "NW-").replace("--", "-")
    for p in S.PRODUCTS:
        if p["name"].split()[0].lower() in m or p["sku"].lower() in m:
            ent.setdefault("products", []).append(p["sku"])
    return ent


# ===========================================================================
# Surface 2 — Responses API  (Concierge: STATEFUL, server-side memory + tools)
# ===========================================================================
# Server-side conversation store. This is the real thing: state lives here on
# the "server", chained by previous_response_id. The client never re-sends it.
_CONVERSATIONS: dict[str, dict] = {}


def _new_state(previous_response_id: str | None) -> dict:
    prior = _CONVERSATIONS.get(previous_response_id or "")
    if prior:
        return {"history": list(prior["history"]), "facts": dict(prior["facts"])}
    return {"history": [], "facts": {}}


def concierge(user_input: str, previous_response_id: str | None) -> dict:
    state = _new_state(previous_response_id)
    facts = state["facts"]
    msg = (user_input or "")
    low = msg.lower()
    tool_events: list[dict] = []
    memory_used = []

    # --- update memory from this turn ---
    name = re.search(r"\b(?:i'?m|my name is|this is)\s+([A-Z][a-z]+)", msg)
    if name:
        facts["name"] = name.group(1)
    if any(w in low for w in ("snap", "pole", "broke", "broken")):
        facts["issue"] = "snapped tent pole on a Cirrus 2P (first setup)"
        facts.setdefault("product", "NW-TENT-2P")
    trip = re.search(r"(\d+)\s*day", low)
    if trip:
        facts["deadline_days"] = int(trip.group(1))

    # --- decide tools + answer ---
    if previous_response_id and facts.get("name"):
        memory_used.append(f"name = {facts['name']}")
    if facts.get("issue") and previous_response_id:
        memory_used.append(f"issue = {facts['issue']}")

    if any(w in low for w in ("find", "recommend", "backup", "shelter", "tent", "pack", "under", "looking for")):
        price = re.search(r"\$?\s?(\d{2,4})", low)
        max_price = float(price.group(1)) if price and ("under" in low or "$" in low) else None
        results = S.search_products(_search_terms(low), max_price=max_price)
        tool_events.append({"name": "search_products",
                            "arguments": {"query": _search_terms(low), "max_price": max_price},
                            "result": [{"sku": r["sku"], "name": r["name"],
                                        "price": r["price"], "stock": r["stock"]} for r in results]})
        text = _concierge_reco_text(facts, results, max_price)
    elif (facts.get("issue") and (previous_response_id or "what can i do" in low
                                  or "deadline" in low or facts.get("deadline_days"))):
        order = S.get_order("NW-100423")
        tool_events.append({"name": "get_order", "arguments": {"order_id": "NW-100423"},
                            "result": {"order_id": order["order_id"], "status": order["status"],
                                       "items": order["items"], "note": order["note"]}})
        pol = S.get_policy("warranty")
        tool_events.append({"name": "get_policy", "arguments": {"topic": "warranty"},
                            "result": {"title": pol["title"], "text": pol["text"]}})
        text = _concierge_resolve_text(facts)
    else:
        pol = S.get_policy("warranty")
        if facts.get("issue"):
            tool_events.append({"name": "get_policy", "arguments": {"topic": "warranty"},
                                "result": {"title": pol["title"], "text": pol["text"]}})
        text = _concierge_open_text(facts)

    # --- persist new state, return a fresh response id ---
    rid = _id("resp")
    state["history"].append({"role": "user", "content": msg})
    state["history"].append({"role": "assistant", "content": text})
    _CONVERSATIONS[rid] = state
    return {"id": rid, "text": text, "tool_events": tool_events,
            "facts": facts, "memory_used": memory_used,
            "history_len": len(state["history"]), "previous_response_id": previous_response_id}


def _search_terms(low: str) -> str:
    for kw in ("shelter", "tent", "pack", "daypack", "bag", "stove", "filter", "jacket", "boot", "pad"):
        if kw in low:
            return kw
    return "ultralight shelter"


def _concierge_open_text(facts) -> str:
    nm = facts.get("name", "there")
    if facts.get("issue"):
        return (f"Oh no — I'm really sorry, {nm}. A {facts['issue']} should never happen, "
                f"and it's exactly what our Trailhead Lifetime Warranty is for. Structural "
                f"defects like poles are covered for the life of the product, and we ship the "
                f"replacement part next-business-day at no charge. Want me to pull up the order "
                f"and start that now?")
    return (f"Hi {nm}! Welcome to Northwind Outfitters. How can I help with your gear today?")


def _concierge_resolve_text(facts) -> str:
    nm = facts.get("name", "there")
    days = facts.get("deadline_days")
    urgency = (f" Since you're leaving in {days} days, I've flagged this for "
               f"next-business-day shipping so the new pole reaches you in time."
               if days else "")
    return (f"Got it, {nm} — I found your order **NW-100423** (Cirrus 2P + 2 sleeping pads, "
            f"delivered May 26). Because the snapped pole is a structural defect, it's fully "
            f"covered by the **Trailhead Lifetime Warranty**: I'm sending a free replacement "
            f"pole segment, no return of the tent required.{urgency} You'll get a tracking "
            f"number by email shortly. Anything else I can sort out before your trip?")


def _concierge_reco_text(facts, results, max_price) -> str:
    nm = facts.get("name", "there")
    if not results:
        return f"I couldn't find a match under that budget, {nm} — want me to widen the search?"
    top = results[0]
    cap = f" under ${int(max_price)}" if max_price else ""
    lines = [f"- **{r['name']}** ({r['sku']}) — ${r['price']:.0f}"
             + (" · _backordered_" if r["stock"] == 0 else f" · {r['stock']} in stock")
             for r in results[:3]]
    backup_note = ""
    if facts.get("issue"):
        backup_note = (" Given your Cirrus 2P is just waiting on a replacement pole, this would "
                       "be a solid lightweight backup so you're covered either way.")
    return (f"Here are the best lightweight shelters{cap}, {nm}:\n\n" + "\n".join(lines) +
            f"\n\nMy pick is the **{top['name']}** for the weight-to-price ratio.{backup_note}")


# ===========================================================================
# Surface 3 — Messages API  (Analyst: Anthropic-native, typed content + thinking)
# ===========================================================================
def analyst(case_prompt: str) -> dict:
    order = S.get_order("NW-100423")
    pol = S.get_policy("warranty")
    cust = S.CUSTOMER

    thinking = (
        "Let me work the case. Order NW-100423 shows a Cirrus 2P delivered 2026-05-26; the "
        "note says a pole segment snapped on first setup. A first-setup structural failure is a "
        "manufacturing defect, not wear — so this is a Trailhead Lifetime Warranty case, NOT a "
        "90-day return. Warranty path ships a free replacement part next-business-day, which is "
        "the fastest resolution and avoids making a Gold-tier customer return the whole tent. "
        "The customer flagged a trip in 5 days, so speed and a goodwill gesture matter for CSAT."
    )

    text = f"""## Case resolution — {cust['name']} · order {order['order_id']}

**Classification:** Warranty (manufacturing defect) — *not* a standard return.

**Root cause:** Pole segment snapped on first setup → structural defect covered by the
**{pol['title']}**. Wear-and-tear exclusions do not apply.

**Entitlement:** Free replacement pole segment, shipped next-business-day. No need for the
customer to return the tent. Customer is **{cust['tier']}**, LTV ${cust['lifetime_value']:,.0f} —
authorize a goodwill credit.

**Recommended reply to send:**
> Hi {cust['name']}, I'm so sorry your Cirrus 2P pole snapped on the first pitch — that's a
> manufacturing defect and it's fully covered. I've shipped a replacement pole segment
> next-business-day (free), so you'll be set well before your trip. I've also added a $25
> trail credit for the hassle. Adventure on!

**Next steps:** (1) Trigger warranty SKU NW-TENT-2P-POLE replacement. (2) Apply $25 goodwill
credit. (3) Set a 5-day follow-up to confirm delivery before the customer's trip."""

    return {"thinking": thinking, "text": text}


# ===========================================================================
# Build provider-shaped RESPONSE bodies (so the wire inspector is accurate)
# ===========================================================================
def chat_completion_response(model_id: str, content: str, in_tok: int, out_tok: int) -> dict:
    return {
        "id": _id("chatcmpl"),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": in_tok, "completion_tokens": out_tok,
                  "total_tokens": in_tok + out_tok},
    }


def responses_response(model_id: str, rid: str, text: str, tool_events: list,
                       previous_response_id: str | None, in_tok: int, out_tok: int) -> dict:
    output = []
    for ev in tool_events:
        output.append({"type": "function_call", "name": ev["name"],
                       "arguments": json.dumps(ev["arguments"]), "status": "completed"})
    output.append({"type": "message", "role": "assistant",
                   "content": [{"type": "output_text", "text": text}]})
    return {
        "id": rid,
        "object": "response",
        "created_at": int(time.time()),
        "model": model_id,
        "previous_response_id": previous_response_id,
        "store": True,
        "status": "completed",
        "output": output,
        "output_text": text,
        "usage": {"input_tokens": in_tok, "output_tokens": out_tok,
                  "total_tokens": in_tok + out_tok},
    }


def messages_response(model_id: str, thinking: str, text: str, in_tok: int, out_tok: int) -> dict:
    content = []
    if thinking:
        content.append({"type": "thinking", "thinking": thinking})
    content.append({"type": "text", "text": text})
    return {
        "id": _id("msg"),
        "type": "message",
        "role": "assistant",
        "model": model_id,
        "content": content,
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": in_tok, "output_tokens": out_tok},
    }
