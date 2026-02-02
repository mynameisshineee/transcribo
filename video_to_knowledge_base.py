#!/usr/bin/env python3
"""
Video to Knowledge Base Converter
==================================
Convierte videos a documentos Markdown LLM-friendly con:
- Transcripción completa con timestamps
- Frames extraídos en momentos clave (cambios de escena, palabras clave)
- Imágenes embebidas en base64
- Metadata estructurada
- Formato optimizado para ingestión por LLMs

Optimizado para MacBook Pro M4 con MPS acceleration
"""

import argparse
import base64
import cv2
import io
import logging
import os
import re
import sys
import whisper
import torch
from datetime import datetime, timedelta
from pathlib import Path
from PIL import Image
from skimage.metrics import structural_similarity as ssim
import numpy as np

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Cache global para modelos Whisper
_model_cache = {}

def get_device():
    """Detecta el mejor dispositivo disponible (MPS > CUDA > CPU)"""
    if torch.backends.mps.is_available():
        logging.info("🚀 Usando MPS (Metal Performance Shaders) en M4")
        return "mps"
    elif torch.cuda.is_available():
        logging.info("🚀 Usando CUDA (GPU NVIDIA)")
        return "cuda"
    else:
        logging.info("🚀 Usando CPU optimizado para M4 Pro (48GB RAM)")
        logging.info("💡 CPU en M4 Pro es muy rápido con modelos grandes")
        return "cpu"

def load_whisper_model(model_size="base", device=None):
    """Carga modelo Whisper con cache global"""
    if device is None:
        device = get_device()

    cache_key = f"{model_size}_{device}"

    if cache_key in _model_cache:
        logging.info(f"♻️  Reutilizando modelo Whisper desde cache: {model_size} en {device}")
        return _model_cache[cache_key], device

    logging.info(f"Cargando modelo Whisper: {model_size} en {device}")
    model = whisper.load_model(model_size, device=device)
    _model_cache[cache_key] = model

    return model, device

def transcribe_video(video_path, model_size="base", language="es", device=None):
    """Transcribe video completo con timestamps detallados"""
    model, device = load_whisper_model(model_size, device)

    logging.info(f"Transcribiendo: {video_path}")

    # Configuración optimizada para MPS
    # NOTA: word_timestamps causa problemas con MPS (float64), así que lo deshabilitamos
    options = {
        'language': language,
        'task': 'transcribe',
        'fp16': device == "mps",  # fp16 solo en MPS
        'verbose': False,
        'word_timestamps': False  # Deshabilitado para compatibilidad con MPS
    }

    result = model.transcribe(str(video_path), **options)

    return result

