"""Shared numeric validation and deterministic artifact serialization."""
import hashlib
import json
import math
from datetime import date
from pathlib import Path

HIGH = {"Major", "Super-elite", "Elite"}


class DataError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise DataError(message)


def number(value, low, high, label):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            label + ": 非有限数值或超出范围")


def iso(value, label):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise DataError(label + ": 需要 YYYY-MM-DD")


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False).encode("utf-8")).hexdigest()


def normalize(value, config):
    r = config["rating"]
    return 100*max(0, min(1, (value-r["low"])/(r["high"]-r["low"])))


def dump_json(path, value):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def fmt(value):
    return "—" if value is None else "%.2f" % value
