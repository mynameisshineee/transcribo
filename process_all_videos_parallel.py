#!/usr/bin/env python3
"""
Transcribo - Batch transcription processor.
Processes all video/audio files in a directory.
Auto-detects GPU: MPS (Apple Silicon), CUDA (NVIDIA), or CPU.
"""

import os
import sys
import glob
import logging
import torch
import multiprocessing as mp
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import lru_cache
import time

try:
    import whisper
except ImportError as e:
    print(f"Error: Whisper no está instalado. Ejecuta: pip install openai-whisper")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(processName)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcriptor de Whisper optimizado para M4"""

    def __init__(self, model_size="large", language="es"):
        self.model_size = model_size
        self.language = language
        self.device = self._get_device()
        self.model = None

    def _get_device(self):
        """Detectar dispositivo óptimo - M4 Pro a máxima potencia"""
        if torch.backends.mps.is_available():
            logger.info("🚀 Usando MPS (Metal Performance Shaders) - M4 Pro a tope!")
            return "mps"
        elif torch.cuda.is_available():
            logger.info("✨ Usando CUDA GPU")
            return "cuda"
        else:
            logger.info("⚠️  Usando CPU (MPS no disponible)")
            return "cpu"

    def load_model(self):
        """Cargar modelo Whisper una sola vez"""
        if self.model is None:
            logger.info(f"Cargando modelo {self.model_size} en {self.device}")
            self.model = whisper.load_model(self.model_size, device=self.device)
        return self.model

    def transcribe_file(self, file_path):
        """Transcribir un archivo individual"""
        try:
            output_path = str(Path(file_path).with_stem(Path(file_path).stem + "_transcripcion"))
            output_path = output_path.rsplit(".", 1)[0] + ".txt"

            if os.path.exists(output_path):
                logger.info(f"✓ Ya existe: {Path(file_path).name}")
                return {"status": "skipped", "file": file_path, "output": output_path}

            logger.info(f"📝 Transcribiendo: {Path(file_path).name}")

            model = self.load_model()

            options = {
                'language': self.language,
                'fp16': self.device == "mps",  # fp16 en MPS para mejor rendimiento
                'verbose': False,
            }

            result = model.transcribe(file_path, **options)

            # Guardar transcripción
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"Transcripción de: {Path(file_path).name}\n")
                f.write("=" * 60 + "\n\n")
                f.write(result["text"])

                if result.get("segments"):
                    f.write("\n\n" + "=" * 60)
                    f.write("\nTranscripción con timestamps:\n")
                    f.write("=" * 60 + "\n\n")
                    for segment in result["segments"]:
                        start = segment["start"]
                        end = segment["end"]
                        text = segment["text"]
                        f.write(f"[{start:.2f}s - {end:.2f}s] {text}\n")

            logger.info(f"✓ Completado: {Path(file_path).name}")
            return {"status": "success", "file": file_path, "output": output_path}

        except Exception as e:
            logger.error(f"✗ Error en {Path(file_path).name}: {str(e)}")
            return {"status": "error", "file": file_path, "error": str(e)}


def process_batch_sequential(target_dir, model_size="base", language="es"):
    """Procesamiento secuencial (mejor para un archivo a la vez)"""
    logger.info(f"Procesando carpeta: {target_dir}")

    transcriber = WhisperTranscriber(model_size, language)

    video_extensions = ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm']
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.aac', '*.ogg', '*.wma']

    all_media_files = []
    for ext in video_extensions + audio_extensions:
        pattern = os.path.join(target_dir, ext)
        all_media_files.extend(glob.glob(pattern))

    if not all_media_files:
        logger.warning("No se encontraron archivos multimedia")
        return

    logger.info(f"\n🎬 Encontrados {len(all_media_files)} archivos")
    logger.info("=" * 60)

    results = []
    for idx, media_file in enumerate(all_media_files, 1):
        logger.info(f"\n[{idx}/{len(all_media_files)}]")
        result = transcriber.transcribe_file(media_file)
        results.append(result)

    # Resumen
    logger.info("\n" + "=" * 60)
    logger.info("📊 RESUMEN")
    logger.info("=" * 60)

    success = sum(1 for r in results if r["status"] == "success")
    skipped = sum(1 for r in results if r["status"] == "skipped")
    errors = sum(1 for r in results if r["status"] == "error")

    logger.info(f"✓ Completados: {success}")
    logger.info(f"⊘ Saltados: {skipped}")
    logger.info(f"✗ Errores: {errors}")
    logger.info("=" * 60)


def main():
    # Configuración
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    model_size = "base"
    language = "es"

    # Validar directorio
    if not os.path.isdir(target_dir):
        print(f"Error: No existe la carpeta {target_dir}")
        sys.exit(1)

    logger.info("🚀 Iniciando transcripción en paralelo para M4")
    logger.info(f"Carpeta: {target_dir}")
    logger.info(f"Modelo: {model_size}")
    logger.info(f"Idioma: {language}")

    start_time = time.time()

    try:
        # Usar procesamiento secuencial (recomendado para M4 con 48GB)
        process_batch_sequential(target_dir, model_size, language)

    except Exception as e:
        logger.error(f"Error fatal: {e}")
        sys.exit(1)

    elapsed = time.time() - start_time
    logger.info(f"\n⏱️  Tiempo total: {elapsed:.1f}s ({elapsed/60:.1f}min)")


if __name__ == "__main__":
    # Configurar multiprocessing para M4
    mp.set_start_method('fork', force=True)
    main()
