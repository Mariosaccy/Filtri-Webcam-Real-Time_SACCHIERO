# main.py
# questo è il file principale: avvia la webcam, gestisce i tasti,
# chiama i filtri giusti e mostra il risultato a schermo
#
# opzionalmente può mandare il video a una webcam virtuale (come obs virtual camera)
# così puoi usare l'app su meet, zoom, ecc. — vedi il readme per come attivarlo

import cv2
import time
import sys
from datetime import datetime
from collections import deque
from pathlib import Path

from filters import FILTRI_COLORE
from effects import (
    rileva_facce,
    sfondo_sfocato,
    metti_cappello,
    metti_occhiali,
    metti_baffi,
    metti_maschera,
    ghost_effect,
    rilevamento_movimento,
)
from ui import disegna_hud, disegna_barra_filtri, disegna_etichette


# ─────────────────────────────────────────────
#  webcam virtuale (opzionale)
#  imposta WEBCAM_VIRTUALE = True per attivare
#  richiede: pip install pyvirtualcam
#  su linux richiede anche il modulo v4l2loopback (vedi readme)
# ─────────────────────────────────────────────

WEBCAM_VIRTUALE = False   # cambia in True per attivare la webcam virtuale

# prova a importare pyvirtualcam solo se l'utente vuole usarla
cam_virtuale = None
if WEBCAM_VIRTUALE:
    try:
        import pyvirtualcam
        print("[webcam virtuale] pyvirtualcam trovato, verrà attivata")
    except ImportError:
        print("[webcam virtuale] pyvirtualcam non installato — esegui: pip install pyvirtualcam")
        print("[webcam virtuale] continuo senza webcam virtuale")
        WEBCAM_VIRTUALE = False


# ─────────────────────────────────────────────
#  cartelle di output
# ─────────────────────────────────────────────

CARTELLA_FOTO  = Path("scatti");        CARTELLA_FOTO.mkdir(exist_ok=True)
CARTELLA_VIDEO = Path("registrazioni"); CARTELLA_VIDEO.mkdir(exist_ok=True)


# ─────────────────────────────────────────────
#  lista dei filtri facciali disponibili
#  ogni voce è (nome da mostrare, tipo di effetto)
#  i tipi con variante (cappello, maschera, baffi) si cambiano con i tasti 1-4
# ─────────────────────────────────────────────

FILTRI_FACCIALI = [
    "nessuno",          # nessun effetto sulla faccia
    "sfondo_sfocato",   # sfoca lo sfondo mantenendo nitida la faccia
    "cappello",         # cappello sopra la testa (varianti 1-4)
    "occhiali",         # occhiali all'altezza degli occhi
    "baffi",            # baffi sotto il naso (varianti 1-4)
    "maschera",         # maschera sull'intera faccia (varianti 1-4)
    "ghost",            # effetto scia del frame precedente
    "movimento",        # evidenzia in rosso le zone in movimento
]

# nomi "belli" da mostrare nella HUD
NOMI_FACCIALI = {
    "nessuno":        "nessuno",
    "sfondo_sfocato": "sfondo blur",
    "cappello":       "cappello",
    "occhiali":       "occhiali",
    "baffi":          "baffi",
    "maschera":       "maschera",
    "ghost":          "ghost",
    "movimento":      "movimento",
}


# ─────────────────────────────────────────────
#  funzione principale
# ─────────────────────────────────────────────

