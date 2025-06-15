import json
import time
from motor_controller import MotorController
from robot_arm_controller import BrazoRobotico
from carro_wifi_module import CarroWiFi
from my_oled_lib import MyOLED

# --- Configuración de Pines I2C para la OLED ---
# Define los pines SDA y SCL que vas a usar.
# Para GP2 y GP3, puedes dejarlo así:
OLED_SDA_PIN = 2
OLED_SCL_PIN = 3

# Si quisieras usar otros pines, por ejemplo, GP4 y GP5, lo harías así:
# OLED_SDA_PIN = 4
# OLED_SCL_PIN = 5
# -----------------------------------------------

# Inicializa la pantalla OLED pasando los pines que has definido.
oled = MyOLED(sda_pin=OLED_SDA_PIN, scl_pin=OLED_SCL_PIN)
# -----------------Crear una instancia de la clase WIFI
carro = CarroWiFi(
    ssid="CentralAPT",
    password="12345678",
    host="192.168.0.100",
    port=1234,
    local_port=5555,
    my_ip="192.168.0.123",
    uart_tx=0,
    uart_rx=1
)
#-----------------
# Función para parsear comandos JSON
def parsear_comando(datos_json):
    try:
        data = json.loads(datos_json)

        # Buscar la clave principal 'Carro_X'
        if not data or not any(key.startswith("Carro_") for key in data):
            raise ValueError("El JSON no contiene una clave 'Carro_X' principal.")

        # Obtener la clave del carro (asumimos que solo hay una, por ejemplo "Carro_1")
        carro_key = next(key for key in data if key.startswith("Carro_"))
        pasos = data[carro_key]

        if not pasos:
            raise ValueError("La sección '{}' no contiene ningún paso.".format(carro_key))

        # --- CORRECCIÓN: Ordenar pasos numéricamente ---
        # Extraer y ordenar las claves de los pasos por su número
        claves_pasos = [k for k in pasos.keys() if k.startswith("Paso_")]
        claves_ordenadas = sorted(claves_pasos, key=lambda x: int(x.split('_')[1]))
        
        secuencia_comandos = []

        # Iterar a través de cada paso EN ORDEN
        for paso_nombre in claves_ordenadas:
            paso_data = pasos[paso_nombre]
            if "Movimiento" not in paso_data:
                raise ValueError("Falta la sección 'Movimiento' en el {}".format(paso_nombre))

            mov = paso_data["Movimiento"]

            if "distancia_mm" not in mov or "velocidad_mm_s" not in mov or "radio_mm" not in mov:
                raise ValueError("Faltan los campos 'distancia_mm', 'velocidad_mm_s' o 'radio_mm' en la sección 'Movimiento' de {}".format(paso_nombre))

            comando_actual = {"tipo": None}
            comando_actual["distancia_original"] = mov["distancia_mm"]
            comando_actual["distancia_abs"] = abs(mov["distancia_mm"])
            comando_actual["velocidad"] = mov["velocidad_mm_s"]

            comando_actual["direccion_avance"] = "adelante" if mov["distancia_mm"] >= 0 else "atras"

            if str(mov["radio_mm"]).lower() == "inf":
                comando_actual["tipo"] = "recto"
                comando_actual["angulo"] = 0
                comando_actual["direccion_giro"] = None
                comando_actual["vel_giro"] = 0
            elif isinstance(mov["radio_mm"], (int, float)):
                comando_actual["tipo"] = "giro_y_recto"
                comando_actual["angulo"] = abs(mov["radio_mm"])

                if mov["radio_mm"] < 0:
                    comando_actual["direccion_giro"] = "izquierda"
                else:
                    comando_actual["direccion_giro"] = "derecha"
                
                comando_actual["vel_giro"] = mov.get("vel_grados_s", 60)
            else:
                raise ValueError("El valor de 'radio_mm' en {} debe ser 'inf' o un número (grados de giro).".format(paso_nombre))

            # Manejar brazo robótico si está presente en el paso actual
            if "Brazo" in paso_data:
                brazo = paso_data["Brazo"]
                for campo in ["angulo0_grados", "angulo1_grados", "angulo2_grados"]:
                    if campo not in brazo:
                        raise ValueError("Falta el campo requerido: {} en Brazo para {}".format(campo, paso_nombre))

                angulos = [
                    brazo["angulo0_grados"],
                    brazo["angulo1_grados"],
                    brazo["angulo2_grados"]
                ]

                if not all(isinstance(a, (int, float)) for a in angulos):
                    raise TypeError("Los ángulos del brazo deben ser numéricos para {}".format(paso_nombre))

                comando_actual["angulos"] = angulos
                # Obtener t_ser si está presente, de lo contrario usar un valor por defecto (ej. 1.0 segundos)
                comando_actual["t_ser"] = brazo.get("t_ser", 1.0)  
            else:
                comando_actual["angulos"] = None
                comando_actual["t_ser"] = None # No hay movimiento de brazo, no hay tiempo de servo

            secuencia_comandos.append(comando_actual)

        return secuencia_comandos

    except Exception as e:
        print("ERROR en el parseo:", e)
        return None


## Programa Principal Actualizado: Escucha Continua de Comandos

