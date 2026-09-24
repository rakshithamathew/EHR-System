from collections.abc import Awaitable, Callable, Mapping
from typing import Any
from urllib.parse import urljoin

FHIRResource = dict[str, Any]
FHIRQueryParams = Mapping[str, str | int | float | bool | None]
FHIRPageFetcher = Callable[
    [str, FHIRQueryParams | None],
    Awaitable[FHIRResource],
]


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
