# effects.py
# questo file gestisce gli effetti che richiedono il rilevamento del volto,
# come lo sfondo sfocato e gli overlay (cappelli, occhiali, baffi, maschere)
# gestisce anche gli effetti multi-frame come il ghost e il movimento

import cv2
import numpy as np
from pathlib import Path

# percorso della cartella con le immagini png (relativo a questo file)
ASSETS = Path(__file__).parent / "assets"

# carica i cascade di opencv per rilevare facce e occhi
# questi file xml sono già inclusi con opencv, non serve scaricarli
_cascade_facce  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_cascade_occhi  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")


# ─────────────────────────────────────────────
#  funzioni di supporto
# ─────────────────────────────────────────────

def carica_immagine(nome_file):
    # carica un png con canale alpha (trasparenza) dalla cartella assets
    # se il file non esiste o non ha la trasparenza, avvisa e restituisce None
    percorso = ASSETS / nome_file
    img = cv2.imread(str(percorso), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"[attenzione] file non trovato: {percorso}")
        return None
    if img.ndim < 3 or img.shape[2] != 4:
        print(f"[attenzione] '{nome_file}' non ha il canale alpha, serve un png rgba")
        return None
    return img


def incolla_con_trasparenza(frame, immagine_rgba, x, y, larghezza, altezza):
    # incolla un'immagine rgba (con trasparenza) sopra il frame
    # x, y è l'angolo in alto a sinistra dove inizia l'immagine
    # gestisce anche il caso in cui l'immagine esca dai bordi del frame

    if larghezza <= 0 or altezza <= 0:
        return   # dimensioni non valide, non fare niente

    h_frame, w_frame = frame.shape[:2]

    # ridimensiona l'immagine alle dimensioni richieste
    img = cv2.resize(immagine_rgba, (larghezza, altezza), interpolation=cv2.INTER_AREA)

    # calcola la zona del frame dove incollare (con clip ai bordi)
    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + larghezza, w_frame), min(y + altezza, h_frame)
    if x2 <= x1 or y2 <= y1:
        return   # completamente fuori schermo, non fare niente

    # se l'immagine è parzialmente fuori (es. cappello a bordo schermo),
    # dobbiamo prendere solo la parte visibile dell'immagine
    ox = x1 - x
    oy = y1 - y
    img_crop = img[oy: oy + (y2 - y1), ox: ox + (x2 - x1)]

    # estrai il canale alpha e normalizzalo tra 0 e 1
    alpha = img_crop[:, :, 3:4].astype(np.float32) / 255.0

    # mescola pixel per pixel: dove alpha=1 vedi l'immagine, dove alpha=0 vedi il frame
    zona_frame = frame[y1:y2, x1:x2].astype(np.float32)
    zona_img   = img_crop[:, :, :3].astype(np.float32)
    frame[y1:y2, x1:x2] = (alpha * zona_img + (1 - alpha) * zona_frame).astype(np.uint8)


def rileva_facce(frame):
    # rileva i volti nel frame e restituisce una lista di rettangoli (x, y, w, h)
    # equalizeHist migliora il contrasto del grigio → rileva meglio in condizioni di luce difficile
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    grigio = cv2.equalizeHist(grigio)
    raw = _cascade_facce.detectMultiScale(grigio, scaleFactor=1.15,
                                          minNeighbors=5, minSize=(60, 60))
    # detectMultiScale restituisce un array numpy vuoto se non trova niente,
    # quindi controlliamo con len() invece di "if raw"
    return [tuple(b) for b in raw] if len(raw) > 0 else []


# ─────────────────────────────────────────────
#  caricamento immagini (fatto una volta sola all'avvio)
#  ogni lista ha 4 varianti: intanto puntano tutte allo stesso file,
#  poi puoi sostituirle con file diversi (es. cappello2.png, cappello3.png...)
# ─────────────────────────────────────────────

CAPPELLI = [
    carica_immagine("cappello.png"),    # cappello 1
    carica_immagine("cappello.png"),    # cappello 2 — sostituisci con cappello2.png
    carica_immagine("cappello.png"),    # cappello 3 — sostituisci con cappello3.png
    carica_immagine("cappello.png"),    # cappello 4 — sostituisci con cappello4.png
]

MASCHERE = [
    carica_immagine("maschera.png"),    # maschera 1
    carica_immagine("maschera.png"),    # maschera 2 — sostituisci con maschera2.png
    carica_immagine("maschera.png"),    # maschera 3 — sostituisci con maschera3.png
    carica_immagine("maschera.png"),    # maschera 4 — sostituisci con maschera4.png
]

BAFFI = [
    carica_immagine("baffi.png"),       # baffi 1
    carica_immagine("baffi.png"),       # baffi 2 — sostituisci con baffi2.png
    carica_immagine("baffi.png"),       # baffi 3 — sostituisci con baffi3.png
    carica_immagine("baffi.png"),       # baffi 4 — sostituisci con baffi4.png
]

OCCHIALI = carica_immagine("occhiali.png")


# ─────────────────────────────────────────────
#  effetti principali
# ─────────────────────────────────────────────

