# A.E.T.H.E.R Production Orchestration & Observability

A production stack is now provided in `deploy/production/`.

## Stack

- `aether-sidecar` (FastAPI runtime)
- `prometheus` for metrics scraping
- `grafana` for dashboards
- `loki` for logs backend

## Sidecar observability

The sidecar now exposes `GET /metrics` with Prometheus metrics such as:

- `aether_http_requests_total`
- `aether_http_request_latency_seconds`
- `aether_generate_requests_total`
- `aether_backend_attempts_total`
- `aether_backend_attempt_latency_seconds`
- `aether_generate_fallback_hops`

## Start stack

```bash
cd deploy/production
docker compose up
```

Grafana is available at `http://localhost:3000`.
Prometheus is available at `http://localhost:9090`.
