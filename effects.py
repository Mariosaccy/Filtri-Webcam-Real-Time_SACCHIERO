"""
effects.py
----------
Effetti che richiedono face detection (Haar cascade) o elaborazione
multi-frame (ghost, motion blur, rilevamento movimento).

Ogni funzione:
  - riceve il frame BGR come primo parametro (+ eventuali parametri extra)
  - restituisce il frame modificato
  - NON modifica l'originale — lavora su una copia
  - ha un commento in cima che ne descrive il comportamento
"""

import cv2
import numpy as np
from pathlib import Path

# ------------------------------------------------------------------
# Caricamento cascades
# ------------------------------------------------------------------
_face_cascade  = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
_upper_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml")
_eye_cascade   = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_eye.xml")

ASSETS_DIR = Path(__file__).parent / "assets"


# ------------------------------------------------------------------
# Helper: rilevazione facce
# ------------------------------------------------------------------
def rileva_facce(frame: np.ndarray) -> list[tuple]:
    """
    Rileva i volti nel frame e restituisce una lista di (x, y, w, h).
    Usa equalizeHist sul grigio per migliorare la rilevazione in ambienti scuri.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    raw  = _face_cascade.detectMultiScale(gray, scaleFactor=1.15,
                                          minNeighbors=5, minSize=(60, 60))
    return [tuple(b) for b in raw] if len(raw) > 0 else []


def rileva_upper(frame: np.ndarray) -> list[tuple]:
    """Rileva il busto superiore nel frame (usato per overlay sul corpo)."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)
    raw  = _upper_cascade.detectMultiScale(gray, scaleFactor=1.2,
                                           minNeighbors=3, minSize=(80, 80))
    return [tuple(b) for b in raw] if len(raw) > 0 else []


# ------------------------------------------------------------------
# Helper: overlay PNG con alpha
# ------------------------------------------------------------------
def _overlay_alpha(frame: np.ndarray, overlay_rgba: np.ndarray,
                   x: int, y: int, w: int, h: int) -> None:
    """
    Sovrappone un'immagine RGBA su frame BGR in posizione (x, y),
    ridimensionata a (w, h). Modifica frame in-place.
    Gestisce correttamente il clipping ai bordi dello schermo.
    """
    if w <= 0 or h <= 0:
        return
    fh, fw = frame.shape[:2]
    ov = cv2.resize(overlay_rgba, (w, h), interpolation=cv2.INTER_AREA)

    x1, y1 = max(x, 0), max(y, 0)
    x2, y2 = min(x + w, fw), min(y + h, fh)
    if x2 <= x1 or y2 <= y1:
        return

    ox1, oy1 = x1 - x, y1 - y
    ov_crop   = ov[oy1: oy1 + (y2 - y1), ox1: ox1 + (x2 - x1)]
    alpha     = ov_crop[:, :, 3:4].astype(np.float32) / 255.0

    dst = frame[y1:y2, x1:x2].astype(np.float32)
    src = ov_crop[:, :, :3].astype(np.float32)
    frame[y1:y2, x1:x2] = np.clip(alpha * src + (1 - alpha) * dst, 0, 255).astype(np.uint8)


def _carica_asset(nome_file: str) -> np.ndarray | None:
    """Carica un PNG RGBA dalla cartella assets/ con gestione errori."""
    path = ASSETS_DIR / nome_file
    img = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"[WARNING] Asset non trovato: {path}")
        return None
    if img.ndim < 3 or img.shape[2] != 4:
        print(f"[WARNING] '{nome_file}' non ha canale alpha.")
        return None
    return img


# Cache asset (caricati una volta sola all'import)
_ASSETS: dict[str, np.ndarray | None] = {
    "cappello": _carica_asset("cappello.png"),
    "occhiali": _carica_asset("occhiali.png"),
    "baffi":    _carica_asset("baffi.png"),
    "maschera": _carica_asset("maschera.png"),
}


