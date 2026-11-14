# Forever Vendor Flip Lab

A local dashboard for finding NPC vendor-to-Auction-House flips in **WoW Forever**. Includes live AHledger market snapshots, a locally imported Kaydee vendor catalog, faction filtering, profit estimates and conservative listing-size forecasts.

**Runs on your own computer.** No Git, Docker, cloud account, or programming knowledge required.

## Start here (Windows — easiest)

1. Install **Python 3.11 or 3.12** from https://www.python.org/downloads/ if you don't already have it. During setup, select **Add Python to PATH** when available.
2. On this GitHub repository page, choose **Code → Download ZIP**. Extract the ZIP to a normal folder (for example, Documents). **Do not run files from inside the ZIP.**
3. Double-click **`start_windows.bat`**.
4. Wait while it installs Python packages the first time. A browser window should open; otherwise visit **http://localhost:8501**.

That's it. Next time, double-click `start_windows.bat` again. The app keeps your vendor catalog and downloaded market data in `local_data/` inside the project folder.

**Important:** Windows may hide file extensions; the launcher might display as `start_windows`. You do **not** need Git to run it. An internet connection is needed to install dependencies and fetch current market prices.

### macOS / Linux

Install Python 3.11 or 3.12, download and extract the ZIP, then run this from the extracted directory:

```sh
sh start_unix.sh
```

Or on any platform: `python launch.py` (often `python3 launch.py` on macOS/Linux). The launcher creates `.venv` and installs dependencies automatically.

## Load vendor prices (recommended)

The first time you launch, the vendor catalog may be empty. To populate it:

1. Install Kaydee's Vendor Item Database addon in WoW Forever, or obtain your own copy of its addon ZIP.
2. In the dashboard, upload the **entire addon ZIP** under **Import built-in WoW Forever vendor database**, then select **Import Forever vendor database**. The ZIP must contain `Data_Forever.lua`.
3. Select **Alliance**, **Horde**, or **All** in the vendor catalog section. Shared vendors are shown for either faction.

The Kaydee addon database is **not redistributed in this repository**. Imported prices are reference data, not personally verified NPC prices. Check stock and requirements in game before buying. If you import again, your existing verified prices are preserved.

## Updating

**If you downloaded a ZIP:** Download a fresh ZIP from GitHub and extract it to a **new folder**. Copy your old `local_data/` folder into the new folder **before launching** to preserve your catalog and cached market data. Do not delete your old folder until you confirm the new version works.

**If you cloned with Git:** Run `update_windows.bat` (Windows) or `git pull --ff-only` (macOS/Linux), then launch normally. The startup script intentionally **does not** run Git or unit tests: it should work for friends who downloaded a ZIP.

Developers can run `test_windows.bat` or `python -m unittest discover -s . -p "test_*.py" -v` to test changes.

## Common problems

- **Python not found:** Install Python 3.11/3.12, restart the terminal or Windows Explorer, and try again. `py -3 --version` should print a version.
- **Python opens Microsoft Store:** Install Python from python.org and disable Windows Python app execution aliases if necessary.
- **Package installation fails:** Confirm internet access, then run `python launch.py --reinstall`.
- **Browser didn't open:** Visit http://localhost:8501 manually. Keep the terminal open while using the app.
- **Port 8501 in use:** Close an older instance. Advanced users can run `.venv\Scripts\python.exe -m streamlit run app.py --server.port 8502` on Windows.
- **No vendor listings:** Import the Kaydee ZIP (see above). An AH market download alone does not contain NPC prices.
- **No Alliance/Horde listings:** Reimport the Kaydee ZIP to restore faction metadata from older catalogs.
- **No internet:** Previously cached market data may be available; the dashboard warns when snapshots are stale.

## What the numbers mean

Vendor prices are the **cost to buy from the NPC**, in copper (10,000 copper = 1 gold). The app estimates AH sale price after the AH cut, potential profit, modeled demand, competition, and how many units might sell within your selected horizon. The **List now** recommendation uses a modeled 80% per-unit sell-through threshold. These are estimates, not guaranteed sales. Unsold listings can cost deposits and tie up gold. The model does not optimize the total budget across all items.

The dashboard supports a vendor CSV with `item_id,item_name,vendor_buy_copper` and optional `vendor_name,vendor_location,stock,verified,faction` and other metadata. Your catalog edits are saved locally when you click **Save changes**. Back up `local_data/` before replacing the application folder.

## Advanced

```sh
python launch.py --setup-only
python launch.py --reinstall
python sync.py --inspect
python sync.py --export history.csv
```

Market data uses AHledger's WoW Forever / US Normal / Alliance endpoint by default. The faction toggle filters **NPC vendors**, not the AH realm; Horde users should verify whether the selected AH market reflects their own trading environment. Historic trend comparisons require sufficient saved snapshots. Sample CSV files are fictional.

Source code: https://github.com/jfbenson/forever-vendor-flip-lab
