import cv2
import numpy as np
from datetime import datetime
import os

# ----------------------------------------------
#  FUNZIONE PER SOVRAPPORRE UN'IMMAGINE CON ALPHA
# ----------------------------------------------
def overlay_image_alpha(frame, overlay, x, y, target_w, target_h):
    """
    Sovrappone un'immagine RGBA (con trasparenza) su frame.
    x, y: coordinate dell'angolo in alto a sinistra dell'overlay.
    target_w, target_h: dimensioni a cui ridimensionare overlay.
    """
    h_frame, w_frame = frame.shape[:2]
    # Ridimensiona l'overlay mantenendo le proporzioni
    overlay_resized = cv2.resize(overlay, (target_w, target_h), interpolation=cv2.INTER_AREA)

    # Estrai canale alpha e normalizza
    alpha_overlay = overlay_resized[:, :, 3] / 255.0
    alpha_frame = 1.0 - alpha_overlay

    # Definisci la regione del frame dove applicare l'overlay
    x1 = max(x, 0)
    y1 = max(y, 0)
    x2 = min(x + target_w, w_frame)
    y2 = min(y + target_h, h_frame)

    if x2 <= x1 or y2 <= y1:
        return  # fuori schermo

    # Ritaglia overlay e alpha alla regione visibile
    overlay_crop = overlay_resized[0:y2 - y1, 0:x2 - x1]
    alpha_overlay_crop = alpha_overlay[0:y2 - y1, 0:x2 - x1]
    alpha_frame_crop = alpha_frame[0:y2 - y1, 0:x2 - x1]

    # Applica la miscelazione canale per canale
    for c in range(3):
        frame[y1:y2, x1:x2, c] = (
            alpha_overlay_crop * overlay_crop[:, :, c] +
            alpha_frame_crop * frame[y1:y2, x1:x2, c]
        ).astype(np.uint8)


# ----------------------------------------------
#  CARICAMENTO DELLE IMMAGINI DEI FILTRI
# ----------------------------------------------
# Metti qui i tuoi file PNG (con trasparenza).
# Ogni filtro è un dizionario con:
#   nome       -> etichetta visualizzata
#   img        -> array numpy dell'immagine caricata
#   placement  -> 'face' (centrato sul box faccia) o 'upper_body' (spalla sinistra)
#   scale      -> fattore di scala rispetto alla larghezza faccia / upper body
#   offset_y   -> spostamento verticale (frazione dell'altezza), positivo = in basso
#                 (per 'face' il centro è il centro del box faccia)
#   offset_x   -> spostamento orizzontale (frazione della larghezza)
#                 (per 'upper_body' si usa per spostare a sinistra/destra)
FILTRI_IMMAGINI = [
    {
        "nome": "Nessuno",
        "img": None,
        "placement": "face",
        "scale": 0.0,
        "offset_x": 0.0,
        "offset_y": 0.0
    },
    {
        "nome": "Cappello",
        "img": cv2.imread("filtri/cappello.png", cv2.IMREAD_UNCHANGED),
        "placement": "face",
        "scale": 1.3,
        "offset_x": 0.0,
        "offset_y": -0.65   # sopra la testa
    },
    {
        "nome": "Maschera",
        "img": cv2.imread("filtri/maschera.png", cv2.IMREAD_UNCHANGED),
        "placement": "face",
        "scale": 1.1,
        "offset_x": 0.0,
        "offset_y": 0.3
    },
    {
        "nome": "Occhiali",
        "img": cv2.imread("filtri/occhiali.png", cv2.IMREAD_UNCHANGED),
        "placement": "face",
        "scale": 0.9,
        "offset_x": 0.0,
        "offset_y": -0.05
    },
    {
        "nome": "Baffi",
        "img": cv2.imread("filtri/baffi.png", cv2.IMREAD_UNCHANGED),
        "placement": "face",
        "scale": 0.3,
        "offset_x": 0.0,
        "offset_y": 0.2   # sotto il centro (bocca)
    },
    {
        "nome": "Scudetto spalla",
        "img": cv2.imread("filtri/scudetto.png", cv2.IMREAD_UNCHANGED),
        "placement": "upper_body",
        "scale": 0.15,
        "offset_x": -0.3,   # sinistra rispetto al centro dell'upper body
        "offset_y": 0.1
    }
]

# Controlla che tutte le immagini siano state caricate correttamente
for filtro in FILTRI_IMMAGINI:
    if filtro["img"] is not None and filtro["img"].shape[2] != 4:
        print(f"[WARNING] L'immagine '{filtro['nome']}' non ha canale alpha!")


