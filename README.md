# MAR Chart Generator

A web-based **Medication Administration Record (MAR) chart** generator. Fill in a simple form and download a ready-to-use MAR chart as a **PDF** or **Word (.docx)** document.

![MAR Chart Generator Form](https://github.com/user-attachments/assets/83da4daa-fd6d-401f-8764-141ade160a24)

---

## Features

- **AYP Healthcare branding**: organisation name, address, pharmacy number shown in header
- **Patient information**: name, NHS number, date of birth, gender, allergies/conditions, address, doctor, patient ID, room
- **Chart period**: enter a start date — the chart automatically covers the **4 complete Mon–Sun weeks** from that date
- **Up to 3 medications** on the front page:
  - Medication name, dose, route, start/end date, special instructions, container/storage note
  - Administration rounds: **MORNI, LUNCH, TEA, NIGHT**
  - Weekly grid (4 weeks × 7 days) with Received / Returned / Destroyed tracking row per medication
- **Front page**: medication administration grid
- **Back page**: **Carers Medication Notes** log table (DATE / TIME / INITIALS / MEDICATION / DOSE / REASON / RESULT / TIME / INITIALS)
- **Output formats**: PDF (landscape A4) or Word (.docx, landscape A4)

---

## Getting Started

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the app

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**, fill in the form and click **Generate & Download MAR Chart**.

---

## Project Structure

```
mar_chart/
├── app.py            # Flask web application (routes)
├── mar_generator.py  # PDF and Word generation logic
├── templates/
│   └── index.html    # HTML form
└── requirements.txt  # Python dependencies
```

---

## MAR Chart Layout

### Front page

| Section | Contents |
|---|---|
| Header | AYP Healthcare (org name), address, pharmacy number; Medication Administration / Record Sheet title; Document No. |
| Patient info | Name, NHS Number, DOB, Gender, Allergies/Conditions, Doctor, Address, Start Date, Period, Patient ID, Room, Prescribing Organisation |
| Medication grid | Up to 3 medications — weekly grid (4 weeks × 7 days), MORNI / LUNCH / TEA / NIGHT rounds, Received / Returned / Destroyed row |
| Legend | R – Refused, B – Nausea or Vomiting, C – Hospitalized, D – Social Leave, E – Refused & Destroyed, F – Other |

### Back page

| Section | Contents |
|---|---|
| Title | CARERS MEDICATION NOTES |
| Notes table | DATE / TIME / INITIALS / MEDICATION / DOSE / REASON / RESULT / TIME / INITIALS — 30 blank rows |
| Branding | AYP Healthcare logo area (bottom right) |

---

## Running Tests

```bash
python -m pytest tests/
```