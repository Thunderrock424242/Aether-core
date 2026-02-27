import time

from fastapi import Request
from prometheus_client import CONTENT_TYPE_LATEST, CollectorRegistry, Counter, Histogram, generate_latest
from starlette.responses import Response

registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    "aether_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)

REQUEST_LATENCY_SECONDS = Histogram(
    "aether_http_request_latency_seconds",
    "HTTP request latency seconds",
    ["method", "path"],
    registry=registry,
)

GENERATE_REQUESTS = Counter(
    "aether_generate_requests_total",
    "Total /generate requests",
    ["subsystem", "blocked"],
    registry=registry,
)

BACKEND_ATTEMPTS = Counter(
    "aether_backend_attempts_total",
    "Total backend call attempts by operation and outcome",
    ["operation", "url", "outcome"],
    registry=registry,
)

BACKEND_ATTEMPT_LATENCY_SECONDS = Histogram(
    "aether_backend_attempt_latency_seconds",
    "Backend attempt latency seconds",
    ["operation", "url", "outcome"],
    registry=registry,
)

GENERATE_FALLBACK_HOPS = Histogram(
    "aether_generate_fallback_hops",
    "How many fallback hops were required before a successful generate response",
    buckets=(0, 1, 2, 3, 4, 5, 8, 13),
    registry=registry,
)


async def metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - started
    path = request.url.path
    REQUEST_COUNT.labels(request.method, path, str(response.status_code)).inc()
    REQUEST_LATENCY_SECONDS.labels(request.method, path).observe(elapsed)
    return response


def metrics_response() -> Response:
    payload = generate_latest(registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)
