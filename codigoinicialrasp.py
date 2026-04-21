import cv2
import easyocr
import re

# Inicializar OCR
reader = easyocr.Reader(['en'], gpu=False)

# Abrir webcam (0 = default)
cap = cv2.VideoCapture(0)

def limpar(texto):
    return re.sub(r'[^A-Z0-9]', '', texto.upper())

def validar_matricula(placa):
    return re.fullmatch(r"[A-Z0-9]{6,7}", placa) is not None

while True:
    ret, frame = cap.read()
    if not ret:
        break

    # Converter para escala de cinza
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Aplicar blur
    gray = cv2.GaussianBlur(gray, (5,5), 0)

    # Threshold (preparar para OCR)
    _, thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    # OCR
    resultados = reader.readtext(thresh)

    for bbox, texto, conf in resultados:
        if conf < 0.4:
            continue

        placa = limpar(texto)

        if validar_matricula(placa):
            print("Matrícula:", placa)

            # desenhar na imagem
            (tl, tr, br, bl) = bbox
            tl = tuple(map(int, tl))
            br = tuple(map(int, br))

            cv2.rectangle(frame, tl, br, (0,255,0), 2)
            cv2.putText(frame, placa, (tl[0], tl[1]-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0,255,0), 2)

    cv2.imshow("Sistema OCR", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
