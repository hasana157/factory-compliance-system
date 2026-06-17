# Factory Compliance & Alert Escalation System

An automated safety monitoring application that detects unsafe workplace behaviors in factory video clips, assigns policy-grounded severity tiers, routes high-risk alerts in real time, and stores immutable compliance records for audit review.

## Overview

The system is built as five connected modules:

1. Detection Engine: processes video clips and emits structured violation detections.
2. Severity Categorization: maps each violation to LOW, MEDIUM, HIGH, or CRITICAL using `src/severity/rules.json`.
3. Escalation Pipeline: logs every violation and sends real-time alerts for HIGH and CRITICAL events.
4. Report Generation: persists records to SQLite, JSON Lines, and CSV.
5. Operations Dashboard: React dashboard with live feed, alert timeline, history filters, and export.

The current implementation is a practical assessment MVP. It includes optional YOLO hooks, but it does not claim to be a fully trained custom CV model. For the Kaggle dataset structure, it uses the parent folder label as a deterministic fallback so the pipeline can be evaluated end to end before model fine-tuning.

## Getting Started

### Prerequisites

- Python 3.10 or newer
- Node.js 18 or newer
- npm
- Optional: Kaggle account for the video dataset

### Backend Setup

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/database_init.py
python src/main.py
```

Backend API: `http://localhost:8000`

API docs: `http://localhost:8000/docs`

### Dashboard Setup

```bash
cd src/dashboard
npm install
npm run dev
```

Dashboard: `http://localhost:5173`

If PowerShell blocks `npm`, run `npm.cmd install` and `npm.cmd run dev`.

## Dataset

Download the dataset from Kaggle:

`https://www.kaggle.com/datasets/trnhhnggiang/videodataset-for-safe-and-unsafe-behaviours`

Extract it into:

```text
data/train/[behavior folders]
data/test/[behavior folders]
```

The detector recognizes these unsafe behavior folders:

- `Safe_Walkway_Violation`
- `Unauthorized_Intervention`
- `Opened_Panel_Cover`
- `Carrying_Overload_with_Forklift`

## Running the Pipeline

Process a labeled dataset path:

```bash
curl -X POST http://localhost:8000/api/process_video ^
  -H "Content-Type: application/json" ^
  -d "{\"video_path\":\"data/test/Carrying_Overload_with_Forklift/demo_overload.mp4\"}"
```

Seed four demo records:

```bash
curl -X POST http://localhost:8000/api/demo/seed
```

Run tests:

```bash
python -m pytest tests
```

## Architecture

Video clips flow through:

```text
Video or dataset path
  -> DetectionEngine
  -> SeverityClassifier
  -> ComplianceReportGenerator
  -> EscalationRouter
  -> SQLite / JSONL / CSV + WebSocket dashboard alert
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for the module design.

## Policy Parsing Approach

Policy-derived rules live in [src/severity/rules.json](src/severity/rules.json). Each unsafe behavior includes:

- Policy section reference
- Observable indicator
- Detection approach
- Default severity
- Escalation conditions
- Severity rationale

See [POLICY_EXTRACTION.md](POLICY_EXTRACTION.md) for the mapping.

## API Documentation

Key endpoints:

- `GET /api/health`
- `POST /api/process_video`
- `POST /api/upload_video`
- `POST /api/demo/seed`
- `GET /api/violations`
- `GET /api/export/violations`
- `WebSocket /ws/alerts`

See [API_ENDPOINTS.md](API_ENDPOINTS.md) for details.

## Known Limitations

- The current CV layer is not fine-tuned on the Kaggle dataset.
- Dataset-folder labels are used as a fallback to keep the full pipeline testable.
- Walkway frame heuristics require visible green markings and person detection.
- Vest, panel, and block-count detection need custom model training for production accuracy.
- The dashboard has no authentication because the assessment scope is single-user local operation.

See [LIMITATIONS.md](LIMITATIONS.md) for the full trade-off list.

## Project Structure

```text
src/
  detection/      Module 1
  severity/       Module 2
  escalation/     Module 3
  reports/        Module 4
  dashboard/      Module 5
tests/
docs/
outputs/
```

## Future Improvements

- Fine-tune YOLOv8 on the labeled videos.
- Add a vest color classifier and panel state classifier.
- Add Slack/email escalation for critical alerts.
- Add authentication and role-based access for supervisors.
- Move from SQLite to PostgreSQL for multi-camera deployments.

## License

MIT.
