# Filtri Webcam AR

Applicazione desktop Python che accede alla webcam in tempo reale e permette di applicare filtri colore, effetti visivi e overlay facciali interattivi. Tutto viene controllato da tastiera mentre la webcam è attiva.

---

## Requisiti

| Voce | Dettaglio |
|------|-----------|
| Sistema operativo | Linux, macOS, Windows 10/11 |
| Python | 3.10 o superiore |
| Hardware | Webcam USB o integrata |
| Dipendenze | `opencv-python`, `numpy` (installate automaticamente) |

---

## Installazione step by step

### 1. Clona il repository

```bash
git clone https://github.com/tuo-utente/filtri-webcam-ar.git
cd filtri-webcam-ar
```

### 2. Aggiungi le immagini dei filtri

Copia nella cartella `assets/` i file PNG **con canale alpha (RGBA)**:

```
assets/
├── cappello.png
├── occhiali.png
├── baffi.png
└── maschera.png
```

> Se un file manca il programma avvisa nella console e disabilita solo quel filtro — non crasha.

### 3. Avvio rapido (consigliato)

```bash
bash run.sh
```

Lo script crea automaticamente un virtualenv, installa le dipendenze e avvia l'applicazione.

### 4. Avvio manuale (alternativa)

```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## Tasti disponibili

| Tasto | Azione |
|-------|--------|
| **C** | Filtro colore successivo (ciclo) |
| **F** | Filtro facciale successivo (ciclo) |
| **S** | Salva screenshot con data/ora in `scatti/` |
| **V** | Avvia / ferma registrazione video in `registrazioni/` |
| **D** | Mostra / nascondi rettangoli di debug face detection |
| **R** | Reset: torna a "Originale" e "Nessuno" |
| **Q** / **ESC** | Esci e rilascia la webcam |

---

## Filtri colore disponibili

| Nome | Effetto |
|------|---------|
| Originale | Nessuna modifica |
| B&N | Scala di grigi |
| Negativo | Inversione valori pixel |
| Seppia | Tonalità calda vintage |
| Termico | Heatmap INFERNO |
| Cartoon | Bilateral filter + bordi Canny |
| Pixelato | Effetto pixel art |
| Vignetta | Bordi scurati progressivamente |
| Vintage | Seppia + vignettatura |
| Sketch | Effetto matita |

## Filtri facciali disponibili

| Nome | Effetto |
|------|---------|
| Nessuno | Solo frame originale |
| Sfondo blur | Sfoca tutto tranne le facce |
| Cappello | PNG sovrapposto sopra la testa |
| Occhiali | PNG posizionato all'altezza degli occhi |
| Baffi | PNG nella zona mediana inferiore della faccia |
| Maschera | PNG sull'intera faccia |
| Ghost | Scia del frame precedente |
| Movimento | Evidenzia in rosso le zone in movimento |
| Motion blur | Blur direzionale orizzontale |

---

## Struttura del progetto

```
progetto/
├── main.py           # Loop principale, gestione tasti, orchestrazione
├── filters.py        # Filtri colore (grigio, negativo, cartoon, ecc.)
├── effects.py        # Effetti con face detection e multi-frame
├── ui.py             # HUD, barra filtri, etichette facce
├── run.sh            # Script di avvio automatico
├── requirements.txt  # Dipendenze Python con versioni
├── assets/           # PNG RGBA per overlay facciali
├── scatti/           # Screenshot salvati automaticamente
└── registrazioni/    # Video registrati
```

---

## Note specifiche per Raspberry Pi

### Dipendenza di sistema aggiuntiva

Su Raspberry Pi OS potrebbe servire:

```bash
sudo apt-get update
sudo apt-get install -y python3-dev libatlas-base-dev
```

### Webcam USB

Verificare che la webcam sia riconosciuta:

```bash
ls /dev/video*
```

Se appare `/dev/video0` la webcam è disponibile.

### Performance

Su Raspberry Pi 4 l'applicazione gira a circa 15–20 FPS con i filtri leggeri. I filtri più pesanti (Cartoon, Sfondo blur) possono scendere a 8–12 FPS. Per migliorare le performance:

1. Ridurre la risoluzione della webcam nel codice:
   ```python
   cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
   cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
   ```
2. Usare l'ambiente `venv` come da script `run.sh` — evita conflitti con i pacchetti di sistema.

### Display

Se si usa Raspberry Pi senza desktop (headless), è necessario un display collegato via HDMI o la variabile `DISPLAY` configurata correttamente. L'app non supporta modalità headless.
