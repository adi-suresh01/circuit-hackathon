# CDK Deployment (Python)

This CDK app provisions:

- ECR repository for backend images.
- ECS Fargate service behind an internet-facing ALB.
- Task definition with container `api` on port `8080`.
- Runtime env vars for Datadog + Bedrock + Neo4j URI.
- Secrets Manager injection for `NEO4J_USERNAME` and `NEO4J_PASSWORD`.
- Optional Datadog agent sidecar with `DD_API_KEY` secret.
- IAM task role permissions for Bedrock runtime, logs stream writes, and Secrets Manager reads.

## Prerequisites

- AWS CLI configured (`AWS_PROFILE`, `AWS_REGION`).
- Node.js + npm (for CDK CLI).
- Python 3.11+.
- IAM role/user permissions to create VPC/ALB/ECS/ECR/IAM/Logs/SecretsManager resources.

Install CDK CLI once:

```bash
npm install -g aws-cdk
```

## 1) Setup

```bash
cd infra/cdk
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

This app is configured with `BootstraplessSynthesizer`, so `cdk bootstrap` is not required.

## 2) Create required secrets

Use existing secret ARNs or create new ones:

```bash
NEO4J_USERNAME_SECRET_ARN=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" secretsmanager create-secret \
  --name circuit/neo4j/username \
  --secret-string "neo4j" \
  --query ARN --output text)

NEO4J_PASSWORD_SECRET_ARN=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" secretsmanager create-secret \
  --name circuit/neo4j/password \
  --secret-string "your-strong-neo4j-password" \
  --query ARN --output text)
```

Optional (Datadog agent):

```bash
DD_API_KEY_SECRET_ARN=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" secretsmanager create-secret \
  --name circuit/datadog/api_key \
  --secret-string "YOUR_DATADOG_API_KEY" \
  --query ARN --output text)
```

## 3) Synthesize

```bash
cdk synth \
  --profile "$AWS_PROFILE" \
  -c desiredCount=0 \
  -c ddEnv=prod \
  -c ddService=circuit-backend \
  -c ecrRepoName=circuit-backend \
  -c imageTag=latest \
  -c enableDatadogAgent=true \
  -c ddApiKeySecretArn="$DD_API_KEY_SECRET_ARN" \
  --parameters Neo4jUri=bolt://<neo4j-host>:7687 \
  --parameters Neo4jUsernameSecretArn="$NEO4J_USERNAME_SECRET_ARN" \
  --parameters Neo4jPasswordSecretArn="$NEO4J_PASSWORD_SECRET_ARN" \
  --parameters BedrockModelId=nvidia.nemotron-nano-12b-v2
```

If you are not running a Datadog agent sidecar yet, set `-c enableDatadogAgent=false` and omit `-c ddApiKeySecretArn=...`.

## 4) Deploy

```bash
cdk deploy \
  --profile "$AWS_PROFILE" \
  -c desiredCount=0 \
  -c ddEnv=prod \
  -c ddService=circuit-backend \
  -c ecrRepoName=circuit-backend \
  -c imageTag=latest \
  -c enableDatadogAgent=true \
  -c ddApiKeySecretArn="$DD_API_KEY_SECRET_ARN" \
  --parameters Neo4jUri=bolt://<neo4j-host>:7687 \
  --parameters Neo4jUsernameSecretArn="$NEO4J_USERNAME_SECRET_ARN" \
  --parameters Neo4jPasswordSecretArn="$NEO4J_PASSWORD_SECRET_ARN" \
  --parameters BedrockModelId=nvidia.nemotron-nano-12b-v2
```

This first deploy creates infra with ECS desired count `0` so it does not fail before image push.

## 5) Build + push backend image to ECR

Get outputs:

```bash
STACK_NAME=CircuitBackendStack
REPO_URI=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='EcrRepositoryUri'].OutputValue" \
  --output text)

CLUSTER_NAME=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='EcsClusterName'].OutputValue" \
  --output text)

SERVICE_NAME=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='EcsServiceName'].OutputValue" \
  --output text)
```

Login, build, push:

```bash
aws --profile "$AWS_PROFILE" --region "$AWS_REGION" ecr get-login-password | \
  docker login --username AWS --password-stdin "$(echo "$REPO_URI" | cut -d/ -f1)"

docker build -t "$REPO_URI:latest" ../../backend
docker push "$REPO_URI:latest"
```

Roll ECS service and scale to 1:

```bash
cdk deploy \
  --profile "$AWS_PROFILE" \
  -c desiredCount=1 \
  -c ddEnv=prod \
  -c ddService=circuit-backend \
  -c ecrRepoName=circuit-backend \
  -c imageTag=latest \
  -c enableDatadogAgent=true \
  -c ddApiKeySecretArn="$DD_API_KEY_SECRET_ARN" \
  --parameters Neo4jUri=bolt://<neo4j-host>:7687 \
  --parameters Neo4jUsernameSecretArn="$NEO4J_USERNAME_SECRET_ARN" \
  --parameters Neo4jPasswordSecretArn="$NEO4J_PASSWORD_SECRET_ARN" \
  --parameters BedrockModelId=nvidia.nemotron-nano-12b-v2
```

## 6) Verify ALB health

```bash
ALB_URL=$(aws --profile "$AWS_PROFILE" --region "$AWS_REGION" cloudformation describe-stacks \
  --stack-name "$STACK_NAME" \
  --query "Stacks[0].Outputs[?OutputKey=='AlbUrl'].OutputValue" \
  --output text)

curl -i "$ALB_URL/health"
```

Expected:

```json
{"status":"ok"}
```
