# Datadog Monitors Plan

Use the same scope in all monitors:

- `service:$DD_SERVICE env:$DD_ENV`

Recommended starting thresholds are included below and can be tuned after baseline data.

## Monitor 1: p95 latency for /extract

- Name: `backend /extract p95 latency high`
- Type: `APM Trace Analytics monitor` (Query Alert)
- Query scope:
  - `service:$DD_SERVICE env:$DD_ENV operation_name:fastapi.request resource_name:POST /extract`
- Aggregation:
  - `p95(@duration)`
- Evaluation window:
  - `last 5 minutes`
- Alert condition:
  - `p95(@duration) > 1500 ms`
- Recommended thresholds:
  - Alert: `1500 ms`
  - Warning: `1000 ms`
- No data behavior:
  - `Do not notify` (or notify only in production)

## Monitor 2: Error rate high OR substitute quality degraded

Use a composite monitor so the OR behavior is explicit and maintainable.

## 2A) Child monitor: API error rate high

- Name: `backend error rate high`
- Type: `APM Trace Analytics monitor` (Formula + Query)
- Query A (error count):
  - `service:$DD_SERVICE env:$DD_ENV operation_name:fastapi.request status:error`
  - Compute: `count()`
- Query B (total count):
  - `service:$DD_SERVICE env:$DD_ENV operation_name:fastapi.request`
  - Compute: `count()`
- Formula:
  - `(A / B) * 100`
- Window:
  - `last 10 minutes`
- Condition:
  - Alert if `> 5`

## 2B) Child monitor: candidates_count drops while bom_size is large

- Name: `backend substitute candidates low for large BOM`
- Type: `APM Trace Analytics monitor`
- Prerequisite instrumentation:
  - Add numeric span tag `bom_size` on the substitute request span path (for example on `neo4j.find_substitutes` spans or a parent span).
  - Keep `candidates_count` numeric on `neo4j.find_substitutes` spans (already present).
- Query scope:
  - `service:$DD_SERVICE env:$DD_ENV operation_name:neo4j.find_substitutes @bom_size:>3 @candidates_count:*`
- Aggregation:
  - `avg(@candidates_count)` over `last 10 minutes`
- Condition:
  - Alert if `< 1`

## 2C) Composite monitor (the required OR alert)

- Name: `backend error-or-quality regression`
- Type: `Composite monitor`
- Expression:
  - `monitor("backend error rate high") || monitor("backend substitute candidates low for large BOM")`
- Behavior:
  - Alerts when either API error rate is high OR candidate quality drops for large BOM requests.

## Implementation note

If you must keep exactly two visible monitors in the UI:

- Keep Monitor 1 (`/extract p95`) visible.
- Keep the composite monitor (`backend error-or-quality regression`) visible.
- Mark child monitors 2A and 2B with a prefix like `[child]` and mute their direct notifications.
