#!/bin/bash
# Transcribo - Quick transcription wrapper

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función de ayuda
show_help() {
    cat <<EOF
${BLUE}════════════════════════════════════════════════${NC}
${GREEN}Transcribo - Quick Transcription${NC}
${BLUE}════════════════════════════════════════════════${NC}

${YELLOW}Uso:${NC}
  ./transcribe.sh [archivo] [opciones]

${YELLOW}Ejemplos:${NC}
  # Transcripción básica en español
  ./transcribe.sh "video.mp4"

  # Con timestamps
  ./transcribe.sh "video.mp4" -t

  # Modelo diferente
  ./transcribe.sh "video.mp4" -m small

  # Inglés con timestamps
  ./transcribe.sh "audio.mp3" -l en -t

  # Forzar CPU (debug)
  ./transcribe.sh "video.mp4" -d cpu

${YELLOW}Opciones:${NC}
  -m, --model      Modelo (tiny, base, small, medium, large) [default: large]
  -l, --language   Idioma (es, en, fr, etc) [default: es]
  -t, --timestamps Incluir timestamps en salida
  -d, --device     Dispositivo (mps, cpu, cuda) [auto-detecta MPS]
  -h, --help       Mostrar esta ayuda

${YELLOW}Modelos (M4 Pro 48GB):${NC}
  • large (default) - 🚀 MÁXIMA PRECISIÓN, aprovecha M4 Pro
  • medium         - Muy buena precisión, más rápido
  • small          - Balance precisión/velocidad
  • base/tiny      - Solo para testing rápido

${YELLOW}Idiomas soportados:${NC}
  es (español), en (inglés), fr (francés), de (alemán),
  ja (japonés), zh (chino), y muchos más...

${BLUE}════════════════════════════════════════════════${NC}
EOF
}

# Validar que existe el archivo
if [[ $# -eq 0 || "$1" == "-h" || "$1" == "--help" ]]; then
    show_help
    exit 0
fi

ARCHIVO="$1"
MODEL="large"
LANGUAGE="es"
TIMESTAMPS=""
DEVICE=""

# Parsear argumentos
shift
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--model)
            MODEL="$2"
            shift 2
            ;;
        -l|--language)
            LANGUAGE="$2"
            shift 2
            ;;
        -t|--timestamps)
            TIMESTAMPS="-t"
            shift
            ;;
        -d|--device)
            DEVICE="-d $2"
            shift 2
            ;;
        *)
            echo "${RED}Error: Opción desconocida: $1${NC}"
            exit 1
            ;;
    esac
done

# Validar archivo
if [ ! -f "$ARCHIVO" ]; then
    echo "${RED}❌ Error: No se encuentra el archivo: $ARCHIVO${NC}"
    exit 1
fi

# Mostrar configuración
echo ""
echo "${BLUE}════════════════════════════════════════════════${NC}"
echo "${GREEN}🚀 Transcribiendo con optimizaciones M4${NC}"
echo "${BLUE}════════════════════════════════════════════════${NC}"
echo "${YELLOW}Archivo:${NC}    $ARCHIVO"
echo "${YELLOW}Modelo:${NC}     $MODEL"
echo "${YELLOW}Idioma:${NC}     $LANGUAGE"
echo "${YELLOW}Timestamps:${NC} $([ -n "$TIMESTAMPS" ] && echo "Sí" || echo "No")"
echo "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# Activar venv y ejecutar
source venv/bin/activate

# Construir comando
CMD="python3 simple_audio_to_text.py \"$ARCHIVO\" -m $MODEL -l $LANGUAGE $TIMESTAMPS $DEVICE"

# Ejecutar
eval "$CMD"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo "${GREEN}✅ Transcripción completada exitosamente${NC}"
    echo ""
else
    echo ""
    echo "${RED}❌ Error durante la transcripción${NC}"
    exit 1
fi
