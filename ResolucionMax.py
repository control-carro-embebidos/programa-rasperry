from flask import Flask, send_file, Response
import threading
import socket
import numpy as np
import cv2
import os
import random
from cv2 import dnn_superres

app = Flask(__name__)
WIDTH, HEIGHT = 320, 240  # Cambiado de 160x120 a 320x240
YUV_FILE = "latest.yuv"
PNG_FILE = "latest.png"
EXPECTED_SIZE = WIDTH * HEIGHT * 2  # 320*240*2 = 153600 bytes

# Superresolución
sr = dnn_superres.DnnSuperResImpl_create()
sr.readModel("EDSR_x4.pb")
sr.setModel("edsr", 4)

def generar_datos_falsos():
    print("Generando imagen falsa por datos incompletos.")
    return bytes([random.randint(0, 255) for _ in range(EXPECTED_SIZE)])

def yuv422_to_png(yuv_data):
    try:
        yuv = np.frombuffer(yuv_data, dtype=np.uint8)
        if yuv.size != EXPECTED_SIZE:
            print("Advertencia: tamaño inesperado. Completando.")
            yuv_padded = bytearray(yuv_data)
            yuv_padded.extend([random.randint(0, 255) for _ in range(EXPECTED_SIZE - len(yuv_padded))])
            yuv = np.frombuffer(yuv_padded, dtype=np.uint8)

        yuv = yuv.reshape((HEIGHT, WIDTH, 2))
        bgr = np.zeros((HEIGHT, WIDTH, 3), dtype=np.uint8)

        for y in range(HEIGHT):
            for x in range(0, WIDTH, 2):
                y0 = yuv[y, x, 0]
                u  = yuv[y, x, 1]
                y1 = yuv[y, x+1, 0]
                v  = yuv[y, x+1, 1]

                def convert(y, u, v):
                    c = y - 16
                    d = u - 128
                    e = v - 128
                    r = np.clip((298 * c + 409 * e + 128) >> 8, 0, 255)
                    g = np.clip((298 * c - 100 * d - 208 * e + 128) >> 8, 0, 255)
                    b = np.clip((298 * c + 516 * d + 128) >> 8, 0, 255)
                    return b, g, r

                bgr[y, x] = convert(y0, u, v)
                bgr[y, x+1] = convert(y1, u, v)

        enhanced = sr.upsample(bgr)
        cv2.imwrite(PNG_FILE, enhanced)
        print("Imagen mejorada y guardada.")
    except Exception as e:
        print(f"Error en conversión YUV->PNG: {e}")

def tcp_receiver():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("0.0.0.0", 8080))
        s.listen(1)
        print("Esperando imagen de la Pico W en el puerto 8080...")
        while True:
            conn, addr = s.accept()
            with conn:
                print(f"Conexión desde {addr}")
                try:
                    size_bytes = conn.recv(4)
                    if not size_bytes or len(size_bytes) < 4:
                        print("No se recibió tamaño.")
                        conn.sendall(b"NACK")
                        continue

                    size = int.from_bytes(size_bytes, 'big')
                    data = b''
                    while len(data) < size:
                        packet = conn.recv(min(1024, size - len(data)))
                        if not packet:
                            break
                        data += packet

                    if len(data) != size:
                        print(f"Incompleto ({len(data)} / {size}).")
                        conn.sendall(b"NACK")
                        continue
                    else:
                        conn.sendall(b"ACK")

                    yuv_data = data
                    with open(YUV_FILE, "wb") as f:
                        f.write(yuv_data)
                    print(f"Imagen recibida correctamente.")
                    yuv422_to_png(yuv_data)

                except Exception as e:
                    print(f"Error en recepción: {e}")
                    try:
                        conn.sendall(b"NACK")
                    except:
                        pass

@app.route('/')
def index():
    return '''
    <html>
        <head><title>Imagen desde Pico W</title></head>
        <body>
            <h1>Última imagen recibida</h1>
            <img src="/image" width="1280" height="960"/>
        </body>
    </html>
    '''

@app.route('/image')
def image():
    if os.path.exists(PNG_FILE):
        return send_file(PNG_FILE, mimetype="image/png")
    else:
        return Response("No se ha recibido ninguna imagen todavía.", status=404)

if __name__ == '__main__':
    threading.Thread(target=tcp_receiver, daemon=True).start()
    app.run(host="0.0.0.0", port=5000)

