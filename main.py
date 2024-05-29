from alpha1s import Alpha1S


def main():
    robot = Alpha1S()
    battery_info = robot.battery()
    if battery_info:
        print("Battery Info:", battery_info)
    else:
        print("Failed to read battery info")

    robot.leds(True)
    print("LEDs turned on")
    robot.leds(False)
    print("LEDs turned off")


if __name__ == '__main__':
    main()
