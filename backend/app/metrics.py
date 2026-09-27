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

TRIAGE_LATENCY = Histogram(
    "civicpulse_triage_duration_seconds",
    "Time to triage one complaint, by the provider that produced the result",
    ["provider"],
    buckets=(0.005, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0),
)
TRIAGE_FALLBACKS = Counter(
    "civicpulse_triage_fallback_total",
    "Triage calls that fell back to the rule-based provider",
    ["provider", "error"],
)
TRIAGE_CACHE = Counter(
    "civicpulse_triage_cache_total",
    "Triage cache lookups by result",
    ["result"],  # hit | miss
)
