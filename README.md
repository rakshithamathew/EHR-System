# EHR Patient Dashboard

This is a small full-stack app I built to bring patient data from multiple EHR
sandboxes into one dashboard. You can switch between EHRs, search and paginate
the patient list, run a fresh sync, and open a patient to see their conditions
and medications.

- **Live app:** [ehr-system-tau.vercel.app](https://ehr-system-tau.vercel.app)
- **Repository:** [github.com/rakshithamathew/EHR-System](https://github.com/rakshithamathew/EHR-System)

## How it works

```text
React/Vercel -> FastAPI/Render -> HAPI, Oracle, or Epic FHIR`-> PostgreSQL
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

## System Design for a Real Hospital (25,000 Patients)

At this scale, I would avoid premature microservices. A modular API, separate
sync workers, a managed queue, and PostgreSQL provide enough scale while keeping
the system easier to operate and audit.

```text
Clinician -> SSO/MFA -> API -> PostgreSQL
                         ^
EHRs -> Queue -> FHIR workers -> validation + patient matching
                         |
                         +-> encrypted raw FHIR archive + audit log
```

- **Reliable ingestion:** use `_since`, FHIR history, or Bulk Data where
  available, plus a nightly reconciliation. Jobs are batched, idempotent,
  checkpointed, retried with backoff, and moved to a dead-letter queue after
  repeated failures.
- **Clinical correctness:** preserve source, version, and timestamps; show data
  freshness and incomplete-sync warnings. Use a Master Patient Index with human
  review for uncertain matches—merging the wrong patients is more dangerous
  than temporarily keeping duplicates.
- **Balanced storage:** keep searchable fields in PostgreSQL and the original
  encrypted FHIR payload for traceability. Add read replicas only when measured
  load requires them, and avoid caching PHI without a clear need.
- **Database scaling:** 25,000 patients do not require sharding. Start with a
  managed PostgreSQL primary, vertical scaling, connection pooling, good indexes,
  and batch writes. Add read replicas for dashboard traffic and partition large
  clinical/audit tables by date only when measurements justify it.
- **Field management:** keep frequently queried FHIR fields normalized and
  indexed, retain raw JSONB for traceability, and record source, version, and
  timestamps. Encrypt sensitive fields, validate schema changes through
  migrations, and apply retention rules instead of keeping PHI forever.
- **Gateway and rate limits:** place an API gateway and WAF in front of the API
  for authentication, request limits, payload limits, and audit correlation.
  Apply per-user inbound limits and separate token-bucket limits per EHR vendor
  so one integration cannot exhaust another vendor's quota.
- **Application scaling:** scale the database vertically first, but keep API and
  worker processes stateless so they can scale horizontally behind a health-aware
  load balancer. The queue distributes sync work and provides backpressure when
  an EHR slows down.
<!-- - **Network security:** use TLS 1.2+ externally, private subnets for databases and
  workers, strict security groups, private endpoints or VPN links to hospital
  networks, and mTLS for sensitive service-to-service traffic. Secrets stay in a
  managed vault and neither databases nor internal services are public. -->
- **HIPAA safeguards:** use vendors that sign BAAs, encrypt data in transit and
  at rest, enforce least-privilege RBAC, MFA, consent rules, access reviews,
  immutable audit logs, backups, retention policies, and tested incident and
  disaster-recovery plans. Never put PHI in logs or non-production systems;
  use de-identified test data.
- **Key tradeoff:** synchronization is eventually consistent but resilient. The
  dashboard shows provenance and freshness and is not treated as the clinical
  system of record.

One final note: these are shared public sandboxes, so records and totals can
change between syncs. Epic also depends on an interactive sandbox login and an
exactly registered callback URL.
