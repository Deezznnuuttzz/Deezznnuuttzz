"""Live terminal dashboard using curses. No external UI deps required."""
from __future__ import annotations

import curses
import time
from typing import Callable

from .alerts import AlertEngine
from .pids import STANDARD_PIDS

LABELS = {p.name: (p.name, p.unit) for p in STANDARD_PIDS.values()}


def run_dashboard(
    poll_fn: Callable[[], dict[str, float]],
    alert_engine: AlertEngine | None,
    interval: float,
    on_values: Callable[[dict[str, float]], None] | None = None,
) -> None:
    """poll_fn: called each cycle, returns {pid_name: value}.
    on_values: optional callback (e.g. to feed a CSV logger) invoked with
    the same dict each cycle.
    """
    curses.wrapper(_main, poll_fn, alert_engine, interval, on_values)


def _main(stdscr, poll_fn, alert_engine, interval, on_values):
    curses.curs_set(0)
    stdscr.nodelay(True)
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN, -1)
    curses.init_pair(2, curses.COLOR_RED, -1)
    curses.init_pair(3, curses.COLOR_YELLOW, -1)

    while True:
        c = stdscr.getch()
        if c in (ord("q"), 27):  # q or ESC quits
            return

        values = poll_fn()
        if on_values:
            on_values(values)
        alerts = alert_engine.check(values) if alert_engine else []
        alert_names = {a.name for a in alerts}

        stdscr.erase()
        stdscr.addstr(0, 0, "Duramax OBD-II Monitor  (q to quit)", curses.A_BOLD)
        row = 2
        for name, value in sorted(values.items()):
            label, unit = LABELS.get(name, (name, ""))
            color = curses.color_pair(2) if name in alert_names else curses.color_pair(1)
            try:
                stdscr.addstr(row, 2, f"{label:<24}", curses.A_NORMAL)
                stdscr.addstr(row, 26, f"{value:>10.2f} {unit}", color)
            except curses.error:
                pass
            row += 1

        if alerts:
            row += 1
            stdscr.addstr(row, 2, "ALERTS:", curses.color_pair(3) | curses.A_BOLD)
            row += 1
            for a in alerts:
                try:
                    stdscr.addstr(row, 4, a.message(), curses.color_pair(2))
                except curses.error:
                    pass
                row += 1

        stdscr.refresh()
        time.sleep(interval)
