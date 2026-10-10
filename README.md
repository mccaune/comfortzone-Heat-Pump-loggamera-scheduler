# Comfort Zone heat pump scheduler (unofficial)

**Automatically adjust a Comfort Zone heat pump's room-temperature setpoint based on time of day or cheaper electricity periods, using the Loggamera web portal.** Intended for a small always-on Linux machine such as a Raspberry Pi.

> **Unofficial community project.** Not affiliated with or endorsed by ComfortZone, Loggamera, or their manufacturers. The integration uses undocumented web portal requests and may stop working if the portal changes. This project is not a safety controller.

## The problem

Some Comfort Zone owners can change the requested indoor temperature in their phone app, but cannot schedule it to track their preferred electricity-tariff windows. The original use case was to request **24 °C at 02:00–06:00 and 12:00–16:00**, and **19 °C otherwise**. These are *requested indoor-temperature setpoints*, **not** guarantees that the home reaches those temperatures or that the strategy saves money. Heat pumps, building thermal mass, COP and tariff structures vary.

### Why a portal-based approach instead of the API?

During development, an API-based approach was investigated, but **the available API access did not provide a working way to change the target room-temperature setting**. That is a statement about this project's testing, **not** a claim that no official write API exists for any device or account. The Loggamera web portal's authenticated request to `POST /LoggameraPro/SetParameter` with capability `SetIndoorTemp` was then tested successfully from both Windows and a Raspberry Pi 3. The web request emulates an action made by the portal; it is **not a supported or documented public API**.

**Verified in this project:** Python 3.12 on Ubuntu Server 24.04, Raspberry Pi 3, login followed by temperature-setting response `OK`, actual 19 °C setpoint observed on the heat pump, and scheduled service surviving a reboot. **Not established:** compatibility with every Comfort Zone model, other portal accounts, long-term stability across portal changes, or actual electricity savings.

## How it works

```text
systemd timer (02:00 / 06:00 / 12:00 / 16:00)
        |
        v
Python script --once -> evaluate configured time zone + schedule
        |
        v
Loggamera login page -> login form + session cookies
        |
        v
POST /LoggameraPro/SetParameter
  deviceId=<your device ID>
  capability=SetIndoorTemp
  value=<requested Celsius setpoint>
        |
        v
Expect response text "OK"; log success or return nonzero on error
```

A fresh login is attempted before every write to avoid depending on an hours-old session. `requests.Session` keeps cookies across the login and write calls. Each scheduled run attempts up to three writes, with 15-second intervals. `systemd` runs the script on schedule, starts it after missed events when booting (`Persistent=true`), and logs results to the journal. **A network outage lasting longer than the three attempts is not continuously retried** until the next timer event or a manual run.

## Prerequisites

- Ubuntu Server 24.04 (tested on Raspberry Pi 3) or another Python 3.9+ Linux system with `zoneinfo` timezone data
- Python 3, `venv`, and working network access to `https://portal.loggamera.se`
- Working Loggamera account credentials **and the device ID from your own portal account**
- `systemd` for automatic scheduling (optional for manual tests)

## Quick start (Ubuntu / Raspberry Pi)

```bash
sudo apt update
sudo apt install -y python3 python3-venv git
# Once you publish/fork the repository, clone YOUR GitHub URL:
git clone https://github.com/YOUR-USERNAME/comfortzone-loggamera-scheduler.git
cd comfortzone-loggamera-scheduler
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
chmod 600 .env
nano .env
```

Fill `LOGGAMERA_EMAIL`, `LOGGAMERA_PASSWORD`, `LOGGAMERA_DEVICE_ID`, timezone and schedule. **Never share the populated `.env`.**

For a one-time test, load settings in the current shell (simple Bash `.env` syntax is required):

```bash
set -a
source .env
set +a
.venv/bin/python comfortzone_scheduler.py --once
```

This **sends a real command** to your heat pump. Verify the new setpoint on the device or in its app. To set a specific permitted temperature instead of the schedule, run `... comfortzone_scheduler.py --set 19`.

### Install a systemd service and timer

The provided sample service assumes the repo lives directly at `/home/<user>/comfortzone-loggamera-scheduler`. If you keep it elsewhere, update **every** path.

```bash
sudo cp systemd/comfortzone.service /etc/systemd/system/
sudo cp systemd/comfortzone.timer /etc/systemd/system/
sudo nano /etc/systemd/system/comfortzone.service
```

Replace **every** `REPLACE_WITH_LINUX_USERNAME` in the service with your Linux username, and update the path if needed. Then:

```bash
sudo timedatectl set-timezone Europe/Riga  # choose YOUR time zone
sudo systemctl daemon-reload
sudo systemctl enable --now comfortzone.timer
systemctl list-timers --all comfortzone.timer
sudo systemctl start comfortzone.service   # REAL temperature write
sudo journalctl -u comfortzone.service -n 50 --no-pager
```

**Important:** the example `OnCalendar` times in `systemd/comfortzone.timer` must match `COMFORTZONE_SCHEDULE` in `.env`. The timer decides *when* to run; Python decides *which setpoint* is valid at that time. If you edit the schedule, edit both and run `sudo systemctl daemon-reload && sudo systemctl restart comfortzone.timer`.

After reboot, verify with `systemctl is-active comfortzone.timer`. To stop automation: `sudo systemctl disable --now comfortzone.timer`.

### Example time-of-use schedule

| Local time | Setpoint |
| --- | ---: |
| 02:00 | 24 °C |
| 06:00 | 19 °C |
| 12:00 | 24 °C |
| 16:00 | 19 °C |

`COMFORTZONE_SCHEDULE="02:00=24,06:00=19,12:00=24,16:00=19"`

Only times between `00:00` and `23:59` and temperatures **10–30 °C** are accepted by this script. Change limits only after confirming device-supported values. DST transitions use the OS time zone; scheduled times during a skipped or repeated clock hour may behave differently.

## Troubleshooting

- **`302` with `ReturnUrl=...SetParameter`:** commonly means the write request was redirected toward authentication. In the original setup it was ultimately caused by an **incorrect password in the environment file**, although login was initially logged as successful. Check credentials first; the basic login URL check does **not** prove authentication.
- **`LOGGAMERA_*` missing:** `.env` is not automatically imported by Python; load it in your shell or use the `EnvironmentFile=` entry in systemd.
- **Service failed:** `sudo journalctl -u comfortzone.service -n 100 --no-pager`, `systemctl status comfortzone.service`.
- **Timer not firing:** verify `timedatectl`, `systemctl list-timers --all comfortzone.timer`, and timer schedule matches `.env`.
- **Write returns something other than `OK`:** the portal may have changed, account permissions may differ, or the device ID may be wrong. Do not blindly retry indefinitely.
- **Network failure:** the command is retried three times in one run, then the script returns a nonzero exit code. Run manually after connectivity is restored or wait for the next scheduled event.

## Security, limitations, and community contributions

Read [SECURITY.md](SECURITY.md), [docs/TECHNICAL_NOTES.md](docs/TECHNICAL_NOTES.md) and [docs/README.lv.md](docs/README.lv.md). Keep the Pi and SSH protected, use least-privilege accounts where possible, and **do not commit passwords, tokens, real device IDs, IP addresses or session cookies**. Respect the provider's terms and avoid excessive polling. Portal behavior is not guaranteed. Review any change carefully before using it to control heating equipment.

Tests (offline, no heat-pump access required):

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Issues and pull requests for verified compatibility fixes, clearer instructions and non-sensitive error reports are welcome. Please never post credentials or full authenticated HTTP traces.

## License

[MIT](LICENSE). This is original community code, not vendor software.
