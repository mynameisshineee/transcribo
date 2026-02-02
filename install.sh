#!/bin/bash
# Transcribo - Cross-platform installer (macOS + Linux)

set -e

echo "Installing Transcribo..."
echo ""

# Check Python 3
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    echo ""
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "  brew install python3"
    else
        echo "  sudo apt install python3 python3-venv python3-pip"
    fi
    exit 1
fi

# Check FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "Warning: FFmpeg not found (required for video processing)"
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "  brew install ffmpeg"
    else
        echo "  sudo apt install ffmpeg"
    fi
    echo ""
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv

# Activate
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip -q

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Optional: Install MLX Whisper on Apple Silicon
if [[ "$(uname)" == "Darwin" && "$(uname -m)" == "arm64" ]]; then
    echo "Apple Silicon detected - installing MLX Whisper..."
    pip install mlx-whisper -q 2>/dev/null || echo "Note: mlx-whisper optional, using openai-whisper"
fi

# Optional: Install yt-dlp for YouTube support
pip install yt-dlp -q 2>/dev/null || echo "Note: yt-dlp optional (for YouTube downloads)"

# Verify
echo ""
echo "Verifying installation..."
python3 -c "import whisper; print('  whisper: OK')"
python3 -c "import torch; print(f'  torch:   OK ({torch.__version__})')"
python3 -c "
import torch
if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
    print('  GPU:     Apple Silicon (MPS)')
elif torch.cuda.is_available():
    print(f'  GPU:     NVIDIA CUDA ({torch.version.cuda})')
else:
    print('  GPU:     None (using CPU)')
"

echo ""
echo "Installation complete!"
echo ""
echo "Usage:"
echo "  source venv/bin/activate"
echo "  python3 simple_audio_to_text.py \"file.mp4\" -m base -l es"
echo "  python3 cli_pipeline.py \"https://youtube.com/watch?v=xxx\""
echo ""
echo "Run diagnostics:  python3 setup_m4_optimization.py"