"""
The demo's single coherent storyline: Northwind Outfitters, an online
outdoor-gear retailer running an AI customer-experience platform on the
bedrock-mantle endpoint. The three API surfaces each power one stage of the
customer journey:

  Chat Completions (stateless)  -> Triage:     classify & route every inbound message
  Responses API   (stateful)    -> Concierge:  the customer-facing agent w/ memory + tools
  Messages API    (Anthropic)   -> Analyst:    Claude assists the human agent on hard cases

This module holds the canned business data and the "tool" functions that the
stateful Concierge surface calls server-side (order lookup, product search,
returns policy). Keeping it deterministic means the demo behaves identically
whether it runs against the real endpoint or the mock engine.
"""
from __future__ import annotations

COMPANY = {
    "name": "Northwind Outfitters",
    "tagline": "Gear for the long way round.",
    "support_email": "help@northwind-outfitters.example",
}

PRODUCTS = [
    {"sku": "NW-TENT-2P", "name": "Cirrus 2P Ultralight Tent", "category": "Shelter",
     "price": 389.00, "stock": 14, "rating": 4.7,
     "blurb": "1.1 kg freestanding two-person tent. 3-season."},
    {"sku": "NW-TENT-1P", "name": "Cirrus 1P Ultralight Tent", "category": "Shelter",
     "price": 329.00, "stock": 0, "rating": 4.6,
     "blurb": "880 g solo shelter. Currently backordered."},
    {"sku": "NW-BAG-0", "name": "Summit 0°F Down Bag", "category": "Sleep",
     "price": 459.00, "stock": 6, "rating": 4.8,
     "blurb": "850-fill water-resistant down. Rated to 0°F / -18°C."},
    {"sku": "NW-PAD-XL", "name": "CloudCore Insulated Pad XL", "category": "Sleep",
     "price": 179.00, "stock": 22, "rating": 4.5,
     "blurb": "R-value 5.4, 540 g. Pump sack included."},
    {"sku": "NW-PACK-55", "name": "Traverse 55L Pack", "category": "Packs",
     "price": 279.00, "stock": 9, "rating": 4.6,
     "blurb": "Adjustable torso, 1.4 kg, rain cover included."},
    {"sku": "NW-PACK-35", "name": "Traverse 35L Daypack", "category": "Packs",
     "price": 169.00, "stock": 31, "rating": 4.4,
     "blurb": "Fast-and-light overnight / big day pack."},
    {"sku": "NW-BOOT-MID", "name": "Granite Mid GTX Boot", "category": "Footwear",
     "price": 215.00, "stock": 18, "rating": 4.3,
     "blurb": "Waterproof leather/textile mid. Vibram outsole."},
    {"sku": "NW-STOVE-TI", "name": "Ember Ti Canister Stove", "category": "Cooking",
     "price": 64.00, "stock": 40, "rating": 4.7,
     "blurb": "45 g titanium stove. Boils 1 L in ~3.5 min."},
    {"sku": "NW-FILT-SQ", "name": "ClearFlow Squeeze Filter", "category": "Water",
     "price": 39.00, "stock": 55, "rating": 4.6,
     "blurb": "0.1-micron hollow-fiber filter. 100k L lifespan."},
    {"sku": "NW-JKT-RAIN", "name": "Stratus Hardshell Jacket", "category": "Apparel",
     "price": 245.00, "stock": 12, "rating": 4.5,
     "blurb": "3-layer waterproof/breathable shell, 320 g."},
]
PRODUCTS_BY_SKU = {p["sku"]: p for p in PRODUCTS}

ORDERS = {
    "NW-100423": {
        "order_id": "NW-100423", "customer": "Jordan Avery", "placed": "2026-05-21",
        "status": "Delivered 2026-05-26",
        "items": [{"sku": "NW-TENT-2P", "qty": 1}, {"sku": "NW-PAD-XL", "qty": 2}],
        "total": 747.00, "carrier": "UPS", "tracking": "1Z-NW-88241",
        "note": "Customer reports a snapped tent pole segment on first setup.",
    },
    "NW-100588": {
        "order_id": "NW-100588", "customer": "Jordan Avery", "placed": "2026-05-29",
        "status": "Backordered — Cirrus 1P out of stock",
        "items": [{"sku": "NW-TENT-1P", "qty": 1}],
        "total": 329.00, "carrier": "—", "tracking": "—",
        "note": "ETA to restock: ~10 days. Customer wants a date.",
    },
}

