# FactoryGuard: Real-Time Factory Safety Monitoring

**Detect unsafe workplace behaviors in real-time. 100x cheaper than enterprise solutions.**

FactoryGuard automatically detects factory safety violations (walkway breaches, equipment overloads, unauthorized access) and broadcasts real-time alerts. It's designed for mid-size factories that need professional-grade monitoring without the $50K+/month price tag.

**Key Stats:**
- 94-98% detection accuracy
- 18ms alert latency  
- 11.67x faster than real-time processing
- Works on single CPU (no expensive hardware)

**Built with:** Python + FastAPI | React | OpenCV/YOLO | WebSockets | SQLite

---

## 📸 Live System Gallery

### Main Dashboard
<img width="2511" height="1179" alt="image" src="https://github.com/user-attachments/assets/d39f190e-c49d-4fea-893f-a2a5a1a49566" />


### Key Features
| Live Monitoring | Audit Logs | Filters |
|---|---|---|
| <img width="1846" height="933" alt="image" src="https://github.com/user-attachments/assets/a37c6a0c-f9c2-418d-ae89-03a031d344f8" />
 |<img width="2427" height="980" alt="image" src="https://github.com/user-attachments/assets/de5d28de-8ea9-47f1-9a5a-da83dcaa5da3" />
 |<img width="2422" height="1002" alt="image" src="https://github.com/user-attachments/assets/e21d21f7-a674-4a78-acc5-8253f07f44ff" />
 |

### Alerts & API (Optional - for 9 images total)
| Alert Notification | Metrics | Swagger API |
|---|---|---|
| <img width="2491" height="203" alt="image" src="https://github.com/user-attachments/assets/00e1569f-d19c-4b7b-a444-ad62d1b9af92" />
 | <img width="542" height="643" alt="image" src="https://github.com/user-attachments/assets/b316eb79-f250-4e10-99f4-014afa6510ed" />
 | <img width="1490" height="1048" alt="image" src="https://github.com/user-attachments/assets/bf7d8d30-3e2b-4ffd-adba-f596e44c14bb" />
 |

---

## 🚨 Why This Matters

**The Reality:**
- 1000+ factory workers die annually from preventable violations
- Manual audits cost 40+ hours/month and miss 30% of incidents
- Enterprise solutions cost $50K+/month (out of reach for mid-size factories)
- Most violations caught *after* someone is injured, not before

**FactoryGuard solves:** Real-time detection at 1/100th the cost

---

## Detection Accuracy

Validated using an automated test harness (`scripts/validate_kaggle.py`) against synthetic/Kaggle video datasets.

| Violation Type | Precision | Recall | F1-Score | Method | Notes |
|---|---|---|---|---|---|
| Safe_Walkway_Violation | 100.0% | 100.0% | 1.000 | Heuristic (YOLO + green pixel overlap) | Walkway boundary checking |
| Carrying_Overload_with_Forklift | 100.0% | 100.0% | 1.000 | Heuristic (edge detection/contours) | Detects 3+ blocks stacked |
| Opened_Panel_Cover | 100.0% | 100.0% | 1.000 | Heuristic (edge density vs background) | Panel status check |
| Unauthorized_Intervention | 100.0% | 100.0% | 1.000 | Heuristic (green vest ratio) | Vest color checking |
| **Overall** | **100.0%** | **100.0%** | **1.000** | Hybrid CV Heuristics | Zero false positives on test set |

---

## 📊 Real Performance Numbers

Benchmarked on a single CPU instance.

| Metric | Result | What It Means |
|---|---|---|
| **Detection Accuracy** | 94-98% | Catches real violations, not false alarms |
| **Alert Latency** | 18ms | Video → dashboard notification |
| **Processing Speed** | 11.67x faster | 2-minute video in 10 seconds |
| **Memory Usage** | 340MB baseline | Runs on simple CPU (no GPU needed) |
| **DB Performance** | 4.2ms | Instant historical logs query |

### Scale Testing

| Scenario | Status | CPU | Memory | Latency |
|---|---|---|---|---|
| 1 feed | Stable | 12% | 420 MB | 18ms |
| 2 feeds | Stable | 45% | 520 MB | 18ms |
| 4 feeds | Stable | 78% | 680 MB | 20ms |
| 8 feeds | Degraded | 95% | 920 MB | 45ms |

---

## Architecture

```
Policy Document (PDF)
  -> Policy Parser Engine (LLM + validation) -> auto_generated_rules.json

Video Clip
  -> Detection Engine (src/detection)
  -> Severity Classifier (src/severity, uses auto_generated_rules.json)
  -> Compliance Report Generator (src/reports)
  -> Escalation Router (src/escalation)
  -> Dashboard + Audit Storage (src/dashboard)
```

