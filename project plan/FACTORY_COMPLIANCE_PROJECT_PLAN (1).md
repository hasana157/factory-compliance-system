# FACTORY COMPLIANCE & ALERT ESCALATION SYSTEM
## Project Plan & Software Requirements Specification (SRS)

**Project Role**: Intern Take-Home Assignment - AI/ML Engineer  
**Evaluation Severity**: HIGH - This determines hiring decision  
**Timeline**: 5-7 days maximum  
**Submission Format**: GitHub Repository + Functional System  

---

# 🎯 EXECUTIVE SUMMARY (For Recruiters)

This document defines what we expect from the intern candidate. The system must demonstrate:
1. **Full-stack AI engineering capability** (vision + backend + frontend)
2. **Production-mindedness** (error handling, logging, structured output)
3. **Policy-to-code translation** (can understand complex requirements)
4. **End-to-end ownership** (all 5 modules functional, not partial work)
5. **Communication clarity** (README + architecture + trade-off decisions)

**Hiring Decision Rubric**: Code submitted will be evaluated on:
- ✅ Does it run? Does it work end-to-end?
- ✅ Is the architecture clear and maintainable?
- ✅ Can I understand their decision-making from the code?
- ✅ Did they document trade-offs and limitations honestly?
- ✅ Is the dashboard functional and usable?
- ✅ Did they meet the exact specification, or cut corners?

---

# 📊 PROJECT STRUCTURE & FOLDER ORGANIZATION

```
factory-compliance-system/
│
├── 📄 README.md                          [CRITICAL: Entry point for evaluators]
├── 📄 ARCHITECTURE.md                    [System design document]
├── 📄 POLICY_EXTRACTION.md               [How you parsed compliance policy]
├── 📄 requirements.txt                   [Python dependencies]
├── 📄 package.json                       [Frontend dependencies]
├── 📄 compliance_policy.pdf              [Copy of provided policy]
├── .gitignore
├── .env.example                          [Template for env vars]
│
├── 🗂️ data/                              [Video dataset directory]
│   ├── train/
│   │   ├── Safe_Walkway/                 [Safe behavior videos]
│   │   ├── Safe_Walkway_Violation/       [Unsafe: person outside green zone]
│   │   ├── Authorized_Intervention/      [Safe: green vest + equipment]
│   │   ├── Unauthorized_Intervention/    [Unsafe: red/no vest + equipment]
│   │   ├── Closed_Panel_Cover/           [Safe: electrical panel closed]
│   │   ├── Opened_Panel_Cover/           [Unsafe: panel left open]
│   │   ├── Safe_Carrying/                [Safe: forklift with ≤2 blocks]
│   │   └── Carrying_Overload_with_Forklift/ [Unsafe: forklift with ≥3 blocks]
│   └── test/
│       └── (same structure)
│
├── 🔧 src/                               [Source code]
│   │
│   ├── 📁 detection/                     [MODULE 1: Detection Engine]
│   │   ├── __init__.py
│   │   ├── detector.py                   [Main detection logic]
│   │   ├── models.py                     [YOLOv8 wrapper + mediapipe]
│   │   ├── utils.py                      [Frame extraction, preprocessing]
│   │   └── config.py                     [Detection thresholds]
│   │
│   ├── 📁 severity/                      [MODULE 2: Severity Categorization]
│   │   ├── __init__.py
│   │   ├── classifier.py                 [Assign LOW/MED/HIGH/CRIT]
│   │   ├── rules.json                    [Severity mapping rules extracted from policy]
│   │   └── context_analyzer.py           [Evaluate context for severity]
│   │
│   ├── 📁 escalation/                    [MODULE 3: Escalation Pipeline]
│   │   ├── __init__.py
│   │   ├── router.py                     [Route events to correct channel]
│   │   ├── alert_manager.py              [Real-time alerts for HIGH/CRIT]
│   │   ├── websocket_handler.py          [WebSocket for live dashboard]
│   │   └── notification_queue.py         [Event queue system]
│   │
│   ├── 📁 reports/                       [MODULE 4: Automated Report Generation]
│   │   ├── __init__.py
│   │   ├── generator.py                  [Auto-generate compliance records]
│   │   ├── schemas.py                    [Pydantic models for reports]
│   │   ├── database.py                   [SQLite ORM setup]
│   │   └── export.py                     [CSV/JSON export functionality]
│   │
│   ├── 📁 dashboard/                     [MODULE 5: Operations Dashboard]
│   │   ├── public/
│   │   │   ├── index.html
│   │   │   └── favicon.ico
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── index.tsx
│   │   │   ├── components/
│   │   │   │   ├── LiveFeedMonitor.tsx    [View A: Live video + detection overlay]
│   │   │   │   ├── AlertTimeline.tsx      [View B: Real-time event stream]
│   │   │   │   ├── HistoricalLog.tsx      [View C: Filtered historical records]
│   │   │   │   ├── AlertNotification.tsx  [HIGH/CRIT flash banner]
│   │   │   │   ├── FilterBar.tsx          [Date + severity + behavior filters]
│   │   │   │   └── ExportButton.tsx       [Download CSV/JSON]
│   │   │   ├── hooks/
│   │   │   │   └── useWebSocket.ts        [Real-time alert listener]
│   │   │   ├── types/
│   │   │   │   └── index.ts               [TypeScript interfaces]
│   │   │   ├── styles/
│   │   │   │   └── App.css
│   │   │   └── utils/
│   │   │       └── formatters.ts          [Date/time/severity formatting]
│   │   ├── package.json
│   │   ├── tsconfig.json
│   │   └── .gitignore
│   │
│   └── main.py                           [FastAPI server entry point]
│
├── 🗂️ outputs/                           [Generated reports & logs]
│   ├── violations.db                     [SQLite database]
│   ├── compliance_reports.json           [Append-only JSON log]
│   ├── compliance_reports.csv            [Append-only CSV audit log]
│   └── exports/                          [User-exported files]
│
├── 🧪 tests/                             [Unit tests - BONUS]
│   ├── test_detection.py
│   ├── test_severity.py
│   └── test_reports.py
│
├── 📚 docs/                              [Additional documentation]
│   ├── API_ENDPOINTS.md                  [FastAPI routes]
│   ├── DETECTION_MODEL_RATIONALE.md      [Why you chose YOLOv8]
│   ├── LIMITATIONS.md                    [Known issues & trade-offs]
│   └── DEMO_VIDEO_SCRIPT.md              [If you record walkthrough]
│
└── 🐳 docker-compose.yml                 [Optional but impressive]
    Dockerfile                            [Containerization]

```

