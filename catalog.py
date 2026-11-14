"""Vendor catalog validation, merging and provenance."""
import pandas as pd

REQUIRED=("item_id","item_name","vendor_buy_copper")
OPTIONAL=("vendor_name","vendor_location","stock","vendor_sellback_copper","verified","source_url","checked_at","notes")
def validate_catalog(df):
    missing=set(REQUIRED)-set(df.columns)
    if missing: raise ValueError(f"Missing vendor columns: {sorted(missing)}")
    v=df.copy()
    v["item_id"]=v["item_id"].astype(str).str.strip()
    v["item_name"]=v["item_name"].astype(str).str.strip()
    for c in ("vendor_buy_copper","vendor_sellback_copper","stock"):
        if c in v: v[c]=pd.to_numeric(v[c],errors="coerce")
    v["vendor_buy_copper"]=pd.to_numeric(v["vendor_buy_copper"],errors="coerce")
    bad=v["item_id"].eq("")|v["item_name"].eq("")|v["vendor_buy_copper"].isna()|(v["vendor_buy_copper"]<=0)
    if bad.any(): raise ValueError(f"{bad.sum()} catalog rows have missing IDs/names or invalid NPC purchase prices")
    if "verified" not in v: v["verified"]=False
    v["verified"]=v["verified"].astype(str).str.lower().isin(("true","yes","1"))
    for c in OPTIONAL:
        if c not in v: v[c]=None
    v["checked_at"]=pd.to_datetime(v["checked_at"],errors="coerce",utc=True)
    return v
def catalog_stats(v):
    return {"rows":len(v),"verified":int(v.verified.sum()),"unique_items":v.item_id.nunique()}
