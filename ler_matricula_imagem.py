import cv2
import easyocr
import numpy as np
import requests
import re
from collections import Counter

# ================= CONFIG =================

IMAGE_URL = "http://10.1.31.97:8000/ultima.jpg"
CONF_MIN = 0.4
MAX_RECENT = 10

reader = easyocr.Reader(['en'], gpu=False)
historico = []

# ================= FUNÇÕES =================

def limpar(texto):
    return re.sub(r'[^A-Z0-9]', '', texto.upper())

def obter_imagem(url):
    r = requests.get(url, timeout=5)
    if r.status_code != 200:
        return None
    img_array = np.frombuffer(r.content, np.uint8)
    return cv2.imdecode(img_array, cv2.IMREAD_COLOR)

# ================= MAIN =================

print("🔄 A obter imagem do Raspberry Pi...")
img = obter_imagem(IMAGE_URL)

if img is None:
    print("❌ ERRO: não foi possível obter a imagem")
    exit()

cv2.imshow("Imagem recebida", img)
cv2.waitKey(500)

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("🔍 A executar OCR...")

results = reader.readtext(gray)

placas = []

for (bbox, text, prob) in results:
    if prob >= CONF_MIN:
        plate = limpar(text)
        if 6 <= len(plate) <= 8:
            placas.append(plate)
            historico.append(plate)
            if len(historico) > MAX_RECENT:
                historico.pop(0)

            x1, y1 = map(int, bbox[0])
            x2, y2 = map(int, bbox[2])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, plate, (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

if placas:
    final = Counter(historico).most_common(1)[0][0]
    print(f"✅ MATRÍCULA DETECTADA: {final}")
else:
    print("⚠️ Nenhuma matrícula reconhecida")

cv2.imshow("Resultado OCR", img)
cv2.waitKey(0)
cv2.destroyAllWindows()