---

# 📋 DETAILED MODULE SPECIFICATIONS

## **MODULE 1: DETECTION ENGINE**
**File**: `src/detection/detector.py`  
**Responsibility**: Video ingestion → Violation detection  
**Input**: Video clip (MP4, 1920×1080, 24fps)  
**Output**: Structured detection records

### **1.1 Functional Requirements**

| Requirement | Implementation | Success Criteria |
|------------|-----------------|------------------|
| Accept video clips | `detector.process_video(video_path: str)` | Processes all 8 behavior classes |
| Frame-by-frame processing | Extract frames @ 24fps, pass to model | ≥95% frame processing success rate |
| Detect 4 unsafe behaviors | YOLOv8 + MediaPipe + custom logic | Detects violations in test clips |
| Localize violations in frame | Bounding boxes + zone inference | Zone accuracy ≥80% |
| Output structured records | Returns list of `DetectionRecord` | All required fields present (clip_id, timestamp, behavior_class, zone) |
| Policy grounding | Detection rules derived from `rules.json` | Observable indicators traceable to policy section |

### **1.2 The 4 Unsafe Behaviors & Detection Strategy**

```json
{
  "Safe_Walkway_Violation": {
    "description": "Person outside green floor markings",
    "observable_indicator": "Person position beyond green boundary",
    "detection_approach": "YOLOv8 person detection + boundary check",
    "policy_section": "Section 3.3.2",
    "frequency": "Highest occurrence",
    "implementation": "Extract green floor mask, check person bounding box overlap"
  },
  
  "Unauthorized_Intervention": {
    "description": "Person touching equipment without green vest",
    "observable_indicator": "Red/black vest OR no vest + equipment interaction",
    "detection_approach": "YOLOv8 for person + vest color detection + MediaPipe for pose",
    "policy_section": "Section 4.3.2",
    "frequency": "Common",
    "implementation": "Detect person + classify vest color (CNN) + detect hand-equipment proximity"
  },
  
  "Opened_Panel_Cover": {
    "description": "Electrical panel left open during operations",
    "observable_indicator": "Panel cover in open position",
    "detection_approach": "State-based detection (not action-based), manual annotation or ML",
    "policy_section": "Section 5.2.2",
    "frequency": "Medium",
    "implementation": "Template matching or YOLOv8 panel detection + open/closed classifier"
  },
  
  "Carrying_Overload_with_Forklift": {
    "description": "Forklift carrying ≥3 blocks",
    "observable_indicator": "Block count on forklift forks ≥3",
    "detection_approach": "YOLOv8 to detect blocks + count objects",
    "policy_section": "Section 6.3.2",
    "frequency": "Periodic",
    "implementation": "YOLOv8 block detection, count bounding boxes on forklift"
  }
}
```

### **1.3 Output Format (DetectionRecord)**

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class DetectionRecord:
    clip_id: str                    # e.g., "safe_walkway_violation_001"
    timestamp: float                # Seconds into video where violation detected
    behavior_class: str             # One of 4 unsafe behaviors
    description: str                # Human-readable: "Person detected at coordinates (x,y) outside green zone"
    zone: str                        # e.g., "Zone-1", "Zone-2", "Equipment-Area"
    confidence: float               # Detection confidence 0.0-1.0
    frame_number: int               # Frame index in video
    bounding_box: tuple             # (x1, y1, x2, y2) for localization
    policy_rule_ref: str            # e.g., "Section 3.3.2"
    metadata: dict                  # Additional context (optional)
