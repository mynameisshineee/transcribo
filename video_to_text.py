#!/usr/bin/env python3
"""
Script robusto para convertir video a texto usando Whisper de OpenAI
Autor: Claude AI
"""

import os
import sys
import argparse
import tempfile
import logging
from pathlib import Path
from typing import Optional, Tuple

try:
    import whisper
    import moviepy.editor as mp
    from pydub import AudioSegment
except ImportError as e:
    print(f"Error: Falta instalar dependencias. Ejecuta: pip install -r requirements.txt")
    print(f"Error específico: {e}")
    sys.exit(1)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VideoToTextConverter:
    """Clase para convertir video a texto usando Whisper"""

    def __init__(self, model_size: str = "base"):
        """
        Inicializar el convertidor

        Args:
            model_size: Tamaño del modelo Whisper (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self.supported_video_formats = ['.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.m4v']
        self.supported_audio_formats = ['.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac']

    def load_model(self) -> None:
        """Cargar el modelo de Whisper"""
        try:
            logger.info(f"Cargando modelo Whisper: {self.model_size}")
            self.model = whisper.load_model(self.model_size)
            logger.info("Modelo cargado exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar el modelo: {e}")
            raise

    def extract_audio_from_video(self, video_path: str, output_dir: str) -> str:
        """
        Extraer audio de un archivo de video

        Args:
            video_path: Ruta del archivo de video
            output_dir: Directorio para guardar el audio extraído

        Returns:
            Ruta del archivo de audio extraído
        """
        try:
            logger.info(f"Extrayendo audio de: {video_path}")

            # Crear nombre del archivo de audio temporal
            video_name = Path(video_path).stem
            audio_path = os.path.join(output_dir, f"{video_name}_audio.wav")

            # Extraer audio usando moviepy
            with mp.VideoFileClip(video_path) as video:
                audio = video.audio
                if audio is None:
                    raise ValueError("El video no contiene pista de audio")
                audio.write_audiofile(audio_path, verbose=False, logger=None)

            logger.info(f"Audio extraído: {audio_path}")
            return audio_path

        except Exception as e:
            logger.error(f"Error al extraer audio: {e}")
            raise

    def convert_audio_format(self, audio_path: str, target_format: str = "wav") -> str:
        """
        Convertir formato de audio si es necesario

        Args:
            audio_path: Ruta del archivo de audio
            target_format: Formato objetivo (wav por defecto)

        Returns:
            Ruta del archivo convertido
        """
        try:
            file_ext = Path(audio_path).suffix.lower()

            if file_ext == f".{target_format}":
                return audio_path

            logger.info(f"Convirtiendo audio a formato {target_format}")

            # Cargar y convertir audio
            audio = AudioSegment.from_file(audio_path)

            # Crear nuevo nombre de archivo
            output_path = str(Path(audio_path).with_suffix(f".{target_format}"))

            # Exportar en nuevo formato
            audio.export(output_path, format=target_format)

            logger.info(f"Audio convertido: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error al convertir audio: {e}")
            raise

    def transcribe_audio(self, audio_path: str, language: Optional[str] = None) -> dict:
        """
        Transcribir audio a texto usando Whisper

        Args:
            audio_path: Ruta del archivo de audio
            language: Idioma del audio (opcional, Whisper lo detecta automáticamente)

        Returns:
            Diccionario con el resultado de la transcripción
        """
        try:
            if self.model is None:
                self.load_model()

            logger.info(f"Transcribiendo audio: {audio_path}")

            # Configurar opciones de transcripción
            options = {}
            if language:
                options['language'] = language

            # Realizar transcripción
            result = self.model.transcribe(audio_path, **options)

            logger.info("Transcripción completada")
            return result

        except Exception as e:
            logger.error(f"Error en la transcripción: {e}")
            raise

    def save_transcript(self, result: dict, output_path: str, include_timestamps: bool = False) -> None:
        """
        Guardar la transcripción en un archivo

        Args:
            result: Resultado de la transcripción de Whisper
            output_path: Ruta donde guardar el archivo
            include_timestamps: Si incluir marcas de tiempo
        """
        try:
            logger.info(f"Guardando transcripción: {output_path}")

            with open(output_path, 'w', encoding='utf-8') as f:
                if include_timestamps:
                    # Guardar con timestamps por segmento
                    for segment in result['segments']:
                        start_time = self.format_timestamp(segment['start'])
                        end_time = self.format_timestamp(segment['end'])
                        text = segment['text'].strip()
                        f.write(f"[{start_time} - {end_time}] {text}\n")
                else:
                    # Guardar solo el texto completo
                    f.write(result['text'].strip())

            logger.info("Transcripción guardada exitosamente")

        except Exception as e:
            logger.error(f"Error al guardar transcripción: {e}")
            raise

    def format_timestamp(self, seconds: float) -> str:
        """
        Formatear timestamp en formato HH:MM:SS

        Args:
            seconds: Tiempo en segundos

        Returns:
            Timestamp formateado
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def validate_input_file(self, file_path: str) -> Tuple[bool, str]:
        """
        Validar si el archivo de entrada es compatible

        Args:
            file_path: Ruta del archivo

        Returns:
            Tupla (es_válido, tipo_archivo)
        """
        if not os.path.exists(file_path):
            return False, "El archivo no existe"

        file_ext = Path(file_path).suffix.lower()

        if file_ext in self.supported_video_formats:
            return True, "video"
        elif file_ext in self.supported_audio_formats:
            return True, "audio"
        else:
            return False, f"Formato no soportado: {file_ext}"

    def process_file(self, input_path: str, output_path: str, language: Optional[str] = None,
                    include_timestamps: bool = False, keep_audio: bool = False) -> None:
        """
        Procesar un archivo de video o audio y convertirlo a texto

        Args:
            input_path: Ruta del archivo de entrada
            output_path: Ruta del archivo de salida
            language: Idioma del contenido (opcional)
            include_timestamps: Si incluir marcas de tiempo
            keep_audio: Si mantener el archivo de audio extraído
        """
        # Validar archivo de entrada
        is_valid, file_type = self.validate_input_file(input_path)
        if not is_valid:
            raise ValueError(f"Archivo no válido: {file_type}")

        # Crear directorio temporal
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = input_path

            # Si es video, extraer audio
            if file_type == "video":
                audio_path = self.extract_audio_from_video(input_path, temp_dir)

            # Convertir formato de audio si es necesario
            audio_path = self.convert_audio_format(audio_path)

            # Transcribir audio
            result = self.transcribe_audio(audio_path, language)

            # Guardar transcripción
            self.save_transcript(result, output_path, include_timestamps)

            # Mover archivo de audio si se debe mantener
            if keep_audio and file_type == "video":
                final_audio_path = str(Path(output_path).with_suffix('.wav'))
                os.rename(audio_path, final_audio_path)
                logger.info(f"Audio guardado en: {final_audio_path}")

