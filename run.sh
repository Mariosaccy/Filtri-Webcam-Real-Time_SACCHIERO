#!/usr/bin/env bash
# ============================================================
#  run.sh  –  Avvio Filtri Webcam AR
#  Uso: bash run.sh
# ============================================================

set -e   # interrompi se un comando fallisce

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Crea e attiva virtualenv se non esiste già
if [ ! -d "venv" ]; then
    echo "[setup] Creazione virtualenv..."
    python3 -m venv venv
fi

# Attiva il virtualenv
source venv/bin/activate

# Installa / aggiorna dipendenze
echo "[setup] Installazione dipendenze..."
pip install --quiet -r requirements.txt

# Crea cartella assets se non esiste (placeholder avvisa l'utente)
mkdir -p assets scatti registrazioni

echo ""
echo "============================================"
echo "  Filtri Webcam AR  –  avvio in corso..."
echo "  Premi Q o ESC nella finestra per uscire."
echo "============================================"
echo ""

python main.py
