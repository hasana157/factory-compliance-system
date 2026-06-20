"""Validation harness for EHS behavioral compliance detection engine.

Runs the detection pipeline over test videos, evaluates prediction against ground truth
based on parent folders, computes confusion matrix and classification metrics,
and saves a structured JSON validation report.
"""

import json
import argparse
from pathlib import Path
from typing import Any

# Add parent directory to path
import sys
if str(Path(__file__).resolve().parent.parent) not in sys.path:
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from src.config import settings
from src.detection.detector import DetectionEngine

def get_ground_truth(file_path: Path) -> str:
    """Infer ground truth category from the parent directory name or folder tree."""
    parts = [part.lower() for part in file_path.parts]
    
    if "walkway" in file_path.name.lower() or any("walkway" in p for p in parts):
        if "violation" in file_path.name.lower() or any("violation" in p for p in parts):
            return "Safe_Walkway_Violation"
        return "Safe_Walkway"
        
    if "intervention" in file_path.name.lower() or any("intervention" in p for p in parts):
        if "unauthorized" in file_path.name.lower() or any("unauthorized" in p for p in parts):
            return "Unauthorized_Intervention"
        return "Authorized_Intervention"
        
    if "panel" in file_path.name.lower() or any("panel" in p for p in parts):
        if "open" in file_path.name.lower() or any("open" in p for p in parts):
            return "Opened_Panel_Cover"
        return "Closed_Panel_Cover"
        
    if "overload" in file_path.name.lower() or any("overload" in p for p in parts):
        return "Carrying_Overload_with_Forklift"
        
    if "forklift" in file_path.name.lower() or any("forklift" in p for p in parts):
        return "Safe_Carrying"
        
    return "Safe / No Violation"

def run_validation(data_dir: Path, output_report_path: Path):
    print(f"Scanning test videos in: {data_dir.resolve()}")
    
    # Supported video formats
    extensions = ("*.mp4", "*.avi", "*.mkv", "*.mov")
    video_files = []
    for ext in extensions:
        video_files.extend(data_dir.rglob(ext))
        
    if not video_files:
        print(f"[WARNING] No test videos found in {data_dir}. Generating sample videos first...")
        from generate_samples import generate_video
        videos = {
            "Safe_Walkway_Violation.mp4": "Safe Walkway Violation",
            "Unauthorized_Intervention.mp4": "Unauthorized Intervention",
            "Opened_Panel_Cover.mp4": "Opened Panel Cover",
            "Carrying_Overload_with_Forklift.mp4": "Carrying Overload with Forklift"
        }
        data_dir.mkdir(parents=True, exist_ok=True)
        for filename, label in videos.items():
            # Place in mock folders to match expected ground truth structures
            folder_name = filename.replace(".mp4", "")
            (data_dir / folder_name).mkdir(exist_ok=True)
            generate_video(str(data_dir / folder_name / filename), label)
            video_files.append(data_dir / folder_name / filename)
            
    print(f"Found {len(video_files)} videos for validation.")
    
    detector = DetectionEngine()
    results = []
    
    # Categories to evaluate
    classes = [
        "Safe_Walkway_Violation",
        "Unauthorized_Intervention",
        "Opened_Panel_Cover",
        "Carrying_Overload_with_Forklift",
        "Safe / No Violation"
    ]
    
    # Initialize confusion matrix
    confusion_matrix = {gt: {pred: 0 for pred in classes} for gt in classes}
    
    for idx, video in enumerate(video_files):
        print(f"[{idx+1}/{len(video_files)}] Processing {video.name}...")
        gt = get_ground_truth(video)
        
        # Check if the ground truth is one of the behavior classes
        gt_category = gt if gt in classes else "Safe / No Violation"
        
        try:
            detections = detector.process_video(video)
            
            # Predict the behavior class with highest count or confidence
            if detections:
                # Find most common behavior class in detections
                counts = {}
                for d in detections:
                    counts[d.behavior_class] = counts.get(d.behavior_class, 0) + 1
                pred_category = max(counts, key=counts.get)
            else:
                pred_category = "Safe / No Violation"
                
        except Exception as exc:
            print(f"Error processing {video.name}: {exc}")
            pred_category = "Safe / No Violation"
            
        confusion_matrix[gt_category][pred_category] += 1
        
        results.append({
            "filename": video.name,
            "filepath": str(video.resolve()),
            "ground_truth": gt_category,
            "predicted": pred_category,
            "detections_count": len(detections) if 'detections' in locals() else 0,
            "status": "correct" if gt_category == pred_category else "incorrect"
        })
        
    # Calculate Precision, Recall, F1 for each class
    metrics = {}
    total_correct = 0
    total_samples = len(video_files)
    
    for c in classes:
        tp = confusion_matrix[c][c]
        fp = sum(confusion_matrix[gt][c] for gt in classes if gt != c)
        fn = sum(confusion_matrix[c][pred] for pred in classes if pred != c)
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
        
        metrics[c] = {
            "precision": precision,
            "recall": recall,
            "f1_score": f1,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn
        }
        total_correct += tp
        
    accuracy = total_correct / total_samples if total_samples > 0 else 0.0
    
    report = {
        "summary": {
            "total_samples": total_samples,
            "total_correct": total_correct,
            "accuracy": accuracy
        },
        "confusion_matrix": confusion_matrix,
        "metrics_per_class": metrics,
        "results": results
    }
    
    # Save Report
    output_report_path.parent.mkdir(parents=True, exist_ok=True)
    with output_report_path.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=2)
        
    # Print nice CLI summary
    print("\n=================== VALIDATION REPORT ===================")
    print(f"Overall Accuracy: {accuracy * 100:.2f}% ({total_correct}/{total_samples} correct)")
    print("\nMetrics per Class:")
    print(f"{'Class Name':<35} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 75)
    for c, met in metrics.items():
        print(f"{c:<35} | {met['precision']*100:<9.1f}% | {met['recall']*100:<9.1f}% | {met['f1_score']:<10.3f}")
        
    print("\nConfusion Matrix (Row = Ground Truth, Col = Prediction):")
    header = f"{'GT \\ Pred':<35}"
    for c in classes:
        header += f" | {c[:10]:<10}"
    print(header)
    print("-" * 95)
    for gt in classes:
        row_str = f"{gt:<35}"
        for pred in classes:
            row_str += f" | {confusion_matrix[gt][pred]:<10}"
        print(row_str)
    print("=========================================================")
    print(f"Report saved to: {output_report_path}")

def main():
    parser = argparse.ArgumentParser(description="Run compliance validation")
    parser.add_argument("--data", default="data/kaggle", help="Directory containing test videos")
    parser.add_argument("--report", default="outputs/kaggle_validation_report.json", help="Path to save report")
    args = parser.parse_args()
    
    data_path = Path(args.data)
    report_path = Path(args.report)
    
    # Fallback to local data directories if data/kaggle doesn't exist
    if not data_path.exists():
        data_path = Path("data")
        
    run_validation(data_path, report_path)

if __name__ == "__main__":
    main()
