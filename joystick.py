import pygame
from alpha1s import Alpha1s
from alpha1s.constants import walk, init
from time import sleep

def main():
    pygame.init()
    robot = Alpha1s()
    pygame.joystick.init()
    robot.battery()
    robot.led_handler(False)
    _joystick = pygame.joystick.Joystick(0)
    _joystick.init()
    current = 0
    while True:
        for i in range(current, len(walk)):
            pygame.event.pump()
            value = _joystick.get_axis(1)
            if value < -0.1:
                print(i)
                robot.servo_write_all(walk[i])
                sleep(1 + value)
            else:
                current = 0
                robot.servo_write_all(init)
                break
            current = 0

if __name__ == '__main__':
    main()