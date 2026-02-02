#!/usr/bin/env python3
import os
import sys
import glob
import whisper
from pathlib import Path

def process_video(video_path, model):
    """Procesa un video y genera su transcripción"""
    print(f"\n{'='*60}")
    print(f"Procesando: {os.path.basename(video_path)}")
    print(f"{'='*60}")

    output_path = video_path.rsplit('.', 1)[0] + '_transcripcion.txt'

    if os.path.exists(output_path):
        print(f"✓ Ya existe transcripción: {os.path.basename(output_path)}")
        return

    try:
        print("Transcribiendo audio...")
        result = model.transcribe(video_path, language='es', task='transcribe')

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"Transcripción de: {os.path.basename(video_path)}\n")
            f.write("="*60 + "\n\n")
            f.write(result["text"])

            if result.get("segments"):
                f.write("\n\n" + "="*60)
                f.write("\nTranscripción con marcas de tiempo:\n")
                f.write("="*60 + "\n\n")
                for segment in result["segments"]:
                    start = segment["start"]
                    end = segment["end"]
                    text = segment["text"]
                    f.write(f"[{start:.2f}s - {end:.2f}s] {text}\n")

        print(f"✓ Transcripción guardada: {os.path.basename(output_path)}")

    except Exception as e:
        print(f"✗ Error procesando {os.path.basename(video_path)}: {str(e)}")

def main():
    target_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    print(f"Usage: python3 process_all_videos.py [directory]")
    print(f"Using: {target_dir}")

    print(f"Carpeta objetivo: {target_dir}")
    print("Cargando modelo Whisper (base)...")
    model = whisper.load_model("base")

    video_extensions = ['*.mkv', '*.mp4', '*.avi', '*.mov', '*.wmv', '*.flv', '*.webm']
    audio_extensions = ['*.mp3', '*.wav', '*.m4a', '*.flac', '*.aac', '*.ogg', '*.wma']

    all_media_files = []

    for ext in video_extensions + audio_extensions:
        pattern = os.path.join(target_dir, ext)
        all_media_files.extend(glob.glob(pattern))

    if not all_media_files:
        print("No se encontraron archivos de video o audio en la carpeta.")
        return

    print(f"\nEncontrados {len(all_media_files)} archivos multimedia:")
    for f in all_media_files:
        print(f"  - {os.path.basename(f)}")

    for media_file in all_media_files:
        process_video(media_file, model)

    print(f"\n{'='*60}")
    print("¡Proceso completado!")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()