"""Custom logging handler that buffers records for display in a Streamlit container."""

import logging
import threading
from datetime import datetime

import streamlit as st

# Loggers from src/ modules that the handler should attach to.
_SRC_LOGGERS = [
    "src.extraction",
    "src.completion",
    "src.graph",
    "src.ingestion",
    "src.cache",
    "src.vision_extraction",
    "src.notify",
]

_SESSION_KEY = "log_handler"


class StreamlitLogHandler(logging.Handler):
    """Buffers log records keyed by step label for later rendering."""

    def __init__(self):
        super().__init__(level=logging.INFO)
        self._records: dict[str, list[str]] = {}
        self._current_step: str = "General"
        self._lock = threading.Lock()
        self._step_order: list[str] = []

    def set_step(self, label: str) -> None:
        with self._lock:
            self._current_step = label
            if label not in self._records:
                self._records[label] = []
                self._step_order.append(label)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        ts = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        line = f"{ts} {record.levelname}: {msg}"
        with self._lock:
            step = self._current_step
            if step not in self._records:
                self._records[step] = []
                self._step_order.append(step)
            self._records[step].append(line)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()
            self._step_order.clear()

    def render(self) -> None:
        with self._lock:
            snapshot = {k: list(v) for k, v in self._records.items()}
            order = list(self._step_order)

        if not snapshot:
            return

        last_step = order[-1] if order else None

        for step_label in order:
            lines = snapshot.get(step_label, [])
            if not lines:
                continue
            expanded = step_label == last_step
            with st.status(step_label, expanded=expanded, state="complete" if not expanded else "running") as status:
                for line in lines:
                    status.markdown(f"`{line}`")


def setup_log_capture(step: str) -> StreamlitLogHandler:
    """Get or create the session-scoped log handler and set the active step."""
    if _SESSION_KEY not in st.session_state:
        handler = StreamlitLogHandler()
        formatter = logging.Formatter("%(message)s")
        handler.setFormatter(formatter)
        for name in _SRC_LOGGERS:
            lg = logging.getLogger(name)
            lg.addHandler(handler)
            lg.setLevel(logging.DEBUG)
        st.session_state[_SESSION_KEY] = handler

    handler = st.session_state[_SESSION_KEY]
    handler.set_step(step)
    return handler


def render_log_container() -> None:
    """Render the log output section at the bottom of the page."""
    handler: StreamlitLogHandler | None = st.session_state.get(_SESSION_KEY)
    if handler is None:
        return

    has_logs = bool(handler._records)
    col1, col2 = st.columns([6, 1])
    with col1:
        st.subheader("Output Log")
    with col2:
        if has_logs:
            if st.button("Clear", key="clear_logs"):
                handler.clear()
                st.rerun()

    if has_logs:
        handler.render()
    else:
        st.caption("No logs yet. Run a pipeline step to see output here.")
