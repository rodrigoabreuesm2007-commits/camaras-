import cv2
import easyocr
import numpy as np
import re
import requests
import socket
import threading
import time
from collections import Counter
import ssl

# Desativar verificação SSL para a API se necessário
ssl._create_default_https_context = ssl._create_unverified_context

# ===================================================================================
# CONFIGURAÇÕES (API, Raspberry Pi e RTSP)
# ===================================================================================
PI_IP = '192.168.1.36'
PORT = 65432
API_VALIDA = "http://matriculas.alunos.esmonserrate.org/public/api/matriculas/valida/"
RTSP_URL = "rtsp://admin:ESMesm123@128.128.1.113:554/stream1"

# Configurações de processamento
CONF_MIN = 0.45
MAX_RECENT = 10
recent_plates = []
last_processed_plate = ""
cooldown_timer = 0  # Para evitar enviar a mesma matrícula várias vezes seguidas

# Inicialização do Reader (uma única vez para performance)
reader = easyocr.Reader(['en'], gpu=False)

# -----------------------------------------------------------------------------------
# FUNÇÃO DE CORREÇÃO (Original mantida)
# -----------------------------------------------------------------------------------
def corrigir_pelo_padrao(texto):
    texto = texto.upper().replace(" ", "").replace("-", "")
    if len(texto) != 6:
        return texto

    para_num = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8'}
    para_let = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B'} 

    padroes = ["LLNNLL", "NNNNLL", "LLNNNN", "NNLLNN"]
    melhor_texto = texto
    melhor_score = -1

    for padrao in padroes:
        score_atual = 0
        texto_tentativa = list(texto)
        for i in range(6):
            tipo_esperado = padrao[i]
            char = texto[i]
            if tipo_esperado == 'L':
                if char.isalpha(): 
                    score_atual += 1
                elif char in para_let:
                    texto_tentativa[i] = para_let[char]
                    score_atual += 0.5
            else:
                if char.isdigit():
                    score_atual += 1
                elif char in para_num:
                    texto_tentativa[i] = para_num[char]
                    score_atual += 0.5

        if score_atual > melhor_score:
            melhor_score = score_atual
            melhor_texto = "".join(texto_tentativa)

    return melhor_texto

# -----------------------------------------------------------------------------------
# FUNÇÃO DE DETEÇÃO ADAPTADA PARA STREAM
# -----------------------------------------------------------------------------------
def processar_frame_ocr(img):
    h, w = img.shape[:2]
    
    # ROI: Foco na zona onde as matrículas costumam passar (ajustável)
    y_start, y_end = int(h * 0.45), int(h * 0.85)
    x_start, x_end = int(w * 0.15), int(w * 0.85)
    crop = img[y_start:y_end, x_start:x_end]
    
    # Pré-processamento
    cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    cinza = cv2.resize(cinza, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)
    
    # OCR
    resultados = reader.readtext(cinza)

    for (bbox, texto, conf) in resultados:
        if conf < CONF_MIN:
            continue
            
        texto_limpo = re.sub(r'[^A-Z0-9]', '', texto.upper())
        
        if 5 <= len(texto_limpo) <= 7:
            if len(texto_limpo) == 7: 
                texto_limpo = texto_limpo[:6]
            
            final = corrigir_pelo_padrao(texto_limpo)
            return final, conf
    return None, 0

# -----------------------------------------------------------------------------------
# THREAD DE PROCESSAMENTO
# -----------------------------------------------------------------------------------
class OCRThread(threading.Thread):
    def __init__(self, socket_conn):
        super().__init__()
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.socket_conn = socket_conn

    def set_frame(self, frame):
        with self.lock:
            self.frame = frame.copy()

    def run(self):
        global recent_plates, cooldown_timer
        
        while self.running:
            frame_to_process = None
            with self.lock:
                if self.frame is not None:
                    frame_to_process = self.frame
                    self.frame = None

            if frame_to_process is not None:
                matricula, conf = processar_frame_ocr(frame_to_process)
                
                if matricula and len(matricula) >= 6:
                    print(f"Detectada: {matricula} (Conf: {conf:.2f})")
                    
                    # Estabilização: Adiciona à lista de recentes
                    recent_plates.append(matricula)
                    if len(recent_plates) > MAX_RECENT:
                        recent_plates.pop(0)
                    
                    # Só valida se a matrícula for a mais comum nos últimos frames
                    matricula_estavel = Counter(recent_plates).most_common(1)[0][0]
                    
                    # Cooldown de 5 segundos para não validar a mesma matrícula repetidamente
                    if time.time() > cooldown_timer:
                        self.validar_e_enviar(matricula_estavel)

            time.sleep(0.01)

    def validar_e_enviar(self, matricula):
        global cooldown_timer
        try:
            print(f"A validar na API: {matricula}")
            response = requests.get(API_VALIDA + matricula, timeout=3).json()
            total_elementos = response[0].get('numElements', 0)

            if total_elementos == 1:
                print(f"✅ Matrícula {matricula} VÁLIDA. Enviando LIGAR (1)...")
                self.socket_conn.sendall("1".encode('utf-8'))
                cooldown_timer = time.time() + 7 # Espera 7 segundos até aceitar nova leitura
            else:
                print(f"❌ Matrícula {matricula} não autorizada.")
                
        except Exception as e:
            print(f"Erro na validação/comunicação: {e}")

# -----------------------------------------------------------------------------------
# LOOP PRINCIPAL (CAPTURA RTSP)
# -----------------------------------------------------------------------------------
def main():
    # Tenta conectar ao Raspberry Pi
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            print(f"A ligar ao Raspberry Pi em {PI_IP}...")
            s.connect((PI_IP, PORT))
            print("✅ Ligado ao Raspberry Pi")

            # Inicia captura RTSP
            cap = cv2.VideoCapture(RTSP_URL)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Minimiza delay

            if not cap.isOpened():
                print("❌ Erro: Não foi possível abrir o stream RTSP.")
                return

            # Inicia a Thread de OCR passando o socket
            ocr_thread = OCRThread(s)
            ocr_thread.start()

            print("SISTEMA ATIVO - Pressione 'q' para sair")

            while True:
                ret, frame = cap.read()
                if not ret:
                    print("Falha na receção do frame RTSP...")
                    time.sleep(1)
                    continue

                # Envia o frame atual para a thread processar
                ocr_thread.set_frame(frame)

                # Visualização (Opcional - podes comentar para ganhar performance)
                cv2.imshow("Sistema de Matriculas RTSP", cv2.resize(frame, (800, 450)))

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            # Limpeza ao fechar
            ocr_thread.running = False
            ocr_thread.join()
            cap.release()
            cv2.destroyAllWindows()

    except Exception as e:
        print(f"Erro fatal: {e}")

if __name__ == "__main__":
    main()
