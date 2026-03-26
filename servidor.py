import socket
import RPi.GPIO as GPIO
import time 

# Configuração do LED
LED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, GPIO.LOW)

# Configuração do Servidor
HOST = '0.0.0.0' 
PORT = 65432    

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    # Permite reutilizar a porta imediatamente após fechar o servidor
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen()
    print(f"Servidor aguardando conexões em {HOST}:{PORT}...")

    try:
        while True:  # LOOP PRINCIPAL: Aceita novas conexões continuamente
            conn, addr = s.accept()
            with conn:
                print(f"Conectado por {addr}")
                while True: # LOOP DA CONEXÃO: Recebe dados do cliente atual
                    try:
                        data = conn.recv(1024).decode('utf-8')
                        if not data:
                            print(f"Cliente {addr} desconectou.")
                            GPIO.output(LED_PIN, GPIO.LOW)
                            break
                        elif data == "1":
                            GPIO.output(LED_PIN, GPIO.HIGH)
                            print("LED Ligado")
                            time.sleep(5)
                            GPIO.output(LED_PIN, GPIO.LOW)

#                        elif data == "0":
#                            GPIO.output(LED_PIN, GPIO.LOW)
#                            print("LED Desligado")
                            
                    except ConnectionResetError:
                        print(f"Conexão forçada a fechar por {addr}")
                        GPIO.output(LED_PIN, GPIO.LOW)
                        break
    except KeyboardInterrupt:
        print("\nServidor encerrado manualmente (Ctrl+C).")
    finally:
        GPIO.cleanup()
        print("GPIO limpo e recursos liberados.")
