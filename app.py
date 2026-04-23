"""
MAR Chart Web Application
Run with: python app.py
"""
from __future__ import annotations

import calendar
from datetime import date

from flask import Flask, Response, render_template, request

from mar_generator import MARData, Medication, generate_pdf, generate_word

app = Flask(__name__)


@app.route("/", methods=["GET"])
def index():
    today = date.today()
    return render_template("index.html", month=today.month, year=today.year)


@app.route("/generate", methods=["POST"])
def generate():
    form = request.form

    # Collect medications (up to 6 — 3 per page side)
    medications = []
    for i in range(1, 7):
        name = form.get(f"med_{i}_name", "").strip()
        if not name:
            continue
        rounds = form.getlist(f"med_{i}_rounds")
        med = Medication(
            name=name,
            dose=form.get(f"med_{i}_dose", "").strip(),
            route=form.get(f"med_{i}_route", "").strip(),
            start_date=form.get(f"med_{i}_start", "").strip(),
            end_date=form.get(f"med_{i}_end", "").strip(),
            rounds=rounds,
            instructions=form.get(f"med_{i}_instructions", "").strip(),
        )
        medications.append(med)

    try:
        chart_month = int(form.get("chart_month", date.today().month))
        chart_year = int(form.get("chart_year", date.today().year))
    except ValueError:
        chart_month = date.today().month
        chart_year = date.today().year

    mar_data = MARData(
        patient_name=form.get("patient_name", "").strip(),
        patient_dob=form.get("patient_dob", "").strip(),
        patient_id=form.get("patient_id", "").strip(),
        allergies=form.get("allergies", "").strip(),
        org_name=form.get("org_name", "").strip(),
        org_address=form.get("org_address", "").strip(),
        prescriber_name=form.get("prescriber_name", "").strip(),
        chart_month=chart_month,
        chart_year=chart_year,
        medications=medications,
    )

    output_format = form.get("output_format", "pdf")

    if output_format == "word":
        content = generate_word(mar_data)
        month_str = calendar.month_abbr[chart_month]
        filename = f"MAR_Chart_{mar_data.patient_name.replace(' ', '_')}_{month_str}{chart_year}.docx"
        return Response(
            content,
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        content = generate_pdf(mar_data)
        month_str = calendar.month_abbr[chart_month]
        filename = f"MAR_Chart_{mar_data.patient_name.replace(' ', '_')}_{month_str}{chart_year}.pdf"
        return Response(
            content,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=5000)
