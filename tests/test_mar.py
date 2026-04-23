"""Tests for the MAR chart generator."""
import pytest

from mar_generator import MARData, Medication, generate_pdf, generate_word


SAMPLE_DATA = MARData(
    patient_name="Jane Smith",
    patient_dob="01/01/1950",
    patient_id="943 476 5919",
    allergies="Penicillin",
    org_name="Sunrise Care Home",
    org_address="12 High St, London, SW1A 1AA",
    prescriber_name="Dr. A. Jones",
    chart_month=4,
    chart_year=2026,
    medications=[
        Medication(
            name="Amlodipine 5mg tablets",
            dose="5mg",
            route="Oral",
            start_date="01/04/2026",
            end_date="",
            rounds=["Morning"],
            instructions="",
        ),
        Medication(
            name="Metformin 500mg tablets",
            dose="500mg",
            route="Oral",
            start_date="01/04/2026",
            end_date="",
            rounds=["Morning", "Evening"],
            instructions="With food",
        ),
        Medication(
            name="Atorvastatin 20mg tablets",
            dose="20mg",
            route="Oral",
            start_date="01/04/2026",
            end_date="",
            rounds=["Bedtime"],
            instructions="",
        ),
    ],
)


def test_generate_pdf_returns_bytes():
    result = generate_pdf(SAMPLE_DATA)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_pdf_starts_with_pdf_header():
    result = generate_pdf(SAMPLE_DATA)
    assert result[:4] == b"%PDF"


def test_generate_word_returns_bytes():
    result = generate_word(SAMPLE_DATA)
    assert isinstance(result, bytes)
    assert len(result) > 0


def test_generate_word_is_zip_format():
    """docx files are ZIP archives."""
    result = generate_word(SAMPLE_DATA)
    assert result[:2] == b"PK"


def test_generate_pdf_no_medications():
    data = MARData(
        patient_name="Test Patient",
        patient_dob="",
        patient_id="",
        allergies="",
        org_name="Test Org",
        org_address="",
        prescriber_name="",
        chart_month=1,
        chart_year=2026,
        medications=[],
    )
    result = generate_pdf(data)
    assert result[:4] == b"%PDF"


def test_generate_word_no_medications():
    data = MARData(
        patient_name="Test Patient",
        patient_dob="",
        patient_id="",
        allergies="",
        org_name="Test Org",
        org_address="",
        prescriber_name="",
        chart_month=1,
        chart_year=2026,
        medications=[],
    )
    result = generate_word(data)
    assert result[:2] == b"PK"


def test_generate_pdf_with_back_page():
    """Six medications triggers a back page."""
    data = MARData(
        patient_name="Jane Smith",
        patient_dob="01/01/1950",
        patient_id="",
        allergies="",
        org_name="Test Org",
        org_address="",
        prescriber_name="",
        chart_month=4,
        chart_year=2026,
        medications=[
            Medication(f"Medication {i}", "5mg", "Oral", "01/04/2026", "", ["Morning"], "")
            for i in range(1, 7)
        ],
    )
    result = generate_pdf(data)
    assert result[:4] == b"%PDF"


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
            "patient_id": "943 476 5919",
            "allergies": "Penicillin",
            "org_name": "Sunrise Care Home",
            "org_address": "12 High St, London",
            "prescriber_name": "Dr. A. Jones",
            "chart_month": "4",
            "chart_year": "2026",
            "med_1_name": "Amlodipine 5mg",
            "med_1_dose": "5mg",
            "med_1_route": "Oral",
            "med_1_start": "01/04/2026",
            "med_1_rounds": "Morning",
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
            "patient_id": "943 476 5919",
            "allergies": "Penicillin",
            "org_name": "Sunrise Care Home",
            "org_address": "12 High St, London",
            "prescriber_name": "Dr. A. Jones",
            "chart_month": "4",
            "chart_year": "2026",
            "med_1_name": "Amlodipine 5mg",
            "med_1_dose": "5mg",
            "med_1_route": "Oral",
            "med_1_start": "01/04/2026",
            "med_1_rounds": "Morning",
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
            "org_name": "Test Org",
            "chart_month": "6",
            "chart_year": "2026",
            "med_1_name": "Aspirin 75mg",
            "output_format": "pdf",
        },
    )
    assert b"John_Doe" in resp.headers["Content-Disposition"].encode()
