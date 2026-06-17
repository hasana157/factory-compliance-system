# QUICK START GUIDE - Code Templates

This guide provides starter code for each of the 5 modules. Copy these into your project and build from here.

---

## SETUP: requirements.txt

```txt
# Core dependencies
fastapi==0.104.1
uvicorn==0.24.0
python-socketio==5.10.0
python-multipart==0.0.6

# Computer Vision
opencv-python==4.8.1.5
ultralytics==8.0.0
mediapipe==0.10.0

# Database & ORM
sqlalchemy==2.0.23
pydantic==2.5.0

# File handling & utilities
python-dotenv==1.0.0
requests==2.31.0

# Data processing
numpy==1.24.3
pandas==2.1.3

# Testing (bonus)
pytest==7.4.3
pytest-asyncio==0.21.1
```

---

## MODULE 1: DETECTION ENGINE

### File: src/detection/detector.py

```python
import cv2
import numpy as np
from ultralytics import YOLO
import mediapipe as mp
from datetime import datetime
from typing import List, Dict, Tuple
import json
import os

class DetectionRecord:
    """Structured output from detector"""
    def __init__(
        self,
        clip_id: str,
        timestamp: float,
        behavior_class: str,
        description: str,
        zone: str,
        confidence: float,
        frame_number: int,
        bounding_box: Tuple[int, int, int, int],
        policy_rule_ref: str,
        metadata: Dict = None
    ):
        self.clip_id = clip_id
        self.timestamp = timestamp
        self.behavior_class = behavior_class
        self.description = description
        self.zone = zone
        self.confidence = confidence
        self.frame_number = frame_number
        self.bounding_box = bounding_box
        self.policy_rule_ref = policy_rule_ref
        self.metadata = metadata or {}
    
    def to_dict(self):
        return {
            "clip_id": self.clip_id,
            "timestamp": self.timestamp,
            "behavior_class": self.behavior_class,
            "description": self.description,
            "zone": self.zone,
            "confidence": self.confidence,
            "frame_number": self.frame_number,
            "bounding_box": self.bounding_box,
            "policy_rule_ref": self.policy_rule_ref,
            "metadata": self.metadata
        }


class DetectionEngine:
    """
    Main detection engine for Module 1.
    
    Detects 4 unsafe behaviors:
    1. Safe_Walkway_Violation
    2. Unauthorized_Intervention
    3. Opened_Panel_Cover
    4. Carrying_Overload_with_Forklift
    """
    
    def __init__(self, rules_path: str = "src/severity/rules.json"):
        """Initialize YOLOv8 and load policy rules"""
        self.model = YOLO("yolov8m.pt")  # Pre-trained YOLOv8
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose()
        
        # Load rules from policy
        with open(rules_path, 'r') as f:
            self.rules = json.load(f)
        
        # Detection thresholds
        self.confidence_threshold = 0.5
    
    def process_video(self, video_path: str) -> List[DetectionRecord]:
        """
        Process entire video clip and detect violations.
        
        Args:
            video_path: Path to MP4 video file
            
        Returns:
            List of DetectionRecord objects
        """
        detections = []
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        clip_id = os.path.basename(video_path).replace('.mp4', '')
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = 0
        
        print(f"Processing video: {video_path}")
        
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Get timestamp in seconds
            timestamp = frame_count / fps
            
            # Run detection on this frame
            frame_detections = self._detect_violations(
                frame, 
                frame_count, 
                clip_id, 
                timestamp
            )
            
            detections.extend(frame_detections)
            frame_count += 1
            
            # Progress indicator
            if frame_count % 30 == 0:
                print(f"  Processed {frame_count} frames...")
        
        cap.release()
        print(f"Total detections: {len(detections)}")
        
        return detections
    
    def _detect_violations(
        self,
        frame: np.ndarray,
        frame_number: int,
        clip_id: str,
        timestamp: float
    ) -> List[DetectionRecord]:
        """
        Detect all violations in a single frame.
        Returns list of DetectionRecord objects.
        """
        detections = []
        
        # Run YOLOv8 inference
        results = self.model(frame, conf=self.confidence_threshold)
        
        # Extract detections
        boxes = results[0].boxes
        
        # DETECTION LOGIC FOR EACH BEHAVIOR CLASS
        
        # 1. Safe_Walkway_Violation
        # Strategy: Detect persons outside green walkway boundaries
        detections.extend(self._detect_walkway_violation(
            frame, boxes, frame_number, clip_id, timestamp
        ))
        
        # 2. Unauthorized_Intervention
        # Strategy: Detect person + not wearing green vest + touching equipment
        detections.extend(self._detect_unauthorized_intervention(
            frame, boxes, frame_number, clip_id, timestamp
        ))
        
        # 3. Opened_Panel_Cover
        # Strategy: Manual template matching or ML (simplified for now)
        detections.extend(self._detect_open_panel(
            frame, frame_number, clip_id, timestamp
        ))
        
        # 4. Carrying_Overload_with_Forklift
        # Strategy: Detect forklift + count blocks on forks
        detections.extend(self._detect_overload(
            frame, boxes, frame_number, clip_id, timestamp
        ))
        
        return detections
    
    def _detect_walkway_violation(
        self, frame, boxes, frame_number, clip_id, timestamp
    ) -> List[DetectionRecord]:
        """Detect person outside green walkway marking"""
        detections = []
        
        # Extract green pixels (walkway boundaries)
        # Simplified: check HSV range for green color
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        lower_green = np.array([35, 40, 40])
        upper_green = np.array([85, 255, 255])
        green_mask = cv2.inRange(hsv, lower_green, upper_green)
        
        # Find person bounding boxes
        for box in boxes:
            if box.cls[0] == 0:  # COCO class 0 = person
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                confidence = float(box.conf[0])
                
                # Check if person is outside green zone
                person_center_y = (y1 + y2) // 2
                green_at_center = green_mask[person_center_y, (x1+x2)//2]
                
                if green_at_center == 0:  # Not in green zone
                    detections.append(DetectionRecord(
                        clip_id=clip_id,
                        timestamp=timestamp,
                        behavior_class="Safe_Walkway_Violation",
                        description=f"Person detected at ({(x1+x2)//2}, {person_center_y}) outside green-marked walkway boundaries",
                        zone="Production_Floor",
                        confidence=confidence,
                        frame_number=frame_number,
                        bounding_box=(x1, y1, x2, y2),
                        policy_rule_ref="Section 3.3.2",
                        metadata={"detected_outside_zone": True}
                    ))
        
        return detections
    
    def _detect_unauthorized_intervention(
        self, frame, boxes, frame_number, clip_id, timestamp
    ) -> List[DetectionRecord]:
        """Detect person without green vest interacting with equipment"""
        detections = []
        
        # TODO: Implement vest color detection
        # 1. Detect person
        # 2. Extract bounding box region
        # 3. Classify vest color (CNN or manual)
        # 4. Check if interacting with equipment
        # 5. If not green vest + equipment interaction = violation
        
        # Placeholder: would require custom trained vest classifier
        # For MVP: can use simple color histogram matching
        
        return detections
    
    def _detect_open_panel(
        self, frame, frame_number, clip_id, timestamp
    ) -> List[DetectionRecord]:
        """Detect electrical panel in open position"""
        detections = []
        
        # TODO: Implement panel detection
        # Strategy 1: Template matching with open panel image
        # Strategy 2: Train YOLO on open/closed panel images
        # For MVP: can hardcode panel location if known
        
        return detections
    
    def _detect_overload(
        self, frame, boxes, frame_number, clip_id, timestamp
    ) -> List[DetectionRecord]:
        """Detect forklift carrying ≥3 blocks"""
        detections = []
        
        # Detect objects and count blocks
        block_count = 0
        forklift_detected = False
        forklift_bbox = None
        
        for box in boxes:
            # Note: YOLO COCO doesn't have specific block class
            # Would need to train custom model or use different approach
            # Placeholder logic:
            
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            # Look for bounding box area that could be blocks on forklift
            # This would require labeled training data
        
        # If ≥3 blocks detected on forklift = violation
        if block_count >= 3 and forklift_detected:
            detections.append(DetectionRecord(
                clip_id=clip_id,
                timestamp=timestamp,
                behavior_class="Carrying_Overload_with_Forklift",
                description=f"Forklift detected carrying {block_count} blocks (threshold: 2)",
                zone="Loading_Area",
                confidence=0.75,  # Placeholder
                frame_number=frame_number,
                bounding_box=forklift_bbox if forklift_bbox else (0, 0, 0, 0),
                policy_rule_ref="Section 6.3.2",
                metadata={"block_count": block_count}
            ))
        
        return detections


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    detector = DetectionEngine()
    
    # Process a single video
    video_path = "data/train/Safe_Walkway_Violation/video_001.mp4"
    detections = detector.process_video(video_path)
    
    # Print results
    for det in detections:
        print(f"{det.behavior_class}: {det.description}")
```

