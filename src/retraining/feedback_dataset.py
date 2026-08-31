"""Build a labeled, time-ordered retraining dataset from production review feedback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
from sqlalchemy import select

from src.database.schema import HumanFeedbackRecord, ProductionTransactionRecord
from src.database.session import Database
from src.human_review import FeedbackDecision


REQUIRED_RAW_COLUMNS = {
    "transaction_id", "timestamp", "account_id", "amount", "velocity_1h",
    "amount_vs_avg_ratio", "time_since_last_s", "ip_risk_score", "hour_of_day",
    "day_of_week", "is_weekend", "is_foreign_txn", "card_present", "device_known",
    "has_2fa", "account_age_days", "credit_limit", "in_ring", "account_degree",
    "n_shared_types",
}


@dataclass(frozen=True)
class RetrainingEligibility:
    """Minimum evidence needed before a candidate model can be trained."""

    minimum_labeled_rows: int = 500
    minimum_positive_rows: int = 50

    def assess(self, dataset: pd.DataFrame) -> dict[str, Any]:
        positives = int(dataset["is_fraud"].sum()) if "is_fraud" in dataset else 0
        missing = sorted(REQUIRED_RAW_COLUMNS.difference(dataset.columns))
        return {
            "eligible": len(dataset) >= self.minimum_labeled_rows and positives >= self.minimum_positive_rows and not missing,
            "labeled_rows": len(dataset),
            "positive_rows": positives,
            "minimum_labeled_rows": self.minimum_labeled_rows,
            "minimum_positive_rows": self.minimum_positive_rows,
            "missing_columns": missing,
        }


class FeedbackDatasetBuilder:
    """Join only resolved human labels to their captured production payloads."""

    def __init__(self, database: Database, eligibility: RetrainingEligibility | None = None) -> None:
        self.database = database
        self.eligibility = eligibility or RetrainingEligibility()

    def build(self) -> tuple[pd.DataFrame, dict[str, Any]]:
        statement = (
            select(HumanFeedbackRecord, ProductionTransactionRecord)
            .join(
                ProductionTransactionRecord,
                HumanFeedbackRecord.transaction_id == ProductionTransactionRecord.transaction_id,
            )
            .where(HumanFeedbackRecord.decision.in_([
                FeedbackDecision.CONFIRM_FRAUD.value,
                FeedbackDecision.FALSE_POSITIVE.value,
            ]))
            .order_by(ProductionTransactionRecord.occurred_at, HumanFeedbackRecord.created_at)
        )
        with self.database.session() as session:
            rows = list(session.execute(statement))

        # A transaction may receive multiple review records. Keep its most recent
        # resolved review to avoid duplicating one transaction in a training set.
        latest: dict[str, tuple[HumanFeedbackRecord, ProductionTransactionRecord]] = {}
        for feedback, transaction in rows:
            latest[transaction.transaction_id] = (feedback, transaction)

        examples: list[dict[str, Any]] = []
        labels = {
            FeedbackDecision.CONFIRM_FRAUD.value: 1,
            FeedbackDecision.FALSE_POSITIVE.value: 0,
        }
        for feedback, transaction in latest.values():
            example = dict(transaction.payload)
            example["is_fraud"] = labels[feedback.decision]
            example["reviewed_at"] = feedback.created_at.isoformat()
            examples.append(example)
        dataset = pd.DataFrame(examples)
        if not dataset.empty:
            dataset["timestamp"] = pd.to_datetime(dataset["timestamp"], utc=True, errors="coerce")
            dataset = dataset.sort_values("timestamp").reset_index(drop=True)
        return dataset, self.eligibility.assess(dataset)
