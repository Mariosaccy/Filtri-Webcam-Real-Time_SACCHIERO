import cv2
import numpy as np
from datetime import datetime

def riconoscimento_real_time():
    # 1. Carica il classificatore per i volti
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )

    # 2. Avvia la webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[ERRORE] Webcam non accessibile.")
        return

    print("Rilevamento avviato. Premi 'q' per uscire.")

    while True:
        # Cattura frame per frame
        ret, frame = cap.read()
        if not ret:
            break

        # Specchia il frame per renderlo naturale (come uno specchio)
        frame = cv2.flip(frame, 1)

        # mostra istruzione per scattare foto
        cv2.putText(frame, "S = scatta  |  Q = esci", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
        # cv2.imshow("Cattura Foto", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nome_file = f"foto_{timestamp}.jpg"
            # ricattura il frame pulito (senza il testo sopra) da cap
            ret2, frame_pulito = cap.read()
            frame_pulito = cv2.flip(frame_pulito, 1)
            if ret2:
                cv2.imwrite(nome_file, frame_pulito)
                print(f"Foto salvata: {nome_file}")

        # 3. Trasforma in grigio per ottimizzare le prestazioni
        grigio = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # 4. Rileva i volti nel frame attuale
        facce = face_cascade.detectMultiScale(
            grigio,
            scaleFactor=1.2, # Ridimensionamento dell'immagine (più alto = più veloce)
            minNeighbors=5,   # Quanti rettangoli vicini devono esserci per confermare un volto
            minSize=(30, 30) # Dimensione minima del volto cercato
        )

        # 5. Disegna un rettangolo intorno a ogni volto rilevato
        for (x, y, w, h) in facce:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
            cv2.putText(frame, "Persona Rilevata", (x, y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        # Mostra il numero di persone in alto a sinistra
        cv2.putText(frame, f"Persone: {len(facce)}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Visualizza il risultato
        cv2.imshow('Riconoscimento Real-Time', frame)

        # Esci se premi 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

def main():


    print(" Filtri Webcam in Real Time ")
    print("=" * 55)

    riconoscimento_real_time()




if __name__ == "__main__":
    main()