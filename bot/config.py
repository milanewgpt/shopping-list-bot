import os
import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN: str = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")

BASE_DIR: Path = Path(__file__).resolve().parent.parent
_db_env = os.environ.get("DB_PATH")
DB_PATH: Path = Path(_db_env) if _db_env else BASE_DIR / "shopping.db"
TEMP_DIR: Path = Path(os.environ.get("TEMP_DIR", str(BASE_DIR / "tmp")))
TEMP_DIR.mkdir(exist_ok=True)

# Bundled ffmpeg from imageio-ffmpeg (no system install needed)
try:
    import imageio_ffmpeg
    FFMPEG_PATH: str = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("shopping_bot")
