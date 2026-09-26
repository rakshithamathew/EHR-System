# EHR Patient Dashboard

This is a small full-stack app I built to bring patient data from multiple EHR
sandboxes into one dashboard. You can switch between EHRs, search and paginate
the patient list, run a fresh sync, and open a patient to see their conditions
and medications.

- **Live app:** [ehr-system-tau.vercel.app](https://ehr-system-tau.vercel.app)
- **Repository:** [github.com/rakshithamathew/EHR-System](https://github.com/rakshithamathew/EHR-System)

## How it works

```text
React/Vercel -> FastAPI/Render -> HAPI, Oracle, or Epic FHIR
                           `-> PostgreSQL
```

The frontend is React and TypeScript. The backend is FastAPI, and PostgreSQL
stores everything pulled from the EHR APIs.

### HAPI FHIR

HAPI provides a public FHIR R4 server, so no login is required. The sync first
loads patients, then requests `Condition` and `MedicationRequest` resources for
each patient.

### Oracle Health/Cerner

Oracle also provides an open FHIR R4 sandbox. I use its shared SMART patient
cohort and retrieve the same patient, condition, and medication resources.

### Epic

Epic uses SMART on FHIR rather than an open API. I implemented its OAuth
authorization-code flow with PKCE. The backend validates the OAuth state,
exchanges the authorization code, keeps the short-lived token server-side, and
uses it as a Bearer token for FHIR requests.

For every provider, the sync follows the server's FHIR Bundle `next` links. It
limits requests to five per second, retries temporary failures and rate limits,
and respects the `Retry-After` header.

## How the data is stored

PostgreSQL has five main tables: `ehr_sources`, `patients`, `conditions`,
`medications`, and `sync_runs`. I store both the fields needed by the dashboard
and the complete original FHIR resource as JSON.

Records are identified by their EHR source and FHIR ID. PostgreSQL upserts and
a unique constraint on `(ehr_source_id, external_id)` mean that running the
same sync twice updates existing patients instead of creating duplicates.

## Run it locally

You will need Python 3.12+, Node.js 20+, and PostgreSQL.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
copy .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm install
# Create .env with VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Run the backend tests with:

```bash
cd backend
pytest -q
```

To verify that repeated syncing does not create duplicate patients:

```bash
python scripts/test_idempotency.py --source hapi
```

## What I would change for a real hospital

For a hospital with 25,000 patients, I would move synchronization into
background jobs instead of keeping an HTTP request open. I would also use
incremental updates or FHIR Bulk Data where supported, batch database writes,
and add resumable checkpoints so a failed sync can continue where it stopped.

Authentication tokens would move to an encrypted shared store with refresh-token
support. A production system would also need monitoring, audit logs, role-based
access, consent controls, stricter validation, terminology mapping, and
HIPAA-compliant infrastructure.

One final note: these are shared public sandboxes, so records and totals can
change between syncs. Epic also depends on an interactive sandbox login and an
exactly registered callback URL.
