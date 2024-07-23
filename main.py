from alpha1s import Alpha1s
from alpha1s.constants import walk, init
from time import sleep


def main():
    robot = Alpha1s()
    print(robot.battery())
    robot.led_handler(False)
    for i in range(0, len(walk)):
        robot.servo_write_all(walk[i])
        sleep(0.5)


if __name__ == '__main__':
    main()