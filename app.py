import io
import pandas as pd
import requests
import streamlit as st
from engine import compute
from trends import analyze_trends
from catalog import validate_catalog, catalog_stats

st.set_page_config(page_title="Forever Vendor Flip Lab", layout="wide")
st.title("⚒️ Forever Vendor Flip Lab")
st.caption("US Normal • Alliance | Research tool, not guaranteed sales. Example records are fictional.")

with st.sidebar:
    st.header("Market & assumptions")
    days = st.slider("Forecast horizon (days)", 1, 30, 7)
    cut = st.slider("AH cut (%)", 0, 15, 5) / 100
    discount = st.slider("Demand confidence factor (%)", 10, 100, 65) / 100
    deposit = st.number_input("Estimated listing deposit (copper/unit)", min_value=0, value=0, step=10)
    capital = st.number_input("Capital budget (gold)", min_value=1, value=20, step=5)
    max_units = st.slider("Max units per item", 1, 100, 10)
    max_age = st.slider("Max scan age (hours)", 1, 168, 24)

st.subheader("1 · Load market data")
st.write("Upload normalized market CSV, or try downloading the documented AHledger endpoint. The endpoint's live response schema has not been verified; if it is not CSV with these headers, normalize it before upload.")
url = st.text_input("Market endpoint", "https://api.ahledger.com/v1/pricetable/forever.normal.alliance.us")
uploaded_market = st.file_uploader("Market CSV", type="csv", key="market")
uploaded_vendor = st.file_uploader("Vendor catalog CSV", type="csv", key="vendor")
use_demo = st.checkbox("Use fictional demo data", value=True)
market, vendors = None, None
if uploaded_market:
    market = pd.read_csv(uploaded_market)
elif use_demo:
    market = pd.read_csv("sample_market.csv")
if uploaded_vendor:
    vendors = pd.read_csv(uploaded_vendor)
elif use_demo:
    vendors = pd.read_csv("sample_vendors.csv")
if st.button("Test market endpoint"):
    try:
        response = requests.get(url, timeout=15, headers={"User-Agent":"ForeverVendorFlipLab/0.1"})
        st.write(f"HTTP {response.status_code}; content type: {response.headers.get('content-type','unknown')}")
        st.code(response.text[:1000])
        response.raise_for_status()
        st.download_button("Download raw response", response.content, file_name="ahledger_raw.txt")
    except requests.RequestException as exc:
        st.error(f"Connection failed: {exc}")
if vendors is not None:
    try:
        vendors = validate_catalog(vendors)
    except ValueError as exc:
        st.error(f"Vendor catalog validation: {exc}")
        st.stop()
if market is None or vendors is None:
    st.info("Upload both CSVs, or enable demo mode.")
    st.stop()

with st.expander("Required CSV columns and meaning"):
    st.code("vendors: item_id,item_name,vendor_name,vendor_location,vendor_buy_copper,vendor_sellback_copper,stock,verified\nmarket: item_id,ah_buyout_copper,market_price_copper,daily_sales,competing_units,scan_age_hours")
    st.write("Vendor cost means **NPC purchase price**, never NPC sellback value. Unknown stock may be left blank. Set verified=true only for Forever-confirmed vendor prices.")
try:
    result = compute(vendors, market, days, cut, deposit, discount, max_units, int(capital*10000), max_age)
except Exception as exc:
    st.error(f"Data validation error: {exc}")
    st.stop()
if result.empty:
    st.warning("No matching valid item IDs in both datasets.")
    st.stop()

