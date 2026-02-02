#!/usr/bin/env python3
"""
Transcribo - Simple audio/video to text transcription.
Auto-detects GPU acceleration: MPS (Apple Silicon), CUDA (NVIDIA), or CPU fallback.
Supports all Whisper model sizes with global model caching.
"""

import os
import sys
import argparse
import logging
import torch
import ssl
from pathlib import Path

# Fix SSL certificate issues for model downloads
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import whisper
except ImportError as e:
    print(f"Error: Whisper no está instalado. Ejecuta: pip install openai-whisper")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache global para el modelo
_model_cache = {}

def get_device():
    """Detect optimal compute device."""
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        logger.info("Using Apple Silicon (MPS)")
        return "mps"
    elif torch.cuda.is_available():
        logger.info("Using NVIDIA GPU (CUDA)")
        return "cuda"
    else:
        logger.info("Using CPU")
        return "cpu"

def transcribe_audio(audio_path, model_size="base", language=None, include_timestamps=False, device=None):
    """Transcribir archivo de audio a texto con optimizaciones M4"""

    if device is None:
        device = get_device()

    # Usar caché para el modelo
    cache_key = f"{model_size}_{device}"
    if cache_key not in _model_cache:
        logger.info(f"Cargando modelo Whisper: {model_size} en {device}")
        model = whisper.load_model(model_size, device=device)
        _model_cache[cache_key] = model
    else:
        logger.info(f"Usando modelo cacheado: {model_size}")
        model = _model_cache[cache_key]

    logger.info(f"Transcribiendo: {audio_path}")

    # Configurar opciones optimizadas
    options = {
        'language': language,
        'fp16': device == "mps",  # Usar fp16 en MPS para mejor rendimiento
        'verbose': False,
    }
    if language is None:
        del options['language']

    # Transcribir
    result = model.transcribe(audio_path, **options)

    # Crear archivo de salida
    input_path = Path(audio_path)
    output_path = input_path.with_suffix('.txt')

    logger.info(f"Guardando transcripción: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        if include_timestamps:
            for segment in result['segments']:
                start = int(segment['start'] // 60), int(segment['start'] % 60)
                end = int(segment['end'] // 60), int(segment['end'] % 60)
                text = segment['text'].strip()
                f.write(f"[{start[0]:02d}:{start[1]:02d} - {end[0]:02d}:{end[1]:02d}] {text}\n")
        else:
            f.write(result['text'].strip())

    logger.info("✅ Transcripción completada")
    return str(output_path)

def main():
    parser = argparse.ArgumentParser(description="Transcribo - Audio/video to text with Whisper")
    parser.add_argument("audio", help="Audio or video file to transcribe")
    parser.add_argument("-m", "--model", default="small",
                       choices=["tiny", "base", "small", "medium", "large", "turbo"],
                       help="Whisper model (default: small)")
    parser.add_argument("-l", "--language", help="Language code (e.g. es, en)")
    parser.add_argument("-t", "--timestamps", action="store_true",
                       help="Include timestamps in output")
    parser.add_argument("-d", "--device", choices=["mps", "cpu", "cuda"],
                       help="Compute device (default: auto-detect)")

    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Error: No se encuentra el archivo {args.audio}")
        sys.exit(1)

    try:
        output_file = transcribe_audio(
            args.audio,
            args.model,
            args.language,
            args.timestamps,
            args.device
        )
        print(f"✅ Transcripción guardada en: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()