def extract_frames_on_scene_change(video_path, threshold=0.3, min_interval=2.0):
    """
    Extrae frames cuando hay cambios significativos de escena

    Args:
        video_path: Ruta al video
        threshold: Umbral de diferencia para considerar cambio de escena (0-1)
        min_interval: Intervalo mínimo en segundos entre frames

    Returns:
        Lista de tuplas (timestamp, frame_array)
    """
    logging.info(f"Analizando cambios de escena en: {video_path}")

    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    frames_extracted = []
    prev_frame_gray = None
    last_extracted_time = -min_interval  # Para forzar primera extracción
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_count / fps

        # Convertir a escala de grises para comparación
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Reducir resolución para comparación más rápida
        gray_small = cv2.resize(gray, (320, 180))

        if prev_frame_gray is not None:
            # Calcular similitud estructural
            similarity = ssim(prev_frame_gray, gray_small)
            difference = 1 - similarity

            # Si hay cambio significativo y ha pasado el intervalo mínimo
            if difference > threshold and (current_time - last_extracted_time) >= min_interval:
                # Redimensionar frame para el documento (más pequeño)
                frame_resized = cv2.resize(frame, (854, 480))  # 480p
                frames_extracted.append((current_time, frame_resized))
                last_extracted_time = current_time
                logging.info(f"  Frame extraído en {format_timestamp(current_time)} (diferencia: {difference:.2f})")

        prev_frame_gray = gray_small
        frame_count += 1

        # Progreso cada 10%
        if frame_count % (total_frames // 10) == 0:
            progress = (frame_count / total_frames) * 100
            logging.info(f"  Progreso: {progress:.0f}%")

    cap.release()

    # Siempre extraer primer y último frame si no están ya
    cap = cv2.VideoCapture(str(video_path))

    # Primer frame
    if not frames_extracted or frames_extracted[0][0] > 1.0:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret, frame = cap.read()
        if ret:
            frame_resized = cv2.resize(frame, (854, 480))
            frames_extracted.insert(0, (0.0, frame_resized))

    # Último frame
    duration = total_frames / fps
    if not frames_extracted or (duration - frames_extracted[-1][0]) > min_interval:
        cap.set(cv2.CAP_PROP_POS_FRAMES, total_frames - 1)
        ret, frame = cap.read()
        if ret:
            frame_resized = cv2.resize(frame, (854, 480))
            frames_extracted.append((duration, frame_resized))

    cap.release()

    logging.info(f"✅ Extraídos {len(frames_extracted)} frames clave")
    return frames_extracted

def extract_frames_on_keywords(video_path, transcription, keywords=None):
    """
    Extrae frames adicionales cuando se detectan palabras clave en la transcripción

    Args:
        video_path: Ruta al video
        transcription: Resultado de Whisper con word_timestamps
        keywords: Lista de palabras clave (None = usar defaults)

    Returns:
        Lista de tuplas (timestamp, frame_array, keyword)
    """
    if keywords is None:
        keywords = [
            # Indicadores visuales
            r'\b(mira|miren|vean|ves|observa|fíjate|aquí|acá)\b',
            r'\b(código|diagrama|gráfico|pantalla|ejemplo|demo)\b',
            r'\b(importante|clave|esencial|crucial)\b',
            # Términos técnicos
            r'\b(función|clase|método|variable|API|endpoint)\b',
            r'\b(error|bug|problema|solución|fix)\b',
            # Transiciones
            r'\b(ahora|siguiente|paso|primero|segundo|finalmente)\b',
        ]

    logging.info("Buscando palabras clave en transcripción...")

    keyword_frames = []
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Procesar segmentos
    for segment in transcription.get('segments', []):
        text = segment['text'].lower()
        start_time = segment['start']

        # Buscar keywords
        for pattern in keywords:
            if re.search(pattern, text, re.IGNORECASE):
                # Extraer frame en ese momento
                cap.set(cv2.CAP_PROP_POS_MSEC, start_time * 1000)
                ret, frame = cap.read()
                if ret:
                    frame_resized = cv2.resize(frame, (854, 480))
                    matched = re.search(pattern, text, re.IGNORECASE)
                    keyword_frames.append((start_time, frame_resized, matched.group()))
                    logging.info(f"  Keyword '{matched.group()}' encontrado en {format_timestamp(start_time)}")
                break  # Solo un keyword por segmento

    cap.release()

    logging.info(f"✅ Extraídos {len(keyword_frames)} frames por keywords")
    return keyword_frames

def frame_to_base64(frame):
    """Convierte frame de OpenCV a base64 string"""
    # Convertir BGR (OpenCV) a RGB (PIL)
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(frame_rgb)

    # Comprimir como JPEG para reducir tamaño
    buffer = io.BytesIO()
    pil_image.save(buffer, format='JPEG', quality=85, optimize=True)

    # Convertir a base64
    img_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f"data:image/jpeg;base64,{img_str}"

def format_timestamp(seconds):
    """Formatea segundos a MM:SS o HH:MM:SS"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def generate_knowledge_base_markdown(
    video_path,
    transcription,
    scene_frames,
    keyword_frames,
    output_path,
    model_size="base"
):
    """Genera documento Markdown LLM-friendly con todo integrado"""

    video_name = Path(video_path).stem
    duration = transcription.get('segments', [{}])[-1].get('end', 0)

    # Combinar y ordenar todos los frames
    all_frames = []

    # Scene frames
    for timestamp, frame in scene_frames:
        all_frames.append({
            'timestamp': timestamp,
            'frame': frame,
            'type': 'scene_change',
            'description': 'Cambio de escena detectado'
        })

    # Keyword frames
    for timestamp, frame, keyword in keyword_frames:
        all_frames.append({
            'timestamp': timestamp,
            'frame': frame,
            'type': 'keyword',
            'description': f'Palabra clave: "{keyword}"'
        })

    # Ordenar por timestamp
    all_frames.sort(key=lambda x: x['timestamp'])

    # Eliminar duplicados cercanos (< 1 segundo de diferencia)
    filtered_frames = []
    for frame_data in all_frames:
        if not filtered_frames or (frame_data['timestamp'] - filtered_frames[-1]['timestamp']) > 1.0:
            filtered_frames.append(frame_data)

    logging.info(f"Generando documento Markdown: {output_path}")
    logging.info(f"Total frames a incluir: {len(filtered_frames)}")

    # Generar contenido
    md_content = []

    # Frontmatter YAML
    md_content.append("---")
    md_content.append(f"title: \"{video_name}\"")
    md_content.append(f"duration: \"{format_timestamp(duration)}\"")
    md_content.append(f"transcription_date: \"{datetime.now().strftime('%Y-%m-%d')}\"")
    md_content.append(f"whisper_model: \"{model_size}\"")
    md_content.append(f"frames_extracted: {len(filtered_frames)}")
    md_content.append(f"source_video: \"{Path(video_path).name}\"")
    md_content.append("---")
    md_content.append("")

    # Título principal
    md_content.append(f"# {video_name}")
    md_content.append("")

    # Metadata
    md_content.append("## 📊 Metadata")
    md_content.append("")
    md_content.append(f"- **Duración**: {format_timestamp(duration)}")
    md_content.append(f"- **Frames capturados**: {len(filtered_frames)}")
    md_content.append(f"- **Modelo Whisper**: {model_size}")
    md_content.append(f"- **Fecha de transcripción**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    md_content.append("")

    # Resumen ejecutivo (primeros 3 segmentos)
    md_content.append("## 📝 Resumen Ejecutivo")
    md_content.append("")
    segments = transcription.get('segments', [])
    if segments:
        summary_segments = segments[:min(3, len(segments))]
        for seg in summary_segments:
            md_content.append(f"- {seg['text'].strip()}")
    md_content.append("")

    # Índice con timestamps
    md_content.append("## 📑 Índice")
    md_content.append("")
    for i, seg in enumerate(segments[:20]):  # Primeros 20 para no saturar
        ts = format_timestamp(seg['start'])
        anchor = f"ts{int(seg['start'])}"
        preview = seg['text'].strip()[:60]
        if len(seg['text'].strip()) > 60:
            preview += "..."
        md_content.append(f"- [{ts}](#{anchor}) - {preview}")
    md_content.append("")

    # Contenido principal: transcripción con frames
    md_content.append("---")
    md_content.append("")
    md_content.append("## 🎬 Transcripción Completa con Frames")
    md_content.append("")

    frame_index = 0

    for seg_idx, segment in enumerate(segments):
        start_time = segment['start']
        end_time = segment['end']
        text = segment['text'].strip()

        # Anchor para el índice
        anchor = f"ts{int(start_time)}"

        # Timestamp como encabezado
        md_content.append(f"### [{format_timestamp(start_time)} - {format_timestamp(end_time)}] {{#{anchor}}}")
        md_content.append("")

        # Insertar frames que caen en este segmento
        while frame_index < len(filtered_frames) and filtered_frames[frame_index]['timestamp'] <= end_time:
            frame_data = filtered_frames[frame_index]

            # Solo insertar si está cerca del inicio del segmento (±2 segundos)
            if abs(frame_data['timestamp'] - start_time) <= 2.0:
                img_base64 = frame_to_base64(frame_data['frame'])
                md_content.append(f"![Frame en {format_timestamp(frame_data['timestamp'])}]({img_base64})")
                md_content.append("")
                md_content.append(f"*🖼️ {frame_data['description']} - Timestamp: {format_timestamp(frame_data['timestamp'])}*")
                md_content.append("")

            frame_index += 1

        # Texto de la transcripción
        md_content.append(text)
        md_content.append("")

    # Frames finales que no se insertaron
    while frame_index < len(filtered_frames):
        frame_data = filtered_frames[frame_index]
        md_content.append(f"### [{format_timestamp(frame_data['timestamp'])}]")
        md_content.append("")
        img_base64 = frame_to_base64(frame_data['frame'])
        md_content.append(f"![Frame en {format_timestamp(frame_data['timestamp'])}]({img_base64})")
        md_content.append("")
        md_content.append(f"*🖼️ {frame_data['description']}*")
        md_content.append("")
        frame_index += 1

    # Footer
    md_content.append("---")
    md_content.append("")
    md_content.append("## 🤖 Información del Documento")
    md_content.append("")
    md_content.append("Este documento fue generado automáticamente usando:")
    md_content.append("- **OpenAI Whisper** para transcripción")
    md_content.append("- **OpenCV** para extracción de frames")
    md_content.append("- **scikit-image** para detección de cambios de escena")
    md_content.append("- **Optimizado para M4 Pro** con MPS acceleration")
    md_content.append("")
    md_content.append("Formato optimizado para ingestión por LLMs y agentes de IA.")
    md_content.append("")

    # Escribir archivo
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(md_content))

    # Calcular tamaño del archivo
    file_size = os.path.getsize(output_path) / (1024 * 1024)  # MB
    logging.info(f"✅ Documento generado: {output_path}")
    logging.info(f"📦 Tamaño del archivo: {file_size:.2f} MB")

def main():
    parser = argparse.ArgumentParser(
        description='Convierte video a Knowledge Base Markdown LLM-friendly',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python3 video_to_knowledge_base.py "video.mp4"
  python3 video_to_knowledge_base.py "video.mp4" -m small -l en
  python3 video_to_knowledge_base.py "video.mp4" --threshold 0.4 --min-interval 3
        """
    )

    parser.add_argument('video_path', help='Ruta al archivo de video')
    parser.add_argument('-m', '--model', default='base',
                       choices=['tiny', 'base', 'small', 'medium', 'large'],
                       help='Modelo Whisper (default: base)')
    parser.add_argument('-l', '--language', default='es',
                       help='Idioma del audio (default: es)')
    parser.add_argument('-o', '--output', help='Ruta del archivo Markdown de salida')
    parser.add_argument('-d', '--device', choices=['mps', 'cuda', 'cpu'],
                       help='Forzar dispositivo específico')
    parser.add_argument('--threshold', type=float, default=0.3,
                       help='Umbral para detección de cambio de escena (0-1, default: 0.3)')
    parser.add_argument('--min-interval', type=float, default=2.0,
                       help='Intervalo mínimo en segundos entre frames (default: 2.0)')

    args = parser.parse_args()

    # Validar archivo de entrada
    video_path = Path(args.video_path)
    if not video_path.exists():
        logging.error(f"❌ Error: Archivo no encontrado: {video_path}")
        sys.exit(1)

    # Determinar ruta de salida
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = video_path.with_suffix('.knowledge.md')

    logging.info("=" * 70)
    logging.info("🎥 VIDEO TO KNOWLEDGE BASE CONVERTER")
    logging.info("=" * 70)
    logging.info(f"📹 Video: {video_path.name}")
    logging.info(f"📄 Output: {output_path.name}")
    logging.info(f"🤖 Modelo: {args.model}")
    logging.info(f"🌍 Idioma: {args.language}")
    logging.info("=" * 70)

    # 1. Transcribir audio
    logging.info("\n🎙️  PASO 1: Transcribiendo audio...")
    transcription = transcribe_video(
        video_path,
        model_size=args.model,
        language=args.language,
        device=args.device
    )

    # 2. Extraer frames en cambios de escena
    logging.info("\n🎬 PASO 2: Detectando cambios de escena...")
    scene_frames = extract_frames_on_scene_change(
        video_path,
        threshold=args.threshold,
        min_interval=args.min_interval
    )

    # 3. Extraer frames en keywords
    logging.info("\n🔍 PASO 3: Buscando palabras clave...")
    keyword_frames = extract_frames_on_keywords(video_path, transcription)

    # 4. Generar documento Markdown
    logging.info("\n📝 PASO 4: Generando Knowledge Base Markdown...")
    generate_knowledge_base_markdown(
        video_path,
        transcription,
        scene_frames,
        keyword_frames,
        output_path,
        model_size=args.model
    )

    logging.info("\n" + "=" * 70)
    logging.info("✅ PROCESO COMPLETADO")
    logging.info("=" * 70)
    logging.info(f"📄 Documento generado: {output_path}")
    logging.info(f"🎯 Listo para usar con LLMs y agentes de IA")
    logging.info("=" * 70)

if __name__ == "__main__":
    main()
