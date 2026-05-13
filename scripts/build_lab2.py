"""Builds the three notebooks in src/lab2/."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))
from _nb import md, code, write_notebook


# ---------------------------------------------------------------------------
# Lab 2.1 — Streaming
# ---------------------------------------------------------------------------

streaming_cells = [
    md(
        """# Lab 2.1 — Streaming on Mantle

**Duration:** ~10 min · **Level:** L200 · **Lab 2 of 4 — part 1/3**

Streaming on Mantle uses **Server-Sent Events (SSE)** on every surface
(`/v1/chat/completions`, `/v1/responses`, `/anthropic/v1/messages`), but the
*event taxonomy* is different on each. This notebook:

1. Streams a completion through Chat Completions and shows how to accumulate
   `delta.content` fragments.
2. Streams through the Responses API and shows the typed events
   (`response.output_text.delta`, `response.completed`).
3. Streams through Anthropic Messages and shows `content_block_delta`.
4. Compares the three side-by-side so you know which one to reach for.
"""
    ),
    code(
        """import os
import sys
import time
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

from src.common.mantle import (
    openai_client, anthropic_client,
    GPT_OSS_120B, CLAUDE_OPUS_47,
)

client = openai_client()
anth = anthropic_client()
print("ready:", os.environ["AWS_REGION"])
"""
    ),
    md(
        """## 1. Chat Completions stream

Pass `stream=True`. Each yielded chunk exposes
`chunk.choices[0].delta.content` (string fragment) and, optionally,
`delta.tool_calls` for tool streaming (covered in Lab 2.2).

Set `stream_options={"include_usage": True}` to get a terminal chunk with
`usage` populated — otherwise you don't know how many tokens the stream
actually consumed.
"""
    ),
    code(
        """PROMPT = "Write a 60-word haiku-ish poem about the Nitro hypervisor."

t0 = time.time()
ttft = None
frags = 0
full_text = []
usage = None                          # populated by the terminal chunk

stream = client.chat.completions.create(
    model=GPT_OSS_120B,
    messages=[{"role": "user", "content": PROMPT}],
    max_tokens=120,
    stream=True,
    stream_options={"include_usage": True},
)

for chunk in stream:
    if chunk.choices and chunk.choices[0].delta.content:
        if ttft is None:
            ttft = time.time() - t0
        piece = chunk.choices[0].delta.content
        full_text.append(piece)
        print(piece, end="", flush=True)
        frags += 1
    if chunk.usage:
        usage = chunk.usage

print("\\n\\n--- stream stats ---")
print(f"TTFT            : {ttft:.2f} s" if ttft else "TTFT            : n/a (no content)")
print(f"total fragments : {frags}")
if usage:
    print(f"prompt_tokens     = {usage.prompt_tokens}")
    print(f"completion_tokens = {usage.completion_tokens}")
else:
    print("usage chunk not emitted (stream_options.include_usage was ignored?)")
"""
    ),
    md(
        """## 2. Responses API stream

The Responses API uses *typed* events instead of raw `delta.content` strings.
Each event has a `type` field; the ones you'll almost always handle are:

- `response.output_text.delta` — incremental text for the visible answer.
- `response.function_call_arguments.delta` / `.done` — tool-call arguments
  (Lab 2.2 covers these).
- `response.completed` — final event, with full `usage` on the nested
  `.response.usage`.

The event tree is richer than Chat Completions but also friendlier for
tool-heavy workflows because you don't have to reassemble arguments
byte-by-byte.
"""
    ),
    code(
        """t0 = time.time()
ttft = None
pieces = []
final_usage = None

stream = client.responses.create(
    model=GPT_OSS_120B,
    input=PROMPT,
    max_output_tokens=120,
    stream=True,
)

for event in stream:
    etype = getattr(event, "type", "")
    if etype == "response.output_text.delta":
        if ttft is None:
            ttft = time.time() - t0
        pieces.append(event.delta)
        print(event.delta, end="", flush=True)
    elif etype == "response.completed":
        final_usage = event.response.usage

