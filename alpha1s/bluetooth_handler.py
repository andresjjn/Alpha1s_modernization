import bluetooth
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class alpha1s_bluetooth:
    def __init__(self, name: str):
        self.sock = None
        address = self.__discover(name)
        if address is not None:
            logger.info("Robot found")
            self.__connect(address)
        else:
            logger.error(f"Error: {name} not found")
            raise ValueError(f"Error: {name} not found")

    def __del__(self):
        if self.sock:
            self.sock.close()

    def __discover(self, name: str) -> Optional[str]:
        try:
            devices = bluetooth.discover_devices(lookup_names=True)
            for addr, text in devices:
                if text == name:
                    return addr
        except bluetooth.BluetoothError as e:
            logger.error(f"Error discovering devices: {e}")
        return None

    def __connect(self, addr: str):
        try:
            self.sock = bluetooth.BluetoothSocket(bluetooth.RFCOMM)
            self.sock.connect((addr, 6))
            self.sock.settimeout(10.0)
        except bluetooth.BluetoothError as e:
            logger.error(f"Error connecting to device: {e}")
            self.sock = None

    @contextmanager
    def connection(self, addr: str):
        try:
            self.__connect(addr)
            yield
        finally:
            if self.sock:
                self.sock.close()

    def write(self, msg: bytes):
        cmd = self.__compose(msg)
        self.sock.send(cmd)

    def read(self, msg: bytes, ans_len: int) -> Optional[bytes]:
        self.write(msg)
        length = 6 + ans_len
        ans = self.sock.recv(length)
        if self.__check(ans):
            return ans[4:-2]
        return None

    def __compose(self, msg: bytes) -> bytes:
        header = b'\xFB\xBF'
        end = b'\xED'
        length = bytes([4 + len(msg)])
        check_list = bytearray(length)
        check_list.extend(msg)
        check = bytes([sum(check_list) % 256])
        return header + length + msg + check + end

    def __check(self, msg: bytes) -> bool:
        msg = bytearray(msg)
        if msg[:2] != b'\xFB\xBF' or msg[-1:] != b'\xED' or msg[-2:-1] != bytes([sum(msg[2:-2]) % 256]):
            return False
        return True
