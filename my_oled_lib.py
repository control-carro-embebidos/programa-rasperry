# my_oled_lib.py

from machine import Pin, I2C
import ssd1306

# Ajusta el ancho y alto a las dimensiones de tu pantalla OLED
OLED_WIDTH = 128
OLED_HEIGHT = 64 # O 32, si tu pantalla es de 128x32

class MyOLED:
    def __init__(self, sda_pin=2, scl_pin=3, width=OLED_WIDTH, height=OLED_HEIGHT):
        """
        Inicializa la pantalla OLED.
        sda_pin: Pin GPIO para SDA (Datos I2C). Por defecto GP2.
        scl_pin: Pin GPIO para SCL (Reloj I2C). Por defecto GP3.
        width: Ancho de la pantalla en píxeles.
        height: Alto de la pantalla en píxeles.
        """
        # *** CAMBIO CLAVE AQUÍ: Usamos I2C(1, ...) para los pines GP2 y GP3 ***
        self.i2c = I2C(1, sda=Pin(sda_pin), scl=Pin(scl_pin), freq=400000)
        # Inicializa el controlador SSD1306 con el bus I2C
        self.oled = ssd1306.SSD1306_I2C(width, height, self.i2c, addr=0x3C)
        self.width = width
        self.height = height
        print(f"OLED inicializada en I2C bus 1 (SDA: GP{sda_pin}, SCL: GP{scl_pin})")


    def clear(self):
        """Limpia toda la pantalla (la pone en negro)."""
        self.oled.fill(0) # 0 para negro
        self.oled.show()

    def write_text(self, text, x=0, y=0, color=1):
        """
        Escribe texto en la pantalla.
        text: La cadena de texto a escribir.
        x: Coordenada X de inicio (columna).
        y: Coordenada Y de inicio (fila).
        color: 1 para blanco, 0 para negro (útil para "borrar" texto).
        """
        self.oled.text(text, x, y, color)
        self.oled.show()

    def draw_pixel(self, x, y, color=1):
        """
        Dibuja un píxel individual en la pantalla.
        x: Coordenada X del píxel.
        y: Coordenada Y del píxel.
        color: 1 para blanco, 0 para negro.
        """
        self.oled.pixel(x, y, color)
        self.oled.show()

    def draw_line(self, x1, y1, x2, y2, color=1):
        """
        Dibuja una línea entre dos puntos.
        (x1, y1): Coordenadas del punto inicial.
        (x2, y2): Coordenadas del punto final.
        color: 1 para blanco, 0 para negro.
        """
        self.oled.line(x1, y1, x2, y2, color)
        self.oled.show()

    def draw_rectangle(self, x, y, width, height, color=1, fill=False):
        """
        Dibuja un rectángulo.
        x, y: Coordenadas de la esquina superior izquierda.
        width, height: Ancho y alto del rectángulo.
        color: 1 para blanco, 0 para negro.
        fill: True para un rectángulo relleno, False para un contorno.
        """
        if fill:
            self.oled.fill_rect(x, y, width, height, color)
        else:
            self.oled.rect(x, y, width, height, color)
        self.oled.show()

    def display_on(self):
        """Enciende la pantalla (sale del modo de ahorro de energía)."""
        self.oled.poweron()

    def display_off(self):
        """Apaga la pantalla (entra en modo de ahorro de energía)."""
        self.oled.poweroff()

    def contrast(self, level):
        """
        Ajusta el contraste de la pantalla.
        level: Nivel de contraste (0-255).
        """
        self.oled.contrast(level)
        self.oled.show()