print("\\n\\n--- stream stats ---")
print(f"TTFT          : {ttft:.2f} s" if ttft else "TTFT          : n/a")
if final_usage:
    print(f"input_tokens  : {final_usage.input_tokens}")
    print(f"output_tokens : {final_usage.output_tokens}")
else:
    print("no response.completed event observed")
"""
    ),
    md(
        """## 3. Anthropic Messages stream

The Anthropic path uses its native SSE event names: `message_start`,
`content_block_start`, `content_block_delta`, `content_block_stop`,
`message_delta`, `message_stop`. The SDK gives you an iterator of typed
objects — you almost always want the text accumulator, which the SDK
exposes as `.text_stream`.
"""
    ),
    code(
        """t0 = time.time()
ttft = None
pieces = []

with anth.messages.stream(
    model=CLAUDE_OPUS_47,
    max_tokens=200,
    messages=[{"role": "user", "content": PROMPT}],
) as stream:
    for text in stream.text_stream:
        if ttft is None:
            ttft = time.time() - t0
        pieces.append(text)
        print(text, end="", flush=True)
    final = stream.get_final_message()

print("\\n\\n--- stream stats ---")
print(f"TTFT         : {ttft:.2f} s")
print(f"input_tokens : {final.usage.input_tokens}")
print(f"output_tokens: {final.usage.output_tokens}")
print(f"stop_reason  : {final.stop_reason}")
"""
    ),
    md(
        """## 4. Event-taxonomy cheat sheet

| Concept | Chat Completions | Responses API | Anthropic Messages |
|---|---|---|---|
| Start of stream | First chunk with `choices[0].delta.role` | `response.created` | `message_start` |
| Visible text | `delta.content` | `response.output_text.delta` | `content_block_delta` (text) |
| Tool-call name/id | `delta.tool_calls[i].function.name` / `.id` | `response.output_item.added` (function_call) | `content_block_start` (tool_use) |
| Tool-call args | `delta.tool_calls[i].function.arguments` (byte fragments) | `response.function_call_arguments.delta`/`.done` (full JSON on `.done`) | `content_block_delta` with `input_json_delta` |
| Reasoning / thinking | not surfaced | `response.reasoning.delta` / `summary.text.delta` | `content_block_delta` with `thinking_delta` |
| Terminal usage | last chunk iff `stream_options.include_usage=True` | `response.completed.response.usage` | `message_delta` + `message_stop` |

**Takeaway:** if you only need text, all three are roughly equivalent. If
you need tool calls or reasoning tokens in the stream, the Responses API is
the easiest to consume.
"""
    ),
    md(
        """## 5. Common pitfalls

- **Forgetting `stream_options`.** Without it, Chat Completions streams do
  *not* include a terminal `usage` block; you'll silently miss
  input/output token counts.
- **Accumulating `tool_calls` wrong.** Each Chat Completions chunk carries
  *only the new arguments fragment* — you must concatenate them keyed by
  `tool_calls[i].index`. Lab 2.2 has a reusable accumulator.
- **Timing out on slow models.** Extended-thinking models (Opus 4.7 with
  `thinking`, Kimi K2 Thinking) can take 15–60 s to produce the first token.
  Bump your HTTP client read timeout accordingly.
- **Buffering in the middle.** Nginx / ALB / some corporate proxies buffer
  SSE by default. If you see "all at once" output instead of incremental,
  disable response buffering in your infra layer.
"""
    ),
]


# ---------------------------------------------------------------------------
# Lab 2.2 — Tool calling
# ---------------------------------------------------------------------------

tools_cells = [
    md(
        """# Lab 2.2 — Tool / Function Calling on Mantle

**Duration:** ~10 min · **Level:** L300 · **Lab 2 of 4 — part 2/3**

Mantle exposes tool calling on all three surfaces, but with different
shapes. Migrating a Converse tool loop to Mantle is the single largest
source of code changes in a real migration.

Scope of this notebook:

1. Define a tiny `get_weather` tool and call it via **Chat Completions**.
2. Show the critical `json.loads()` step for tool arguments on the OpenAI
   surfaces.
3. Run the same tool via the **Anthropic Messages** path (no `json.loads()`
   needed — arguments arrive parsed).
