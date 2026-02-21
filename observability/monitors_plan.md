# Datadog Monitors Plan

Use this scope in all monitors:

- `service:$DD_SERVICE env:$DD_ENV`

## Monitor 1: p95 latency on image upload flow

- Name: `backend image flow latency high`
- Type: `APM Trace Analytics monitor` (Query Alert)
- Query scope:
  - `service:$DD_SERVICE env:$DD_ENV operation_name:fastapi.request (resource_name:POST /extract OR resource_name:POST /pipeline/demo)`
- Aggregation:
  - `p95(@duration)` over `last 5 minutes`
- Condition:
  - Alert if `> 2000 ms`
  - Warning if `> 1200 ms`

## Monitor 2: Upload parsing failures OR quality drop

Use a composite monitor to keep a single top-level alert.

## 2A) Child monitor: parse warnings on extract

- Name: `[child] backend extract parse warnings high`
- Type: `APM Trace Analytics monitor`
- Query scope:
  - `service:$DD_SERVICE env:$DD_ENV operation_name:bedrock.extract_bom @bom.parse_warnings_count:*`
- Aggregation:
  - `avg(@bom.parse_warnings_count)` over `last 10 minutes`
- Condition:
  - Alert if `> 0.5`

## 2B) Child monitor: candidates_count drops for uploaded BOMs

- Name: `[child] backend candidates low for uploaded BOM`
- Type: `APM Trace Analytics monitor`
- Query scope:
  - `service:$DD_SERVICE env:$DD_ENV operation_name:neo4j.find_substitutes @candidates_count:* @item.type:*`
- Aggregation:
  - `avg(@candidates_count)` over `last 10 minutes`
- Condition:
  - Alert if `< 1`

## 2C) Composite monitor

- Name: `backend upload parse-or-quality regression`
- Type: `Composite monitor`
- Expression:
  - `monitor("[child] backend extract parse warnings high") || monitor("[child] backend candidates low for uploaded BOM")`

## Notes

- Keep only Monitor 1 and Monitor 2 visible in on-call dashboards; child monitors can be muted for direct paging.
- If `@bom.parse_warnings_count` or `@candidates_count` are not selectable, create them as measures in APM Trace Explorer first.
