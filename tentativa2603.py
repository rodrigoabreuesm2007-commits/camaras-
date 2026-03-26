import cv2
import easyocr
import numpy as np
import re
import requests
import socket


# Configurações da API e do Raspberry Pi
PI_IP = '192.168.1.36'
PORT = 65432
API_VALIDA = "http://matriculas.alunos.esmonserrate.org/public/api/matriculas/valida/"

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
    cinza = cv2.resize(cinza, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    reader = easyocr.Reader(['en'])
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


with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.settimeout(5) # Define um limite de 5 segundos para não travar
    s.connect((PI_IP, PORT))
   
    while True:
        #imagem ou cam
        mat = input("Matricula: ")
        CAMINHO_IMAGEM = r"C:\Users\utilizador\Desktop\grava\img_20260319_1456"+mat+".jpg"
        img = cv2.imread(CAMINHO_IMAGEM)




        # ... (funções de deteção e correção permanecem iguais)

        matricula = detetar_matricula_v3(img)
        print(f"A matricula final: {matricula}")


        if len(matricula) >=6:
            try:
                # Faz a chamada à API e converte para JSON
                response = requests.get(API_VALIDA + matricula).json()
                
                # Obtemos o número de elementos (0 ou 1)
                total_elementos = response[0].get('numElements', 0)
                print(f"Resposta da API: {total_elementos} elementos encontrados.")

                # Lógica de decisão
                if total_elementos == 1:           
                    print("Matrícula VÁLIDA. Enviando comando LIGAR (1)...")
                    s.sendall("1".encode('utf-8'))

            except Exception as e:
                print(f"Erro na comunicação: {e}")