def sfondo_sfocato(frame, facce):
    # sfoca tutto il frame, poi "ritaglia" le facce nitide e le incolla sopra
    # così sembra che solo lo sfondo sia sfocato
    sfocato = cv2.GaussianBlur(frame, (31, 31), 0)
    risultato = sfocato.copy()

    for (x, y, w, h) in facce:
        # prendi un po' di margine attorno alla faccia (15%) per non tagliare le orecchie
        mx = int(w * 0.15)
        my = int(h * 0.15)
        x1 = max(x - mx, 0)
        y1 = max(y - my, 0)
        x2 = min(x + w + mx, frame.shape[1])
        y2 = min(y + h + my, frame.shape[0])
        # copia la zona nitida dal frame originale nello sfondo sfocato
        risultato[y1:y2, x1:x2] = frame[y1:y2, x1:x2]

    return risultato


def metti_cappello(frame, facce, variante=0):
    # sovrappone il cappello scelto (variante 0-3) sopra ogni faccia
    out = frame.copy()
    img = CAPPELLI[variante % len(CAPPELLI)]   # usa il modulo per non uscire dalla lista
    if img is None:
        return out   # se il file non esiste, restituisce il frame senza modifiche

    ih, iw = img.shape[:2]   # dimensioni originali dell'immagine cappello
    for (x, y, w, h) in facce:
        larghezza = int(w * 1.3)             # il cappello è un po' più largo della faccia
        altezza   = int(larghezza * ih / iw) # mantieni le proporzioni dell'immagine
        sx = x + w // 2 - larghezza // 2    # centra orizzontalmente sulla faccia
        sy = y - int(h * 0.55)              # metti sopra la testa
        incolla_con_trasparenza(out, img, sx, sy, larghezza, altezza)
    return out


def metti_maschera(frame, facce, variante=0):
    # sovrappone la maschera scelta sull'intera faccia
    out = frame.copy()
    img = MASCHERE[variante % len(MASCHERE)]
    if img is None:
        return out

    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        larghezza = int(w * 1.1)
        altezza   = int(larghezza * ih / iw)
        sx = x + w // 2 - larghezza // 2
        sy = y + h // 2 - altezza // 2      # centra verticalmente sulla faccia
        incolla_con_trasparenza(out, img, sx, sy, larghezza, altezza)
    return out


def metti_baffi(frame, facce, variante=0):
    # sovrappone i baffi scelti nella zona tra naso e bocca
    out = frame.copy()
    img = BAFFI[variante % len(BAFFI)]
    if img is None:
        return out

    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        larghezza = int(w * 0.7)
        altezza   = int(larghezza * ih / iw)
        sx = x + w // 2 - larghezza // 2
        sy = y + int(h * 0.62)              # circa al 62% dall'alto della faccia
        incolla_con_trasparenza(out, img, sx, sy, larghezza, altezza)
    return out


def metti_occhiali(frame, facce):
    # sovrappone gli occhiali all'altezza degli occhi
    # usa la eye cascade per trovare la posizione precisa, altrimenti usa un'altezza di default
    out = frame.copy()
    if OCCHIALI is None:
        return out

    ih, iw = OCCHIALI.shape[:2]
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for (x, y, w, h) in facce:
        # cerca gli occhi solo dentro il rettangolo della faccia
        roi = grigio[y: y + h, x: x + w]
        occhi = _cascade_occhi.detectMultiScale(roi, scaleFactor=1.1,
                                                minNeighbors=5, minSize=(20, 20))
        if len(occhi) >= 1:
            # usa il primo occhio trovato per l'altezza
            _, ey, _, _ = sorted(occhi, key=lambda e: e[0])[0]
            y_occhi = y + ey
        else:
            # se non trova occhi, stima che siano al 30% dall'alto della faccia
            y_occhi = y + int(h * 0.30)

        larghezza = int(w * 0.95)
        altezza   = int(larghezza * ih / iw)
        sx = x + w // 2 - larghezza // 2
        sy = y_occhi - altezza // 2
        incolla_con_trasparenza(out, OCCHIALI, sx, sy, larghezza, altezza)
    return out


def ghost_effect(frame, frame_precedente):
    # sovrappone il frame corrente con una versione semitrasparente del frame precedente
    # crea un effetto "scia fantasma"
    if frame_precedente is None:
        return frame.copy()
    # addWeighted mescola due immagini: 65% frame attuale + 35% frame precedente
    return cv2.addWeighted(frame, 0.65, frame_precedente, 0.35, 0)


def rilevamento_movimento(frame, frame_precedente):
    # confronta il frame attuale con quello precedente e colora in rosso le zone cambiate
    out = frame.copy()
    if frame_precedente is None:
        return out

    # absdiff calcola la differenza assoluta pixel per pixel tra i due frame
    diff  = cv2.absdiff(frame, frame_precedente)
    grigio = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # tutto ciò che ha differenza > 25 viene considerato "in movimento"
    _, maschera = cv2.threshold(grigio, 25, 255, cv2.THRESH_BINARY)
    maschera = cv2.dilate(maschera, None, iterations=2)   # ingrandisce le zone rilevate

    # colora le zone in rosso semitrasparente
    rosso = out.copy()
    rosso[maschera > 0] = [0, 0, 200]
    return cv2.addWeighted(rosso, 0.4, out, 0.6, 0)