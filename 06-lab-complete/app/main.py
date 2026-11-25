"""Production entry point for the Day 14 mock agent."""

import json
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from time import perf_counter
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from redis.exceptions import RedisError

from utils.mock_llm import ask as llm_ask

from .auth import verify_api_key
from .config import settings
from .cost_guard import check_budget, record_cost
from .rate_limiter import check_rate_limit
from .redis_client import r, redis_healthy

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.propagate = False
logger.addHandler(logging.StreamHandler())


def log_event(event: str, **fields: object) -> None:
    logger.info(json.dumps({
        "ts": datetime.now(timezone.utc).isoformat(),
        "lvl": "INFO",
        "event": event,
        **fields,
    }))


@asynccontextmanager
async def lifespan(app: FastAPI):
    log_event("startup", environment=settings.environment)
    try:
        yield
    finally:
        r.close()
        log_event("shutdown")


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


@app.middleware("http")
async def log_request(request: Request, call_next):
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        route = request.scope.get("route")
        log_event(
            "request",
            method=request.method,
            path=getattr(route, "path", "unmatched"),
            status=status,
            ms=round((perf_counter() - started) * 1000, 2),
        )


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/ready")
def ready() -> dict:
    if not redis_healthy():
        raise HTTPException(status_code=503, detail="Redis unavailable")
    return {"status": "ready"}


@app.post("/ask")
def ask(body: AskRequest, api_key: Annotated[str, Depends(verify_api_key)]) -> dict:
    now = datetime.now(timezone.utc)
    try:
        check_rate_limit(api_key)
        check_budget(now)
        answer = llm_ask(body.question)
        # The mock has no tokenizer. Approximate usage from text length.
        record_cost((len(body.question) + 3) // 4, (len(answer) + 3) // 4, now)
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis unavailable") from None
    return {"question": body.question, "answer": answer}
