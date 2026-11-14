"""Cross-platform installer and launcher: python launch.py [--setup-only]."""
import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent
VENV = ROOT / ".venv"
PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")

def run(args):
    print("+", " ".join(map(str, args)), flush=True)
    subprocess.run([str(x) for x in args], cwd=ROOT, check=True)

def main():
    parser = argparse.ArgumentParser(description="Install and run Forever Vendor Flip Lab")
    parser.add_argument("--setup-only", action="store_true", help="Install dependencies without starting UI")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall dependencies")
    args = parser.parse_args()
    if sys.version_info < (3, 10):
        parser.error("Python 3.10+ is required; Python 3.11 or 3.12 recommended")
    if not PYTHON.exists():
        run([sys.executable, "-m", "venv", str(VENV)])
    # Reinstall only when necessary, or when explicitly requested.
    ready = subprocess.run([str(PYTHON), "-c", "import streamlit, pandas, requests"],
                           cwd=ROOT, stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL).returncode == 0
    if not ready or args.reinstall:
        run([PYTHON, "-m", "pip", "install", "-r", ROOT / "requirements.txt"])
    if args.setup_only:
        print("Setup complete. Run python launch.py to start the app.")
        return
    print("Opening Streamlit at http://localhost:8501 (Ctrl+C to stop).")
    run([PYTHON, "-m", "streamlit", "run", ROOT / "app.py",
         "--server.address", "127.0.0.1"])

if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print(f"Command failed (exit {exc.returncode}). Check Python and internet connectivity.", file=sys.stderr)
        sys.exit(exc.returncode)
    except KeyboardInterrupt:
        print("\nStopped.")