if __name__ == "__main__":
    # Inicializar hardware
    controlador_rover = MotorController()
    brazo_robotico = BrazoRobotico()
    
    while True: # Bucle infinito para escuchar continuamente
        print("\nEsperando un nuevo comando...")
        msg = carro.recibir_del_central()
        
        if msg:
            datos_json_desde_archivo = msg
            print(f"Comando recibido: {datos_json_desde_archivo}")
            secuencia_pasos = parsear_comando(datos_json_desde_archivo)

            if secuencia_pasos is None:
                print("Comando inválido. Esperando el siguiente mensaje...")
                continue # Vuelve al inicio del bucle para esperar otro mensaje

            try:
                # Iterar sobre cada paso en la secuencia
                for i, comando_paso in enumerate(secuencia_pasos, start=1):
                    print("\n--- Ejecutando Paso {} ---".format(i))

                    # Mover brazo primero si está especificado para este paso
                    if comando_paso["angulos"] is not None:
                        print(f"Posicionando brazo en ángulos: {comando_paso['angulos']}")
                        tiempo_servo = comando_paso["t_ser"] if comando_paso["t_ser"] is not None else 1.0
                        print(f"Tiempo de movimiento del servo: {tiempo_servo}s")
                        brazo_robotico.mover_brazo(comando_paso["angulos"], tiempo_servo)
                        time.sleep(tiempo_servo) # Esperar el tiempo especificado para el movimiento del brazo

                    # Ejecutar movimiento según el tipo para este paso
                    if comando_paso["tipo"] == "recto":
                        if comando_paso["distancia_abs"] > 0:
                            if comando_paso["direccion_avance"] == "adelante":
                                print("Avanzando: {}mm a {}mm/s".format(comando_paso['distancia_abs'], comando_paso['velocidad']))
                                controlador_rover.mover_adelante(comando_paso["distancia_abs"])
                            else: # direccion_avance == "atras"
                                print("Retrocediendo: {}mm a {}mm/s".format(comando_paso['distancia_abs'], comando_paso['velocidad']))
                                controlador_rover.mover_atras(comando_paso["distancia_abs"])

                            tiempo_avance = comando_paso["distancia_abs"] / comando_paso["velocidad"] if comando_paso["velocidad"] > 0 else 0
                            print("Tiempo de movimiento estimado: {:.1f}s".format(tiempo_avance))
                            time.sleep(tiempo_avance)
                        else:
                            print("Paso {}: Movimiento recto (distancia_mm=0), no se realiza avance.".format(i))

                    elif comando_paso["tipo"] == "giro_y_recto":
                        if comando_paso["angulo"] > 0:
                            print("Paso {}: Giro: {}° a {}°/s - Dirección: {}".format(i, comando_paso['angulo'], comando_paso['vel_giro'], comando_paso['direccion_giro']))

                            if comando_paso["direccion_giro"] == "derecha":
                                controlador_rover.girar_derecha(comando_paso["angulo"])
                            else: # direccion_giro es "izquierda"
                                controlador_rover.girar_izquierda(comando_paso["angulo"])

                            tiempo_giro = comando_paso["angulo"] / comando_paso["vel_giro"] if comando_paso["vel_giro"] > 0 else 0
                            print("Tiempo de giro estimado: {:.1f}s".format(tiempo_giro))
                            time.sleep(tiempo_giro)
                        else:
                            print("Paso {}: Giro (radio_mm=0), no se realiza giro.".format(i))

                        if comando_paso["distancia_abs"] > 0:
                            if comando_paso["direccion_avance"] == "adelante":
                                print("Paso {}: Después del giro, avanzando: {}mm a {}mm/s".format(i, comando_paso['distancia_abs'], comando_paso['velocidad']))
                                controlador_rover.mover_adelante(comando_paso["distancia_abs"])
                            else: # direccion_avance == "atras"
                                print("Paso {}: Después del giro, retrocediendo: {}mm a {}mm/s".format(i, comando_paso['distancia_abs'], comando_paso['velocidad']))
                                controlador_rover.mover_atras(comando_paso["distancia_abs"])

                            tiempo_avance = comando_paso["distancia_abs"] / comando_paso["velocidad"] if comando_paso["velocidad"] > 0 else 0
                            print("Tiempo de movimiento estimado: {:.1f}s".format(tiempo_avance))
                            time.sleep(tiempo_avance)
                        else:
                            print("Paso {}: Movimiento después del giro (distancia_mm=0), no se realiza avance.".format(i))
                    
                    # Asegurarse de que el rover se detenga al final de cada paso
                    controlador_rover.detener()

                print("\n¡Todos los pasos completados con éxito!")

            except Exception as e:
                print(f"Error durante la ejecución del paso: {e}")
            finally:
                # Limpieza segura al final de la ejecución de comandos (antes de esperar el siguiente)
                controlador_rover.detener()
                # Considera si quieres apagar el brazo después de cada secuencia o mantenerlo encendido
                # brazo_robotico.apagar() 
        else:
            #print("No se recibió ningún mensaje. Reintentando en breve...")
            time.sleep(0.1) # Esperar un poco antes de reintentar recibir un mensaje
            oled.write_text("No hay mensajes", 0, 20)