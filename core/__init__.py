"""
Core module for Transcribo transcription system.
Provides unified configuration, device detection, model caching, and quality validation.
"""

from .config import Config, get_config
from .device import get_device, get_device_info
from .model_cache import ModelCache, get_model_cache
from .quality_validator import (
    QualityValidator,
    QualityReport,
    QualityMetrics,
    Recommendation,
    validate_transcription,
)
from .importance import (
    ImportanceAssessor,
    ImportanceAssessment,
    assess_importance,
    get_model_for_video,
)
from .utils import (
    format_duration,
    format_timestamp,
    sanitize_filename,
    get_video_duration,
    get_audio_bitrate,
)

__all__ = [
    # Config
    "Config",
    "get_config",
    # Device
    "get_device",
    "get_device_info",
    # Model Cache
    "ModelCache",
    "get_model_cache",
    # Quality Validation
    "QualityValidator",
    "QualityReport",
    "QualityMetrics",
    "Recommendation",
    "validate_transcription",
    # Importance Assessment
    "ImportanceAssessor",
    "ImportanceAssessment",
    "assess_importance",
    "get_model_for_video",
    # Utils
    "format_duration",
    "format_timestamp",
    "sanitize_filename",
    "get_video_duration",
    "get_audio_bitrate",
]
