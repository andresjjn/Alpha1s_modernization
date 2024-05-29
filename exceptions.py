class Alpha1SError(Exception):
    """Base class for other exceptions"""
    pass

class BluetoothConnectionError(Alpha1SError):
    """Raised when there is an issue with the Bluetooth connection"""
    pass

class ServoError(Alpha1SError):
    """Raised when there is an issue with the servo"""
    pass
