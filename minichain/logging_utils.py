from __future__ import annotations

import json
import sys
import time
from typing import Any
from . import config


LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}
CURRENT = LEVELS.get(config.LOG_LEVEL.upper(), 20)


def log(level: str, event: str, **fields: Any):
    if LEVELS[level] < CURRENT:
        return
    rec = {"ts": time.time(), "level": level, "event": event}
    if fields:
        rec.update(fields)
    sys.stdout.write(json.dumps(rec) + "\n")
    sys.stdout.flush()


def debug(event: str, **fields: Any):
    log("DEBUG", event, **fields)


def info(event: str, **fields: Any):
    log("INFO", event, **fields)


def warn(event: str, **fields: Any):
    log("WARN", event, **fields)


def error(event: str, **fields: Any):
    log("ERROR", event, **fields)
