"""
Recording of experiment events to a CSV file.

Experiment data is the actual product of the study, so it is written through a real
CSV writer instead of being formatted into log messages. Formatting rows by hand
means that a comma or a newline typed by a participant silently shifts the columns
and corrupts the recorded session.

One recorder - and therefore one file - is created per application run; use
`get_experiment_recorder()` to obtain it.
"""

from __future__ import annotations

import csv
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

# Column layout of the experiment CSV. `Level` is kept for backwards compatibility
# with previously recorded sessions and analysis scripts; it is always "DEBUG".
CSV_HEADER = [
    "Date",
    "Time",
    "Level",
    "Module",
    "Action",
    "Type",
    "Text",
    "Additional information",
]

_LEVEL = "DEBUG"

_recorder: Optional["ExperimentRecorder"] = None
_recorder_lock = threading.Lock()


def get_experiment_dir() -> Path:
    """Return the directory holding experiment recordings, creating it if needed."""
    path = Path.home() / "aac_app" / "experiment"
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_session_file_path() -> Path:
    """
    Build the CSV path for the current session, named after participant, model and
    start time.
    """
    participant = os.getenv("PARTICIPANT_NAME", "experiment").lower()
    model = os.getenv("APP_MODEL_NAME", "unknown_model")
    started_at = datetime.now().strftime("%Y-%m-%d_%H-%M")
    return get_experiment_dir() / f"{participant}_{model}_{started_at}.csv"


class ExperimentRecorder:
    """
    Appends experiment events to a CSV file.

    Rows are written through `csv.writer`, so any commas, quotes or newlines in the
    participant's text are quoted correctly instead of breaking the column layout.
    Every row is flushed immediately: a crash mid-session must not cost the data
    collected so far.
    """

    def __init__(self, file_path: Path):
        self._file_path = file_path
        self._lock = threading.Lock()

        is_new_file = (not file_path.exists()) or file_path.stat().st_size == 0
        self._file = open(file_path, "a", newline="", encoding="utf-8")
        self._writer = csv.writer(self._file)
        if is_new_file:
            self._writer.writerow(CSV_HEADER)
            self._file.flush()

    @property
    def file_path(self) -> Path:
        """Path of the CSV file this recorder writes to."""
        return self._file_path

    def record(
        self,
        module: str,
        action: str,
        event_type: str = "",
        text: str = "",
        additional: str = "",
    ) -> None:
        """
        Record a single experiment event.

        :param module: Name of the module reporting the event (usually `__name__`)
        :param action: What happened, e.g. "BUTTON CLICKED"
        :param event_type: Type of the involved item, e.g. a ButtonType
        :param text: Text associated with the event (may safely contain commas)
        :param additional: Any extra information
        """
        now = datetime.now()
        row = [
            now.strftime("%Y.%m.%d"),
            f"{now.strftime('%H:%M:%S')}.{now.microsecond // 1000:03d}",
            _LEVEL,
            module,
            action,
            str(event_type),
            text,
            str(additional),
        ]
        # The worker thread may deliver predictions, so guard the writer.
        with self._lock:
            self._writer.writerow(row)
            self._file.flush()

    def close(self) -> None:
        """Close the underlying file."""
        with self._lock:
            if not self._file.closed:
                self._file.close()


def get_experiment_recorder() -> ExperimentRecorder:
    """
    Return the recorder for this run, creating it on first use.

    A single shared instance guarantees that one run produces exactly one CSV file.
    """
    global _recorder
    if _recorder is None:
        with _recorder_lock:
            if _recorder is None:
                _recorder = ExperimentRecorder(build_session_file_path())
    return _recorder


def close_experiment_recorder() -> None:
    """Close and discard the current recorder, if any."""
    global _recorder
    with _recorder_lock:
        if _recorder is not None:
            _recorder.close()
            _recorder = None
