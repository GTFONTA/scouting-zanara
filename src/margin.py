"""Fase 5: what the product sells for around a listing, and the margin it leaves (plan aprobado el 15/11/2026).

Value of the zone (USD/m2, from src/registro.py): median of the comparables of that product within margen.radio_m
of the listing, seen in the last margen.meses; with fewer than margen.avisos_min, the median of the localidad,
then of the partido. Each value says which step it used (escalon) and how many comparables (n).

Margins (costs of Gonzalo, 14/11/2026, in config.yaml margen:):
  multifamiliar / casas   per m2 sellable = value x (1 - descuento) - cost of works - incidencia
                          total = margin per m2 x m2 construibles (taken as sellable); on cost = margin / (cost + incidencia)
  loteo de barrio cerrado per m2 of raw land = lot value x sellable share x (1 - descuento) - development cost
                          - land price per m2; total = x surface; on cost = margin / (cost + land price per m2)
Nothing here changes the result of a listing: with margen.activo the margin is data and order only.
"""

import math
import statistics
from datetime import date, timedelta

from .comparables import PARTIDO

# vía of ZANARA -> product of the register
PRODUCTS = {"multifamiliar": "departamento", "casas": "casa", "loteo_bc": "lote_barrio_cerrado"}
PREFIX = {"multifamiliar": "depto", "casas": "casa", "loteo_bc": "lote_bc"}
SAME_SURFACE, SAME_PIN_M = 0.01, 150


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def distance_m(lat1, lon1, lat2, lon2) -> float:
    """Equirectangular approximation: plenty for a few km."""
    k = 111_320
    return math.hypot((lat2 - lat1) * k, (lon2 - lon1) * k * math.cos(math.radians((lat1 + lat2) / 2)))


def _usable(registry: list[dict], name: str, m: dict, today: str) -> list[dict]:
    since = (date.fromisoformat(today) - timedelta(days=round(m["meses"] * 30.4))).isoformat()
    rows = [x for x in registry if x["producto"] == name and str(x.get("ultima_vez", "")) >= since]
    if name in m["solo_a_estrenar"]:
        rows = [x for x in rows if x.get("a_estrenar") == "si"]
    return rows


def _dedupe(rows: list[dict], tol: float) -> list[dict]:
    """The same unit published by several agencies or portals counts once."""
    out = []
    for x in rows:
        s, p = float(x["m2"]), float(x["precio_usd"])
        lat, lon = _f(x.get("lat")), _f(x.get("lon"))
        dup = False
        for y in out:
            if abs(float(y["m2"]) - s) > SAME_SURFACE * s or abs(float(y["precio_usd"]) - p) > tol * p:
                continue
            ylat, ylon = _f(y.get("lat")), _f(y.get("lon"))
            if None in (lat, lon, ylat, ylon):
                dup = x.get("localidad") == y.get("localidad")
            else:
                dup = distance_m(lat, lon, ylat, ylon) <= SAME_PIN_M
            if dup:
                break
        if not dup:
            out.append(x)
    return out


def zone_value(registry: list[dict], name: str, lat, lon, localidad: str, cfg: dict,
               today: str | None = None) -> dict:
    """{'usd_m2', 'n', 'escalon'} of product `name` around a point; usd_m2 None if not even the partido has enough."""
    m = cfg["margen"]
    rows = _dedupe(_usable(registry, name, m, today or date.today().isoformat()), cfg["deduplicacion"]["tolerancia"])
    lat, lon = _f(lat), _f(lon)
    steps = []
    if lat is not None and lon is not None:
        steps.append((f"{m['radio_m']} m", [x for x in rows if _f(x.get("lat")) is not None and _f(x.get("lon")) is not None
                                            and distance_m(lat, lon, float(x["lat"]), float(x["lon"])) <= m["radio_m"]]))
    if localidad:
        steps.append(("localidad", [x for x in rows if x.get("localidad") == localidad]))
    steps.append((PARTIDO, rows))
    for step, xs in steps:
        if len(xs) >= m["avisos_min"]:
            return {"usd_m2": round(statistics.median(float(x["usd_m2"]) for x in xs)), "n": len(xs), "escalon": step}
    return {"usd_m2": None, "n": len(rows), "escalon": ""}


def margin_built(value: float, incidencia: float, m2: float, cost: float, discount: float) -> dict:
    per_m2 = value * (1 - discount) - cost - incidencia
    return {"usd_m2": round(per_m2), "total": round(per_m2 * m2), "pct": round(100 * per_m2 / (cost + incidencia), 1)}


def margin_loteo(lot_value: float, land_usd_m2: float, surface: float, cost: float, sellable: float,
                 discount: float) -> dict:
    per_m2 = lot_value * sellable * (1 - discount) - cost - land_usd_m2
    return {"usd_m2": round(per_m2), "total": round(per_m2 * surface), "pct": round(100 * per_m2 / (cost + land_usd_m2), 1)}


def _applies(r: dict, via: str) -> bool:
    n = lambda k: _f(r.get(k)) or 0
    if via == "multifamiliar":
        return n("multifamiliar_unidades") > 0 and n("m2_construibles") > 0
    if via == "casas":
        return max(n("lotes_frente_propio"), n("agrupadas_calle"), n("agrupadas_acceso_comun")) >= 2 and \
            n("m2_construibles") > 0
    return n("lotes_calle_interna") > 0


def evaluate(r: dict, registry: list[dict], cfg: dict, today: str | None = None) -> dict:
    """Value of the zone and margin of each vía the listing allows, plus the best one (margen_mejor_*)."""
    m = cfg["margen"]
    out = {}
    best = None
    lat, lon = r.get("lat_usada") or r.get("lat"), r.get("lon_usada") or r.get("lon")
    for via, name in PRODUCTS.items():
        pre = PREFIX[via]
        if not _applies(r, via):
            continue
        v = zone_value(registry, name, lat, lon, r.get("localidad") or "", cfg, today)
        out.update({f"valor_venta_{pre}_usd_m2": v["usd_m2"], f"valor_venta_{pre}_n": v["n"],
                    f"valor_venta_{pre}_escalon": v["escalon"]})
        if v["usd_m2"] is None:
            continue
        price, s = float(r["precio_usd"]), float(r["superficie_m2"])
        if via == "loteo_bc":
            g = margin_loteo(v["usd_m2"], price / s, s, m["costo_loteo_bc_usd_m2_bruto"],
                             1 - cfg["productos"]["pct_calle"], m["descuento_negociacion"])
        else:
            m2 = float(r["m2_construibles"])
            g = margin_built(v["usd_m2"], price / m2, m2, m["costo_obra_usd_m2"][via], m["descuento_negociacion"])
        out.update({f"margen_{pre}_usd_m2": g["usd_m2"], f"margen_{pre}_total": g["total"],
                    f"margen_{pre}_pct": g["pct"]})
        if best is None or g["pct"] > best[1]:
            best = (via, g["pct"])
    out["margen_mejor_producto"], out["margen_mejor_pct"] = best if best else ("", None)
    return out