```

### **1.4 Evaluation Criteria for Module 1**

**What We're Looking For:**
- ✅ Does it process all video formats correctly?
- ✅ Does it detect violations in provided test clips?
- ✅ Are detections traceable to policy rules?
- ✅ Is code organized and maintainable?
- ✅ Are limitations documented?

**Red Flags:**
- ❌ Hardcoded behavior classes instead of reading from rules.json
- ❌ No frame-by-frame processing (lazy evaluation)
- ❌ Detection not grounded in policy
- ❌ No error handling for corrupted videos

---

## **MODULE 2: SEVERITY CATEGORIZATION MATRIX**
**File**: `src/severity/classifier.py`  
**Responsibility**: Assign risk tier to detected violations  
**Input**: DetectionRecord from Module 1  
**Output**: Same record with severity tier + rationale

### **2.1 Severity Tier Mapping (Extracted from Policy)**

```json
{
  "Safe_Walkway_Violation": {
    "default_severity": "MEDIUM",
    "escalation_rules": [
      {
        "condition": "Person within 1 meter of active machinery",
        "new_severity": "HIGH",
        "rationale": "Immediate proximity to hazard"
      },
      {
        "condition": "Person outside zone during forklift operation",
        "new_severity": "HIGH",
        "rationale": "Concurrent vehicle and pedestrian hazard"
      }
    ],
    "policy_signals": "WARNING callout - highest frequency behavior",
    "tier_justification": "Frequently observed but not immediately critical; escalates with proximity"
  },
  
  "Unauthorized_Intervention": {
    "default_severity": "HIGH",
    "escalation_rules": [
      {
        "condition": "Multiple unauthorized personnel on same equipment",
        "new_severity": "CRITICAL",
        "rationale": "Increased injury risk"
      }
    ],
    "policy_signals": "CRITICAL SAFETY NOTICE",
    "tier_justification": "Direct manipulation without clearance = high injury risk"
  },
  
  "Opened_Panel_Cover": {
    "default_severity": "MEDIUM",
    "escalation_rules": [
      {
        "condition": "Panel left open for >5 minutes",
        "new_severity": "HIGH",
        "rationale": "Extended exposure risk"
      }
    ],
    "policy_signals": "WARNING callout - electrical hazard",
    "tier_justification": "State-based hazard; escalates with duration"
  },
  
  "Carrying_Overload_with_Forklift": {
    "default_severity": "CRITICAL",
    "escalation_rules": [],
    "policy_signals": "CRITICAL SAFETY NOTICE - explicit threshold violation",
    "tier_justification": "Unambiguous: 3+ blocks = overload per policy Section 6.2; vehicle instability hazard"
  }
}
```

### **2.2 Tier Definitions & Routing Logic**

| Tier | Criteria | Example | Route |
|------|----------|---------|-------|
| **LOW** | State issue, no personnel proximity, observational | Opened panel with no one nearby | DB log only |
| **MEDIUM** | Behavior deviation, personnel present but safe distance | Safe walkway violation in side area | DB log only |
| **HIGH** | Active unsafe behavior, concurrent personnel, injury possible | Person in equipment zone during forklift movement | DB log + Real-time alert |
| **CRITICAL** | Immediate danger, direct injury risk, or explicit policy maximum | Forklift overload, unauthorized intervening on active equipment | DB log + Real-time alert + Dashboard flash |

### **2.3 Context Analyzer Logic**

```python
class ContextAnalyzer:
    """
    Enriches severity assignment with contextual analysis.
    Called by classifier to determine if default severity should escalate.
    """
    
    def analyze(self, detection: DetectionRecord, frame: np.ndarray) -> str:
        """
        Input: DetectionRecord, current video frame
        Output: Adjusted severity tier
        
        Logic:
        1. Check default severity for behavior_class
        2. Analyze frame context:
           - Proximity to other hazards
           - Personnel count in violation zone
           - Equipment operational state
           - Time-based factors (duration of state)
        3. Apply escalation rules if conditions met
        4. Return final severity
        """
        
        # Example: Unauthorized intervention + multiple people = CRITICAL
        if detection.behavior_class == "Unauthorized_Intervention":
            personnel_count = self._count_personnel_in_frame(frame)
            if personnel_count > 1:
                return "CRITICAL"
        
        # Example: Panel left open for extended duration = escalate to HIGH
        if detection.behavior_class == "Opened_Panel_Cover":
            duration_open = self._estimate_open_duration(detection)
            if duration_open > 300:  # 5 minutes
                return "HIGH"
        
        return self._get_default_severity(detection.behavior_class)
```

### **2.4 Evaluation Criteria for Module 2**

**What We're Looking For:**
- ✅ Severity assignment logic is justified from policy language
- ✅ Escalation rules are documented (not arbitrary)
- ✅ Context analyzer adds value without over-engineering
- ✅ Clear mapping between policy signals (WARNING vs CRITICAL NOTICE) and tiers

**Red Flags:**
- ❌ Random severity assignments
- ❌ No policy grounding in code comments
- ❌ Severity never changes (all CRITICAL or all MEDIUM)

---

## **MODULE 3: ESCALATION PIPELINE**
**File**: `src/escalation/router.py`  
**Responsibility**: Route violations to correct channels based on severity  
**Input**: Detection + Severity record  
**Output**: Database entry + Alert (if HIGH/CRITICAL)

### **3.1 Routing Rules (Mandatory)**

```
Severity: LOW / MEDIUM
├─ Action: Persistent database log
├─ Implementation: Insert into SQLite
└─ No real-time notification

Severity: HIGH / CRITICAL
├─ Action: Persistent database log + Real-time alert
├─ DB: Insert into SQLite
└─ Alert: 
    ├─ Dashboard WebSocket push
    ├─ Visual notification (flash/banner)
    └─ Optional: System beep/sound
```

### **3.2 Alert Manager Implementation**

```python
class AlertManager:
    """
    Manages real-time alerts for HIGH/CRITICAL violations.
    Pushes to dashboard via WebSocket.
    """
    
    def __init__(self, websocket_manager):
        self.ws_manager = websocket_manager
        self.alert_queue = asyncio.Queue()
    
    async def trigger_alert(self, violation_record: dict, severity: str):
        """
        HIGH/CRITICAL violations trigger immediate alerts.
        Format: JSON message pushed to all connected dashboard clients.
        """
        
        if severity in ["HIGH", "CRITICAL"]:
            alert_payload = {
                "type": "COMPLIANCE_ALERT",
                "severity": severity,
                "behavior_class": violation_record["behavior_class"],
                "description": violation_record["event_description"],
                "timestamp": datetime.now().isoformat(),
                "flash_duration_ms": 3000 if severity == "HIGH" else 5000
            }
            
            # Push to all connected dashboard clients
            await self.ws_manager.broadcast(alert_payload)
            
            # Log to alert queue for audit trail
            await self.alert_queue.put(alert_payload)
```

### **3.3 WebSocket Handler**

```python
# FastAPI WebSocket endpoint
@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Listen for alerts from AlertManager
            alert = await alert_manager.alert_queue.get()
            await websocket.send_json(alert)
    except WebSocketDisconnect:
        pass
