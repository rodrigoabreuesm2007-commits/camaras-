import cv2
import easyocr
import re
from collections import Counter
import threading
import time
import numpy as np

# ==========================
# CONFIGURAÇÃO
# ==========================
RTSP_URL = "rtsp://admin:ESMesm123@128.128.1.113:554/stream1"
reader = easyocr.Reader(['en'], gpu=False)

CONF_MIN = 0.45
MAX_RECENT = 10
recent_plates = []
last_plate = ""

# ==========================
# FUNÇÕES
# ==========================
def limpar(texto):
    return re.sub(r'[^A-Z0-9]', '', texto.upper())

def validar_matricula(placa):
    return re.fullmatch(r"[A-Z0-9]{6,7}", placa) is not None

# ==========================
# THREAD DE OCR
# ==========================
class OCRThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.detected_boxes = []
        self.detected_texts = []

    def set_frame(self, frame):
        with self.lock:
            self.frame = frame.copy()

    def run(self):
        global last_plate, recent_plates

        while self.running:
            with self.lock:
                if self.frame is None:
                    time.sleep(0.01)
                    continue
                frame = self.frame.copy()
                self.frame = None

            h, w, _ = frame.shape

            # ==========================
            # ROI CORRETA (IGNORA DATA/HORA)
            # ==========================
            y_start = int(h * 0.45)   # ignora topo
            y_end   = int(h * 0.85)   # ignora fundo extremo
            x_start = int(w * 0.20)
            x_end   = int(w * 0.80)

            roi = frame[y_start:y_end, x_start:x_end]

            # ==========================
            # PRÉ-PROCESSAMENTO
            # ==========================
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (5,5), 0)
            _, thresh = cv2.threshold(
                gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            resultados = reader.readtext(thresh)

            placas_detectadas = []
            self.detected_boxes.clear()
            self.detected_texts.clear()

            for bbox, texto, conf in resultados:
                if conf < CONF_MIN:
                    continue

                placa = limpar(texto)
                if not validar_matricula(placa):
                    continue

                placas_detectadas.append(placa)
                recent_plates.append(placa)
                if len(recent_plates) > MAX_RECENT:
                    recent_plates.pop(0)

                # Ajustar bbox para frame inteiro
                (tl, tr, br, bl) = bbox
                tl = (int(tl[0] + x_start), int(tl[1] + y_start))
                br = (int(br[0] + x_start), int(br[1] + y_start))

                self.detected_boxes.append((tl, br))
                self.detected_texts.append(placa)

            if placas_detectadas:
                last_plate = Counter(recent_plates).most_common(1)[0][0]
                print(f"✅ MATRÍCULA: {last_plate}")

# ==========================
# CAPTURA RTSP
# ==========================
cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("❌ Não foi possível ligar ao RTSP")
    exit()

print("✅ Ligado à câmara")

ocr = OCRThread()
ocr.start()

while True:
    ret, frame = cap.read()
    if not ret:
        continue

    ocr.set_frame(frame)

    # Desenhar deteções
    #for (tl, br), texto in zip(ocr.detected_boxes, ocr.detected_texts):
      #  cv2.rectangle(frame, tl, br, (0,255,0), 2)
      #  cv2.putText(frame, texto, (tl[0], tl[1]-10),
      #              cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

    #if last_plate:
    #    cv2.putText(frame, last_plate, (50,50),
    #                cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0,255,0), 3)

    #cv2.imshow("Leitura de Matrículas", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

ocr.running = False
ocr.join()
cap.release()
cv2.destroyAllWindows()
