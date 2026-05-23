# filters.py
# questo file contiene tutte le funzioni che cambiano i colori del frame
# ogni funzione riceve il frame (l'immagine della webcam) e restituisce il frame modificato

import cv2
import numpy as np


def originale(frame):
    # non fa niente, restituisce il frame così com'è
    return frame.copy()


def bianco_e_nero(frame):
    # converte il frame in scala di grigi, poi lo riconverte in BGR
    # (serve riconvertirlo in BGR perché opencv lavora sempre con 3 canali)
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(grigio, cv2.COLOR_GRAY2BGR)


def negativo(frame):
    # inverte tutti i colori: il bianco diventa nero, il rosso diventa ciano, ecc.
    return cv2.bitwise_not(frame)


def seppia(frame):
    # effetto foto vecchia: converte in grigio e poi colora con tonalità marroncina
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    out = np.zeros_like(frame, dtype=np.float32)
    out[:, :, 0] = grigio * 112   # canale blu (basso)
    out[:, :, 1] = grigio * 156   # canale verde (medio)
    out[:, :, 2] = grigio * 200   # canale rosso (alto) → dà il tono caldo
    return np.clip(out, 0, 255).astype(np.uint8)


def termico(frame):
    # simula una telecamera termica: converte in grigio e applica una tavolozza di colori caldi
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(grigio, cv2.COLORMAP_INFERNO)


def cartoon(frame):
    # effetto fumetto: prima smussa i colori con bilateralFilter (ripetuto più volte),
    # poi rileva i bordi con Canny e li sovrappone in nero
    colorato = frame.copy()
    for _ in range(4):
        # bilateralFilter mantiene i bordi ma smussa le aree piatte → effetto dipinto
        colorato = cv2.bilateralFilter(colorato, d=9, sigmaColor=75, sigmaSpace=75)

    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    bordi  = cv2.Canny(grigio, 50, 150)           # trova i contorni
    bordi_inv = cv2.bitwise_not(bordi)            # inverti: bordi neri su sfondo bianco
    bordi_bgr = cv2.cvtColor(bordi_inv, cv2.COLOR_GRAY2BGR)
    return cv2.bitwise_and(colorato, bordi_bgr)   # combina colori + bordi neri


def pixelato(frame):
    # rimpicciolisce il frame e lo riingrandisce senza interpolazione → effetto pixel art
    h, w = frame.shape[:2]
    block = 12   # più è grande, più i "pixel" sono grossi
    piccolo = cv2.resize(frame, (max(1, w // block), max(1, h // block)),
                         interpolation=cv2.INTER_NEAREST)
    return cv2.resize(piccolo, (w, h), interpolation=cv2.INTER_NEAREST)


def vintage(frame):
    # seppia + bordi scuri (vignettatura) → effetto foto d'epoca completo
    sep = seppia(frame)
    h, w = sep.shape[:2]
    # crea una griglia di coordinate da -1 a 1 per x e y
    X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    # calcola la distanza dal centro per ogni pixel → più è lontano, più è scuro
    maschera = 1.0 - np.clip(np.sqrt(X**2 + Y**2) * 0.85, 0, 1)
    return (sep.astype(np.float32) * maschera[:, :, np.newaxis]).astype(np.uint8)


def sketch(frame):
    # effetto matita: divide il grigio per la sua versione sfocata → esalta i dettagli fini
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    sfocato = cv2.GaussianBlur(grigio, (21, 21), 0)
    matita  = cv2.divide(grigio, sfocato, scale=256)
    return cv2.cvtColor(matita, cv2.COLOR_GRAY2BGR)


# lista di tutti i filtri disponibili: ogni voce è (nome da mostrare, funzione da chiamare)
# main.py usa questa lista per scorrere i filtri con il tasto C
FILTRI_COLORE = [
    ("Originale", originale),
    ("B&N",       bianco_e_nero),
    ("Negativo",  negativo),
    ("Seppia",    seppia),
    ("Termico",   termico),
    ("Cartoon",   cartoon),
    ("Pixelato",  pixelato),
    ("Vintage",   vintage),
    ("Sketch",    sketch),
]