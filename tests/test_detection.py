import pytest
from pathlib import Path
from src.detection.detector import DetectionEngine
from generate_samples import generate_video

def test_detector_raises_error_for_missing_video(rules_path):
    detector = DetectionEngine(rules_path=rules_path)
    with pytest.raises(FileNotFoundError):
        detector.process_video("nonexistent_video_file.mp4")

def test_detector_detects_walkway_violation(tmp_path, rules_path):
    # Generate a synthetic walkway video
    video_path = tmp_path / "Safe_Walkway_Violation.mp4"
    generate_video(str(video_path), "Safe Walkway Violation")
    
    detector = DetectionEngine(rules_path=rules_path)
    detections = detector.process_video(video_path)
    
    assert len(detections) > 0
    assert detections[0].behavior_class == "Safe_Walkway_Violation"
    assert detections[0].policy_rule_ref == "Section 4.2.1"
    assert detections[0].metadata["source"] == "frame_heuristic"
    assert "Quadrant" in detections[0].zone

def test_detector_detects_forklift_overload(tmp_path, rules_path):
    # Generate a synthetic forklift overload video
    video_path = tmp_path / "Carrying_Overload_with_Forklift.mp4"
    generate_video(str(video_path), "Carrying Overload with Forklift")
    
    detector = DetectionEngine(rules_path=rules_path)
    detections = detector.process_video(video_path)
    
    assert len(detections) > 0
    assert detections[0].behavior_class == "Carrying_Overload_with_Forklift"
    assert detections[0].policy_rule_ref == "Section 6.3.2"