def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(
        description="Convertir video/audio a texto usando Whisper de OpenAI"
    )

    parser.add_argument(
        "input",
        help="Archivo de video o audio de entrada"
    )

    parser.add_argument(
        "-o", "--output",
        help="Archivo de texto de salida (por defecto: mismo nombre con extensión .txt)"
    )

    parser.add_argument(
        "-m", "--model",
        choices=["tiny", "base", "small", "medium", "large"],
        default="base",
        help="Tamaño del modelo Whisper (por defecto: base)"
    )

    parser.add_argument(
        "-l", "--language",
        help="Idioma del contenido (ej: es, en, fr). Si no se especifica, se detecta automáticamente"
    )

    parser.add_argument(
        "-t", "--timestamps",
        action="store_true",
        help="Incluir marcas de tiempo en la transcripción"
    )

    parser.add_argument(
        "-k", "--keep-audio",
        action="store_true",
        help="Mantener el archivo de audio extraído (solo para videos)"
    )

    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Mostrar información detallada"
    )

    args = parser.parse_args()

    # Configurar nivel de logging
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Determinar archivo de salida
    if args.output:
        output_path = args.output
    else:
        input_path = Path(args.input)
        output_path = str(input_path.with_suffix('.txt'))

    try:
        # Crear convertidor
        converter = VideoToTextConverter(model_size=args.model)

        # Procesar archivo
        converter.process_file(
            input_path=args.input,
            output_path=output_path,
            language=args.language,
            include_timestamps=args.timestamps,
            keep_audio=args.keep_audio
        )

        print(f"✅ Transcripción completada: {output_path}")

    except Exception as e:
        logger.error(f"Error durante el procesamiento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()