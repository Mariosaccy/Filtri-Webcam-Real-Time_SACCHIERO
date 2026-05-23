# ui.py
# questo file si occupa di tutto quello che viene scritto o disegnato sullo schermo:
# la barra in alto con le informazioni (HUD), la barra in basso con i filtri,
# e le etichette sopra le facce rilevate

import cv2


# colori in formato BGR (opencv usa BGR invece di RGB)
VERDE   = (0, 255, 180)
GIALLO  = (0, 220, 255)
ROSSO   = (0, 0, 220)
BIANCO  = (240, 240, 240)
GRIGIO  = (150, 150, 150)
ARANCIO = (0, 180, 255)   # usato per evidenziare il filtro attivo


def disegna_hud(frame, nome_colore, nome_filtro, n_facce, fps, recording):
    # disegna la barra in alto con tutte le informazioni principali
    # HUD = heads-up display, le info sempre visibili in primo piano

    h, w = frame.shape[:2]

    # disegna un rettangolo nero semitrasparente come sfondo della barra
    sfondo = frame.copy()
    cv2.rectangle(sfondo, (0, 0), (w, 95), (0, 0, 0), -1)
    cv2.addWeighted(sfondo, 0.5, frame, 0.5, 0, frame)   # 50% nero, 50% frame

    # prima riga: filtro colore (sinistra) e filtro facciale (destra)
    cv2.putText(frame, f"colore: {nome_colore}",
                (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, VERDE, 2, cv2.LINE_AA)
    cv2.putText(frame, f"filtro: {nome_filtro}",
                (w // 2, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.65, GIALLO, 2, cv2.LINE_AA)

    # seconda riga: numero di facce rilevate (sinistra) e fps (destra)
    cv2.putText(frame, f"facce: {n_facce}",
                (10, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BIANCO, 1, cv2.LINE_AA)
    cv2.putText(frame, f"fps: {fps:.0f}",
                (w // 2, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, BIANCO, 1, cv2.LINE_AA)

    # terza riga: promemoria tasti
    cv2.putText(frame, "C=colore  F=filtro  1-4=variante  S=foto  V=video  D=debug  R=reset  Q=esci",
                (10, 83), cv2.FONT_HERSHEY_SIMPLEX, 0.36, GRIGIO, 1, cv2.LINE_AA)

    # pallino rosso + scritta REC nell'angolo in alto a destra, solo se si sta registrando
    if recording:
        cv2.circle(frame, (w - 22, 20), 9, ROSSO, -1)
        cv2.putText(frame, "REC", (w - 55, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, ROSSO, 1, cv2.LINE_AA)


def disegna_barra_filtri(frame, nomi, idx_attivo):
    # disegna in basso una riga con i nomi di tutti i filtri colore
    # quello attivo è evidenziato in arancio, gli altri sono in grigio

    h, w = frame.shape[:2]
    altezza_barra = 34
    y_inizio = h - altezza_barra

    # sfondo semitrasparente per la barra
    sfondo = frame.copy()
    cv2.rectangle(sfondo, (0, y_inizio), (w, h), (20, 20, 20), -1)
    cv2.addWeighted(sfondo, 0.6, frame, 0.4, 0, frame)

    n = len(nomi)
    larghezza_slot = w // n   # ogni filtro occupa una porzione uguale della barra

    for i, nome in enumerate(nomi):
        colore   = ARANCIO if i == idx_attivo else GRIGIO
        spessore = 2 if i == idx_attivo else 1

        # evidenzia lo slot del filtro attivo con un rettangolo scuro
        if i == idx_attivo:
            cv2.rectangle(frame, (i * larghezza_slot + 1, y_inizio + 1),
                          ((i + 1) * larghezza_slot - 1, h - 1), (50, 50, 50), -1)

        # calcola dove scrivere il nome per centrarlo dentro lo slot
        (tw, th), _ = cv2.getTextSize(nome, cv2.FONT_HERSHEY_SIMPLEX, 0.38, spessore)
        tx = i * larghezza_slot + (larghezza_slot - tw) // 2
        ty = y_inizio + (altezza_barra + th) // 2 - 2
        cv2.putText(frame, nome, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, colore, spessore, cv2.LINE_AA)


def disegna_etichette(frame, facce, etichetta="persona"):
    # scrive un'etichetta sopra ogni faccia rilevata
    # se ci sono più facce, aggiunge un numero (persona 1, persona 2, ecc.)
    for i, (x, y, w, h) in enumerate(facce):
        testo = f"{etichetta} {i + 1}" if len(facce) > 1 else etichetta
        cv2.putText(frame, testo, (x, max(y - 8, 15)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, VERDE, 2, cv2.LINE_AA)