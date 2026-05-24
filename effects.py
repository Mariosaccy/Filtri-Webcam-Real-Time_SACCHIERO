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
#  caricamento immagini con parametri di posizionamento personalizzati
#
#  ogni voce è un dizionario con:
#    "img"      → l'immagine caricata
#    "scala"    → larghezza dell'overlay rispetto alla larghezza della faccia
#                 (es. 1.3 = 30% più largo della faccia)
#    "offset_y" → spostamento verticale espresso come frazione dell'altezza della faccia
#                 il punto di riferimento è il bordo superiore della faccia (y del box)
#                 es.  0.0 → il centro dell'immagine è al bordo superiore della faccia
#                 es. -0.5 → spostato su di metà faccia (buono per cappelli)
#                 es.  0.5 → spostato giù di metà faccia (buono per baffi/bocca)
#                 es.  0.0 → centrato sul bordo superiore (buono per maschere intere)
#
#  come regolare un overlay che non è allineato:
#    troppo in alto  → aumenta offset_y
#    troppo in basso → diminuisci offset_y
#    troppo piccolo  → aumenta scala
#    troppo grande   → diminuisci scala
# ─────────────────────────────────────────────

CAPPELLI = [
    {"img": carica_immagine("cappello1.png"),  "scala": 1.5,  "offset_y": -0.25},
    {"img": carica_immagine("cappello2.png"),  "scala": 1.6,  "offset_y": -0.25},
    {"img": carica_immagine("cappello3.png"),  "scala": 1.5,  "offset_y": -0.35},
    {"img": carica_immagine("cappello4.png"),  "scala": 1.3,  "offset_y": -0.25},
]

MASCHERE = [
    {"img": carica_immagine("maschera1.png"),  "scala": 1.1,  "offset_y": 0.18},
    {"img": carica_immagine("maschera2.png"),  "scala": 1.1,  "offset_y": 0.45},
    {"img": carica_immagine("maschera3.png"),  "scala": 3.3,  "offset_y": 0.55},
    {"img": carica_immagine("maschera4.png"),  "scala": 1.0,  "offset_y": 0.8},
]

BAFFI = [
    {"img": carica_immagine("baffi1.png"),     "scala": 1.1,  "offset_y": 0.7},
    {"img": carica_immagine("baffi2.png"),     "scala": 0.8,  "offset_y": 0.85},
    {"img": carica_immagine("baffi3.png"),     "scala": 0.65,  "offset_y": 0.75},
    {"img": carica_immagine("baffi4.png"),     "scala": 0.25,  "offset_y": 0.7},
]

OCCHIALI = {
    "img":      carica_immagine("occhiali.png"),
    "scala":    0.85,
    # offset_y non usato per gli occhiali: la posizione viene dagli occhi rilevati
}


# ─────────────────────────────────────────────
#  funzione generica che posiziona un overlay sulla faccia
#  usata internamente da metti_cappello, metti_maschera, metti_baffi
# ─────────────────────────────────────────────

def _applica_overlay_faccia(frame, facce, voce):
    # voce è un dizionario con "img", "scala", "offset_y"
    # il punto di ancoraggio è il bordo superiore della faccia (x, y del box)
    # offset_y sposta il centro dell'immagine verso l'alto o il basso rispetto a quel punto
    out = frame.copy()
    img = voce["img"]
    if img is None:
        return out   # file mancante, restituisce il frame senza modifiche

    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        larghezza = int(w * voce["scala"])
        altezza   = int(larghezza * ih / iw)   # mantieni le proporzioni originali

        # centra orizzontalmente sulla faccia
        sx = x + w // 2 - larghezza // 2

        # posizione verticale: partiamo dal bordo superiore della faccia (y)
        # e spostiamo il centro dell'immagine di offset_y * h
        # esempio: offset_y=-0.55 → centro dell'immagine è 0.55*h sopra il bordo della faccia
        centro_y = y + int(h * voce["offset_y"])
        sy = centro_y - altezza // 2

        incolla_con_trasparenza(out, img, sx, sy, larghezza, altezza)
    return out


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
    # per aggiustare la posizione di un cappello specifico, modifica offset_y nella lista CAPPELLI
    voce = CAPPELLI[variante % len(CAPPELLI)]
    return _applica_overlay_faccia(frame, facce, voce)


