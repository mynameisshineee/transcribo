# CLAUDE.md - Transcribo

## Project Overview

Cross-platform video/audio transcription toolkit using OpenAI Whisper with GPU acceleration.

## Key Commands

```bash
source venv/bin/activate

# Simple transcription
python3 simple_audio_to_text.py "file.mp4" -m base -l es

# Knowledge base generation (MLX - Apple Silicon)
python3 video_to_knowledge_base_mlx.py "video.mp4" -m medium -l en

# Knowledge base generation (cross-platform)
python3 video_to_knowledge_base.py "video.mp4" -m medium -l en

# Unified pipeline (download + transcribe + validate)
python3 cli_pipeline.py "https://youtube.com/watch?v=xxx" -l en

# Batch processing
python3 process_all_videos_parallel.py /path/to/videos

# Diagnostics
python3 setup_m4_optimization.py
```

## Architecture

- `core/` - Shared modules (config, device detection, model cache, quality validation, importance assessment)
- `config.yaml` - Centralized configuration
- `cli_pipeline.py` - Main unified pipeline
- `simple_audio_to_text.py` - Minimal transcription script
- `video_to_knowledge_base_mlx.py` - MLX-optimized knowledge base generator (Apple Silicon)
- `video_to_knowledge_base.py` - Cross-platform knowledge base generator

## Device Detection

Auto-detects in order: MPS (Apple Silicon) > CUDA (NVIDIA) > CPU. See `core/device.py`.

## Models

Default: `medium`. Use `large-v3` for important content, `small`/`base` for quick jobs.

## Dependencies

All in `requirements.txt`. FFmpeg required externally. Optional: `mlx-whisper` (Apple Silicon), `yt-dlp` (YouTube).
