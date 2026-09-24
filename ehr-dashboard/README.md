# EHR/FHIR Dashboard

Minimal full-stack foundation for an EHR/FHIR dashboard. The frontend and backend are intentionally separate. The backend currently exposes only a health endpoint; product UI, EHR APIs, authentication, and business logic remain unimplemented.

## Structure

```text
ehr-dashboard/
|-- frontend/   React, TypeScript, Vite, and Tailwind CSS
|-- backend/    FastAPI, SQLAlchemy, PostgreSQL, and Alembic
|-- README.md
`-- .gitignore
```

## Frontend

Requirements: Node.js 20 or newer and npm.

```bash
cd frontend
cp .env.example .env
npm install
npm run dev
```

The frontend environment exposes `VITE_API_BASE_URL` for the future API base URL.

## Backend

Requirements: Python 3.12 or newer and a PostgreSQL database.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

On Windows PowerShell, activate the virtual environment with `.venv\Scripts\Activate.ps1` and copy environment files with `Copy-Item .env.example .env`.

Set `DATABASE_URL` in `backend/.env` before running Alembic commands. The URL should use SQLAlchemy's psycopg dialect, for example `postgresql+psycopg://user:password@localhost:5432/ehr_dashboard`.

Set `FRONTEND_URL` to the frontend origin allowed by CORS.

Set `HAPI_FHIR_BASE_URL` to the HAPI FHIR R4 endpoint.

Set `ORACLE_FHIR_BASE_URL` to the Oracle Health FHIR R4 endpoint.

Epic settings are included as empty placeholders. Epic resource access remains disabled until SMART on FHIR OAuth authorization is implemented.

```bash
alembic upgrade head
```

The backend health check is available at `GET /api/health`.

## Deployment

The projects are kept independent. The backend includes a minimal `vercel.json`; configure the backend directory as the Vercel project root when deploying it separately. See `backend/README.md` for local and deployment instructions.
