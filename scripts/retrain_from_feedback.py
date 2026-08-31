"""Create a time-based challenger model only when production feedback is eligible."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.database import Database
from src.retraining import FeedbackDatasetBuilder, RetrainingEligibility, log_candidate_to_registry, train_candidate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--artifact-dir", type=Path, default=PROJECT_ROOT / "models" / "candidates")
    parser.add_argument("--min-labeled", type=int, default=500)
    parser.add_argument("--min-positive", type=int, default=50)
    args = parser.parse_args()
    if not args.database_url:
        raise SystemExit("DATABASE_URL is required")
    database = Database(args.database_url)
    dataset, readiness = FeedbackDatasetBuilder(
        database, RetrainingEligibility(args.min_labeled, args.min_positive)
    ).build()
    print(readiness)
    if not readiness["eligible"]:
        raise SystemExit("Retraining blocked: production feedback is not eligible yet.")
    result = train_candidate(dataset, args.artifact_dir)
    run_id, version = log_candidate_to_registry(result)
    print({"run_id": run_id, "registered_model": "SentinelAI-Fraud-Detector", "version": version, "alias": "challenger"})


if __name__ == "__main__":
    main()
