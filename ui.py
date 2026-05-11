"""
ui.py
-----
Tutto ciò che riguarda la visualizzazione delle informazioni sullo schermo:
HUD con filtro/FPS/facce, barra filtri navigabile, indicatore REC.

Le funzioni modificano il frame in-place (sono overlay grafici puri).
"""

import cv2
import numpy as np


# Colori (BGR)
C_VERDE    = (0, 255, 180)
C_GIALLO   = (0, 220, 255)
C_ROSSO    = (0, 0, 220)
C_BIANCO   = (240, 240, 240)
C_GRIGIO   = (160, 160, 160)
C_EVIDENZIA = (0, 200, 255)   # arancio per il filtro attivo


def disegna_hud(frame: np.ndarray, nome_filtro_colore: str,
                nome_filtro_facciale: str, n_facce: int,
                fps: float, recording: bool) -> None:
    """
    Sovrimprime la barra HUD in alto con:
      - nome filtro colore attivo
      - nome filtro facciale attivo
      - numero di facce rilevate
      - FPS calcolati in real time
      - indicatore REC se la registrazione è attiva
    """
    h, w = frame.shape[:2]

    # Sfondo semitrasparente
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, 95), (15, 15, 15), -1)
    cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

    # Riga 1: filtro colore + filtro facciale
    cv2.putText(frame, f"Colore: {nome_filtro_colore}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, C_VERDE, 2, cv2.LINE_AA)
    cv2.putText(frame, f"Filtro: {nome_filtro_facciale}",
                (w // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, C_GIALLO, 2, cv2.LINE_AA)

    # Riga 2: facce + FPS
    cv2.putText(frame, f"Facce: {n_facce}",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_BIANCO, 1, cv2.LINE_AA)
    cv2.putText(frame, f"FPS: {fps:.1f}",
                (w // 2, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_BIANCO, 1, cv2.LINE_AA)

    # Riga 3: comandi
    cv2.putText(frame, "C=colore  F=filtro  S=foto  V=video  D=debug  R=reset  Q=esci",
                (10, 85), cv2.FONT_HERSHEY_SIMPLEX, 0.38, C_GRIGIO, 1, cv2.LINE_AA)

    # Indicatore REC
    if recording:
        cv2.circle(frame, (w - 20, 20), 9, C_ROSSO, -1)
        cv2.putText(frame, "REC", (w - 50, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_ROSSO, 1, cv2.LINE_AA)


def disegna_barra_filtri(frame: np.ndarray, nomi: list[str], idx_attivo: int) -> None:
    """
    Disegna in basso una barra orizzontale con i nomi di tutti i filtri.
    Il filtro attivo è evidenziato in arancio; gli altri in grigio.
    Navigabile con C (prossimo) o tasto sinistro/destro.
    """
    h, w = frame.shape[:2]
    bh   = 36                          # altezza barra
    y0   = h - bh

    # Sfondo
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, y0), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    n     = len(nomi)
    slot  = w // n                     # larghezza di ogni slot
    font  = cv2.FONT_HERSHEY_SIMPLEX
    scale = 0.38

    for i, nome in enumerate(nomi):
        x_center = i * slot + slot // 2
        colore   = C_EVIDENZIA if i == idx_attivo else C_GRIGIO
        spessore = 2 if i == idx_attivo else 1

        # Sottolineatura per il filtro attivo
        if i == idx_attivo:
            cv2.rectangle(frame, (i * slot + 2, y0 + 2),
                          ((i + 1) * slot - 2, h - 2), (50, 50, 50), -1)

        text_size = cv2.getTextSize(nome, font, scale, spessore)[0]
        tx = x_center - text_size[0] // 2
        ty = y0 + bh // 2 + text_size[1] // 2 - 2
        cv2.putText(frame, nome, (tx, ty), font, scale, colore, spessore, cv2.LINE_AA)


def disegna_etichette_facce(frame: np.ndarray, facce: list[tuple],
                             etichetta: str = "Utente") -> None:
    """
    Scrive un'etichetta personalizzata sopra ogni faccia rilevata.
    L'etichetta è configurabile nel codice (parametro `etichetta`).
    """
    for i, (x, y, w, h) in enumerate(facce):
        testo = f"{etichetta} {i + 1}" if len(facce) > 1 else etichetta
        cv2.putText(frame, testo, (x, max(y - 8, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, C_VERDE, 2, cv2.LINE_AA)
