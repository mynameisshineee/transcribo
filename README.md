# transcribo

Video and audio transcription toolkit powered by OpenAI Whisper. Auto-detects GPU acceleration on Apple Silicon (MPS), NVIDIA (CUDA), or falls back to CPU.

## Features

- **Multi-format**: MP4, MKV, AVI, MOV, MP3, WAV, M4A, FLAC, and more
- **GPU accelerated**: Apple Silicon (MPS), NVIDIA CUDA, or CPU
- **YouTube support**: Download and transcribe with one command
- **Knowledge base output**: Rich Markdown with embedded screenshots for LLMs/RAG
- **Batch processing**: Process entire folders of media files
- **Smart model selection**: Auto-selects Whisper model based on content importance
- **Quality validation**: Built-in transcription quality checks

## Quick Start

```bash
git clone https://github.com/YOUR_USER/transcribo.git
cd transcribo
./install.sh
source venv/bin/activate
```

### Transcribe a file

```bash
python3 simple_audio_to_text.py "video.mp4" -m base -l es
```

### Transcribe with timestamps

```bash
python3 simple_audio_to_text.py "video.mp4" -m small -l en -t
```

### Transcribe from YouTube

```bash
python3 cli_pipeline.py "https://youtube.com/watch?v=xxx" -l en
```

### Generate a knowledge base (Markdown + screenshots)

```bash
python3 video_to_knowledge_base_mlx.py "video.mp4" -m medium -l en
# Output: video.knowledge.md (self-contained Markdown with base64 images)
```

## Scripts

| Script | Purpose |
|--------|---------|
| `simple_audio_to_text.py` | Single file transcription (text output) |
| `cli_pipeline.py` | Unified pipeline: download + transcribe + validate + organize |
| `video_to_knowledge_base_mlx.py` | Rich Markdown output with embedded images (Apple Silicon) |
| `video_to_knowledge_base.py` | Rich Markdown output (cross-platform, OpenAI Whisper) |
| `url_to_text.py` | Download and transcribe from URL |
| `process_all_videos_parallel.py` | Batch process a directory |
| `transcribe.sh` | Quick bash wrapper |
| `setup_m4_optimization.py` | System diagnostics and GPU check |
| `benchmark_models.py` | Benchmark different models/devices |
| `extract_knowledge.py` | Analyze and cross-reference knowledge base files |

## Models

| Model | Accuracy | Speed | Use case |
|-------|----------|-------|----------|
| `tiny` | Basic | Fastest | Testing |
| `base` | Good | Fast | Quick transcriptions |
| `small` | Better | Moderate | General use |
| `medium` | High | Slower | **Recommended default** |
| `large-v3` | Best | Slowest | Important content |

## Configuration

Edit `config.yaml` to customize:

- Default model and language
- Knowledge base destination folder
- Importance auto-detection keywords and thresholds
- Quality validation settings
- YouTube download format

User config can also be placed at `~/.transcribo/config.yaml`.

### Smart Model Selection

The pipeline can auto-select models based on content importance:

| Importance (1-10) | Model | Trigger keywords |
|--------------------|-------|------------------|
| 1-3 (Low) | `small` | test, draft, temp |
| 4-7 (Medium) | `medium` | webinar, demo, charla |
| 8-10 (High) | `large-v3` | curso, tutorial, masterclass |

```bash
# Manual importance
python3 cli_pipeline.py "video.mp4" -i 8          # -> large-v3

# Category-based
python3 cli_pipeline.py "video.mp4" -I high        # -> large-v3

# Auto-detect from filename/duration
python3 cli_pipeline.py "video.mp4"                 # -> auto
```

## Supported Platforms

| Platform | GPU Acceleration | Status |
|----------|-----------------|--------|
| macOS (Apple Silicon) | MPS (Metal) | Full support |
| macOS (Intel) | CPU only | Works |
| Linux (NVIDIA) | CUDA | Full support |
| Linux (no GPU) | CPU only | Works |

## Supported Formats

**Video**: MP4, AVI, MOV, MKV, FLV, WMV, M4V, WebM
**Audio**: MP3, WAV, M4A, AAC, OGG, FLAC

## Dependencies

- Python 3.9+
- [FFmpeg](https://ffmpeg.org/)
- [OpenAI Whisper](https://github.com/openai/whisper)
- PyTorch (with MPS or CUDA support)
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) (optional, for YouTube)
- [MLX Whisper](https://github.com/ml-explore/mlx-examples) (optional, Apple Silicon only)

## Troubleshooting

```bash
# Run diagnostics
python3 setup_m4_optimization.py

# Force CPU if GPU has issues
python3 simple_audio_to_text.py "file.mp4" -d cpu

# FFmpeg missing
# macOS:  brew install ffmpeg
# Linux:  sudo apt install ffmpeg
```

## License

MIT
