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
"""
import json
import logging
import os
import re

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

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

    async with httpx.AsyncClient(timeout=300) as client:
        upstream = await client.post(
            f"{OLLAMA_BASE_URL}/v1/chat/completions",
            json=body,
        )
    return StreamingResponse(
        iter([upstream.content]),
        status_code=upstream.status_code,
        media_type=upstream.headers.get("content-type", "application/json"),
    )


@app.get("/v1/models")
async def models():
    async with httpx.AsyncClient(timeout=30) as client:
        upstream = await client.get(f"{OLLAMA_BASE_URL}/v1/models")
    return JSONResponse(status_code=upstream.status_code, content=upstream.json())