4. Preview **server-side tool execution** on the Responses API (MCP /
   Lambda).
"""
    ),
    code(
        """import os, sys, json
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

from src.common.mantle import (
    openai_client, anthropic_client,
    GPT_OSS_120B, CLAUDE_OPUS_47, CLAUDE_HAIKU_45,
)

client = openai_client()
anth = anthropic_client()

# The "tool" is a dictionary lookup. In real code it would call an API.
_WEATHER = {"paris": {"temp_c": 22, "condition": "sunny"},
            "seattle": {"temp_c": 15, "condition": "drizzle"},
            "tokyo": {"temp_c": 27, "condition": "humid"}}

def get_weather(city: str) -> dict:
    return _WEATHER.get(city.lower(), {"error": f"no data for {city!r}"})
"""
    ),
    md(
        """## 1. Chat Completions — full tool loop

**Schema wrapper:** `tools[]` with a `function` envelope, `parameters` is a
standard JSON schema.

**`tool_choice`:** `"auto"` / `"required"` / `{"type":"function","function":{"name":"…"}}`.

**Arguments on the wire:** `tool_calls[].function.arguments` is a **JSON
string**, not a dict. You must `json.loads()` it before using it.

**Tool result turn-in:** a dedicated `role: "tool"` message carrying
`tool_call_id` and a **string** `content` (JSON-encode your result).
"""
    ),
    code(
        """tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "Current weather for a city",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string"}},
            "required": ["city"],
            "additionalProperties": False,
        },
    },
}]

messages = [
    {"role": "system", "content": "Use the get_weather tool whenever the user asks about weather."},
    {"role": "user",   "content": "Compare the weather in Paris and Tokyo."},
]

MAX_ITER = 6    # cap so a misbehaving model can't infinite-loop us.
for iteration in range(MAX_ITER):
    r = client.chat.completions.create(
        model=GPT_OSS_120B,
        messages=messages,
        tools=tools,
        tool_choice="auto",
        max_tokens=400,
    )
    msg = r.choices[0].message

    # Preserve the assistant turn verbatim. Content may be None while
    # tool_calls are being requested — that's expected on OpenAI.
    assistant_turn = {"role": "assistant", "content": msg.content}
    if msg.tool_calls:
        assistant_turn["tool_calls"] = [tc.model_dump() for tc in msg.tool_calls]
    messages.append(assistant_turn)

    if r.choices[0].finish_reason != "tool_calls":
        print("--- final answer ---")
        print(msg.content)
        break

    # Execute each tool call the model requested.
    for tc in msg.tool_calls:
        args = json.loads(tc.function.arguments)   # STRING → dict
        print(f"[tool] {tc.function.name}({args})")
        result = get_weather(**args)
        messages.append({
            "role": "tool",
            "tool_call_id": tc.id,
            "content": json.dumps(result),          # STRING content
        })
else:
    print(f"⚠️  loop hit MAX_ITER={MAX_ITER} without terminating")
"""
    ),
    md(
        """### Watch the loop terminate

The while-loop exits when `finish_reason == "stop"`. Other terminals you
should handle in production:

- `length` — ran out of `max_tokens` mid-tool-call. Raise `max_tokens`.
- `content_filter` — Bedrock guardrail or model refusal.
- `tool_calls` persisting — the model is convinced it needs another round;
  add an iteration cap so you can't infinite-loop on bad prompts.
"""
    ),
    md(
        """## 2. Anthropic Messages — same tool, native shape

On the Anthropic surface:

- **Schema wrapper:** `tools[].input_schema` (no `function` envelope).
- **`tool_choice`:** `{"type":"auto"}` / `{"type":"any"}` /
  `{"type":"tool","name":"..."}` — *not* the bare strings used on OpenAI.
- **Arguments:** arrive as a parsed **dict** under `content[].input` — no
  `json.loads()`.
- **Tool result turn-in:** a `user` message with `tool_result` content
  blocks, *not* a `tool` role.
"""
    ),
    code(
        """anth_tools = [{
    "name": "get_weather",
    "description": "Current weather for a city",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"],
    },
}]

anth_messages = [
    {"role": "user", "content": "Compare the weather in Paris and Seattle."}
]

