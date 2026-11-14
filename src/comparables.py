"""What a small lot sells for in each localidad: the yardstick for a loteo or agrupadas, priced per unit.

Comparables are lots (tipología terreno) of superficie_min..superficie_max m2 with a valid price. They come from
this week's download (the main searches bring the 400-600 m2 ones; the extra Mercado Libre search, the smaller
ones) plus the last `semanas` weeks kept in the Sheet tab "comparables". The median USD/m2 of each localidad is
used when it has at least `avisos_min` distinct lots; otherwise, the median of the whole partido (PARTIDO).
"""

import statistics
from datetime import date, timedelta

COLUMNS = ["fecha", "id", "portal", "localidad", "superficie_m2", "precio_usd", "usd_m2", "url"]
PARTIDO = "partido"


def collect(rows: list[dict], locator, cfg: dict) -> list[dict]:
    """Small lots among this run's normalized listings (before the surface prefilter drops them)."""
    c = cfg["productos"]["comparables"]
    today = date.today().isoformat()
    out = []
    for r in rows:
        s, price = r.get("superficie_m2"), r.get("precio_usd")
        if r.get("motivo_descarte") or r.get("tipologia") != "terreno" or not s or not price:
            continue
        if not c["superficie_min"] <= s <= c["superficie_max"]:
            continue
        loc = locator.localidad(r)
        if loc:
            out.append({"fecha": today, "id": r["id"], "portal": r["portal"], "localidad": loc,
                        "superficie_m2": round(s), "precio_usd": round(price), "usd_m2": round(price / s),
                        "url": r["url"]})
    return out


def merge(history: list[dict], current: list[dict], cfg: dict) -> list[dict]:
    """History + this week, one row per listing id (the latest wins), without rows older than `semanas`."""
    since = (date.today() - timedelta(weeks=cfg["productos"]["comparables"]["semanas"])).isoformat()
    by_id = {h["id"]: h for h in history if str(h.get("fecha", "")) >= since}
    by_id.update({x["id"]: x for x in current})
    return sorted(by_id.values(), key=lambda x: (x["localidad"], float(x["usd_m2"])))


SAME_SURFACE = 0.01      # the same lot published by several agencies: surface within 1% and price within 5%


def medians(comps: list[dict], cfg: dict) -> dict[str, dict]:
    """localidad (and PARTIDO) -> {'mediana_usd_m2', 'n'}; the same lot published by several agencies counts once."""
    c = cfg["productos"]["comparables"]
    tol = cfg["deduplicacion"]["tolerancia"]
    groups: dict[str, list[dict]] = {}
    for x in comps:
        s, price = float(x["superficie_m2"]), float(x["precio_usd"])
        same = [y for y in groups.get(x["localidad"], [])
                if abs(float(y["superficie_m2"]) - s) <= SAME_SURFACE * s and abs(float(y["precio_usd"]) - price) <= tol * price]
        if not same:
            groups.setdefault(x["localidad"], []).append(x)
    groups[PARTIDO] = [x for xs in groups.values() for x in xs]
    return {loc: {"mediana_usd_m2": round(statistics.median(float(x["usd_m2"]) for x in xs)), "n": len(xs)}
            for loc, xs in groups.items() if len(xs) >= c["avisos_min"]}
