from machine import Pin, PWM
import time

# Constantes de calibración (AJUSTAR EXPERIMENTALMENTE)
VELOCIDAD_BASE = 40000  # Duty cycle base (0-65535)
#LOS VALORES AJUSTE MOTORES, SE CAMBIAN EN CASO DE QUE EL CARRO AL IR EN LINEA RECTA, SE VAYA EN DIAGONAL, ASI SE DISMINUYE EL CICLO UTIL PARA CADA MOTOR SEGUN ES NECESARIO
AJUSTE_MOTOR_A = 0.75    # Factor de corrección motor izquierdo
AJUSTE_MOTOR_B = 1.00   # Factor de corrección motor derecho 

# Configuración de pines (GP10 a GP15)
PIN_ENA = 10
PIN_IN1 = 11
PIN_IN2 = 12
PIN_ENB = 13
PIN_IN3 = 14
PIN_IN4 = 15

# Parámetros de movimiento (calibrar experimentalmente)

#Si el carro no alcanza la posicion deseada, disminuir cm/segundo. Si el carro se pasa de dicha posicion, aumentar este valor
#esta variable indica aproximadamente cual es la velocidad en cm/s del carro segun el ciclo util de la variable "VELOCIDAD BASE"
CM_POR_SEGUNDO = 25.0   # Velocidad lineal (cm/seg)
# Si el carro no alcanza el valor del giro seleccionado, disminuir el valor de esta variable, Si se pasa, aumentarlo
#Grados por segundo indica la velocidad angular del carro.
GRADOS_POR_SEGUNDO = 120.0  # Velocidad angular (grados/seg) 

class MotorController:
    def __init__(self):
        # Configuración motor izquierdo (A)
        self.ena = PWM(Pin(PIN_ENA))
        self.in1 = Pin(PIN_IN1, Pin.OUT)
        self.in2 = Pin(PIN_IN2, Pin.OUT)
        
        # Configuración motor derecho (B)
        self.enb = PWM(Pin(PIN_ENB))
        self.in3 = Pin(PIN_IN3, Pin.OUT)
        self.in4 = Pin(PIN_IN4, Pin.OUT)
        
        # Frecuencia PWM
        self.ena.freq(1000)
        self.enb.freq(1000)
        
        # Aplicar calibración inicial
        self.velocidad_a = int(VELOCIDAD_BASE * AJUSTE_MOTOR_A)
        self.velocidad_b = int(VELOCIDAD_BASE * AJUSTE_MOTOR_B)
        self.ena.duty_u16(self.velocidad_a)
        self.enb.duty_u16(self.velocidad_b)
    
    def _set_motors(self, dir_a, dir_b):
        """Control direccional independiente para cada motor"""
        # Motor A (izquierdo)
        self.in1.value(1 if dir_a == 'forward' else 0)
        self.in2.value(1 if dir_a == 'backward' else 0)
        
        # Motor B (derecho)
        self.in3.value(1 if dir_b == 'forward' else 0)
        self.in4.value(1 if dir_b == 'backward' else 0)
    
    def _ajustar_velocidad(self, ajuste_temp_a=1.0, ajuste_temp_b=1.0):
        """Ajuste temporal de velocidad para maniobras"""
        self.ena.duty_u16(int(self.velocidad_a * ajuste_temp_a))
        self.enb.duty_u16(int(self.velocidad_b * ajuste_temp_b))
    
    def mover_adelante(self, distancia_cm):
        t = distancia_cm / CM_POR_SEGUNDO
        self._ajustar_velocidad()
        self._set_motors('forward', 'forward')
        time.sleep(t)
        self.detener()
    
    def mover_atras(self, distancia_cm):
        t = distancia_cm / CM_POR_SEGUNDO
        self._ajustar_velocidad()
        self._set_motors('backward', 'backward')
        time.sleep(t)
        self.detener()
    
    def girar_izquierda(self, angulo_grados):
        t = angulo_grados / GRADOS_POR_SEGUNDO
        # Ligero ajuste para compensar diferencia motores en giro
        self._ajustar_velocidad(ajuste_temp_b=1.5)
        self._set_motors('backward', 'forward')
        time.sleep(t)
        self.detener()
        self._ajustar_velocidad()  # Restaurar ajustes
    
    def girar_derecha(self, angulo_grados):
        t = angulo_grados / GRADOS_POR_SEGUNDO
        # Ligero ajuste para compensar diferencia motores en giro
        #AJUSTE_TEMP, ES EL AJUSTE QUE SE HACE A LA VELOCIDAD DE LOS MOTORES, EN ESTE CASO PARA LAS MANIOBRAS, SE DISMINIYE O SE
        #AUMENTA EL CICLO ÚTIL SEGÚN SEA NECESARIO
        self._ajustar_velocidad(ajuste_temp_a=1.2)
        self._set_motors('forward', 'backward')
        time.sleep(t)
        self.detener()
        self._ajustar_velocidad()  # Restaurar ajustes
    
    def detener(self):
        self._set_motors('stop', 'stop')
    
    def curva_suave(self, direccion, radio_cm, distancia_cm):
        """Movimiento curvilíneo con radio controlado"""
        t = distancia_cm / CM_POR_SEGUNDO
        if direccion == 'izquierda':
            # Motor exterior (derecho) más rápido
            self._ajustar_velocidad(ajuste_temp_b=1.2) 
        else:  # derecha
            # Motor exterior (izquierdo) más rápido
            self._ajustar_velocidad(ajuste_temp_a=1.2)
        
        self._set_motors('forward', 'forward')
        time.sleep(t)
        self.detener()
        self._ajustar_velocidad()  # Restaurar ajustes