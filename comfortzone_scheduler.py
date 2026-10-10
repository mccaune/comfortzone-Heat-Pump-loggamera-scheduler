#!/usr/bin/env python3
"""Unofficial Comfort Zone / Loggamera temperature scheduler.

This integration relies on undocumented Loggamera web portal behavior. It may
stop working if the portal changes. No password or device ID is bundled.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo

import requests

LOGGER = logging.getLogger('comfortzone')
BASE_URL = 'https://portal.loggamera.se'
DEFAULT_SCHEDULE = '02:00=24,06:00=19,12:00=24,16:00=19'


def parse_schedule(value):
    result = []
    for item in value.split(','):
        try:
            clock, temp = item.strip().split('=', 1)
            hour, minute = (int(x) for x in clock.split(':'))
            temperature = float(temp)
        except (ValueError, TypeError) as exc:
            raise ValueError(f'Invalid schedule entry: {item!r}') from exc
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 10 <= temperature <= 30):
            raise ValueError(f'Schedule entry out of range: {item!r}')
        result.append((hour * 60 + minute, temperature))
    if not result or len(set(x[0] for x in result)) != len(result):
        raise ValueError('Schedule must contain unique times')
    return sorted(result)


def desired_temperature(now, schedule):
    minute = now.hour * 60 + now.minute
    selection = schedule[-1][1]
    for start, temperature in schedule:
        if minute >= start:
            selection = temperature
        else:
            break
    return selection


class LoggameraClient:
    def __init__(self, email, password, device_id, timeout=20):
        self.email, self.password, self.device_id = email, password, str(device_id)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/154 Safari/537.36'})

    def login(self):
        LOGGER.info('Logging in to Loggamera')
        self.session.cookies.clear()
        r = self.session.get(f'{BASE_URL}/Login/Start', timeout=self.timeout)
        r.raise_for_status()
        payload = [
            ('LoginUrl', ''), ('ReturnUrl', ''),
            ('email', self.email), ('password', self.password),
            ('rememberMe', 'true'), ('rememberMe', 'false'),
            ('change-language-dropdown', 'en-US'),
        ]
        r = self.session.post(
            f'{BASE_URL}/Login/Login', data=payload,
            headers={'Referer': f'{BASE_URL}/Login/Start'},
            allow_redirects=True, timeout=self.timeout,
        )
        r.raise_for_status()
        # This is a heuristic only, NOT proof that authentication succeeded.
        if '/Login/' in r.url:
            raise RuntimeError('Login appears to have failed (redirected to login page)')
        LOGGER.info('Login request completed; checking authorization with write request')

    def set_room_temperature(self, temperature):
        if not 10 <= temperature <= 30:
            raise ValueError('Temperature must be between 10 and 30 °C')
        self.login()
        LOGGER.info('Setting room temperature to %.1f °C', temperature)
        r = self.session.post(
            f'{BASE_URL}/LoggameraPro/SetParameter',
            data={'deviceId': self.device_id, 'capability': 'SetIndoorTemp', 'value': f'{temperature:.1f}'},
            headers={
                'X-Requested-With': 'XMLHttpRequest',
                'Referer': f'{BASE_URL}/Myheatpump/App?id={self.device_id}&startPage=settings&showMenu=false',
            },
            allow_redirects=False, timeout=self.timeout,
        )
        if r.status_code in (301, 302, 303, 307, 308):
            # Avoid printing full redirect URLs in case of unexpected tokens.
            raise RuntimeError(f'Write not authorized or redirected (HTTP {r.status_code})')
        r.raise_for_status()
        if r.text.strip().lower() != 'ok':
            raise RuntimeError(f'Unexpected write response (HTTP {r.status_code}); expected OK')
        LOGGER.info('Command accepted: %.1f °C', temperature)


def set_with_retry(client, temperature, attempts=3, delay=15):
    for attempt in range(1, attempts + 1):
        try:
            client.set_room_temperature(temperature)
            return True
        except (requests.RequestException, RuntimeError) as exc:
            LOGGER.error('Attempt %d/%d failed: %s', attempt, attempts, exc)
            if attempt < attempts:
                time.sleep(delay)
    LOGGER.error('Failed to set temperature after %d attempts', attempts)
    return False


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument('--once', action='store_true', help='Apply the current scheduled setpoint once (default)')
    operation.add_argument('--set', type=float, metavar='TEMP', help='Set a specific temperature once')
    operation.add_argument('--loop', action='store_true', help='Run continuously; use a systemd timer instead when possible')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
    email = os.environ.get('LOGGAMERA_EMAIL')
    password = os.environ.get('LOGGAMERA_PASSWORD')
    device_id = os.environ.get('LOGGAMERA_DEVICE_ID')
    if not all((email, password, device_id)):
        parser.error('Set LOGGAMERA_EMAIL, LOGGAMERA_PASSWORD and LOGGAMERA_DEVICE_ID')
    try:
        tz = ZoneInfo(os.environ.get('TZ', 'Europe/Riga'))
        schedule = parse_schedule(os.environ.get('COMFORTZONE_SCHEDULE', DEFAULT_SCHEDULE))
    except (ValueError, KeyError) as exc:
        parser.error(str(exc))
    client = LoggameraClient(email, password, device_id)
    if args.loop:
        last_successful = None
        while True:
            target = desired_temperature(datetime.now(tz), schedule)
            if target != last_successful:
                if set_with_retry(client, target):
                    last_successful = target
            time.sleep(20)
    target = args.set if args.set is not None else desired_temperature(datetime.now(tz), schedule)
    LOGGER.info('Target temperature: %.1f °C', target)
    return 0 if set_with_retry(client, target) else 1


if __name__ == '__main__':
    sys.exit(main())
