# carro_wifi_module.py

import machine
import time
import network
import socket
import json
from my_oled_lib import MyOLED
OLED_SDA_PIN = 2
OLED_SCL_PIN = 3
oled = MyOLED(sda_pin=OLED_SDA_PIN, scl_pin=OLED_SCL_PIN)

class CarroWiFi:
    def __init__(self, ssid, password, host, port, local_port, my_ip, uart_tx, uart_rx, uart_baud=9600):
        # UART
        self.uart = machine.UART(0, baudrate=uart_baud, tx=machine.Pin(uart_tx), rx=machine.Pin(uart_rx))

        # WiFi
        self.ssid = ssid
        self.password = password
        self.host = host
        self.port = port
        self.local_port = local_port
        self.my_ip = my_ip

        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.ifconfig((self.my_ip, '255.255.255.0', self.host, '8.8.8.8'))

        # Socket UDP
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(('0.0.0.0', self.local_port))
        self.s.setblocking(False)

        # Buffer UART
        self.buffer = b""
        self.last_send = 0
        self.send_interval = 5

        # Conectar al iniciar
        self.connect_wifi()

    def connect_wifi(self):
        self.wlan.active(True)
        if not self.wlan.isconnected():
            #print("Conectando a WiFi...")
            oled.write_text("Conectando a WiFi...", 0, 0)
            self.wlan.ifconfig((self.my_ip, '255.255.255.0', self.host, '8.8.8.8'))
            self.wlan.connect(self.ssid, self.password)
            timeout = 10
            start = time.time()
            while not self.wlan.isconnected():
                if time.time() - start > timeout:
                    print("❌ Timeout conectando WiFi")
                    break
                time.sleep(1)
        if self.wlan.isconnected():
            ip_info = self.wlan.ifconfig()
            # La IP es el primer elemento de la tupla
            ip_address = ip_info[0]
            print("✅ WiFi conectado:", self.wlan.ifconfig())
            oled.write_text("WiFi conectado!", 0, 0)
            oled.write_text("IP:", 0, 10)
            
            oled.write_text(ip_address, 25, 10) # Mostrar la IP en la pantalla
            
        else:
            print("❌ No conectado a WiFi")
            #oled.clear() # Limpiamos antes de escribir el nuevo mensaje
            oled.clear()
            oled.write_text("NO CONECTADO", 0, 20)
            
            self.ensure_wifi()

    def ensure_wifi(self):
        if not self.wlan.isconnected():
            self.wlan.ifconfig((self.my_ip, '255.255.255.0', self.host, '8.8.8.8'))
            print("WiFi desconectado, intentando reconectar...")
            oled.write_text("intentando reconectar...", 0, 40)
            self.connect_wifi()

    def read_internal_temp(self):
        sensor_temp = machine.ADC(4)
        conversion_factor = 3.3 / 65535
        reading = sensor_temp.read_u16() * conversion_factor
        temperature = 27 - (reading - 0.706) / 0.001721
        return round(temperature, 2)

    def send_json(self, data):
        try:
            self.ensure_wifi()
            if not self.wlan.isconnected():
                print("No conectado a WiFi, no se envía")
                return

            json_str = json.dumps(data)
            self.s.sendto(json_str.encode(), (self.host, self.port))
        except Exception as e:
            print("❌ Error al enviar al servidor:", e)

    def recibir_del_central(self):
        try:
            data, addr = self.s.recvfrom(8192)
            msg = data.decode('utf-8')
            oled.write_text(msg, 0, 20)
            try:
                json_data = json.loads(msg)
                ip_destino = json_data.get("ip_destino", "")
                if ip_destino == self.my_ip:
                    return msg
                    # Aquí puedes procesar el mensaje localmente si lo deseas
                    pass
                else:
                    self.uart.write(json.dumps(json_data) + "\n")
                return 
            except json.JSONDecodeError:
                return msg  # Retornar aunque sea malformado
        except OSError:
            return None