POLICIES = {
    "returns": {
        "title": "Returns & Exchanges",
        "text": "Unused gear can be returned within 90 days for a full refund. "
                "Defective items are covered regardless of date under the Trailhead Warranty.",
    },
    "warranty": {
        "title": "Trailhead Lifetime Warranty",
        "text": "Manufacturing defects (seams, poles, zippers, delamination) are repaired "
                "or replaced free for the life of the product. Wear-and-tear is excluded. "
                "Defective structural parts ship a free replacement part next-business-day.",
    },
    "shipping": {
        "title": "Shipping",
        "text": "Free standard shipping over $99. 2-day available. Backordered items ship "
                "as soon as stock arrives; customers may cancel a backorder any time before fulfillment.",
    },
}

CUSTOMER = {
    "name": "Jordan Avery", "tier": "Trail Club (Gold)", "since": "2021",
    "lifetime_value": 4280.00, "open_orders": ["NW-100423", "NW-100588"],
}


# --------------------------------------------------------------------------
# "Tools" — these are what the stateful Responses/Concierge surface invokes
# server-side. The mock engine and (optionally) a real MCP/Lambda connector
# would expose exactly these.
# --------------------------------------------------------------------------
def search_products(query: str, max_price: float | None = None) -> list[dict]:
    q = (query or "").lower()
    hits = []
    for p in PRODUCTS:
        hay = f"{p['name']} {p['category']} {p['blurb']}".lower()
        if any(tok in hay for tok in q.split()) or q in hay:
            if max_price is None or p["price"] <= max_price:
                hits.append(p)
    if not hits and q:  # soft fallback so the demo always shows something
        hits = [p for p in PRODUCTS if max_price is None or p["price"] <= max_price][:3]
    return hits[:5]


def get_order(order_id: str) -> dict | None:
    return ORDERS.get((order_id or "").strip().upper())


def get_policy(topic: str) -> dict | None:
    return POLICIES.get((topic or "").strip().lower())


# Tool schemas advertised to the model (OpenAI / Responses tool format).
TOOL_SCHEMAS = [
    {"type": "function", "name": "get_order",
     "description": "Look up a Northwind order by its ID (e.g. NW-100423).",
     "parameters": {"type": "object", "properties": {
         "order_id": {"type": "string"}}, "required": ["order_id"]}},
    {"type": "function", "name": "search_products",
     "description": "Search the Northwind catalog. Optional max_price filter.",
     "parameters": {"type": "object", "properties": {
         "query": {"type": "string"},
         "max_price": {"type": "number"}}, "required": ["query"]}},
    {"type": "function", "name": "get_policy",
     "description": "Fetch a support policy: returns, warranty, or shipping.",
     "parameters": {"type": "object", "properties": {
         "topic": {"type": "string", "enum": ["returns", "warranty", "shipping"]}},
        "required": ["topic"]}},
]


# --------------------------------------------------------------------------
# Suggested prompts shown as one-click chips in each console.
# --------------------------------------------------------------------------
SAMPLE_PROMPTS = {
    "triage": [
        "My tent pole snapped the FIRST time I set it up. This is unacceptable.",
        "Hi! Do you know when the Cirrus 1P will be back in stock?",
        "Where's my order NW-100423? It said delivered but I want a return label.",
        "Just wanted to say the Summit 0 bag kept me warm at 12°F. Amazing.",
    ],
    "concierge": [
        "Hi, I'm Jordan. A pole on my Cirrus 2P tent snapped on the first setup.",
        "What can I do about it — I'm leaving for a trip in 5 days?",
        "Also, can you find me a lightweight backup shelter under $350?",
    ],
    "analyst": [
        "Draft a resolution for Jordan Avery's snapped-pole case on order NW-100423, "
        "citing the right policy and proposing concrete next steps.",
    ],
}
