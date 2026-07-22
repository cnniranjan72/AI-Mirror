import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class StructuredFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "trace_id"):
            log_entry["trace_id"] = record.trace_id
        if hasattr(record, "user_id"):
            log_entry["user_id"] = record.user_id
        if hasattr(record, "stage"):
            log_entry["stage"] = record.stage
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if record.args:
            log_entry["extra"] = str(record.args)
        return json.dumps(log_entry)


def configure_logging(level: str = "INFO"):
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    return root


def stage_logger(name: str, stage: str):
    logger = logging.getLogger(name)
    logger = logging.LoggerAdapter(logger, {"stage": stage})
    return logger


def log_with_context(logger, level: str, message: str, trace_id: Optional[str] = None, user_id: Optional[str] = None,
                     **extra):
    extra_attrs = {}
    if trace_id:
        extra_attrs["trace_id"] = trace_id
    if user_id:
        extra_attrs["user_id"] = user_id
    extra_attrs.update(extra)
    log_fn = getattr(logger, level.lower(), logger.info)
    log_fn(message, extra=extra_attrs)
