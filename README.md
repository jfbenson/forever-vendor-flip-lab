# Forever Vendor Flip Lab

A local Streamlit dashboard for **WoW Forever / US Normal / Alliance** vendor-to-auction-house opportunities. Works on **Windows, macOS, and Linux**. No Docker, AWS account, or GitHub Actions required.

> **Current data status:** The included demo items and historical observations are fictional. The AHledger live API schema and actual Forever vendor purchase prices have **not** been verified. This is a research prototype, not a source of live trade recommendations.

## Quick start

**Prerequisite:** Install **Python 3.11 or 3.12** (3.10+ supported). On Windows, download Python from https://www.python.org/downloads/ and enable **Add python.exe to PATH** if offered. An internet connection is needed for first-time package installation.

1. Extract the ZIP to a writable folder (for example `Documents/ForeverFlipLab`). **Don't run directly inside the ZIP.**
2. Start it:
   - **Windows:** double-click `start_windows.bat`.
   - **macOS / Linux:** in a terminal inside the folder, run `sh start_unix.sh`.
   - **Any OS:** run `python launch.py` (or `python3 launch.py`).
3. The first launch creates a local `.venv` and installs dependencies automatically. Subsequent launches reuse them.
4. Open **http://localhost:8501** if your browser doesn't open automatically.
5. Press **Ctrl+C** in the terminal to stop the server. The app runs only on your machine.

### Optional commands

```bash
python launch.py --setup-only     # Install packages without starting the app
python launch.py --reinstall      # Reinstall packages, then start
```

On macOS/Linux, substitute `python3` for `python` as needed. The launcher invokes Streamlit through the venv's Python, so manual activation is not required.

### Troubleshooting

- **Windows says Python is missing:** Install Python 3.11/3.12 and restart the terminal. Try `py -3 --version`.
- **Windows opens Microsoft Store instead of Python:** Use the Python launcher (`py -3 launch.py`) or disable the Windows app execution aliases for `python.exe` and `python3.exe`.
- **Packages fail to install:** Check internet access, VPN/proxy settings, and retry with `python launch.py --reinstall`.
- **Port 8501 is busy:** Stop the previous app instance or run `.venv/Scripts/python.exe -m streamlit run app.py --server.port 8502` on Windows; use `.venv/bin/python` on macOS/Linux.
- **Antivirus warns about the batch file:** Open `start_windows.bat` in a text editor to inspect it, or use `py -3 launch.py` directly. No administrator rights should be required for normal use.
- **API test fails:** The public endpoint or response schema may be different from the unverified assumptions. Demo mode still works offline after dependencies are installed.

## Real market data

The app accepts a normalized market CSV with required fields:
`item_id,ah_buyout_copper,daily_sales,competing_units`.
Optional fields: `market_price_copper,scan_age_hours`.

For a raw AHledger response, use the **API response mapping workbench** in the app to inspect fields and create a normalized CSV. Alternatively, from a terminal:
```bash
python sync.py --inspect
python sync.py --mapping mapping.json
python sync.py --export history.csv
```
Only run the second command **after** verifying the real field names and price units and editing the mapping. The current API address is a hypothesis, not a verified working integration.

## Vendor catalog

Upload a CSV containing `item_id,item_name,vendor_buy_copper`. Optional columns:
`vendor_name,vendor_location,vendor_sellback_copper,stock,verified,source_url,checked_at,notes`.
`vendor_buy_copper` is **what you pay the NPC**, not what the NPC pays you. All prices are copper (10,000 copper = 1 gold). Use the vendor catalog editor to revise records and **download your edits** before closing the app; changes are not autosaved.

## Trends

The dashboard compares 1, 2, 3, 5, or 7-day periods against the immediately preceding equal-length window. A 7-day comparison requires 14 days of history. Upload timestamped `history.csv` in the Momentum section. `collect.py` can append normalized market snapshots to a local SQLite database. Use real observations for actual trends.

## Model limitations

- Profit/unit = conservative resale price after AH cut minus NPC buy price and assumed listing deposit.
- Expected weekly profit is a **heuristic** based on estimated sales rates and competing listings, not confirmed transactions.
- The per-item budget cap does **not** enforce a combined portfolio budget.
- Repeat listing fees, travel, price impact and changing supply are not modeled.
- All included sample data is fictional, even if sample `verified` flags are true.

## Files

- `launch.py`, `start_windows.bat`, `start_unix.sh`: portable setup and launch
- `app.py`: Streamlit dashboard
- `engine.py`, `trends.py`, `catalog.py`: calculations and validation
- `ahledger.py`, `sync.py`, `collect.py`: API inspection and historical ingestion
- `sample_*.csv`: fictional examples
- `requirements.txt`: Python dependencies

Cloud hosting and scheduled AWS collection are intentionally outside this app's scope.
