import machine
import network
import socket
import time
from ov7670_wrapper import *

# Pines para la cámara OV7670
data_pin_base = 0
pclk_pin_no = 8
mclk_pin_no = 9
href_pin_no = 12
vsync_pin_no = 13
reset_pin_no = 14
shutdown_pin_no = 15
sda_pin_no = 20
scl_pin_no = 21

# Configuración de red WiFi
SSID = "Familia_Barragan"
PASSWORD = "Barragan2025"
SERVER_IP = "192.168.20.166"
SERVER_PORT = 8080

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Conectando a WiFi...")
        wlan.connect(SSID, PASSWORD)
        while not wlan.isconnected():
            time.sleep(0.0001)
    print("Conectado:", wlan.ifconfig())

def init_camera():
    i2c = machine.I2C(0, freq=100000, scl=machine.Pin(scl_pin_no), sda=machine.Pin(sda_pin_no))
    cam = OV7670Wrapper(
        i2c_bus=i2c,
        mclk_pin_no=mclk_pin_no,
        pclk_pin_no=pclk_pin_no,
        data_pin_base=data_pin_base,
        vsync_pin_no=vsync_pin_no,
        href_pin_no=href_pin_no,
        reset_pin_no=reset_pin_no,
        shutdown_pin_no=shutdown_pin_no,
    )
    cam.wrapper_configure_yuv()
    cam.wrapper_configure_base()
    cam.wrapper_configure_size(OV7670_WRAPPER_SIZE_DIV2)  
    cam.wrapper_configure_test_pattern(OV7670_WRAPPER_TEST_PATTERN_NONE)
    return cam

def send_image(cam):
    width, height = 320, 240  # Cambiado de 160x120
    buf_size = width * height * 2  # YUV422
    buf = bytearray(buf_size)

    print("Capturando imagen...")
    cam.capture(buf)

    try:
        print("Conectando al servidor...")
        addr = socket.getaddrinfo(SERVER_IP, SERVER_PORT)[0][-1]
        s = socket.socket()
        s.connect(addr)
        print("Conectado. Enviando imagen...")

        start_time = time.ticks_ms()

        s.send(len(buf).to_bytes(4, 'big'))  # Tamaño en 4 bytes

        chunk_size = 1024
        for i in range(0, len(buf), chunk_size):
            s.send(buf[i:i+chunk_size])
            time.sleep(0.01)

        end_time = time.ticks_ms()
        duracion_total = time.ticks_diff(end_time, start_time) / 1000

        print(f"Imagen enviada correctamente en {duracion_total:.2f} segundos.")
        s.close()
    except Exception as e:
        print("Error al enviar:", e)

# === FLUJO PRINCIPAL ===
connect_wifi()
camera = init_camera()
time.sleep(1)

while True:
    send_image(camera)
    time.sleep(2)
