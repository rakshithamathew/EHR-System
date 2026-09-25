"""Small reusable client for the public HAPI FHIR R4 server."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import requests


FHIRResource = dict[str, Any]


class HapiFhirClient:
    """Fetch and display Patient and Observation resources from a FHIR server."""

    def __init__(
        self,
        base_url: str = "https://hapi.fhir.org/baseR4",
        *,
        timeout: float = 30.0,
    ) -> None:
        if not base_url.strip():
            raise ValueError("base_url must not be empty")
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/fhir+json"}

    def build_url(
        self,
        path: str,
        params: dict[str, str | int] | None = None,
    ) -> str:
        """Build an absolute FHIR URL and safely encode optional query values."""

        url = path if path.startswith(("http://", "https://")) else (
            f"{self.base_url}/{path.lstrip('/')}"
        )
        if not params:
            return url

        prepared = requests.Request("GET", url, params=params).prepare()
        if prepared.url is None:
            raise ValueError("Could not build the FHIR request URL")
        return prepared.url

    def _get_json(
        self,
        url: str,
        *,
        params: dict[str, str | int] | None = None,
    ) -> FHIRResource | None:
        """Perform one JSON FHIR request and report failures clearly."""

        request_url = self.build_url(url)
        try:
            response = requests.get(
                request_url,
                params=params,
                headers=self.headers,
                timeout=self.timeout,
            )
        except requests.RequestException as exc:
            print(f"FHIR request failed for {request_url}: {exc}")
            return None

        if response.status_code != 200:
            detail = response.text.strip().replace("\n", " ")[:300]
            suffix = f" Response: {detail}" if detail else ""
            print(
                f"FHIR request failed with HTTP {response.status_code} "
                f"for {response.url}.{suffix}"
            )
            return None

        try:
            payload = response.json()
        except ValueError:
            print(f"FHIR server returned invalid JSON for {response.url}")
            return None

        if not isinstance(payload, dict):
            print(f"FHIR server returned an unexpected payload for {response.url}")
            return None
        return payload

    @staticmethod
    def _bundle_resources(bundle: FHIRResource) -> list[FHIRResource]:
        entries = bundle.get("entry")
        if not isinstance(entries, list):
            return []

        resources: list[FHIRResource] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            resource = entry.get("resource")
            if isinstance(resource, dict):
                resources.append(resource)
        return resources

    @staticmethod
    def _next_link(bundle: FHIRResource) -> str | None:
        links = bundle.get("link")
        if not isinstance(links, list):
            return None

        for link in links:
            if not isinstance(link, dict) or link.get("relation") != "next":
                continue
            url = link.get("url")
            if isinstance(url, str) and url.strip():
                return url.strip()
        return None

    @staticmethod
    def _patient_name(patient: FHIRResource) -> str:
        names = patient.get("name")
        if not isinstance(names, list) or not names or not isinstance(names[0], dict):
            return "Unknown"

        name = names[0]
        text = name.get("text")
        if isinstance(text, str) and text.strip():
            return text.strip()

        given = name.get("given")
        given_names = (
            [value.strip() for value in given if isinstance(value, str) and value.strip()]
            if isinstance(given, list)
            else []
        )
        family = name.get("family")
        if isinstance(family, str) and family.strip():
            given_names.append(family.strip())
        return " ".join(given_names) or "Unknown"

    @staticmethod
    def _observation_display(observation: FHIRResource) -> str:
        code = observation.get("code")
        if not isinstance(code, dict):
            return "Unknown observation"

        codings = code.get("coding")
        if isinstance(codings, list):
            for coding in codings:
                if not isinstance(coding, dict):
                    continue
                display = coding.get("display")
                if isinstance(display, str) and display.strip():
                    return display.strip()

        text = code.get("text")
        return text.strip() if isinstance(text, str) and text.strip() else "Unknown observation"

    def get_patient(self, patient_id: str) -> FHIRResource | None:
        """Fetch one Patient by logical ID and print basic demographics."""

        normalized_id = patient_id.strip()
        if not normalized_id:
            print("Patient ID must not be empty")
            return None

        patient = self._get_json(f"Patient/{normalized_id}")
        if patient is None:
            return None
        if patient.get("resourceType") != "Patient":
            print(f"FHIR response for Patient/{normalized_id} was not a Patient")
            return None

        print(f"Name: {self._patient_name(patient)}")
        print(f"DOB: {patient.get('birthDate') or 'Unknown'}")
        print(f"Gender: {patient.get('gender') or 'Unknown'}")
        return patient

    def search_patients(self, count: int = 5) -> list[FHIRResource]:
        """Fetch one Patient search page and print each matching patient."""

        if count < 1:
            raise ValueError("count must be at least 1")

        bundle = self._get_json("Patient", params={"_count": count})
        if bundle is None:
            return []

        patients = self._bundle_resources(bundle)
        if not patients:
            print("No patients found")
            return []

        for patient in patients:
            print(
                f"ID: {patient.get('id') or 'Unknown'} | "
                f"Name: {self._patient_name(patient)} | "
                f"Gender: {patient.get('gender') or 'Unknown'}"
            )
        return patients

    def get_observations(
        self,
        patient_id: str,
        count: int = 25,
    ) -> list[FHIRResource]:
        """Fetch one Observation search page for a patient and print its codes."""

        normalized_id = patient_id.strip()
        if not normalized_id:
            print("Patient ID must not be empty")
            return []
        if count < 1:
            raise ValueError("count must be at least 1")

        bundle = self._get_json(
            "Observation",
            params={"patient": normalized_id, "_count": count},
        )
        if bundle is None:
            return []

        observations = self._bundle_resources(bundle)
        if not observations:
            print(f"No observations found for patient {normalized_id}")
            return []

        for observation in observations:
            print(self._observation_display(observation))
        return observations

    def fetch_all_pages(
        self,
        url: str,
        *,
        max_pages: int | None = None,
    ) -> list[FHIRResource]:
        """Follow Bundle next links and combine resources from every visited page."""

        if max_pages is not None and max_pages < 1:
            raise ValueError("max_pages must be at least 1")

        resources: list[FHIRResource] = []
        current_url: str | None = self.build_url(url)
        visited_urls: set[str] = set()
        pages_fetched = 0

        while current_url is not None:
            if current_url in visited_urls:
                print(f"Pagination stopped because the next link repeated: {current_url}")
                break
            if max_pages is not None and pages_fetched >= max_pages:
                print(f"Pagination safety cap reached after {max_pages} pages")
                break

            visited_urls.add(current_url)
            bundle = self._get_json(current_url)
            if bundle is None:
                break

            resources.extend(self._bundle_resources(bundle))
            pages_fetched += 1

            next_url = self._next_link(bundle)
            current_url = urljoin(current_url, next_url) if next_url else None

        return resources


def main() -> None:
    client = HapiFhirClient()

    print("\nFetching the known synthetic Patient/4237 resource")
    client.get_patient("4237")

    print("\nSearching for 5 patients")
    patients = client.search_patients(count=5)

    if patients:
        first_patient_id = patients[0].get("id")
        if isinstance(first_patient_id, str) and first_patient_id:
            print(f"\nFetching Patient/{first_patient_id}")
            client.get_patient(first_patient_id)

            print(f"\nFetching observations for Patient/{first_patient_id}")
            client.get_observations(first_patient_id, count=25)
    else:
        print("Skipping patient and observation requests because search returned no patients")

    print("\nFetching paginated patients (maximum 5 pages)")
    patient_search_url = client.build_url("Patient", {"_count": 20})
    all_patients = client.fetch_all_pages(patient_search_url, max_pages=5)
    print(f"Fetched {len(all_patients)} patient resources across up to 5 pages")


if __name__ == "__main__":
    main()
