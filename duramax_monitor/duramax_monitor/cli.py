from __future__ import annotations

import argparse
import logging
import sys

from .adapter import Elm327Adapter, NoData
from .alerts import AlertEngine
from .config import Config
from .discovery import sweep, write_results_csv
from .dtc import clear_dtcs, read_dtcs, read_freeze_frame
from .enhanced_pids import ENGINE_ECU_HEADER
from .logger import CsvLogger
from .pids import STANDARD_PIDS, decode as decode_pid


def _poll_values(adapter: Elm327Adapter, pid_names: list[str]) -> dict[str, float]:
    by_name = {p.name: p for p in STANDARD_PIDS.values()}
    values: dict[str, float] = {}
    for name in pid_names:
        definition = by_name.get(name)
        if definition is None:
            continue
        try:
            resp = adapter.query(0x01, definition.pid)
            values[name] = decode_pid(definition.pid, resp.data)
        except NoData:
            continue
    return values


def cmd_monitor(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    adapter = Elm327Adapter(config.connection_uri, timeout=config.timeout)
    adapter.connect()

    logger = CsvLogger(config.log_csv, fieldnames=config.pids) if config.log_csv else None
    alert_engine = AlertEngine.from_config(config.alert_entries)

    def poll_fn() -> dict[str, float]:
        return _poll_values(adapter, config.pids)

    def on_values(values: dict[str, float]) -> None:
        if logger:
            logger.log(values)

    try:
        if args.plain:
            import time

            while True:
                values = poll_fn()
                on_values(values)
                alerts = alert_engine.check(values)
                parts = [f"{k}={v:.1f}" for k, v in sorted(values.items())]
                line = "  ".join(parts)
                if alerts:
                    line += "  !! " + "; ".join(a.message() for a in alerts)
                print(line)
                time.sleep(config.interval)
        else:
            from .dashboard import run_dashboard

            run_dashboard(poll_fn, alert_engine, config.interval, on_values)
    except KeyboardInterrupt:
        pass
    finally:
        if logger:
            logger.close()
        adapter.close()
    return 0


def cmd_dtc_read(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    adapter = Elm327Adapter(config.connection_uri, timeout=config.timeout)
    adapter.connect()
    try:
        for label, mode in (("Stored", 0x03), ("Pending", 0x07), ("Permanent", 0x0A)):
            codes = read_dtcs(adapter, mode)
            print(f"{label} DTCs:", ", ".join(c.code for c in codes) or "(none)")
            if codes:
                ff = read_freeze_frame(adapter)
                if ff.values:
                    print(f"  Freeze frame @ set time: {ff.values}")
    finally:
        adapter.close()
    return 0


def cmd_dtc_clear(args: argparse.Namespace) -> int:
    if not args.yes:
        print(
            "This clears ALL stored/pending DTCs and resets emissions readiness\n"
            "monitors (they'll show 'not ready' until enough drive cycles\n"
            "complete, which can affect state inspection). Re-run with --yes\n"
            "to confirm."
        )
        return 1
    config = Config.load(args.config)
    adapter = Elm327Adapter(config.connection_uri, timeout=config.timeout)
    adapter.connect()
    try:
        clear_dtcs(adapter)
        print("DTCs cleared.")
    finally:
        adapter.close()
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    config = Config.load(args.config)
    adapter = Elm327Adapter(config.connection_uri, timeout=config.timeout, header=ENGINE_ECU_HEADER)
    adapter.connect()

    def progress(pid: int, found: int) -> None:
        if pid % 0x100 == 0:
            print(f"  scanning 0x{pid:04X}... ({found} responsive so far)", file=sys.stderr)

    try:
        results = sweep(adapter, start=args.start, end=args.end, delay=args.delay, on_progress=progress)
    finally:
        adapter.close()

    write_results_csv(results, args.out)
    print(f"Found {len(results)} responsive PID(s) in [0x{args.start:04X}, 0x{args.end:04X}]. "
          f"Wrote {args.out}")
    print(
        "These are RAW, UNVERIFIED responses - do not assume you know what a PID "
        "means just because it responded. Correlate against a known real-world "
        "change before trusting it (see enhanced_pids.py docstring)."
    )
    return 0


def cmd_list_pids(args: argparse.Namespace) -> int:
    print("Standard (Mode 01) PIDs this build can decode:")
    for p in sorted(STANDARD_PIDS.values(), key=lambda p: p.pid):
        print(f"  0x{p.pid:02X}  {p.name:<24} {p.unit:<8} {p.description}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="duramax-monitor", description=__doc__)
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_monitor = sub.add_parser("monitor", help="Live-poll configured PIDs")
    p_monitor.add_argument("--plain", action="store_true", help="Print lines instead of curses dashboard")
    p_monitor.set_defaults(func=cmd_monitor)

    p_dtc = sub.add_parser("dtc", help="Read or clear diagnostic trouble codes")
    dtc_sub = p_dtc.add_subparsers(dest="dtc_command", required=True)
    p_dtc_read = dtc_sub.add_parser("read", help="Read stored/pending/permanent DTCs + freeze frame")
    p_dtc_read.set_defaults(func=cmd_dtc_read)
    p_dtc_clear = dtc_sub.add_parser("clear", help="Clear DTCs and reset readiness monitors")
    p_dtc_clear.add_argument("--yes", action="store_true", help="Confirm the clear")
    p_dtc_clear.set_defaults(func=cmd_dtc_clear)

    p_discover = sub.add_parser("discover", help="Sweep Mode 22 enhanced PIDs to help identify real ones")
    p_discover.add_argument("--start", type=lambda s: int(s, 0), default=0x0000)
    p_discover.add_argument("--end", type=lambda s: int(s, 0), default=0x00FF)
    p_discover.add_argument("--delay", type=float, default=0.05)
    p_discover.add_argument("--out", default="discovery_results.csv")
    p_discover.set_defaults(func=cmd_discover)

    p_list = sub.add_parser("list-pids", help="List known standard PIDs")
    p_list.set_defaults(func=cmd_list_pids)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.WARNING)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