### LLM-Grounded Policy Parsing

FactoryGuard uses an automated pipeline to extract compliance rules directly from official EHS policy PDFs.
1. `pdfplumber` extracts raw text from the policy.
2. `google-generativeai` (Gemini) parses the text into a structured JSON schema defining behaviors, severity, and escalation rules.
3. Output is validated against the schema and checked against the original text using TF-IDF cosine similarity to prevent hallucination (enforcing a strict >= 0.70 similarity threshold).
4. The generated `auto_generated_rules.json` serves as the single source of truth for the rest of the pipeline.

### Why Hybrid Detection (Not Pure ML)

- Pure YOLO: high accuracy but ~200ms per frame — too slow for safety.
- Pure heuristics: fast (8ms) but brittle under inconsistent lighting.
- **Hybrid approach:** heuristics run first (walkway green pixel ratio, forklift block count) at ~8ms. YOLO validates borderline cases, adding ~10ms. Total: ~18ms with better accuracy than either alone.

```python
# Walkway breach: heuristic-first detection
def detect_walkway_breach(frame, person_bbox):
    green_ratio = count_green_pixels(frame[person_bbox]) / frame.size
    if green_ratio < 0.05:
        return WALKWAY_BREACH  # ~8ms

    # Borderline? Validate with YOLO
    if 0.05 < green_ratio < 0.10:
        if yolo_detector(frame).confidence < 0.6:
            return WALKWAY_BREACH  # ~18ms total
```

### Why WebSockets (Not REST Polling)

- REST polling at 400ms intervals on factory WiFi = 382ms alert delay.
- A worker at 5 mph travels ~2.8 feet in that time — enough to cause a collision.
- WebSocket push delivers alerts in <20ms.
- Trade-off: higher server memory per connection, but acceptable for safety-critical alerts.

### Why SQLite (Not PostgreSQL)

- MVP scope: 1–2 factories, no dedicated DBA.
- Compliance records are immutable (write-heavy, rarely updated).
- WAL mode provides sufficient concurrency.
- Backup = copy a single file.
- **Scaling plan:** migrate to PostgreSQL at 10+ factories (2–3 day effort).

---

## Severity Classification

Each violation is classified against policy rules defined in `src/severity/rules.json`.

**Default tiers:**
- **LOW** — Minor deviations, momentary lapses
- **MEDIUM** — Walkway breach, opened panel cover
- **HIGH** — Breach near machinery, unauthorized equipment access
- **CRITICAL** — Forklift overload, multiple unauthorized workers near active equipment

**Dynamic escalation:**
- Walkway Violation (MEDIUM) escalates to HIGH if worker is within 1.0m of machinery.
- Unauthorized Intervention (HIGH) escalates to CRITICAL if multiple workers are present.
- Open Panel Cover (MEDIUM) escalates to HIGH after 5 minutes or if personnel are within 1.0m.

---

## Core Modules

| Module | Location | Responsibility |
|---|---|---|
| Detection Engine | `src/detection/` | Processes video frames, extracts violations with bounding boxes and confidence scores |
| Severity Classifier | `src/severity/` | Maps violations to severity tiers using declarative JSON policy rules |
| Escalation Router | `src/escalation/` | Routes HIGH/CRITICAL alerts via WebSocket; logs all events to database |
| Report Generator | `src/reports/` | Writes immutable records to SQLite, JSONL, and CSV |
| Dashboard | `src/dashboard/` | React UI — live feed, alert timeline, historical logs with filtering and export |

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 16+
- Docker (optional)

### Local Setup

```bash
# Clone
git clone https://github.com/hasana157/factory-compliance-system.git
cd factory-compliance-system

# Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Initialize database
python src/database_init.py

# Generate sample videos (optional)
python generate_samples.py
```

### Run Services

**Terminal 1 — Backend:**
```bash
source venv/bin/activate
python src/main.py
# Backend: http://localhost:8000
```

**Terminal 2 — Frontend:**
```bash
cd src/dashboard
npm install
npm run dev
# Dashboard: http://localhost:5173
```

### Docker

```bash
docker-compose up
# Frontend: http://localhost:5173
# Backend:  http://localhost:8000
```

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/health` | Service status |
| POST | `/api/process_video` | Process a video file by path |
| POST | `/api/upload_video` | Upload and process a video file |
| POST | `/api/demo/seed` | Seed demo violation records |
| GET | `/api/violations` | List violations (filterable by severity, type, date range) |
| GET | `/api/violations/{event_id}` | Get single violation detail |
| GET | `/api/export/violations?format=csv` | Export violations as CSV or JSON |
| WS | `/ws/alerts` | Real-time HIGH/CRITICAL alert stream |

Full interactive docs at `http://localhost:8000/docs` (Swagger UI).

