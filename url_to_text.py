#!/usr/bin/env python3
"""
Transcribo - Download and transcribe videos from YouTube and 1000+ sites.
Uses yt-dlp for downloading and Whisper for transcription.

Usage:
    python3 url_to_text.py "https://youtube.com/watch?v=xxx" -m base -l es -t
    python3 url_to_text.py "https://vimeo.com/xxx" -m small -l en
"""

import os
import sys
import argparse
import logging
import tempfile
import torch
import ssl
from pathlib import Path

ssl._create_default_https_context = ssl._create_unverified_context

try:
    import yt_dlp
except ImportError:
    print("Error: yt-dlp no está instalado. Ejecuta: pip install yt-dlp")
    sys.exit(1)

try:
    import whisper
except ImportError:
    print("Error: Whisper no está instalado. Ejecuta: pip install openai-whisper")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

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

def download_audio(url, output_dir=None):
    """Descargar solo el audio de una URL usando yt-dlp"""

    if output_dir is None:
        output_dir = tempfile.gettempdir()

    logger.info(f"📥 Descargando audio de: {url}")

    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(output_dir, '%(title)s.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'video')
        # El archivo se guarda como .mp3 después del postprocesador
        audio_path = os.path.join(output_dir, f"{title}.mp3")

        # Sanitizar nombre de archivo (yt-dlp lo hace automáticamente)
        safe_title = yt_dlp.utils.sanitize_filename(title)
        audio_path = os.path.join(output_dir, f"{safe_title}.mp3")

    logger.info(f"✅ Audio descargado: {audio_path}")
    return audio_path, title

def transcribe_audio(audio_path, model_size="base", language=None, include_timestamps=False, device=None):
    """Transcribir archivo de audio a texto"""

    if device is None:
        device = get_device()

    cache_key = f"{model_size}_{device}"
    if cache_key not in _model_cache:
        logger.info(f"🧠 Cargando modelo Whisper: {model_size} en {device}")
        model = whisper.load_model(model_size, device=device)
        _model_cache[cache_key] = model
    else:
        logger.info(f"🧠 Usando modelo cacheado: {model_size}")
        model = _model_cache[cache_key]

    logger.info(f"🎯 Transcribiendo...")

    options = {
        'language': language,
        'fp16': device == "mps",
        'verbose': False,
    }
    if language is None:
        del options['language']

    result = model.transcribe(audio_path, **options)

    return result

def save_transcription(result, output_path, include_timestamps=False):
    """Guardar transcripción a archivo"""

    with open(output_path, 'w', encoding='utf-8') as f:
        if include_timestamps:
            for segment in result['segments']:
                start = int(segment['start'] // 60), int(segment['start'] % 60)
                end = int(segment['end'] // 60), int(segment['end'] % 60)
                text = segment['text'].strip()
                f.write(f"[{start[0]:02d}:{start[1]:02d} - {end[0]:02d}:{end[1]:02d}] {text}\n")
        else:
            f.write(result['text'].strip())

    logger.info(f"💾 Transcripción guardada: {output_path}")
    return output_path

def main():
    parser = argparse.ArgumentParser(
        description="Descargar y transcribir videos de YouTube y 1000+ sitios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
    python3 url_to_text.py "https://youtube.com/watch?v=xxx" -l es
    python3 url_to_text.py "https://vimeo.com/xxx" -m small -l en -t
    python3 url_to_text.py "https://twitter.com/xxx/status/xxx" -l es -t

Sitios soportados: YouTube, Vimeo, Twitter/X, TikTok, Instagram, y 1000+ más
Lista completa: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
        """
    )
    parser.add_argument("url", help="URL del video (YouTube, Vimeo, Twitter, etc.)")
    parser.add_argument("-m", "--model", default="base",
                       choices=["tiny", "base", "small", "medium", "large", "turbo"],
                       help="Modelo Whisper (default: base)")
    parser.add_argument("-l", "--language", help="Idioma (ej: es, en)")
    parser.add_argument("-t", "--timestamps", action="store_true",
                       help="Incluir timestamps")
    parser.add_argument("-d", "--device", choices=["mps", "cpu", "cuda"],
                       help="Dispositivo (default: auto)")
    parser.add_argument("-o", "--output", help="Directorio de salida (default: actual)")
    parser.add_argument("-k", "--keep", action="store_true",
                       help="Mantener archivo de audio descargado")

    args = parser.parse_args()

    output_dir = args.output or os.getcwd()

    try:
        # 1. Descargar audio
        audio_path, title = download_audio(args.url, output_dir if args.keep else None)

        # 2. Transcribir
        result = transcribe_audio(
            audio_path,
            args.model,
            args.language,
            args.timestamps,
            args.device
        )

        # 3. Guardar transcripción
        safe_title = yt_dlp.utils.sanitize_filename(title)
        output_path = os.path.join(output_dir, f"{safe_title}.txt")
        save_transcription(result, output_path, args.timestamps)

        # 4. Limpiar archivo temporal si no se quiere mantener
        if not args.keep and os.path.exists(audio_path):
            os.remove(audio_path)
            logger.info("🧹 Archivo temporal eliminado")

        print(f"\n✅ Transcripción completada: {output_path}")

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
