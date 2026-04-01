import json
import os
import re
from datetime import datetime, timezone
from uuid import uuid4


ISO_FMT = "%Y-%m-%dT%H:%M:%SZ"
DATE_FMT = "%Y-%m-%d"
TIME_FMT = "%H:%M"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def load_json(path: str, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data) -> None:
    ensure_dir(os.path.dirname(path) or ".")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def now_utc_iso() -> str:
    return datetime.now(timezone.utc).strftime(ISO_FMT)


def now_local_date() -> str:
    return datetime.now().strftime(DATE_FMT)


def now_local_time() -> str:
    return datetime.now().strftime(TIME_FMT)


def parse_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    s = str(value).strip().lower()
    return s in {"1", "true", "si", "sí", "yes", "y", "on"}


def normalize_key(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text


def make_uuid() -> str:
    return str(uuid4())


def apply_calculo(calculo: str, field_type: str):
    if not calculo:
        return None
    c = calculo.strip().lower()
    if c in {"hoy()", "today()"}:
        return now_local_date()
    if c in {"hora()", "now_time()"}:
        return now_local_time()
    if c in {"ahora()", "now()"}:
        return now_utc_iso()
    if c.startswith("fijo:"):
        return calculo.split(":", 1)[1].strip()
    # valor por defecto de respaldo según tipo
    if field_type == "BOOLEANO":
        return "NO"
    return None