def metti_maschera(frame, facce, variante=0):
    # sovrappone la maschera scelta sull'intera faccia
    # per aggiustare la posizione, modifica offset_y nella lista MASCHERE
    voce = MASCHERE[variante % len(MASCHERE)]
    return _applica_overlay_faccia(frame, facce, voce)


def metti_baffi(frame, facce, variante=0):
    # sovrappone i baffi scelti nella zona tra naso e bocca
    # per aggiustare la posizione, modifica offset_y nella lista BAFFI
    voce = BAFFI[variante % len(BAFFI)]
    return _applica_overlay_faccia(frame, facce, voce)


def metti_occhiali(frame, facce):
    out = frame.copy()
    img = OCCHIALI["img"]
    if img is None:
        return out

    ih, iw = img.shape[:2]
    scala = OCCHIALI["scala"]
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for (x, y, w, h) in facce:
        roi = grigio[y: y + h, x: x + w]
        occhi = _cascade_occhi.detectMultiScale(roi, scaleFactor=1.1,
                                                minNeighbors=5, minSize=(20, 20))
        if len(occhi) >= 1:
            # SPACCHETTIAMO ANCHE L'ALTEZZA DELL'OCCHIO (eh)
            _, ey, _, eh = sorted(occhi, key=lambda e: e[0])[0]
            # Calcoliamo y_occhi a METÀ dell'altezza dell'occhio, non sul bordo superiore!
            y_occhi = y + ey + (eh // 2)
        else:
            # Aumentato dal 30% al 35/40% per un posizionamento più naturale senza occhi
            y_occhi = y + int(h * 0.38)

        larghezza = int(w * scala)
        altezza = int(larghezza * ih / iw)

        # TWEAK: Offset manuale per abbassare o alzare la montatura
        # Aumentando questo valore (es. + 10 o + 20) scenderanno di più.
        # Usa una percentuale dell'altezza per mantenerlo coerente se la faccia si allontana
        offset_y = int(altezza * 0.15)  # Abbassa gli occhiali del 15% della loro altezza

        sx = x + w // 2 - larghezza // 2
        sy = y_occhi - altezza // 2 + offset_y

        incolla_con_trasparenza(out, img, sx, sy, larghezza, altezza)

    return out


def ghost_effect(frame, frame_precedente):
    # sovrappone il frame corrente con una versione semitrasparente del frame precedente
    # crea un effetto "scia fantasma"
    if frame_precedente is None:
        return frame.copy()
    # addWeighted mescola due immagini: 65% frame attuale + 35% frame precedente
    return cv2.addWeighted(frame, 0.65, frame_precedente, 0.35, 0)


def rilevamento_movimento(frame, frame_precedente, soglia=25):
    # confronta il frame attuale con quello precedente e colora in rosso le zone cambiate
    # soglia: valore da 5 a 100 — basso = rileva anche piccoli movimenti, alto = solo movimenti grandi
    out = frame.copy()
    if frame_precedente is None:
        return out

    # absdiff calcola la differenza assoluta pixel per pixel tra i due frame
    diff   = cv2.absdiff(frame, frame_precedente)
    grigio = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)

    # sfoca leggermente prima della soglia: elimina il rumore della webcam
    # (senza questo, anche stando fermi i pixel rumorosi vengono rilevati come movimento)
    grigio = cv2.GaussianBlur(grigio, (5, 5), 0)

    # tutto ciò che supera la soglia viene considerato "in movimento"
    _, maschera = cv2.threshold(grigio, soglia, 255, cv2.THRESH_BINARY)
    maschera = cv2.dilate(maschera, None, iterations=2)   # ingrandisce le zone rilevate

    # le zone in movimento restano a colori normali, tutto il resto diventa rosso
    # (logica invertita rispetto a prima: così è più intuitivo)
    rosso    = np.full_like(out, [0, 0, 180])
    maschera3 = cv2.cvtColor(maschera, cv2.COLOR_GRAY2BGR).astype(np.float32) / 255.0
    risultato = (maschera3 * out + (1 - maschera3) * rosso).astype(np.uint8)
    # rende il rosso semitrasparente mescolandolo col frame originale
    return cv2.addWeighted(risultato, 0.8, out, 0.2, 0)
