"""Fase 5, backtest: the hits of past runs, ordered by incidencia (today) and by margin (Fase 5), side by side.

Offline: no portal, no API. Steps:
  1. Seed register: the saved raw downloads of every run (raw_*.json) go through the same mappers and normalize as
     a run, and src/registro.py keeps the comparables (houses, lots in barrios cerrados; flats only once the
     comparables searches exist). Dollar: the last saved quote (data/cotizacion_dolar.json); no API.
  2. Each run's resultado.csv: hits (oportunidad, casi) and grandes predios get src/margin.py with the register as it
     was on that date (only comparables seen up to then).
Output (runs/backtest_fase5/):
  registro_semilla.csv     the seed register
  comparables.csv          comparables per product and localidad (n, median USD/m2)
  comparacion.csv          one row per hit: incidencia, value of the zone and margin of each vía, both rankings
  resumen.txt              what moves up and down

Usage:
    python tools/backtest_fase5.py                       # runs/ of this folder
    python tools/backtest_fase5.py --runs "C:/Users/ZN - GF/Proyectos/scouting-zanara/runs"
    python tools/backtest_fase5.py --municipio tigre
"""

import argparse
import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import margin, normalize, registro  # noqa: E402
from src.config import load_config, path  # noqa: E402
from src.locate import Locator  # noqa: E402
from src.main import MAPPERS  # noqa: E402

RUN_DIR = re.compile(r"^(\d{4}-\d{2}-\d{2})_\d{4}$")
KEEP = ["fecha_corrida", "resultado", "via", "titulo", "localidad", "precio_usd", "superficie_m2", "m2_construibles",
        "incidencia_usd_m2", "mejor_producto"]


def _fixed_dollar() -> None:
    saved = path("data/cotizacion_dolar.json")
    quote = json.loads(saved.read_text(encoding="utf-8")) if saved.exists() else {}
    normalize._quotes.clear()
    normalize.dolar_mep = lambda ncfg: {"venta": quote.get("venta"), "fecha": quote.get("fecha", ""),
                                        "error": "" if quote else "sin cotización guardada"}


def _runs(runs: Path) -> list[tuple[str, Path]]:
    out = [(m.group(1), d) for d in sorted(runs.iterdir()) if d.is_dir() and (m := RUN_DIR.match(d.name))]
    return [(f, d) for f, d in out if (d / "resultado.csv").exists()]


def seed(runs: list[tuple[str, Path]], cfg: dict) -> list[dict]:
    locator = Locator(cfg)
    reg: list[dict] = []
    for fecha, d in runs:
        rows = []
        for raw in sorted(d.glob("raw_*.json")):
            portal = raw.stem[len("raw_"):]
            if portal not in MAPPERS:
                continue
            for item in json.loads(raw.read_text(encoding="utf-8")):
                try:
                    rows.append(normalize.normalize(MAPPERS[portal](item), cfg))
                except Exception:                 # a malformed item of an old download: skip it
                    continue
        reg = registro.merge(reg, registro.collect(rows, locator, cfg, today=fecha))
    return reg


def _read(file: Path) -> list[dict]:
    with open(file, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs", default=str(ROOT / "runs"))
    ap.add_argument("--municipio", default=None)
    args = ap.parse_args()
    cfg = load_config(args.municipio)
    runs_root = Path(args.runs)
    if cfg["municipio"]["slug"] != "san_isidro":
        runs_root = runs_root / cfg["municipio"]["slug"]
    runs = _runs(runs_root) if runs_root.exists() else []
    if not runs:
        sys.exit(f"No hay corridas con resultado.csv en {runs_root}")
    _fixed_dollar()
    out = ROOT / "runs" / "backtest_fase5"
    out.mkdir(parents=True, exist_ok=True)

    reg = seed(runs, cfg)
    registro.save(out / "registro_semilla.csv", reg)
    groups: dict[tuple[str, str], list[float]] = {}
    for x in reg:
        groups.setdefault((x["producto"], x["localidad"] or "(sin localidad)"), []).append(float(x["usd_m2"]))
    with open(out / "comparables.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["producto", "localidad", "n", "mediana_usd_m2"])
        for (prod, loc), xs in sorted(groups.items()):
            w.writerow([prod, loc, len(xs), round(statistics.median(xs))])

    hits = []
    for fecha, d in runs:
        known = [x for x in reg if x["primera_vez"] <= fecha]      # the register as it was on that date
        for r in _read(d / "resultado.csv"):
            if r.get("resultado") not in ("oportunidad", "casi") and r.get("gran_predio") not in ("True", "true", "1"):
                continue
            try:
                ev = margin.evaluate(r, known, cfg, today=fecha)
            except (TypeError, ValueError, KeyError):
                continue
            hits.append({"fecha_corrida": fecha, **{k: r.get(k, "") for k in KEEP if k != "fecha_corrida"},
                         **ev, "url": r.get("url", "")})
    latest = {}
    for h in hits:                                 # a listing found in several weeks: its latest run
        latest[h["url"] or id(h)] = h
    hits = list(latest.values())
    by_inc = sorted(hits, key=lambda h: margin._f(h["incidencia_usd_m2"]) or 1e9)
    for i, h in enumerate(by_inc, 1):
        h["orden_incidencia"] = i
    by_margin = sorted(hits, key=lambda h: -(h["margen_mejor_pct"] if h["margen_mejor_pct"] is not None else -1e9))
    for i, h in enumerate(by_margin, 1):
        h["orden_margen"] = i
    cols = list(dict.fromkeys(k for h in hits for k in h))
    with open(out / "comparacion.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(by_margin)

    n_prod = {p: sum(1 for x in reg if x["producto"] == p) for p in margin.PRODUCTS.values()}
    with_margin = [h for h in hits if h["margen_mejor_pct"] is not None]
    lines = [f"Backtest Fase 5 — {cfg['municipio']['nombre']}, {len(runs)} corridas ({runs[0][0]} a {runs[-1][0]})",
             "Registro semilla: " + ", ".join(f"{p} {n}" for p, n in n_prod.items()),
             f"Hits y grandes predios: {len(hits)}; con margen calculable: {len(with_margin)}", ""]
    if not n_prod["departamento"]:
        lines.append("Sin departamentos en el registro: las búsquedas actuales no los bajan. El margen multifamiliar "
                     "queda vacío hasta sumar la búsqueda de comparables (piloto, después del 16/11).")
    lines += ["", "Top 10 por margen sobre costo (orden por incidencia entre paréntesis):"]
    for h in by_margin[:10]:
        if h["margen_mejor_pct"] is None:
            break
        lines.append(f"  {h['orden_margen']:>3} ({h['orden_incidencia']:>3})  {h['margen_mejor_pct']:>6}%  "
                     f"{h['margen_mejor_producto']:<13} inc {h['incidencia_usd_m2']:>6}  {h['localidad'] or '-':<14} "
                     f"{(h['titulo'] or '')[:50]}")
    (out / "resumen.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    print(f"\n-> {out}")


if __name__ == "__main__":
    main()
