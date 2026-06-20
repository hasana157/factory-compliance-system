"""scripts/batch_inference.py

Batch inference runner for the FactoryGuard detection pipeline.

Iterates through all videos in a dataset directory, runs the NEW honest
pixel-based detection pipeline on every video, and saves results to
results/batch_report.json.

The detection engine NEVER reads the file path for classification —
only pixel data is used. Ground-truth labels come from the folder names
(which are used ONLY for accuracy analysis in analyze_results.py,
never for driving detection decisions).

Usage:
    python scripts/batch_inference.py
    python scripts/batch_inference.py --dataset data/kaggle_dataset --output results/batch_report.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Ensure project root is importable
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# Known behavior class folder names in the Kaggle dataset
SAFE_BEHAVIORS = {"Normal", "Safe", "safe", "normal"}
BEHAVIOR_LABELS = {
    # Map dataset folder names → canonical behavior class names
    "Safe_Walkway_Violation":         "Safe_Walkway_Violation",
    "Unauthorized_Intervention":      "Unauthorized_Intervention",
    "Opened_Panel_Cover":             "Opened_Panel_Cover",
    "Carrying_Overload_with_Forklift": "Carrying_Overload_with_Forklift",
    "Normal":                         "SAFE",
    "Safe":                           "SAFE",
    "safe":                           "SAFE",
    "normal":                         "SAFE",
}

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv"}


def discover_videos(dataset_dir: Path) -> list[tuple[Path, str]]:
    """Walk dataset_dir and return (video_path, folder_label) pairs."""
    videos: list[tuple[Path, str]] = []
    for folder in dataset_dir.iterdir():
        if not folder.is_dir():
            continue
        label = folder.name
        for video in folder.rglob("*"):
            if video.suffix.lower() in VIDEO_EXTS:
                videos.append((video, label))
    # Also check top-level videos (unlabeled)
    for video in dataset_dir.iterdir():
        if video.suffix.lower() in VIDEO_EXTS:
            videos.append((video, "Unknown"))
    return sorted(videos, key=lambda t: str(t[0]))


def run_batch(
    dataset_dir: Path,
    output_path: Path,
    max_videos: int | None = None,
) -> dict:
    """Run inference on all videos and write results/batch_report.json."""
    from src.detection.detector import DetectionEngine
    from src.severity.classifier import SeverityClassifier
    from src.escalation.router import RoutingRule

    print(f"[batch] Loading detection engine from: {_ROOT / 'src/severity/auto_generated_rules.json'}")
    engine     = DetectionEngine()
    classifier = SeverityClassifier()

    videos = discover_videos(dataset_dir)
    if max_videos:
        videos = videos[:max_videos]

    print(f"[batch] Found {len(videos)} videos in: {dataset_dir}")
    print()

    results = []
    errors  = []
    total   = len(videos)

    for idx, (video_path, folder_label) in enumerate(videos, 1):
        print(f"[{idx:4d}/{total}] {video_path.name} (label={folder_label})", end=" ... ")
        start = time.perf_counter()

        try:
            detections = engine.process_video(video_path)
            elapsed = time.perf_counter() - start

            if not detections:
                # No violations detected
                results.append({
                    "video":          str(video_path.relative_to(dataset_dir)),
                    "folder_label":   folder_label,
                    "detected":       False,
                    "violations":     [],
                    "processing_ms":  round(elapsed * 1000, 1),
                })
                print(f"SAFE ({elapsed*1000:.0f}ms)")
            else:
                classified = []
                for det in detections:
                    det_dict = det.to_dict()
                    decision = classifier.classify(det_dict)
                    classified.append({
                        "behavior_class":  det.behavior_class,
                        "severity":        decision.severity.value,
                        "confidence":      round(det.confidence, 4),
                        "zone":            det.zone,
                        "frame_number":    det.frame_number,
                        "timestamp":       round(det.timestamp, 3),
                        "policy_rule_ref": det.policy_rule_ref,
                        "rationale":       decision.rationale,
                        "metadata":        det.metadata,
                    })

                max_severity = max(
                    classified,
                    key=lambda r: ["LOW", "MEDIUM", "HIGH", "CRITICAL"].index(r["severity"]),
                )["severity"]

                results.append({
                    "video":          str(video_path.relative_to(dataset_dir)),
                    "folder_label":   folder_label,
                    "detected":       True,
                    "violations":     classified,
                    "max_severity":   max_severity,
                    "processing_ms":  round(elapsed * 1000, 1),
                })
                print(f"{max_severity} ({elapsed*1000:.0f}ms, {len(classified)} violations)")

        except FileNotFoundError:
            errors.append({"video": str(video_path), "error": "File not found"})
            print("ERROR: file not found")
        except Exception as exc:
            errors.append({"video": str(video_path), "error": str(exc)})
            print(f"ERROR: {exc}")

    # Summary statistics
    detected_count = sum(1 for r in results if r.get("detected"))
    safe_count     = sum(1 for r in results if not r.get("detected"))

    batch_report = {
        "metadata": {
            "dataset_dir":    str(dataset_dir),
            "total_videos":   total,
            "detected":       detected_count,
            "safe":           safe_count,
            "errors":         len(errors),
            "detection_rate": round(detected_count / total * 100, 1) if total > 0 else 0,
        },
        "results": results,
        "errors":  errors,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fh:
        json.dump(batch_report, fh, indent=2)

    print()
    print("=" * 60)
    print(f"  Total videos  : {total}")
    print(f"  Violations    : {detected_count} ({batch_report['metadata']['detection_rate']}%)")
    print(f"  Safe / Clean  : {safe_count}")
    print(f"  Errors        : {len(errors)}")
    print(f"  Report saved  : {output_path}")
    print("=" * 60)

    return batch_report


def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Run FactoryGuard batch inference on a video dataset."
    )
    parser.add_argument(
        "--dataset",
        default=str(_ROOT / "data" / "kaggle_dataset"),
        help="Path to the dataset directory (with behavior subfolders).",
    )
    parser.add_argument(
        "--output",
        default=str(_ROOT / "results" / "batch_report.json"),
        help="Path to save batch_report.json.",
    )
    parser.add_argument(
        "--max-videos",
        type=int,
        default=None,
        help="Limit inference to the first N videos (for quick testing).",
    )
    args = parser.parse_args()

    run_batch(
        dataset_dir=Path(args.dataset),
        output_path=Path(args.output),
        max_videos=args.max_videos,
    )


if __name__ == "__main__":
    _cli()