st.subheader("API response mapping workbench")
with st.expander("Inspect and map an AHledger response (no assumptions about provider fields)"):
    raw_upload=st.file_uploader("Upload raw AHledger response",type=["json","csv","txt"],key="raw_api")
    if raw_upload is not None:
        from ahledger import decode, normalize
        try:
            source=decode(raw_upload.getvalue())
            st.write(f"Decoded {len(source)} records; available fields: {list(source.columns)}")
            st.dataframe(source.head(5),hide_index=True)
            required=["item_id","ah_buyout_copper","daily_sales","competing_units"]
            optional=["market_price_copper","scan_age_hours"]
            mappings={}
            for canonical in required+optional:
                options=["(not mapped)"]+list(source.columns)
                guess=canonical if canonical in source.columns else "(not mapped)"
                choice=st.selectbox(f"{canonical} source field",options,index=options.index(guess),key="map_"+canonical)
                if choice!="(not mapped)": mappings[canonical]=choice
            scale=st.number_input("Sales/day multiplier (verify provider units)",value=1.0,min_value=0.000001,format="%.6f")
            if st.button("Validate mapping"):
                try:
                    mapped=normalize(source,mappings,scale)
                    st.success(f"Normalized {len(mapped)} item records.")
                    st.dataframe(mapped.head(10),hide_index=True)
                    st.download_button("Download normalized market CSV",mapped.to_csv(index=False),file_name="market_latest.csv",mime="text/csv")
                    st.download_button("Download reusable mapping JSON",__import__("json").dumps({"mapping":mappings,"daily_sales_scale":scale},indent=2),file_name="mapping.json",mime="application/json")
                except ValueError as exc: st.error(str(exc))
        except Exception as exc: st.error(f"Could not decode response: {exc}")

st.subheader("2 · Filter and rank")
a,b,c,d = st.columns(4)
min_profit = a.number_input("Min net profit (silver/unit)", min_value=0., value=0., step=1.)
min_sales = b.number_input("Min estimated market sales/day", min_value=0., value=0., step=.1)
only_fresh = c.checkbox("Fresh scans only", value=False)
only_verified = d.checkbox("Verified vendors only", value=False)
f = result[(result["profit_per_unit_copper"] >= min_profit*100) & (result["daily_sales"] >= min_sales)]
if only_fresh: f = f[~f["stale"]]
if only_verified: f = f[f["verified"]]
st.caption("Click any column heading to sort. The weekly EV is an approximate modeled return, not observed profit.")
def gold(s): return (s/10000).round(3)
show = pd.DataFrame({
    "Item": f["item_name"], "Vendor": f.get("vendor_name", pd.Series("",index=f.index)),
    "Vendor cost (g)": gold(f["vendor_buy_copper"]),
    "AH resale (g)": gold(f["resale_copper"]),
    "Profit/unit (g)": gold(f["profit_per_unit_copper"]),
    "ROI (%)": f["roi_pct"].round(1),
    "Market sales/day": f["daily_sales"].round(2),
    "Competing units": f["competing_units"],
    "P(sell 1 in horizon)": (100*f["sale_probability"]).round(1),
    "EV one unit (g)": gold(f["ev_one_copper"]),
    "Buy units": f["units_recommended"],
    "Weekly EV (g)": gold(f["ev_week_copper"]),
    "Scan age (h)": f["scan_age_hours"],
    "Quality": f["data_quality"],
})
st.dataframe(show, use_container_width=True, hide_index=True)
st.download_button("Export filtered results (CSV)", show.to_csv(index=False), file_name="forever_vendor_flips.csv", mime="text/csv")
m1,m2,m3=st.columns(3)
m1.metric("Candidate items", len(f))
m2.metric("Total modeled weekly EV (g)", f["ev_week_copper"].sum().round(0)/10000)
m3.metric("Suggested purchase spend (g)", (f["units_recommended"]*f["vendor_buy_copper"]).sum().round(0)/10000)
st.warning("Per-item budget caps are applied independently. Total recommended purchases may exceed your overall budget; this is not yet a portfolio optimizer.")
st.subheader("3 · Opportunity overview")
st.bar_chart(show.set_index("Item")["Weekly EV (g)"])
st.info("Sale probabilities assume Poisson demand, a demand-confidence discount, and equal competition across listed units. AH listings disappearing are not confirmed sales. Validate with real completed sales before buying in bulk.")

