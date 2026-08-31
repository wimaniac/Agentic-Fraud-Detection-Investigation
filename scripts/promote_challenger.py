"""Explicitly promote a reviewed MLflow challenger to the Champion alias."""

from __future__ import annotations

import argparse
import os


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", required=True, help="Reviewed MLflow model version to promote")
    parser.add_argument("--approve", action="store_true", help="Required acknowledgement of human approval")
    parser.add_argument("--model-name", default="SentinelAI-Fraud-Detector")
    args = parser.parse_args()
    if not args.approve:
        raise SystemExit("Promotion is blocked. Review metrics and run again with --approve.")
    import mlflow
    from mlflow import MlflowClient

    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns"))
    client = MlflowClient()
    version = client.get_model_version(args.model_name, args.version)
    if version.tags.get("promotion_status") != "pending_human_approval":
        raise SystemExit("Version is not an approved candidate state.")
    client.set_registered_model_alias(args.model_name, "champion", args.version)
    client.set_model_version_tag(args.model_name, args.version, "promotion_status", "champion")
    print({"model_name": args.model_name, "champion_version": args.version})


if __name__ == "__main__":
    main()
