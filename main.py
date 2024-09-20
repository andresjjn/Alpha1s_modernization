from alpha1s import Alpha1s
from alpha1s.constants import walk, init, forward
from time import sleep


def main():
    robot = Alpha1s()
    robot.battery()

    # Leer la versión del software
    # robot.read_software_version()

    # Leer la versión del hardware
    # robot.read_hardware_version()

    # Apagar todos los servos
    # robot.servo_off()

    # Ajustar el volumen a un nivel intermedio (128 de 255)
    # robot.adjust_volume(128)

    # Leer el estado completo del robot (sonido, reproducción, volumen, etc.)
    # robot.read_robot_state() NO FUNCIONA!!!

    # Encender el LED
    # robot.led_handler(True)
    # sleep(1)

    # Apagar el LED
    # robot.led_handler(False)

    # Mover todos los servos a la posición inicial (init)
    # print("Moviendo a la posición inicial...")
    # robot.move_multiple_servos(init)
    # sleep(2)

    # Ejecutar una secuencia de movimiento, como "walk"
    # print("Ejecutando secuencia de cam
    # Leer la batería y mostrar la capacidadinar...")
    for i in range(0, len(walk)):
        robot.move_multiple_servos(walk[i])
        sleep(0.5)

    # Ejecutar otra acción predefinida, como "hands_up"
    # print("Levantando las manos...")
    # robot.move_multiple_servos(forward)
    # sleep(2)

    # Detener la reproducción actual
    # robot.stop_play()

    # Leer el ángulo de un servo específico (por ejemplo, el servo 1)
    # robot.read_servo_angle(1)

    # Obtener la lista de acciones disponibles (si el robot lo soporta)
    robot.get_action_list()

    # Ejecutar una acción (si tienes el nombre de la acción)
    # robot.execute_action("WaveHand")  # Asegúrate de que "WaveHand" sea una acción válida en tu robot


if __name__ == '__main__':
    main()
