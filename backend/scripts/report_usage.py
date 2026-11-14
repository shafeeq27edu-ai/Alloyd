"""Summarize stored usage events.

Read-only. Aggregates routing, latency, token, and cost data; it never selects
message content, so the report cannot leak prompts or answers.

Run from the backend directory:

    .venv/Scripts/python.exe scripts/report_usage.py
    .venv/Scripts/python.exe scripts/report_usage.py --days 7
"""
import argparse
import asyncio
import base64
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Reading usage rows needs no auth keys. Give the settings object harmless local
# values so the script runs without printing, requiring, or overriding the real
# secrets; DATABASE_URL still comes from the environment or .env.
os.environ.setdefault("SECRET_KEY", "usage-report-placeholder-secret-key-not-for-auth")
os.environ.setdefault("ENCRYPTION_KEY", base64.urlsafe_b64encode(b"1" * 32).decode())

from sqlalchemy import select  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402

from app.config import settings  # noqa: E402
from app.db.models import UsageEvent  # noqa: E402


def _percentile(values: list[int], fraction: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(fraction * (len(ordered) - 1))))
    return ordered[index]


def _cost(rows: list[UsageEvent]) -> tuple[float, int]:
    priced = [row.estimated_cost_usd for row in rows if row.estimated_cost_usd is not None]
    return sum(priced), len(priced)


def _table(title: str, groups: dict[str, list[UsageEvent]]) -> None:
    print(f"\n{title}")
    header = f"  {'':<34}{'events':>7}{'errors':>8}{'in':>10}{'out':>10}{'cost USD':>11}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for key in sorted(groups, key=lambda k: (-len(groups[k]), k)):
        rows = groups[key]
        errors = sum(1 for row in rows if row.status == "error")
        input_tokens = sum(row.input_tokens or 0 for row in rows)
        output_tokens = sum(row.output_tokens or 0 for row in rows)
        cost, priced = _cost(rows)
        cost_text = f"{cost:.6f}" if priced else "n/a"
        print(
            f"  {key[:33]:<34}{len(rows):>7}{errors:>8}{input_tokens:>10}{output_tokens:>10}{cost_text:>11}"
        )


def _report(rows: list[UsageEvent], days: int | None) -> None:
    if not rows:
        print("No usage events recorded.")
        return

    window = f"last {days} days" if days else "all time"
    first = min(row.created_at for row in rows)
    last = max(row.created_at for row in rows)
    print(f"Usage report ({window})")
    print(f"Events: {len(rows)} from {first:%Y-%m-%d %H:%M} to {last:%Y-%m-%d %H:%M} UTC")

    statuses = Counter(row.status for row in rows)
    failures = [row for row in rows if row.status == "error"]
    fallbacks = [row for row in rows if row.fallback_from]
    print(f"Success: {statuses.get('success', 0)}   Errors: {statuses.get('error', 0)}   Fallbacks fired: {len(fallbacks)}")

    if failures:
        codes = Counter(row.error_code or "UNKNOWN" for row in failures)
        print("Error codes: " + ", ".join(f"{code}={count}" for code, count in codes.most_common()))

    latencies = [row.latency_ms for row in rows if row.status == "success"]
    if latencies:
        print(
            f"Latency (successful attempts): avg {sum(latencies) // len(latencies)} ms, "
            f"p50 {_percentile(latencies, 0.5)} ms, p95 {_percentile(latencies, 0.95)} ms"
        )

    input_tokens = sum(row.input_tokens or 0 for row in rows)
    output_tokens = sum(row.output_tokens or 0 for row in rows)
    sources = Counter(row.token_source or "unknown" for row in rows if row.status == "success")
    print(
        f"Tokens: {input_tokens} in / {output_tokens} out "
        f"({sources.get('provider', 0)} provider-reported, {sources.get('estimated', 0)} estimated)"
    )

    cost, priced = _cost(rows)
    if priced:
        unpriced = len(rows) - priced
        note = f"; {unpriced} event(s) unpriced" if unpriced else ""
        print(f"Estimated cost: ${cost:.6f} across {priced} event(s){note}")
    else:
        print("Estimated cost: n/a (set PRICING_JSON to price catalog models)")

    by_model: dict[str, list[UsageEvent]] = defaultdict(list)
    by_category: dict[str, list[UsageEvent]] = defaultdict(list)
    by_mode: dict[str, list[UsageEvent]] = defaultdict(list)
    by_day: dict[str, list[UsageEvent]] = defaultdict(list)
    for row in rows:
        by_model[f"{row.provider}/{row.model}"].append(row)
        by_category[row.category or "(manual)"].append(row)
        by_mode[row.mode].append(row)
        by_day[f"{row.created_at:%Y-%m-%d}"].append(row)

    _table("By provider/model:", by_model)
    _table("By category:", by_category)
    _table("By mode:", by_mode)
    if len(by_day) > 1:
        _table("By day (UTC):", by_day)


async def _load(days: int | None) -> list[UsageEvent]:
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            statement = select(UsageEvent).order_by(UsageEvent.created_at)
            if days:
                statement = statement.where(
                    UsageEvent.created_at >= datetime.now(timezone.utc) - timedelta(days=days)
                )
            return list((await session.execute(statement)).scalars().all())
    finally:
        await engine.dispose()


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize stored usage events.")
    parser.add_argument("--days", type=int, default=None, help="Only include events from the last N days.")
    args = parser.parse_args()

    try:
        rows = asyncio.run(_load(args.days))
    except Exception:
        print("Could not read usage events from the database configured by DATABASE_URL.")
        return 1

    _report(rows, args.days)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
