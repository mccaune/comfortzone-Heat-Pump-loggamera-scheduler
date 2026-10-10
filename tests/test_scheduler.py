import unittest
from datetime import datetime
from unittest.mock import Mock, patch

from comfortzone_scheduler import parse_schedule, desired_temperature, set_with_retry


class ScheduleTests(unittest.TestCase):
    def setUp(self):
        self.schedule = parse_schedule('02:00=24,06:00=19,12:00=24,16:00=19')

    def test_each_interval(self):
        for hour, minute, expected in [(0, 0, 19), (2, 0, 24), (5, 59, 24), (6, 0, 19), (12, 0, 24), (16, 0, 19), (23, 59, 19)]:
            self.assertEqual(desired_temperature(datetime(2026, 10, 10, hour, minute), self.schedule), expected)

    def test_unsorted_input(self):
        self.assertEqual(parse_schedule('16:00=19,02:00=24'), [(120, 24), (960, 19)])

    def test_invalid_schedule(self):
        for value in ['', '25:00=24', '12:00=31', '12:00=19,12:00=20', 'garbage']:
            with self.assertRaises(ValueError):
                parse_schedule(value)

    @patch('comfortzone_scheduler.time.sleep')
    def test_write_failure_returns_false(self, sleep):
        client = Mock()
        client.set_room_temperature.side_effect = RuntimeError('Unauthorized')
        self.assertFalse(set_with_retry(client, 19, attempts=3, delay=15))
        self.assertEqual(client.set_room_temperature.call_count, 3)
        self.assertEqual(sleep.call_count, 2)


if __name__ == '__main__':
    unittest.main()
