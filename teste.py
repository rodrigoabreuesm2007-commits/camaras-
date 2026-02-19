import cv2
import easyocr
import re
from collections import Counter
import threading
import time
import numpy as np


RTSP_URL = "rtsp://admin:ESMesm123@128.128.1.113:554/stream1"
reader = easyocr.Reader(['en'], gpu=True)

CONF_MIN = 0.45
MAX_RECENT = 10
recent_plates = []
last_plate = ""

cap = cv2.VideoCapture(RTSP_URL)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

if not cap.isOpened():
    print("❌ Não foi possível ligar à câmara")
    exit()

print("✅ Câmara ligada. Pressiona Q para sair.")

while True:
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print("⚠️ Erro ao receber frame...")
        continue

    # MOSTRAR IMAGEM
    cv2.imshow("Camera RTSP Live", frame)

    # Sair com Q
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
