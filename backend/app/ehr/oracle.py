from app.ehr.hapi import FHIRClient, FHIRResource

PATIENT_SEARCH = "smart"


async def fetch_patients(client: FHIRClient) -> list[FHIRResource]:
    return await client.all("Patient", {"_count": 5, "name": PATIENT_SEARCH})


async def fetch_conditions(client: FHIRClient, patient_id: str) -> list[FHIRResource]:
    return await client.all("Condition", {"patient": patient_id, "_count": 50})


async def fetch_medications(client: FHIRClient, patient_id: str) -> list[FHIRResource]:
    return await client.all("MedicationRequest", {"patient": patient_id, "_count": 50})