---

## MODULE 2: SEVERITY CATEGORIZATION

### File: src/severity/rules.json

```json
{
  "Safe_Walkway_Violation": {
    "default_severity": "MEDIUM",
    "policy_section": "Section 3.3.2",
    "policy_signal": "WARNING - highest frequency behavior",
    "escalation_rules": [
      {
        "condition": "person_proximity_to_machinery < 1_meter",
        "new_severity": "HIGH",
        "rationale": "Immediate danger zone"
      }
    ]
  },
  
  "Unauthorized_Intervention": {
    "default_severity": "HIGH",
    "policy_section": "Section 4.3.2",
    "policy_signal": "CRITICAL SAFETY NOTICE",
    "escalation_rules": [
      {
        "condition": "personnel_count_on_equipment > 1",
        "new_severity": "CRITICAL",
        "rationale": "Multiple unauthorized personnel = compound hazard"
      }
    ]
  },
  
  "Opened_Panel_Cover": {
    "default_severity": "MEDIUM",
    "policy_section": "Section 5.2.2",
    "policy_signal": "WARNING",
    "escalation_rules": [
      {
        "condition": "duration_open > 300_seconds",
        "new_severity": "HIGH",
        "rationale": "Extended electrical hazard exposure"
      }
    ]
  },
  
  "Carrying_Overload_with_Forklift": {
    "default_severity": "CRITICAL",
    "policy_section": "Section 6.3.2",
    "policy_signal": "CRITICAL SAFETY NOTICE - unambiguous threshold",
    "escalation_rules": [],
    "note": "Always CRITICAL - explicit 2/3 block threshold in policy"
  }
}
```

