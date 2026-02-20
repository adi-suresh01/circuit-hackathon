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
- `NEO4J_URI`: Neo4j connection URI.
- `NEO4J_USERNAME`: Neo4j username.
- `NEO4J_PASSWORD`: Neo4j password.
- `DDTRACE_ENABLED`: Enable Datadog tracing flag (`true`/`false`).

## Endpoints

- `GET /health` -> `{ "status": "ok" }`
- `POST /extract` (multipart file field: `image`) -> `ExtractResponse`
- `POST /graph/seed` seeds demo `Part` and `SUBSTITUTES_FOR` data in Neo4j
- `POST /graph/substitutes` -> `SubstituteResponse`
- `POST /graph/chaos/toggle` (flips in-memory chaos flag)

When chaos mode is enabled, substitute lookups add a 1.5s artificial delay and
`SubstituteResponse.warnings` includes a chaos warning.

## Docker

Build and run with Docker Compose:

```bash
cd backend
docker compose up --build
```