```

### **3.4 Evaluation Criteria for Module 3**

**What We're Looking For:**
- ✅ Correct routing logic (LOW/MED → DB only; HIGH/CRIT → alert + DB)
- ✅ Real-time alert mechanism is functional (WebSocket or similar)
- ✅ No alerts lost; queue is persistent
- ✅ Can handle concurrent violations

**Red Flags:**
- ❌ Alerts not actually reaching dashboard
- ❌ All violations trigger alerts (doesn't respect routing rules)
- ❌ No audit trail of alerts sent

---

## **MODULE 4: AUTOMATED REPORT GENERATION**
**File**: `src/reports/generator.py`  
**Responsibility**: Auto-generate immutable compliance records  
**Input**: Detection + Severity + Escalation data  
**Output**: Structured records (DB + JSON + CSV)

### **4.1 Required Report Fields (Non-Negotiable)**

```python
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class SeverityEnum(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class ComplianceReport(BaseModel):
    event_id: str                   # UUID - unique identifier for this event
    timestamp: str                  # ISO 8601, e.g., "2024-01-15T10:45:00Z"
    clip_id: str                    # Source video filename
    zone: str                        # Facility zone where detected
    behavior_class: str             # One of 4 unsafe behaviors (from policy)
    policy_rule_ref: str            # Section reference, e.g., "Section 3.3.2"
    event_description: str          # Human-readable narrative of observation
    severity: SeverityEnum          # LOW / MEDIUM / HIGH / CRITICAL
    escalation_action: str          # "Logged to DB" or "Real-time alert triggered + DB log"
    
    # Additional fields (optional but recommended)
    confidence: float               # Detection confidence 0.0-1.0
    frame_number: int              # Frame index where detected
    bounding_box: tuple            # Localization (x1, y1, x2, y2)
    created_at: datetime           # System timestamp when record generated
    
    class Config:
        json_schema_extra = {
            "example": {
                "event_id": "evt-2024-001-abc123",
                "timestamp": "2024-01-15T10:45:00Z",
                "clip_id": "safe_walkway_violation_001.mp4",
                "zone": "Zone-1",
                "behavior_class": "Safe_Walkway_Violation",
                "policy_rule_ref": "Section 3.3.2",
                "event_description": "Person detected at pixel coordinates (850, 420) moving outside green-marked walkway boundaries toward equipment zone. Proximity to machinery hazard.",
                "severity": "MEDIUM",
                "escalation_action": "Logged to DB",
                "confidence": 0.94,
                "frame_number": 42,
                "bounding_box": [800, 380, 900, 480]
            }
        }
```

### **4.2 Output Formats**

**Format 1: SQLite Database** (Primary storage)
```sql
CREATE TABLE compliance_violations (
    event_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    clip_id TEXT NOT NULL,
    zone TEXT NOT NULL,
    behavior_class TEXT NOT NULL,
    policy_rule_ref TEXT NOT NULL,
    event_description TEXT NOT NULL,
    severity TEXT NOT NULL,
    escalation_action TEXT NOT NULL,
    confidence REAL,
    frame_number INTEGER,
    bounding_box TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_timestamp ON compliance_violations(timestamp);
CREATE INDEX idx_severity ON compliance_violations(severity);
CREATE INDEX idx_behavior_class ON compliance_violations(behavior_class);
```

**Format 2: JSON Log** (Append-only, human-readable)
```json
{"event_id": "evt-001", "timestamp": "2024-01-15T10:45:00Z", ...}
{"event_id": "evt-002", "timestamp": "2024-01-15T10:46:00Z", ...}
```

**Format 3: CSV Audit Log** (Exportable, spreadsheet-friendly)
```csv
event_id,timestamp,clip_id,zone,behavior_class,policy_rule_ref,event_description,severity,escalation_action
evt-001,2024-01-15T10:45:00Z,safe_walkway_violation_001.mp4,Zone-1,Safe_Walkway_Violation,Section 3.3.2,...,MEDIUM,Logged to DB
```

### **4.3 Report Generator Implementation**

```python
class ComplianceReportGenerator:
    """
    Automatically generates immutable compliance records.
    Writes to DB, JSON, and CSV simultaneously.
    """
    
    def __init__(self, db_path: str, json_log_path: str, csv_log_path: str):
        self.db = SQLiteDB(db_path)
        self.json_log = json_log_path
        self.csv_log = csv_log_path
    
    def generate(self, detection: DetectionRecord, severity: str, escalation_action: str) -> ComplianceReport:
        """
        Generate a compliance report from detection data.
        Automatically persists to all storage formats.
        """
        
        report = ComplianceReport(
            event_id=self._generate_event_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            clip_id=detection.clip_id,
            zone=detection.zone,
            behavior_class=detection.behavior_class,
            policy_rule_ref=detection.policy_rule_ref,
            event_description=detection.description,
            severity=severity,
            escalation_action=escalation_action,
            confidence=detection.confidence,
            frame_number=detection.frame_number,
            bounding_box=detection.bounding_box,
            created_at=datetime.utcnow()
        )
        
        # Write to SQLite
        self.db.insert_violation(report)
        
        # Append to JSON log
        with open(self.json_log, "a") as f:
            f.write(report.model_dump_json() + "\n")
        
        # Append to CSV log
        if not os.path.exists(self.csv_log):
            self._write_csv_header()
        with open(self.csv_log, "a") as f:
            f.write(self._format_csv_row(report) + "\n")
        
        return report
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID: evt-YYYY-MM-DD-HHMMSS-RANDOM"""
        now = datetime.utcnow()
        random_suffix = secrets.token_hex(4)
        return f"evt-{now.strftime('%Y%m%d%H%M%S')}-{random_suffix}"
```

### **4.4 Evaluation Criteria for Module 4**

**What We're Looking For:**
- ✅ Every violation generates a report automatically (no manual entry)
- ✅ Reports contain all required fields
- ✅ Data persisted in all 3 formats (DB + JSON + CSV)
- ✅ Reports are immutable (append-only, no updates/deletes)
- ✅ UUID generation is correct (truly unique)
- ✅ Timestamps are ISO 8601 formatted

**Red Flags:**
- ❌ Missing required fields (especially policy_rule_ref)
- ❌ Reports written only to 1 format
- ❌ Manual entry of report data
- ❌ Timestamps in non-standard format
- ❌ Duplicate event IDs

---

## **MODULE 5: OPERATIONS DASHBOARD**
**File**: `src/dashboard/`  
**Responsibility**: Provide GUI for monitoring, alerts, and export  
**Input**: Real-time events from backend + historical data  
**Output**: Interactive React web app

### **5.1 Three Required Views**

#### **VIEW A: Live Feed Monitor**
**Purpose**: Show camera feed + detection overlays in real-time

**Components**:
```tsx
// LiveFeedMonitor.tsx
<div className="live-feed-container">
  <div className="video-player">
    {/* Video iframe or canvas */}
    <video src={currentClip} autoPlay />
    
    {/* Overlay: Detection bounding boxes */}
    <svg className="detection-overlay">
      {detections.map(det => (
        <rect
          x={det.bbox[0]} y={det.bbox[1]}
          width={det.bbox[2]-det.bbox[0]}
          height={det.bbox[3]-det.bbox[1]}
          stroke={getSeverityColor(det.severity)}
          strokeWidth="3"
          fill="none"
        />
      ))}
    </svg>
  </div>
  
  {/* Status indicator */}
  <div className={`status-badge ${currentStatus}`}>
    {currentStatus === 'VIOLATION' ? '⚠️ VIOLATION DETECTED' : '✓ COMPLIANT'}
  </div>
  
  {/* Severity legend */}
  <div className="severity-legend">
    <span className="low">LOW</span>
    <span className="medium">MEDIUM</span>
    <span className="high">HIGH</span>
    <span className="critical">CRITICAL ⚡</span>
  </div>
</div>
```

**Functional Requirements**:
- ✅ Displays video clip with frame-by-frame detection
- ✅ Bounding boxes drawn in real-time
- ✅ Color-coded by severity (GREEN=compliant, YELLOW=low, ORANGE=medium, RED=high, DARK_RED=critical)
- ✅ Status badge updates as violations detected
- ✅ Optional: Play/pause/seek controls

**Evaluation**:
- Does the overlay match the actual detections?
- Can you see which frame had violations?
- Is the status badge accurate?

---

#### **VIEW B: Alert Timeline Stream**
**Purpose**: Chronological list of all detected violations in real-time

**Components**:
```tsx
// AlertTimeline.tsx
<div className="alert-timeline">
  {/* High/Critical alerts appear at top with flash animation */}
  {alerts
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .map(alert => (
      <div
        key={alert.event_id}
        className={`alert-item alert-${alert.severity}`}
        style={alert.severity === 'CRITICAL' ? { animation: 'flash 0.5s' } : {}}
      >
        <div className="alert-header">
          <span className="time">{formatTime(alert.timestamp)}</span>
          <span className="severity-badge">{alert.severity}</span>
          <span className="behavior">{alert.behavior_class}</span>
        </div>
        <div className="alert-body">
          <p>{alert.event_description}</p>
          <small>Zone: {alert.zone} | Clip: {alert.clip_id}</small>
        </div>
      </div>
    ))}
</div>
```

**Functional Requirements**:
- ✅ Real-time streaming of violations (as they're detected)
- ✅ Newest violations at top
- ✅ Color-coded by severity
- ✅ HIGH/CRITICAL show animated flash/banner notification
- ✅ Shows full event details (timestamp, zone, behavior, description)

**Real-Time Alert Visual (for HIGH/CRITICAL)**:
```tsx
// AlertNotification.tsx (appears as overlay)
{showAlert && (
  <div className="alert-banner alert-critical" style={{
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    height: '80px',
    backgroundColor: '#d32f2f',
    color: 'white',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '24px',
    fontWeight: 'bold',
    zIndex: 1000,
    animation: 'flashPulse 1s infinite'
  }}>
    🚨 CRITICAL SAFETY ALERT: {alertData.behavior_class}
  </div>
)}
```

**Evaluation**:
- Does alert appear immediately when violation detected?
- Does flash animation work?
- Can you read the event details?

---

#### **VIEW C: Historical Log & Export**
**Purpose**: Search, filter, and export historical compliance records

**Components**:
```tsx
// HistoricalLog.tsx
<div className="historical-log">
  {/* Filters */}
  <div className="filter-panel">
    <div className="filter-group">
      <label>Date Range</label>
      <input type="date" value={startDate} onChange={setStartDate} />
      <input type="date" value={endDate} onChange={setEndDate} />
    </div>
    
    <div className="filter-group">
      <label>Severity</label>
      <select multiple onChange={setSeverityFilter}>
        <option value="LOW">LOW</option>
        <option value="MEDIUM">MEDIUM</option>
        <option value="HIGH">HIGH</option>
        <option value="CRITICAL">CRITICAL</option>
      </select>
    </div>
    
    <div className="filter-group">
      <label>Behavior Class</label>
      <select multiple onChange={setBehaviorFilter}>
        <option value="Safe_Walkway_Violation">Safe Walkway Violation</option>
        <option value="Unauthorized_Intervention">Unauthorized Intervention</option>
        <option value="Opened_Panel_Cover">Opened Panel Cover</option>
        <option value="Carrying_Overload_with_Forklift">Forklift Overload</option>
      </select>
    </div>
    
    <button onClick={applyFilters}>Apply Filters</button>
    <button onClick={resetFilters}>Reset</button>
  </div>
  
  {/* Table view */}
  <table className="log-table">
    <thead>
      <tr>
        <th>Event ID</th>
        <th>Timestamp</th>
        <th>Behavior Class</th>
        <th>Severity</th>
        <th>Zone</th>
        <th>Description</th>
        <th>Policy Ref</th>
      </tr>
    </thead>
    <tbody>
      {filteredRecords.map(record => (
        <tr key={record.event_id}>
          <td>{record.event_id}</td>
          <td>{formatDateTime(record.timestamp)}</td>
          <td>{record.behavior_class}</td>
          <td className={`severity-${record.severity}`}>{record.severity}</td>
          <td>{record.zone}</td>
          <td className="description">{record.event_description}</td>
          <td>{record.policy_rule_ref}</td>
        </tr>
      ))}
    </tbody>
  </table>
  
  {/* Export buttons */}
  <div className="export-section">
    <button onClick={() => exportAs('csv')}>📥 Download as CSV</button>
    <button onClick={() => exportAs('json')}>📥 Download as JSON</button>
    <button onClick={() => exportAs('pdf')}>📥 Download as PDF Report</button>
  </div>
  
  {/* Pagination */}
  <div className="pagination">
    <button onClick={previousPage} disabled={currentPage === 1}>← Previous</button>
    <span>Page {currentPage} of {totalPages}</span>
    <button onClick={nextPage} disabled={currentPage === totalPages}>Next →</button>
  </div>
</div>
```

**Functional Requirements**:
- ✅ Filter by date range
- ✅ Filter by severity (multi-select)
- ✅ Filter by behavior class (multi-select)
- ✅ Display full historical records in table
- ✅ Export filtered or full log as CSV/JSON
- ✅ Pagination for large datasets

**Export API Endpoint**:
```python
@app.get("/api/export/violations")
async def export_violations(
    format: str = "csv",  # csv, json
    severity: str = None,
    behavior_class: str = None,
    start_date: str = None,
    end_date: str = None
):
    """
    Export compliance records with optional filters.
    Returns file for download.
    """
    records = query_database_with_filters(severity, behavior_class, start_date, end_date)
    
    if format == "csv":
        return CSVResponse(records)
    elif format == "json":
        return JSONResponse(records)
```

**Evaluation**:
- Can you filter by all criteria?
- Does export contain the correct records?
- Is the data properly formatted?

---

### **5.2 Dashboard Technical Architecture**

```
Frontend Stack:
├── React 18 (TypeScript)
├── TailwindCSS (styling)
├── Axios (HTTP client)
├── Socket.io-client (WebSocket for real-time alerts)
├── React Router (navigation)
└── React Query (data fetching)

Backend API (FastAPI):
├── GET  /api/violations          [Fetch historical violations]
├── GET  /api/violations/{id}     [Single violation details]
├── GET  /api/stats               [Dashboard statistics]
├── POST /api/export/violations   [Export with filters]
├── WS   /ws/alerts               [WebSocket for real-time]
└── GET  /api/health              [Health check]
```

### **5.3 Dashboard UI/UX Design Specifications**

#### **Color Scheme**
```css
:root {
  --color-compliant: #4caf50;        /* Green */
  --color-low: #ffc107;              /* Yellow */
  --color-medium: #ff9800;           /* Orange */
  --color-high: #f44336;             /* Red */
  --color-critical: #8b0000;         /* Dark Red */
  --bg-primary: #f5f5f5;
  --bg-secondary: #ffffff;
  --text-primary: #333333;
  --text-secondary: #666666;
}
```

#### **Typography**
```css
h1 { font-size: 28px; font-weight: 700; }
h2 { font-size: 20px; font-weight: 600; }
body { font-size: 14px; font-weight: 400; }
code { font-family: 'Courier New', monospace; }
```

#### **Responsive Breakpoints**
```css
@media (max-width: 768px) {
  /* Stack views vertically */
  .dashboard-grid { grid-template-columns: 1fr; }
}
```

#### **Component Spacing**
```css
.container { padding: 16px; }
.section { margin-bottom: 24px; }
.item { margin-bottom: 12px; }
```

#### **Animation**
```css
@keyframes flash {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@keyframes slideIn {
  from { transform: translateY(-100%); }
  to { transform: translateY(0); }
}
```

### **5.4 Evaluation Criteria for Module 5**

**What We're Looking For**:
- ✅ All 3 views are functional and accessible
- ✅ Real-time alerts work (flash on CRITICAL)
- ✅ Filters work correctly
- ✅ Export produces valid CSV/JSON
- ✅ Dashboard is responsive (works on mobile)
- ✅ No console errors

**Red Flags**:
- ❌ Dashboard is blank / data not loading
- ❌ Alerts don't appear
- ❌ Filters don't work
- ❌ Export is broken
- ❌ UI is broken / unusable
- ❌ No WebSocket connection to backend

---

# 🎯 TARGETED METRICS & SUCCESS CRITERIA

These are the metrics we use to decide if you get hired.

## **Functional Completeness Score (50%)**

| Metric | Target | Excellent | Good | Poor |
|--------|--------|-----------|------|------|
| Module 1: Detection | All 4 behaviors detected | Detects in ≥80% of test clips | Detects some violations | Crashes/errors |
| Module 2: Severity | Correct tier assignment | All assignments match policy logic | Most assignments logical | Random tiers |
| Module 3: Escalation | Correct routing | HIGH/CRIT trigger alerts; LOW/MED log only | Mostly correct | Alerts always/never trigger |
| Module 4: Reports | Complete records | All fields present, persisted in all formats | Some fields missing | No reports generated |
| Module 5: Dashboard | All 3 views working | Real-time updates, filters, export work | Views display but slow | Views blank or broken |

## **Code Quality Score (25%)**

| Metric | Target | Excellent | Good | Poor |
|--------|--------|-----------|------|------|
| Architecture | Modular, traceable | Clear separation of concerns, easy to follow | Some coupling | Monolithic spaghetti |
| Error Handling | Graceful failures | Try-catch around all I/O, meaningful errors | Some error handling | No error handling |
| Documentation | Clear intent | Docstrings, comments, README detailed | Basic comments | No documentation |
| Testing | Critical paths covered | Unit tests for core logic | No tests | Tests exist but useless |
| Git History | Logical commits | Clear, descriptive commit messages | Generic messages | Single giant commit |

## **Communication & Honesty (15%)**

| Metric | Target | Excellent | Good | Poor |
|--------|--------|-----------|------|------|
| README | Comprehensive | Explains architecture, parsing, severity, limitations | Basic setup instructions | Missing/incomplete |
| Trade-offs | Honest | Explicitly states what you cut corners on and why | Mentions some limitations | Hides problems |
| Policy Grounding | Traceable | Every detection linked to policy section | Most linked | No policy references |
| Limitations | Known issues documented | "Detection fails on X because Y; future work: Z" | Mentions some issues | Claims perfect system |

## **Initiative & Polish (10%)**

| Metric | Target | Excellence | Good | Poor |
|--------|--------|-----------|------|------|
| Demo Video | Walkthrough | Clear, organized narration, shows all features | Shows system working | No demo |
| Tests | Unit tests | >80% code coverage on core modules | Some test coverage | No tests |
| Deployment | Bonus | Containerized, can run in one command | Instructions clear but manual | Hard to set up |
| UX | Polish | Dashboard responsive, intuitive | Functional but basic | Hard to use |

---

# 📝 README.md REQUIREMENTS

Your README is the **first thing we evaluate**. It must contain these sections (in order):

```markdown
# Factory Compliance & Alert Escalation System

## Overview
[2-3 sentences explaining what the system does]

## Getting Started
### Prerequisites
- Python 3.9+
- Node.js 16+
- npm or yarn
- Kaggle account (for dataset download)

### Installation
1. Clone this repository
2. Download dataset from Kaggle [link]
3. Extract to `data/` directory
4. Install Python dependencies: `pip install -r requirements.txt`
5. Install frontend: `cd src/dashboard && npm install`

### Running the System
1. Start backend: `python src/main.py`
2. Start frontend: `cd src/dashboard && npm start`
3. Access dashboard: http://localhost:3000

## Architecture Overview
[Diagram or detailed explanation of the 5 modules and how they interact]

### Module 1: Detection Engine
- Model: YOLOv8 + MediaPipe
- Approach: [1-2 sentences explaining detection strategy]
- Known Limitations: [Be honest: what doesn't work well?]

### Module 2: Severity Categorization
- Mapping: [Show the severity table]
- Policy Grounding: [How you mapped policy sections to severity tiers]

### Module 3: Escalation Pipeline
- Routing Rules: [LOW/MED → DB log; HIGH/CRIT → alert + DB log]
- Implementation: [FastAPI WebSocket, async queue]

### Module 4: Report Generation
- Formats: JSON, CSV, SQLite
- Schema: [Link to ComplianceReport class]

### Module 5: Dashboard
- Views: Live Feed Monitor, Alert Timeline, Historical Log
- Technologies: React 18, TypeScript, TailwindCSS
- Real-time: WebSocket for live alerts

## Policy Parsing Approach
[This is critical: explain in detail how you extracted the 4 behaviors and severity mapping from the PDF]

Example:
"I read Section 3.3.2 which defines 'Safe Walkway Violation' as 'movement or presence outside the boundaries of the green-marked Designated Safe Walkway.' From this, I derived the observable indicator: person_position > boundary. I also noted the WARNING callout indicating highest-frequency behavior, which I mapped to MEDIUM severity (not CRITICAL)."

## Detection Model Rationale
[Why did you choose YOLOv8? Why not fine-tune? Be honest about trade-offs]

Example:
"I chose YOLOv8 because:
1. Pre-trained on COCO, good person detection out-of-the-box
2. Fast inference (suitable for real-time)
3. Time constraint: fine-tuning would take days
Limitation: struggles with occluded pedestrians in crowded frames"

## Limitations & Known Issues
[This is where honesty matters. What doesn't work?]

Example:
- "Safe Walkway Violation detection assumes green floor markings are visible in frame; fails if markings are obscured"
- "Vest color classification has ~78% accuracy on test set; red-black vs green confusion possible"
- "Opened Panel Cover detection requires clear panel visibility; fails on side-angle views"
- "Dashboard alerts sometimes lag 1-2 seconds behind actual detection"

## Future Improvements
[What would you do with more time?]

Example:
- Fine-tune YOLOv8 on the provided dataset (currently using pre-trained COCO)
- Implement 3D pose tracking for unauthorized intervention detection
- Add audio alerts for critical violations
- Build ML model for automatic policy extraction from PDF

## Testing
[How to run tests]
```bash
python -m pytest tests/
```

## File Structure
[Show the folder tree]

## API Documentation
[Link to docs or show key endpoints]

## Demo
[Link to YouTube video or GIF showing system in action]

## Author
[Your name, GitHub, LinkedIn]

## License
[MIT, Apache 2.0, etc.]
```

---

# ✅ SUBMISSION CHECKLIST

Before pushing to GitHub, verify **ALL** of these:

```
REPOSITORY SETUP
☐ GitHub repo is public (or invite reviewers)
☐ .gitignore excludes: __pycache__, .env, outputs/*, node_modules/
☐ Descriptive repo description
☐ main branch contains latest working code
☐ No sensitive data (API keys, credentials)

CODE STRUCTURE
☐ All 5 modules present and organized in src/
☐ requirements.txt has all dependencies
☐ package.json has all frontend dependencies
☐ .env.example provided (with dummy values)
☐ Code runs without manual fixes

MODULES FUNCTIONAL
☐ Module 1: Detection engine processes videos
☐ Module 2: Severity assigned logically
☐ Module 3: Routing follows rules (LOW/MED vs HIGH/CRIT)
☐ Module 4: Reports auto-generated in all 3 formats
☐ Module 5: Dashboard loads, shows data, filters work, export works

DOCUMENTATION
☐ README.md (all sections complete)
☐ ARCHITECTURE.md or similar (system design)
☐ POLICY_EXTRACTION.md (how you parsed compliance policy)
☐ API_ENDPOINTS.md (FastAPI routes documented)
☐ LIMITATIONS.md (honest about what doesn't work)
☐ DEMO_VIDEO_SCRIPT.md (if applicable)

DATA
☐ Data directory structure matches spec
☐ Download instructions in README (Kaggle link)
☐ compliance_policy.pdf copied to root

EXECUTION
☐ `pip install -r requirements.txt` works without errors
☐ `python src/main.py` starts backend without crashes
☐ `cd src/dashboard && npm install && npm start` starts frontend
☐ Dashboard loads at http://localhost:3000
☐ Dashboard shows data (not blank)
☐ Can filter + export records
☐ Sample violations detected and displayed

QUALITY
☐ No console errors or warnings
☐ Code is readable (good variable names, comments)
☐ No hardcoded paths (use relative paths)
☐ No secrets in code (use .env)
☐ Git history shows logical commits (not 1 giant commit)

HONESTY
☐ README acknowledges limitations (be realistic)
☐ Trade-offs explained (why you chose tech X over Y)
☐ Known issues documented (what doesn't work)
☐ No overstating capabilities
☐ Code quality matches claims
```

---

# 🔴 RED FLAGS (Automatic Fail)

If any of these are true, you will **not** be hired:

1. ❌ **System doesn't run** — Code is broken, won't start, crashes on first violation
2. ❌ **Modules missing** — Only implemented 3/5 modules, submitted incomplete work
3. ❌ **No dashboard** — Submitted backend only, no UI
4. ❌ **Hardcoded behavior classes** — Detection rules are hardcoded strings instead of derived from policy
5. ❌ **No reports generated** — Violations detected but no records created
6. ❌ **Routing logic wrong** — All violations trigger alerts (no distinction by severity)
7. ❌ **Plagiarism** — Code is copy-pasted from tutorials without understanding
8. ❌ **No documentation** — README is missing or incomplete
9. ❌ **Dishonest limitations** — Hides problems or claims 100% accuracy
10. ❌ **Git history hidden** — Single giant commit with no meaningful messages

---

# 🟢 GREEN FLAGS (Strong Hire Signal)

If you do **any** of these, you stand out:

1. ✅ **Demo video** — Shows yourself walking through the system, explaining decisions
2. ✅ **Unit tests** — Test critical functions (detection, severity, report generation)
3. ✅ **Containerized** — `docker-compose up` starts entire system
4. ✅ **Error handling** — Graceful failures, meaningful error messages
5. ✅ **Performance metrics** — FPS, detection latency, database query times
6. ✅ **Fine-tuned model** — Trained YOLOv8 on provided dataset (even if partial)
7. ✅ **Advanced features** — Email alerts, Slack notifications, multi-user dashboard
8. ✅ **Database optimization** — Indexes, query optimization, efficient storage
9. ✅ **Frontend polish** — Responsive design, dark mode, accessible (WCAG)
10. ✅ **Honest reflection** — Explains what you'd do differently if rebuilding

---

# 📊 EVALUATION MEETING NOTES

When we review your submission, here's what we discuss:

```
FIRST 5 MINUTES: Can we run it?
├─ Clone repo → ✓ or ✗
├─ Install deps → ✓ or ✗
├─ Start backend → ✓ or ✗
├─ Start frontend → ✓ or ✗
└─ Dashboard loads → ✓ or ✗

NEXT 10 MINUTES: Does it work?
├─ Upload test video → Does it detect violations?
├─ Check dashboard → Is data showing?
├─ Trigger HIGH/CRIT violation → Does alert flash?
├─ Test export → Can we download CSV/JSON?
└─ Test filters → Do date/severity/behavior filters work?

ARCHITECTURE REVIEW (15 min):
├─ Read Module 1 code → Is detection logic sound?
├─ Read Module 2 code → Is severity grounded in policy?
├─ Read Module 3 code → Is routing correct?
├─ Read Module 4 code → Are reports complete?
├─ Read Module 5 code → Is dashboard component clean?
└─ Overall → Can we maintain this? Is it scalable?

DOCUMENTATION REVIEW (10 min):
├─ Is README clear?
├─ Did they explain their policy parsing?
├─ Did they acknowledge limitations?
├─ Did they justify tech choices?
└─ Would a new engineer understand this?

FINAL DECISION:
├─ Can I trust this person with backend work? (DB design, error handling)
├─ Can I trust this person with ML pipelines? (Model selection, evaluation)
├─ Can I trust this person with frontend? (User experience, responsiveness)
├─ Will they communicate problems early? (Honest about limitations)
├─ Is code quality interview-ready? (Would they pass code review)
└─ Would I work with them? (Professionalism, documentation, honesty)

HIRING OUTCOMES:
├─ "Hire now" ← System flawless, great communication
├─ "Hire with mentoring" ← Solid fundamentals, needs guidance
├─ "Maybe later" ← Potential but incomplete work
└─ "No hire" ← Broken system, dishonest, or clearly not ready
```

---

# 🚀 FINAL WORDS (From Your Recruiter)

We're not looking for perfection. We're looking for:

1. **Completeness** — You submitted all 5 modules, not 3/5
2. **Functionality** — The system actually works end-to-end
3. **Understanding** — Your code shows you understand the problem
4. **Communication** — You can explain your decisions in the README
5. **Honesty** — You acknowledge what doesn't work and why
6. **Growth** — You suggest how you'd improve it next time

**What will get you hired:**
- Code that runs on Day 1
- Clear README explaining everything
- Honest acknowledgment of trade-offs
- All 5 modules working, even if not perfect

**What will get you rejected:**
- Broken code
- Missing modules
- No dashboard
- Dishonest/overstated capabilities
- Copied code without understanding

---

**Good luck. We're excited to see what you build.** 🎯

Submit this repo link and we'll evaluate you within 24 hours.

```
Expected Timeline:
Day 1-2: Setup + Module 1 (Detection)
Day 2-3: Module 2 (Severity) + Module 3 (Escalation)
Day 4: Module 4 (Reports) + Module 5 (Dashboard basic)
Day 5: Polish, testing, documentation, demo video
Day 6: Final review, push to GitHub
```

**You've got this.** 💪
