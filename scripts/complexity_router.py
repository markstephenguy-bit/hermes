#!/usr/bin/env python3
"""OpenAI-compatible routing proxy: sends simple prompts to local Ollama,
deliberately fails complex ones with 503 so Hermes's own fallback_model
mechanism (built for rate-limits/errors) retries them against Codex.

This exists because Hermes has no working complexity-based routing itself:
smart_model_routing is an accepted-but-unimplemented config key, and
delegation.model only sets one global model for all subagents, not a
per-turn decision for the main conversation.

Classification is a tunable heuristic, not a judgment call - see
COMPLEX_KEYWORDS and the thresholds below. Every decision is logged so it
can be reviewed and retuned against real usage.

Two escalation paths, both landing on the same 503 -> Hermes fallback_model
mechanism:
  1. Upfront (classify()): judges the *question* before ever calling Ollama.
  2. Post-hoc (looks_inadequate()): judges the *answer* after Ollama responds -
     catches cases where the question looked simple but qwen's response was
     empty, a refusal, truncated, or degenerately repetitive. This requires
     buffering the full response before relaying it (even if Hermes asked for
     a streamed response), since a 503 can't be issued after a 200 has
     already started streaming to the client - so the simple/qwen path loses
     live token-by-token display in exchange for this safety net. Total wait
     time is unaffected, only the progressive-typing visual is.
"""
import json
import logging
import os
import re

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

REFUSAL_PATTERNS = [
    "i cannot", "i can't", "i am unable to", "i'm unable to",
    "as an ai language model", "i don't have the ability",
    "i do not have the ability", "sorry, but i", "i apologize, but i",
    "i'm not able to", "i am not able to",
]

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://192.168.40.100:11434")
LOG_PATH = os.environ.get("ROUTER_LOG", "/home/hermes/.hermes/logs/complexity_router.log")

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s %(message)s",
)
log = logging.getLogger("router")

app = FastAPI()

WORD_COUNT_THRESHOLD = 120
CODE_BLOCK_LINE_THRESHOLD = 30

COMPLEX_KEYWORDS = [
    "architect", "architecture", "refactor", "debug", "optimi", "algorithm",
    "vulnerability", "security review", "prove", "step by step",
    "chain of thought", "think carefully", "design a", "design the",
    "multi-step", "trade-off", "tradeoff", "compare and contrast",
    "write a program that", "implement a", "root cause", "race condition",
    "concurrency", "distributed system",
]


def last_user_message(messages: list[dict]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                return " ".join(
                    part.get("text", "") for part in content if isinstance(part, dict)
                )
            return content or ""
    return ""


def classify(messages: list[dict]) -> tuple[str, str]:
    text = last_user_message(messages)
    lower = text.lower()

    word_count = len(text.split())
    if word_count > WORD_COUNT_THRESHOLD:
        return "complex", f"word_count={word_count} > {WORD_COUNT_THRESHOLD}"

    for block in re.findall(r"```.*?```", text, re.DOTALL):
        if block.count("\n") > CODE_BLOCK_LINE_THRESHOLD:
            return "complex", f"code_block_lines={block.count(chr(10))} > {CODE_BLOCK_LINE_THRESHOLD}"

    for kw in COMPLEX_KEYWORDS:
        if kw in lower:
            return "complex", f"keyword={kw!r}"

    numbered_items = len(re.findall(r"(?m)^\s*\d+[.)]\s", text))
    if numbered_items >= 3:
        return "complex", f"numbered_items={numbered_items} >= 3"

    return "simple", f"word_count={word_count}, no complexity signals"


def _max_repeated_ngram_ratio(text: str, n: int = 6) -> float:
    """Fraction of n-word windows that are exact duplicates of an earlier window.
    Catches the degenerate small-model failure mode of looping on a phrase."""
    words = text.split()
    if len(words) < n * 3:
        return 0.0
    windows = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
    seen = {}
    repeats = 0
    for w in windows:
        seen[w] = seen.get(w, 0) + 1
        if seen[w] > 1:
            repeats += 1
    return repeats / len(windows)


def looks_inadequate(content: str, finish_reason: str) -> tuple[bool, str]:
    """Judge the ANSWER after generation - the upfront classify() only judges
    the question. Catches cases that looked simple but weren't handled well."""
    stripped = content.strip()

    if not stripped:
        return True, "empty response"

    lower = stripped.lower()
    for pattern in REFUSAL_PATTERNS:
        if pattern in lower:
            return True, f"refusal pattern={pattern!r}"

    if finish_reason == "length":
        return True, "truncated (finish_reason=length, ran out of tokens mid-answer)"

    repeat_ratio = _max_repeated_ngram_ratio(stripped)
    if repeat_ratio > 0.3:
        return True, f"degenerate repetition (repeat_ratio={repeat_ratio:.2f})"

    return False, "looks fine"


def _wrap_as_stream_chunks(message: dict, model: str, finish_reason: str) -> bytes:
    """Package a full (non-streamed) completion as minimal SSE chunks, since
    we had to buffer the whole response to inspect it before relaying -
    Hermes gets the answer in one chunk instead of progressively, but still
    in the streaming wire format it asked for."""
    chunk1 = {
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": message.get("content", "")}, "finish_reason": None}],
    }
    chunk2 = {
        "object": "chat.completion.chunk",
        "model": model,
        "choices": [{"index": 0, "delta": {}, "finish_reason": finish_reason}],
    }
    out = f"data: {json.dumps(chunk1)}\n\ndata: {json.dumps(chunk2)}\n\ndata: [DONE]\n\n"
    return out.encode()


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    verdict, reason = classify(messages)
    log.info("verdict=%s reason=%s preview=%r", verdict, reason, last_user_message(messages)[:120])

    if verdict == "complex":
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": f"complexity_router: routed to fallback ({reason})",
                    "type": "service_unavailable",
                    "code": "complexity_routed",
                }
            },
        )

    wanted_stream = bool(body.get("stream"))
    ollama_body = {**body, "stream": False}  # always buffer upstream so we can inspect before relaying

    async with httpx.AsyncClient(timeout=300) as client:
        upstream = await client.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json=ollama_body,
        )

    if upstream.status_code != 200:
        return JSONResponse(status_code=upstream.status_code, content=upstream.json())

    data = upstream.json()
    choice = (data.get("choices") or [{}])[0]
    message = choice.get("message", {})
    content = message.get("content", "")
    finish_reason = choice.get("finish_reason", "stop")

    bad, why = looks_inadequate(content, finish_reason)
    if bad:
        log.info("post-hoc verdict=complex reason=%s preview=%r", why, content[:120])
        return JSONResponse(
            status_code=503,
            content={
                "error": {
                    "message": f"complexity_router: post-hoc routed to fallback ({why})",
                    "type": "service_unavailable",
                    "code": "complexity_routed_posthoc",
                }
            },
        )

    if wanted_stream:
        return StreamingResponse(
            iter([_wrap_as_stream_chunks(message, data.get("model", ""), finish_reason)]),
            status_code=200,
            media_type="text/event-stream",
        )
    return JSONResponse(status_code=200, content=data)


@app.get("/v1/models")
async def models():
    async with httpx.AsyncClient(timeout=30) as client:
        upstream = await client.get(f"{OLLAMA_BASE_URL}/v1/models")
    return JSONResponse(status_code=upstream.status_code, content=upstream.json())
