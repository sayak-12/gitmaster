# config.py

from pathlib import Path

APP_ROOT = Path(__file__).parent.resolve()
BASE_DATA_PATH = APP_ROOT / "data"
BASE_DATA_PATH.mkdir(parents=True, exist_ok=True)
