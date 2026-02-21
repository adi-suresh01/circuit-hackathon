# Datadog Dashboard Plan

This plan creates one dashboard focused on image-upload demo flow metrics (`/extract` + `/pipeline/demo`) for `DD_SERVICE` + `DD_ENV`.

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

## Widget 4: /extract and /pipeline request volume

- Title: `Image upload flow request volume`
- Type: `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:$web_op (resource_name:POST /extract OR resource_name:POST /pipeline/demo)`
- Compute:
  - `count()`
- Group by:
  - `resource_name`

## Widget 5: Bedrock span latency p95

- Title: `Bedrock extract p95 latency`
- Type: `Query Value` or `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:bedrock.extract_bom`
- Compute:
  - `p95(@duration)`
- Display:
  - Unit: `ms`

## Widget 6: Image bytes distribution

- Title: `Uploaded image size distribution (bytes)`
- Type: `Distribution` (or `Heatmap`)
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:bedrock.extract_bom @image.bytes:*`
- Measure:
  - `@image.bytes`
- Optional split:
  - `resource_name`

## Widget 7: BOM size distribution from uploads

- Title: `Extracted BOM size distribution`
- Type: `Distribution` (or `Heatmap`)
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:bedrock.extract_bom @bom.size:*`
- Measure:
  - `@bom.size`

## Widget 8: Neo4j span latency p95

- Title: `Neo4j find_substitutes p95 latency`
- Type: `Query Value` or `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:neo4j.find_substitutes`
- Compute:
  - `p95(@duration)`
- Display:
  - Unit: `ms`

## Widget 9: Digi-Key pricing span p95

- Title: `Digi-Key pricing_by_quantity p95 latency`
- Type: `Query Value` or `Timeseries`
- Data source: `APM Spans`
- Query filter:
  - `service:$dd_service env:$dd_env operation_name:supplier.digikey.pricing_by_quantity`
- Compute:
  - `p95(@duration)`
- Display:
  - Unit: `ms`

## Widget 10: candidates_count distribution

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

- If `@candidates_count`, `@image.bytes`, or `@bom.size` do not appear in the measure picker, open APM Trace Explorer and create each as a measure.
- Keep all queries filtered by both `service:$dd_service` and `env:$dd_env` to avoid cross-service noise.
