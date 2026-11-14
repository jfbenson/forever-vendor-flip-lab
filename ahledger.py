"""AHledger ingestion with explicit field mapping: do not guess API units/schema."""
import csv
import hashlib
import io
import json
from pathlib import Path
from datetime import datetime, timezone
import requests
import pandas as pd

DEFAULT_URL = "https://api.ahledger.com/v1/pricetable/forever.normal.alliance.us"
FIELDS = ("item_id", "ah_buyout_copper", "daily_sales", "competing_units")
OPTIONAL = ("market_price_copper", "scan_age_hours")
def fetch(url=DEFAULT_URL, timeout=30):
    if not url.startswith("https://api.ahledger.com/"):
        raise ValueError("Only HTTPS api.ahledger.com URLs are allowed")
    r = requests.get(url, timeout=timeout, headers={"Accept":"application/json, text/plain, text/csv, */*",
                                                     "User-Agent":"ForeverVendorFlipLab/0.4"})
    r.raise_for_status()
    if not r.content: raise ValueError("Empty API response")
    return r.content

def decode(raw):
    text=raw.decode("utf-8-sig")
    try:
        obj=json.loads(text)
    except json.JSONDecodeError:
        obj=None
    if obj is not None:
        if isinstance(obj,list): return pd.DataFrame(obj)
        if isinstance(obj,dict):
            for key in ("items","data","results","prices","rows"):
                if isinstance(obj.get(key),list): return pd.DataFrame(obj[key])
            raise ValueError("JSON object has no recognized row array; inspect the raw response")
        raise ValueError("Unsupported JSON response")
    if text.startswith("AHL1|"):
        lines = text.splitlines()
        header = lines[0].split("|")
        if len(header) != 4 or header[0] != "AHL1":
            raise ValueError("Malformed AHL1 header")
        _, realm, timestamp, declared_count = header
        if not realm or not timestamp.isdecimal() or not declared_count.isdecimal():
            raise ValueError("Invalid AHL1 realm, timestamp, or record count")
        rows = []
        seen = set()
        for line_number, line in enumerate(lines[1:], start=2):
            cells = line.split(":")
            if len(cells) != 9 or not all(cell.isdecimal() for cell in cells):
                raise ValueError(f"Malformed AHL1 record at line {line_number}")
            values = [int(cell) for cell in cells]
            if values[0] in seen:
                raise ValueError(f"Duplicate AHL1 item ID at line {line_number}")
            seen.add(values[0])
            rows.append(values)
        if len(rows) != int(declared_count):
            raise ValueError(f"AHL1 count mismatch: expected {declared_count}, got {len(rows)}")
        frame = pd.DataFrame(rows, columns=["item_id"] + [f"field_{i}" for i in range(1, 9)])
        frame.attrs.update(format="AHL1", realm=realm, timestamp=int(timestamp))
        return frame
    # Try delimited text with header. Unknown formats must fail visibly.
    sample=text[:4096]
    try: dialect=csv.Sniffer().sniff(sample, delimiters=",;\\t|")
    except csv.Error: raise ValueError("Unrecognized response format; inspect saved raw file")
    df=pd.read_csv(io.StringIO(text),sep=dialect.delimiter)
    if df.empty: raise ValueError("No rows found")
    return df

def normalize(df, mapping, daily_sales_scale=1.0):
    """Mapping maps canonical column name -> actual response column.
    daily_sales_scale must be explicit (e.g. 0.1 if API encodes tenths).
    """
    missing=[f for f in FIELDS if f not in mapping or mapping[f] not in df.columns]
    if missing: raise ValueError(f"Missing field mappings or source columns: {missing}; found {list(df.columns)}")
    if daily_sales_scale <= 0: raise ValueError("daily_sales_scale must be positive")
    result=pd.DataFrame({k:df[src] for k,src in mapping.items() if k in FIELDS+OPTIONAL and src in df.columns})
    result["item_id"]=result["item_id"].astype(str).str.strip()
    for k in FIELDS[1:]:
        result[k]=pd.to_numeric(result[k],errors="coerce")
    if "market_price_copper" in result:
        result["market_price_copper"]=pd.to_numeric(result["market_price_copper"],errors="coerce")
    result["daily_sales"] *= daily_sales_scale
    result=result.dropna(subset=list(FIELDS))
    result=result[(result.item_id!="") & (result.ah_buyout_copper>0) &
                  (result.daily_sales>=0) & (result.competing_units>=0)]
    return result.drop_duplicates("item_id",keep="last").reset_index(drop=True)

def response_hash(raw):
    return hashlib.sha256(raw).hexdigest()

# Official AHL1 layout: https://ahledger.com/developers
# The quantity field counts listed units, not auctions. It is a competition proxy.
AHL1_COLUMNS = ("median_copper", "min_buyout_copper", "listed_quantity",
                "median_7d_copper", "median_30d_copper", "low_30d_copper",
                "high_30d_copper", "estimated_sales_per_day_x10")

def normalize_ahl1(frame, now=None):
    """Convert documented AHL1 columns into the ranking engine's market schema.

    AHledger's sold/day is estimated from scans, not confirmed sales.
    Listed quantity is used as a proxy for competing units.
    """
    if frame.attrs.get("format") != "AHL1":
        raise ValueError("Expected a decoded AHL1 price table")
    expected = ["item_id"] + [f"field_{i}" for i in range(1, 9)]
    if any(c not in frame.columns for c in expected):
        raise ValueError("Missing AHL1 source columns")
    result = frame[expected].copy()
    result.columns = ["item_id"] + list(AHL1_COLUMNS)
    for col in AHL1_COLUMNS:
        result[col] = pd.to_numeric(result[col], errors="coerce")
    result["ah_buyout_copper"] = result["min_buyout_copper"]
    result["market_price_copper"] = result["median_7d_copper"].where(
        result["median_7d_copper"] > 0, result["median_copper"])
    result["daily_sales"] = result["estimated_sales_per_day_x10"] / 10.0
    result["competing_units"] = result["listed_quantity"]
    observed = datetime.fromtimestamp(frame.attrs["timestamp"], tz=timezone.utc)
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    result["scan_age_hours"] = max(0.0, (now - observed).total_seconds() / 3600)
    result = result.dropna(subset=["item_id", "ah_buyout_copper",
                                   "daily_sales", "competing_units"])
    result = result[(result.ah_buyout_copper > 0) &
                    (result.daily_sales >= 0) &
                    (result.competing_units >= 0)]
    return result.reset_index(drop=True)
