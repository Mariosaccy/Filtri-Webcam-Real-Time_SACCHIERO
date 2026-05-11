"""
main.py
-------
Loop principale dell'applicazione Filtri Webcam AR.
Gestisce: acquisizione frame, orchestrazione filtri, input tastiera,
          registrazione video, screenshot, smoothing dei box facciali.

Controlli tastiera:
  C        – filtro colore successivo
  F        – filtro facciale successivo
  S        – salva screenshot (frame corrente con filtri)
  V        – avvia / ferma registrazione video
  D        – mostra / nascondi rettangoli di debug
  R        – reset tutti i filtri a "Originale / Nessuno"
  Q / ESC  – esci
"""

import cv2
import numpy as np
import time
from datetime import datetime
from collections import deque
from pathlib import Path

from filters import FILTRI_COLORE
from effects import (
    rileva_facce, rileva_upper,
    sfondo_sfocato,
    overlay_cappello, overlay_occhiali, overlay_baffi, overlay_maschera,
    ghost_effect, rilevamento_movimento, motion_blur,
)
from ui import disegna_hud, disegna_barra_filtri, disegna_etichette_facce

# ------------------------------------------------------------------
# Cartelle di output
# ------------------------------------------------------------------
FOTO_DIR  = Path("scatti");        FOTO_DIR.mkdir(exist_ok=True)
VIDEO_DIR = Path("registrazioni"); VIDEO_DIR.mkdir(exist_ok=True)


# ------------------------------------------------------------------
# Filtri facciali disponibili
# Ogni voce: (nome_breve, funzione(frame, facce) -> frame)
# "nessuno" restituisce il frame invariato.
# ------------------------------------------------------------------
FILTRI_FACCIALI = [
    ("Nessuno",          lambda f, fa: f),
    ("Sfondo blur",      sfondo_sfocato),
    ("Cappello",         overlay_cappello),
    ("Occhiali",         overlay_occhiali),
    ("Baffi",            overlay_baffi),
    ("Maschera",         overlay_maschera),
    ("Ghost",            lambda f, fa: ghost_effect(f, _prev_frame)),
    ("Movimento",        lambda f, fa: rilevamento_movimento(f, _prev_frame)),
    ("Motion blur",      lambda f, fa: motion_blur(f)),
]


# ------------------------------------------------------------------
# Smoothing dei box facciali (EMA)
# ------------------------------------------------------------------
class FaceSmoother:
    """Smoothing esponenziale delle coordinate dei bounding box facciali."""

    def __init__(self, alpha: float = 0.5, max_dist_px: int = 200):
        self.alpha       = alpha
        self.max_dist_sq = max_dist_px ** 2
        self._history: dict[int, tuple] = {}
        self._next_id = 0

    def _center(self, b): return b[0] + b[2] // 2, b[1] + b[3] // 2

    def _ema(self, new, old):
        a = self.alpha
        return tuple(int(a * n + (1 - a) * o) for n, o in zip(new, old))

    def update(self, raw) -> list:
        faces = [tuple(b) for b in raw] if len(raw) > 0 else []
        if not faces:
            self._history.clear()
            return []
        if not self._history:
            for b in faces:
                self._history[self._next_id] = b; self._next_id += 1
            return faces

        used, new_hist, smoothed = set(), {}, []
        for box in faces:
            cx, cy = self._center(box)
            best_id, best_d = None, float("inf")
            for oid, ob in self._history.items():
                if oid in used: continue
                ox, oy = self._center(ob)
                d = (cx - ox)**2 + (cy - oy)**2
                if d < best_d: best_d, best_id = d, oid
            if best_id is not None and best_d < self.max_dist_sq:
                sb = self._ema(box, self._history[best_id])
                new_hist[best_id] = sb; used.add(best_id); smoothed.append(sb)
            else:
                nid = self._next_id; self._next_id += 1
                new_hist[nid] = box; smoothed.append(box)
        self._history = new_hist
        return smoothed


# ------------------------------------------------------------------
# Variabile globale per il frame precedente (ghost / movimento)
# ------------------------------------------------------------------
_prev_frame: np.ndarray | None = None


