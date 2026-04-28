import cv2
import easyocr
import numpy as np
import re
import time
import threading
#from collections import Counter
import requests
import socket
import xml.etree.ElementTree as ET



# Configurações da API e do Raspberry Pi
config = {}
reader = easyocr.Reader(['en'], gpu=False)
# -----------------------------------------------------------------------------------
# Carregamento das constantes a partir de ficherio configuracao.xml
# -----------------------------------------------------------------------------------
def carregar_constantes(ficheiro_xml):
    try:
        # Carrega e analisa o ficheiro
        tree = ET.parse(ficheiro_xml)
        root = tree.getroot()
        
        constantes = {}
        
        # Percorre todos os elementos chamados 'constante'
        for elem in root.findall('constante'):
            chave = elem.get('nome')
            valor = elem.text
            constantes[chave] = valor
        return constantes
    except FileNotFoundError:
        print("Erro: O ficheiro XML não foi encontrado.")
        return {}
    except ET.ParseError:
        print("Erro: Falha ao ler o formato do XML.")
        return {}




# -----------------------------------------------------------------------------------
# 
def corrigir_pelo_padrao(texto):
    # 1. Limpeza básica
    texto = texto.upper().replace(" ", "").replace("-", "")
    if len(texto) != 6:
        return texto

    # Dicionários de conversão
    para_num = {'O': '0', 'D': '0', 'Q': '0', 'I': '1', 'L': '1', 'Z': '2', 'S': '5', 'G': '6', 'B': '8'}
    para_let = {'0': 'O', '1': 'I', '2': 'Z', '5': 'S', '8': 'B'} #adicionar as mesmas combinações de para_num: '0': 'D', ...

    # Definição dos padrões: L = Letra, N = Número
    padroes = [
        "LLNNLL", # Novo (AA 00 AA)
        "NNNNLL", # Formato de máquinas/outros
        "LLNNNN", # Antigo (AA 00 00)
        "NNLLNN"  # Intermédio (00 AA 00)
    ]

    melhor_texto = texto
    melhor_score = -1

    for padrao in padroes:
        score_atual = 0
        texto_tentativa = list(texto)
        
        for i in range(6):
            tipo_esperado = padrao[i] # 'L' ou 'N'
            char = texto[i]

            if tipo_esperado == 'L':
                if char.isalpha(): 
                    score_atual += 1
                elif char in para_let:
                    texto_tentativa[i] = para_let[char]
                    score_atual += 0.5 # Meio ponto por ser uma troca comum
            else: # Esperado Número 'N'
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
# 
def detetar_matricula_v3(img):
    h, w = img.shape[:2]
    
    # Crop focado (ajustado para a tua imagem)
    crop = img[int(h*0.43):int(h*0.9), int(w*0.1):int(w*0.8)]
    
    # Pré-processamento simples
    cinza = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    
    # Opcional: Aumentar o tamanho ajuda muito se a matrícula estiver longe
    # VERIFICAR SE FAZ SENTIDO AUMENTAR
    ###cinza = cv2.resize(cinza, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    #reader = easyocr.Reader(['en'])
    # Lemos sem allowlist rígida primeiro para não bloquear a deteção inicial
    resultados = reader.readtext(cinza)

    for (bbox, texto, conf) in resultados:
        # Filtramos apenas o que parece ter o tamanho de uma matrícula
        texto_limpo = re.sub(r'[^A-Z0-9]', '', texto.upper())
        
        if 5 <= len(texto_limpo) <= 7: # Flexível para capturar erros de leitura
            # Se tiver 7, talvez leu um ponto ou borda, tentamos limpar
            if len(texto_limpo) == 7: 
                texto_limpo = texto_limpo[:6]
            
            final = corrigir_pelo_padrao(texto_limpo)
            print(f"Original: {texto} | Corrigida: {final} (Conf: {conf:.2f})")
            return final
    return ""

# -----------------------------------------------------------------------------------
# -----------------------------------------------------------------------------------
# THREAD 1: CAPTURA RTSP (Esvazia o buffer continuamente)
# -----------------------------------------------------------------------------------
class VideoCaptureThread:
    def __init__(self, src):
        self.cap = cv2.VideoCapture(src)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1) # Força buffer mínimo
        self.ret, self.frame = False, None
        self.running = True
        self.thread = threading.Thread(target=self.update, args=())
        self.thread.daemon = True
        self.thread.start()

    def update(self):
        while self.running:
            if self.cap.isOpened():
                self.ret, self.frame = self.cap.read()
            time.sleep(0.01)

    def get_frame(self):
        return self.ret, self.frame

    def stop(self):
        self.running = False
        self.cap.release()


# -----------------------------------------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------------------------------------
def main():
    global config 
    config = carregar_constantes('configuracao.xml')
    cam = VideoCaptureThread(config.get('RTSP_URL'))
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(5) # Define um limite de 5 segundos para não travar
        s.connect((config.get('PI_IP'), int(config.get('PORTA', '65432'))))
    
        ult_processamento = 0
        intervalo_ocr = 2
        while True:
            ret, img = cam.get_frame()
            if not ret or img is None:
                continue # Se a câmara falhar um frame, ignora e tenta o próximo

            preview = cv2.resize(img, (640, 360))
            cv2.imshow("LIVE RTSP (Q para sair)", preview)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            
            agora = time.time()
            if agora - ult_processamento > intervalo_ocr:
                ult_processamento = agora
                matricula = detetar_matricula_v3(img)
                print(f"A matricula final: {matricula}")
                if len(matricula) >=6:
                    try:
                        # Faz a chamada à API e converte para JSON
                        response = requests.get(config.get('API_VALIDA') + matricula).json()
                        
                        # Obtemos o número de elementos (0 ou 1)
                        total_elementos = response[0].get('numElements', 0)
                        print(f"Resposta da API: {total_elementos} elementos encontrados.")

                        # Lógica de decisão
                        if total_elementos == 1:           
                            print("Matrícula VÁLIDA. Enviando comando LIGAR (1)...")
                            s.sendall("1".encode('utf-8'))

                    except Exception as e:
                        print(f"Erro na comunicação: {e}")


if __name__ == "__main__":
    main()
