"""Download, inspect, normalize and archive auction market snapshots."""
import argparse
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import pandas as pd
from ahledger import DEFAULT_URL, fetch, decode, normalize, response_hash

def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS runs (
        digest TEXT PRIMARY KEY, fetched_at TEXT NOT NULL,
        source_url TEXT NOT NULL, row_count INTEGER NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        timestamp TEXT NOT NULL, item_id TEXT NOT NULL,
        ah_buyout_copper REAL, daily_sales REAL, competing_units REAL,
        PRIMARY KEY(timestamp,item_id))""")

def archive(db_path, raw, normalized, source, timestamp=None):
    digest=response_hash(raw)
    stamp=timestamp or datetime.now(timezone.utc).isoformat()
    stamp=pd.Timestamp(stamp)
    if stamp.tzinfo is None: stamp=stamp.tz_localize("UTC")
    stamp=stamp.tz_convert("UTC").isoformat()
    with sqlite3.connect(db_path) as db:
        initialize(db)
        if db.execute("SELECT 1 FROM runs WHERE digest=?",(digest,)).fetchone():
            return False,0
        db.executemany("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)",
            [(stamp,str(r.item_id),float(r.ah_buyout_copper),float(r.daily_sales),
              float(r.competing_units)) for r in normalized.itertuples(index=False)])
        db.execute("INSERT INTO runs VALUES (?,?,?,?)",(digest,stamp,source,len(normalized)))
        db.commit()
    return True,len(normalized)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--url",default=DEFAULT_URL)
    p.add_argument("--raw-file",help="Use a previously downloaded API response")
    p.add_argument("--mapping",help="JSON file with mapping and daily_sales_scale")
    p.add_argument("--db",default="market_history.sqlite")
    p.add_argument("--raw-dir",default="raw_responses")
    p.add_argument("--timestamp",help="Actual provider scan timestamp, if known")
    p.add_argument("--inspect",action="store_true",help="Show response fields and sample")
    p.add_argument("--export",help="Export historical snapshots as CSV")
    args=p.parse_args()
    if args.export:
        with sqlite3.connect(args.db) as db:
            initialize(db)
            pd.read_sql_query("SELECT * FROM snapshots ORDER BY timestamp,item_id",db).to_csv(args.export,index=False)
        print("Exported",args.export)
        return
    raw=Path(args.raw_file).read_bytes() if args.raw_file else fetch(args.url)
    folder=Path(args.raw_dir);folder.mkdir(parents=True,exist_ok=True)
    dest=folder/(response_hash(raw)+".raw")
    dest.write_bytes(raw)
    print("Raw response saved:",dest)
    try: frame=decode(raw)
    except Exception as exc:
        print("Could not decode response:",exc)
        raise SystemExit(2)
    print("Columns:",list(frame.columns),"Rows:",len(frame))
    print(frame.head(2).to_string(index=False,max_cols=12))
    if args.inspect or not args.mapping:
        print("Inspection only; supply --mapping with verified field names and units to archive.")
        return
    config=json.loads(Path(args.mapping).read_text())
    normalized=normalize(frame,config["mapping"],float(config.get("daily_sales_scale",1)))
    if normalized.empty: raise SystemExit("No valid normalized rows")
    stored,count=archive(args.db,raw,normalized,args.url,args.timestamp)
    print(("Archived" if stored else "Skipped unchanged response"),count,"rows")
    normalized.to_csv("market_latest.csv",index=False)
    print("Latest normalized market saved: market_latest.csv")

if __name__=="__main__": main()
