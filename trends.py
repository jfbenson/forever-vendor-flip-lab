"""Historical market trend analytics. Input: one row per item per timestamp."""
import numpy as np
import pandas as pd

def analyze_trends(history, vendor_catalog=None, window_days=7, baseline_days=None,
                   fee=.05, min_coverage=.5):
    required={"timestamp","item_id","ah_buyout_copper","daily_sales","competing_units"}
    missing=required-set(history.columns)
    if missing: raise ValueError(f"History missing columns: {sorted(missing)}")
    h=history.copy()
    h["timestamp"]=pd.to_datetime(h["timestamp"],utc=True,errors="coerce")
    h=h.dropna(subset=["timestamp"]).copy()
    h["item_id"]=h["item_id"].astype(str)
    for c in ["ah_buyout_copper","daily_sales","competing_units"]:
        h[c]=pd.to_numeric(h[c],errors="coerce")
    h=h.dropna(subset=["ah_buyout_copper","daily_sales","competing_units"])
    h=h[(h["ah_buyout_copper"]>0)&(h["daily_sales"]>=0)&(h["competing_units"]>=0)]
    if h.empty: return pd.DataFrame()
    h=h.sort_values("timestamp").drop_duplicates(["item_id","timestamp"],keep="last")
    # Use the latest observed timestamp as anchor, not wall-clock time (demo/offline safe).
    anchor=h["timestamp"].max()
    period=pd.Timedelta(days=window_days)
    baseline=pd.Timedelta(days=baseline_days or window_days)
    recent=h[(h.timestamp>anchor-period)&(h.timestamp<=anchor)]
    previous=h[(h.timestamp>anchor-period-baseline)&(h.timestamp<=anchor-period)]
    if recent.empty or previous.empty: return pd.DataFrame()
    def agg(frame):
        # Multiple daily-sales estimates per window: median estimate, not sum.
        out=frame.groupby("item_id").agg(
            sales=("daily_sales","median"),
            price=("ah_buyout_copper","median"),
            competition=("competing_units","median"),
            observations=("timestamp","count"),
            first=("timestamp","min"),
            last=("timestamp","max"))
        return out
    r=agg(recent).add_prefix("recent_")
    p=agg(previous).add_prefix("previous_")
    df=r.join(p,how="inner")
    if df.empty: return df
    # Coverage = observed span relative to window; single observation has zero span.
    df["recent_coverage"]=((df.recent_last-df.recent_first).dt.total_seconds()/period.total_seconds()).clip(0,1)
    df["previous_coverage"]=((df.previous_last-df.previous_first).dt.total_seconds()/baseline.total_seconds()).clip(0,1)
    df["coverage_ok"]=(df.recent_coverage>=min_coverage)&(df.previous_coverage>=min_coverage)&(df.recent_observations>=2)&(df.previous_observations>=2)
    df["demand_change_pct"]=np.where(df.previous_sales>0,100*(df.recent_sales/df.previous_sales-1),np.nan)
    df["price_change_pct"]=np.where(df.previous_price>0,100*(df.recent_price/df.previous_price-1),np.nan)
    df["competition_change_pct"]=np.where(df.previous_competition>0,100*(df.recent_competition/df.previous_competition-1),np.nan)
    df["velocity_per_listing_recent"]=df.recent_sales/(df.recent_competition+1)
    df["velocity_per_listing_previous"]=df.previous_sales/(df.previous_competition+1)
    df["velocity_change_pct"]=np.where(df.velocity_per_listing_previous>0,100*(df.velocity_per_listing_recent/df.velocity_per_listing_previous-1),np.nan)
    df["net_profit_change_copper"] = np.nan
    df["recent_profit_copper"] = np.nan
    if vendor_catalog is not None and not vendor_catalog.empty:
        v=vendor_catalog.copy()
        v["item_id"]=v["item_id"].astype(str)
        v=v.drop_duplicates("item_id").set_index("item_id")
        df=df.join(v[["vendor_buy_copper"]],how="left")
        df["recent_profit_copper"]=df.recent_price*(1-fee)-df.vendor_buy_copper
        df["previous_profit_copper"]=df.previous_price*(1-fee)-df.vendor_buy_copper
        df["net_profit_change_copper"]=df.recent_profit_copper-df.previous_profit_copper
    df["signal_score"]=(df["velocity_change_pct"].clip(-100,200).fillna(0)*.55+
                        df["price_change_pct"].clip(-100,200).fillna(0)*.3-
                        df["competition_change_pct"].clip(-100,200).fillna(0)*.15)
    df.loc[~df.coverage_ok,"signal_score"]=np.nan
    return df.reset_index().sort_values("signal_score",ascending=False,na_position="last")
