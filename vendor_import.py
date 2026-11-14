"""Import Classic NPC vendor inventories from the documented WoWDB API.

Prices are Classic reference data, not Forever-confirmed. Only copper-only
purchases are accepted; no honor, barter, or reputation discounts inferred.
"""
import time
import requests
import pandas as pd

BASE = "https://api.wowdb.assemblee-defias.fr/v1/classic/npcs"
COLUMNS = ["item_id", "item_name", "vendor_name", "vendor_location",
           "vendor_buy_copper", "vendor_sellback_copper", "stock", "verified",
           "source_url", "checked_at", "notes"]

def _get(session, url, params=None):
    r = session.get(url, params=params, timeout=20, headers={"User-Agent": "ForeverVendorFlipLab/0.5"})
    r.raise_for_status()
    obj = r.json()
    if not isinstance(obj, dict):
        raise ValueError("Unexpected WoWDB response")
    return obj

def import_npcs(npc_ids, session=None, pause=0.2, max_pages=20):
    """Fetch selected NPC IDs and all paginated vendor items, with bounded calls."""
    session = session or requests.Session()
    rows = []
    for npc_id in dict.fromkeys(int(i) for i in npc_ids):
        if npc_id <= 0:
            raise ValueError("NPC IDs must be positive")
        npc = _get(session, f"{BASE}/{npc_id}")
        name = npc.get("english_name") or npc.get("name") or f"NPC {npc_id}"
        zones = npc.get("zones") or []
        location = ", ".join(str(z.get("name")) for z in zones if z.get("name"))
        cursor = None
        for page in range(max_pages):
            params = {"limit": 100}
            if cursor: params["cursor"] = cursor
            obj = _get(session, f"{BASE}/{npc_id}/sells", params)
            for entry in obj.get("data", []):
                item = entry.get("item") or {}
                cost = entry.get("cost") or {}
                money = cost.get("money")
                if not isinstance(money, int) or money <= 0:
                    continue
                if any(cost.get(k) for k in ("honor", "arena", "personal_rating", "items", "currencies")):
                    continue
                item_id = item.get("id")
                if not isinstance(item_id, int):
                    continue
                rows.append({"item_id": str(item_id), "item_name": item.get("name") or f"Item {item_id}",
                    "vendor_name": name, "vendor_location": location,
                    "vendor_buy_copper": money, "vendor_sellback_copper": None,
                    "stock": None, "verified": False,
                    "source_url": f"{BASE}/{npc_id}/sells", "checked_at": "",
                    "notes": "Classic reference price; NOT verified on Forever. NPC discounts/requirements may differ."})
            if not obj.get("has_more"):
                break
            next_cursor = obj.get("next_cursor")
            if not next_cursor or next_cursor == cursor:
                raise ValueError("Invalid WoWDB pagination cursor")
            cursor = next_cursor
            if pause: time.sleep(pause)
        else:
            raise ValueError(f"Exceeded pagination limit for NPC {npc_id}")
        if pause: time.sleep(pause)
    return pd.DataFrame(rows, columns=COLUMNS)

def merge_catalog(existing, incoming):
    """Keep existing user edits, but restore missing metadata from imports.

    In particular, older workbench saves dropped the Kaydee faction and NPC
    identifiers. Reimporting the addon should recover these fields without
    overwriting confirmed prices or other edits.
    """
    if existing is None or existing.empty:
        return incoming.copy()
    old = existing.copy()
    new = incoming.copy()
    keys = ["item_id", "vendor_name"]
    old["item_id"] = old["item_id"].astype(str)
    new["item_id"] = new["item_id"].astype(str)
    # Enrich existing rows, keeping their prices and verified flags.
    metadata = ["faction", "npc_id", "limited_stock"]
    lookup = new.drop_duplicates(keys).set_index(keys)
    indexed = old.set_index(keys)
    for col in metadata:
        if col not in indexed:
            indexed[col] = None
        if col in lookup:
            indexed[col] = indexed[col].combine_first(lookup[col])
    old = indexed.reset_index()
    existing_keys = pd.MultiIndex.from_frame(old[keys])
    additions = new[~pd.MultiIndex.from_frame(new[keys]).isin(existing_keys)]
    return pd.concat([old, additions], ignore_index=True)

def parse_addon_csv(file):
    """Explicit CSV bridge; no unverified assumptions about /kvid export format."""
    frame = pd.read_csv(file, dtype={"item_id": str})
    required = {"item_id", "item_name", "vendor_name", "vendor_buy_copper"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"CSV needs columns: {sorted(missing)}. Kaydee's raw /kvid export format is not yet confirmed.")
    for column in COLUMNS:
        if column not in frame:
            frame[column] = False if column == "verified" else None
    frame["verified"] = False
    frame["notes"] = frame["notes"].fillna("").astype(str) + " | Imported addon CSV; verify source and prices in Forever."
    return frame[COLUMNS]
