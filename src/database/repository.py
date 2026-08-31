"""Audit-safe repositories shared by FastAPI handlers."""

from __future__ import annotations

import uuid
import json
import math
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import numpy as np
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.human_review import FeedbackDecision

from .schema import HumanFeedbackRecord, InvestigationReportRecord, ProductionTransactionRecord
from .session import Database


def _json_safe(value: dict[str, Any]) -> dict[str, Any]:
    """Return strict JSON: convert non-finite and pandas missing values to null.

    PostgreSQL's JSON parser intentionally rejects JavaScript-only values such
    as ``NaN`` and ``Infinity``. Investigation evidence often originates from
    pandas aggregations, so missing numeric statistics must be represented as
    JSON ``null`` before the audit snapshot is persisted.
    """
    def normalize(item: Any) -> Any:
        if item is None or isinstance(item, (str, bool, int)):
            return item
        if isinstance(item, float):
            return item if math.isfinite(item) else None
        if isinstance(item, np.generic):
            return normalize(item.item())
        if isinstance(item, (pd.Timestamp, datetime)):
            return None if pd.isna(item) else item.isoformat()
        if item is pd.NA or item is pd.NaT:
            return None
        if isinstance(item, dict):
            return {str(key): normalize(nested) for key, nested in item.items()}
        if isinstance(item, (list, tuple, set)):
            return [normalize(nested) for nested in item]
        return str(item)

    normalized = normalize(value)
    # ``allow_nan=False`` is a final invariant check before SQLAlchemy sends
    # JSON to PostgreSQL; it must never serialize non-standard numeric tokens.
    return json.loads(json.dumps(normalized, ensure_ascii=False, allow_nan=False))


class InvestigationRepository:
    """Persist immutable deterministic investigation results."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def record(self, result: dict[str, Any]) -> dict[str, Any]:
        summary = result.get("investigation_summary", {})
        risk_score = summary.get("composite_risk_score")
        risk_tier = summary.get("risk_tier")
        transaction_id = result.get("transaction_id")
        if risk_score is None or not risk_tier or not transaction_id:
            raise ValueError("Only completed deterministic investigations can be persisted")
        record = InvestigationReportRecord(
            investigation_id=str(uuid.uuid4()),
            transaction_id=str(transaction_id),
            risk_score=float(risk_score),
            risk_tier=str(risk_tier),
            report=_json_safe(result),
        )
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return self._as_dict(record)

    def latest_for_transaction(self, transaction_id: str) -> dict[str, Any] | None:
        statement = (
            select(InvestigationReportRecord)
            .where(InvestigationReportRecord.transaction_id == transaction_id)
            .order_by(InvestigationReportRecord.created_at.desc())
            .limit(1)
        )
        with self.database.session() as session:
            record = session.scalar(statement)
            return self._as_dict(record) if record else None

    @staticmethod
    def _as_dict(record: InvestigationReportRecord) -> dict[str, Any]:
        return {
            "investigation_id": record.investigation_id,
            "transaction_id": record.transaction_id,
            "risk_score": record.risk_score,
            "risk_tier": record.risk_tier,
            "report": record.report,
            "created_at": record.created_at.isoformat(),
        }


class ProductionTransactionRepository:
    """Persist production payloads once so reviewed labels can be retrained on."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def record(self, payload: dict[str, Any], source: str = "api") -> dict[str, Any]:
        transaction_id = str(payload.get("transaction_id", "")).strip()
        timestamp = pd.to_datetime(payload.get("timestamp"), utc=True, errors="coerce")
        if not transaction_id:
            raise ValueError("transaction_id is required")
        if pd.isna(timestamp):
            raise ValueError("timestamp must be an ISO-8601 datetime")
        record = ProductionTransactionRecord(
            transaction_id=transaction_id,
            occurred_at=timestamp.to_pydatetime(),
            payload=_json_safe(payload),
            source=source,
        )
        try:
            with self.database.session() as session:
                session.add(record)
                session.commit()
        except IntegrityError as error:
            raise ValueError(f"transaction_id already exists: {transaction_id}") from error
        return self._as_dict(record)

    def get(self, transaction_id: str) -> dict[str, Any] | None:
        with self.database.session() as session:
            record = session.get(ProductionTransactionRecord, transaction_id)
            return self._as_dict(record) if record else None

    @staticmethod
    def _as_dict(record: ProductionTransactionRecord) -> dict[str, Any]:
        return {
            "transaction_id": record.transaction_id,
            "occurred_at": record.occurred_at.isoformat(),
            "payload": record.payload,
            "source": record.source,
            "received_at": record.received_at.isoformat(),
        }