def main():
    # apri la webcam (0 = prima webcam disponibile)
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[errore] non riesco ad aprire la webcam")
        sys.exit(1)

    # leggi la risoluzione della webcam (serve per la registrazione video)
    w_cam = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h_cam = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # indici dei filtri attivi (si cambiano con i tasti C e F)
    idx_colore   = 0   # quale filtro colore è attivo
    idx_facciale = 0   # quale filtro facciale è attivo
    variante     = 0   # variante 0-3 per cappello/maschera/baffi (tasti 1-4)

    # stato della registrazione video
    recording    = False
    video_writer = None

    # mostrare i rettangoli di debug attorno alle facce?
    show_debug = False

    # il frame precedente serve per ghost e rilevamento movimento
    # importante: salviamo il frame GREZZO (senza filtri) altrimenti il confronto
    # cambia sempre anche quando non ci muoviamo, e tutto diventa rosso
    frame_precedente = None

    # soglia di sensibilità per il rilevamento movimento (0-255)
    # bassa = rileva anche piccoli movimenti, alta = solo movimenti grandi
    # si regola con i tasti + e - mentre il filtro movimento è attivo
    soglia_movimento = 25

    # coda degli ultimi 30 tempi di frame per calcolare gli fps reali
    tempi_frame = deque(maxlen=30)
    fps_display = 0.0

    # se l'utente vuole la webcam virtuale, la apriamo ora
    global cam_virtuale
    if WEBCAM_VIRTUALE:
        try:
            cam_virtuale = pyvirtualcam.Camera(width=w_cam, height=h_cam, fps=30)
            print(f"[webcam virtuale] attiva su: {cam_virtuale.device}")
            print("[webcam virtuale] selezionala in meet/zoom come 'virtual camera'")
        except Exception as e:
            print(f"[webcam virtuale] errore nell'apertura: {e}")
            cam_virtuale = None

    print("=" * 60)
    print("  filtri webcam ar — avviato")
    print("  c=colore  f=filtro  1-4=variante  s=foto  v=video  q=esci")
    print("=" * 60)

    while True:
        t_inizio = time.perf_counter()   # segna il tempo di inizio del frame

        # leggi un frame dalla webcam
        ret, frame = cap.read()
        if not ret:
            print("[errore] impossibile leggere il frame, esco")
            break

        # capovolgi orizzontalmente: così sembra uno specchio (più naturale per una webcam)
        frame = cv2.flip(frame, 1)

        # salva il frame grezzo qui, PRIMA di applicare qualsiasi filtro
        # serve per ghost e movimento: confrontare frame già filtrati darebbe risultati sbagliati
        # (es. l'hud che cambia ogni frame farebbe diventare tutto rosso anche da fermi)
        frame_grezzo = frame.copy()

        # rileva i volti nel frame corrente
        facce = rileva_facce(frame)

        # ── applica il filtro facciale attivo ───────────────────
        tipo = FILTRI_FACCIALI[idx_facciale]

        if tipo == "nessuno":
            pass   # non fare niente

        elif tipo == "sfondo_sfocato":
            frame = sfondo_sfocato(frame, facce)

        elif tipo == "cappello":
            frame = metti_cappello(frame, facce, variante)

        elif tipo == "occhiali":
            frame = metti_occhiali(frame, facce)

        elif tipo == "baffi":
            frame = metti_baffi(frame, facce, variante)

        elif tipo == "maschera":
            frame = metti_maschera(frame, facce, variante)

        elif tipo == "ghost":
            # usa il frame grezzo precedente, non quello filtrato
            frame = ghost_effect(frame, frame_precedente)

        elif tipo == "movimento":
            # usa il frame grezzo precedente e la soglia regolabile con + e -
            frame = rilevamento_movimento(frame, frame_precedente, soglia_movimento)

        # ── mostra i rettangoli di debug (solo se D è premuto) ──
        if show_debug:
            for (x, y, w, h) in facce:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)

        # ── applica il filtro colore attivo ──────────────────────
        nome_colore, fn_colore = FILTRI_COLORE[idx_colore]
        frame = fn_colore(frame)

        # ── scrivi nel video PRIMA di aggiungere hud e grafica ───
        # così il video registrato è pulito senza barre e testi sopra
        if recording and video_writer is not None:
            video_writer.write(frame)

        # ── manda il frame alla webcam virtuale (se attiva) ──────
        if cam_virtuale is not None:
            # pyvirtualcam vuole rgb, opencv usa bgr → convertiamo
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            cam_virtuale.send(frame_rgb)
            cam_virtuale.sleep_until_next_frame()

        # ── aggiungi le etichette sopra le facce ─────────────────
        disegna_etichette(frame, facce)

        # ── disegna la barra in alto con le info (hud) ───────────
        nome_facciale = NOMI_FACCIALI[tipo]
        # se il filtro ha varianti, mostra anche quale variante è attiva
        if tipo in ("cappello", "maschera", "baffi"):
            nome_facciale += f" {variante + 1}"
        disegna_hud(frame, nome_colore, nome_facciale, len(facce), fps_display, recording)

        # ── disegna la barra in basso con i filtri colore ────────
        nomi_colori = [n for n, _ in FILTRI_COLORE]
        disegna_barra_filtri(frame, nomi_colori, idx_colore)

        # ── mostra il frame finale nella finestra ─────────────────
        cv2.imshow("filtri webcam ar", frame)

        # salva il frame GREZZO (senza filtri e senza hud) come riferimento per il prossimo ciclo
        # usare frame_grezzo invece di frame evita che i testi e colori dell'hud
        # vengano interpretati come "movimento" nel frame successivo
        frame_precedente = frame_grezzo

        # ── calcolo fps reali ─────────────────────────────────────
        tempi_frame.append(time.perf_counter() - t_inizio)
        if len(tempi_frame) == tempi_frame.maxlen:
            fps_display = 1.0 / (sum(tempi_frame) / len(tempi_frame))

        # ── gestione tasti ────────────────────────────────────────
        tasto = cv2.waitKey(1) & 0xFF

        if tasto in (ord("q"), 27):   # q oppure esc per uscire
            break

        elif tasto == ord("c"):
            # passa al filtro colore successivo (ciclo circolare)
            idx_colore = (idx_colore + 1) % len(FILTRI_COLORE)
            print(f"  → colore: {FILTRI_COLORE[idx_colore][0]}")

        elif tasto == ord("f"):
            # passa al filtro facciale successivo (ciclo circolare)
            idx_facciale = (idx_facciale + 1) % len(FILTRI_FACCIALI)
            variante = 0   # reset variante quando cambi filtro
            print(f"  → filtro: {FILTRI_FACCIALI[idx_facciale]}")

        elif tasto in (ord("1"), ord("2"), ord("3"), ord("4")):
            # cambia variante per cappello, maschera e baffi
            variante = tasto - ord("1")   # "1" → 0, "2" → 1, "3" → 2, "4" → 3
            print(f"  → variante {variante + 1}")

        elif tasto == ord("r"):
            # reset: torna ai filtri di default
            idx_colore = 0
            idx_facciale = 0
            variante = 0
            soglia_movimento = 25
            print("  → reset filtri")

        elif tasto in (ord("+"), ord("=")) and tipo == "movimento":
            # aumenta la soglia → meno sensibile, rileva solo movimenti grandi
            soglia_movimento = min(soglia_movimento + 5, 100)
            print(f"  → soglia movimento: {soglia_movimento} (meno sensibile)")

        elif tasto == ord("-") and tipo == "movimento":
            # abbassa la soglia → più sensibile, rileva anche piccoli movimenti
            soglia_movimento = max(soglia_movimento - 5, 5)
            print(f"  → soglia movimento: {soglia_movimento} (più sensibile)")

        elif tasto == ord("d"):
            # mostra/nascondi i rettangoli attorno alle facce rilevate
            show_debug = not show_debug
            print(f"  → debug: {'on' if show_debug else 'off'}")

        elif tasto == ord("s"):
            # salva uno screenshot del frame attuale (già con tutti i filtri applicati)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            percorso  = CARTELLA_FOTO / f"foto_{nome_colore}_{nome_facciale}_{timestamp}.jpg"
            cv2.imwrite(str(percorso), frame)
            print(f"  → foto salvata: {percorso}")

        elif tasto == ord("v"):
            if not recording:
                # avvia la registrazione video
                timestamp  = datetime.now().strftime("%Y%m%d_%H%M%S")
                percorso   = CARTELLA_VIDEO / f"video_{nome_colore}_{nome_facciale}_{timestamp}.mp4"
                fps_rec    = fps_display if fps_display > 1 else 20.0
                # mp4v è il codec per file .mp4 — funziona su tutti i sistemi
                video_writer = cv2.VideoWriter(
                    str(percorso), cv2.VideoWriter_fourcc(*"mp4v"),
                    round(fps_rec), (w_cam, h_cam))
                recording = True
                print(f"  → registrazione avviata: {percorso}")
            else:
                # ferma la registrazione e chiude il file
                recording = False
                if video_writer:
                    video_writer.release()
                    video_writer = None
                print("  → registrazione fermata")

    # ── pulizia finale ────────────────────────────────────────────
    # rilascia tutte le risorse quando il programma finisce
    if recording and video_writer:
        video_writer.release()
    if cam_virtuale:
        cam_virtuale.close()
    cap.release()
    cv2.destroyAllWindows()
    print("programma terminato")


if __name__ == "__main__":
    main()
