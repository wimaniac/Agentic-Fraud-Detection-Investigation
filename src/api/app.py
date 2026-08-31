"""HTTP API for deterministic investigations and append-only human feedback."""

from __future__ import annotations

import os
import logging
import secrets
import time
import uuid
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, Field

from src.database import Database, InvestigationRepository, ProductionTransactionRepository, SqlFeedbackRepository
from src.cache import RedisJsonCache
from src.human_review import FeedbackDecision
from src.investigation import InvestigationAgent
from src.retraining import FeedbackDatasetBuilder
from src.observability import (
    configure_logging, record_investigation, record_request, render_metrics, request_id_context,
)


DEFAULT_DATABASE_URL = "postgresql+psycopg://sentinel:sentinel@localhost:5432/sentinelai"
DEFAULT_DATA_DIR = Path("data/processed/fraud_1m_processed")


class FeedbackRequest(BaseModel):
    reviewer_id: str = Field(min_length=1, max_length=128)
    decision: FeedbackDecision
    notes: str = ""


class TransactionIngestRequest(BaseModel):
    """Raw transaction payload retained for investigation and future approved retraining."""

    transaction: dict[str, Any]
    source: str = Field(default="api", min_length=1, max_length=64)


def create_app(
    database_url: str | None = None,
    data_dir: str | Path = DEFAULT_DATA_DIR,
    agent_factory: Callable[[], InvestigationAgent] | None = None,
    redis_url: str | None = None,
    api_key: str | None = None,
    environment: str | None = None,
) -> FastAPI:
    """Build an API whose model decision path stays deterministic and local.

    ``database_url`` is injectable so integration tests can use SQLite. Production
    should set ``DATABASE_URL`` to a PostgreSQL URL; the default is for local
    Docker development only and contains no production credential.
    """
    database = Database(database_url or os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    investigations = InvestigationRepository(database)
    production_transactions = ProductionTransactionRepository(database)
    feedback = SqlFeedbackRepository(database)
    cache = RedisJsonCache(redis_url or os.getenv("REDIS_URL"))
    source_dir = Path(data_dir)
    configured_api_key = api_key if api_key is not None else os.getenv("SENTINEL_API_KEY")
    app_environment = (environment or os.getenv("APP_ENV", "development")).lower()
    logger = logging.getLogger("sentinel.api")
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))

    def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
        """Require a configured API key in production; local development is explicit."""
        if not configured_api_key:
            if app_environment == "production":
                raise HTTPException(status_code=503, detail="API authentication is not configured")
            return
        if not x_api_key or not secrets.compare_digest(x_api_key, configured_api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")

    @lru_cache(maxsize=1)
    def transactions() -> pd.DataFrame:
        source = source_dir / "transactions_clean.parquet"
        if not source.exists():
            raise FileNotFoundError(f"Processed transaction store was not found: {source}")
        return pd.read_parquet(source)

    @lru_cache(maxsize=1)
    def agent() -> InvestigationAgent:
        return agent_factory() if agent_factory else InvestigationAgent(data_dir=str(source_dir))

    @lru_cache(maxsize=1)
    def ensure_schema() -> None:
        """Open the database only for an operation that actually needs it."""
        database.create_schema()

    app = FastAPI(
        title="SentinelAI API",
        version="0.1.0",
        description="Deterministic fraud scoring, investigation and human-review audit API.",
    )

    @app.middleware("http")
    async def observe_request(request: Request, call_next: Callable[..., Any]) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        token = request_id_context.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            route = getattr(request.scope.get("route"), "path", request.url.path)
            duration = time.perf_counter() - started
            status_code = response.status_code if "response" in locals() else 500
            record_request(request.method, route, status_code, duration)
            logger.info(
                "request_completed",
                extra={
                    "event": "request_completed", "method": request.method, "path": route,
                    "status_code": status_code, "duration_ms": round(duration * 1000, 2),
                },
            )
            request_id_context.reset(token)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "scoring": "deterministic_ml_only"}

    @app.get("/metrics", include_in_schema=False)
    def metrics() -> Response:
        body, content_type = render_metrics()
        return Response(content=body, media_type=content_type)

    @app.post("/transactions", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def ingest_transaction(payload: TransactionIngestRequest) -> dict[str, Any]:
        ensure_schema()
        try:
            return production_transactions.record(payload.transaction, source=payload.source)
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/investigations/{transaction_id}", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_investigation(
        transaction_id: str,
        idempotency_key: str | None = Header(default=None),
    ) -> dict[str, Any]:
        ensure_schema()
        cache_key = f"sentinel:idempotency:{idempotency_key}" if idempotency_key else None
        if cache_key:
            cached = cache.get_json(cache_key)
            if cached and cached.get("transaction_id") == transaction_id:
                return cached
            if not cache.reserve(cache_key, ttl_seconds=60):
                raise HTTPException(status_code=409, detail="Investigation with this idempotency key is in progress")
        production_record = production_transactions.get(transaction_id)
        if production_record is not None:
            transaction = pd.Series(production_record["payload"])
        else:
            try:
                matches = transactions().loc[lambda frame: frame["transaction_id"] == transaction_id]
            except FileNotFoundError as error:
                raise HTTPException(status_code=503, detail=str(error)) from error
            if matches.empty:
                raise HTTPException(status_code=404, detail="Transaction not found")
            transaction = matches.iloc[0]

        # No llm_model is passed: public API never turns a request into a paid
        # external LLM call. The existing deterministic workflow owns scoring.
        result = agent().investigate_transaction(transaction)
        if result.get("errors") or "investigation_summary" not in result:
            raise HTTPException(status_code=503, detail="Investigation could not be completed deterministically")
        persisted = investigations.record(result)
        cache.set_json(f"sentinel:risk:{transaction_id}", persisted, ttl_seconds=300)
        cache.set_json(f"sentinel:network:{transaction_id}", {
            "transaction_id": transaction_id,
            "graph_evidence": result.get("investigation_summary", {}).get("graph_evidence", {}),
        }, ttl_seconds=300)
        if cache_key:
            cache.set_json(cache_key, persisted, ttl_seconds=86_400)
        record_investigation(persisted["risk_tier"])
        return persisted

    @app.get("/transactions/{transaction_id}/risk", dependencies=[Depends(require_api_key)])
    def get_latest_risk(transaction_id: str) -> dict[str, Any]:
        ensure_schema()
        record = cache.get_json(f"sentinel:risk:{transaction_id}")
        if record is None:
            record = investigations.latest_for_transaction(transaction_id)
        if record is None:
            raise HTTPException(status_code=404, detail="No completed investigation found for transaction")
        return {
            "transaction_id": record["transaction_id"],
            "investigation_id": record["investigation_id"],
            "risk_score": record["risk_score"],
            "risk_tier": record["risk_tier"],
            "created_at": record["created_at"],
        }

    @app.get("/transactions/{transaction_id}/network", dependencies=[Depends(require_api_key)])
    def get_network_evidence(transaction_id: str) -> dict[str, Any]:
        ensure_schema()
        cached = cache.get_json(f"sentinel:network:{transaction_id}")
        if cached is not None:
            return cached
        record = investigations.latest_for_transaction(transaction_id)
        if record is None:
            raise HTTPException(status_code=404, detail="No completed investigation found for transaction")
        response = {
            "transaction_id": transaction_id,
            "graph_evidence": record["report"].get("investigation_summary", {}).get("graph_evidence", {}),
        }
        cache.set_json(f"sentinel:network:{transaction_id}", response, ttl_seconds=300)
        return response

    @app.post("/investigations/{investigation_id}/feedback", status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
    def create_feedback(investigation_id: str, payload: FeedbackRequest) -> dict[str, Any]:
        ensure_schema()
        record = None
        # The lookup validates that feedback references a persisted immutable report.
        with database.session() as session:
            from sqlalchemy import select
            from src.database.schema import InvestigationReportRecord

            record = session.scalar(
                select(InvestigationReportRecord).where(
                    InvestigationReportRecord.investigation_id == investigation_id
                )
            )
            if record is not None:
                transaction_id, snapshot = record.transaction_id, record.report
        if record is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        try:
            return feedback.record_feedback(
                investigation_id=investigation_id,
                transaction_id=transaction_id,
                reviewer_id=payload.reviewer_id,
                decision=payload.decision,
                notes=payload.notes,
                investigation_snapshot=snapshot,
            )
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/retraining/eligibility", dependencies=[Depends(require_api_key)])
    def retraining_eligibility() -> dict[str, Any]:
        """Expose only aggregate readiness; labeled payloads remain in the database."""
        ensure_schema()
        _, assessment = FeedbackDatasetBuilder(database).build()
        return assessment

    return app


app = create_app()
