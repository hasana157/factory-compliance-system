"""Detection module constants and configuration."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DetectionConfig:
    confidence_threshold: float = 0.5
    frame_stride: int = 12
    max_frames: int = 180
    use_ml: bool = False
    yolo_model: str = "yolov8n.pt"

