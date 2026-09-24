# EHR Dashboard Backend

FastAPI backend for synchronizing a small set of public FHIR R4 resources into PostgreSQL. Synchronization runs within the API request intentionally; this take-home project does not use queues or background workers.

## Requirements

- Python 3.12 or newer
- PostgreSQL

## Environment

Copy `.env.example` to `.env` and provide values for the environment you are running:

```env
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/ehr_dashboard
FRONTEND_URL=http://localhost:5173

HAPI_FHIR_BASE_URL=https://your-hapi-r4-base-url
ORACLE_FHIR_BASE_URL=https://your-oracle-r4-base-url

EPIC_FHIR_BASE_URL=
EPIC_CLIENT_ID=
EPIC_REDIRECT_URI=
EPIC_AUTHORIZATION_URL=
EPIC_TOKEN_URL=
```

Epic values remain optional until SMART on FHIR OAuth support is implemented. Do not commit `.env` or production credentials.

## Local development

Create and activate a virtual environment, then install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
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

## Vercel deployment

Create a Vercel project with this `backend` directory as its root. Add every production environment variable in the Vercel project settings, using a hosted PostgreSQL connection string for `DATABASE_URL`.

The `app` object exported by `app/main.py` is the deployment entrypoint. The minimal `vercel.json` selects Vercel's FastAPI framework; no build command, route rewrite, Dockerfile, or custom server command is required.

For a local Vercel-runtime check, install the Vercel CLI and run:

```bash
vercel dev
```