### File: src/severity/classifier.py

```python
import json
from typing import Dict, Tuple
from enum import Enum

class SeverityTier(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SeverityClassifier:
    """Classify detected violations into severity tiers"""
    
    def __init__(self, rules_path: str = "src/severity/rules.json"):
        """Load severity rules from policy-derived JSON"""
        with open(rules_path, 'r') as f:
            self.rules = json.load(f)
    
    def classify(self, detection: Dict) -> Tuple[SeverityTier, str]:
        """
        Classify a detection into severity tier.
        
        Args:
            detection: Dict with 'behavior_class' key
            
        Returns:
            Tuple of (SeverityTier, rationale_string)
        """
        behavior = detection.get("behavior_class")
        
        if behavior not in self.rules:
            return SeverityTier.MEDIUM, "Unknown behavior - default to MEDIUM"
        
        rule = self.rules[behavior]
        default_severity = rule["default_severity"]
        
        # Check escalation rules
        escalation_rules = rule.get("escalation_rules", [])
        
        for escalation in escalation_rules:
            # In production: evaluate condition against detection metadata
            # For MVP: simplified logic
            
            if self._evaluate_condition(escalation["condition"], detection):
                return SeverityTier(escalation["new_severity"]), escalation["rationale"]
        
        return SeverityTier(default_severity), rule.get("policy_signal", "Default severity")
    
    def _evaluate_condition(self, condition: str, detection: Dict) -> bool:
        """Evaluate if escalation condition is met"""
        # Simplified for MVP
        # In production: would parse and evaluate condition string
        
        if "proximity" in condition and detection.get("proximity_to_hazard"):
            return detection["proximity_to_hazard"] < 1.0
        
        if "personnel_count" in condition and detection.get("personnel_count"):
            return detection["personnel_count"] > 1
        
        if "duration" in condition and detection.get("duration_open"):
            return detection["duration_open"] > 300
        
        return False


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    classifier = SeverityClassifier()
    
    detection = {
        "behavior_class": "Carrying_Overload_with_Forklift",
        "metadata": {"block_count": 4}
    }
    
    severity, rationale = classifier.classify(detection)
    print(f"Severity: {severity}")
    print(f"Rationale: {rationale}")
```

