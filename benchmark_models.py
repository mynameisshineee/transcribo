#!/usr/bin/env python3
"""
Benchmark de modelos Whisper en M4 Pro
Prueba: SMALL + MPS, MEDIUM + MPS, LARGE + CPU
"""

import os
import sys
import time
import json
import torch
import ssl
from pathlib import Path
from datetime import datetime

# Fix SSL
ssl._create_default_https_context = ssl._create_unverified_context

try:
    import whisper
except ImportError:
    print("Error: Instala openai-whisper")
    sys.exit(1)

# Configuración de benchmark
# Pass video paths as command line arguments, e.g.:
#   python3 benchmark_models.py video1.mp4 video2.mp4
VIDEOS = sys.argv[1:] if len(sys.argv) > 1 else []
if not VIDEOS:
    print("Usage: python3 benchmark_models.py <video1.mp4> [video2.mp4 ...]")
    sys.exit(1)

CONFIGS = [
    {"model": "base", "device": "mps", "name": "BASE + MPS (rápido)"},
    {"model": "small", "device": "cpu", "name": "SMALL + CPU"},
    {"model": "medium", "device": "mps", "name": "MEDIUM + MPS (balance)"},
    {"model": "large", "device": "cpu", "name": "LARGE + CPU (preciso)"},
]

results = []

print("=" * 70)
print("🚀 BENCHMARK WHISPER EN M4 PRO 48GB")
print("=" * 70)
print(f"Videos a procesar: {len(VIDEOS)}")
print(f"Configuraciones: {len(CONFIGS)}")
print(f"Total de pruebas: {len(VIDEOS) * len(CONFIGS)}")
print("=" * 70)
print()

for config in CONFIGS:
    model_name = config["model"]
    device = config["device"]
    config_name = config["name"]

    print(f"\n{'='*70}")
    print(f"📊 Probando: {config_name}")
    print(f"{'='*70}")

    # Cargar modelo una sola vez
    print(f"⏳ Cargando modelo {model_name} en {device}...")
    load_start = time.time()

    try:
        model = whisper.load_model(model_name, device=device)
        load_time = time.time() - load_start
        print(f"✅ Modelo cargado en {load_time:.2f}s")
    except Exception as e:
        print(f"❌ Error cargando modelo: {e}")
        continue

    # Procesar cada video
    for video_path in VIDEOS:
        video_name = Path(video_path).stem
        print(f"\n  🎬 Procesando: {video_name[:50]}...")

        try:
            # Transcribir
            start_time = time.time()
            result = model.transcribe(
                video_path,
                language="en",
                fp16=(device == "mps"),
                verbose=False
            )
            transcribe_time = time.time() - start_time

            # Guardar transcripción
            output_path = f"benchmark_{model_name}_{device}_{Path(video_path).stem}.txt"
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result['text'].strip())

            # Estadísticas
            text_length = len(result['text'])
            words_count = len(result['text'].split())

            print(f"  ✅ Completado en {transcribe_time:.2f}s")
            print(f"     - Palabras: {words_count}")
            print(f"     - Caracteres: {text_length}")

            # Guardar resultado
            results.append({
                "config": config_name,
                "model": model_name,
                "device": device,
                "video": video_name,
                "load_time": load_time,
                "transcribe_time": transcribe_time,
                "words": words_count,
                "chars": text_length,
                "output": output_path,
                "success": True
            })

        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append({
                "config": config_name,
                "model": model_name,
                "device": device,
                "video": video_name,
                "error": str(e),
                "success": False
            })

    # Liberar memoria
    del model
    if device == "mps":
        torch.mps.empty_cache()

# Guardar resultados
print(f"\n{'='*70}")
print("💾 GUARDANDO RESULTADOS")
print(f"{'='*70}")

results_file = f"benchmark_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
with open(results_file, 'w', encoding='utf-8') as f:
    json.dump(results, f, indent=2)

print(f"✅ Resultados guardados en: {results_file}")

# Mostrar resumen
print(f"\n{'='*70}")
print("📊 RESUMEN DE RESULTADOS")
print(f"{'='*70}\n")

successful = [r for r in results if r.get('success')]
failed = [r for r in results if not r.get('success')]

print(f"✅ Exitosos: {len(successful)}/{len(results)}")
print(f"❌ Fallidos: {len(failed)}/{len(results)}\n")

if successful:
    print("TIEMPOS DE TRANSCRIPCIÓN (por ~10 min de video):\n")
    for config in CONFIGS:
        config_results = [r for r in successful if r['config'] == config['name']]
        if config_results:
            avg_time = sum(r['transcribe_time'] for r in config_results) / len(config_results)
            print(f"  {config['name']:20} : {avg_time:6.2f}s (promedio)")

print(f"\n{'='*70}")
print("✅ BENCHMARK COMPLETADO")
print(f"{'='*70}")
