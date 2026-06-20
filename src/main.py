"""FastAPI server for the Factory Compliance System."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Literal

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, File, HTTPException, Query, UploadFile, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from src.config import settings
from src.detection.detector import DetectionEngine
from src.escalation.alert_manager import AlertManager, WebSocketConnectionManager
from src.escalation.router import EscalationRouter, RoutingRule
from src.escalation.websocket_handler import alerts_websocket_endpoint
from src.reports.database import ViolationRepository
from src.reports.export import records_to_csv, records_to_json
from src.reports.generator import ComplianceReportGenerator
from src.severity.classifier import SeverityClassifier


class ProcessVideoRequest(BaseModel):
    video_path: str


# ---------------------------------------------------------------------------
# Startup guard — crash immediately if policy has not been parsed
# ---------------------------------------------------------------------------
if not settings.rules_path.exists():
    raise SystemExit(
        "\n"
        "╔══════════════════════════════════════════════════════════╗\n"
        "║  POLICY NOT PARSED — system cannot start.               ║\n"
        "║  Run the policy parser first:                           ║\n"
        "║  python -m pipeline.parsers.llm_rule_extractor          ║\n"
        "╚══════════════════════════════════════════════════════════╝\n"
    )

settings.ensure_directories()
repository = ViolationRepository(settings.database_path)
generator = ComplianceReportGenerator(repository=repository)
detector = DetectionEngine()
classifier = SeverityClassifier()
ws_manager = WebSocketConnectionManager()
alert_manager = AlertManager(ws_manager)
router = EscalationRouter(alert_manager=alert_manager)

app = FastAPI(
    title="Factory Compliance & Alert Escalation System",
    version="1.0.0",
    description="Detect unsafe factory behaviors, classify severity, and route alerts.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


_SEVERITY_ORDER_PIPELINE = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]


async def run_pipeline(video_path: str) -> list[dict]:
    """Process a video through the detection + severity pipeline.

    Multi-event handling (Task 3.3):
    - All violations are individually classified and routed.
    - A single CONSOLIDATED_ALERT WebSocket message is pushed with the
      highest-severity event to prevent dashboard UI spam.
    """
    detections = detector.process_video(video_path)
    reports: list[dict] = []

    for detection in detections:
        detection_data = detection.to_dict()
        decision = classifier.classify(detection_data)
        action = RoutingRule.action_for_severity(decision.severity.value)
        report = generator.generate(
            detection=detection_data,
            severity=decision.severity.value,
            escalation_action=action,
            rationale=decision.rationale,
        )
        await router.route_report(report)
        reports.append(report.model_dump())

    # Consolidated alert — single WebSocket broadcast with the highest severity
    if len(reports) > 1:
        highest = max(
            reports,
            key=lambda r: _SEVERITY_ORDER_PIPELINE.index(r.get("severity", "LOW")),
        )
        consolidated = {
            "type":           "CONSOLIDATED_ALERT",
            "event_id":       highest.get("event_id", ""),
            "timestamp":      highest.get("timestamp", ""),
            "severity":       highest.get("severity", ""),
            "behavior_class": highest.get("behavior_class", ""),
            "description":    highest.get("event_description", ""),
            "zone":           highest.get("zone", ""),
            "total_events":   len(reports),
            "all_behaviors":  [r.get("behavior_class") for r in reports],
        }
        await ws_manager.broadcast(consolidated)

    return reports


@app.get("/api/health")
async def health_check() -> dict:
    return {"status": "healthy", "service": "factory-compliance-system"}


@app.get("/api/stats")
async def get_stats() -> dict:
    return repository.stats()


@app.post("/api/process_video")
async def process_video(payload: ProcessVideoRequest) -> dict:
    try:
        reports = await run_pipeline(payload.video_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "success", "count": len(reports), "reports": reports}


@app.post("/api/upload_video")
async def upload_video(file: UploadFile = File(...)) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    upload_path = settings.output_dir / "uploads" / Path(file.filename).name
    with upload_path.open("wb") as output:
        shutil.copyfileobj(file.file, output)
    reports = await run_pipeline(str(upload_path))
    return {"status": "success", "count": len(reports), "reports": reports}


@app.post("/api/demo/seed")
async def seed_demo_records() -> dict:
    """Inject pre-canned mock violation records for UI/dashboard testing.

    NOTE: This endpoint never calls the production detection engine.
    It directly inserts known HIGH/CRITICAL records into the database
    so the dashboard can show live flashing behaviour during demos.
    The production /api/process_video endpoint never uses path labels.
    """
    import uuid
    from datetime import datetime, timezone

    mock_events = [
        {
            "event_id": f"demo-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "behavior_class": "Safe_Walkway_Violation",
            "description": "[DEMO] Person detected outside green walkway boundary.",
            "severity": "MEDIUM",
            "zone": "Production_Floor",
            "confidence": 0.87,
            "policy_rule_ref": "Section 3.3.2",
            "escalation_action": "Database log only",
            "rationale": "Walkway violation sourced from WARNING callout (DEMO).",
            "facility_id": "demo-facility",
        },
        {
            "event_id": f"demo-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "behavior_class": "Unauthorized_Intervention",
            "description": "[DEMO] Person without vest interacting with equipment.",
            "severity": "HIGH",
            "zone": "Equipment_Area",
            "confidence": 0.84,
            "policy_rule_ref": "Section 4.3.2",
            "escalation_action": "Database log + real-time dashboard alert",
            "rationale": "Unauthorized intervention sourced from CRITICAL SAFETY NOTICE (DEMO).",
            "facility_id": "demo-facility",
        },
        {
            "event_id": f"demo-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "behavior_class": "Opened_Panel_Cover",
            "description": "[DEMO] Electrical panel cover left open.",
            "severity": "MEDIUM",
            "zone": "Electrical_Panel",
            "confidence": 0.82,
            "policy_rule_ref": "Section 5.2.2",
            "escalation_action": "Database log only",
            "rationale": "Open panel sourced from WARNING callout (DEMO).",
            "facility_id": "demo-facility",
        },
        {
            "event_id": f"demo-{uuid.uuid4().hex[:8]}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "behavior_class": "Carrying_Overload_with_Forklift",
            "description": "[DEMO] Forklift carrying 3+ blocks exceeding policy threshold.",
            "severity": "CRITICAL",
            "zone": "Loading_Area",
            "confidence": 0.90,
            "policy_rule_ref": "Section 6.3.2",
            "escalation_action": "Database log + real-time dashboard alert",
            "rationale": "Overload sourced from CRITICAL SAFETY NOTICE (DEMO).",
            "facility_id": "demo-facility",
        },
    ]

    # Insert into database and broadcast HIGH/CRITICAL events over WebSocket
    for event in mock_events:
        report_data = {
            "event_id": event["event_id"],
            "timestamp": event["timestamp"],
            "clip_id": event.get("clip_id") or "demo_clip",
            "zone": event["zone"],
            "behavior_class": event["behavior_class"],
            "policy_rule_ref": event["policy_rule_ref"],
            "event_description": event.get("event_description") or event.get("description") or "",
            "severity": event["severity"],
            "escalation_action": event["escalation_action"],
            "confidence": event.get("confidence") or 0.0,
            "frame_number": event.get("frame_number") or 0,
            "bounding_box": event.get("bounding_box"),
            "metadata": event.get("metadata") or {},
            "rationale": event.get("rationale") or "",
            "created_at": event.get("created_at") or event["timestamp"]
        }
        repository.insert(report_data)
        if event["severity"] in {"HIGH", "CRITICAL"}:
            await alert_manager.trigger_alert(report_data)

    return {"status": "success", "count": len(mock_events), "reports": mock_events}


@app.get("/api/violations")
async def get_violations(
    severity: str | None = None,
    behavior_class: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[dict]:
    return repository.list(
        severity=severity,
        behavior_class=behavior_class,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )


@app.get("/api/violations/{event_id}")
async def get_violation(event_id: str) -> dict:
    violation = repository.get(event_id)
    if violation is None:
        raise HTTPException(status_code=404, detail="Violation not found")
    return violation


@app.get("/api/export/violations")
async def export_violations(
    format: Literal["csv", "json"] = "csv",
    severity: str | None = None,
    behavior_class: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Response:
    records = repository.list(
        severity=severity,
        behavior_class=behavior_class,
        start_date=start_date,
        end_date=end_date,
        limit=10000,
        offset=0,
    )
    if format == "json":
        return Response(
            records_to_json(records),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=violations.json"},
        )
    return Response(
        records_to_csv(records),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=violations.csv"},
    )


@app.websocket("/ws/alerts")
async def websocket_alerts(websocket: WebSocket) -> None:
    await alerts_websocket_endpoint(websocket, ws_manager)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
    )