# ------------------------------------------------------------------
# Sfondo sfocato (requisito minimo)
# ------------------------------------------------------------------
def sfondo_sfocato(frame: np.ndarray, facce: list[tuple],
                   blur_strength: int = 31) -> np.ndarray:
    """
    Sfoca tutto il frame tranne la regione delle facce rilevate,
    che restano nitide. Usa GaussianBlur forte sullo sfondo.
    """
    out   = frame.copy()
    sfondo = cv2.GaussianBlur(frame, (blur_strength, blur_strength), 0)
    mask   = np.zeros(frame.shape[:2], dtype=np.uint8)

    for (x, y, w, h) in facce:
        # Margine extra per includere un po' di capelli/collo
        pad_x = int(w * 0.15)
        pad_y = int(h * 0.15)
        x1 = max(x - pad_x, 0)
        y1 = max(y - pad_y, 0)
        x2 = min(x + w + pad_x, frame.shape[1])
        y2 = min(y + h + pad_y, frame.shape[0])
        cv2.ellipse(mask, ((x1 + x2) // 2, (y1 + y2) // 2),
                    ((x2 - x1) // 2, (y2 - y1) // 2), 0, 0, 360, 255, -1)

    mask3 = mask[:, :, np.newaxis].astype(np.float32) / 255.0
    out   = (frame * mask3 + sfondo * (1 - mask3)).astype(np.uint8)
    return out


# ------------------------------------------------------------------
# Overlay facciali
# ------------------------------------------------------------------
def overlay_cappello(frame: np.ndarray, facce: list[tuple]) -> np.ndarray:
    """Sovrappone un cappello PNG sopra ogni faccia rilevata."""
    out = frame.copy()
    img = _ASSETS["cappello"]
    if img is None or not facce:
        return out
    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        tw = int(w * 1.3)
        th = int(tw * ih / iw)
        sx = x + w // 2 - tw // 2
        sy = y - int(h * 0.55)
        _overlay_alpha(out, img, sx, sy, tw, th)
    return out


def overlay_occhiali(frame: np.ndarray, facce: list[tuple]) -> np.ndarray:
    """
    Sovrappone occhiali PNG all'altezza degli occhi di ogni faccia.
    Usa la eye cascade per posizionare con precisione; fallback al
    terzo superiore del box facciale se gli occhi non vengono rilevati.
    """
    out = frame.copy()
    img = _ASSETS["occhiali"]
    if img is None or not facce:
        return out
    ih, iw = img.shape[:2]
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    for (x, y, w, h) in facce:
        roi_gray = gray[y: y + h, x: x + w]
        eyes = _eye_cascade.detectMultiScale(roi_gray, scaleFactor=1.1,
                                             minNeighbors=5, minSize=(20, 20))
        if len(eyes) >= 2:
            ex, ey, ew, _ = sorted(eyes, key=lambda e: e[0])[0]
            ey_abs = y + ey
        else:
            ey_abs = y + int(h * 0.3)   # fallback

        tw = int(w * 0.95)
        th = int(tw * ih / iw)
        sx = x + w // 2 - tw // 2
        sy = ey_abs - th // 2
        _overlay_alpha(out, img, sx, sy, tw, th)
    return out


def overlay_baffi(frame: np.ndarray, facce: list[tuple]) -> np.ndarray:
    """Sovrappone baffi PNG nella zona mediana inferiore della faccia."""
    out = frame.copy()
    img = _ASSETS["baffi"]
    if img is None or not facce:
        return out
    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        tw = int(w * 0.7)
        th = int(tw * ih / iw)
        sx = x + w // 2 - tw // 2
        sy = y + int(h * 0.62)
        _overlay_alpha(out, img, sx, sy, tw, th)
    return out


def overlay_maschera(frame: np.ndarray, facce: list[tuple]) -> np.ndarray:
    """Sovrappone una maschera PNG sull'intera faccia rilevata."""
    out = frame.copy()
    img = _ASSETS["maschera"]
    if img is None or not facce:
        return out
    ih, iw = img.shape[:2]
    for (x, y, w, h) in facce:
        tw = int(w * 1.1)
        th = int(tw * ih / iw)
        sx = x + w // 2 - tw // 2
        sy = y + h // 2 - th // 2
        _overlay_alpha(out, img, sx, sy, tw, th)
    return out


# ------------------------------------------------------------------
# Effetti di movimento
# ------------------------------------------------------------------
def ghost_effect(frame: np.ndarray, prev_frame: np.ndarray | None,
                 alpha: float = 0.4) -> np.ndarray:
    """
    Sovrappone il frame corrente con una versione pesata del frame precedente
    (effetto scia/fantasma). Se non c'è frame precedente, restituisce il corrente.
    """
    if prev_frame is None:
        return frame.copy()
    return cv2.addWeighted(frame, 1.0 - alpha, prev_frame, alpha, 0)


def rilevamento_movimento(frame: np.ndarray,
                          prev_frame: np.ndarray | None,
                          soglia: int = 25) -> np.ndarray:
    """
    Evidenzia in rosso le zone del frame che differiscono dal frame precedente
    oltre una certa soglia (rilevamento movimento semplice con absdiff).
    """
    out = frame.copy()
    if prev_frame is None:
        return out

    diff  = cv2.absdiff(frame, prev_frame)
    gray  = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, soglia, 255, cv2.THRESH_BINARY)
    mask  = cv2.dilate(mask, None, iterations=2)

    # Colora di rosso semitrasparente le zone in movimento
    overlay = out.copy()
    overlay[mask > 0] = [0, 0, 200]
    return cv2.addWeighted(overlay, 0.4, out, 0.6, 0)


def motion_blur(frame: np.ndarray, size: int = 15) -> np.ndarray:
    """Applica un motion blur orizzontale simulato con kernel direzionale."""
    out    = frame.copy()
    kernel = np.zeros((size, size), dtype=np.float32)
    kernel[size // 2, :] = 1.0 / size
    return cv2.filter2D(out, -1, kernel)
