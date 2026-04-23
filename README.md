# MAR Chart Generator

A web-based **Medication Administration Record (MAR) chart** generator. Fill in a simple form and download a ready-to-use MAR chart as a **PDF** or **Word (.docx)** document.

![MAR Chart Generator Form](https://github.com/user-attachments/assets/83da4daa-fd6d-401f-8764-141ade160a24)

---

## Features

- **Patient information**: name, date of birth, patient ID / NHS number, allergies
- **Prescribing organisation**: organisation name, prescriber name, address
- **Chart period**: choose any month and year
- **Up to 6 medications** (3 per page side):
  - Medication name, dose, route, start/end date, special instructions
  - Administration rounds: Morning, Noon, Evening, Bedtime
  - Day-by-day administration grid for the whole month
- **Front page** (medications 1–3) and **Back page** (medications 4–6)
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

Each page of the generated document contains:

| Section | Contents |
|---|---|
| Header | Title with month/year and page label |
| Patient info | Name, DOB, Patient ID, Allergies |
| Organisation info | Organisation name, prescriber, address |
| Medication grid | Medication details + day-by-day administration columns |
| Key | Symbol legend (✓ Administered, X Not given, R Refused, H Hospital, S Self-administered) |

---

## Running Tests

```bash
python -m pytest tests/
```