"""Structured JSON logs with a call id, so a call can be traced end to end."""

import json
import logging
import sys
import time

_logger = logging.getLogger("elevatebox")
if not _logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    _logger.addHandler(handler)
    _logger.setLevel(logging.INFO)
    _logger.propagate = False


def log_event(event: str, call_id: str = "-", **fields) -> None:
    record = {"ts": round(time.time(), 3), "event": event, "call_id": call_id}
    record.update(fields)
    _logger.info(json.dumps(record, default=str, ensure_ascii=False))
