import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
runpy.run_path(str(ROOT / "backend" / "scripts" / "seed_data.py"), run_name="__main__")