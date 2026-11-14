"""Classify NPC stock independently of market auction quantities."""
import pandas as pd

def stock_category(vendors):
    """Return unlimited, limited, or unknown for each vendor listing.

    Kaydee's limited_stock flag is authoritative only when populated.
    A numeric stock cap overrides any unlimited flag.
    Blank stock without a known limited_stock flag is unknown, not unlimited.
    """
    categories = pd.Series("unknown", index=vendors.index, dtype="object")
    if "limited_stock" in vendors:
        raw = vendors["limited_stock"].astype("string").str.strip().str.lower()
        categories.loc[raw.isin(["true", "1", "yes"])] = "limited"
        categories.loc[raw.isin(["false", "0", "no"])] = "unlimited"
    if "stock" in vendors:
        stock = pd.to_numeric(vendors["stock"], errors="coerce")
        categories.loc[stock.notna()] = "limited"
    return categories

def filter_vendor_stock(vendors, selection):
    if selection == "All stock types":
        return vendors.copy()
    mapping = {"Unlimited only": "unlimited", "Limited only": "limited",
               "Unknown only": "unknown"}
    if selection not in mapping:
        raise ValueError(f"Unknown stock selection: {selection}")
    return vendors.loc[stock_category(vendors).eq(mapping[selection])].copy()

def stock_counts(vendors):
    return stock_category(vendors).value_counts().reindex(
        ["unlimited", "limited", "unknown"], fill_value=0).to_dict()
