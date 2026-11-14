"""Durable local market cache. Provider timestamps determine freshness."""
from datetime import datetime, timezone
from pathlib import Path
import os
import pandas as pd
from ahledger import DEFAULT_URL, decode, fetch, normalize_ahl1

DATA_DIR = Path(__file__).resolve().parent / "local_data"
RAW_PATH = DATA_DIR / "market_ahl1.raw"
VENDOR_PATH = DATA_DIR / "vendors.csv"

def read_market(path=RAW_PATH, now=None):
    path = Path(path)
    if not path.exists():
        return None, None
    frame = decode(path.read_bytes())
    if frame.attrs.get("format") != "AHL1":
        raise ValueError("Cached market is not AHL1")
    return normalize_ahl1(frame, now=now), frame.attrs["timestamp"]

def load_market(url=DEFAULT_URL, refresh_hours=6, force=False, fetcher=fetch,
                path=RAW_PATH, now=None):
    """Return (market, status). Falls back to last valid local data if offline."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    path = Path(path)
    cached, stamp = None, None
    cache_error = None
    try:
        cached, stamp = read_market(path, now)
    except (ValueError, UnicodeError, OSError) as exc:
        cache_error = str(exc)
    age_hours = (now.timestamp() - stamp) / 3600 if stamp is not None else None
    if cached is not None and not force and age_hours is not None and age_hours < refresh_hours and age_hours >= 0:
        return cached, {"source": "local cache", "timestamp": stamp, "age_hours": age_hours}
    try:
        raw = fetcher(url)
        decoded = decode(raw)
        if decoded.attrs.get("format") != "AHL1":
            raise ValueError("Provider returned unsupported market format")
        if decoded.attrs.get("realm") != "forever/normal/alliance/us":
            raise ValueError("Unexpected AHledger realm")
        market = normalize_ahl1(decoded, now)
        if market.empty:
            raise ValueError("Provider returned no usable market records")
        new_stamp = decoded.attrs["timestamp"]
        # Never replace a newer snapshot with older provider data.
        if stamp is not None and new_stamp < stamp:
            return cached, {"source": "local cache (provider snapshot older)", "timestamp": stamp,
                            "age_hours": age_hours}
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix(".tmp")
        temp.write_bytes(raw)
        os.replace(temp, path)
        return market, {"source": "AHledger (saved locally)", "timestamp": new_stamp,
                        "age_hours": max(0, (now.timestamp() - new_stamp) / 3600)}
    except Exception as exc:
        if cached is not None:
            return cached, {"source": "offline fallback", "timestamp": stamp,
                            "age_hours": age_hours, "warning": str(exc)}
        raise RuntimeError(f"Unable to load AHledger market (no local cache): {exc}; cached error: {cache_error}") from exc

def read_vendors(path=VENDOR_PATH):
    path = Path(path)
    return pd.read_csv(path, dtype={"item_id": str}) if path.exists() else None

def save_vendors(frame, path=VENDOR_PATH):
    from catalog import validate_catalog
    valid = validate_catalog(frame)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    valid.to_csv(temp, index=False)
    os.replace(temp, path)
    return valid
