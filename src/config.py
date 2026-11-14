"""Load config.yaml (+ the municipio overlay) and resolve project paths.

San Isidro is the base config (config.yaml as it always was). Any other municipio has its own
municipios/<slug>/municipio.yaml, deep-merged over config.yaml: dicts merge key by key, anything else
(lists, numbers, strings) replaces. Paths inside it are relative to the project root, like in config.yaml.
"""

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MUNICIPIO = "san_isidro"


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


def _merge(base: dict, over: dict) -> dict:
    """A key written with a trailing '!' (alias_barrios!: {...}) replaces the base dict instead of merging."""
    out = dict(base)
    for k, v in over.items():
        if k.endswith("!"):
            out[k[:-1]] = v
        else:
            out[k] = _merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def municipios() -> list[str]:
    return sorted({DEFAULT_MUNICIPIO} | {p.parent.name for p in (ROOT / "municipios").glob("*/municipio.yaml")})


def load_config(municipio: str | None = None) -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    slug = municipio or DEFAULT_MUNICIPIO
    if slug != DEFAULT_MUNICIPIO:
        overlay = ROOT / "municipios" / slug / "municipio.yaml"
        if not overlay.exists():
            raise ValueError(f"municipio desconocido: {slug} (hay: {', '.join(municipios())})")
        with open(overlay, encoding="utf-8") as fh:
            cfg = _merge(cfg, yaml.safe_load(fh) or {})
    m = cfg.setdefault("municipio", {})
    m.setdefault("slug", slug)
    m.setdefault("nombre", "San Isidro")
    m.setdefault("motor", "zonas")           # zonas: zone layer + normativa (San Isidro, PBA) | caba: Ciudad 3D
    m.setdefault("en_prueba", False)         # mail marked as a test, only to mail.para
    load_env(cfg.get("archivos_secretos"))
    return cfg


def path(rel: str) -> Path:
    return ROOT / rel
