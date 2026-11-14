"""Read Kaydee's bundled Forever vendor data from a local addon folder or ZIP.

No bundled addon content is distributed with this repository. Parsing is limited
to the known Data_Forever.lua literal-table format, never executing Lua.
"""
from pathlib import Path
import re
import zipfile
import pandas as pd

def _fields(body):
    out, start, depth, quoted, escaped = [], 0, 0, False, False
    for i, ch in enumerate(body):
        if quoted:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': quoted = False
        elif ch == '"': quoted = True
        elif ch == "{": depth += 1
        elif ch == "}": depth -= 1
        elif ch == "," and depth == 0:
            out.append(body[start:i].strip())
            start = i + 1
    out.append(body[start:].strip())
    return out

def _number(value):
    return int(value) if re.fullmatch(r"\d+", value or "") else None

def _list(value):
    if not value.startswith("{") or not value.endswith("}"):
        return []
    return [int(x) for x in re.findall(r"\d+", value[1:-1])]

def _overrides(value):
    if not value.startswith("{"): return {}
    return {int(k): int(v) for k, v in re.findall(r"\[(\d+)\]\s*=\s*(\d+)", value)}

def _unquote(value):
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1].replace(r'\"', '"')
    return ""

def _section(text, name):
    match = re.search(r"ns\." + name + r"\s*=\s*\{", text)
    if not match: raise ValueError(f"Missing {name} in Forever addon data")
    start = match.end()
    depth = 1
    quoted = escaped = False
    for i in range(start, len(text)):
        ch = text[i]
        if quoted:
            if escaped: escaped = False
            elif ch == "\\": escaped = True
            elif ch == '"': quoted = False
        elif ch == '"': quoted = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return text[start:i]
    raise ValueError(f"Unterminated {name}")

def _records(section):
    for line in section.splitlines():
        match = re.match(r"\s*\[(\d+)\]\s*=\s*\{(.*)\}\s*,?\s*$", line)
        if match: yield int(match.group(1)), _fields(match.group(2))

def read_forever_text(text):
    npcs = {}
    for npc_id, fields in _records(_section(text, "DATA_NPCS")):
        if len(fields) < 3: continue
        npcs[npc_id] = {"name": _unquote(fields[0]), "faction": _unquote(fields[2]),
                        "zone": _unquote(fields[6]) if len(fields) > 6 else ""}
    rows = []
    for item_id, f in _records(_section(text, "DATA_ITEMS")):
        if len(f) < 13: continue
        name, base_price = _unquote(f[0]), _number(f[5])
        vendors = _list(f[12])
        limited = set(_list(f[13])) if len(f) > 13 else set()
        requirements = f[14] if len(f) > 14 else "nil"
        overrides = _overrides(f[15]) if len(f) > 15 else {}
        special = _overrides(f[16]) if len(f) > 16 else {}
        # Special currencies and unknown prices cannot be compared to copper AH prices.
        for npc_id in vendors:
            price = overrides.get(npc_id, base_price)
            if not price or npc_id in special: continue
            npc = npcs.get(npc_id, {})
            rows.append({"item_id": str(item_id), "item_name": name,
                "vendor_name": npc.get("name") or f"NPC {npc_id}",
                "vendor_location": npc.get("zone", ""),
                "vendor_buy_copper": price, "vendor_sellback_copper": None,
                "stock": None, "verified": False,
                "source_url": "", "checked_at": "",
                "notes": f"Kaydee bundled Forever data; NPC {npc_id}; "
                         + ("limited stock; " if npc_id in limited else "")
                         + ("requirements may apply; " if requirements != "nil" else "")
                         + "not personally verified; discounts may apply",
                "npc_id": npc_id, "faction": npc.get("faction", ""),
                "limited_stock": npc_id in limited})
    if not rows: raise ValueError("No usable vendor listings in Data_Forever.lua")
    return pd.DataFrame(rows)

def import_forever_addon(source):
    path = Path(source)
    if path.is_dir():
        candidates = list(path.rglob("Data_Forever.lua"))
        if len(candidates) != 1: raise ValueError("Expected exactly one Data_Forever.lua")
        raw = candidates[0].read_bytes()
    elif zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            candidates = [name for name in archive.namelist() if name.endswith("/Data_Forever.lua")]
            if len(candidates) != 1: raise ValueError("Expected exactly one Data_Forever.lua in ZIP")
            raw = archive.read(candidates[0])
    else:
        raise ValueError("Select a Kaydee addon folder or ZIP")
    return read_forever_text(raw.decode("utf-8-sig"))
