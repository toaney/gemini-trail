import yaml
from pathlib import Path
from functools import lru_cache

CONFIG_PATH = Path(__file__).parent.parent / "config" / "game_config.yaml"


@lru_cache(maxsize=1)
def get_config() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)
