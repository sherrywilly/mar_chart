"""Tests for the AYP Healthcare MAR chart generator."""
import pytest

from mar_generator import MARData, Medication, ROUNDS, generate_pdf, generate_word


def _make_data(**overrides) -> MARData:
    defaults = dict(
        patient_name="Jane Smith",
        patient_dob="01/01/1950",
        nhs_number="943 476 5919",
        allergies="Penicillin",
        gender="Female",
        patient_address="12 High St, London, SW1A 1AA",
        doctor="Dr. A. Jones",
        start_date="27/12/2025",
        patient_id="53486",
        room="12",
        org_name="AYP Healthcare",
        org_address="Unit 9 Guardian Business Centre\nRM3 8FD",
        prescribing_org="Sunrise Care Home",
        document_no="MAR-001",
        pharmacy_no="FKD50",
        phone="0208 344 0500",
    )
    defaults.update(overrides)
    return MARData(**defaults)


SAMPLE_MED = Medication(
    name="Paracetamol 500mg tab",
    dose="500mg",
    route="Oral",
    start_date="27/12/2025",
    end_date="",
    rounds=list(ROUNDS),
    instructions="Two to be taken when required",
    container="Separate container",
)

SAMPLE_DATA = _make_data(medications=[SAMPLE_MED])


# ---- PDF tests ----

def test_generate_pdf_returns_bytes():
    result = generate_pdf(SAMPLE_DATA)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_starts_with_pdf_header():
    result = generate_pdf(SAMPLE_DATA)
    assert result[:4] == b"%PDF"


def test_generate_pdf_no_medications():
    data = _make_data(medications=[])
    result = generate_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_pdf_three_medications():
    meds = [
        Medication(
            name=f"Med {i}", dose="5mg", route="Oral",
            start_date="27/12/2025", rounds=list(ROUNDS),
        )
        for i in range(1, 4)
    ]
    data = _make_data(medications=meds)
    result = generate_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_pdf_invalid_start_date_falls_back():
    """Generator should not raise even if start_date is malformed."""
    data = _make_data(start_date="not-a-date")
    result = generate_pdf(data)
    assert result[:4] == b"%PDF"


# ---- Word tests ----

def test_generate_word_returns_bytes():
    result = generate_word(SAMPLE_DATA)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_word_is_zip_format():
    """docx files are ZIP archives."""
    result = generate_word(SAMPLE_DATA)
    assert result[:2] == b"PK"


def test_generate_word_no_medications():
    data = _make_data(medications=[])
    result = generate_word(data)
    assert result[:2] == b"PK"


# ---- Flask route tests ----

def test_flask_get_form(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"MAR Chart" in resp.data
    assert b"patient_name" in resp.data


def test_flask_generate_pdf(client):
    resp = client.post(
        "/generate",
        data={
            "patient_name": "Jane Smith",
            "patient_dob": "01/01/1950",
            "nhs_number": "943 476 5919",
            "allergies": "Penicillin",
            "gender": "Female",
            "patient_address": "12 High St, London",
            "doctor": "Dr. A. Jones",
            "start_date": "27/12/2025",
            "patient_id": "53486",
            "room": "12",
            "org_name": "AYP Healthcare",
            "org_address": "Unit 9 Guardian Business Centre\nRM3 8FD",
            "prescribing_org": "Sunrise Care Home",
            "document_no": "MAR-001",
            "pharmacy_no": "FKD50",
            "phone": "0208 344 0500",
            "med_1_name": "Paracetamol 500mg",
            "med_1_dose": "500mg",
            "med_1_route": "Oral",
            "med_1_start": "27/12/2025",
            "med_1_rounds": "MORNI",
            "output_format": "pdf",
        },
    )
    assert resp.status_code == 200
    assert resp.content_type == "application/pdf"
    assert b"MAR_Chart" in resp.headers["Content-Disposition"].encode()
    assert resp.data[:4] == b"%PDF"


def test_flask_generate_word(client):
    resp = client.post(
        "/generate",
        data={
            "patient_name": "Jane Smith",
            "patient_dob": "01/01/1950",
            "nhs_number": "943 476 5919",
            "allergies": "Penicillin",
            "gender": "Female",
            "patient_address": "12 High St, London",
            "doctor": "Dr. A. Jones",
            "start_date": "27/12/2025",
            "patient_id": "53486",
            "room": "12",
            "org_name": "AYP Healthcare",
            "org_address": "Unit 9 Guardian Business Centre",
            "prescribing_org": "Sunrise Care Home",
            "document_no": "",
            "pharmacy_no": "FKD50",
            "phone": "0208 344 0500",
            "med_1_name": "Paracetamol 500mg",
            "med_1_dose": "500mg",
            "med_1_route": "Oral",
            "med_1_start": "27/12/2025",
            "med_1_rounds": "MORNI",
            "output_format": "word",
        },
    )
    assert resp.status_code == 200
    assert "wordprocessingml" in resp.content_type
    assert b"MAR_Chart" in resp.headers["Content-Disposition"].encode()
    assert resp.data[:2] == b"PK"


def test_flask_filename_uses_patient_name(client):
    resp = client.post(
        "/generate",
        data={
            "patient_name": "John Doe",
            "org_name": "AYP Healthcare",
            "start_date": "01/01/2026",
            "med_1_name": "Aspirin 75mg",
            "output_format": "pdf",
        },
    )
    assert b"John_Doe" in resp.headers["Content-Disposition"].encode()
