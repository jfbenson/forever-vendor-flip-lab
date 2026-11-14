"""Append normalized AH snapshot CSV to a local SQLite history store.

Usage:
    python collect.py --input market.csv --db market_history.sqlite
    python collect.py --export history.csv --db market_history.sqlite

Run after each fresh market download, preferably every 3-6 hours.
"""
import argparse
import sqlite3
from datetime import datetime, timezone
import pandas as pd

COLUMNS = ["item_id", "ah_buyout_copper", "daily_sales", "competing_units"]
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input")
    p.add_argument("--export")
    p.add_argument("--db",default="market_history.sqlite")
    p.add_argument("--timestamp",help="ISO 8601 time of actual source scan, not time of import")
    args=p.parse_args()
    if not args.input and not args.export: p.error("provide --input or --export")
    with sqlite3.connect(args.db) as db:
        db.execute("""CREATE TABLE IF NOT EXISTS snapshots (
          timestamp TEXT NOT NULL, item_id TEXT NOT NULL,
          ah_buyout_copper REAL, daily_sales REAL, competing_units REAL,
          PRIMARY KEY (timestamp,item_id))""")
        if args.input:
            df=pd.read_csv(args.input)
            missing=set(COLUMNS)-set(df.columns)
            if missing: p.error(f"missing columns: {sorted(missing)}")
            stamp=args.timestamp or datetime.now(timezone.utc).isoformat()
            stamp=pd.Timestamp(stamp).tz_convert("UTC").isoformat() if pd.Timestamp(stamp).tzinfo else pd.Timestamp(stamp).tz_localize("UTC").isoformat()
            count=0
            for row in df[COLUMNS].itertuples(index=False,name=None):
                db.execute("INSERT OR REPLACE INTO snapshots VALUES (?,?,?,?,?)",(stamp,str(row[0]),*map(float,row[1:])))
                count+=1
            db.commit()
            print(f"Stored {count} item observations at {stamp} in {args.db}")
        if args.export:
            df=pd.read_sql_query("SELECT * FROM snapshots ORDER BY timestamp,item_id",db)
            df.to_csv(args.export,index=False)
            print(f"Exported {len(df)} observations to {args.export}")
if __name__=="__main__": main()
