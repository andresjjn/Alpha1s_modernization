import unittest
from alpha1s.robot import Alpha1S


class TestAlpha1S(unittest.TestCase):

    def setUp(self):
        self.robot = Alpha1S()

    def test_battery(self):
        battery_info = self.robot.battery()
        self.assertIsInstance(battery_info, dict)
        self.assertIn("percent", battery_info)
        self.assertIn("state", battery_info)
        self.assertIn("mV", battery_info)

    def test_servo_read(self):
        position = self.robot.servo_read(0)
        self.assertIsInstance(position, int)
        self.assertGreaterEqual(position, 0)
        self.assertLessEqual(position, 180)

    def test_servo_write(self):
        result = self.robot.servo_write(0, 90)
        self.assertIn(result, [0, 1, 2, 3])


if __name__ == '__main__':
    unittest.main()
