#!/usr/bin/env bash
# run.sh — avvia l'applicazione filtri webcam ar
# uso: bash run.sh

set -e   # se un comando fallisce, lo script si ferma

# vai nella cartella dove si trova questo script
cd "$(dirname "${BASH_SOURCE[0]}")"

# crea il virtualenv se non esiste ancora
if [ ! -d "venv" ]; then
    echo "[setup] creo il virtualenv..."
    python3 -m venv venv
fi

# attiva il virtualenv
source venv/bin/activate

# installa le dipendenze (salta quelle già installate)
echo "[setup] installo le dipendenze..."
pip install --quiet -r requirements.txt

# crea le cartelle necessarie se non esistono
mkdir -p assets scatti registrazioni

echo ""
echo "============================================"
echo "  filtri webcam ar — in avvio..."
echo "  premi Q nella finestra per uscire"
echo "============================================"
echo ""

python main.py