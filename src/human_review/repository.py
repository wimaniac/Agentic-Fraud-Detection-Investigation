"""Audit-friendly local persistence for Phase 7 human-review feedback."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


class FeedbackDecision(StrEnum):
    CONFIRM_FRAUD = "CONFIRM_FRAUD"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    NEED_MORE_INFORMATION = "NEED_MORE_INFORMATION"


class HumanFeedbackRepository:
    """Persist append-only reviewer decisions and export a retraining dataset."""

    def __init__(self, db_path: str | Path = "data/feedback/human_feedback.sqlite") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS human_feedback (
                    feedback_id TEXT PRIMARY KEY,
                    transaction_id TEXT NOT NULL,
                    reviewer_id TEXT NOT NULL,
                    decision TEXT NOT NULL CHECK (decision IN (
                        'CONFIRM_FRAUD', 'FALSE_POSITIVE', 'NEED_MORE_INFORMATION'
                    )),
                    notes TEXT NOT NULL,
                    investigation_snapshot TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_feedback_transaction ON human_feedback(transaction_id)"
            )

    def record_feedback(
        self,
        transaction_id: str,
        reviewer_id: str,
        decision: FeedbackDecision | str,
        notes: str,
        investigation_snapshot: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Append one validated human decision; historical decisions are never overwritten."""
        try:
            normalized_decision = FeedbackDecision(decision)
        except ValueError as error:
            raise ValueError(f"Unsupported review decision: {decision!r}") from error
        if not transaction_id.strip() or not reviewer_id.strip():
            raise ValueError("transaction_id and reviewer_id are required")
        if normalized_decision is FeedbackDecision.NEED_MORE_INFORMATION and not notes.strip():
            raise ValueError("Notes are required when more information is requested")

        record = {
            "feedback_id": str(uuid.uuid4()),
            "transaction_id": transaction_id.strip(),
            "reviewer_id": reviewer_id.strip(),
            "decision": normalized_decision.value,
            "notes": notes.strip(),
            "investigation_snapshot": json.dumps(investigation_snapshot, default=str, ensure_ascii=False),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO human_feedback (
                    feedback_id, transaction_id, reviewer_id, decision, notes,
                    investigation_snapshot, created_at
                ) VALUES (
                    :feedback_id, :transaction_id, :reviewer_id, :decision, :notes,
                    :investigation_snapshot, :created_at
                )
                """,
                record,
            )
        return record

    def list_feedback(self, limit: int = 200) -> pd.DataFrame:
        """Return latest feedback records for the review dashboard."""
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            return pd.read_sql_query(
                """
                SELECT feedback_id, transaction_id, reviewer_id, decision, notes, created_at
                FROM human_feedback
                ORDER BY created_at DESC
                LIMIT ?
                """,
                connection,
                params=(limit,),
            )

    def export_feedback_dataset(self) -> pd.DataFrame:
        """Export reviewer labels without unresolved cases as fraud training labels."""
        with self._connect() as connection:
            dataset = pd.read_sql_query(
                """
                SELECT feedback_id, transaction_id, reviewer_id, decision, notes,
                       investigation_snapshot, created_at
                FROM human_feedback
                ORDER BY created_at
                """,
                connection,
            )
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
