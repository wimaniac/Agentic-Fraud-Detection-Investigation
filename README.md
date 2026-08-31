# SentinelAI

SentinelAI is an end-to-end fraud detection and investigation platform for
suspicious financial transactions. It combines a calibrated XGBoost model with
deterministic evidence gathering, explainability, human review, and a controlled
MLflow model lifecycle.

> This repository is a technical demonstration, not a financial decisioning
> service. Do not submit real customer, account, device, IP, or transaction data
> to the public demo.

## What it does

```text
Transaction
  -> feature engineering
  -> calibrated XGBoost probability
  -> ML-only Risk Score (0-100) and escalation flags
  -> deterministic investigation
  -> Investigation Report
  -> Human Review
  -> approved production-feedback retraining
```

### Core design decisions

- **Risk score is calibrated ML only.** Rule, anomaly, and graph findings are
  separate escalation signals and investigation evidence; they are not added to
  the score.
- Risk tiers are fixed: `LOW < 30`, `MEDIUM 30-<70`, `HIGH >= 70`.
- Graph structure contributes through the feature pipeline
  (`in_ring`, `account_degree`, `n_shared_types`). Historical fraud labels are
  investigation-only evidence, never online model features.
- The investigation workflow is deterministic. DeepSeek is optional and may
  only turn completed evidence into a natural-language report.
- Human feedback is append-only. Only resolved `CONFIRM_FRAUD` and
  `FALSE_POSITIVE` decisions may become retraining labels.

## Components

| Area | Implementation |
| --- | --- |
| Fraud model | Calibrated XGBoost with chronological train/calibration/holdout evaluation |
| Feature engineering | Shared `extract_features(..., mode="train"|"infer")` pipeline |
| Detection evidence | Rule engine, Isolation Forest escalation, graph investigation, history and similar-case tools |
| Explainability | Native XGBoost TreeSHAP plus rule and graph evidence |
| Human review | Streamlit dashboard with append-only reviewer feedback |
| API | FastAPI, API-key protection, PostgreSQL persistence and fail-open Redis cache |
| Observability | Structured logs, Prometheus metrics and MLflow tracking/Registry |
| Deployment | Docker Compose: API, dashboard, PostgreSQL, Redis, Neo4j, MLflow and Prometheus |

## Repository layout

```text
src/
  features/          # feature pipeline
  anomaly/           # independent anomaly signal
  rule_engine/       # rules and rule evidence
  graph_engine/      # graph utilities
  risk_engine/       # ML-only score aggregation and tiers
  investigation/     # deterministic workflow and evidence tools
  human_review/      # append-only feedback stores
  api/               # FastAPI application
  retraining/        # feedback curation and challenger training
  serving/           # local/MLflow champion model resolution
streamlit_app.py     # internal human-review dashboard
demo_app.py          # public synthetic-only Streamlit demo
scripts/             # MLflow import, retraining and promotion commands
docker-compose.yml   # local service stack
```

## Quick start

Requires Python 3.12+ and `uv`.

```powershell
rtk uv sync
rtk uv run python -m compileall -q src streamlit_app.py demo_app.py
rtk uv run streamlit run streamlit_app.py
```

The internal dashboard requires local model/data artifacts and must not be
deployed publicly with production data.

## Public Streamlit demo

For Streamlit Community Cloud, deploy `demo_app.py` as the main file. It uses
only synthetic, precomputed scenarios and has no secrets, database, model
artifacts, or external API calls. The root `requirements.txt` intentionally
contains only the dependencies needed by that public demo.

Do not deploy `streamlit_app.py` publicly unless it has been specifically
adapted to use a sanitized demo dataset and no persistent customer data.

## Local production-style stack

Create a local `.env` from `.env.example`, set a strong `SENTINEL_API_KEY`, then
start the service stack:

```powershell
docker compose up -d --build
```

The local endpoints are API `8000`, dashboard `8501`, MLflow `5000`, and
Prometheus `9090`. Never commit `.env`, local data, fitted model artifacts,
feedback databases, or generated exports.

## Model lifecycle

1. Ingest a production transaction through the API.
2. Run deterministic investigation and complete human review.
3. Check aggregate readiness at `/retraining/eligibility`.
4. Train a chronological candidate from resolved feedback.
5. Log metrics/artifacts to MLflow and register it as `challenger`.
6. Review its holdout metrics, then explicitly promote it to `champion`.
7. Configure API serving to resolve the MLflow `champion` alias.

Promotion never happens automatically. A historical model import is audit-only
and is not implicitly trusted as a champion.

## Security and data handling

- Keep secrets in `.env` locally or a deployment secret manager.
- Keep raw transaction/account/device/IP data and reviewer notes out of source
  control and public demos.
- Do not use historical fraud labels in online decisions or serving features.
- Do not let an LLM calculate scores, assign tiers, route investigation tools,
  or override deterministic policy.

## Status

Phases 1-9 are implemented: modelling, anomaly/rule/graph evidence,
deterministic investigation, human review, explainability, API/persistence,
observability, Docker Compose, MLflow, and production-feedback candidate
lifecycle. Operational hardening still matters before a real financial
production deployment: label maturity, promotion gates, data validation,
monitoring, access control, migration strategy, retention, and encryption.
