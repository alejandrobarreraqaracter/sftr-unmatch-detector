# SFTR Unmatch Detector

A full-stack web application for financial compliance teams to automate SFTR (Securities Financing Transactions Regulation) report reconciliation. Compares 155 SFTR fields between two counterparty reports, identifies discrepancies, classifies them by severity, and provides a resolution workflow.

## Features

- **File Upload & Parsing** — Upload CSV (semicolon-separated) or XML (ISO 20022) reports from two counterparties
- **Field-by-Field Comparison** — Compares all 155 SFTR fields with obligation-aware severity classification
- **Mirror Field Handling** — Recognizes valid inverse values (e.g., GIVE/TAKE) as non-mismatches
- **Resolution Workflow** — Track mismatch status (Pending → In Negotiation → Resolved), assign to team members, add notes
- **Dashboard** — Summary metrics, filterable mismatch table, click-to-expand detail panel
- **Analytics** — Top unmatch fields, trend over time, breakdown by counterparty and SFT type
- **XLSX Export** — Color-coded Excel export matching the existing compliance template format
- **Bulk Actions** — Resolve all, assign all critical fields to a user

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, Vite, Tailwind CSS, shadcn/ui, Recharts |
| Backend | FastAPI, SQLAlchemy, Python 3.11 |
| Database | SQLite |
| File Parsing | pandas (CSV), lxml (XML) |
| Export | openpyxl (XLSX) |

## Setup

### Backend

```bash
cd backend
poetry install
poetry run fastapi dev app/main.py
```

The API server starts at `http://localhost:8000`. API docs available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend starts at `http://localhost:5173`.

### Environment Variables

**Frontend** (`frontend/.env`):
```
VITE_API_URL=http://localhost:8000
```

**Backend**: Uses SQLite by default at `./sftr_unmatch.db`. Set `DATABASE_URL` to override.

## Sample Data

Two sample CSV files are included in `backend/sample_data/`:
- `emisor_report.csv` — Emisor counterparty report
- `receptor_report.csv` — Receptor counterparty report

These contain 5 intentional mismatches for demo:
1. **Maturity date** — Emisor: 2024-03-22, Receptor: 2024-03-29 (CRITICAL)
2. **Fixed rate** — Emisor: 0.0125, Receptor: 0.0150 (CRITICAL)
3. **Principal amount on maturity date** — Different values (CRITICAL)
4. **Sector of the reporting counterparty** — CDTI vs INVF (different entities, expected)
5. **Availability for collateral reuse** — true vs false (CRITICAL)

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions/upload` | Upload two files, run comparison |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Session detail + field results |
| GET | `/api/sessions/{id}/summary` | Summary metrics |
| GET | `/api/sessions/{id}/activity` | Activity log |
| PATCH | `/api/fields/{id}` | Update field status/assignee/notes |
| POST | `/api/sessions/{id}/bulk-update` | Bulk resolve or assign |
| POST | `/api/sessions/{id}/export` | Download XLSX |
| GET | `/api/analytics/top-fields` | Top unmatch fields |
| GET | `/api/analytics/trend` | Unmatch rate over time |
| GET | `/api/analytics/by-counterparty` | Breakdown by counterparty |
| GET | `/api/analytics/by-sft-type` | Breakdown by SFT type |

## SFTR Field Registry

The 155-field registry is at `backend/app/data/sftr_fields.json`, covering:
- Table 1: Counterparty Data (18 fields)
- Table 2: Loan and Collateral Data (99 fields)
- Table 3: Margin Data (20 fields)
- Table 4: Re-use Data (18 fields)

Each field includes obligation rules per SFT type (Repo/BSB/SL/ML) and action type (NEWT/MODI/EROR/ETRM/CORR/VALU).

## Severity Classification

| Level | Obligation | Color | Meaning |
|-------|-----------|-------|---------|
| CRITICAL | M (Mandatory) | Red | Report will be rejected by TR |
| WARNING | C (Conditional) | Amber | Check condition applicability |
| INFO | O (Optional) | Blue | Not blocking, format-only |
| NONE | — | Green | Match or N/A |
