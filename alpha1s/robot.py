from .bluetooth_handler import alpha1s_bluetooth
from typing import List, Dict, Optional
from prettytable import PrettyTable
from time import sleep


class Alpha1s:
    def __init__(self, name: str = "ALPHA 1S"):
        print("Alpha 1S Robot Controller")
        self.__bt = alpha1s_bluetooth(name)

    def battery(self):
        msg = b'\x18\x00'
        parameter_len = 4
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            print(f"Battery with {int.from_bytes(ans[3:], 'big')}% of charge | {int.from_bytes(ans[:2], 'big')}mv ")

    def led_handler(self, state: bool):
        msg = b'\x0D' + (b'\x01' if state else b'\x00')
        self.__bt.write(msg)

    def servo_read(self, servo_id: int):
        servo_id = bytes([servo_id+1])
        msg = b'\x24' + servo_id
        parameter_len = 2
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None and ans[:1] == servo_id:
            return int.from_bytes(ans[1:], "big")
        return None

    def servo_read_all(self):
        msg = b'\x25\x00'
        parameter_len = 16
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            t = PrettyTable([str(i+1) for i in range(16)])
            t.add_row(ans)
            print(t)
            sleep(1)
            return [x for x in ans]
        return None

    def servo_write(self, servo_id: int, angle: int, travelling: int = 20):
        servo_id = bytes([servo_id+1])
        angle = bytes([angle])
        run_time = bytes([travelling])
        time_frames = b'\x00\x10'
        msg = b'\x22' + servo_id + angle + run_time + time_frames
        parameter_len = 2
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None and ans[:1] == servo_id:
            return int.from_bytes(ans[1:], "big")
        return None

    def servo_write_all(self, angles: List[int], travelling: int = 20):
        if len(angles) != 16:
            return None
        angles = bytearray(angles)
        run_time = bytes([travelling])
        time_frames = b'\x00\x10'
        msg = b'\x23' + angles + run_time + time_frames
        parameter_len = 16
        ans = self.__bt.read(msg, parameter_len)
        if ans is not None:
            return [x for x in ans]
        return None

    def servo_off(self):
        msg = b'\x0C\x00'
        self.__bt.write(msg)