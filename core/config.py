"""
Configuration management for Transcribo.
Loads settings from config.yaml with sensible defaults.
"""

import os
from pathlib import Path
from typing import Any, Optional
import yaml

# Singleton instance
_config_instance: Optional["Config"] = None


class Config:
    """Centralized configuration manager."""

    DEFAULT_CONFIG = {
        "paths": {
            "knowledge_base_destination": None,
            "temp_download_dir": "./downloads",
            "output_dir": None,
        },
        "transcription": {
            "default_model": "medium",
            "default_language": None,
            "engine": "mlx",
            "frame_extraction": {
                "enabled": True,
                "threshold": 0.3,
                "min_interval": 5,
                "max_frames": 20,
            },
        },
        "importance": {
            "thresholds": {
                "low": {"max_score": 3, "model": "small"},
                "medium": {"max_score": 7, "model": "medium"},
                "high": {"max_score": 10, "model": "large-v3"},
            },
            "auto_detection": {
                "enabled": True,
                "weights": {
                    "duration": 0.25,
                    "audio_quality": 0.20,
                    "filename_keywords": 0.30,
                    "source_folder": 0.15,
                    "file_size": 0.10,
                },
            },
            "filename_keywords": {
                "high": ["curso", "tutorial", "formacion", "masterclass", "conferencia"],
                "medium": ["charla", "demo", "webinar", "presentacion"],
                "low": ["test", "prueba", "draft", "borrador"],
            },
        },
        "quality": {
            "enabled": True,
            "thresholds": {
                "accept": 0.8,
                "warn": 0.6,
                "retry": 0.4,
                "fail": 0.4,
            },
            "max_retries": 2,
            "metrics": {
                "avg_logprob_min": -0.8,
                "compression_ratio_max": 2.4,
                "no_speech_prob_max": 0.6,
                "text_density_min": 0.3,
            },
        },
        "workflow": {
            "ask_importance": True,
            "confirm_before_process": False,
            "auto_move": True,
            "cleanup_sources": True,
            "skip_existing": True,
            "youtube": {
                "format": "best[height<=360]",
                "extract_audio_only": False,
            },
        },
        "logging": {
            "level": "INFO",
            "save_metrics": True,
            "verbose_progress": True,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration.

        Args:
            config_path: Path to config.yaml. If None, searches in standard locations.
        """
        self._config = self._deep_copy(self.DEFAULT_CONFIG)
        self._config_path = self._find_config(config_path)

        if self._config_path and self._config_path.exists():
            self._load_config()

    def _find_config(self, config_path: Optional[str]) -> Optional[Path]:
        """Find config file in standard locations."""
        if config_path:
            return Path(config_path)

        # Search locations in order
        search_paths = [
            Path.cwd() / "config.yaml",
            Path(__file__).parent.parent / "config.yaml",
            Path.home() / ".transcribo" / "config.yaml",
        ]

        for path in search_paths:
            if path.exists():
                return path

        return search_paths[0]  # Default to cwd

    def _load_config(self) -> None:
        """Load configuration from YAML file."""
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                user_config = yaml.safe_load(f) or {}
            self._merge_config(self._config, user_config)
        except Exception as e:
            print(f"Warning: Could not load config from {self._config_path}: {e}")

    def _deep_copy(self, d: dict) -> dict:
        """Deep copy a dictionary."""
        import copy
        return copy.deepcopy(d)

    def _merge_config(self, base: dict, override: dict) -> None:
        """Recursively merge override into base."""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value using dot notation.

        Example:
            config.get("transcription.default_model")
            config.get("quality.thresholds.accept")
        """
        keys = key.split(".")
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any) -> None:
        """Set configuration value using dot notation."""
        keys = key.split(".")
        config = self._config

        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        config[keys[-1]] = value

    @property
    def default_model(self) -> str:
        return self.get("transcription.default_model", "medium")

    @property
    def default_language(self) -> Optional[str]:
        return self.get("transcription.default_language")

    @property
    def knowledge_base_destination(self) -> Optional[str]:
        return self.get("paths.knowledge_base_destination")

    @property
    def quality_enabled(self) -> bool:
        return self.get("quality.enabled", True)

    @property
    def max_retries(self) -> int:
        return self.get("quality.max_retries", 2)

    def get_model_for_importance(self, importance: int) -> str:
        """Get recommended model based on importance score (1-10)."""
        thresholds = self.get("importance.thresholds", {})

        if importance <= thresholds.get("low", {}).get("max_score", 3):
            return thresholds.get("low", {}).get("model", "small")
        elif importance <= thresholds.get("medium", {}).get("max_score", 7):
            return thresholds.get("medium", {}).get("model", "medium")
        else:
            return thresholds.get("high", {}).get("model", "large-v3")

    def get_importance_keywords(self, level: str) -> list:
        """Get keywords for importance level (high, medium, low)."""
        return self.get(f"importance.filename_keywords.{level}", [])

    def __repr__(self) -> str:
        return f"Config(path={self._config_path})"


def get_config(config_path: Optional[str] = None) -> Config:
    """Get or create singleton Config instance."""
    global _config_instance

    if _config_instance is None or config_path is not None:
        _config_instance = Config(config_path)

    return _config_instance
