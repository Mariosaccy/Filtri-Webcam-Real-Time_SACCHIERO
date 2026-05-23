# filtri webcam ar

applicazione desktop python che accede alla webcam in tempo reale e permette di applicare filtri colore, effetti visivi e overlay facciali. tutto si controlla da tastiera.

supporta anche la **webcam virtuale**: il feed filtrato può essere mandato a un dispositivo webcam virtuale, così lo puoi selezionare in google meet, zoom, teams ecc. come se fosse una vera webcam.

---

## requisiti

| voce | dettaglio |
|------|-----------|
| sistema operativo | linux, macos, windows 10/11 |
| python | 3.10 o superiore |
| hardware | webcam usb o integrata |
| dipendenze | `opencv-python`, `numpy` (installate automaticamente) |

---

## installazione

### 1. clona il repository

```bash
git clone https://github.com/tuo-utente/filtri-webcam-ar.git
cd filtri-webcam-ar
```

### 2. aggiungi le immagini degli overlay

metti nella cartella `assets/` i file png **con canale alpha (rgba)**:

```
assets/
├── cappello.png     ← usato per cappello 1, 2, 3, 4 finché non aggiungi le varianti
├── occhiali.png
├── baffi.png
└── maschera.png
```

> per aggiungere le 4 varianti, basta aggiungere `cappello2.png`, `cappello3.png`, `cappello4.png`
> e modificare i nomi in `effects.py` nella lista `CAPPELLI`. stessa cosa per maschera e baffi.

se un file manca il programma avvisa nella console e disabilita solo quel filtro, non crasha.

### 3. avvio rapido

```bash
bash run.sh
```

lo script crea automaticamente un virtualenv, installa le dipendenze e avvia l'app.

### 4. avvio manuale (alternativa)

```bash
python3 -m venv venv
source venv/bin/activate       # su windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## tasti disponibili

| tasto | azione |
|-------|--------|
| **c** | filtro colore successivo (ciclo tra tutti) |
| **f** | filtro facciale successivo (ciclo tra tutti) |
| **1 2 3 4** | cambia variante di cappello / maschera / baffi |
| **s** | salva screenshot con data e ora in `scatti/` |
| **v** | avvia / ferma registrazione video in `registrazioni/` |
| **d** | mostra / nascondi rettangoli di debug face detection |
| **r** | reset: torna a "originale" e "nessuno" |
| **q** / **esc** | esci e rilascia la webcam |

---

## filtri colore disponibili

| nome | effetto |
|------|---------|
| originale | nessuna modifica |
| b&n | scala di grigi |
| negativo | inversione colori |
| seppia | tono caldo vintage |
| termico | heatmap inferno |
| cartoon | bilateral filter + bordi canny |
| pixelato | pixel art |
| vintage | seppia + vignettatura |
| sketch | effetto matita |

## filtri facciali disponibili

| nome | effetto |
|------|---------|
| nessuno | frame originale |
| sfondo blur | sfoca lo sfondo, faccia nitida |
| cappello | png sopra la testa (varianti 1–4 con tasti 1-4) |
| occhiali | png all'altezza degli occhi |
| baffi | png sotto il naso (varianti 1–4) |
| maschera | png sull'intera faccia (varianti 1–4) |
| ghost | scia del frame precedente |
| movimento | evidenzia in rosso le zone in movimento |

---

## webcam virtuale (per meet, zoom, teams, ecc.)

questa funzione manda il video filtrato a una webcam virtuale sul sistema. poi in meet/zoom selezioni quella webcam invece della tua vera webcam.

### attivazione

1. in `main.py`, cambia questa riga:
   ```python
   WEBCAM_VIRTUALE = False
   ```
   in:
   ```python
   WEBCAM_VIRTUALE = True
   ```

2. installa pyvirtualcam:
   ```bash
   pip install pyvirtualcam
   ```

3. segui le istruzioni per il tuo sistema operativo qui sotto

### su linux (incluso raspberry pi)

installa il modulo kernel `v4l2loopback` che crea il dispositivo webcam virtuale:

```bash
sudo apt-get install v4l2loopback-dkms
sudo modprobe v4l2loopback
```

verifica che sia stato creato:
```bash
ls /dev/video*
```

dovresti vedere un `/dev/video1` (o simile) in più rispetto a prima. quella è la webcam virtuale.

per renderlo permanente (si carica ad ogni avvio):
```bash
echo "v4l2loopback" | sudo tee -a /etc/modules
```

### su windows

installa **obs studio** (gratuito): durante l'installazione include il driver "obs virtual camera".

poi in `main.py` non devi fare altro, pyvirtualcam lo trova automaticamente.

scarica obs: https://obsproject.com

### su macos

su macos pyvirtualcam richiede obs installato oppure il driver "obs-mac-virtualcam".

scarica obs: https://obsproject.com

### come usarla in google meet / zoom

una volta avviato il programma con `WEBCAM_VIRTUALE = True`:

1. apri google meet (o zoom, teams, ecc.)
2. vai nelle impostazioni della videocamera
3. seleziona "obs virtual camera" oppure il dispositivo virtuale che vedi in lista
4. il feed con i filtri appare direttamente nella videochiamata

---

## struttura del progetto

```
progetto/
├── main.py           ← loop principale, gestione tasti, orchestrazione
├── filters.py        ← filtri colore puri
├── effects.py        ← effetti con face detection e overlay
├── ui.py             ← hud, barra filtri, etichette
├── run.sh            ← script di avvio automatico
├── requirements.txt  ← dipendenze python
├── assets/           ← png rgba per gli overlay
├── scatti/           ← screenshot salvati automaticamente
└── registrazioni/    ← video registrati
```

---

## note per raspberry pi

### dipendenze di sistema aggiuntive

```bash
sudo apt-get update
sudo apt-get install -y python3-dev libatlas-base-dev
```

### verifica webcam usb

```bash
ls /dev/video*
```

se compare `/dev/video0` la webcam è riconosciuta.

### performance

su raspberry pi 4 ci si aspetta circa 15–20 fps con i filtri leggeri. cartoon e sfondo blur sono più pesanti (8–12 fps). per ridurre il carico, puoi abbassare la risoluzione aggiungendo in `main.py` dopo `cap = cv2.VideoCapture(0)`:

```python
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
```