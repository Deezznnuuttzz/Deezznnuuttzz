# Duramax OBD-II Engine Monitor

A Python OBD-II engine monitor built for a 2013 GM Duramax (LML) truck, but
usable on any ISO 15765-4 (CAN) OBD-II vehicle for the standard PID set. It
talks to any ELM327-compatible adapter (USB, Bluetooth-SPP, or WiFi) over
serial or a TCP socket.

## What it does

- Polls standard (SAE J1979 Mode 01) PIDs: RPM, speed, coolant temp, intake
  air temp, engine load, throttle position, MAF, fuel level, control module
  voltage, and more (`duramax_monitor list-pids` for the full list).
- Live terminal dashboard (curses) or plain line-by-line output, with
  configurable min/max alert thresholds.
- Logs every poll cycle to a timestamped CSV.
- Reads/clears diagnostic trouble codes (stored, pending, permanent) and
  freeze frame data.
- Includes the plumbing for GM's proprietary "enhanced" Mode 22 PIDs (boost,
  EGT, trans temp, DPF/DEF, etc.) plus a PID-discovery tool - see the
  important caveat below before you use this part.
- Ships a built-in simulator (`sim://`) so you can run and test the whole
  pipeline without any hardware plugged in.

## Important: about Duramax-specific data (boost, EGT, trans temp, DPF/DEF)

Those readings are **not** part of the public OBD-II standard - they live
behind GM's manufacturer-specific "Mode 22" diagnostic PIDs, and the exact
PID numbers and byte-scaling formulas are specific to your truck's ECU
calibration. There is no single trustworthy public list of these, and forum
posts/plugins are frequently wrong or mismatched to the wrong calibration.

Because of that, this project does **not** ship any pre-filled enhanced PID
values - `duramax_monitor/enhanced_pids.py` starts empty on purpose. Instead:

1. Use `duramax-monitor discover` to sweep a range of Mode 22 identifiers on
   your own truck and log which ones respond (see `duramax_monitor/discovery.py`
   for the full rationale - it's a read-only diagnostic query, safe to run,
   but do it parked/idling rather than while driving).
2. Correlate candidate PIDs against a real-world change (rev the engine, let
   coolant/trans temp climb, compare against the factory Driver Information
   Center) before you decide what a PID means.
3. Once verified, add it to `config.yaml` under `enhanced_pids:` (see
   `config.example.yaml` for the format) or directly to
   `duramax_monitor/enhanced_pids.py`.

Do not trust an unverified enhanced PID value for anything that matters
(e.g. towing EGT limits) - verify it against a known-good reference first.

## Hardware

- **Adapter**: any ELM327-compatible adapter works for the standard PID set.
  For the enhanced/Mode-22 diesel PIDs, a name-brand adapter (OBDLink SX/LX/MX+,
  BAFX, etc.) is worth it - clone ELM327 firmware is often flaky on UDS
  extended-session and Mode 22 requests.
- **Host**: a Raspberry Pi (or any Linux/Windows/Mac machine) works fine.
  This is plain Python + pyserial, so it runs the same way on a laptop for
  development/testing and on a Pi for an always-on in-cab logger.
- **Connection**:
  - USB or paired-Bluetooth adapter → `serial:///dev/ttyUSB0` (Linux) or
    `serial://COM5` (Windows), or `serial:///dev/rfcomm0` for a Bluetooth-SPP
    adapter bound with `rfcomm bind`.
  - WiFi adapter → `socket://<adapter-ip>:35000` (port varies by adapter,
    check its manual - 35000 is the common ELM327 WiFi default).
  - No hardware yet → `sim://` (built-in simulator).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp config.example.yaml config.yaml
# edit config.yaml: set connection.uri to your adapter, adjust pids/alerts
```

## Usage

```bash
# Live dashboard
duramax-monitor monitor

# Plain-text output (easier to pipe/redirect)
duramax-monitor monitor --plain

# Read stored/pending/permanent DTCs + freeze frame
duramax-monitor dtc read

# Clear DTCs (resets readiness monitors - requires --yes)
duramax-monitor dtc clear --yes

# Sweep Mode 22 enhanced PIDs to find real ones on your truck
duramax-monitor discover --start 0x1000 --end 0x1100 --out discovery_results.csv

# List every standard PID this build knows how to decode
duramax-monitor list-pids
```

All commands accept `--config path/to/config.yaml` (defaults to
`config.yaml` in the current directory) and `-v` for verbose logging (must
come before the subcommand, e.g. `duramax-monitor -v monitor`).

## Development / testing without a truck

```bash
pip install -e . pytest
pytest                              # unit tests for PID/DTC decoding + response parsing
duramax-monitor monitor --plain     # runs against config.example.yaml's sim:// by default
```

## Project layout

```
duramax_monitor/
  transport.py      # Serial / socket / simulated transports
  adapter.py         # ELM327 init + Mode 01/02/03/04/07/22 request/response parsing
  pids.py            # Standard (SAE J1979) PID table + decode formulas
  enhanced_pids.py   # GM Mode 22 PID scaffold (empty by design - see caveat above)
  discovery.py       # Mode 22 PID sweep tool
  dtc.py             # DTC decode, clear, freeze frame
  logger.py          # CSV logging
  alerts.py          # Threshold alerting
  dashboard.py       # curses live dashboard
  cli.py             # Command-line entry point
```
