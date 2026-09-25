from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from datetime import date, datetime
from typing import Any, TypedDict
from urllib.parse import urljoin

FHIRResource = dict[str, Any]
FHIRQueryParams = Mapping[str, str | int | float | bool | None]
FHIRPageFetcher = Callable[
    [str, FHIRQueryParams | None],
    Awaitable[FHIRResource],
]


class NormalizedPatient(TypedDict):
    external_id: str | None
    name: str | None
    given_name: str | None
    family_name: str | None
    gender: str | None
    birth_date: date | None
    raw_resource: FHIRResource


class NormalizedCondition(TypedDict):
    external_id: str | None
    clinical_status: str | None
    verification_status: str | None
    code: str | None
    code_system: str | None
    display: str | None
    onset_date: date | None
    raw_resource: FHIRResource


class NormalizedMedicationRequest(TypedDict):
    external_id: str | None
    status: str | None
    medication_code: str | None
    medication_display: str | None
    authored_on: datetime | None
    raw_resource: FHIRResource


class FHIRPage(TypedDict):
    resources: list[FHIRResource]
    has_next: bool


def _as_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None

    stripped = value.strip()
    return stripped or None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, list):
        return {}

    return next((item for item in value if isinstance(item, Mapping)), {})


def _first_coding(concept: Any) -> Mapping[str, Any]:
    coding = _as_mapping(concept).get("coding")
    if not isinstance(coding, list) or not coding:
        return {}

    return _as_mapping(coding[0])


def _concept_code(concept: Any) -> str | None:
    concept_mapping = _as_mapping(concept)
    return _as_string(_first_coding(concept_mapping).get("code")) or _as_string(
        concept_mapping.get("text")
    )


def _parse_fhir_date(value: Any) -> date | None:
    text = _as_string(value)
    if text is None:
        return None

    try:
        return date.fromisoformat(text)
    except ValueError:
        return None


def _parse_fhir_datetime(value: Any) -> datetime | None:
    text = _as_string(value)
    if text is None:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _parse_onset_date(resource: Mapping[str, Any]) -> date | None:
    onset = resource.get("onsetDateTime")
    if onset is None:
        onset = _as_mapping(resource.get("onsetPeriod")).get("start")

    parsed_date = _parse_fhir_date(onset)
    if parsed_date is not None:
        return parsed_date

    parsed_datetime = _parse_fhir_datetime(onset)
    return parsed_datetime.date() if parsed_datetime is not None else None


def normalize_patient(resource: Mapping[str, Any]) -> NormalizedPatient:
    """Convert a raw FHIR Patient into fields accepted by the patient model."""

    name = _first_mapping(resource.get("name"))
    given_values = name.get("given")
    given_names = (
        [value for item in given_values if (value := _as_string(item))]
        if isinstance(given_values, list)
        else []
    )
    family_name = _as_string(name.get("family"))
    display_name = _as_string(name.get("text"))

    if display_name is None:
        display_name = " ".join(
            [*given_names, *([family_name] if family_name else [])]
        ) or None

    return {
        "external_id": _as_string(resource.get("id")),
        "name": display_name,
        "given_name": given_names[0] if given_names else None,
        "family_name": family_name,
        "gender": _as_string(resource.get("gender")),
        "birth_date": _parse_fhir_date(resource.get("birthDate")),
        "raw_resource": deepcopy(dict(resource)),
    }


def normalize_condition(resource: Mapping[str, Any]) -> NormalizedCondition:
    """Convert a raw FHIR Condition into fields accepted by the condition model."""

    code_concept = _as_mapping(resource.get("code"))
    coding = _first_coding(code_concept)

    return {
        "external_id": _as_string(resource.get("id")),
        "clinical_status": _concept_code(resource.get("clinicalStatus")),
        "verification_status": _concept_code(resource.get("verificationStatus")),
        "code": _as_string(coding.get("code")),
        "code_system": _as_string(coding.get("system")),
        "display": _as_string(coding.get("display"))
        or _as_string(code_concept.get("text")),
        "onset_date": _parse_onset_date(resource),
        "raw_resource": deepcopy(dict(resource)),
    }


def normalize_medication_request(
    resource: Mapping[str, Any],
) -> NormalizedMedicationRequest:
    """Convert a raw MedicationRequest into fields accepted by its model."""

    concept = _as_mapping(resource.get("medicationCodeableConcept"))
    coding = _first_coding(concept)
    medication_code = _as_string(coding.get("code"))
    medication_display = _as_string(coding.get("display")) or _as_string(
        concept.get("text")
    )

    if not concept:
        reference_value = resource.get("medicationReference")
        reference = _as_mapping(reference_value)
        medication_code = _as_string(reference.get("reference")) or _as_string(
            reference_value
        )
        medication_display = _as_string(reference.get("display")) or _as_string(
            reference.get("text")
        )

    return {
        "external_id": _as_string(resource.get("id")),
        "status": _as_string(resource.get("status")),
        "medication_code": medication_code,
        "medication_display": medication_display,
        "authored_on": _parse_fhir_datetime(resource.get("authoredOn")),
        "raw_resource": deepcopy(dict(resource)),
    }


def extract_bundle_resources(
    bundle: Mapping[str, Any] | None,
) -> list[FHIRResource]:
    """Extract valid raw resources from a FHIR Bundle's entries."""

    if not bundle:
        return []

    entries = bundle.get("entry")
    if not isinstance(entries, list):
        return []

    resources: list[FHIRResource] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue

        resource = entry.get("resource")
        if isinstance(resource, dict):
            resources.append(resource)

    return resources


def get_next_bundle_link(bundle: Mapping[str, Any] | None) -> str | None:
    """Return the server-provided next-page URL from a FHIR Bundle."""

    if not bundle:
        return None

    links = bundle.get("link")
    if not isinstance(links, list):
        return None

    for link in links:
        if not isinstance(link, Mapping) or link.get("relation") != "next":
            continue

        url = link.get("url")
        if isinstance(url, str) and url.strip():
            return url.strip()

    return None


async def paginate_fhir_bundle(
    initial_url: str,
    fetch_page: FHIRPageFetcher,
    *,
    params: FHIRQueryParams | None = None,
) -> list[FHIRResource]:
    """Follow Bundle next links and return every contained FHIR resource."""

    resources: list[FHIRResource] = []
    current_url: str | None = initial_url
    current_params = params

    while current_url is not None:
        bundle = await fetch_page(current_url, current_params)
        resources.extend(extract_bundle_resources(bundle))

        next_link = get_next_bundle_link(bundle)
        current_url = urljoin(current_url, next_link) if next_link else None
        current_params = None

    return resources


async def fetch_fhir_bundle_page(
    initial_url: str,
    fetch_page: FHIRPageFetcher,
    *,
    page: int,
    params: FHIRQueryParams | None = None,
) -> FHIRPage:
    """Follow server next links until the requested one-based Bundle page."""

    if page < 1:
        raise ValueError("page must be at least 1")

    current_url: str | None = initial_url
    current_params = params
    current_page = 1

    while current_url is not None:
        bundle = await fetch_page(current_url, current_params)
        next_link = get_next_bundle_link(bundle)

        if current_page == page:
            return {
                "resources": extract_bundle_resources(bundle),
                "has_next": next_link is not None,
            }

        current_url = urljoin(current_url, next_link) if next_link else None
        current_params = None
        current_page += 1

    return {"resources": [], "has_next": False}