MAX_ITER = 6
for iteration in range(MAX_ITER):
    r = anth.messages.create(
        model=CLAUDE_HAIKU_45,
        max_tokens=400,
        system="Use the get_weather tool for any weather question.",
        tools=anth_tools,
        messages=anth_messages,
    )

    # Preserve the assistant turn (mix of text and tool_use blocks).
    anth_messages.append({"role": "assistant", "content": r.content})

    if r.stop_reason != "tool_use":
        text = next((b.text for b in r.content if b.type == "text"), "")
        print("--- final answer ---")
        print(text)
        break

    tool_results = []
    for block in r.content:
        if block.type != "tool_use":
            continue
        # .input is ALREADY a dict here — no json.loads()
        print(f"[tool] {block.name}({block.input})")
        out = get_weather(**block.input)
        tool_results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(out),            # strings are lingua franca
        })
    anth_messages.append({"role": "user", "content": tool_results})
else:
    print(f"⚠️  loop hit MAX_ITER={MAX_ITER} without terminating")
"""
    ),
    md(
        """### Axis-A vs Axis-B differences to memorise

From the playbook:

- **Axis A** — *Converse (runtime) → any Mantle surface.* The schema
  wrapper, stop-reason vocab, and message-history shape all change.
- **Axis B** — *between Mantle surfaces.* Chat Completions has strings and
  a dedicated `tool` role; Anthropic has dicts and `user`+`tool_result`
  blocks. Your provider abstraction must branch *three* ways, not one.

| Shape | Chat Completions | Responses API | Anthropic Messages |
|---|---|---|---|
| Tool schema wrapper | `tools[].function.parameters` | `tools[]` flat | `tools[].input_schema` |
| `tool_choice=auto` | `"auto"` | `"auto"` | `{"type":"auto"}` |
| `tool_choice=required` | `"required"` | `"required"` | `{"type":"any"}` |
| Arguments on wire | **JSON string** | **JSON string** (on `.done` event) | **dict** |
| Tool result turn-in | `role:"tool"` + `tool_call_id` | `function_call_output` item | `user` + `tool_result` block |
| Rich tool results (image / JSON) | strings only | strings only | typed blocks |
| Stop-reason keyword | `finish_reason == "tool_calls"` | walk `output[]` | `stop_reason == "tool_use"` |
"""
    ),
    md(
        """## 3. Server-side tools (preview — Responses API only)

The Responses API lets Mantle run the tool loop *inside Bedrock*. You
register an MCP-compatible Lambda and the model calls it directly — no
round-trip to your client between tool calls.

The snippet below is for reference; running it requires you to deploy a
Lambda with the MCP contract (`tools/list`, `tools/call`) first. Lab 4
shows the end-to-end wiring.
"""
    ),
    code(
        """# NOTE: This cell is illustrative. Uncomment and replace <account> +
# <fn-name> after you deploy an MCP-compatible Lambda in your account.
#
# response = client.responses.create(
#     model=GPT_OSS_120B,
#     tools=[{
#         "type": "mcp",
#         "server_label": "product_tools",
#         "connector_id": "arn:aws:lambda:us-east-1:<account>:function:<fn-name>",
#         "require_approval": "never",
#     }],
#     input="Find laptops under $1000 and list their prices.",
# )
# print(response.output_text)
print("server-side tool snippet shown as a comment — no live call is made in this cell.")
"""
    ),
    md(
        """## 4. Migration checklist

When you port a Converse tool loop to Mantle Chat Completions:

- [ ] Flatten `toolSpec.inputSchema.json` → `function.parameters`.
- [ ] Remap `toolChoice`: `{"any":{}}` → `"required"`,
      `{"tool":{"name":"x"}}` → `{"type":"function","function":{"name":"x"}}`.
- [ ] Switch `stopReason == "tool_use"` → `finish_reason == "tool_calls"`.
- [ ] **`json.loads()` every tool argument.** They arrive as strings.
- [ ] Emit `role:"tool"` with `tool_call_id` (not `user` + `toolResult`).
- [ ] Collapse image / document / JSON tool results to strings
      (JSON-encode dicts, stringify numbers).
