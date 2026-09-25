"""Run the HAPI sync twice and verify that database row counts do not grow.

Run from the project root with the backend virtual environment active:
    python scripts/test_idempotency.py
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import NamedTuple

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SourceCounts(NamedTuple):
    patients: int
    conditions: int
    medications: int


def read_source_counts(database_url: str, source: str) -> SourceCounts:
    engine = create_engine(database_url)
    queries = {
        "patients": """
            SELECT count(*)
            FROM patients AS record
            JOIN ehr_sources AS source ON source.id = record.ehr_source_id
            WHERE source.code = :source_code
        """,
        "conditions": """
            SELECT count(*)
            FROM conditions AS record
            JOIN ehr_sources AS source ON source.id = record.ehr_source_id
            WHERE source.code = :source_code
        """,
        "medications": """
            SELECT count(*)
            FROM medications AS record
            JOIN ehr_sources AS source ON source.id = record.ehr_source_id
            WHERE source.code = :source_code
        """,
    }
    try:
        with engine.connect() as connection:
            values = {
                name: int(
                    connection.execute(
                        text(query),
                        {"source_code": source},
                    ).scalar_one()
                )
                for name, query in queries.items()
            }
    finally:
        engine.dispose()

    return SourceCounts(**values)


def run_sync(api_base_url: str, source: str, timeout: float) -> dict[str, int]:
    response = requests.post(
        f"{api_base_url.rstrip('/')}/api/sync",
        params={"source": source},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    print(
        "Sync completed: "
        f"patients={payload['patients']} "
        f"conditions={payload['conditions']} "
        f"medications={payload['medications']}"
    )
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that repeated source synchronization is idempotent."
    )
    parser.add_argument("--source", default="hapi", choices=("hapi", "oracle"))
    parser.add_argument("--api-base-url", default="http://localhost:8000")
    parser.add_argument(
        "--timeout",
        type=float,
        default=1800,
        help="Timeout in seconds for each inline sync request.",
    )
    args = parser.parse_args()

    load_dotenv(PROJECT_ROOT / "backend" / ".env")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is required in backend/.env or the environment")

    print(f"Running first {args.source} synchronization...")
    run_sync(args.api_base_url, args.source, args.timeout)
    first_counts = read_source_counts(database_url, args.source)
    print(f"Counts after first sync: {first_counts}")

    print(f"Running second {args.source} synchronization...")
    run_sync(args.api_base_url, args.source, args.timeout)
    second_counts = read_source_counts(database_url, args.source)
    print(f"Counts after second sync: {second_counts}")

    assert first_counts.patients == second_counts.patients, (
        "Patient count changed between identical syncs: "
        f"{first_counts.patients} != {second_counts.patients}"
    )
    assert first_counts.conditions == second_counts.conditions, (
        "Condition count changed between identical syncs: "
        f"{first_counts.conditions} != {second_counts.conditions}"
    )
    assert first_counts.medications == second_counts.medications, (
        "Medication count changed between identical syncs: "
        f"{first_counts.medications} != {second_counts.medications}"
    )
    print("PASS: repeated synchronization did not create duplicate rows.")


if __name__ == "__main__":
    main()
