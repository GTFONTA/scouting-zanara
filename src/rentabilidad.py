"""Expected profit per m2 of each hit (Gonzalo, 23/11/2026): land incidence, total cost, sale value and the
difference, so the listings can be ordered by it. It never changes whether a listing is an opportunity.

  multifamiliar (per sellable m2; CABA always)
      incidencia  = price / m2 construibles (CABA: with the plusvalía), / fraccion_vendible
      costo total = incidencia + cost of works (margen.costo_obra_usd_m2.multifamiliar: 1.300 + 500)
      venta       = USD/m2 of new flats in the barrio / localidad (rentabilidad.tabla: public reports; without a
                    figure for new flats, the general one x premio_a_estrenar)
  loteo / agrupadas (per m2 of land)
      incidencia  = price / surface
      costo total = incidencia + development (calle interna: margen.costo_loteo_bc_usd_m2_bruto; else
                    rentabilidad.costo_loteo_abierto_usd_m2)
      venta       = the small-lot value of the localidad (mediana_usd_m2_lote, Fase 4) x sellable share
  diferencia = venta - costo total; margen % = diferencia / costo total.
"""

import csv
import math
import unicodedata

from .config import path

COLUMNS = ["rent_producto", "rent_por", "rent_incidencia_usd_m2", "rent_costo_total_usd_m2", "rent_venta_usd_m2",
           "rent_venta_fuente", "rent_diferencia_usd_m2", "rent_margen_pct", "rent_total_usd"]


def _f(v) -> float | None:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(x) else x


def _key(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().replace("-", " ").split())


class SaleValues:
    """USD/m2 of a new flat by zone (barrio in CABA, localidad in PBA) for one municipio."""

    def __init__(self, cfg: dict):
        k = cfg["rentabilidad"]
        self.premium = k["premio_a_estrenar"]
        self.alias = {_key(a): _key(b) for a, b in (k.get("alias_zonas") or {}).items()}
        slug = cfg["municipio"]["slug"]
        self.zones = {}
        with open(path(k["tabla"]), encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row["municipio"] != slug:
                    continue
                new, general = _f(row["usd_m2_a_estrenar"]), _f(row["usd_m2_general"])
                value, how = (new, "a estrenar") if new else (general * self.premium, f"general x {self.premium:g}")
                self.zones[_key(row["zona"])] = (round(value), f"{row['zona']}: {how} ({row['fuente']})")
        values = sorted(v for v, _ in self.zones.values())
        self.default = None
        if "_partido" not in self.zones and values:
            mid = values[len(values) // 2]
            self.default = (mid, f"zona sin dato: mediana del municipio")

    def get(self, *names: str) -> tuple[float | None, str]:
        for name in names:
            k = _key(name)
            if not k:
                continue
            k = self.alias.get(k, k)
            if k in self.zones:
                return self.zones[k]
            for zone in sorted(self.zones, key=len, reverse=True):      # "Palermo Soho", "Belgrano C", "Caballito Sur"
                if k.startswith(zone + " "):
                    return self.zones[zone]
        if "_partido" in self.zones:
            return self.zones["_partido"]
        return self.default or (None, "sin valor de venta")


def _multifamiliar(r: dict, cfg: dict) -> bool:
    via = r.get("via") or ""
    if cfg["municipio"]["motor"] == "caba" or "multifamiliar" in via:
        return bool(_f(r.get("m2_construibles")))
    return "loteo" not in via and (_f(r.get("multifamiliar_unidades")) or 0) > 0 and bool(_f(r.get("m2_construibles")))


def apply(r: dict, values: SaleValues, cfg: dict) -> None:
    """Fill the rent_* columns of one hit (left empty when there is no sale value or no basis)."""
    k, m = cfg["rentabilidad"], cfg["margen"]
    r.update({c: None for c in COLUMNS})
    price = _f(r.get("precio_usd"))
    if not price:
        return
    if _multifamiliar(r, cfg):
        sellable = _f(r["m2_construibles"]) * k["fraccion_vendible"]
        land = price + (_f(r.get("plusvalia_usd")) or 0)               # CABA: the plusvalía is paid like the land
        names = (r.get("barrio"),) if cfg["municipio"]["motor"] == "caba" else \
            (r.get("localidad"), r.get("barrio_usado"), r.get("barrio"))     # PBA: the localidad of the pin first
        sale, source = values.get(*(n or "" for n in names))
        product, per, base, cost = "multifamiliar", "m² vendible", sellable, m["costo_obra_usd_m2"]["multifamiliar"]
    else:
        lot = _f(r.get("mediana_usd_m2_lote"))
        surface = _f(r.get("superficie_m2"))
        if not lot or not surface:
            return
        internal = "calle interna" in (r.get("mejor_producto") or "") or "acceso común" in (r.get("mejor_producto") or "")
        share = 1 - cfg["productos"]["pct_calle"] if internal else 1.0
        sale = lot * share
        source = f"lote chico de {r.get('comparables') or 'la zona'}" + (f" x {share:g} (sin calle)" if internal else "")
        land, base, product, per = price, surface, "loteo / agrupadas", "m² de terreno"
        cost = m["costo_loteo_bc_usd_m2_bruto"] if internal else k["costo_loteo_abierto_usd_m2"]
    if not sale or not base:
        r["rent_venta_fuente"] = source
        return
    incid = land / base
    total = incid + cost
    diff = sale - total
    r.update(rent_producto=product, rent_por=per, rent_incidencia_usd_m2=round(incid), rent_costo_total_usd_m2=round(total),
             rent_venta_usd_m2=round(sale), rent_venta_fuente=source, rent_diferencia_usd_m2=round(diff),
             rent_margen_pct=round(100 * diff / total, 1), rent_total_usd=round(diff * base))


def apply_all(rows: list[dict], cfg: dict) -> None:
    if not (cfg.get("rentabilidad") or {}).get("activo"):
        return
    values = SaleValues(cfg)
    for r in rows:
        if r.get("resultado") in ("oportunidad", "casi", "gran_predio"):
            apply(r, values, cfg)


def order_key(r: dict) -> float:
    """Best expected profit per m2 first; hits without it go last."""
    d = r.get("rent_diferencia_usd_m2")
    return -d if d is not None else math.inf
