"""Fase 5: register of what things sell for, to value each zone (plan aprobado por Gonzalo el 15/11/2026).

One CSV per municipio on the local disk (margen.registro), never in Google Drive. One row per listing:
  departamento          flats (the value of multifamiliar), flagged a_estrenar when the text says so
  casa                  houses (the value of housing / agrupadas)
  lote_barrio_cerrado   lots whose text says barrio cerrado / country / club de campo (loteo de barrio cerrado)
Every week adds the new listings and refreshes the ones still published (ultima_vez, price): the map gets denser
without downloading everything at once. Listings come from the normal searches (houses, lots) and, later, from
extra comparables searches (flats); this module never downloads anything.
"""

import csv
import re
from datetime import date
from pathlib import Path

from .config import path

COLUMNS = ["portal", "id", "producto", "localidad", "lat", "lon", "m2", "precio_usd", "usd_m2", "a_estrenar",
           "primera_vez", "ultima_vez", "titulo", "url"]


def file_for(cfg: dict) -> Path:
    slug = cfg["municipio"]["slug"]
    sufijo = "" if slug == "san_isidro" else f"_{slug}"
    return path(cfg["margen"]["registro"].format(sufijo=sufijo))


def product(r: dict, m: dict) -> str | None:
    """departamento / casa / lote_barrio_cerrado, or None (not a comparable)."""
    tipo = (r.get("tipologia") or "").strip().lower()
    text = f"{r.get('titulo') or ''} {r.get('descripcion') or ''}"
    for name, c in m["comparables"].items():
        if tipo not in c["tipologias"]:
            continue
        if name == "lote_barrio_cerrado" and not re.search(m["texto_barrio_cerrado"], text, re.I):
            continue
        return name
    return None


def area(r: dict, name: str) -> float | None:
    """m2 the price is compared with: covered (≈ sellable) for flats and houses, land for lots."""
    keys = ("superficie_terreno_m2", "superficie_m2", "superficie_total_m2") if name == "lote_barrio_cerrado" else \
           ("superficie_cubierta_m2", "superficie_total_m2", "superficie_m2")
    for k in keys:
        try:
            v = float(r.get(k) or 0)
        except (TypeError, ValueError):
            continue
        if v > 0:
            return v
    return None


def collect(rows: list[dict], locator, cfg: dict, today: str | None = None) -> list[dict]:
    """Comparables among this run's normalized listings (including the tipologías the scouting excludes)."""
    m = cfg["margen"]
    today = today or date.today().isoformat()
    out = []
    for r in rows:
        name = product(r, m)
        price = r.get("precio_usd")
        if not name or not price:
            continue
        c, s = m["comparables"][name], area(r, name)
        if not s or not c["m2_min"] <= s <= c["m2_max"]:
            continue
        usd_m2 = price / s
        if not c["usd_m2_min"] <= usd_m2 <= c["usd_m2_max"]:
            continue                                    # badly loaded price or surface
        lat, lon = r.get("lat_usada") or r.get("lat"), r.get("lon_usada") or r.get("lon")
        loc = locator.localidad(r) if locator else (r.get("localidad") or "")
        if lat is None and not loc:
            continue
        text = f"{r.get('titulo') or ''} {r.get('descripcion') or ''}"
        out.append({"portal": r["portal"], "id": r["id"], "producto": name, "localidad": loc,
                    "lat": round(lat, 6) if lat is not None else "", "lon": round(lon, 6) if lon is not None else "",
                    "m2": round(s), "precio_usd": round(price), "usd_m2": round(usd_m2),
                    "a_estrenar": "si" if re.search(m["texto_a_estrenar"], text, re.I) else "no",
                    "primera_vez": today, "ultima_vez": today,
                    "titulo": (r.get("titulo") or "")[:120], "url": r.get("url") or ""})
    return out


def merge(registry: list[dict], current: list[dict]) -> list[dict]:
    """Upsert by (portal, id): a listing seen again keeps its primera_vez and takes this week's data."""
    by_key = {(x["portal"], str(x["id"])): x for x in registry}
    for x in current:
        old = by_key.get((x["portal"], str(x["id"])))
        by_key[(x["portal"], str(x["id"]))] = {**x, "primera_vez": old["primera_vez"]} if old else x
    return sorted(by_key.values(), key=lambda x: (x["producto"], x["localidad"], float(x["usd_m2"])))


def load(file: Path) -> list[dict]:
    if not file.exists():
        return []
    with open(file, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def save(file: Path, rows: list[dict]) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    tmp.replace(file)