- [ ] Set `parallel_tool_calls` explicitly (defaults vary per model).
- [ ] Cap loop iterations (`for _ in range(8)`) to prevent runaways.
- [ ] Add telemetry for `(tool_name, args, latency, ok)` — Mantle itself
      does not log tool names by default.
"""
    ),
]


# ---------------------------------------------------------------------------
# Lab 2.3 — Caching + Stateful
# ---------------------------------------------------------------------------

caching_cells = [
    md(
        """# Lab 2.3 — Prompt Caching and Stateful Conversations

**Duration:** ~10 min · **Level:** L300 · **Lab 2 of 4 — part 3/3**

This notebook covers three advanced Mantle features:

1. **Prompt-prefix caching** on Chat Completions via `extra_body.cache_salt`.
2. **Stateful conversations** on the **Responses API** via
   `previous_response_id` (an OpenAI Responses feature that Mantle supports
   faithfully — not a Mantle-only primitive).
3. **Prompt caching via `cache_control`** on the Anthropic Messages API.

These features collectively drive down latency and cost for multi-turn,
long-context, or repeated-prompt workloads.
"""
    ),
    code(
        """import os, sys, time
from pathlib import Path

ROOT = Path.cwd().resolve()
while ROOT.name and not (ROOT / "src" / "common").exists():
    ROOT = ROOT.parent
sys.path.insert(0, str(ROOT))

os.environ["AWS_REGION"] = os.environ.get("AWS_REGION", "us-east-1")
os.environ["AWS_DEFAULT_REGION"] = os.environ["AWS_REGION"]

from src.common.mantle import (
    openai_client, anthropic_client,
    GPT_OSS_120B, CLAUDE_OPUS_47,
)

client = openai_client()
anth = anthropic_client()
"""
    ),
    md(
        """## 1. Prompt-prefix caching on Chat Completions

Mantle's internal inference engine shares a vLLM-class prefix cache across
requests. You can *signal* cache affinity with `extra_body.cache_salt` —
two requests with the same prompt prefix **and** the same `cache_salt` are
eligible to hit the same cache.

To *see* the effect, we'll run the same 2 KB system prompt twice and
compare **time-to-first-token**.
"""
    ),
    code(
        """LONG_SYSTEM = (
    "You are an enterprise risk analyst. Respond using exactly three bullets. "
    * 80
)
print(f"prefix length: {len(LONG_SYSTEM)} chars (~{len(LONG_SYSTEM)//4} tokens rough)")

def timed_call(salt: str) -> float | None:
    t0 = time.time()
    ttft = None
    stream = client.chat.completions.create(
        model=GPT_OSS_120B,
        messages=[
            {"role": "system", "content": LONG_SYSTEM},
            {"role": "user",   "content": "List three risks of migrating LLM workloads."},
        ],
        max_tokens=80,
        stream=True,
        extra_body={"cache_salt": salt},
    )
    # Drain the whole stream — we need the generator to finish cleanly so the
    # underlying HTTP connection is released. We only record the *first* TTFT.
    for chunk in stream:
        if chunk.choices and chunk.choices[0].delta.content and ttft is None:
            ttft = time.time() - t0
    return ttft

cold = timed_call("workshop-demo-v1")    # likely a miss
warm = timed_call("workshop-demo-v1")    # likely a hit — same salt, same prefix

def fmt(v): return f"{v:.3f}s" if v is not None else "n/a"
print(f"cold TTFT: {fmt(cold)}")
print(f"warm TTFT: {fmt(warm)}")
if cold and warm:
    print(f"warm is {cold/warm:.2f}x faster at TTFT")
else:
    print("measurement failed — one of the streams produced no content")
"""
    ),
    md(
        """### What cache-affinity buys you

- TTFT speedups of 2× – 10× are typical when the cached prefix is large
  (system prompts, few-shot examples, RAG contexts).
- It does **not** reduce *billed* input tokens — you still pay for the
  context (on most models; verify per model card).
- The cache is *best-effort*. Don't build correctness assumptions on top of
  it — it can evict at any time.