---

## MODULE 3: ESCALATION PIPELINE

### File: src/escalation/router.py

```python
import asyncio
from enum import Enum
from typing import Dict
from datetime import datetime

class RoutingRule:
    """
    Implements routing logic:
    - LOW/MEDIUM → DB log only
    - HIGH/CRITICAL → DB log + real-time alert
    """
    
    @staticmethod
    def should_trigger_alert(severity: str) -> bool:
        """
        Determine if violation should trigger real-time alert.
        
        Args:
            severity: One of LOW, MEDIUM, HIGH, CRITICAL
            
        Returns:
            True if alert should be triggered
        """
        return severity in ["HIGH", "CRITICAL"]
    
    @staticmethod
    def should_log_to_db(severity: str) -> bool:
        """All violations logged to DB"""
        return True


class EscalationRouter:
    """Routes violations to appropriate channels"""
    
    def __init__(self, db_logger, alert_manager):
        """
        Args:
            db_logger: Database logger instance
            alert_manager: Alert manager for real-time alerts
        """
        self.db_logger = db_logger
        self.alert_manager = alert_manager
    
    async def route_violation(self, violation: Dict) -> Dict:
        """
        Route a violation based on severity.
        
        Args:
            violation: Violation record with severity field
            
        Returns:
            Escalation result dict
        """
        severity = violation.get("severity")
        escalation_action = None
        
        # Log to database (mandatory)
        if RoutingRule.should_log_to_db(severity):
            self.db_logger.insert(violation)
            escalation_action = f"Logged to DB"
        
        # Trigger real-time alert (HIGH/CRITICAL only)
        if RoutingRule.should_trigger_alert(severity):
            await self.alert_manager.trigger_alert(violation, severity)
            escalation_action = f"Real-time alert triggered + DB log"
        
        return {
            "event_id": violation.get("event_id"),
            "severity": severity,
            "escalation_action": escalation_action,
            "timestamp": datetime.utcnow().isoformat()
        }


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    # In main.py, you'd instantiate:
    # router = EscalationRouter(db_logger, alert_manager)
    # result = await router.route_violation(violation_dict)
    pass
```

---

## MODULE 4: REPORT GENERATION

### File: src/reports/generator.py

```python
import json
import csv
import uuid
import os
from datetime import datetime
from typing import Dict
from dataclasses import dataclass, asdict

@dataclass
class ComplianceReport:
    """Compliance report schema (required fields)"""
    event_id: str
    timestamp: str
    clip_id: str
    zone: str
    behavior_class: str
    policy_rule_ref: str
    event_description: str
    severity: str
    escalation_action: str
    confidence: float = 0.0
    frame_number: int = 0
    bounding_box: tuple = None
    created_at: str = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow().isoformat() + "Z"


class ComplianceReportGenerator:
    """Automatically generates immutable compliance records"""
    
    def __init__(
        self,
        db_path: str = "outputs/violations.db",
        json_log_path: str = "outputs/compliance_reports.json",
        csv_log_path: str = "outputs/compliance_reports.csv"
    ):
        """Initialize output paths"""
        self.db_path = db_path
        self.json_log_path = json_log_path
        self.csv_log_path = csv_log_path
        
        # Ensure output directory exists
        os.makedirs("outputs", exist_ok=True)
        
        # Write CSV header if file doesn't exist
        if not os.path.exists(csv_log_path):
            self._write_csv_header()
    
    def generate(self, detection: Dict, severity: str, escalation_action: str) -> ComplianceReport:
        """
        Generate compliance report from detection data.
        Automatically persists to all storage formats.
        
        Args:
            detection: Detection record from Module 1
            severity: Severity tier from Module 2
            escalation_action: Escalation result from Module 3
            
        Returns:
            ComplianceReport object
        """
        
        # Create report object
        report = ComplianceReport(
            event_id=self._generate_event_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            clip_id=detection.get("clip_id"),
            zone=detection.get("zone", "Unknown"),
            behavior_class=detection.get("behavior_class"),
            policy_rule_ref=detection.get("policy_rule_ref"),
            event_description=detection.get("description"),
            severity=severity,
            escalation_action=escalation_action,
            confidence=detection.get("confidence", 0.0),
            frame_number=detection.get("frame_number", 0),
            bounding_box=detection.get("bounding_box"),
        )
        
        # Write to all formats
        self._write_to_json(report)
        self._write_to_csv(report)
        # self._write_to_db(report)  # Optional: SQLite
        
        return report
    
    def _generate_event_id(self) -> str:
        """Generate unique event ID"""
        now = datetime.utcnow()
        random_suffix = str(uuid.uuid4())[:8]
        return f"evt-{now.strftime('%Y%m%d%H%M%S')}-{random_suffix}"
    
    def _write_to_json(self, report: ComplianceReport):
        """Append report to JSON log (one JSON object per line)"""
        with open(self.json_log_path, "a") as f:
            f.write(json.dumps(asdict(report)) + "\n")
    
    def _write_to_csv(self, report: ComplianceReport):
        """Append report to CSV log"""
        row = [
            report.event_id,
            report.timestamp,
            report.clip_id,
            report.zone,
            report.behavior_class,
            report.policy_rule_ref,
            report.event_description,
            report.severity,
            report.escalation_action
        ]
        
        with open(self.csv_log_path, "a", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(row)
    
    def _write_csv_header(self):
        """Write CSV header if file is new"""
        header = [
            "event_id", "timestamp", "clip_id", "zone", "behavior_class",
            "policy_rule_ref", "event_description", "severity", "escalation_action"
        ]
        
        with open(self.csv_log_path, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(header)
    
    # def _write_to_db(self, report: ComplianceReport):
    #     """Optional: Write to SQLite database"""
    #     # Implementation would go here
    #     pass


# --- USAGE EXAMPLE ---
if __name__ == "__main__":
    generator = ComplianceReportGenerator()
    
    detection = {
        "clip_id": "safe_walkway_violation_001.mp4",
        "zone": "Zone-1",
        "behavior_class": "Safe_Walkway_Violation",
        "description": "Person outside green zone",
        "policy_rule_ref": "Section 3.3.2",
        "confidence": 0.92
    }
    
    report = generator.generate(detection, "MEDIUM", "Logged to DB")
    print(f"Report generated: {report.event_id}")
```