st.divider()
st.header("4 · Demand & profit momentum")
st.write("Compare 1, 2, 3, 5 or 7 days against the preceding equal-length period. A 7-day comparison requires 14 days of history; shorter windows are more useful during launch week.")
history_upload = st.file_uploader("Historical snapshots CSV",type="csv",key="history")
st.caption("Run python sync.py --inspect to inspect the provider format; then supply a verified mapping and schedule sync.py. Export SQLite history with python sync.py --export history.csv.")
demo_history = st.checkbox("Use fictional historical demo",value=use_demo)
window = st.selectbox("Comparison window",options=[1,2,3,5,7],format_func=lambda x: f"Last {x} day(s) vs preceding {x} day(s)")
history = pd.read_csv(history_upload) if history_upload else (pd.read_csv("sample_history.csv") if demo_history else None)
if history is not None:
    try:
        trends = analyze_trends(history,vendors,window_days=window,fee=cut)
        if trends.empty:
            st.warning("Insufficient history for this comparison. You need observations in both windows.")
        else:
            trends = trends.merge(vendors[["item_id","item_name"]].assign(item_id=lambda x:x.item_id.astype(str)),on="item_id",how="left")
            display = pd.DataFrame({
                "Item":trends["item_name"].fillna(trends["item_id"]),
                "Demand change (%)":trends["demand_change_pct"].round(1),
                "Sales/day (recent)":trends["recent_sales"].round(2),
                "Sales/day (previous)":trends["previous_sales"].round(2),
                "AH price change (%)":trends["price_change_pct"].round(1),
                "Competition change (%)":trends["competition_change_pct"].round(1),
                "Sales/listing change (%)":trends["velocity_change_pct"].round(1),
                "Net profit change (g)":(trends["net_profit_change_copper"]/10000).round(3),
                "Current profit/unit (g)":(trends["recent_profit_copper"]/10000).round(3),
                "Momentum score":trends["signal_score"].round(1),
                "Sufficient coverage":trends["coverage_ok"]
            })
            good = st.checkbox("Only sufficiently covered items",value=True)
            if good: display=display[display["Sufficient coverage"]]
            st.dataframe(display,use_container_width=True,hide_index=True)
            st.download_button("Export momentum rankings",display.to_csv(index=False),file_name=f"momentum_{window}d.csv",mime="text/csv")
            if not display.empty:
                st.bar_chart(display.set_index("Item")["Momentum score"])
            st.caption("Momentum is a heuristic, not a sales forecast. Demand is based on estimated sales/day snapshots, not confirmed transactions. Price increases alone do not establish demand. Coverage is based on observation span, not guaranteed completeness.")
    except Exception as e:
        st.error(f"Could not analyze history: {e}")
else:
    st.info("Upload a historical CSV with timestamp,item_id,ah_buyout_copper,daily_sales,competing_units.")

st.divider()
st.header("5 · Vendor catalog workbench")
st.write("Edit NPC purchase prices and provenance, then download the catalog. A verified flag means you personally confirmed the NPC buy price on Forever.")
stats=catalog_stats(vendors)
c1,c2,c3=st.columns(3)
c1.metric("Vendor entries",stats["rows"])
c2.metric("Unique item IDs",stats["unique_items"])
c3.metric("Verified entries",stats["verified"])
catalog_cols=["item_id","item_name","vendor_name","vendor_location","vendor_buy_copper","vendor_sellback_copper","stock","verified","source_url","checked_at","notes"]
editor=vendors[catalog_cols].copy()
editor["checked_at"]=editor["checked_at"].astype(str).replace("NaT","")
edited=st.data_editor(editor,num_rows="dynamic",use_container_width=True,hide_index=True,key="vendor_editor")
try:
    checked=validate_catalog(edited)
    checked["checked_at"]=checked["checked_at"].dt.strftime("%Y-%m-%dT%H:%M:%SZ").fillna("")
    st.download_button("Download validated vendor catalog",checked.to_csv(index=False),file_name="vendors_verified.csv",mime="text/csv")
except ValueError as exc:
    st.warning(f"Fix catalog entries before exporting: {exc}")
st.caption("Vendor prices must be the cost to BUY from an NPC, not the NPC sellback value. Sample catalog entries are fictional.")
