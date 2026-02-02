#!/usr/bin/env python3
"""
Video to Knowledge Base Converter - MLX Optimized for Apple Silicon M4

This script uses mlx-whisper for 30-40% faster transcription on Apple Silicon
compared to standard OpenAI Whisper, with native Metal acceleration.

Usage:
    python3 video_to_knowledge_base_mlx.py "video.mp4" -m large-v3 -l es

Models available (via mlx-community on HuggingFace):
    - tiny, base, small, medium, large, large-v2, large-v3 (best accuracy)
    - distil-large-v3 (fast + good accuracy)
"""

import argparse
import logging
import os
import sys
import base64
import tempfile
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# MLX model mapping to HuggingFace repos
MLX_MODELS = {
    "tiny": "mlx-community/whisper-tiny-mlx",
    "tiny.en": "mlx-community/whisper-tiny.en-mlx",
    "base": "mlx-community/whisper-base-mlx",
    "base.en": "mlx-community/whisper-base.en-mlx",
    "small": "mlx-community/whisper-small-mlx",
    "small.en": "mlx-community/whisper-small.en-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "medium.en": "mlx-community/whisper-medium.en-mlx",
    "large": "mlx-community/whisper-large-v3-mlx",
    "large-v2": "mlx-community/whisper-large-v2-mlx",
    "large-v3": "mlx-community/whisper-large-v3-mlx",
    # Quantized versions for faster inference (slightly lower quality)
    "large-v3-4bit": "mlx-community/whisper-large-v3-mlx-4bit",
    "medium-4bit": "mlx-community/whisper-medium-mlx-4bit",
}


def get_model_repo(model_name: str) -> str:
    """Get the HuggingFace repo for the model."""
    if model_name in MLX_MODELS:
        return MLX_MODELS[model_name]
    # If it's already a full repo path, return as-is
    if "/" in model_name:
        return model_name
    # Default to large-v3 for unknown models
    logger.warning(f"Unknown model '{model_name}', defaulting to large-v3")
    return MLX_MODELS["large-v3"]


def transcribe_with_mlx(audio_path: str, model_name: str = "large-v3",
                        language: str = None) -> dict:
    """
    Transcribe audio using mlx-whisper (optimized for Apple Silicon).

    Returns dict with 'text' and 'segments' keys.
    """
    import mlx_whisper

    model_repo = get_model_repo(model_name)
    logger.info(f"Loading MLX Whisper model: {model_repo}")
    logger.info(f"Using Apple Silicon MLX acceleration (Metal GPU)")

    # Transcribe with word-level timestamps
    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=model_repo,
        language=language,
        word_timestamps=True,
        verbose=False
    )

    return result


