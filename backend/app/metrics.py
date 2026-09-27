"""Prometheus metrics, defined once and imported wherever they are recorded."""

from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "civicpulse_http_requests_total",
    "Total HTTP requests received",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "civicpulse_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)
