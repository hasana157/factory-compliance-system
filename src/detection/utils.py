"""src/detection/utils.py

Utility functions for video frame processing and pixel-level heuristics.
All thresholds passed as parameters — never hardcoded inside these functions.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Iterator


# ---------------------------------------------------------------------------
# Video sampling
# ---------------------------------------------------------------------------

def iter_sampled_frames(
    video_path: Path, frame_stride: int, max_frames: int
) -> Iterator[tuple[int, float, Any]]:
    """Yield (frame_number, timestamp_seconds, frame) from a video.

    Defensive: if OpenCV cannot open the file, no frames are yielded.
    """
    try:
        import cv2
    except Exception:
        return

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        return

    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frame_number = 0
    yielded = 0
    try:
        while yielded < max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if frame_number % frame_stride == 0:
                yielded += 1
                yield frame_number, frame_number / fps, frame
            frame_number += 1
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# Heuristic 1 helper — green floor pixel ratio (walkway detection)
# ---------------------------------------------------------------------------

def green_pixel_ratio(
    frame: Any, box: tuple[int, int, int, int] | None = None
) -> float:
    """Return ratio of HSV-green pixels in *frame* (or *box* sub-region).

    Green walkway HSV range: H=[35,85], S=[40,255], V=[40,255].
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return 0.0

    region = _crop(frame, box)
    if region is None or region.size == 0:
        return 0.0

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    lower_green = np.array([35, 40, 40])
    upper_green = np.array([85, 255, 255])
    mask = cv2.inRange(hsv, lower_green, upper_green)
    return float(mask.mean() / 255.0)


# ---------------------------------------------------------------------------
# Heuristic 2 helper — vest green pixel ratio (upper-torso region)
# ---------------------------------------------------------------------------

def vest_green_ratio(
    frame: Any, box: tuple[int, int, int, int] | None = None
) -> float:
    """Return ratio of safety-vest-green pixels in the upper-torso region.

    Safety vests use a brighter, more saturated green than floor markings.
    HSV range: H=[40,80], S=[100,255], V=[80,255].
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return 0.0

    region = _crop(frame, box)
    if region is None or region.size == 0:
        return 0.0

    hsv = cv2.cvtColor(region, cv2.COLOR_BGR2HSV)
    # High-visibility safety vest green: brighter and more saturated
    lower_vest = np.array([40, 100, 80])
    upper_vest = np.array([80, 255, 255])
    mask = cv2.inRange(hsv, lower_vest, upper_vest)
    return float(mask.mean() / 255.0)


# ---------------------------------------------------------------------------
# Heuristic 3 helper — panel open/closed classifier (edge density)
# ---------------------------------------------------------------------------

def detect_panel_open(
    frame: Any,
    box: tuple[int, int, int, int] | None = None,
    edge_threshold: float = 0.3,
) -> bool:
    """Return True if the panel region appears to be in an 'open' state.

    Uses Canny edge density: an open panel exposes internal wiring and
    circuit boards, producing significantly higher edge density than a
    closed panel cover.

    Parameters
    ----------
    frame:
        Full BGR frame.
    box:
        (x1, y1, x2, y2) region to inspect.  Uses full frame if None.
    edge_threshold:
        Edge pixel ratio above which the panel is classified as open.
        Loaded from auto_generated_rules.json threshold_values.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return False

    region = _crop(frame, box)
    if region is None or region.size == 0:
        return False

    gray  = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, 50, 150)
    density = float(edges.mean() / 255.0)
    return density > edge_threshold


# ---------------------------------------------------------------------------
# Heuristic 4 helper — block / object counter on fork region
# ---------------------------------------------------------------------------

def count_objects_in_region(
    frame: Any,
    box: tuple[int, int, int, int] | None = None,
    min_contour_area: int = 500,
) -> int:
    """Count rectangular contours in a region (forklift fork area).

    Finds bounding-box-shaped contours to count stacked blocks/pallets.
    Returns the estimated number of distinct objects.
    """
    try:
        import cv2
        import numpy as np
    except Exception:
        return 0

    region = _crop(frame, box)
    if region is None or region.size == 0:
        return 0

    gray    = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter by area and aspect ratio to keep block-shaped contours
    block_count = 0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < min_contour_area:
            continue
        rect = cv2.boundingRect(cnt)
        _x, _y, w, h = rect
        if w == 0 or h == 0:
            continue
        aspect = w / h
        # Blocks/pallets have aspect ratio between 0.5 and 3.0
        if 0.5 <= aspect <= 3.0:
            block_count += 1

    return block_count


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def pixel_distance(x1: int, y1: int, x2: int, y2: int) -> float:
    """Euclidean pixel distance between two centroids."""
    return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)


def normalize_label(value: str) -> str:
    """Normalize file and folder names for label matching (kept for test compat)."""
    return value.strip().lower().replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# Internal crop helper
# ---------------------------------------------------------------------------

def _crop(frame: Any, box: tuple[int, int, int, int] | None) -> Any:
    """Return a cropped sub-array of *frame*, or *frame* itself if box is None."""
    if box is None:
        return frame
    try:
        height, width = frame.shape[:2]
        x1, y1, x2, y2 = box
        x1, x2 = max(0, x1), min(width, x2)
        y1, y2 = max(0, y1), min(height, y2)
        if x2 <= x1 or y2 <= y1:
            return None
        return frame[y1:y2, x1:x2]
    except Exception:
        return None


def pixel_to_zone(bbox: tuple[int, int, int, int], frame_shape: tuple[int, int]) -> str:
    """Map the pixel coordinates of a bounding box to a facility quadrant zone."""

    h, w = frame_shape[:2]
    x1, y1, x2, y2 = bbox
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2

    if cx < w / 2:
        if cy < h / 2:
            return "Quadrant 1 - North West Floor"
        else:
            return "Quadrant 3 - South West Floor"
    else:
        if cy < h / 2:
            return "Quadrant 2 - North East Floor"
        else:
            return "Quadrant 4 - South East Floor"

