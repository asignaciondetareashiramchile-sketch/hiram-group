#!/bin/bash
# ============================================================
#  HIRAM GROUP – AI Platform Startup Script
# ============================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "  ╔══════════════════════════════════════════════════╗"
echo "  ║   HIRAM GROUP – AI Enterprise Agent Platform    ║"
echo "  ║   Hiram Chile · ProClean Facilities              ║"
echo "  ╚══════════════════════════════════════════════════╝"
echo ""

# Verify Python
if ! command -v python3 &>/dev/null; then
    echo "❌ Python3 no encontrado. Por favor instala Python 3.9+"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import fastapi" &>/dev/null 2>&1; then
    echo "📦 Instalando dependencias..."
    pip3 install -r requirements.txt
fi

# Copy .env if missing
if [ ! -f .env ]; then
    cp .env.example .env
    echo "⚙️  Archivo .env creado. Edita las variables antes de usar en producción."
fi

echo "🚀 Iniciando plataforma en http://localhost:8000"
echo "   Usuario: admin | Contraseña: HiramGroup2024!"
echo ""

# Try to use tmux if available
if command -v tmux &>/dev/null; then
    SESSION="hiram-group"
    tmux kill-session -t $SESSION 2>/dev/null || true
    tmux new-session -d -s $SESSION -n "server"
    tmux send-keys -t $SESSION:server "cd $SCRIPT_DIR && python3 run.py" Enter
    tmux new-window -t $SESSION -n "logs"
    echo "✅ Servidor iniciado en sesión tmux: $SESSION"
    echo "   Ver logs: tmux attach -t $SESSION"
    echo "   Detener:  tmux kill-session -t $SESSION"
    echo ""
    echo "   Abre tu navegador en: http://localhost:8000"
else
    echo "ℹ️  tmux no disponible. Iniciando directamente..."
    echo ""
    python3 run.py
fi
