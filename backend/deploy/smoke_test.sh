#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-${BASE_URL:-}}"
IMAGE_PATH="${2:-${IMAGE_PATH:-}}"

if [[ -z "${BASE_URL}" ]]; then
  echo "Usage: BASE_URL=https://<alb-dns> $0 [image_path]" >&2
  exit 1
fi

if [[ -z "${IMAGE_PATH}" ]]; then
  if [[ -f "./schematic.png" ]]; then
    IMAGE_PATH="./schematic.png"
  elif [[ -f "../schematic.png" ]]; then
    IMAGE_PATH="../schematic.png"
  fi
fi

print_result() {
  local endpoint="$1"
  local headers_file="$2"
  local body_file="$3"
  local status
  local trace_id

  status="$(awk 'toupper($1) ~ /^HTTP\\// {code=$2} END{print code}' "${headers_file}")"
  trace_id="$(awk 'tolower($1)=="x-trace-id:" {print $2}' "${headers_file}" | tr -d '\r')"
  echo "${endpoint} status=${status} x-trace-id=${trace_id:-n/a}"
  cat "${body_file}"
  echo
}

call_endpoint() {
  local label="$1"
  shift
  local headers_file body_file
  headers_file="$(mktemp)"
  body_file="$(mktemp)"
  curl -sS -D "${headers_file}" "$@" > "${body_file}"
  print_result "${label}" "${headers_file}" "${body_file}"
  rm -f "${headers_file}" "${body_file}"
}

echo "Smoke test against ${BASE_URL}"
call_endpoint "GET /health" "${BASE_URL%/}/health"
call_endpoint "GET /ready" "${BASE_URL%/}/ready"

if [[ -n "${IMAGE_PATH}" && -f "${IMAGE_PATH}" ]]; then
  call_endpoint \
    "POST /extract" \
    -X POST "${BASE_URL%/}/extract" \
    -F "image=@${IMAGE_PATH}"
else
  echo "Skipping /extract smoke test: image file not found. Pass IMAGE_PATH or arg #2."
fi
