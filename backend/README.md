# EHR Dashboard Backend

FastAPI backend for synchronizing a small set of public FHIR R4 resources into PostgreSQL. Synchronization runs within the API request intentionally; this take-home project does not use queues or background workers.

## Requirements

- Python 3.12 or newer
- PostgreSQL

## Environment

Copy `.env.example` to `.env` and provide values for the environment you are running:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5433/ehr_dashboard
FRONTEND_URL=http://localhost:5173

HAPI_FHIR_BASE_URL=https://your-hapi-r4-base-url
ORACLE_FHIR_BASE_URL=https://your-oracle-r4-base-url

EPIC_FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_CLIENT_ID=3f340b6c-8ca4-46b0-a50a-55a7cbf60324
EPIC_REDIRECT_URI=http://localhost:5173/callback
EPIC_AUTHORIZATION_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize
EPIC_TOKEN_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
```

Register `http://localhost:5173/callback` for local development and
`https://ehr-system-tau.vercel.app/callback` for the deployed frontend on the
Epic non-production client. Configure `EPIC_REDIRECT_URI` with the exact URI
used by that environment. The frontend callback immediately forwards Epic's
authorization response to the backend token-exchange route. Select **Epic** and choose
**Connect Epic** to begin the standalone SMART authorization-code flow. The
backend validates OAuth `state`, uses PKCE with `S256`, exchanges the code, and
keeps the access token out of frontend JavaScript in a short-lived process-local
session. Restarting the backend requires reconnecting Epic. Do not commit `.env`
or production credentials.

## Local development

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

On Windows PowerShell, activate it with:

```powershell
.venv\Scripts\Activate.ps1
```

Apply database migrations:

```bash
alembic upgrade head
```

Start the development server:

```bash
uvicorn app.main:app --reload
```

Application startup idempotently inserts or updates the `hapi`, `oracle`, and `epic` source records from the configured base URLs. To run the same seed explicitly:

```bash
python -m app.core.seed
```

The local API is available at `http://localhost:8000`, with OpenAPI documentation at `http://localhost:8000/docs`.

## HAPI and Oracle synchronization

Apply migrations before the first sync, then use these endpoints:

```text
GET  /api/sources
POST /api/sync?source=hapi
POST /api/sync?source=oracle
GET  /api/patients?source=hapi&page=1&limit=20
GET  /api/patients/{database_patient_id}
```

Synchronization follows provider-supplied FHIR Bundle `next` links and upserts
patients, conditions, and medication requests into PostgreSQL. Public sandbox
syncs run in the request and can take several minutes. Patient list and detail
requests read PostgreSQL and therefore do not wait on either sandbox.

## Tests

Run the focused backend test suite with:

```bash
pytest
```

The pagination and retry tests run without external services. The two repository tests require PostgreSQL through `TEST_DATABASE_URL` (or `DATABASE_URL`) and use a transaction-scoped temporary schema that is removed after each test.

## Render deployment

Create a Render web service with `backend` as its root directory. Add every
production environment variable in the Render service settings, using a hosted
PostgreSQL connection string for `DATABASE_URL`.

Use these commands and health-check path:

```text
Build: pip install -r requirements.txt
Start: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
Health check: /api/health
```
