"""
Importance assessment for video content.
Determines which Whisper model to use based on content importance.
"""

import os
import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import get_config
from .utils import get_video_duration, get_audio_bitrate, get_file_size_mb


@dataclass
class ImportanceAssessment:
    """Result of importance evaluation."""
    score: int  # 1-10 scale
    model: str  # Recommended model
    factors: Dict[str, float]  # Individual factor scores
    reasoning: List[str]  # Human-readable explanations

    def to_dict(self) -> Dict:
        return asdict(self)


class ImportanceAssessor:
    """
    Assesses video importance to select appropriate transcription model.

    Factors considered:
    - Video duration (longer = more important)
    - Audio quality (higher bitrate = professional content)
    - Filename keywords ("curso", "tutorial" = high importance)
    - Source folder patterns
    - File size
    """

    def __init__(self, config=None):
        self.config = config or get_config()

    def assess(self, video_path: str) -> ImportanceAssessment:
        """
        Evaluate importance of video content.

        Args:
            video_path: Path to video file

        Returns:
            ImportanceAssessment with score (1-10) and recommended model
        """
        path = Path(video_path)
        factors = {}
        reasoning = []

        # Get weights from config
        weights = self.config.get("importance.auto_detection.weights", {})

        # Factor 1: Duration
        duration_score, duration_reason = self._assess_duration(video_path)
        factors["duration"] = duration_score
        if duration_reason:
            reasoning.append(duration_reason)

        # Factor 2: Audio quality
        audio_score, audio_reason = self._assess_audio_quality(video_path)
        factors["audio_quality"] = audio_score
        if audio_reason:
            reasoning.append(audio_reason)

        # Factor 3: Filename keywords
        keyword_score, keyword_reason = self._assess_filename_keywords(path.stem)
        factors["filename_keywords"] = keyword_score
        if keyword_reason:
            reasoning.append(keyword_reason)

        # Factor 4: Source folder
        folder_score, folder_reason = self._assess_source_folder(str(path.parent))
        factors["source_folder"] = folder_score
        if folder_reason:
            reasoning.append(folder_reason)

        # Factor 5: File size
        size_score, size_reason = self._assess_file_size(video_path)
        factors["file_size"] = size_score
        if size_reason:
            reasoning.append(size_reason)

        # Calculate weighted score
        weighted_score = (
            factors["duration"] * weights.get("duration", 0.25) +
            factors["audio_quality"] * weights.get("audio_quality", 0.20) +
            factors["filename_keywords"] * weights.get("filename_keywords", 0.30) +
            factors["source_folder"] * weights.get("source_folder", 0.15) +
            factors["file_size"] * weights.get("file_size", 0.10)
        )

        # Convert to 1-10 scale
        score = max(1, min(10, round(weighted_score * 10)))

        # Get recommended model
        model = self.config.get_model_for_importance(score)

        return ImportanceAssessment(
            score=score,
            model=model,
            factors=factors,
            reasoning=reasoning,
        )

    def _assess_duration(self, video_path: str) -> Tuple[float, str]:
        """Assess importance based on duration."""
        duration = get_video_duration(video_path)
        if duration is None:
            return 0.5, ""

        # Scoring:
        # < 5 min: 0.3 (short clip)
        # 5-15 min: 0.5 (medium)
        # 15-30 min: 0.7 (substantial)
        # 30-60 min: 0.8 (long form)
        # > 60 min: 1.0 (extensive content)

        if duration < 300:  # < 5 min
            return 0.3, f"Short video ({duration/60:.1f} min)"
        elif duration < 900:  # 5-15 min
            return 0.5, ""
        elif duration < 1800:  # 15-30 min
            return 0.7, f"Substantial length ({duration/60:.0f} min)"
        elif duration < 3600:  # 30-60 min
            return 0.8, f"Long form content ({duration/60:.0f} min)"
        else:  # > 60 min
            return 1.0, f"Extensive content ({duration/3600:.1f}h)"

    def _assess_audio_quality(self, video_path: str) -> Tuple[float, str]:
        """Assess importance based on audio bitrate."""
        bitrate = get_audio_bitrate(video_path)
        if bitrate is None:
            return 0.5, ""

        # Scoring:
        # < 64 kbps: 0.3 (low quality)
        # 64-128 kbps: 0.5 (standard)
        # 128-192 kbps: 0.7 (good)
        # > 192 kbps: 1.0 (professional)

        if bitrate < 64:
            return 0.3, f"Low audio quality ({bitrate} kbps)"
        elif bitrate < 128:
            return 0.5, ""
        elif bitrate < 192:
            return 0.7, f"Good audio quality ({bitrate} kbps)"
        else:
            return 1.0, f"Professional audio ({bitrate} kbps)"

    def _assess_filename_keywords(self, filename: str) -> Tuple[float, str]:
        """Assess importance based on filename keywords."""
        filename_lower = filename.lower()

        # Check high importance keywords
        high_keywords = self.config.get_importance_keywords("high")
        for keyword in high_keywords:
            if keyword.lower() in filename_lower:
                return 1.0, f"High-value keyword: '{keyword}'"

        # Check medium importance keywords
        medium_keywords = self.config.get_importance_keywords("medium")
        for keyword in medium_keywords:
            if keyword.lower() in filename_lower:
                return 0.6, f"Medium keyword: '{keyword}'"

        # Check low importance keywords
        low_keywords = self.config.get_importance_keywords("low")
        for keyword in low_keywords:
            if keyword.lower() in filename_lower:
                return 0.2, f"Low-value keyword: '{keyword}'"

        return 0.5, ""

    def _assess_source_folder(self, folder_path: str) -> Tuple[float, str]:
        """Assess importance based on source folder."""
        folder_lower = folder_path.lower()

        # Check high importance folders
        high_patterns = self.config.get("importance.folder_patterns.high", [])
        for pattern in high_patterns:
            if pattern.lower() in folder_lower:
                return 1.0, f"Important folder: '{pattern}'"

        # Check low importance folders
        low_patterns = self.config.get("importance.folder_patterns.low", [])
        for pattern in low_patterns:
            if pattern.lower() in folder_lower:
                return 0.2, f"Temporary folder: '{pattern}'"

        return 0.5, ""

    def _assess_file_size(self, video_path: str) -> Tuple[float, str]:
        """Assess importance based on file size."""
        size_mb = get_file_size_mb(video_path)

        # Scoring:
        # < 50 MB: 0.3 (small, likely low resolution)
        # 50-200 MB: 0.5 (medium)
        # 200-500 MB: 0.7 (large)
        # > 500 MB: 1.0 (very large, high production)

        if size_mb < 50:
            return 0.3, ""
        elif size_mb < 200:
            return 0.5, ""
        elif size_mb < 500:
            return 0.7, f"Large file ({size_mb:.0f} MB)"
        else:
            return 1.0, f"High-production file ({size_mb:.0f} MB)"

    def format_assessment(self, assessment: ImportanceAssessment) -> str:
        """Format assessment as human-readable string."""
        lines = [
            f"Importance Score: {assessment.score}/10",
            f"Recommended Model: {assessment.model}",
        ]

        if assessment.reasoning:
            lines.append("\nFactors:")
            for reason in assessment.reasoning:
                lines.append(f"  - {reason}")

        return "\n".join(lines)


def assess_importance(video_path: str) -> ImportanceAssessment:
    """
    Convenience function to assess video importance.

    Args:
        video_path: Path to video file

    Returns:
        ImportanceAssessment with score and recommended model
    """
    assessor = ImportanceAssessor()
    return assessor.assess(video_path)


def get_model_for_video(video_path: str, user_importance: Optional[int] = None) -> str:
    """
    Get recommended model for a video.

    Args:
        video_path: Path to video file
        user_importance: User-specified importance (1-10), overrides auto-detection

    Returns:
        Model name (base, small, medium, large-v3)
    """
    config = get_config()

    if user_importance is not None:
        return config.get_model_for_importance(user_importance)

    # Auto-detect if enabled
    if config.get("importance.auto_detection.enabled", True):
        assessment = assess_importance(video_path)
        return assessment.model

    # Fall back to default
    return config.default_model
