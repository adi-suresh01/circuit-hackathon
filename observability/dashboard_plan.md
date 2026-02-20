# Datadog Dashboard Plan

This plan creates one dashboard with 6 widgets for `DD_SERVICE` + `DD_ENV`.

## 1) Dashboard Template Variables

Create these template variables first:

- `dd_service`
  - Default: your `DD_SERVICE` value (example: `circuit-backend`)
- `dd_env`
  - Default: your `DD_ENV` value (example: `local`)
- `web_op`
  - Default: `fastapi.request`
  - If your traces use another inbound operation name, set that value (for example `asgi.request`).

All widget filters below must include:

- `service:$dd_service env:$dd_env`

## 2) Widgets (Create In This Order)

## Widget 1: Requests by endpoint

- Title: `Requests by endpoint`
- Type: `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:$web_op`
- Compute:
  - `count()`
- Group by:
  - `resource_name`
- Display:
  - Stacked lines or stacked bars
  - Top 10 by value

## Widget 2: p95 latency by endpoint

- Title: `p95 latency by endpoint`
- Type: `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:$web_op`
- Compute:
  - `p95(@duration)`
- Group by:
  - `resource_name`
- Display:
  - Unit: `ms`
  - Top 10 by value

## Widget 3: Error rate by endpoint

- Title: `Error rate by endpoint (%)`
- Type: `Timeseries` with `Formula`
- Data source: `APM Spans`
- Query A (errors):
  - Filter: `service:$dd_service env:$dd_env operation_name:$web_op status:error`
  - Compute: `count()`
  - Group by: `resource_name`
- Query B (total):
  - Filter: `service:$dd_service env:$dd_env operation_name:$web_op`
  - Compute: `count()`
  - Group by: `resource_name`
- Formula:
  - `(A / B) * 100`
- Display:
  - Unit: `%`
  - Top 10 by value

## Widget 4: Bedrock span latency p95

- Title: `Bedrock extract p95 latency`
- Type: `Query Value` or `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:bedrock.extract_bom`
- Compute:
  - `p95(@duration)`
- Display:
  - Unit: `ms`

## Widget 5: Neo4j span latency p95

- Title: `Neo4j find_substitutes p95 latency`
- Type: `Query Value` or `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:neo4j.find_substitutes`
- Compute:
  - `p95(@duration)`
- Display:
  - Unit: `ms`

## Widget 6: candidates_count distribution

- Title: `Candidates count distribution`
- Type: `Distribution` (or `Heatmap`)
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:neo4j.find_substitutes @candidates_count:*`
- Measure:
  - `@candidates_count`
- Optional split:
  - `@chaos_mode` (to compare chaos on/off)

## 3) Notes

- If `@candidates_count` does not appear in the measure picker, open APM Trace Explorer and create it as a measure.
- Keep all queries filtered by both `service:$dd_service` and `env:$dd_env` to avoid cross-service noise.
