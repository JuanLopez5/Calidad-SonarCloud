from dotenv import load_dotenv
import os

load_dotenv()


class Config:
    """Application configuration values loaded from environment.

    Renamed from `config.py` to `app_config.py` to avoid a module/package
    name collision with the `src/config/` package which contains
    submodules like `src.config.firebase`.
    """

    SPOONACULAR_API_KEY = os.getenv("SPOONACULAR_API_KEY")
    SPOONACULAR_URL_BASE = os.getenv("SPOONACULAR_URL_BASE")
