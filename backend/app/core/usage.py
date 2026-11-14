"""Token normalisation and cost estimation for per-message usage records.

Prices are not hard-coded. The catalog's model IDs cannot be priced from this
repository, and a confident wrong number in the UI is worse than no number.
Owners supply verified prices through ``PRICING_JSON``:

    {"groq/openai/gpt-oss-120b": {"input": 0.15, "output": 0.75}}

Values are USD per one million tokens. When a provider streams its own usage we
keep those counts; otherwise tokens are estimated from characters and the row
is marked ``estimated`` so the UI does not present an estimate as fact.
"""
import json
import math
from typing import Any, Iterable, Mapping

CHARS_PER_TOKEN = 4


class PriceError(ValueError):
    pass


def parse_prices(raw: str) -> dict[str, dict[str, float]]:
    if not raw or not raw.strip():
        return {}
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PriceError(f"PRICING_JSON is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise PriceError("PRICING_JSON must be a JSON object.")
    prices: dict[str, dict[str, float]] = {}
    for key, value in data.items():
        if not isinstance(value, dict):
            raise PriceError(f"Price for {key} must be an object with input and output.")
        for field in ("input", "output"):
            amount = value.get(field)
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                raise PriceError(f"Price for {key}.{field} must be a non-negative number.")
        prices[key] = {"input": float(value["input"]), "output": float(value["output"])}
    return prices


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def estimate_input_tokens(messages: Iterable[Mapping[str, Any]]) -> int:
    return sum(estimate_tokens(message.get("content") or "") for message in messages)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def resolve_usage(
    provider_usage: Mapping[str, Any] | None,
    messages: Iterable[Mapping[str, Any]],
    response_text: str,
) -> tuple[int, int, str]:
    """Return (input_tokens, output_tokens, token_source).

    ``token_source`` is ``provider`` only when both counts came from the
    provider; a partially reported attempt is labelled ``estimated``.
    """
    usage = provider_usage or {}
    input_tokens = usage.get("input_tokens")
    output_tokens = usage.get("output_tokens")
    from_provider = _is_count(input_tokens) and _is_count(output_tokens)
    if from_provider:
        return input_tokens, output_tokens, "provider"
    return (
        input_tokens if _is_count(input_tokens) else estimate_input_tokens(messages),
        output_tokens if _is_count(output_tokens) else estimate_tokens(response_text),
        "estimated",
    )


def estimate_cost(
    provider: str,
    model: str,
    input_tokens: int | None,
    output_tokens: int | None,
    prices: Mapping[str, Mapping[str, float]],
) -> float | None:
    price = prices.get(f"{provider}/{model}")
    if not price:
        return None
    cost = (
        (input_tokens or 0) / 1_000_000 * price["input"]
        + (output_tokens or 0) / 1_000_000 * price["output"]
    )
    return round(cost, 6)