def format_timestamp(seconds: float) -> str:
    """Format seconds to MM:SS or HH:MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def extract_frames_at_timestamps(video_path: str, timestamps: list,
                                  output_dir: str) -> dict:
    """Extract frames at specific timestamps using ffmpeg."""
    import subprocess

    frames = {}
    for i, ts in enumerate(timestamps):
        output_path = os.path.join(output_dir, f"frame_{i:04d}_{ts:.2f}.jpg")

        cmd = [
            "ffmpeg", "-y", "-ss", str(ts), "-i", video_path,
            "-vframes", "1", "-q:v", "2", output_path
        ]

        try:
            subprocess.run(cmd, capture_output=True, check=True)
            if os.path.exists(output_path):
                frames[ts] = output_path
        except subprocess.CalledProcessError:
            continue

    return frames


def detect_scene_changes(video_path: str, threshold: float = 0.3,
                         min_interval: float = 5.0) -> list:
    """Detect scene changes using ffmpeg scene detection filter."""
    import subprocess
    import re

    logger.info(f"Analyzing scene changes in: {os.path.basename(video_path)}")

    cmd = [
        "ffprobe", "-v", "quiet", "-show_entries", "frame=pts_time",
        "-select_streams", "v:0", "-of", "csv=p=0",
        "-f", "lavfi", f"movie={video_path},select='gt(scene,{threshold})'"
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        timestamps = []
        last_ts = -min_interval

        for line in result.stdout.strip().split('\n'):
            if line:
                try:
                    ts = float(line)
                    if ts - last_ts >= min_interval:
                        timestamps.append(ts)
                        last_ts = ts
                except ValueError:
                    continue

        logger.info(f"Detected {len(timestamps)} scene changes")
        return timestamps

    except Exception as e:
        logger.warning(f"Scene detection failed: {e}, using interval sampling")
        return sample_video_timestamps(video_path, interval=10.0)


def sample_video_timestamps(video_path: str, interval: float = 10.0) -> list:
    """Sample timestamps at regular intervals."""
    import subprocess

    # Get video duration
    cmd = [
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        timestamps = [i * interval for i in range(int(duration / interval) + 1)]
        return timestamps
    except:
        return [0, 30, 60, 120, 180]  # Fallback


def image_to_base64(image_path: str) -> str:
    """Convert image to base64 string."""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def generate_knowledge_base(video_path: str, transcription: dict,
                            frames: dict, output_path: str):
    """Generate a markdown knowledge base document."""

    video_name = Path(video_path).stem
    segments = transcription.get("segments", [])

    # Build markdown content
    md_lines = [
        "---",
        f"title: \"{video_name}\"",
        f"source: \"{os.path.basename(video_path)}\"",
        f"generated: \"{datetime.now().isoformat()}\"",
        f"transcription_engine: mlx-whisper (Apple Silicon optimized)",
        f"total_segments: {len(segments)}",
        f"total_frames: {len(frames)}",
        "---",
        "",
        f"# {video_name}",
        "",
        "## Full Transcription",
        "",
    ]

    # Add transcription with timestamps
    current_section_start = 0
    section_interval = 300  # 5 minutes per section

    for segment in segments:
        start = segment.get("start", 0)
        end = segment.get("end", 0)
        text = segment.get("text", "").strip()

        # Add section header every 5 minutes
        if start >= current_section_start + section_interval:
            current_section_start = (start // section_interval) * section_interval
            md_lines.append("")
            md_lines.append(f"### [{format_timestamp(current_section_start)}]")
            md_lines.append("")

        # Add segment
        md_lines.append(f"**[{format_timestamp(start)} - {format_timestamp(end)}]** {text}")
        md_lines.append("")

        # Add frame if available near this timestamp
        for frame_ts, frame_path in list(frames.items()):
            if abs(frame_ts - start) < 3:  # Within 3 seconds
                try:
                    b64 = image_to_base64(frame_path)
                    md_lines.append(f"![Frame at {format_timestamp(frame_ts)}](data:image/jpeg;base64,{b64})")
                    md_lines.append("")
                    del frames[frame_ts]  # Don't reuse
                except Exception as e:
                    logger.warning(f"Failed to embed frame: {e}")
                break

    # Write output
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    logger.info(f"Knowledge base generated: {output_path}")
    logger.info(f"File size: {file_size:.2f} MB")


def main():
    parser = argparse.ArgumentParser(
        description="Convert video to LLM-friendly knowledge base using MLX Whisper"
    )
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("-m", "--model", default="medium",
                        choices=list(MLX_MODELS.keys()),
                        help="Whisper model (default: medium for speed/quality balance)")
    parser.add_argument("-l", "--language", default=None,
                        help="Language code (e.g., 'en', 'es'). Auto-detect if not specified.")
    parser.add_argument("--threshold", type=float, default=0.3,
                        help="Scene change detection threshold (0.0-1.0)")
    parser.add_argument("--min-interval", type=float, default=5.0,
                        help="Minimum interval between frames (seconds)")
    parser.add_argument("-o", "--output", default=None,
                        help="Output path (default: video_name.knowledge.md)")

    args = parser.parse_args()

    # Validate input
    if not os.path.exists(args.video):
        logger.error(f"Video file not found: {args.video}")
        sys.exit(1)

    video_path = os.path.abspath(args.video)
    video_name = Path(video_path).stem
    output_path = args.output or f"{video_name}.knowledge.md"

    # Print header
    logger.info("=" * 70)
    logger.info("VIDEO TO KNOWLEDGE BASE - MLX OPTIMIZED FOR APPLE SILICON")
    logger.info("=" * 70)
    logger.info(f"Video: {os.path.basename(video_path)}")
    logger.info(f"Model: {args.model} (via mlx-community)")
    logger.info(f"Language: {args.language or 'auto-detect'}")
    logger.info("=" * 70)

    # Step 1: Transcribe
    logger.info("")
    logger.info("STEP 1: Transcribing with MLX Whisper...")
    transcription = transcribe_with_mlx(video_path, args.model, args.language)
    logger.info(f"Transcription complete: {len(transcription.get('segments', []))} segments")

    # Step 2: Extract frames
    logger.info("")
    logger.info("STEP 2: Extracting key frames...")

    with tempfile.TemporaryDirectory() as temp_dir:
        # Detect scene changes
        timestamps = detect_scene_changes(video_path, args.threshold, args.min_interval)

        # Add timestamps from transcription segments (every 30 seconds)
        segment_timestamps = set()
        for seg in transcription.get("segments", []):
            ts = seg.get("start", 0)
            if ts > 0 and int(ts) % 30 < 3:  # Near 30-second marks
                segment_timestamps.add(round(ts))

        all_timestamps = sorted(set(timestamps) | segment_timestamps)
        logger.info(f"Extracting {len(all_timestamps)} frames...")

        frames = extract_frames_at_timestamps(video_path, all_timestamps, temp_dir)
        logger.info(f"Extracted {len(frames)} frames successfully")

        # Step 3: Generate knowledge base
        logger.info("")
        logger.info("STEP 3: Generating knowledge base markdown...")
        generate_knowledge_base(video_path, transcription, frames, output_path)

    # Done
    logger.info("")
    logger.info("=" * 70)
    logger.info("PROCESS COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Output: {output_path}")
    logger.info("Ready for LLMs and AI agents")
    logger.info("=" * 70)


if __name__ == "__main__":
    main()
