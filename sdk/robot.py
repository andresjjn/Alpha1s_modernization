from .bluetooth_handler import alpha1s_bluetooth
from typing import List


class Alpha1s:
    def __init__(self, name: str = "ALPHA 1S"):
        print("Alpha 1S Robot Controller")
        self.__bt = alpha1s_bluetooth(name)

    def battery(self):
        """Read battery state. Calls stop_play()+servo_off() automatically if <=20%."""
        msg = b'\x18\x00'
        parameter_len = 4
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            battery_voltage = int.from_bytes(ans[:2], 'big')
            battery_capacity = ans[2]
            charging_state = 'Cargando' if ans[3] == 1 else 'No cargando'
            print(f"Batería: {battery_voltage} mV, Capacidad: {battery_capacity}%, Estado: {charging_state}")
            if battery_capacity <= 20:
                print("⚠️ Batería baja. Apagando servos.")
                self.stop_play()
                self.servo_off()
        else:
            print("No se pudo leer el estado de la batería.")

    def read_software_version(self):
        msg = b'\x11\x00'
        parameter_len = 10
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Versión del software: {ans.decode('utf-8')}")

    def read_hardware_version(self):
        msg = b'\x20\x00'
        parameter_len = 10
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Versión del hardware: {ans.decode('utf-8')}")

    def servo_off(self):
        """Power-off all servos. NOTE: robot will go limp — use only when safe."""
        msg = b'\x0C\x00'
        self.__bt.write(msg)

    def adjust_volume(self, volume: int):
        """Set robot speaker volume. Range: 0–255."""
        msg = b'\x0B' + bytes([volume])
        self.__bt.write(msg)

    def read_servo_angle(self, servo_id: int):
        """Read current angle of a single servo (0-indexed)."""
        msg = b'\x24' + bytes([servo_id + 1])
        parameter_len = 2
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Ángulo del servo {servo_id}: {ans[1]}")

    def move_servo(self, servo_id: int, angle: int, time: int = 20):
        """Move a single servo to the given angle. time is travelling units (20 ≈ 400 ms)."""
        msg = (b'\x22'
               + bytes([servo_id + 1])
               + bytes([angle])
               + bytes([time])
               + b'\x00\x10')
        self.__bt.write(msg)

    def move_multiple_servos(self, angles: List[int], time: int = 20):
        """Move all 16 servos simultaneously. angles must have exactly 16 values (0–180°)."""
        if len(angles) != 16:
            print("Error: Se deben especificar 16 ángulos")
            return
        msg = b'\x23' + bytearray(angles) + bytes([time]) + b'\x00\x10'
        self.__bt.write(msg)

    def servo_write_all(self, angles: List[int], travelling: int = 20):
        """Alias for move_multiple_servos with 'travelling' kwarg — used by the Pi client."""
        self.move_multiple_servos(angles, time=travelling)

    def stop_play(self):
        """Stop any currently playing action or sequence."""
        msg = b'\x05\x00'
        self.__bt.write(msg)

    def set_sound(self, state: bool):
        """Mute (False) or unmute (True) the robot speaker."""
        msg = b'\x06' + (b'\x01' if state else b'\x00')
        self.__bt.write(msg)

    def get_action_list(self):
        """Request the list of available named actions from the robot."""
        msg = b'\x02\x00'
        self.__bt.write(msg)

    def execute_action(self, action_name: str):
        """Trigger a named factory action stored on the robot (e.g. 'WaveHand')."""
        action_name_bytes = action_name.encode('utf-8')
        msg = b'\x03' + action_name_bytes
        self.__bt.write(msg)

    def led_handler(self, state: bool):
        # Opcode 0x08. VERIFY against Alpha1_Series_Bluetooth_communication_protocol PDF
        # before deploying — the exact frame format may differ from other write commands.
        param = b'\x01' if state else b'\x00'
        self.__bt.write(b'\x08\x00' + param)

    def leds(self, state: bool):
        """Alias for led_handler — matches the call signature used by the Pi client."""
        self.led_handler(state)
