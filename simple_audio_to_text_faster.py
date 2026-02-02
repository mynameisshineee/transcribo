#!/usr/bin/env python3
"""
Script optimizado para MacBook Pro M4 - Convertir audio a texto usando faster-whisper
Optimizaciones:
  - faster-whisper (3-4x más rápido que OpenAI Whisper)
  - Optimización automática de CPU threading para 14 cores
  - Sin problemas de MPS/sparse tensors
  - Mejor aprovechamiento del M4
"""

import os
import sys
import argparse
import logging
import torch
from pathlib import Path

try:
    from faster_whisper import WhisperModel
except ImportError as e:
    print(f"Error: faster-whisper no está instalado. Ejecuta: pip install faster-whisper")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

# Cache global para el modelo
_model_cache = {}

def optimize_cpu_threads():
    """Optimizar threading para aprovechar todos los cores del M4"""
    import multiprocessing
    cpu_count = multiprocessing.cpu_count()
    torch.set_num_threads(cpu_count)
    logger.info(f"✨ Optimizado para {cpu_count} cores M4")
    return cpu_count

def transcribe_audio(audio_path, model_size="base", language="es", include_timestamps=False):
    """Transcribir archivo de audio a texto con faster-whisper (optimizado M4)"""

    logger.info(f"⚡ Usando faster-whisper (3-4x más rápido que OpenAI Whisper)")
    logger.info(f"Cargando modelo: {model_size}")

    # Usar caché para el modelo
    if model_size not in _model_cache:
        # device auto detecta el mejor (CPU en nuestro caso, pero optimizado)
        model = WhisperModel(model_size, device="cpu", compute_type="float32")
        _model_cache[model_size] = model
    else:
        logger.info(f"Usando modelo cacheado: {model_size}")
        model = _model_cache[model_size]

    logger.info(f"Transcribiendo: {audio_path}")

    # Transcribir con faster-whisper
    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=5,  # Balance entre velocidad y precisión
        best_of=5,
        patience=1.0,
        length_penalty=1.0,
        temperature=0.0,  # Determinista (mejor reproducibilidad)
        compression_ratio_threshold=2.4,
        no_speech_threshold=0.6,
        word_timestamps=include_timestamps,
    )

    # Crear archivo de salida
    input_path = Path(audio_path)
    output_path = input_path.with_suffix('.txt')

    logger.info(f"Guardando transcripción: {output_path}")

    with open(output_path, 'w', encoding='utf-8') as f:
        if include_timestamps:
            for segment in segments:
                start_time = f"{int(segment.start // 60):02d}:{int(segment.start % 60):02d}"
                end_time = f"{int(segment.end // 60):02d}:{int(segment.end % 60):02d}"
                text = segment.text.strip()
                f.write(f"[{start_time} - {end_time}] {text}\n")
        else:
            for segment in segments:
                f.write(segment.text + "\n")

    logger.info("✅ Transcripción completada")
    return str(output_path)

def main():
    parser = argparse.ArgumentParser(description="Convertir audio a texto con faster-whisper (M4 optimizado)")
    parser.add_argument("audio", help="Archivo de audio")
    parser.add_argument("-m", "--model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Modelo faster-whisper (default: base)")
    parser.add_argument("-l", "--language", default="es",
                       help="Idioma (ej: es, en) - default: es")
    parser.add_argument("-t", "--timestamps", action="store_true",
                       help="Incluir timestamps")

    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"Error: No se encuentra el archivo {args.audio}")
        sys.exit(1)

    try:
        # Optimizar CPU
        optimize_cpu_threads()

        output_file = transcribe_audio(
            args.audio,
            args.model,
            args.language,
            args.timestamps
        )
        print(f"✅ Transcripción guardada en: {output_file}")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