# ----------------------------------------------
#  APPLICAZIONE FILTRO IMMAGINE SUI VOLTI
# ----------------------------------------------
def applica_filtro_immagine(frame, facce, upper_list, idx_filtro):
    filtro = FILTRI_IMMAGINI[idx_filtro]
    if filtro["img"] is None:
        return

    if filtro["placement"] == "face":
        for (x, y, w, h) in facce:
            # Calcola il punto centrale del volto
            center_x = x + w // 2
            center_y = y + h // 2

            # Dimensioni desiderate dell'overlay
            target_w = int(w * filtro["scale"])
            if target_w <= 0:
                continue
            # Calcola altezza mantenendo il rapporto dell'immagine originale
            ratio = filtro["img"].shape[0] / filtro["img"].shape[1]
            target_h = int(target_w * ratio)

            # Posizione finale: centro volto + offset
            start_x = int(center_x - target_w // 2 + filtro["offset_x"] * w)
            start_y = int(center_y - target_h // 2 + filtro["offset_y"] * h)

            overlay_image_alpha(frame, filtro["img"], start_x, start_y, target_w, target_h)

    elif filtro["placement"] == "upper_body":
        for (ux, uy, uw, uh) in upper_list:
            # Spalla sinistra (destra nel frame speculare, ma noi usiamo semplicemente la regione upper body)
            center_x = ux + uw // 2
            center_y = uy + uh // 2
            target_w = int(uw * filtro["scale"])
            if target_w <= 0:
                continue
            ratio = filtro["img"].shape[0] / filtro["img"].shape[1]
            target_h = int(target_w * ratio)

            start_x = int(center_x - target_w // 2 + filtro["offset_x"] * uw)
            start_y = int(center_y - target_h // 2 + filtro["offset_y"] * uh)

            overlay_image_alpha(frame, filtro["img"], start_x, start_y, target_w, target_h)


# ----------------------------------------------
#  FILTRI COLORE (invariati)
# ----------------------------------------------
def colore_nessuno(frame):
    return frame

def bianco_e_nero(frame):
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    return cv2.cvtColor(grigio, cv2.COLOR_GRAY2BGR)

def seppia(frame):
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    norm = grigio.astype(np.float32) / 255.0
    s = np.zeros_like(frame, dtype=np.float32)
    s[:, :, 0] = norm * 112
    s[:, :, 1] = norm * 156
    s[:, :, 2] = norm * 200
    return np.clip(s, 0, 255).astype(np.uint8)

def negativo(frame):
    return cv2.bitwise_not(frame)

def calore(frame):
    lut_r = np.clip(np.arange(256) * 1.2, 0, 255).astype(np.uint8)
    lut_b = np.clip(np.arange(256) * 0.7, 0, 255).astype(np.uint8)
    b, g, r = cv2.split(frame)
    r = cv2.LUT(r, lut_r)
    b = cv2.LUT(b, lut_b)
    return cv2.merge([b, g, r])

def freddo(frame):
    lut_b = np.clip(np.arange(256) * 1.3, 0, 255).astype(np.uint8)
    lut_r = np.clip(np.arange(256) * 0.7, 0, 255).astype(np.uint8)
    b, g, r = cv2.split(frame)
    b = cv2.LUT(b, lut_b)
    r = cv2.LUT(r, lut_r)
    return cv2.merge([b, g, r])

def pixelato(frame, block=12):
    h, w = frame.shape[:2]
    small = cv2.resize(frame, (w // block, h // block), interpolation=cv2.INTER_NEAREST)
    return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)

def sketch(frame):
    grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(grigio, (21, 21), 0)
    edges = cv2.divide(grigio, blur, scale=256)
    return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)

def vintage(frame):
    sep = seppia(frame)
    h, w = sep.shape[:2]
    X, Y = np.meshgrid(np.linspace(-1, 1, w), np.linspace(-1, 1, h))
    vignette = 1 - np.clip(np.sqrt(X ** 2 + Y ** 2) * 0.8, 0, 1)
    vignette = vignette[:, :, np.newaxis]
    return (sep * vignette).astype(np.uint8)

FILTRI_COLORE = [
    ("Originale", colore_nessuno),
    ("B&N",       bianco_e_nero),
    ("Seppia",    seppia),
    ("Negativo",  negativo),
    ("Calore",    calore),
    ("Freddo",    freddo),
    ("Pixelato",  pixelato),
    ("Sketch",    sketch),
    ("Vintage",   vintage),
]


# ----------------------------------------------
#  FUNZIONE PRINCIPALE (con registrazione video)
# ----------------------------------------------
def riconoscimento_real_time():
    # Classificatori Haar
    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    upper_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_upperbody.xml")

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERRORE] Webcam non accessibile.")
        return

    # Stati dei filtri
    idx_facciale = 0   # indice in FILTRI_IMMAGINI
    idx_colore = 0     # indice in FILTRI_COLORE

    # Stati registrazione video
    recording = False
    video_writer = None

    print("=" * 55)
    print("  Filtri Webcam AR – Immagini & Video")
    print("  F = filtro successivo   C = colore successivo")
    print("  S = scatta foto         V = registra/fine video")
    print("  R = reset filtri        Q = esci")
    print("=" * 55)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)
        h_frame, w_frame = frame.shape[:2]

        # Converti in scala di grigi e equalizza
        grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        grigio_eq = cv2.equalizeHist(grigio)

        # Rilevamento volti e upper body
        facce = face_cascade.detectMultiScale(grigio_eq, scaleFactor=1.15,
                                              minNeighbors=5, minSize=(60, 60))
        upper_list = upper_cascade.detectMultiScale(grigio_eq, scaleFactor=1.2,
                                                    minNeighbors=3, minSize=(80, 80))

        # --- Applica filtro immagine (sovrapposto PRIMA del colore) ---
        nome_f = FILTRI_IMMAGINI[idx_facciale]["nome"]
        applica_filtro_immagine(frame, facce, upper_list, idx_facciale)

        # Riquadro sottile intorno ai volti (opzionale)
        for (x, y, w, h) in facce:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 200, 0), 1)

        # --- Applica filtro colore ---
        nome_c, fn_colore = FILTRI_COLORE[idx_colore]
        frame = fn_colore(frame)

        # --- Gestione registrazione video ---
        if recording and video_writer is not None:
            video_writer.write(frame)
            # Disegna un pallino rosso in alto a destra per indicare REC
            cv2.circle(frame, (w_frame - 30, 30), 10, (0, 0, 255), -1)

        # --- HUD (testo in sovrimpressione) ---
        hud_bg = frame.copy()
        cv2.rectangle(hud_bg, (0, 0), (w_frame, 90), (0, 0, 0), -1)
        cv2.addWeighted(hud_bg, 0.45, frame, 0.55, 0, frame)

        cv2.putText(frame, f"Filtro: {nome_f}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 200), 2, cv2.LINE_AA)
        cv2.putText(frame, f"Colore: {nome_c}",
                    (10, 52), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 255, 0), 2, cv2.LINE_AA)
        status = "  V=rec" if not recording else "  REC in corso..."
        cv2.putText(frame, f"Persone: {len(facce)} | F=filtro  C=colore  S=scatta  {status}  R=reset  Q=esci",
                    (10, 78), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (200, 200, 200), 1, cv2.LINE_AA)

        cv2.imshow("Filtri Webcam AR", frame)

        # --- Input da tastiera ---
        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord("f"):
            idx_facciale = (idx_facciale + 1) % len(FILTRI_IMMAGINI)
            print(f"Filtro facciale: {FILTRI_IMMAGINI[idx_facciale]['nome']}")

        elif key == ord("c"):
            idx_colore = (idx_colore + 1) % len(FILTRI_COLORE)
            print(f"Filtro colore: {FILTRI_COLORE[idx_colore][0]}")

        elif key == ord("r"):
            idx_facciale = 0
            idx_colore = 0
            print("Reset filtri.")

        elif key == ord("s"):
            # Scatta foto (senza HUD, ripetendo l'elaborazione)
            ret2, f2 = cap.read()
            if ret2:
                f2 = cv2.flip(f2, 1)
                g2 = cv2.cvtColor(f2, cv2.COLOR_BGR2GRAY)
                g2_eq = cv2.equalizeHist(g2)
                facce2 = face_cascade.detectMultiScale(g2_eq, scaleFactor=1.15, minNeighbors=5, minSize=(60,60))
                upper2 = upper_cascade.detectMultiScale(g2_eq, scaleFactor=1.2, minNeighbors=3, minSize=(80,80))
                applica_filtro_immagine(f2, facce2, upper2, idx_facciale)
                f2 = fn_colore(f2)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome = f"foto_{nome_f}_{nome_c}_{ts}.jpg"
                cv2.imwrite(nome, f2)
                print(f"Foto salvata: {nome}")

        elif key == ord("v"):
            # Toggle registrazione video
            if not recording:
                # Inizia registrazione
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                nome_video = f"video_{nome_f}_{nome_c}_{ts}.mp4"
                fourcc = cv2.VideoWriter_fourcc(*'mp4v')
                fps = cap.get(cv2.CAP_PROP_FPS)
                if fps <= 0:
                    fps = 20  # fallback
                video_writer = cv2.VideoWriter(nome_video, fourcc, fps,
                                               (w_frame, h_frame))
                recording = True
                print(f"Registrazione video iniziata: {nome_video}")
            else:
                # Ferma registrazione
                recording = False
                if video_writer:
                    video_writer.release()
                    video_writer = None
                print("Registrazione video fermata.")

    # Pulisci all'uscita
    if recording and video_writer:
        video_writer.release()
    cap.release()
    cv2.destroyAllWindows()


def main():
    print("=" * 55)
    print("   Filtri Webcam AR – Immagini PNG & Video")
    print("=" * 55)
    riconoscimento_real_time()


if __name__ == "__main__":
    main()