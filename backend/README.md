# Backend (FastAPI)

Python FastAPI scaffold for the circuit hackathon backend.

## Requirements

- Python 3.11+
- pip

## Local setup

1. Create and activate a virtual environment:

   ```bash
   cd backend
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Create local environment file:

   ```bash
   cp .env.example .env
   ```

4. Run the API:

   ```bash
   uvicorn app.main:app --reload
   ```

## Environment variables

- `APP_NAME`: API title shown in docs.
- `APP_ENV`: `local` or `production` (`local` loads `.env` via `python-dotenv`).
- `LOG_LEVEL`: Logging level (`INFO`, `DEBUG`, etc.).
- `AWS_REGION`: Default AWS region.
- `BEDROCK_MODEL_ID`: Bedrock model ID for BOM extraction (`nvidia.nemotron-nano-12b-v2` by default).
- `BOM_EXTRACTION_PROMPT`: Optional prompt override for `/extract` BOM parsing.
- `NEO4J_URI`: Neo4j connection URI.
- `NEO4J_USERNAME`: Neo4j username.
- `NEO4J_PASSWORD`: Neo4j password.
  Use a non-default password (Neo4j rejects `neo4j` as the password).
- `DIGIKEY_CLIENT_ID`: Digi-Key OAuth client id.
- `DIGIKEY_CLIENT_SECRET`: Digi-Key OAuth client secret.
- `DIGIKEY_ACCOUNT_ID`: Optional Digi-Key account id for account pricing contexts (`""` or `0` omits header).
- `DIGIKEY_USE_SANDBOX`: `true` uses `sandbox-api.digikey.com`; `false` uses production host.
- `DIGIKEY_LOCALE_SITE`: Digi-Key locale site (default `US`).
- `DIGIKEY_LOCALE_LANGUAGE`: Digi-Key locale language (default `en`).
- `DIGIKEY_LOCALE_CURRENCY`: Digi-Key locale currency (default `USD`).
- `DIGIKEY_HTTP_TIMEOUT_S`: Digi-Key HTTP timeout in seconds.
- `MINIMAX_API_KEY`: MiniMax API key (required when narrator is enabled).
- `MINIMAX_BASE_URL`: MiniMax API base URL (`https://api.minimax.io`).
- `MINIMAX_MODEL`: MiniMax model name (default `MiniMax-M2.5-highspeed`).
- `ENABLE_MINIMAX_NARRATOR`: Enable incident narrator endpoint (`true`/`false`).
- `DD_SERVICE`: Datadog service name.
- `DD_ENV`: Datadog environment.
- `DD_VERSION`: Datadog version tag.
- `DD_AGENT_HOST`: Datadog agent hostname.
- `DD_TRACE_ENABLED`: Enable Datadog tracing (`true`/`false`).
- `DD_LOGS_INJECTION`: Enable Datadog log injection (`true`/`false`).

## Endpoints

- `GET /health` -> `{ "status": "ok" }`
- `GET /ready` -> `200` when Neo4j is reachable, else `503`
- `POST /extract` (multipart file field: `image`) -> `ExtractResponse`
- `POST /graph/seed` seeds demo `Part` and `SUBSTITUTES_FOR` data in Neo4j
- `POST /graph/substitutes` -> `SubstituteResponse`
- `POST /graph/chaos/toggle` (flips in-memory chaos flag)
- `POST /incident/narrate` -> `NarrateResponse` (MiniMax-backed, requires enable flag + API key)
- `POST /quote/digikey` -> `QuoteResponse` (Digi-Key supplier offers and chosen line pricing)

When chaos mode is enabled, substitute lookups add a 1.5s artificial delay and
`SubstituteResponse.warnings` includes a chaos warning.

All responses include `x-trace-id` and `X-Request-ID` headers.

## MiniMax Narrator

MiniMax narrator is optional and calls:

- `POST {MINIMAX_BASE_URL}/v1/text/chatcompletion_v2`

Local enablement:

1. Set in `.env`:
   - `ENABLE_MINIMAX_NARRATOR=true`
   - `MINIMAX_API_KEY=<your_key>`
2. Restart backend.
3. Call `POST /incident/narrate`.

ECS enablement:

1. Set `ENABLE_MINIMAX_NARRATOR=true` in task env vars.
2. Inject `MINIMAX_API_KEY` via Secrets Manager/SSM secret.
3. Optionally set `MINIMAX_BASE_URL` and `MINIMAX_MODEL`.

If narrator is disabled, endpoint returns `400 Narrator disabled`.
When enabled, Datadog traces include span `minimax.narrate` with tags:
`narrator.model`, `chaos_mode`, and `endpoint`.

## Digi-Key Integration

Digi-Key Product Information v4 integration uses OAuth `client_credentials` and
calls Product Search + PricingByQuantity endpoints.

Required variables:

- `DIGIKEY_CLIENT_ID`
- `DIGIKEY_CLIENT_SECRET`

Optional variables:

- `DIGIKEY_ACCOUNT_ID` (`""` or `0` means header is not sent)
- `DIGIKEY_USE_SANDBOX`
- `DIGIKEY_LOCALE_SITE`
- `DIGIKEY_LOCALE_LANGUAGE`
- `DIGIKEY_LOCALE_CURRENCY`
- `DIGIKEY_HTTP_TIMEOUT_S`

Sandbox vs production host:

- `DIGIKEY_USE_SANDBOX=true` -> `sandbox-api.digikey.com`
- `DIGIKEY_USE_SANDBOX=false` -> `api.digikey.com`

Example quote request:

```bash
curl -X POST http://127.0.0.1:8000/quote/digikey \
  -H 'Content-Type: application/json' \
  -d '{
    "bom": [
      {"type":"regulator","value":"LM7805","qty":1}
    ],
    "prefer_in_stock": true,
    "exclude_marketplace": true
  }'
```

## Docker

Build and run with Docker Compose:

```bash
cd backend
docker compose up --build
```

Run backend container directly:

```bash
cd backend
docker build -t circuit-backend .
docker run --rm -p 8080:8080 circuit-backend
```

## AWS Fargate + Datadog

Production deployment assets are in `backend/deploy/`:

- `backend/deploy/deploy_fargate.sh`: build/push/register task-def/update service.
- `backend/deploy/ecs-taskdef.fargate.datadog.tpl.json`: task-def template (app + Datadog sidecar).
- `backend/deploy/smoke_test.sh`: post-deploy endpoint checks.
- `backend/deploy/README.md`: exact environment variables and command flow.
