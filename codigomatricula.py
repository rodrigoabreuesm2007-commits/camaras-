import ssl
ssl._create_default_https_context = ssl._create_unverified_context

import cv2
import easyocr
import re
from collections import Counter
import threading
import time

# ==========================
# CONFIGURAÇÃO
# ==========================
RTSP_URL = "rtsp://admin:ESMesm123@128.128.1.113:554/stream1"

reader = easyocr.Reader(['en'], gpu=False)

CONF_MIN = 0.45
MAX_RECENT = 6

recent_plates = []
last_plate = ""
last_detect_time = 0

OCR_INTERVAL = 4  # faz OCR a cada X frames


# ==========================
# FUNÇÕES
# ==========================
def limpar(texto):
    return re.sub(r'[^A-Z0-9]', '', texto.upper())


def validar_matricula(placa):
    return re.fullmatch(r"[A-Z0-9]{6,7}", placa) is not None


# ==========================
# THREAD OCR
# ==========================
class OCRThread(threading.Thread):

    def __init__(self):
        super().__init__()
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.detected_boxes = []
        self.detected_texts = []
        self.frame_count = 0

    def set_frame(self, frame):
        with self.lock:
            self.frame = frame.copy()

    def run(self):

        global last_plate, recent_plates, last_detect_time

        while self.running:

            with self.lock:

                if self.frame is None:
                    time.sleep(0.01)
                    continue

                frame = self.frame.copy()
                self.frame = None

            self.frame_count += 1

            # só faz OCR de alguns frames
            if self.frame_count % OCR_INTERVAL != 0:
                continue

            h, w, _ = frame.shape

            # ==========================
            # ROI (zona da matrícula)
            # ==========================
            y_start = int(h * 0.45)
            y_end   = int(h * 0.80)
            x_start = int(w * 0.25)
            x_end   = int(w * 0.75)

            roi = frame[y_start:y_end, x_start:x_end]

            # reduzir tamanho para OCR mais rápido
            roi = cv2.resize(roi, None, fx=0.7, fy=0.7)

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

            gray = cv2.GaussianBlur(gray,(3,3),0)

            _, thresh = cv2.threshold(
                gray,0,255,cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )

            resultados = reader.readtext(thresh)

            self.detected_boxes.clear()
            self.detected_texts.clear()

            for bbox, texto, conf in resultados:

                if conf < CONF_MIN:
                    continue

                placa = limpar(texto)

                if not validar_matricula(placa):
                    continue

                # evitar repetir matrícula sempre
                if placa == last_plate and time.time() - last_detect_time < 3:
                    continue

                recent_plates.append(placa)

                if len(recent_plates) > MAX_RECENT:
                    recent_plates.pop(0)

                last_plate = Counter(recent_plates).most_common(1)[0][0]
                last_detect_time = time.time()

                print("🚗 MATRÍCULA:", last_plate)

                (tl, tr, br, bl) = bbox

                tl = (int(tl[0] + x_start), int(tl[1] + y_start))
                br = (int(br[0] + x_start), int(br[1] + y_start))

                self.detected_boxes.append((tl, br))
                self.detected_texts.append(placa)


# ==========================
# CAPTURA RTSP
# ==========================
cap = cv2.VideoCapture(RTSP_URL, cv2.CAP_FFMPEG)

cap.set(cv2.CAP_PROP_BUFFERSIZE,1)

if not cap.isOpened():
    print("❌ Não foi possível ligar à câmara")
    exit()

print("✅ Câmara ligada")

ocr = OCRThread()
ocr.start()


# ==========================
# LOOP PRINCIPAL
# ==========================
while True:

    # limpar frames antigos (remove delay)
    for i in range(2):
        cap.grab()

    ret, frame = cap.read()

    if not ret:
        continue

    ocr.set_frame(frame)

    h, w, _ = frame.shape

    y_start = int(h * 0.45)
    y_end   = int(h * 0.80)
    x_start = int(w * 0.25)
    x_end   = int(w * 0.75)

    # desenhar zona de leitura
    cv2.rectangle(frame,(x_start,y_start),(x_end,y_end),(255,0,0),2)

    # desenhar deteções
    for (tl, br), texto in zip(ocr.detected_boxes, ocr.detected_texts):

        cv2.rectangle(frame, tl, br, (0,255,0), 2)

        cv2.putText(
            frame,
            texto,
            (tl[0], tl[1]-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0,255,0),
            2
        )

    if last_plate:

        cv2.putText(
            frame,
            last_plate,
            (40,60),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.4,
            (0,255,0),
            3
        )

    # reduzir tamanho da janela
    frame_small = cv2.resize(frame,(0,0),fx=0.35,fy=0.35)

    cv2.imshow("Leitor de Matriculas", frame_small)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break


ocr.running = False
ocr.join()

cap.release()
cv2.destroyAllWindows()
