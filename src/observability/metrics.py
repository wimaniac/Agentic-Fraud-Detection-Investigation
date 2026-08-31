"""Low-cardinality Prometheus metrics; no transaction/account labels."""

from __future__ import annotations

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


HTTP_REQUESTS = Counter(
    "sentinel_http_requests_total", "HTTP requests processed", ["method", "route", "status_code"]
)
HTTP_DURATION = Histogram(
    "sentinel_http_request_duration_seconds", "HTTP request duration", ["method", "route"]
)
INVESTIGATIONS = Counter(
    "sentinel_investigations_total", "Completed investigations", ["risk_tier"]
)


def record_request(method: str, route: str, status_code: int, duration_seconds: float) -> None:
    """Record route-level operational metrics only."""
    HTTP_REQUESTS.labels(method, route, str(status_code)).inc()
    HTTP_DURATION.labels(method, route).observe(duration_seconds)


def record_investigation(risk_tier: str) -> None:
    """Record a completed investigation without customer-identifying labels."""
    INVESTIGATIONS.labels(risk_tier).inc()


def render_metrics() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
