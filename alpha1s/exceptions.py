class Alpha1SError(Exception):
    """Base class for other exceptions"""
    print(Exception)
    pass

class BluetoothConnectionError(Alpha1SError):
    """Raised when there is an issue with the Bluetooth connection"""
    print(Alpha1SError)
    pass

class ServoError(Alpha1SError):
    """Raised when there is an issue with the servo"""
    print(Alpha1SError)
    pass