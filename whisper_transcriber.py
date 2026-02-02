#!/usr/bin/env python3
"""
Script optimizado para transcribir audio usando Whisper
"""

import os
import sys
import argparse
import ssl
import urllib.request
from pathlib import Path

# Solucionar problema de SSL
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import whisper
except ImportError:
    print("❌ Error: Whisper no está instalado")
    print("Ejecuta: pip install openai-whisper")
    sys.exit(1)

def transcribe_file(audio_path, model_name="base", language="Spanish"):
    """Transcribir archivo de audio"""

    print(f"🔄 Cargando modelo: {model_name}")
    try:
        model = whisper.load_model(model_name)
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        return None

    print(f"🎵 Transcribiendo: {Path(audio_path).name}")

    try:
        result = model.transcribe(
            audio_path,
            language=language.lower() if language != "Spanish" else "es",
            fp16=False  # Para compatibilidad con M4
        )

        # Crear archivo de salida
        input_path = Path(audio_path)
        output_path = input_path.with_suffix('.txt')

        print(f"💾 Guardando transcripción en: {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcripción de: {input_path.name}\n")
            f.write("=" * 50 + "\n\n")
            f.write(result['text'].strip())

        print(f"✅ ¡Transcripción completada!")
        print(f"📄 Archivo guardado: {output_path}")

        return str(output_path)

    except Exception as e:
        print(f"❌ Error en transcripción: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Transcribir audio con Whisper")
    parser.add_argument("audio", help="Archivo de audio")
    parser.add_argument("-m", "--model", default="base",
                       choices=["tiny", "base", "small", "medium", "large"],
                       help="Modelo (default: base)")
    parser.add_argument("-l", "--language", default="Spanish",
                       help="Idioma (default: Spanish)")

    args = parser.parse_args()

    if not os.path.exists(args.audio):
        print(f"❌ Error: Archivo no encontrado: {args.audio}")
        sys.exit(1)

    result = transcribe_file(args.audio, args.model, args.language)

    if result:
        print(f"\n🎉 ¡Proceso completado exitosamente!")
    else:
        print(f"\n❌ Proceso falló")
        sys.exit(1)

if __name__ == "__main__":
    main()