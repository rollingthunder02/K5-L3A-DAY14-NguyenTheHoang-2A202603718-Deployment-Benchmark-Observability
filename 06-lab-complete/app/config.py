"""Environment configuration for the production agent."""

import os
from dataclasses import dataclass, field
from decimal import Decimal


def budget_from_env(name: str) -> Decimal | None:
    value = os.getenv(name)
    if not value:
        return None
    budget = Decimal(value)
    if not budget.is_finite() or budget < 0:
        raise ValueError(f"{name} must be a finite, nonnegative amount")
    return budget


@dataclass(frozen=True)
class Settings:
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    agent_api_key: str = field(default_factory=lambda: os.getenv("AGENT_API_KEY", ""), repr=False)
    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
        repr=False,
    )
    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    daily_budget_usd: Decimal | None = field(
        default_factory=lambda: budget_from_env("DAILY_BUDGET_USD")
    )
    monthly_budget_usd: Decimal | None = field(
        default_factory=lambda: budget_from_env("MONTHLY_BUDGET_USD")
    )

    def __post_init__(self) -> None:
        if self.rate_limit_per_minute < 1:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be positive")
        if self.daily_budget_usd is None and self.monthly_budget_usd is None:
            object.__setattr__(self, "monthly_budget_usd", Decimal("10"))


settings = Settings()
