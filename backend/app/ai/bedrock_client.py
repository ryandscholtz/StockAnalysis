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
from decimal import Decimal
from typing import Any, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_CLAUDE_MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"
BEDROCK_USAGE_TABLE = os.getenv("BEDROCK_USAGE_TABLE", "stock-analysis-bedrock-usage")
DEFAULT_INPUT_COST_PER_MILLION = Decimal(os.getenv("BEDROCK_INPUT_COST_PER_MTOKENS", "1.0"))
DEFAULT_OUTPUT_COST_PER_MILLION = Decimal(os.getenv("BEDROCK_OUTPUT_COST_PER_MTOKENS", "5.0"))
MODEL_RATE_DEFAULTS = {
    "claude-haiku": (Decimal("1.0"), Decimal("5.0")),
    "claude-sonnet": (Decimal("3.0"), Decimal("15.0")),
    "claude-opus": (Decimal("15.0"), Decimal("75.0")),
}

# Per-request budget (reset via reset_invocation_budget() at handler start)
_budget_remaining: Optional[int] = None
_tracking_user_id: Optional[str] = None


def set_usage_tracking_user(user_id: Optional[str]) -> None:
    global _tracking_user_id
    _tracking_user_id = user_id.strip() if isinstance(user_id, str) and user_id.strip() else None


def clear_usage_tracking_user() -> None:
    global _tracking_user_id
    _tracking_user_id = None


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


def _estimate_tokens_from_chars(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, round(char_count / 4))


def _extract_usage_counts(resp_body: dict, input_chars: int, out_chars: int) -> tuple[int, int, str]:
    usage = resp_body.get("usage") if isinstance(resp_body, dict) else None
    if isinstance(usage, dict):
        input_tokens = usage.get("input_tokens") or usage.get("inputTokens") or usage.get("prompt_tokens") or usage.get("promptTokens")
        output_tokens = usage.get("output_tokens") or usage.get("outputTokens") or usage.get("completion_tokens") or usage.get("completionTokens")
        if input_tokens is not None or output_tokens is not None:
            return int(input_tokens or 0), int(output_tokens or 0), "provider"
    return _estimate_tokens_from_chars(input_chars), _estimate_tokens_from_chars(out_chars), "estimated"


def _get_model_rate_per_million(model_id: str) -> tuple[Decimal, Decimal]:
    mid = (model_id or "").lower()
    if "claude-haiku" in mid:
        key = "HAIKU"
        defaults = MODEL_RATE_DEFAULTS["claude-haiku"]
    elif "claude-sonnet" in mid:
        key = "SONNET"
        defaults = MODEL_RATE_DEFAULTS["claude-sonnet"]
    elif "claude-opus" in mid:
        key = "OPUS"
        defaults = MODEL_RATE_DEFAULTS["claude-opus"]
    else:
        return DEFAULT_INPUT_COST_PER_MILLION, DEFAULT_OUTPUT_COST_PER_MILLION

    input_rate = Decimal(os.getenv(f"BEDROCK_{key}_INPUT_COST_PER_MTOKENS", str(defaults[0])))
    output_rate = Decimal(os.getenv(f"BEDROCK_{key}_OUTPUT_COST_PER_MTOKENS", str(defaults[1])))
    return input_rate, output_rate


def _estimate_cost_usd(model_id: str, input_tokens: int, output_tokens: int) -> Decimal:
    input_rate, output_rate = _get_model_rate_per_million(model_id)
    return (
        (Decimal(input_tokens) / Decimal(1_000_000)) * input_rate
        + (Decimal(output_tokens) / Decimal(1_000_000)) * output_rate
    )


def _record_usage(model_id: str, operation: str, input_tokens: int, output_tokens: int, usage_source: str) -> None:
    if not _tracking_user_id:
        return
    try:
        import boto3

        now = __import__("datetime").datetime.now().isoformat()
        total_tokens = input_tokens + output_tokens
        estimated_cost = _estimate_cost_usd(model_id, input_tokens, output_tokens)
        table = boto3.resource("dynamodb", region_name=get_bedrock_region()).Table(BEDROCK_USAGE_TABLE)

        for counter_type in ("TOTAL", "INSTANCE"):
            table.update_item(
                Key={"userId": _tracking_user_id, "counterType": counter_type},
                UpdateExpression=(
                    "SET updated_at = :now, created_at = if_not_exists(created_at, :now), "
                    "reset_at = if_not_exists(reset_at, :now), last_model_id = :model, "
                    "last_operation = :operation, last_usage_source = :usage_source "
                    "ADD request_count :request_count, input_tokens :input_tokens, "
                    "output_tokens :output_tokens, total_tokens :total_tokens, estimated_cost_usd :estimated_cost"
                ),
                ExpressionAttributeValues={
                    ":now": now,
                    ":model": model_id,
                    ":operation": operation,
                    ":usage_source": usage_source,
                    ":request_count": Decimal(1),
                    ":input_tokens": Decimal(input_tokens),
                    ":output_tokens": Decimal(output_tokens),
                    ":total_tokens": Decimal(total_tokens),
                    ":estimated_cost": estimated_cost,
                },
            )
    except Exception as exc:
        logger.warning("bedrock_usage_record_failed %s", exc)


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
    input_tokens, output_tokens, usage_source = _extract_usage_counts(resp_body, input_chars, out_chars)
    _record_usage(mid, operation, input_tokens, output_tokens, usage_source)
    logger.info(
        "bedrock_invoke_done %s",
        json.dumps({
            **log_payload,
            "output_chars_approx": out_chars,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "usage_source": usage_source,
        }, default=str),
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
