"""Faction filtering for Kaydee's A, H and AH vendor codes."""
import pandas as pd

def _codes(vendors):
    if "faction" not in vendors.columns:
        return pd.Series("", index=vendors.index)
    return vendors["faction"].fillna("").astype(str).str.strip().str.upper()

def filter_vendors(vendors, choice):
    if choice == "All":
        return vendors.copy()
    if choice not in ("Alliance", "Horde"):
        raise ValueError(f"Unknown faction selection: {choice}")
    code = "A" if choice == "Alliance" else "H"
    faction = _codes(vendors)
    return vendors[faction.isin((code, "AH"))].copy()

def faction_counts(vendors):
    faction = _codes(vendors)
    return {"alliance": int(faction.isin(("A", "AH")).sum()),
            "horde": int(faction.isin(("H", "AH")).sum()),
            "shared": int(faction.eq("AH").sum()),
            "unknown": int((~faction.isin(("A", "H", "AH"))).sum())}
