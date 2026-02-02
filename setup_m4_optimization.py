#!/usr/bin/env python3
"""
Interactive setup and diagnostics script.
Checks system resources, GPU acceleration, and dependencies.
Works on macOS (Apple Silicon), Linux (NVIDIA CUDA), and CPU fallback.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path

def check_system_info():
    """Show system information (cross-platform)"""
    print("\n" + "="*60)
    print("SYSTEM INFORMATION")
    print("="*60)

    print(f"OS: {platform.system()} {platform.release()}")
    print(f"Architecture: {platform.machine()}")
    print(f"Python: {sys.version.split()[0]}")

    # RAM (cross-platform)
    try:
        import psutil
        ram_gb = psutil.virtual_memory().total / (1024**3)
        print(f"RAM: {ram_gb:.1f} GB")
    except ImportError:
        # Fallback for macOS
        if platform.system() == "Darwin":
            try:
                result = subprocess.run(
                    ["sysctl", "-n", "hw.memsize"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    memory_gb = int(result.stdout.strip()) / (1024**3)
                    print(f"RAM: {memory_gb:.1f} GB")
            except Exception:
                print("RAM: Could not determine")
        # Fallback for Linux
        elif platform.system() == "Linux":
            try:
                with open("/proc/meminfo") as f:
                    for line in f:
                        if line.startswith("MemTotal"):
                            kb = int(line.split()[1])
                            print(f"RAM: {kb / (1024**2):.1f} GB")
                            break
            except Exception:
                print("RAM: Could not determine")
        else:
            print("RAM: Could not determine (install psutil for detection)")

    # CPUs (cross-platform)
    cpu_count = os.cpu_count()
    if cpu_count:
        print(f"CPUs: {cpu_count}")


def check_pytorch_support():
    """Verificar soporte de PyTorch y MPS"""
    print("\n" + "="*60)
    print("🔧 VERIFICACIÓN DE PYTORCH Y MPS")
    print("="*60)

    try:
        import torch
        print(f"✓ PyTorch instalado: {torch.__version__}")

        # Detectar MPS
        if hasattr(torch.backends, 'mps'):
            mps_available = torch.backends.mps.is_available()
            print(f"✓ MPS disponible: {'✨ SÍ' if mps_available else '❌ NO'}")

            if mps_available:
                try:
                    mps_built = torch.backends.mps.is_built()
                    print(f"✓ MPS compilado: {'✓ Sí' if mps_built else '❌ No'}")
                except:
                    pass
        else:
            print("❌ MPS no disponible en esta versión de PyTorch")

        # CUDA
        if torch.cuda.is_available():
            print(f"✓ CUDA disponible: Dispositivo - {torch.cuda.get_device_name(0)}")
        else:
            print("ℹ️  CUDA no disponible (esperado en Mac)")

        # Device
        device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"\n✨ Dispositivo por defecto será: {device}")

    except ImportError:
        print("❌ PyTorch no instalado")
        print("Instala con: pip install torch")
        return False

    return True


def check_whisper():
    """Verificar instalación de Whisper"""
    print("\n" + "="*60)
    print("🎤 VERIFICACIÓN DE WHISPER")
    print("="*60)

    try:
        import whisper
        print(f"✓ Whisper instalado")

        # Verificar modelos descargados
        models_dir = Path.home() / ".cache" / "whisper"
        if models_dir.exists():
            models = list(models_dir.glob("*.pt"))
            print(f"✓ Modelos cacheados: {len(models)}")
            for model in models:
                size_mb = model.stat().st_size / (1024**2)
                print(f"  - {model.name}: {size_mb:.0f} MB")
        else:
            print("ℹ️  Sin modelos cacheados (se descargarán en primer uso)")

    except ImportError:
        print("❌ Whisper no instalado")
        print("Instala con: pip install openai-whisper")
        return False

    return True


def check_ffmpeg():
    """Check FFmpeg installation"""
    print("\n" + "="*60)
    print("FFMPEG CHECK")
    print("="*60)

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"OK: FFmpeg installed: {version_line}")
        else:
            print("MISSING: FFmpeg not found")
    except FileNotFoundError:
        print("MISSING: FFmpeg not found in PATH")
        if platform.system() == "Darwin":
            print("Install with: brew install ffmpeg")
        elif platform.system() == "Linux":
            print("Install with: sudo apt install ffmpeg  (or yum/dnf/pacman)")
        else:
            print("Install from: https://ffmpeg.org/download.html")


def check_scripts():
    """Verificar scripts optimizados"""
    print("\n" + "="*60)
    print("📁 VERIFICACIÓN DE SCRIPTS")
    print("="*60)

    scripts = [
        "simple_audio_to_text.py",
        "process_all_videos_parallel.py",
        "M4_OPTIMIZATION_GUIDE.md"
    ]

    for script in scripts:
        path = Path(__file__).parent / script
        if path.exists():
            print(f"✓ {script}")
        else:
            print(f"❌ {script} - No encontrado")


def show_recommendations():
    """Mostrar recomendaciones"""
    print("\n" + "="*60)
    print("💡 RECOMENDACIONES")
    print("="*60)

    print("""
1. **Para mejor rendimiento:**
   - Cierra aplicaciones no esenciales
   - Usa el modelo 'base' por defecto
   - Ejecuta una sola transcripción a la vez

2. **Comandos rápidos:**

   Archivo individual:
   $ source venv/bin/activate
   $ python3 simple_audio_to_text.py "archivo.mp4" -m base -l es -t

   Carpeta completa:
   $ python3 process_all_videos_parallel.py

3. **Para mayor precisión:**
   - Usa modelo 'small' en lugar de 'base'
   - Toma ~2x más tiempo pero mejor calidad

4. **Troubleshooting:**
   - Lee M4_OPTIMIZATION_GUIDE.md
   - Revisa los logs del script
   - Prueba con -d cpu si tienes problemas de MPS
    """)


def main():
    print("\n TRANSCRIBO - System Diagnostics")
    print("="*60)

    check_system_info()
    pytorch_ok = check_pytorch_support()
    whisper_ok = check_whisper()
    check_ffmpeg()
    check_scripts()

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    if pytorch_ok and whisper_ok:
        from core.device import get_device
        device = get_device()
        accel = {"mps": "Apple Silicon (MPS)", "cuda": "NVIDIA GPU (CUDA)", "cpu": "CPU"}
        print(f"""
SYSTEM READY - Acceleration: {accel.get(device, device)}

Next steps:
  python3 simple_audio_to_text.py "file.mp4" -m base -l es
  python3 cli_pipeline.py "https://youtube.com/watch?v=xxx"
        """)
    else:
        print("""
MISSING DEPENDENCIES

Install with:
  pip install -r requirements.txt

Then re-run this script.
        """)

    print("="*60 + "\n")


if __name__ == "__main__":
    main()
