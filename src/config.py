"""Load config.yaml and resolve project paths."""

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent


def load_env(files: list[str] | None = None) -> None:
    """Read secrets from the .env files listed in config.yaml (outside the Google Drive folder), then ./.env.
    Real environment variables win; empty values in a file never override a value found elsewhere."""
    for env in [Path(os.path.expanduser(f)) for f in files or []] + [ROOT / ".env"]:
        if not env.exists():
            continue
        for line in env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                v = v.strip().strip('"').strip("'")
                if v and not os.environ.get(k.strip()):
                    os.environ[k.strip()] = v


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    load_env(cfg.get("archivos_secretos"))
    return cfg


def path(rel: str) -> Path:
    return ROOT / rel
