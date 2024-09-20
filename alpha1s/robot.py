from .bluetooth_handler import alpha1s_bluetooth
from typing import List, Dict, Optional
from prettytable import PrettyTable
from time import sleep


class Alpha1s:
    def __init__(self, name: str = "ALPHA 1S"):
        print("Alpha 1S Robot Controller")
        self.__bt = alpha1s_bluetooth(name)

    # Comando: Leer la batería
    def battery(self):
        msg = b'\x18\x00'
        parameter_len = 4
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Batería con {int.from_bytes(ans[3:], 'big')}% de carga | {
                  int.from_bytes(ans[:2], 'big')} mV")
            battery_voltage = int.from_bytes(ans[:2], 'big')
            battery_capacity = ans[2]
            charging_state = 'Cargando' if ans[3] == 1 else 'No cargando'
            print(f"Batería: {battery_voltage} mV, Capacidad: {
                  battery_capacity}%, Estado de carga: {charging_state}")
            if int.from_bytes(ans[3:], 'big') <= 20:
                print("⚠️ Alerta: Nivel de batería bajo. Por favor, carga el robot.")
                # Puedes añadir acciones adicionales, como detener el robot
                self.stop_play()
                self.servo_off()
        else:
            print("No se pudo leer el estado de la batería.")

    # Comando: Leer versión de software
    def read_software_version(self):
        msg = b'\x11\x00'
        parameter_len = 10
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Versión del software: {ans.decode('utf-8')}")

    # Comando: Leer versión de hardware
    def read_hardware_version(self):
        msg = b'\x20\x00'
        parameter_len = 10
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Versión del hardware: {ans.decode('utf-8')}")

    # Comando: Apagar todos los servos
    def servo_off(self):
        msg = b'\x0C\x00'
        self.__bt.write(msg)

    # Comando: Leer estado del robot (incluye estado de sonido, reproducción, volumen, etc.)

    def read_robot_state(self):
        try:
            # Enviar comando para leer el estado del robot
            msg = b'\x0A\x00'
            # Longitud de la respuesta esperada (según el protocolo)
            parameter_len = 5
            ans = self.__bt.read(msg, parameter_len)

            # Verificar si se recibió una respuesta
            if ans is not None:
                # Para depurar el contenido de la respuesta
                print(f"Respuesta recibida: {ans}")
                sound_state = 'Mute' if ans[0] == 1 else 'No mute'
                play_state = 'Pausado' if ans[1] == 0 else 'Reproduciendo'
                volume = ans[2]
                servo_state = 'Encendido' if ans[3] == 1 else 'Apagado'
                tf_card = 'Insertada' if ans[4] == 1 else 'Removida'

                # Mostrar el estado completo
                print(f"Estado del robot: Sonido: {sound_state}, Reproducción: {play_state}, Volumen: {volume}, "
                      f"Estado del servo: {servo_state}, Tarjeta TF: {tf_card}")
            else:
                print("No se recibió respuesta del robot.")
        except Exception as e:
            print(f"Error al leer el estado del robot: {e}")

    # Comando: Ajustar el volumen

    def adjust_volume(self, volume: int):
        msg = b'\x0B' + bytes([volume])
        self.__bt.write(msg)

    # Comando: Leer capacidad de la batería
    def read_battery_capacity(self):
        msg = b'\x18\x00'
        parameter_len = 4
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Batería: {int.from_bytes(ans[:2], 'big')} mV, Capacidad restante: {
                  ans[2]}%, Cargando: {'Sí' if ans[3] == 1 else 'No'}")

    # Comando: Leer el ángulo de un servo (apagado)
    def read_servo_angle(self, servo_id: int):
        msg = b'\x24' + bytes([servo_id + 1])
        parameter_len = 2
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Ángulo del servo {servo_id}: {ans[1]}")

    # Comando: Controlar el movimiento de un solo servo
    def move_servo(self, servo_id: int, angle: int, time: int = 20):
        msg = b'\x22' + bytes([servo_id + 1]) + \
            bytes([angle]) + bytes([time]) + b'\x00\x10'
        self.__bt.write(msg)

    # Comando: Controlar el movimiento de múltiples servos
    def move_multiple_servos(self, angles: List[int], time: int = 20):
        if len(angles) != 16:
            print("Error: Se deben especificar 16 ángulos")
            return
        msg = b'\x23' + bytearray(angles) + bytes([time]) + b'\x00\x10'
        self.__bt.write(msg)

    # Comando: Detener la reproducción
    def stop_play(self):
        msg = b'\x05\x00'
        self.__bt.write(msg)

    # Comando: Cambiar el estado de sonido (mute o no mute)
    def set_sound(self, state: bool):
        msg = b'\x06' + (b'\x01' if state else b'\x00')
        self.__bt.write(msg)

    # Comando: Leer lista de acciones disponibles
    def get_action_list(self):
        msg = b'\x02\x00'
        self.__bt.write(msg)

    # Comando: Ejecutar lista de acciones
    def execute_action(self, action_name: str):
        action_name_bytes = action_name.encode('utf-8')
        msg = b'\x03' + action_name_bytes
        self.__bt.write(msg)
# Asegúrate de que estas constantes estén definidas
