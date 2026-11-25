"""Track shared daily and monthly LLM spend using integer nano-USD."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException

from .config import settings
from .redis_client import r

NANO_USD_PER_USD = 1_000_000_000
INPUT_TOKEN_NANO_USD = 150
OUTPUT_TOKEN_NANO_USD = 600


def _periods(now: datetime) -> list[tuple[str, Decimal, int]]:
    periods = []
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if settings.daily_budget_usd is not None:
        periods.append((
            f"day14:cost:day:{now:%Y-%m-%d}",
            settings.daily_budget_usd,
            int((midnight + timedelta(days=1)).timestamp()),
        ))
    if settings.monthly_budget_usd is not None:
        first_of_month = midnight.replace(day=1)
        next_month = (first_of_month + timedelta(days=32)).replace(day=1)
        periods.append((
            f"day14:cost:month:{now:%Y-%m}",
            settings.monthly_budget_usd,
            int(next_month.timestamp()),
        ))
    return periods


def check_budget(now: datetime | None = None) -> None:
    """Reject requests when an active UTC budget has already been spent."""
    periods = _periods(now or datetime.now(timezone.utc))
    totals = r.mget([key for key, _, _ in periods])
    for (_, budget, _), total in zip(periods, totals):
        if int(total or 0) >= budget * NANO_USD_PER_USD:
            raise HTTPException(status_code=402, detail="LLM budget exhausted")


def record_cost(input_tokens: int, output_tokens: int, now: datetime | None = None) -> float:
    """Accumulate actual usage for the UTC periods in which the request started."""
    cost = input_tokens * INPUT_TOKEN_NANO_USD + output_tokens * OUTPUT_TOKEN_NANO_USD
    with r.pipeline() as transaction:
        for key, _, expires_at in _periods(now or datetime.now(timezone.utc)):
            transaction.incrby(key, cost)
            transaction.expireat(key, expires_at)
        transaction.execute()
    return cost / NANO_USD_PER_USD
