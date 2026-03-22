"""
Shared AWS Bedrock (Claude) configuration and invocation for cost consistency and observability.

Env:
  BEDROCK_REGION — override Bedrock endpoint region (default: AWS_REGION or us-east-1)
  BEDROCK_CLAUDE_MODEL_ID — default Claude model for most use cases (default: Haiku 4.5)
  BEDROCK_FINANCIAL_MODEL_ID — JSON financial fetch / supplement (optional override)
  BEDROCK_PRESET_MODEL_ID — valuation preset picker (optional)
  BEDROCK_COMMENTARY_MODEL_ID — analyst commentary (optional)
  BEDROCK_PDF_EXTRACTION_MODEL_ID — PDF structured extraction (optional)
  BEDROCK_MODEL_ID — business type detector; falls back to BEDROCK_CLAUDE_MODEL_ID then default

Guardrails:
  BEDROCK_MAX_INVOCATIONS_PER_REQUEST — max successful Bedrock calls per budget window (optional)
  BEDROCK_SKIP_AI_FINANCIAL_FALLBACK=true — disable AI knowledge financial fetch (Lambda + routes)
  BEDROCK_SKIP_AI_COMMENTARY=true — skip analyst commentary Bedrock call (Lambda)
  BEDROCK_SKIP_AUTO_VALUATION_PRESET=true — skip LLM preset; use rule default (Lambda)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Per-request budget (reset via reset_invocation_budget() at handler start)
_budget_remaining: Optional[int] = None


def get_bedrock_region() -> str:
    return os.getenv("BEDROCK_REGION") or os.getenv("AWS_REGION", "us-east-1")


def reset_invocation_budget() -> None:
    """Call once at the start of each API/Lambda request that may invoke Bedrock multiple times."""
    global _budget_remaining
    raw = os.getenv("BEDROCK_MAX_INVOCATIONS_PER_REQUEST", "").strip()
    if not raw:
        _budget_remaining = None
        return
    try:
        n = int(raw)
        _budget_remaining = n if n > 0 else None
    except ValueError:
        _budget_remaining = None


def _consume_budget() -> None:
    global _budget_remaining
    if _budget_remaining is None:
        return
    if _budget_remaining <= 0:
        raise RuntimeError("BEDROCK_MAX_INVOCATIONS_PER_REQUEST exceeded")
    _budget_remaining -= 1


def is_ai_financial_fallback_disabled() -> bool:
    return os.getenv("BEDROCK_SKIP_AI_FINANCIAL_FALLBACK", "").lower() in ("1", "true", "yes")


def is_ai_commentary_disabled() -> bool:
    return os.getenv("BEDROCK_SKIP_AI_COMMENTARY", "").lower() in ("1", "true", "yes")


def is_auto_valuation_preset_disabled() -> bool:
    return os.getenv("BEDROCK_SKIP_AUTO_VALUATION_PRESET", "").lower() in ("1", "true", "yes")


def get_claude_model_id(use_case: str = "default") -> str:
    """
    Resolve model ID for a use case. Specific env overrides, then BEDROCK_CLAUDE_MODEL_ID, then Haiku default.
    use_case: financial | preset | commentary | pdf_extraction | business_type | default
    """
    env_for_case = {
        "financial": "BEDROCK_FINANCIAL_MODEL_ID",
        "preset": "BEDROCK_PRESET_MODEL_ID",
        "commentary": "BEDROCK_COMMENTARY_MODEL_ID",
        "pdf_extraction": "BEDROCK_PDF_EXTRACTION_MODEL_ID",
        "business_type": "BEDROCK_MODEL_ID",
    }.get(use_case)
    if env_for_case:
        v = os.getenv(env_for_case, "").strip()
        if v:
            return v
    if use_case == "business_type":
        v = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "").strip()
        if v:
            return v
        return DEFAULT_CLAUDE_MODEL_ID
    generic = os.getenv("BEDROCK_CLAUDE_MODEL_ID", "").strip()
    if generic:
        return generic
    return DEFAULT_CLAUDE_MODEL_ID


def default_business_type_bedrock_model_id() -> str:
    """Explicit default for BusinessTypeDetector when no BEDROCK_MODEL_ID is set (Haiku)."""
    return get_claude_model_id("business_type")


def _estimate_message_chars(messages: List[dict]) -> int:
    n = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            n += len(c)
        elif isinstance(c, list):
            for block in c:
                if isinstance(block, dict) and block.get("type") == "text":
                    n += len(block.get("text") or "")
    return n


def invoke_claude_bedrock(
    *,
    messages: List[dict],
    max_tokens: int,
    temperature: float = 0.0,
    model_id: Optional[str] = None,
    operation: str = "bedrock_invoke",
    ticker: Optional[str] = None,
    bedrock_client: Any = None,
) -> str:
    """
    Invoke Claude on Bedrock with structured logging. Pass bedrock_client to reuse a client (e.g. PDF flow).
    """
    import boto3

    mid = model_id or get_claude_model_id("financial")
    region = get_bedrock_region()
    client = bedrock_client or boto3.client("bedrock-runtime", region_name=region)

    _consume_budget()

    input_chars = _estimate_message_chars(messages)
    log_payload = {
        "bedrock_operation": operation,
        "bedrock_model_id": mid,
        "bedrock_region": region,
        "ticker": ticker,
        "max_tokens": max_tokens,
        "input_chars_approx": input_chars,
    }
    logger.info("bedrock_invoke_start %s", json.dumps(log_payload, default=str))

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }
    response = client.invoke_model(
        modelId=mid,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    resp_body = json.loads(response["body"].read())
    text = resp_body["content"][0]["text"]
    out_chars = len(text) if text else 0
    logger.info(
        "bedrock_invoke_done %s",
        json.dumps({**log_payload, "output_chars_approx": out_chars}, default=str),
    )
    return text


def invoke_claude_bedrock_simple(
    prompt: str,
    *,
    max_tokens: int = 2000,
    temperature: float = 0.0,
    model_id: Optional[str] = None,
    operation: str = "bedrock_invoke",
    ticker: Optional[str] = None,
    bedrock_client: Any = None,
) -> str:
    """Single user message convenience wrapper."""
    return invoke_claude_bedrock(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=temperature,
        model_id=model_id,
        operation=operation,
        ticker=ticker,
        bedrock_client=bedrock_client,
    )
