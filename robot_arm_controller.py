from machine import Pin, PWM
import time

class BrazoRobotico:
    def __init__(self):
        self.base = PWM(Pin(18))
        self.hombro = PWM(Pin(17))
        self.codo = PWM(Pin(16))
        
        for servo in [self.base, self.hombro, self.codo]:
            servo.freq(50)
        
        self.calibracion = {
            'base': (-9717, 1532862),
            'hombro': (-11111, 1550000),
            'codo': (-11668, 1550000)
        }
        
        self.angulos_actuales = [0, 90, 90]
        self.angulos_actuales[2] = self._corregir_codo(self.angulos_actuales[1], self.angulos_actuales[2])
        self.mover_brazo(self.angulos_actuales, tiempo_segundos=1.0)
    
    def _corregir_codo(self, angulo_hombro, angulo_codo):
        if angulo_hombro == 90:
            return -angulo_codo + 90
        elif 0 < angulo_hombro < 90:
            return -0.6429 * angulo_codo + 102.86
        return angulo_codo
    
    def _angulo_a_duty_ns(self, servo_nombre, angulo):
        m, b = self.calibracion[servo_nombre]
        return int(m * angulo + b)
    
    def _mover_suavemente(self, servo_pwm, servo_nombre, angulo_actual, angulo_final, tiempo_segundos):
        pasos = 1000
        delay = tiempo_segundos / pasos
        delta = (angulo_final - angulo_actual) / pasos
        
        for i in range(pasos + 1):
            angulo_interpolado = angulo_actual + delta * i
            duty = self._angulo_a_duty_ns(servo_nombre, angulo_interpolado)
            servo_pwm.duty_ns(duty)
            time.sleep(delay)
    
    def mover_brazo(self, angulos, tiempo_segundos=1.0):
        if angulos is None:
            return
        
        if len(angulos) != 3:
            raise ValueError("Se requieren exactamente 3 ángulos")
        
        angulo_base, angulo_hombro, angulo_codo = angulos
        
        angulo_codo_corregido = self._corregir_codo(angulo_hombro, angulo_codo)
        
        self._mover_suavemente(self.base, 'base', self.angulos_actuales[0], angulo_base, tiempo_segundos)
        self._mover_suavemente(self.hombro, 'hombro', self.angulos_actuales[1], angulo_hombro, tiempo_segundos)
        self._mover_suavemente(self.codo, 'codo', self.angulos_actuales[2], angulo_codo_corregido, tiempo_segundos)
        
        self.angulos_actuales = [angulo_base, angulo_hombro, angulo_codo_corregido]
    
    def apagar(self):
        for servo in [self.base, self.hombro, self.codo]:
            try:
                servo.deinit()
            except Exception as e:
                print(f"Error al apagar servo: {e}")