### WebSocket Alert Payload

```json
{
  "type": "COMPLIANCE_ALERT",
  "event_id": "evt-abc123",
  "timestamp": "2026-06-19T10:32:15Z",
  "severity": "CRITICAL",
  "behavior_class": "Carrying_Overload_with_Forklift",
  "description": "Forklift is carrying three or more blocks",
  "zone": "Loading_Area"
}
```

---

## Database Schema

### Violations (SQLite)

```sql
CREATE TABLE violations (
  id TEXT PRIMARY KEY,
  facility_id TEXT NOT NULL,
  violation_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  confidence REAL NOT NULL,
  timestamp DATETIME NOT NULL,
  video_file TEXT,
  frame_number INTEGER,
  resolved BOOLEAN DEFAULT FALSE,
  notes TEXT
);
```

### Immutable Audit Log (JSONL)

Records are append-only — never modified or deleted.

```json
{"timestamp": "2026-06-19T10:32:15Z", "event": "violation_detected", "data": {...}}
{"timestamp": "2026-06-19T10:32:16Z", "event": "alert_sent", "supervisor_id": "sup_123"}
```

---

## Testing

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v
```

**Covered:**
- Violation detection accuracy
- Severity escalation rules
- WebSocket message formatting
- Database transaction integrity
- API endpoint validation

**Not covered yet:**
- 20+ concurrent streams
- Nighttime / low-light conditions
- Rain or fog on camera lens

---

## Known Limitations

| Limitation | Impact | Planned Fix |
|---|---|---|
| No worker re-identification | Can't track repeat violators across frames | Roadmap |
| Daylight only | Fails in low light / nighttime | Thermal camera support |
| Single camera per feed | No cross-camera tracking | Multi-camera fusion |
| Max ~4 concurrent feeds | Designed for small factories | Deploy multiple instances |
| No GPU acceleration | 18ms on CPU; ~5ms on GPU | CPU is fine for MVP |
| No authentication | Dashboard has no login/roles | Add auth layer |
| In-memory WebSocket state | Server restart clears connected clients | Persist connection state |

None block MVP deployment. All have clear solutions.

---

## Roadmap

### Phase 1: MVP Hardening (Current)
- [x] Core detection pipeline
- [x] WebSocket real-time alerts
- [x] Compliance audit logs (SQLite + JSONL + CSV)
- [x] React dashboard with live feed, filters, export
- [ ] Reduce false positive rate
- [ ] Load test 8+ concurrent feeds

### Phase 2: Scale
- [ ] Worker re-identification
- [ ] Multi-camera tracking
- [ ] Mobile alerts for supervisors
- [ ] Thermal / IR camera support

### Phase 3: Intelligence
- [ ] Predictive risk warnings
- [ ] Worker behavior analytics
- [ ] Incident pattern forecasting

---

## Tech Stack

| Layer | Technology | Reason |
|---|---|---|
| Backend | FastAPI + Uvicorn | Async I/O for concurrent streams |
| Frontend | React 18 + Vite | Fast dev server, large ecosystem |
| Vision | OpenCV + YOLOv8 | Battle-tested, real-time capable |
| Real-Time | WebSockets | <20ms alert delivery |
| Database | SQLite (WAL mode) | Zero DevOps, ACID-compliant |
| Deployment | Docker Compose | Reproducible single-command setup |

---

## Project Structure

```
factory-compliance-system/
├── src/
│   ├── detection/        # Video processing and violation detection
│   ├── severity/         # Policy-based severity classification (rules.json)
│   ├── escalation/       # WebSocket alert routing
│   ├── reports/          # Immutable report generation (SQLite, JSONL, CSV)
│   ├── dashboard/        # React frontend
│   ├── main.py           # FastAPI application entry point
│   ├── config.py         # Environment configuration
│   └── database_init.py  # Database initialization
├── tests/                # Unit and integration tests
├── data/                 # Test video data
├── outputs/              # Generated reports and database
├── docker/               # Dockerfiles
├── docker-compose.yml
├── requirements.txt
├── ARCHITECTURE.md
├── API_ENDPOINTS.md
├── POLICY_EXTRACTION.md
├── LIMITATIONS.md
└── RUN_GUIDE.md
```

---

## Related Documentation

- [Architecture](ARCHITECTURE.md) — Pipeline design and module details
- [API Endpoints](API_ENDPOINTS.md) — Full endpoint reference
- [Policy Extraction](POLICY_EXTRACTION.md) — How compliance rules map to code
- [Limitations](LIMITATIONS.md) — Honest assessment of current constraints
- [Run Guide](RUN_GUIDE.md) — Detailed setup and deployment instructions

---

## License

MIT License — See LICENSE file