# ------------------------------------------------------------------
# Funzione principale
# ------------------------------------------------------------------
def main() -> None:
    global _prev_frame

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERRORE] Webcam non accessibile.")
        return

    smoother    = FaceSmoother(alpha=0.5)
    idx_colore  = 0
    idx_facciale = 0
    recording   = False
    video_writer: cv2.VideoWriter | None = None
    show_debug  = False

    # Misura FPS reali
    frame_times: deque = deque(maxlen=30)
    fps_display  = 0.0

    print("=" * 60)
    print("  Filtri Webcam AR  |  avviato")
    print("  C=colore  F=filtro  S=foto  V=video  D=debug  R=reset  Q=esci")
    print("=" * 60)

    while True:
        t0 = time.perf_counter()

        ret, frame = cap.read()
        if not ret:
            print("[ERRORE] Frame non leggibile. Uscita.")
            break

        frame = cv2.flip(frame, 1)
        h_fr, w_fr = frame.shape[:2]

        # ── Rilevazione facce ──────────────────────────────────────
        raw_faces = face_cascade.detectMultiScale(
            cv2.equalizeHist(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)),
            scaleFactor=1.15, minNeighbors=5, minSize=(60, 60))
        facce = smoother.update(raw_faces)

        # ── Filtro facciale ────────────────────────────────────────
        nome_facciale, fn_facciale = FILTRI_FACCIALI[idx_facciale]
        frame = fn_facciale(frame, facce)

        # ── Debug: rettangoli ──────────────────────────────────────
        if show_debug:
            for (x, y, w, h) in facce:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)

        # ── Filtro colore ──────────────────────────────────────────
        nome_colore, fn_colore = FILTRI_COLORE[idx_colore]
        frame = fn_colore(frame)

        # ── Registrazione (frame pulito, senza HUD) ────────────────
        if recording and video_writer is not None:
            video_writer.write(frame)

        # ── Etichette facce ────────────────────────────────────────
        disegna_etichette_facce(frame, facce)

        # ── HUD ────────────────────────────────────────────────────
        disegna_hud(frame, nome_colore, nome_facciale,
                    len(facce), fps_display, recording)

        # ── Barra filtri colore in basso ───────────────────────────
        nomi_colori = [n for n, _ in FILTRI_COLORE]
        disegna_barra_filtri(frame, nomi_colori, idx_colore)

        cv2.imshow("Filtri Webcam AR", frame)

        # ── Aggiorna frame precedente ──────────────────────────────
        _prev_frame = frame.copy()

        # ── FPS reali ──────────────────────────────────────────────
        frame_times.append(time.perf_counter() - t0)
        if len(frame_times) == frame_times.maxlen:
            fps_display = 1.0 / (sum(frame_times) / len(frame_times))

        # ── Input tastiera ─────────────────────────────────────────
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("q"), 27):   # Q o ESC
            break

        elif key == ord("c"):
            idx_colore = (idx_colore + 1) % len(FILTRI_COLORE)
            print(f"  → Colore: {FILTRI_COLORE[idx_colore][0]}")

        elif key == ord("f"):
            idx_facciale = (idx_facciale + 1) % len(FILTRI_FACCIALI)
            print(f"  → Filtro facciale: {FILTRI_FACCIALI[idx_facciale][0]}")

        elif key == ord("r"):
            idx_colore = 0; idx_facciale = 0
            print("  → Reset filtri.")

        elif key == ord("d"):
            show_debug = not show_debug
            print(f"  → Debug riquadri: {'ON' if show_debug else 'OFF'}")

        elif key == ord("s"):
            # Salva il frame già filtrato (quello visibile a schermo)
            ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome = FOTO_DIR / f"foto_{nome_colore}_{nome_facciale}_{ts}.jpg"
            cv2.imwrite(str(nome), frame)
            print(f"  → Foto salvata: {nome}")

        elif key == ord("v"):
            if not recording:
                ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
                path = VIDEO_DIR / f"video_{nome_colore}_{nome_facciale}_{ts}.mp4"
                fps_rec = fps_display if fps_display > 1 else 20.0
                video_writer = cv2.VideoWriter(
                    str(path), cv2.VideoWriter_fourcc(*"mp4v"),
                    round(fps_rec), (w_fr, h_fr))
                recording = True
                print(f"  → REC avviata: {path}  ({fps_rec:.1f} FPS)")
            else:
                recording = False
                if video_writer:
                    video_writer.release(); video_writer = None
                print("  → REC fermata.")

    # ── Pulizia risorse ────────────────────────────────────────────
    if recording and video_writer:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()
    print("Programma terminato.")


if __name__ == "__main__":
    main()
