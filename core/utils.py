"""
Shared utilities for VideoATexto.
Common functions used across multiple scripts.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import Optional, Tuple


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted string like "1h 23m 45s" or "5m 30s"
    """
    if seconds < 0:
        return "0s"

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0 or hours > 0:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")

    return " ".join(parts)


def format_timestamp(seconds: float, include_hours: bool = False) -> str:
    """
    Format timestamp for display.

    Args:
        seconds: Time in seconds
        include_hours: Always include hours even if 0

    Returns:
        Formatted timestamp like "01:23" or "1:23:45"
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0 or include_hours:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def sanitize_filename(filename: str, max_length: int = 200) -> str:
    """
    Sanitize filename by removing invalid characters.

    Args:
        filename: Original filename
        max_length: Maximum allowed length

    Returns:
        Safe filename
    """
    # Remove or replace invalid characters
    invalid_chars = r'[<>:"/\\|?*\x00-\x1f]'
    safe_name = re.sub(invalid_chars, "_", filename)

    # Remove leading/trailing whitespace and dots
    safe_name = safe_name.strip(". ")

    # Collapse multiple underscores
    safe_name = re.sub(r"_+", "_", safe_name)

    # Truncate if too long (preserve extension)
    if len(safe_name) > max_length:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[: max_length - len(ext)] + ext

    return safe_name or "unnamed"


def get_video_duration(video_path: str) -> Optional[float]:
    """
    Get video duration using ffprobe.

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds or None if failed
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            return float(result.stdout.strip())

    except Exception:
        pass

    return None


def get_audio_bitrate(file_path: str) -> Optional[int]:
    """
    Get audio bitrate using ffprobe.

    Args:
        file_path: Path to audio/video file

    Returns:
        Bitrate in kbps or None if failed
    """
    try:
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-select_streams", "a:0",
            "-show_entries", "stream=bit_rate",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0 and result.stdout.strip():
            bitrate = int(result.stdout.strip())
            return bitrate // 1000  # Convert to kbps

    except Exception:
        pass

    return None


def get_file_size_mb(file_path: str) -> float:
    """Get file size in megabytes."""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except Exception:
        return 0.0


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, creating it if necessary.

    Args:
        path: Directory path

    Returns:
        Path object for the directory
    """
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def find_media_files(
    directory: str,
    extensions: Optional[list] = None,
    recursive: bool = False,
) -> list:
    """
    Find media files in directory.

    Args:
        directory: Directory to search
        extensions: List of extensions (default: video and audio formats)
        recursive: Search subdirectories

    Returns:
        List of file paths
    """
    if extensions is None:
        extensions = [
            # Video
            ".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".m4v", ".webm",
            # Audio
            ".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac",
        ]

    extensions = [ext.lower() if ext.startswith(".") else f".{ext.lower()}" for ext in extensions]

    dir_path = Path(directory)
    if not dir_path.exists():
        return []

    files = []
    pattern = "**/*" if recursive else "*"

    for file_path in dir_path.glob(pattern):
        if file_path.is_file() and file_path.suffix.lower() in extensions:
            files.append(str(file_path))

    return sorted(files)


def estimate_processing_time(
    duration_seconds: float,
    model_size: str = "medium",
    device: str = "mps",
) -> float:
    """
    Estimate processing time based on video duration and model.

    Args:
        duration_seconds: Video duration in seconds
        model_size: Whisper model size
        device: Compute device

    Returns:
        Estimated processing time in seconds
    """
    # Base ratios (processing time / video duration) on MPS
    ratios = {
        "tiny": 0.05,
        "base": 0.07,
        "small": 0.13,
        "medium": 0.25,
        "large-v3": 0.47,
        "large": 0.47,
    }

    ratio = ratios.get(model_size, 0.25)

    # Adjust for device
    if device == "cpu":
        ratio *= 3.0
    elif device == "cuda":
        ratio *= 0.8

    return duration_seconds * ratio


def check_ffmpeg() -> bool:
    """Check if FFmpeg is installed and accessible."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_ffprobe() -> bool:
    """Check if FFprobe is installed and accessible."""
    try:
        result = subprocess.run(
            ["ffprobe", "-version"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False
