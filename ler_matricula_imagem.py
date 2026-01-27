import cv2
import easyocr
import re
import os
from collections import Counter

# --- CONFIGURAÇÕES --- 
PASTA_FOTOS = r"C:\Users\Utilizador\rodrigo"  # pasta onde as fotos do Raspberry Pi são salvas
reader = easyocr.Reader(['en'], gpu=False)    # OCR em CPU
MAX_RECENT = 10
recent_plates = []

# Função para limpar texto para formato de matrícula
def limpar(texto):
    return re.sub(r'[^A-Z0-9]', '', texto.upper())

# Função para pegar a foto mais recente da pasta
def pegar_ultima_foto(pasta):
    arquivos = [os.path.join(pasta, f) for f in os.listdir(pasta) if f.lower().endswith(('.jpg', '.png', '.jpeg'))]
    if not arquivos:
        return None
    return max(arquivos, key=os.path.getmtime)

# --- PROGRAMA PRINCIPAL ---
ultima_foto = pegar_ultima_foto(PASTA_FOTOS)

if not ultima_foto:
    print("Nenhuma foto encontrada na pasta.")
    exit()

print(f"Abrindo imagem: {ultima_foto}")
img = cv2.imread(ultima_foto)
if img is None:
    print("Erro ao abrir a imagem.")
    exit()

gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
print("A executar OCR...")

results = reader.readtext(gray)

if not results:
    print("Nenhuma matrícula detectada.")
else:
    placas_detectadas = []

    for (bbox, text, prob) in results:
        if prob > 0.4 and len(text) >= 5:
            plate = limpar(text)
            placas_detectadas.append(plate)
            recent_plates.append(plate)
            if len(recent_plates) > MAX_RECENT:
                recent_plates.pop(0)

    if placas_detectadas:
        # pegar a matrícula mais frequente
        last_plate = Counter(recent_plates).most_common(1)[0][0]
        print(f"✅ MATRÍCULA DETECTADA: {last_plate}")

        # desenhar todas as placas detectadas na imagem
        for (bbox, text, prob) in results:
            x1, y1 = map(int, bbox[0])
            x2, y2 = map(int, bbox[2])
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, limpar(text), (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)

        cv2.imshow("Matrículas Detectadas", img)
        cv2.waitKey(0)
    else:
        print("Nenhuma matrícula válida detectada.")

cv2.destroyAllWindows()
