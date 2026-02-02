#!/bin/bash
# knowledge_base.sh - Wrapper para video_to_knowledge_base.py
# Uso: ./knowledge_base.sh "video.mp4" [opciones]

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Banner
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}🎥 Video to Knowledge Base Converter${NC}"
echo -e "${BLUE}========================================${NC}"

# Verificar argumentos
if [ "$#" -lt 1 ]; then
    echo -e "${RED}Error: Se requiere al menos un archivo de video${NC}"
    echo ""
    echo -e "${YELLOW}Uso:${NC}"
    echo "  ./knowledge_base.sh \"video.mp4\""
    echo "  ./knowledge_base.sh \"video.mp4\" -m small -l en"
    echo "  ./knowledge_base.sh \"video.mp4\" --threshold 0.4 --min-interval 3"
    echo ""
    echo -e "${YELLOW}Opciones:${NC}"
    echo "  -m MODEL       Modelo Whisper (tiny, base, small, medium, large)"
    echo "  -l LANGUAGE    Idioma (es, en, fr, etc.)"
    echo "  -o OUTPUT      Archivo de salida personalizado"
    echo "  --threshold N  Umbral de cambio de escena (0-1, default: 0.3)"
    echo "  --min-interval N  Intervalo mínimo entre frames (segundos, default: 2.0)"
    echo ""
    echo -e "${YELLOW}Ejemplos:${NC}"
    echo "  ./knowledge_base.sh \"tutorial.mp4\""
    echo "  ./knowledge_base.sh \"conferencia.mp4\" -m small -l es"
    echo "  ./knowledge_base.sh \"demo.mp4\" --threshold 0.35 --min-interval 3"
    exit 1
fi

# Verificar que existe el archivo
if [ ! -f "$1" ]; then
    echo -e "${RED}❌ Error: Archivo no encontrado: $1${NC}"
    exit 1
fi

# Activar entorno virtual si existe
if [ -d "venv" ]; then
    echo -e "${GREEN}🔧 Activando entorno virtual...${NC}"
    source venv/bin/activate
fi

# Mostrar configuración
echo -e "${BLUE}📹 Video:${NC} $1"
echo -e "${BLUE}⚙️  Ejecutando video_to_knowledge_base.py...${NC}"
echo ""

# Ejecutar script Python con todos los argumentos
python3 video_to_knowledge_base.py "$@"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}✅ Knowledge Base creada exitosamente${NC}"
    echo -e "${GREEN}========================================${NC}"

    # Determinar nombre del archivo de salida
    OUTPUT="${1%.*}.knowledge.md"

    # Buscar -o en argumentos
    for i in "${!@}"; do
        if [ "${!i}" = "-o" ] || [ "${!i}" = "--output" ]; then
            next=$((i+1))
            OUTPUT="${!next}"
            break
        fi
    done

    if [ -f "$OUTPUT" ]; then
        FILE_SIZE=$(du -h "$OUTPUT" | cut -f1)
        echo -e "${BLUE}📄 Archivo:${NC} $OUTPUT"
        echo -e "${BLUE}📦 Tamaño:${NC} $FILE_SIZE"
        echo ""
        echo -e "${YELLOW}💡 Siguiente paso:${NC}"
        echo "   - Abrir con editor Markdown para visualizar"
        echo "   - Ingerir en sistema RAG"
        echo "   - Procesar con LLM multimodal"
    fi
else
    echo ""
    echo -e "${RED}========================================${NC}"
    echo -e "${RED}❌ Error al crear Knowledge Base${NC}"
    echo -e "${RED}========================================${NC}"
    exit 1
fi
