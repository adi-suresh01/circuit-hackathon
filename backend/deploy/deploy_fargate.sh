#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_ROOT="$(cd "${BACKEND_DIR}/.." && pwd)"
TEMPLATE_PATH="${SCRIPT_DIR}/ecs-taskdef.fargate.datadog.tpl.json"

require_command() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

require_env() {
  local name="$1"
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required environment variable: ${name}" >&2
    exit 1
  fi
}

append_optional_secret() {
  local secret_arn_var="$1"
  local secret_name="$2"
  local input_path="$3"
  local output_path

  if [[ -z "${!secret_arn_var:-}" ]]; then
    return 0
  fi

  output_path="$(mktemp)"
  jq \
    --arg secret_name "${secret_name}" \
    --arg secret_arn "${!secret_arn_var}" \
    '.containerDefinitions |= map(if .name == "backend" then .secrets += [{"name": $secret_name, "valueFrom": $secret_arn}] else . end)' \
    "${input_path}" > "${output_path}"
  mv "${output_path}" "${input_path}"
}

aws_cmd() {
  aws --profile "${AWS_PROFILE}" --region "${AWS_REGION}" "$@"
}

require_command aws
require_command docker
require_command envsubst
require_command jq

: "${AWS_PROFILE:=default}"
: "${AWS_REGION:=us-west-2}"
: "${ECR_REPO:=circuit-backend}"
: "${ECS_TASK_FAMILY:=circuit-backend}"
: "${TASK_CPU:=1024}"
: "${TASK_MEMORY:=2048}"
: "${DD_SITE:=datadoghq.com}"
: "${DD_SERVICE:=circuit-backend}"
: "${DD_ENV:=prod}"
: "${LOG_LEVEL:=INFO}"
: "${BEDROCK_MODEL_ID:=nvidia.nemotron-nano-12b-v2}"
: "${DIGIKEY_USE_SANDBOX:=false}"
: "${DIGIKEY_ACCOUNT_ID:=}"
: "${DIGIKEY_LOCALE_SITE:=US}"
: "${DIGIKEY_LOCALE_LANGUAGE:=en}"
: "${DIGIKEY_LOCALE_CURRENCY:=USD}"
: "${DIGIKEY_HTTP_TIMEOUT_S:=20}"
: "${ENABLE_MINIMAX_NARRATOR:=false}"
: "${MINIMAX_BASE_URL:=https://api.minimax.io}"
: "${MINIMAX_MODEL:=MiniMax-M2.5-highspeed}"

require_env ECS_CLUSTER
require_env ECS_SERVICE
require_env TASK_EXECUTION_ROLE_ARN
require_env TASK_ROLE_ARN
require_env DD_API_KEY_SECRET_ARN
require_env NEO4J_URI
require_env NEO4J_USERNAME
require_env NEO4J_PASSWORD_SECRET_ARN

if [[ -z "${AWS_ACCOUNT_ID:-}" ]]; then
  AWS_ACCOUNT_ID="$(aws_cmd sts get-caller-identity --query Account --output text)"
fi

if [[ -z "${IMAGE_TAG:-}" ]]; then
  IMAGE_TAG="$(git -C "${REPO_ROOT}" rev-parse --short HEAD 2>/dev/null || date +%Y%m%d%H%M%S)"
fi

APP_IMAGE="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}:${IMAGE_TAG}"
: "${APP_LOG_GROUP:=/ecs/${ECS_TASK_FAMILY}/backend}"
: "${DD_LOG_GROUP:=/ecs/${ECS_TASK_FAMILY}/datadog-agent}"

echo "Using image: ${APP_IMAGE}"
echo "Ensuring ECR repo exists: ${ECR_REPO}"
if ! aws_cmd ecr describe-repositories --repository-names "${ECR_REPO}" >/dev/null 2>&1; then
  aws_cmd ecr create-repository --repository-name "${ECR_REPO}" >/dev/null
fi

echo "Ensuring CloudWatch log groups exist"
aws_cmd logs create-log-group --log-group-name "${APP_LOG_GROUP}" >/dev/null 2>&1 || true
aws_cmd logs create-log-group --log-group-name "${DD_LOG_GROUP}" >/dev/null 2>&1 || true

echo "Logging in to ECR"
aws_cmd ecr get-login-password | docker login \
  --username AWS \
  --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"

echo "Building backend image"
docker build -t "${APP_IMAGE}" "${BACKEND_DIR}"

echo "Pushing backend image"
docker push "${APP_IMAGE}"

tmp_taskdef="$(mktemp)"
trap 'rm -f "${tmp_taskdef}"' EXIT

echo "Rendering ECS task definition from template"
export ECS_TASK_FAMILY TASK_CPU TASK_MEMORY TASK_EXECUTION_ROLE_ARN TASK_ROLE_ARN
export DD_SITE DD_ENV DD_API_KEY_SECRET_ARN DD_LOG_GROUP
export APP_IMAGE LOG_LEVEL AWS_REGION BEDROCK_MODEL_ID NEO4J_URI NEO4J_USERNAME
export DIGIKEY_USE_SANDBOX DIGIKEY_ACCOUNT_ID DIGIKEY_LOCALE_SITE DIGIKEY_LOCALE_LANGUAGE
export DIGIKEY_LOCALE_CURRENCY DIGIKEY_HTTP_TIMEOUT_S ENABLE_MINIMAX_NARRATOR
export MINIMAX_BASE_URL MINIMAX_MODEL DD_SERVICE IMAGE_TAG NEO4J_PASSWORD_SECRET_ARN
export APP_LOG_GROUP

envsubst < "${TEMPLATE_PATH}" > "${tmp_taskdef}"

append_optional_secret DIGIKEY_CLIENT_ID_SECRET_ARN DIGIKEY_CLIENT_ID "${tmp_taskdef}"
append_optional_secret DIGIKEY_CLIENT_SECRET_ARN DIGIKEY_CLIENT_SECRET "${tmp_taskdef}"
append_optional_secret MINIMAX_API_KEY_SECRET_ARN MINIMAX_API_KEY "${tmp_taskdef}"

jq empty "${tmp_taskdef}" >/dev/null

echo "Registering ECS task definition"
task_definition_arn="$(
  aws_cmd ecs register-task-definition \
    --cli-input-json "file://${tmp_taskdef}" \
    --query 'taskDefinition.taskDefinitionArn' \
    --output text
)"
echo "Registered task definition: ${task_definition_arn}"

echo "Updating ECS service ${ECS_SERVICE} in cluster ${ECS_CLUSTER}"
aws_cmd ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${ECS_SERVICE}" \
  --task-definition "${task_definition_arn}" \
  --force-new-deployment >/dev/null

echo "Waiting for service stabilization"
aws_cmd ecs wait services-stable --cluster "${ECS_CLUSTER}" --services "${ECS_SERVICE}"

echo "Deploy complete."
echo "Next: run backend/deploy/smoke_test.sh against your ALB URL."