---

## MODULE 5: DASHBOARD (React)

### File: src/dashboard/src/App.tsx

```typescript
import React, { useState, useEffect } from 'react';
import './App.css';
import LiveFeedMonitor from './components/LiveFeedMonitor';
import AlertTimeline from './components/AlertTimeline';
import HistoricalLog from './components/HistoricalLog';
import Navbar from './components/Navbar';

type Tab = 'live' | 'alerts' | 'history';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('live');
  const [violations, setViolations] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  // Fetch violations on component mount
  useEffect(() => {
    fetchViolations();
  }, []);

  const fetchViolations = async () => {
    setLoading(true);
    try {
      const response = await fetch('http://localhost:8000/api/violations');
      const data = await response.json();
      setViolations(data);
    } catch (error) {
      console.error('Failed to fetch violations:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app">
      <Navbar />
      
      <div className="tabs">
        <button 
          className={activeTab === 'live' ? 'active' : ''}
          onClick={() => setActiveTab('live')}
        >
          📹 Live Feed
        </button>
        <button 
          className={activeTab === 'alerts' ? 'active' : ''}
          onClick={() => setActiveTab('alerts')}
        >
          🚨 Alert Timeline
        </button>
        <button 
          className={activeTab === 'history' ? 'active' : ''}
          onClick={() => setActiveTab('history')}
        >
          📊 Historical Log
        </button>
      </div>

      <div className="content">
        {loading && <p>Loading...</p>}
        
        {activeTab === 'live' && <LiveFeedMonitor violations={violations} />}
        {activeTab === 'alerts' && <AlertTimeline violations={violations} />}
        {activeTab === 'history' && <HistoricalLog violations={violations} />}
      </div>
    </div>
  );
};

export default App;
```

### File: src/dashboard/src/components/AlertTimeline.tsx

