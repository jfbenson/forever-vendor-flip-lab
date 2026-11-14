"""Pure calculations. Monetary inputs/outputs are integer copper except expected values."""
import math
import pandas as pd

REQUIRED_VENDOR = {"item_id", "item_name", "vendor_buy_copper"}
REQUIRED_MARKET = {"item_id", "ah_buyout_copper", "daily_sales", "competing_units"}


def listing_forecast(daily_sales, competing_units, days, confidence, max_units,
                     minimum_sellthrough=0.8):
    """Poisson sell-through forecast for an auction batch.

    Model demand as Poisson(total expected market purchases); each purchase
    chooses uniformly among competing units and our posted units. This is a
    heuristic, not observed buyer behavior. Competitor inventory is assumed
    static; listings and purchases may differ from this model.
    """
    rate = max(0.0, float(daily_sales)) * max(0.0, float(confidence)) * max(0, int(days))
    competition = max(0.0, float(competing_units))
    cap = max(0, int(max_units))
    best = {"list_units": 0, "expected_sold": 0.0, "expected_unsold": 0.0,
            "sellthrough_pct": 0.0, "prob_all_sell_pct": 0.0}
    for n in range(1, cap + 1):
        # Each of our n units has an approximately independent probability of
        # being bought under Poisson thinning. A static inventory approximation.
        probability = -math.expm1(-rate / (competition + n))
        expected_sold = n * probability
        if probability >= minimum_sellthrough:
            best = {"list_units": n, "expected_sold": expected_sold,
                    "expected_unsold": n - expected_sold,
                    "sellthrough_pct": 100 * probability,
                    "prob_all_sell_pct": 100 * probability ** n}
    return best

def compute(vendors, market, days=7, ah_cut=.05, deposit_copper=0,
            demand_discount=.65, max_units=10, capital_copper=100000,
            max_scan_age=24):
    for frame, required, label in [(vendors, REQUIRED_VENDOR, "vendor"), (market, REQUIRED_MARKET, "market")]:
        missing = required - set(frame.columns)
        if missing:
            raise ValueError(f"{label} file missing columns: {sorted(missing)}")
    v = vendors.copy()
    m = market.copy()
    for frame in (v,m):
        frame["item_id"] = frame["item_id"].astype(str).str.strip()
    v = v.drop_duplicates(["item_id","vendor_name"] if "vendor_name" in v else ["item_id"])
    m = m.drop_duplicates("item_id")
    df = v.merge(m, on="item_id", how="inner", suffixes=("","_market"))
    if df.empty:
        return df
    for c in ["vendor_buy_copper", "vendor_sellback_copper", "stock"]:
        if c not in df: df[c] = float("nan")
    for c in ["ah_buyout_copper", "market_price_copper", "daily_sales", "competing_units", "scan_age_hours",
              "vendor_buy_copper", "vendor_sellback_copper", "stock"]:
        if c in df: df[c] = pd.to_numeric(df[c], errors="coerce")
    if "market_price_copper" not in df: df["market_price_copper"] = df["ah_buyout_copper"]
    if "scan_age_hours" not in df: df["scan_age_hours"] = float("nan")
    if "verified" not in df: df["verified"] = False
    df["verified"] = df["verified"].astype(str).str.lower().isin(["true","1","yes"])
    df = df[(df["vendor_buy_copper"] > 0) & (df["ah_buyout_copper"] > 0) &
            (df["daily_sales"] >= 0) & (df["competing_units"] >= 0)].copy()
    if df.empty: return df
    df["resale_copper"] = df[["ah_buyout_copper","market_price_copper"]].min(axis=1)
    df["profit_per_unit_copper"] = df["resale_copper"] * (1-ah_cut) - df["vendor_buy_copper"] - deposit_copper
    df["roi_pct"] = 100 * df["profit_per_unit_copper"] / df["vendor_buy_copper"]
    df["effective_sales_day"] = demand_discount * df["daily_sales"] / (df["competing_units"]+1)
    df["sale_probability"] = 1 - (-df["effective_sales_day"] * days).apply(math.exp)
    # Unsold inventory is marked at vendor liquidation value; assumes one listing attempt.
    df["liquidation_copper"] = df["vendor_sellback_copper"].fillna(0).clip(lower=0)
    df["ev_one_copper"] = (df["sale_probability"] * (df["resale_copper"]*(1-ah_cut)-deposit_copper)
                           + (1-df["sale_probability"]) * df["liquidation_copper"] - df["vendor_buy_copper"])
    # Model independent unit sale chance using Poisson demand shared across listed inventory.
    # The approximation is conservative about competing units but not a calibrated forecast.
    df["units_recommended"] = 0
    df["ev_week_copper"] = 0.0
    for idx, row in df.iterrows():
        stock = max_units if pd.isna(row["stock"]) else max(0, int(row["stock"]))
        budget_units = int(capital_copper // row["vendor_buy_copper"])
        cap = min(max_units, stock, budget_units)
        best_n, best_ev = 0, 0.
        for n in range(1, cap+1):
            rate = demand_discount * row["daily_sales"] * days
            # Expected sales allocated across competitors and our n units.
            per_unit_p = 1 - math.exp(-rate/(row["competing_units"]+n))
            sale_net = row["resale_copper"]*(1-ah_cut)-deposit_copper
            ev = n*(per_unit_p*sale_net + (1-per_unit_p)*row["liquidation_copper"]-row["vendor_buy_copper"])
            if ev > best_ev: best_n, best_ev = n, ev
        df.at[idx,"units_recommended"] = best_n
        df.at[idx,"ev_week_copper"] = best_ev
    forecasts = [listing_forecast(row["daily_sales"], row["competing_units"],
                                  days, demand_discount, min(max_units,
                                  int(capital_copper // row["vendor_buy_copper"])))
                 for _, row in df.iterrows()]
    for field in ("list_units", "expected_sold", "expected_unsold",
                  "sellthrough_pct", "prob_all_sell_pct"):
        df[field] = [forecast[field] for forecast in forecasts]
    # Deposits are paid when listed and are forfeited on unsold listings.
    # This is a single-listing-window estimate, not a guaranteed outcome.
    df["expected_lost_deposits_copper"] = df["expected_unsold"] * deposit_copper
    df["stale"] = df["scan_age_hours"].isna() | (df["scan_age_hours"] > max_scan_age)
    df["data_quality"] = df.apply(lambda r: "Unverified vendor" if not r["verified"] else
                                 ("Stale/unknown AH scan" if r["stale"] else "Verified vendor; fresh AH"), axis=1)
    return df.sort_values("ev_week_copper", ascending=False)
