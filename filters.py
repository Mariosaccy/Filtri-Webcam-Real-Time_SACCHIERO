"""
filters.py
----------
Funzioni per i filtri colore applicabili al frame webcam.
Ogni funzione:
  - riceve il frame BGR come primo parametro
  - restituisce il frame modificato (NON modifica l'originale)
  - lavora su una copia interna se necessario
"""

import cv2
import numpy as np


def originale(frame: np.ndarray) -> np.ndarray:
    """Restituisce il frame senza modifiche."""
    return frame.copy()


def bianco_e_nero(frame: np.ndarray) -> np.ndarray:
    """Converte il frame in scala di grigi (output BGR a 3 canali)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


def negativo(frame: np.ndarray) -> np.ndarray:
    """Inverte tutti i valori dei pixel (effetto negativo fotografico)."""
    return cv2.bitwise_not(frame)


def seppia(frame: np.ndarray) -> np.ndarray:
    """Applica una tonalità seppia calda (effetto foto vintage)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    out = np.zeros_like(frame, dtype=np.float32)
    out[:, :, 0] = gray * 112   # B
    out[:, :, 1] = gray * 156   # G
    out[:, :, 2] = gray * 200   # R
    return np.clip(out, 0, 255).astype(np.uint8)


def termico(frame: np.ndarray) -> np.ndarray:
    """Applica una heatmap (COLORMAP_INFERNO) per effetto termico."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.applyColorMap(gray, cv2.COLORMAP_INFERNO)


def cartoon(frame: np.ndarray) -> np.ndarray:
    """
    Effetto fumetto: bilateral filter ripetuto per appiattire i colori,
    bordi Canny sovrapposti in nero.
    """
    color = frame.copy()
    for _ in range(4):
        color = cv2.bilateralFilter(color, d=9, sigmaColor=75, sigmaSpace=75)

    gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    edges = cv2.Canny(gray, threshold1=50, threshold2=150)
    edges_inv = cv2.bitwise_not(edges)                 # bordi neri su sfondo bianco
    edges_bgr  = cv2.cvtColor(edges_inv, cv2.COLOR_GRAY2BGR)

    return cv2.bitwise_and(color, edges_bgr)


def pixelato(frame: np.ndarray, block: int = 12) -> np.ndarray:
    """Riduce e reingrandisce il frame con interpolazione nearest (pixel art)."""
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (max(1, w // block), max(1, h // block)),
                       interpolation=cv2.INTER_NEAREST)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)


def vignettatura(frame: np.ndarray) -> np.ndarray:
    """Scurisce progressivamente i bordi con una maschera circolare NumPy."""
    h, w = frame.shape[:2]
    X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    mask  = 1.0 - np.clip(np.sqrt(X**2 + Y**2) * 0.85, 0, 1)
    out   = (frame.astype(np.float32) * mask[:, :, np.newaxis])
    return np.clip(out, 0, 255).astype(np.uint8)


def vintage(frame: np.ndarray) -> np.ndarray:
    """Seppia + vignettatura: effetto foto vintage completo."""
    return vignettatura(seppia(frame))


def sketch(frame: np.ndarray) -> np.ndarray:
    """Effetto matita: divisione del grigio per la sua versione sfocata."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (21, 21), 0)
    edges = cv2.divide(gray, blur, scale=256)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)


# ------------------------------------------------------------------
# Registro unico dei filtri: (nome_breve, funzione)
# Usato da main.py e ui.py per iterare senza duplicare le liste.
# ------------------------------------------------------------------
FILTRI_COLORE: list[tuple[str, callable]] = [
    ("Originale", originale),
    ("B&N",       bianco_e_nero),
    ("Negativo",  negativo),
    ("Seppia",    seppia),
    ("Termico",   termico),
    ("Cartoon",   cartoon),
    ("Pixelato",  pixelato),
    ("Vignetta",  vignettatura),
    ("Vintage",   vintage),
    ("Sketch",    sketch),
]