```typescript
import React, { useEffect, useState } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

interface Violation {
  event_id: string;
  timestamp: string;
  behavior_class: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  description: string;
  zone: string;
}

const AlertTimeline: React.FC<{ violations: Violation[] }> = ({ violations }) => {
  const [alerts, setAlerts] = useState<Violation[]>(violations);
  const [showFlash, setShowFlash] = useState(false);
  
  // WebSocket connection for real-time alerts
  useWebSocket((event: Violation) => {
    if (['HIGH', 'CRITICAL'].includes(event.severity)) {
      // Flash animation for HIGH/CRITICAL
      setShowFlash(true);
      setTimeout(() => setShowFlash(false), event.severity === 'CRITICAL' ? 5000 : 3000);
    }
    
    // Add to timeline
    setAlerts([event, ...alerts]);
  });

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'LOW': return '#ffc107';
      case 'MEDIUM': return '#ff9800';
      case 'HIGH': return '#f44336';
      case 'CRITICAL': return '#8b0000';
      default: return '#999';
    }
  };

  return (
    <div className="alert-timeline">
      {/* Flash banner for CRITICAL */}
      {showFlash && (
        <div className="alert-banner" style={{ 
          backgroundColor: '#8b0000',
          animation: 'flash 1s infinite'
        }}>
          🚨 CRITICAL SAFETY ALERT
        </div>
      )}

      {/* Timeline stream */}
      <div className="timeline">
        {alerts.length === 0 ? (
          <p>No violations detected yet</p>
        ) : (
          alerts.map(alert => (
            <div
              key={alert.event_id}
              className="alert-item"
              style={{ borderLeftColor: getSeverityColor(alert.severity) }}
            >
              <div className="alert-header">
                <span className="time">
                  {new Date(alert.timestamp).toLocaleTimeString()}
                </span>
                <span className="severity" style={{ backgroundColor: getSeverityColor(alert.severity) }}>
                  {alert.severity}
                </span>
              </div>
              <div className="alert-body">
                <strong>{alert.behavior_class}</strong>
                <p>{alert.description}</p>
                <small>Zone: {alert.zone}</small>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

export default AlertTimeline;
```

### File: src/dashboard/src/hooks/useWebSocket.ts

```typescript
import { useEffect } from 'react';
import io from 'socket.io-client';

export const useWebSocket = (onAlert: (alert: any) => void) => {
  useEffect(() => {
    const socket = io('http://localhost:8000');
    
    socket.on('COMPLIANCE_ALERT', (alert) => {
      onAlert(alert);
    });
    
    return () => {
      socket.disconnect();
    };
  }, [onAlert]);
};
```

---

## FASTAPI SERVER ENTRY POINT

### File: src/main.py

```python
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

from detection.detector import DetectionEngine
from severity.classifier import SeverityClassifier
from escalation.router import EscalationRouter
from reports.generator import ComplianceReportGenerator

# Initialize modules
app = FastAPI(title="Factory Compliance System")

# CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize processors
detector = DetectionEngine()
classifier = SeverityClassifier()
generator = ComplianceReportGenerator()

# WebSocket connections
active_connections = []

@app.websocket("/ws/alerts")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time alerts"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception as e:
        active_connections.remove(websocket)

@app.post("/api/process_video")
async def process_video(video_path: str):
    """Process a video clip and detect violations"""
    
    # Module 1: Detection
    detections = detector.process_video(video_path)
    
    # Module 2 & 3 & 4: Severity + Escalation + Reports
    for detection in detections:
        severity, rationale = classifier.classify(detection.to_dict())
        
        # Module 3: Route violation
        # escalation_result = await router.route_violation(...)
        
        # Module 4: Generate report
        report = generator.generate(
            detection.to_dict(),
            severity.value,
            f"Real-time alert triggered + DB log" if severity.value in ["HIGH", "CRITICAL"] else "Logged to DB"
        )
        
        # Broadcast alert to dashboard if HIGH/CRITICAL
        if severity.value in ["HIGH", "CRITICAL"]:
            alert_payload = {
                "event_id": report.event_id,
                "behavior_class": report.behavior_class,
                "severity": severity.value,
                "timestamp": report.timestamp
            }
            for conn in active_connections:
                await conn.send_json(alert_payload)
    
    return {"status": "success", "detections": len(detections)}

@app.get("/api/violations")
async def get_violations():
    """Fetch all violations from database"""
    # TODO: Query database
    return []

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## NEXT STEPS

1. Create all files above in your project
2. Fill in `_detect_*` methods in detector.py with real logic
3. Implement WebSocket properly with python-socketio
4. Connect React components to FastAPI endpoints
5. Test end-to-end with sample videos
6. Write comprehensive README

Good luck! 💪

