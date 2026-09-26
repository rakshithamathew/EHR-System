# Multi-source EHR Patient Dashboard

A small full-stack dashboard that synchronizes sandbox FHIR R4 data from HAPI
FHIR, Oracle Health, and Epic into PostgreSQL. Users can switch providers,
search a paginated patient directory, run an on-demand sync, and inspect each
patient's demographics, conditions, and medications.

The frontend uses React, TypeScript, Vite, TanStack Query, and Tailwind CSS. The
backend uses FastAPI, SQLAlchemy, Alembic, and PostgreSQL.

## Architecture

```text
                         +--> HAPI FHIR R4 (public)
React/Vite <--> FastAPI -+--> Oracle Health R4 (public)
                 |       +--> Epic R4 (SMART OAuth + PKCE)
                 |
                 +<--> PostgreSQL
                       patients / conditions / medications / sync_runs
```

Routes contain HTTP concerns, the sync service orchestrates each run, provider
connectors own FHIR HTTP/pagination/retry behavior, and repositories own SQL and
`ON CONFLICT DO UPDATE` upserts. Resources use source-scoped unique identities,
so repeated syncs update rows instead of creating duplicates.

## EHR authentication

| Source | Auth | Login Required? | Notes |
| --- | --- | --- | --- |
| HAPI | None | No | Public sandbox |
| Oracle | None | No | Public open sandbox |
| Epic | OAuth 2.0 + PKCE | Yes (sandbox user) | SMART on FHIR |

### Epic SMART on FHIR flow

1. `GET /api/epic/login` generates state and a PKCE verifier/challenge, stores the pending authorization server-side, and redirects to Epic.
2. The user signs in to the MyChart sandbox using `fhircamila` / `epicepic1`.
3. Epic redirects to the registered frontend callback (`/callback`) with the
   authorization code and state.
4. The frontend forwards the callback query to `/api/epic/callback`; FastAPI validates state and exchanges the code at Epic's token endpoint.
5. The access token and expiry are stored in the sandbox session and used as a Bearer token for Epic FHIR calls.

Epic requires `aud` to exactly equal the FHIR base URL. Omitting it returns
Epic `error=4`. The redirect URI must also match the URI registered in the Epic
developer portal byte-for-byte.

## Local setup

Requirements: PostgreSQL 18, Python 3.12+, and Node.js 20+.

Create `backend/.env` from `.env.example` and configure:

```ini
DATABASE_URL=postgresql+psycopg://postgres:root@localhost:5432/ehr_dashboard
FRONTEND_URL=http://localhost:5173
HAPI_FHIR_BASE_URL=https://hapi.fhir.org/baseR4
ORACLE_FHIR_BASE_URL=https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d
EPIC_FHIR_BASE_URL=https://fhir.epic.com/interconnect-fhir-oauth/api/FHIR/R4
EPIC_CLIENT_ID=4abffc6a-407b-4a22-848d-41e66c093da3
EPIC_REDIRECT_URI=http://localhost:5173/callback
EPIC_AUTHORIZATION_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/authorize
EPIC_TOKEN_URL=https://fhir.epic.com/interconnect-fhir-oauth/oauth2/token
```

The deployed Render service uses
`EPIC_REDIRECT_URI=https://ehr-system-tau.vercel.app/callback`. Both the local
and deployed callback URIs must be registered on the Epic non-production app.
The Epic app must enable the R4 `Patient.Read (Demographics)`,
`Condition.Search (Problems)`, and
`MedicationRequest.Search (Signed Medication Order)` incoming APIs. The SMART
request uses `openid`, `fhirUser`, and patient-level read scopes for those
three resource types.

Start the backend:

```bash
cd backend
python -m venv .venv
source .venv/Scripts/activate
python -m pip install -r requirements-dev.txt
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

Start the frontend in a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Create `frontend/.env` containing
`VITE_API_BASE_URL=http://localhost:8000`, then visit
[http://localhost:5173](http://localhost:5173).

## Synchronization

```bash
curl -X POST "http://localhost:8000/api/sync?source=hapi"
curl -X POST "http://localhost:8000/api/sync?source=oracle"
curl -X POST "http://localhost:8000/api/sync?source=epic" --cookie "epic_session=..."
```

Epic must first be connected in the browser through `/api/epic/login`. Bundle
pagination follows provider-supplied `link[relation=next]` URLs. Temporary
transport errors, HTTP 429, and HTTP 5xx responses use bounded exponential
backoff, and `Retry-After` is honored. Connectors allow at most five requests
per second.

Run the focused tests and live HAPI idempotency check:

```bash
cd backend
pytest -q
cd ..
python scripts/test_idempotency.py
```

The script runs HAPI sync twice and asserts that source-filtered patient,
condition, and medication table counts remain identical.

## Known limitations

- Epic requires interactive MyChart login; no unauthenticated Epic patient endpoint exists.
- Epic app 61371 is configured for sandbox testing with the required R4
  Patient, Condition, and MedicationRequest APIs and both deployed and local
  callback URIs. Epic authentication remains interactive and depends on the
  availability of Epic's shared MyChart sandbox.
- Each callback URI must match an Endpoint URI registered in Epic byte-for-byte.
- The lightweight Epic token store is process-local and intended for this sandbox demo, not multi-instance production deployment.
- Sync is on demand and runs inline with the API request.
- There is no scheduler, queue, or background worker.
- Public sandboxes can be slow, rate-limited, reset, or temporarily unavailable.
