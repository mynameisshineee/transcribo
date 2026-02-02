"""
Quality validation for Whisper transcriptions.
Detects problems and recommends actions (accept, warn, retry, fail).
"""

import json
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import get_config


class Recommendation(Enum):
    """Quality validation recommendations."""
    ACCEPT = "accept"      # Quality is good, proceed
    WARN = "warn"          # Quality acceptable but has issues
    RETRY = "retry"        # Quality low, retry with better model
    FAIL = "fail"          # Quality very low, manual review needed


@dataclass
class QualityMetrics:
    """Metrics extracted from Whisper transcription."""
    avg_logprob: float = 0.0           # Average log probability (confidence)
    compression_ratio: float = 1.0      # Text compression ratio
    no_speech_prob: float = 0.0         # Probability of no speech
    text_density: float = 0.0           # Words per second
    total_segments: int = 0             # Number of segments
    low_confidence_segments: int = 0    # Segments with low confidence
    high_compression_segments: int = 0  # Segments with high compression (hallucination risk)
    silent_segments_with_text: int = 0  # Suspicious segments


@dataclass
class QualityReport:
    """Complete quality validation report."""
    overall_score: float = 0.0
    recommendation: Recommendation = Recommendation.ACCEPT
    issues: List[str] = field(default_factory=list)
    metrics: QualityMetrics = field(default_factory=QualityMetrics)
    model_used: str = ""
    retry_count: int = 0
    suggested_model: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert report to dictionary for JSON serialization."""
        return {
            "overall_score": round(self.overall_score, 3),
            "recommendation": self.recommendation.value,
            "issues": self.issues,
            "metrics": asdict(self.metrics),
            "model_used": self.model_used,
            "retry_count": self.retry_count,
            "suggested_model": self.suggested_model,
        }

    def save(self, output_path: str) -> None:
        """Save report to JSON file."""
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


class QualityValidator:
    """
    Validates Whisper transcription quality and recommends actions.

    Uses metrics from Whisper output to detect:
    - Low confidence transcriptions
    - Possible hallucinations (high compression ratio)
    - Silent segments incorrectly transcribed
    - Low text density (possible audio issues)
    """

    # Model hierarchy for upgrades
    MODEL_HIERARCHY = ["base", "small", "medium", "large-v3"]

    def __init__(self, config=None):
        """
        Initialize validator with configuration.

        Args:
            config: Config instance or None to use global config
        """
        self.config = config or get_config()

    def validate(
        self,
        transcription_result: Dict[str, Any],
        video_duration: float,
        model_used: str = "medium",
        retry_count: int = 0,
    ) -> QualityReport:
        """
        Validate transcription quality.

        Args:
            transcription_result: Whisper transcription output with segments
            video_duration: Video duration in seconds
            model_used: Model used for transcription
            retry_count: Number of retries so far

        Returns:
            QualityReport with score, recommendation, and issues
        """
        metrics = self._extract_metrics(transcription_result, video_duration)
        issues = self._identify_issues(metrics)
        score = self._calculate_score(metrics, issues)
        recommendation = self._get_recommendation(score, retry_count)
        suggested_model = self._get_suggested_model(model_used, recommendation)

        return QualityReport(
            overall_score=score,
            recommendation=recommendation,
            issues=issues,
            metrics=metrics,
            model_used=model_used,
            retry_count=retry_count,
            suggested_model=suggested_model,
        )

    def _extract_metrics(
        self,
        result: Dict[str, Any],
        video_duration: float,
    ) -> QualityMetrics:
        """Extract quality metrics from Whisper output."""
        segments = result.get("segments", [])

        if not segments:
            return QualityMetrics()

        # Thresholds from config
        thresholds = self.config.get("quality.metrics", {})
        logprob_min = thresholds.get("avg_logprob_min", -0.8)
        compression_max = thresholds.get("compression_ratio_max", 2.4)
        no_speech_max = thresholds.get("no_speech_prob_max", 0.6)

        # Calculate metrics
        logprobs = []
        compressions = []
        no_speech_probs = []
        low_confidence = 0
        high_compression = 0
        silent_with_text = 0
        total_words = 0

        for seg in segments:
            # Log probability (confidence)
            logprob = seg.get("avg_logprob", 0)
            logprobs.append(logprob)
            if logprob < logprob_min:
                low_confidence += 1

            # Compression ratio (hallucination indicator)
            compression = seg.get("compression_ratio", 1.0)
            compressions.append(compression)
            if compression > compression_max:
                high_compression += 1

            # No speech probability
            no_speech = seg.get("no_speech_prob", 0)
            no_speech_probs.append(no_speech)

            # Check for suspicious segments (high no_speech but has text)
            text = seg.get("text", "").strip()
            if no_speech > no_speech_max and len(text) > 10:
                silent_with_text += 1

            # Word count
            total_words += len(text.split())

        # Calculate averages
        avg_logprob = sum(logprobs) / len(logprobs) if logprobs else 0
        avg_compression = sum(compressions) / len(compressions) if compressions else 1
        avg_no_speech = sum(no_speech_probs) / len(no_speech_probs) if no_speech_probs else 0

        # Text density (words per second)
        text_density = total_words / video_duration if video_duration > 0 else 0

        return QualityMetrics(
            avg_logprob=avg_logprob,
            compression_ratio=avg_compression,
            no_speech_prob=avg_no_speech,
            text_density=text_density,
            total_segments=len(segments),
            low_confidence_segments=low_confidence,
            high_compression_segments=high_compression,
            silent_segments_with_text=silent_with_text,
        )

    def _identify_issues(self, metrics: QualityMetrics) -> List[str]:
        """Identify quality issues from metrics."""
        issues = []
        thresholds = self.config.get("quality.metrics", {})

        # Low confidence
        if metrics.avg_logprob < thresholds.get("avg_logprob_min", -0.8):
            issues.append(f"Low overall confidence (avg_logprob: {metrics.avg_logprob:.2f})")

        if metrics.low_confidence_segments > metrics.total_segments * 0.2:
            pct = (metrics.low_confidence_segments / metrics.total_segments) * 100
            issues.append(f"{pct:.0f}% of segments have low confidence")

        # Hallucination risk
        if metrics.compression_ratio > thresholds.get("compression_ratio_max", 2.4):
            issues.append(f"High compression ratio ({metrics.compression_ratio:.2f}) - possible hallucination")

        if metrics.high_compression_segments > metrics.total_segments * 0.1:
            pct = (metrics.high_compression_segments / metrics.total_segments) * 100
            issues.append(f"{pct:.0f}% of segments have hallucination risk")

        # Silent segments with text
        if metrics.silent_segments_with_text > 0:
            issues.append(f"{metrics.silent_segments_with_text} segments may be incorrectly transcribed (high no_speech_prob)")

        # Low text density
        if metrics.text_density < thresholds.get("text_density_min", 0.3):
            issues.append(f"Low text density ({metrics.text_density:.2f} words/sec) - possible audio issues")

        return issues

    def _calculate_score(self, metrics: QualityMetrics, issues: List[str]) -> float:
        """
        Calculate overall quality score (0.0 to 1.0).

        Higher is better. Based on:
        - Confidence (avg_logprob)
        - Hallucination risk (compression_ratio)
        - Issue count
        """
        # Base score from confidence (normalize logprob from [-1, 0] to [0, 1])
        confidence_score = max(0, min(1, (metrics.avg_logprob + 1)))

        # Compression penalty (normalize from [1, 3] to [1, 0])
        compression_score = max(0, min(1, (3 - metrics.compression_ratio) / 2))

        # Issue penalty
        issue_penalty = min(0.5, len(issues) * 0.1)

        # Weighted combination
        score = (
            confidence_score * 0.5 +
            compression_score * 0.3 +
            (1 - issue_penalty) * 0.2
        )

        return max(0, min(1, score))

    def _get_recommendation(self, score: float, retry_count: int) -> Recommendation:
        """Get recommendation based on score and retry count."""
        thresholds = self.config.get("quality.thresholds", {})
        max_retries = self.config.get("quality.max_retries", 2)

        accept_threshold = thresholds.get("accept", 0.8)
        warn_threshold = thresholds.get("warn", 0.6)
        retry_threshold = thresholds.get("retry", 0.4)

        if score >= accept_threshold:
            return Recommendation.ACCEPT
        elif score >= warn_threshold:
            return Recommendation.WARN
        elif score >= retry_threshold and retry_count < max_retries:
            return Recommendation.RETRY
        else:
            return Recommendation.FAIL

    def _get_suggested_model(
        self,
        current_model: str,
        recommendation: Recommendation,
    ) -> Optional[str]:
        """Get suggested model for retry."""
        if recommendation != Recommendation.RETRY:
            return None

        try:
            current_idx = self.MODEL_HIERARCHY.index(current_model)
            if current_idx < len(self.MODEL_HIERARCHY) - 1:
                return self.MODEL_HIERARCHY[current_idx + 1]
        except ValueError:
            pass

        return "large-v3"  # Default to best model

    def should_retry(self, report: QualityReport) -> bool:
        """Check if transcription should be retried."""
        return report.recommendation == Recommendation.RETRY

    def get_next_model(self, current_model: str) -> Optional[str]:
        """Get next model in hierarchy for retry."""
        try:
            current_idx = self.MODEL_HIERARCHY.index(current_model)
            if current_idx < len(self.MODEL_HIERARCHY) - 1:
                return self.MODEL_HIERARCHY[current_idx + 1]
        except ValueError:
            pass
        return None

    def format_report(self, report: QualityReport) -> str:
        """Format report as human-readable string."""
        lines = [
            f"Quality Score: {report.overall_score:.2%}",
            f"Recommendation: {report.recommendation.value.upper()}",
            f"Model Used: {report.model_used}",
        ]

        if report.issues:
            lines.append("\nIssues:")
            for issue in report.issues:
                lines.append(f"  - {issue}")

        if report.suggested_model:
            lines.append(f"\nSuggested: Retry with {report.suggested_model}")

        return "\n".join(lines)


def validate_transcription(
    result: Dict[str, Any],
    video_duration: float,
    model_used: str = "medium",
    retry_count: int = 0,
    output_path: Optional[str] = None,
) -> QualityReport:
    """
    Convenience function to validate transcription.

    Args:
        result: Whisper transcription output
        video_duration: Video duration in seconds
        model_used: Model used for transcription
        retry_count: Number of retries so far
        output_path: Optional path to save metrics JSON

    Returns:
        QualityReport
    """
    validator = QualityValidator()
    report = validator.validate(result, video_duration, model_used, retry_count)

    if output_path:
        report.save(output_path)

    return report