**When to use:** a system prompt + few-shot block that you reuse across
many user questions. Pick a `cache_salt` keyed off the prefix content hash
so updates invalidate the cache naturally.
"""
    ),
    md(
        """## 2. Stateful conversations with the Responses API

The **Responses API** is Mantle's native stateful primitive. Pass
`previous_response_id=<id from the last call>` and Mantle reconstructs the
conversation server-side — you don't have to send history back.

This cuts ingress bytes on long conversations and makes it easier to
maintain reasoning chains (the model keeps its own thinking).
"""
    ),
    code(
        """r1 = client.responses.create(
    model=GPT_OSS_120B,
    input="My name is Alice and I like the color teal.",
    instructions="You are a helpful assistant who remembers user facts.",
    max_output_tokens=60,
    store=True,                        # persist state server-side
)
print("turn 1:", r1.output_text.strip())
print("id    :", r1.id)
"""
    ),
    code(
        """r2 = client.responses.create(
    model=GPT_OSS_120B,
    input="What color do I like, and what is my name?",
    previous_response_id=r1.id,        # continues the thread server-side
    max_output_tokens=80,
)
print("turn 2:", r2.output_text.strip())
"""
    ),
    md(
        """### When to use Responses statefulness

- **Use it** for multi-turn agents where the server can reliably keep the
  thread alive (chat UIs, Slack bots, IDE assistants).
- **Avoid it** when you need reproducibility / audit — history is opaque.
  Prefer explicit client-managed `messages=[…]` for compliance workloads.
- **Use `store=False`** if you want the request to remain stateless but
  still *look* like a Responses call (same SDK shape as Chat Completions).
"""
    ),
    md(
        """## 3. Anthropic prompt caching (`cache_control`)

On the Anthropic Messages path, caching is **explicit**. You mark a content
block with `cache_control: {"type": "ephemeral"}` and Claude caches that
prefix for ~5 minutes. You get:

- ~90% discount on *input tokens that hit the cache*.
- Lower TTFT.
- Verifiable cache hit / miss counts in `usage.cache_read_input_tokens`
  and `usage.cache_creation_input_tokens`.
"""
    ),
    code(
        """LONG_CONTEXT = (
    "# Internal policy document (excerpt)\\n\\n"
    + "This is company policy text. " * 400          # ~10KB
)

def claude_call(question: str):
    return anth.messages.create(
        model=CLAUDE_OPUS_47,
        max_tokens=200,
        system=[
            {
                "type": "text",
                "text": LONG_CONTEXT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[{"role": "user", "content": question}],
    )

first  = claude_call("Summarize the policy in one sentence.")
second = claude_call("Are there any exceptions in the policy?")

def report(resp, label):
    u = resp.usage
    read   = getattr(u, "cache_read_input_tokens", 0) or 0
    create = getattr(u, "cache_creation_input_tokens", 0) or 0
    print(f"{label}: input={u.input_tokens}  cache_read={read}  cache_create={create}  output={u.output_tokens}")

report(first,  "first ")
report(second, "second")
print("\\nSecond call should have cache_read_input_tokens ~= LONG_CONTEXT size.")
"""
    ),
    md(
        """## 4. Recap — which cache for which workload

| Workload | Best Mantle primitive | Why |
|---|---|---|
| Long system prompt reused across thousands of user questions (RAG / few-shot) | Chat Completions `cache_salt` | Covers all OpenAI-compat models; no token math. |
| Multi-turn chat / agentic thread | Responses API `previous_response_id` | Zero-byte context passing; server keeps state. |
| Long policy / document context on Claude | Anthropic `cache_control: ephemeral` | Large discount on input tokens; observable. |

**Next:** Lab 3 migrates a real Bedrock Runtime Converse tool-loop to
Mantle step-by-step, then benchmarks TTFT / tokens-per-second side by side.
"""
    ),
]


if __name__ == "__main__":
    root = Path(__file__).parent.parent / "src" / "lab2"
    write_notebook(root / "01_streaming.ipynb", streaming_cells)
    write_notebook(root / "02_tool_calling.ipynb", tools_cells)
    write_notebook(root / "03_caching_and_stateful.ipynb", caching_cells)
    print("wrote lab2 notebooks")
