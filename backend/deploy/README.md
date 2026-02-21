# ECS Fargate + Datadog Deployment

This folder contains a working deployment path for the backend on ECS Fargate with Datadog APM/logs.

## What this deploy script does

- Builds and pushes Docker image to ECR.
- Renders/registers an ECS task definition with:
  - `backend` app container (port `8080`).
  - `datadog-agent` sidecar (APM enabled).
- Updates an existing ECS service and waits for stabilization.

## Prerequisites

- Existing ECS cluster and service (Fargate launch type).
- Service load balancer target should use container `backend:8080`.
- Task execution role with ECR pull + CloudWatch logs permissions.
- Task role with:
  - Bedrock access (`bedrock:Converse` for your model).
  - Secrets Manager/SSM access for referenced secret ARNs.
- VPC routing/NAT for outbound internet (Datadog + external APIs).
- AWS CLI, Docker, `jq`, `envsubst`.

## Required secrets

- Datadog API key secret ARN (`DD_API_KEY_SECRET_ARN`).
- Neo4j password secret ARN (`NEO4J_PASSWORD_SECRET_ARN`).
- Optional:
  - `DIGIKEY_CLIENT_ID_SECRET_ARN`
  - `DIGIKEY_CLIENT_SECRET_ARN`
  - `MINIMAX_API_KEY_SECRET_ARN`

## Deploy

Run from repo root:

```bash
cd backend
chmod +x deploy/deploy_fargate.sh deploy/smoke_test.sh
```

Set deployment variables (replace placeholders):

```bash
export AWS_PROFILE=hackathon
export AWS_REGION=us-west-2
export ECS_CLUSTER=<your-ecs-cluster>
export ECS_SERVICE=<your-ecs-service>
export ECR_REPO=circuit-backend
export ECS_TASK_FAMILY=circuit-backend

export TASK_EXECUTION_ROLE_ARN=arn:aws:iam::<acct-id>:role/<ecs-execution-role>
export TASK_ROLE_ARN=arn:aws:iam::<acct-id>:role/<backend-task-role>

export DD_API_KEY_SECRET_ARN=arn:aws:secretsmanager:us-west-2:<acct-id>:secret:<dd-api-key-secret>
export NEO4J_URI=bolt://<neo4j-host>:7687
export NEO4J_USERNAME=neo4j
export NEO4J_PASSWORD_SECRET_ARN=arn:aws:secretsmanager:us-west-2:<acct-id>:secret:<neo4j-password-secret>

export DD_ENV=prod
export DD_SITE=datadoghq.com
export DD_SERVICE=circuit-backend
export BEDROCK_MODEL_ID=nvidia.nemotron-nano-12b-v2

# Optional:
# export DIGIKEY_CLIENT_ID_SECRET_ARN=...
# export DIGIKEY_CLIENT_SECRET_ARN=...
# export MINIMAX_API_KEY_SECRET_ARN=...
# export ENABLE_MINIMAX_NARRATOR=true
```

Deploy:

```bash
./deploy/deploy_fargate.sh
```

If your ECS service does not exist yet, create it once (replace placeholders):

```bash
aws --profile "$AWS_PROFILE" --region "$AWS_REGION" ecs create-service \
  --cluster "$ECS_CLUSTER" \
  --service-name "$ECS_SERVICE" \
  --task-definition "$ECS_TASK_FAMILY" \
  --desired-count 1 \
  --launch-type FARGATE \
  --platform-version LATEST \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-aaa,subnet-bbb],securityGroups=[sg-aaa],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...:targetgroup/...,containerName=backend,containerPort=8080"
```

## Smoke test after deploy

```bash
./deploy/smoke_test.sh https://<your-alb-dns-name>
```

If you have an image file to test `/extract`:

```bash
./deploy/smoke_test.sh https://<your-alb-dns-name> /path/to/schematic.png
```

## Datadog verification checklist

In Datadog APM, filter by:

- `service:circuit-backend`
- `env:prod` (or your `DD_ENV`)

Confirm traces contain:

- `bedrock.extract_bom`
- `neo4j.find_substitutes`
- `supplier.digikey.token`
- `supplier.digikey.keyword_search`
- `supplier.digikey.pricing_by_quantity`
- `minimax.narrate` (only when narrator is enabled)

Every API response should include `x-trace-id` and `X-Request-ID`.
