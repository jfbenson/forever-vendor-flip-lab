import io
import pandas as pd
import requests
import streamlit as st
from engine import compute
from trends import analyze_trends
from catalog import validate_catalog, catalog_stats
from ahledger import decode, normalize_ahl1
from local_store import load_market, read_vendors, save_vendors, VENDOR_PATH
from vendor_import import import_npcs, merge_catalog, parse_addon_csv

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

st.subheader("1 · Market data & local catalog")
st.caption("Market prices load automatically from AHledger and are saved on this computer. No manual AH scan or CSV download is required.")
with st.expander("Data settings", expanded=False):
    url = st.text_input("AHledger endpoint", "https://api.ahledger.com/v1/pricetable/forever.normal.alliance.us")
    refresh_hours = st.selectbox("Refresh market when provider snapshot is older than", [1, 3, 6, 12, 24], index=2, format_func=lambda h: f"{h} hours")
    use_demo = st.checkbox("Use fictional demo data", value=False)
    uploaded_market = st.file_uploader("Optional normalized market CSV override", type="csv", key="market")
    uploaded_vendor = st.file_uploader("Import vendor catalog CSV", type="csv", key="vendor")

@st.cache_data(ttl=300, show_spinner="Checking local market and AHledger...")
def cached_market(endpoint, hours):
    return load_market(endpoint, refresh_hours=hours)

market, vendors = None, None
if st.button("Refresh market now", type="primary", disabled=use_demo):
    try:
        market, status = load_market(url, refresh_hours=refresh_hours, force=True)
        cached_market.clear()
        st.success("Market refresh completed.")
    except Exception as exc:
        st.error(f"Refresh failed: {exc}")
if uploaded_market is not None:
    market = pd.read_csv(uploaded_market)
    st.info("Using uploaded market override; local AHledger cache is unchanged.")
elif use_demo:
    market = pd.read_csv("sample_market.csv")
elif market is None:
    try:
        market, status = cached_market(url, refresh_hours)
    except Exception as exc:
        st.error(f"Market unavailable: {exc}")
if market is not None and not use_demo and uploaded_market is None:
    st.caption(f"{len(market):,} market items · {status['source']} · provider scan: {pd.to_datetime(status['timestamp'], unit='s', utc=True)} · age: {status['age_hours']:.1f} hours")
    if status.get("warning"):
        st.warning(f"Using saved market data because refresh failed: {status['warning']}")
    if status["age_hours"] > max_age:
        st.warning("The market snapshot exceeds your maximum scan age; recommendations are marked stale.")

if uploaded_vendor is not None:
    try:
        vendors = save_vendors(pd.read_csv(uploaded_vendor, dtype={"item_id": str}))
        st.success(f"Imported and saved {len(vendors)} vendor records to {VENDOR_PATH}.")
    except Exception as exc:
        st.error(f"Vendor catalog import failed: {exc}")
if vendors is None:
    try:
        vendors = read_vendors()
    except Exception as exc:
        st.error(f"Cannot read saved vendor catalog: {exc}")
st.subheader("Import vendor prices")
with st.expander("Classic vendor database / addon CSV", expanded=vendors is None):
    st.caption("WoWDB Classic prices are reference estimates, NOT verified Forever prices. Only copper-priced items are imported.")
    npc_text = st.text_input("Classic NPC IDs (comma-separated)", placeholder="e.g. 3090")
    if st.button("Import these NPCs from WoWDB"):
        try:
            npc_ids = [int(x.strip()) for x in npc_text.split(",") if x.strip()]
            if not npc_ids or len(npc_ids) > 25:
                raise ValueError("Enter between 1 and 25 NPC IDs.")
            incoming = import_npcs(npc_ids)
            if incoming.empty:
                st.warning("No copper-priced items found for those NPCs.")
            else:
                merged = merge_catalog(vendors, incoming)
                save_vendors(merged)
                st.success(f"Imported {len(incoming)} vendor listings; saved {len(merged)} catalog entries.")
                st.rerun()
        except Exception as exc:
            st.error(f"WoWDB import failed: {exc}")
    st.caption("Kaydee's addon: /kvid export provides in-game observations, but its raw text format has not been validated yet.")
    addon_file = st.file_uploader("Import addon-derived CSV (standard catalog columns)", type=["csv"], key="addon_vendor_csv")
    if addon_file is not None and st.button("Import addon CSV"):
        try:
            incoming = parse_addon_csv(addon_file)
            merged = merge_catalog(vendors, incoming)
            save_vendors(merged)
            st.success(f"Imported {len(incoming)} entries.")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

if vendors is None and use_demo:
    vendors = pd.read_csv("sample_vendors.csv")
if vendors is None:
    st.info("No local vendor catalog yet. Add your first NPC vendor item below, or import a CSV in Data settings.")
    st.caption("Vendor purchase prices cannot be inferred from AHledger; enter prices observed in-game. Data is saved locally.")
    with st.form("first_vendor"):
        item_id = st.text_input("WoW item ID")
        item_name = st.text_input("Item name")
        vendor_name = st.text_input("NPC vendor name")
        vendor_location = st.text_input("Vendor location")
        price = st.number_input("NPC purchase price (copper)", min_value=1, value=100)
        verified = st.checkbox("I verified this NPC price in WoW Forever")
        if st.form_submit_button("Save first vendor item"):
            try:
                frame = pd.DataFrame([{"item_id": item_id, "item_name": item_name,
                    "vendor_name": vendor_name, "vendor_location": vendor_location,
                    "vendor_buy_copper": price, "verified": verified}])
                save_vendors(frame)
                st.rerun()
            except Exception as exc:
                st.error(f"Cannot save vendor: {exc}")
    st.stop()
try:
    vendors = validate_catalog(vendors)
except ValueError as exc:
    st.error(f"Vendor catalog validation: {exc}")
    st.stop()
if market is None:
    st.stop()

st.divider()
st.header("5 · Vendor catalog workbench")
st.write("Edit your local NPC catalog. Click Save changes to persist edits between sessions. A verified flag means you confirmed the NPC purchase price on Forever.")
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
    if st.button("Save vendor changes locally"):
        try:
            save_vendors(checked)
            st.success(f"Saved {len(checked)} vendor records to {VENDOR_PATH}.")
        except Exception as exc:
            st.error(f"Save failed: {exc}")
    st.download_button("Download vendor backup CSV",checked.to_csv(index=False),file_name="vendors_verified.csv",mime="text/csv")
except ValueError as exc:
    st.warning(f"Fix catalog entries before exporting: {exc}")
st.caption("Vendor prices must be the cost to BUY from an NPC, not the NPC sellback value. Sample catalog entries are fictional.")

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
            if source.attrs.get("format") == "AHL1":
                st.info("AHL1 follows the provider schema. Estimated sales/day is field_8 / 10; listed quantity is a competition proxy.")
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

