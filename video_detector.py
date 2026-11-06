from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import cv2
import numpy as np


VIDEO_ANALYSIS_DISCLAIMER = (
    "This AI-assisted analysis is probabilistic and cannot guarantee whether a video is AI-generated, "
    "manipulated, or authentic. Always verify important content using reliable independent sources."
)


def classify_baseline_score(consistency_score: float) -> dict[str, str]:
    """Translate measured OpenCV frame-consistency signals into cautious result language."""
    if consistency_score >= 0.72:
        return {
            "label": "Potential AI-Generated Video",
            "risk": "High",
            "summary": "This may be an AI-generated / Deepfake Video",
            "explanation": (
                "Several sampled frames showed visual consistency patterns that may be associated with AI-generated "
                "or manipulated video. This is a baseline visual analysis and is not forensic proof."
            ),
        }
    if consistency_score >= 0.54:
        return {
            "label": "Potential Deepfake",
            "risk": "Medium",
            "summary": "This may be an AI-generated / Deepfake Video",
            "explanation": (
                "Detected visual inconsistencies may indicate AI-generated or manipulated content. These signals can also "
                "be affected by compression, editing, lighting changes, or camera motion, so they are not proof."
            ),
        }
    return {
        "label": "Likely Authentic",
        "risk": "Low",
        "summary": "This video appears likely authentic",
        "explanation": (
            "No strong inconsistencies were detected in the sampled frames. However, this analysis cannot guarantee that "
            "the video is authentic."
        ),
    }


def _thumbnail_data_url(frame: np.ndarray) -> str | None:
    height, width = frame.shape[:2]
    if width > 280:
        scale = 280 / width
        frame = cv2.resize(frame, (280, max(1, int(height * scale))))
    success, encoded = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 76])
    if not success:
        return None
    content = base64.b64encode(encoded.tobytes()).decode("ascii")
    return f"data:image/jpeg;base64,{content}"


def analyze_video(path: Path) -> dict[str, Any]:
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise ValueError("The uploaded file could not be read as a video.")

    try:
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if fps <= 0 or total_frames <= 0 or width <= 0 or height <= 0:
            raise ValueError("The video metadata is incomplete or the file is corrupted.")

        duration = total_frames / fps
        sample_count = min(18, max(10, total_frames))
        frame_indices = np.linspace(0, total_frames - 1, num=sample_count, dtype=int)
        brightness_values: list[float] = []
        sharpness_values: list[float] = []
        color_values: list[float] = []
        thumbnails: list[str] = []

        for position, index in enumerate(frame_indices):
            capture.set(cv2.CAP_PROP_POS_FRAMES, int(index))
            success, frame = capture.read()
            if not success or frame is None:
                continue
            small_frame = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            brightness_values.append(float(np.mean(gray)))
            sharpness_values.append(float(cv2.Laplacian(gray, cv2.CV_64F).var()))
            color_values.append(float(np.mean(small_frame)))
            if position in {0, len(frame_indices) // 3, (2 * len(frame_indices)) // 3, len(frame_indices) - 1}:
                thumbnail = _thumbnail_data_url(frame)
                if thumbnail:
                    thumbnails.append(thumbnail)

        analyzed_frames = len(brightness_values)
        if analyzed_frames < 5:
            raise ValueError("Too few readable frames were available for baseline visual analysis.")

        brightness_variation = float(np.std(brightness_values) / max(np.mean(brightness_values), 1))
        sharpness_variation = float(np.std(sharpness_values) / max(np.mean(sharpness_values), 1))
        color_variation = float(np.std(color_values) / max(np.mean(color_values), 1))
        weak_frame_ratio = sum(value < 7 for value in sharpness_values) / analyzed_frames
        consistency_score = min(
            1.0,
            0.12 + (brightness_variation * 1.4) + (sharpness_variation * 0.65) + (color_variation * 1.1) + (weak_frame_ratio * 0.3),
        )
        confidence = round(min(88.0, 54.0 + abs(consistency_score - 0.5) * 62), 1)
        classification = classify_baseline_score(consistency_score)

        return {
            "label": classification["label"],
            "detection": classification["label"],
            "result_summary": classification["summary"],
            "risk": classification["risk"],
            "confidence": confidence,
            "explanation": classification["explanation"],
            "metadata": {
                "duration_seconds": round(duration, 2),
                "fps": round(fps, 2),
                "resolution": f"{width} × {height}",
                "total_frames": total_frames,
                "frames_analyzed": analyzed_frames,
            },
            "signals": {
                "baseline_consistency_score": round(consistency_score, 3),
                "brightness_variation": round(brightness_variation, 3),
                "edge_detail_variation": round(sharpness_variation, 3),
                "color_variation": round(color_variation, 3),
            },
            "thumbnails": thumbnails,
            "method": "Baseline Visual Analysis",
            "disclaimer": VIDEO_ANALYSIS_DISCLAIMER,
        }
    finally:
        capture.release()
