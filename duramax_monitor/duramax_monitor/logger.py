"""CSV logging of polled PID values, one row per poll cycle."""
from __future__ import annotations

import csv
import datetime as dt
from pathlib import Path


class CsvLogger:
    def __init__(self, path: str | Path, fieldnames: list[str]):
        self.path = Path(path)
        self.fieldnames = ["timestamp"] + fieldnames
        is_new = not self.path.exists() or self.path.stat().st_size == 0
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=self.fieldnames)
        if is_new:
            self._writer.writeheader()
            self._file.flush()

    def log(self, values: dict[str, float]) -> None:
        row = {"timestamp": dt.datetime.now().isoformat(timespec="milliseconds")}
        row.update({k: values.get(k, "") for k in self.fieldnames if k != "timestamp"})
        self._writer.writerow(row)
        self._file.flush()

    def close(self) -> None:
        self._file.close()

    def __enter__(self) -> "CsvLogger":
        return self

    def __exit__(self, *exc) -> None:
        self.close()
