# Technical notes and design rationale

## Why Python + systemd timer?

The installation is an always-on, low-power Raspberry Pi 3 with ~1 GB RAM. An OS without a desktop reduces unnecessary load. The single Python process uses `requests` rather than a browser/GUI; one-shot `systemd` execution eliminates the need for a continuously running Python scheduler. Systemd handles boot-time enablement, local calendar scheduling, standard logs, and recovery of a missed activation after downtime (`Persistent=true`). `--loop` remains available for experiments but the timer approach is preferred.

## The unofficial write mechanism

Observed flow in the working implementation:

1. `GET https://portal.loggamera.se/Login/Start`
2. `POST https://portal.loggamera.se/Login/Login` using form fields `email`, `password`, `LoginUrl`, `ReturnUrl`, duplicated `rememberMe` values, and a language field
3. In the same `requests.Session`, `POST https://portal.loggamera.se/LoggameraPro/SetParameter` with `deviceId`, `capability=SetIndoorTemp`, `value=<Celsius>` and web-style `Referer` and `X-Requested-With` headers
4. Interpret the literal `OK` body as *portal acceptance*, not definitive proof of physical equipment response

The actual device state should be independently confirmed through the heat pump or app. The route and form fields are undocumented implementation details; they are not a contract. Avoid increasing request frequency without good reason.

## Authentication gotcha

The login implementation historically checked only whether the final redirected URL contained `/Login/`, then printed `Login successful`. An incorrect password nevertheless produced `Login successful` and a subsequent `302` redirect for `SetParameter`, ending in `/?ReturnUrl=%2fLoggameraPro%2fSetParameter`. Correcting the password fixed the issue; a subsequent request received `OK` and the heat pump displayed 19 °C. The public version explicitly clarifies that login URL checking is only a heuristic; actual acceptance is determined at the write response.

## Failure behavior

The original user script in the conversation returned false after three unsuccessful attempts, but its CLI could still exit with status zero. This published version intentionally returns exit code `1` after failed writes, so systemd monitoring can detect failure. There is no alert integration and no continuous correction of settings changed externally. Recovery after loss of connectivity depends on the next timer tick or manual invocation. `Persistent=true` is not the same as a periodic connectivity check.

## Customize scheduling safely

- Change `COMFORTZONE_SCHEDULE` and corresponding `OnCalendar=` entries together.
- Default schedule times refer to system-local timezone; configure it with `timedatectl`, and set `TZ` in `.env` consistently.
- Remember summer/winter clock transitions.
- Consider whether temporary setpoint changes improve total cost when heat-pump efficiency and thermal losses change.
- Before experimenting with higher temperatures, follow the device's operating instructions.

## Privacy and attribution

All identifying properties (account email, password, device ID, LAN IP) must be supplied by the user and excluded from version control. Do not put full portal responses or login request bodies in GitHub Issues.
