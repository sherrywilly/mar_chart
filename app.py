"""
MAR Chart Web Application
Run with: python app.py
"""
from __future__ import annotations

from datetime import date

from flask import Flask, Response, render_template, request

from mar_generator import MARData, Medication, generate_pdf, generate_word, ROUNDS

app = Flask(__name__)


def _date_to_dmy(raw: str) -> str:
    """Accept YYYY-MM-DD or DD/MM/YYYY and return DD/MM/YYYY."""
    value = (raw or "").strip()
    if not value:
        return ""
    if "-" in value:
        try:
            y, m, d = value.split("-")
            return date(int(y), int(m), int(d)).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return ""
    if "/" in value:
        try:
            d, m, y = value.split("/")
            return date(int(y), int(m), int(d)).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            return ""
    return ""


@app.route("/", methods=["GET"])
def index():
    today = date.today()
    default_start = today.strftime("%Y-%m-%d")
    return render_template("index.html", default_start=default_start)


@app.route("/generate", methods=["POST"])
def generate():
    form = request.form

    # Collect medications (up to 3 — all shown on the front page)
    medications = []
    for i in range(1, 4):
        name = form.get(f"med_{i}_name", "").strip()
        if not name:
            continue
        rounds = form.getlist(f"med_{i}_rounds")
        med = Medication(
            name=name,
            dose=form.get(f"med_{i}_dose", "").strip(),
            route=form.get(f"med_{i}_route", "").strip(),
            end_date=form.get(f"med_{i}_end", "").strip(),
            rounds=rounds if rounds else list(ROUNDS),
            instructions=form.get(f"med_{i}_instructions", "").strip(),
            container=form.get(f"med_{i}_container", "").strip(),
        )
        medications.append(med)

    start_date = _date_to_dmy(form.get("start_date", "")) or date.today().strftime("%d/%m/%Y")
    patient_dob = _date_to_dmy(form.get("patient_dob", "")) or form.get("patient_dob", "").strip()

    mar_data = MARData(
        patient_name=form.get("patient_name", "").strip(),
        patient_dob=patient_dob,
        nhs_number=form.get("nhs_number", "").strip(),
        allergies=form.get("allergies", "").strip(),
        gender=form.get("gender", "").strip(),
        patient_address=form.get("patient_address", "").strip(),
        doctor=form.get("doctor", "").strip(),
        start_date=start_date,
        patient_id=form.get("patient_id", "").strip(),
        room=form.get("room", "").strip(),
        org_name=form.get("org_name", "AYP Healthcare").strip(),
        org_address=form.get("org_address", "").strip(),
        prescribing_org=form.get("prescribing_org", "").strip(),
        document_no=form.get("document_no", "").strip(),
        pharmacy_no=form.get("pharmacy_no", "").strip(),
        phone=form.get("phone", "").strip(),
        medications=medications,
    )

    output_format = form.get("output_format", "pdf")
    safe_name = mar_data.patient_name.replace(" ", "_") or "Patient"
    safe_date = start_date.replace("/", "-")

    if output_format == "word":
        content = generate_word(mar_data)
        filename = f"MAR_Chart_{safe_name}_{safe_date}.docx"
        return Response(
            content,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        content = generate_pdf(mar_data)
        filename = f"MAR_Chart_{safe_name}_{safe_date}.pdf"
        return Response(
            content,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
