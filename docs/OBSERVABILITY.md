# Observability

Metrics, logs, traces and errors for every process of the app (Phase 12). It all runs locally in Docker, with free and open-source tools. Splunk is the one exception: it is optional and runs with its Free license.

## Start it

The observability stack is a second Compose file on top of the main one:

```sh
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.observability.yml up -d --build
```

| Tool | URL | What for |
|---|---|---|
| Grafana | http://localhost:3000 | Dashboards open without a login. Explore (searching logs and traces) needs `admin` / `finnancial_dev` |
| Prometheus | http://localhost:9090 | Raw metrics, scrape targets (`/targets`) and alert rules (`/alerts`) |
| GlitchTip | http://localhost:8001 | Errors with their stack trace (`admin@example.com` / `finnancial_dev`) |

These ports only listen on this machine. The passwords are fixed because the setup is local; they are not secrets.

Without the second file, nothing changes: the app sends no telemetry and keeps its readable console logs.

## What is collected

| Signal | Where it comes from | Where it goes |
|---|---|---|
| Metrics | The API serves `/metrics`. The relay, each consumer and the Celery worker serve their own on port 9100. RabbitMQ has its built-in exporter | Prometheus, every 15 s |
| Logs | Every container's output. Backend lines are JSON (`LOG_FORMAT=json`) carrying `request_id` and `trace_id` | Alloy reads them through the Docker socket and pushes them to Loki |
| Traces | OpenTelemetry in the API (FastAPI's own spans), relay, consumers and worker, plus SQLAlchemy, Redis and Celery | The app sends OTLP to Alloy, which forwards it to Tempo |
| Errors | The Sentry SDK in the API, relay, consumers, worker and beat | GlitchTip, which speaks the Sentry protocol |

### Metrics

| Metric | Labels | Meaning |
|---|---|---|
| `http_requests_total` | method, route, status | Requests answered. `route` is the template (`/api/v1/months/{month_id}`); paths that match no route are counted under `unmatched` |
| `http_request_duration_seconds` | method, route | Latency histogram |
| `http_requests_in_progress` | | Requests being answered, including open alert streams |
| `outbox_events_published_total`, `outbox_events_pending` | | Relay throughput and backlog |
| `events_consumed_total` | consumer, outcome | `handled`, `duplicate`, `retried`, `dead_lettered`, `malformed` |
| `event_handle_duration_seconds` | consumer | Time per event |
| `celery_tasks_total` | task, outcome | `succeeded`, `failed`, `retried` |
| `celery_task_duration_seconds` | task | Task run time |
| `rabbitmq_detailed_queue_messages_ready` and similar | queue | Queue depth and consumers, from RabbitMQ |

Labels never carry user ids, entry ids or raw paths.

### Dashboards

Both live in the FinnancialSystem folder. They are provisioned from `deploy/observability/grafana/dashboards/` and read-only in the UI; change the JSON files instead.

- **API**: requests per second, share of server errors, p50/p95/p99 latency, the slowest routes, errors by route, and API warnings from the logs.
- **Events and jobs**: outbox backlog, dead letters, messages waiting and consumers per queue, events by outcome, time per event, Celery tasks and their duration, and background warnings from the logs.

### Alert rules

`deploy/observability/prometheus/alerts.yml` defines five rules: server errors, slow API (p95 above 1 s), dead letters, outbox backlog and a process that stops answering. They show up in Prometheus and Grafana and are not sent anywhere: this is a personal setup with no on-call.

## Following a problem

1. Every API response carries an `X-Request-ID` header. nginx creates the id and the API keeps it.
2. In Grafana → Explore → Loki, run `{service="api"} | request_id="<id>"` to see the request's log lines.
3. Expand a line and choose **Open the trace**: Tempo shows the request, its SQL and Redis calls, and what happened later in other processes. That includes the relay publishing the event, each consumer handling it, and any Celery task the request started, all in the same trace. From a span, **Logs for this span** goes back to Loki.
4. If something raised, GlitchTip has the stack trace, tagged with the process name.

The outbox carries the trace across processes: each event stores the trace context (`traceparent`) of the request that wrote it, the relay puts it in the message headers, and the consumer continues the same trace.

## Privacy

This app holds personal finances, so the telemetry is kept lean:

- Error reports never include request bodies, and the SDK scrubs cookies, tokens and passwords.
- SQL spans carry the statement with placeholders (`$1`), never the values.
- Logs record the method, route template, status and duration of each request, never bodies or amounts.
- Nothing leaves the machine: every tool runs in local containers.

## Optional: Splunk (experimental)

> **Not verified end to end.** On Apple Silicon the Splunk container starts (about 10 minutes the first time, emulated) and reports healthy, but in the Phase 12 tests its HTTP Event Collector and web interface did not answer, so no logs reached it. The configuration is kept for an amd64 machine or a later look; the Grafana stack above is the supported path.

To practise with Splunk, add the `splunk` profile:

```sh
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.observability.yml --profile splunk up -d
```

Splunk opens at http://localhost:8002 with the Free license, which has no login. A second Alloy sends the same container logs to Splunk's HTTP Event Collector, in the `main` index. Search for `index=main source=finnancial`.

Splunk publishes only an amd64 image. On Apple Silicon it runs emulated (Rosetta), needs about 4 GB of memory and is slow. The Free license accepts up to 500 MB of data per day, far more than this app writes.

## Settings

All of these are off when empty, which is how tests and the plain Compose stack run.

| Variable | Effect |
|---|---|
| `LOG_FORMAT` | `json` or `console`. When empty: console in dev and test, JSON elsewhere |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Where traces go (OTLP over HTTP), for example `http://alloy:4318` |
| `SENTRY_DSN` | The GlitchTip project DSN. The Compose setup creates the project with a fixed DSN (`deploy/observability/glitchtip/bootstrap.py`) |
| `METRICS_PORT` | The port background processes serve `/metrics` on (default 9100) |
| `PROMETHEUS_MULTIPROC_DIR` | Set for the Celery worker only: its pool processes share their samples there |
