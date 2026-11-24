"""Offline reprocessing of a saved run, for the golden tests.

Same steps as `python -m src.main --reusar <run> --sin-sheet --sin-mail`, but with no network at all:
- dollar MEP fixed (FIXED_DOLLAR), so listings in pesos always convert the same;
- ARBA cadastre only from a frozen copy of its cache (tests/golden/cache_catastro.json.gz); never written;
- geocoding and any other HTTP request fail (as if the service didn't answer);
- comparables history from the Sheet: empty (as with --sin-sheet).
"""

import csv
import gzip
import io
import json
import re
from datetime import date
from pathlib import Path

import requests

GOLDEN = Path(__file__).resolve().parent / "golden"
FIXED_DOLLAR = {"venta": 1580.9, "fecha": "2026-11-13", "error": ""}
RUNS = ["2026-11-09_1851", "2026-11-02_1030"]


def _no_network(*args, **kwargs):
    raise requests.ConnectionError("tests: sin red")


def offline(monkeypatch, tmp_path: Path) -> None:
    """Patch everything that could reach the network or write outside tmp_path."""
    monkeypatch.setattr(requests, "get", _no_network)
    monkeypatch.setattr(requests.Session, "get", _no_network)
    monkeypatch.setattr(requests.Session, "post", _no_network)
    cache = tmp_path / "cache_catastro.json"
    cache.write_bytes(gzip.decompress((GOLDEN / "cache_catastro.json.gz").read_bytes()))
    from src import normalize
    normalize._quotes.clear()
    monkeypatch.setattr(normalize, "dolar_mep", lambda ncfg: dict(FIXED_DOLLAR))
    return cache


def load_items(run: str) -> tuple[dict, list[dict]]:
    d = GOLDEN / run
    items = {}
    for gz in sorted(d.glob("raw_*.json.gz")):
        portal = gz.name[len("raw_"):-len(".json.gz")]
        items[portal] = json.loads(gzip.decompress(gz.read_bytes()))
    health = json.loads((d / "salud.json").read_text(encoding="utf-8"))
    return items, health


def reprocess(run: str, monkeypatch, tmp_path: Path) -> dict[str, str]:
    """{'resultado.csv': ..., 'resumen.txt': ..., 'mail.html': ...} as text, with today's date masked."""
    cache = offline(monkeypatch, tmp_path)
    from src import main
    from src.config import load_config
    from src.notify import render_report

    cfg = load_config()
    cfg["productos"]["catastro"]["cache"] = str(cache)          # absolute: path() keeps it as is
    items, health = load_items(run)
    processed, _ = main.process(items, cfg, [], health)
    rows = main.finish(processed, cfg)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=main.COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    w.writerows(rows)
    n_raw = sum(len(v) for v in items.values())
    subject, body = render_report(rows, health, None, n_raw, cfg)
    today = date.today().strftime("%d/%m/%Y")
    out = {"resultado.csv": buf.getvalue(), "resumen.txt": main.summary(n_raw, rows, health, cfg),
           "mail.html": subject + "\n" + body}
    return {k: re.sub(re.escape(today), "<HOY>", v) for k, v in out.items()}


def expected(run: str) -> dict[str, str]:
    d = GOLDEN / run
    return {name: gzip.decompress((d / f"esperado_{name}.gz").read_bytes()).decode("utf-8")
            for name in ("resultado.csv", "resumen.txt", "mail.html")}


def save_expected(run: str, out: dict[str, str]) -> None:
    for name, text in out.items():
        (GOLDEN / run / f"esperado_{name}.gz").write_bytes(gzip.compress(text.encode("utf-8"), 9, mtime=0))