class SqlFeedbackRepository:
    """Append feedback only; never updates or deletes a reviewer decision."""

    def __init__(self, database: Database) -> None:
        self.database = database

    def record_feedback(
        self,
        investigation_id: str,
        transaction_id: str,
        reviewer_id: str,
        decision: FeedbackDecision | str,
        notes: str,
        investigation_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            normalized = FeedbackDecision(decision)
        except ValueError as error:
            raise ValueError(f"Unsupported review decision: {decision!r}") from error
        if not investigation_id.strip() or not transaction_id.strip() or not reviewer_id.strip():
            raise ValueError("investigation_id, transaction_id and reviewer_id are required")
        if normalized is FeedbackDecision.NEED_MORE_INFORMATION and not notes.strip():
            raise ValueError("Notes are required when more information is requested")

        record = HumanFeedbackRecord(
            feedback_id=str(uuid.uuid4()),
            investigation_id=investigation_id.strip(),
            transaction_id=transaction_id.strip(),
            reviewer_id=reviewer_id.strip(),
            decision=normalized.value,
            notes=notes.strip(),
            investigation_snapshot=_json_safe(investigation_snapshot),
        )
        with self.database.session() as session:
            session.add(record)
            session.commit()
        return {
            "feedback_id": record.feedback_id,
            "investigation_id": record.investigation_id,
            "transaction_id": record.transaction_id,
            "decision": record.decision,
            "created_at": record.created_at.isoformat() if record.created_at else datetime.now(timezone.utc).isoformat(),
        }

    def list_feedback(self, limit: int = 200) -> pd.DataFrame:
        """Return latest audit records; this remains read-only."""
        if limit < 1:
            raise ValueError("limit must be positive")
        statement = (
            select(HumanFeedbackRecord)
            .order_by(HumanFeedbackRecord.created_at.desc())
            .limit(limit)
        )
        with self.database.session() as session:
            records = list(session.scalars(statement))
        return pd.DataFrame([
            {
                "feedback_id": row.feedback_id,
                "investigation_id": row.investigation_id,
                "transaction_id": row.transaction_id,
                "reviewer_id": row.reviewer_id,
                "decision": row.decision,
                "notes": row.notes,
                "created_at": row.created_at,
            }
            for row in records
        ])

    def export_feedback_dataset(self) -> pd.DataFrame:
        """Export the same retraining policy as the SQLite adapter."""
        statement = select(HumanFeedbackRecord).order_by(HumanFeedbackRecord.created_at)
        with self.database.session() as session:
            records = list(session.scalars(statement))
        dataset = pd.DataFrame([
            {
                "feedback_id": row.feedback_id,
                "investigation_id": row.investigation_id,
                "transaction_id": row.transaction_id,
                "reviewer_id": row.reviewer_id,
                "decision": row.decision,
                "notes": row.notes,
                "investigation_snapshot": row.investigation_snapshot,
                "created_at": row.created_at,
            }
            for row in records
        ])
        if dataset.empty:
            dataset["review_fraud_label"] = pd.Series(dtype="Int64")
            dataset["ready_for_retraining"] = pd.Series(dtype="bool")
            return dataset
        labels = {
            FeedbackDecision.CONFIRM_FRAUD.value: 1,
            FeedbackDecision.FALSE_POSITIVE.value: 0,
        }
        dataset["review_fraud_label"] = dataset["decision"].map(labels).astype("Int64")
        dataset["ready_for_retraining"] = dataset["review_fraud_label"].notna()
        return dataset
