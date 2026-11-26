"""Buildable m2, incidence, units per product and classification (rules in CLAUDE.md, thresholds in config.yaml).

productos.activo in config.yaml switches between:
  false  Fase 2 rule: m2 construibles = superficie x FOT; oportunidad if m2 > min and incidencia < max.
  true   Fase 4: the listing is valued by the products ZANARA develops, with the formulas of the Excel's
         'Calculadora' (docs/Zonificacion_San_Isidro_COU2022_v2.xlsx):
           by right       lotes con frente propio, agrupadas a la calle, multifamiliar
           with approval  loteo con calle interna, agrupadas con acceso común (O.T.), Urbanización Especial
         and it qualifies through one or more vías, each in the most favorable zone near the point:
           multifamiliar    incidencia on the highest FOT among the zones that allow multifamiliar
           loteo_agrupadas  lots or houses by right (not flats), priced per unit against a small lot of the
                            same localidad, or of the partido if the localidad has too few (comparables.py)
           gran_predio      >= 3.000 m2 in a zone with housing, always reported
"""

import math

from . import alturas, entorno
from .comparables import PARTIDO

NO_HOUSING = "Sin vivienda como producto"
PRODUCTS = ("lotes_frente_propio", "lotes_calle_interna", "agrupadas_calle", "agrupadas_acceso_comun",
            "multifamiliar_unidades", "ue_unidades")
BY_RIGHT = ("multifamiliar_unidades", "agrupadas_calle", "lotes_frente_propio")      # ties: first wins
WITH_APPROVAL = ("ue_unidades", "agrupadas_acceso_comun", "lotes_calle_interna")
LOTS = ("agrupadas_calle", "lotes_frente_propio")                                  # houses or lots, by right
PRODUCT_NAMES = {"multifamiliar_unidades": "multifamiliar", "agrupadas_calle": "agrupadas a la calle",
                 "lotes_frente_propio": "lotes con frente propio", "ue_unidades": "urbanización especial",
                 "agrupadas_acceso_comun": "agrupadas con acceso común", "lotes_calle_interna": "loteo con calle interna"}


def address_unknown(r: dict) -> bool:
    """Hits located only by street or barrio go to their own block (mail, Sheet), below the located ones."""
    return r.get("flag_confianza") == "aproximada_barrio"


def sections(rows: list[dict], by_profit: bool = False) -> dict[str, list[dict]]:
    """Fase 4 blocks, in the mail's order. A listing appears once: multifamiliar before loteo, and a large lot
    that is already an opportunity stays in its opportunity block. by_profit (rentabilidad.activo): every block
    ordered by the expected profit per m2 instead."""
    if by_profit:
        from .rentabilidad import order_key
        return {k: sorted(v, key=order_key) for k, v in sections(rows).items()}
    shown = [r for r in rows if r["resultado"] in ("oportunidad", "casi", "gran_predio")]
    located = [r for r in shown if not address_unknown(r)]
    opp = [r for r in located if r["resultado"] == "oportunidad"]
    per_unit = lambda r: r.get("usd_por_unidad_derecho") or 1e12                    # noqa: E731
    per_lot = lambda r: r.get("usd_por_unidad_loteo") or 1e12                       # noqa: E731
    return {
        "multifamiliar": sorted((r for r in opp if "multifamiliar" in r["via"]), key=lambda r: r["incidencia_usd_m2"]),
        "loteo_agrupadas": sorted((r for r in opp if "multifamiliar" not in r["via"]), key=per_lot),
        "gran_predio": sorted((r for r in located if r.get("gran_predio") and r["resultado"] != "oportunidad"),
                              key=lambda r: -r["superficie_m2"]),
        "casi": sorted((r for r in located if r["resultado"] == "casi" and not r.get("gran_predio")), key=per_unit),
        "sin_direccion": sorted((r for r in shown if address_unknown(r)), key=per_unit),
    }


def evaluate(r: dict, cfg: dict, normativa: dict | None = None, medians: dict | None = None) -> dict:
    if cfg["productos"]["activo"]:
        return _evaluate_products(r, cfg, normativa, medians or {})
    return _evaluate_fot(r, cfg)


def _evaluate_fot(r: dict, cfg: dict) -> dict:
    c = cfg["criterio"]
    out = {"m2_construibles": None, "incidencia_usd_m2": None, "resultado": "descartado"}
    if r.get("motivo_descarte"):
        return out
    sup, fot, price = r.get("superficie_m2"), r.get("fot_usado"), r.get("precio_usd")
    if sup is not None and sup < cfg["zonificacion"]["superficie_min_prefiltro"]:
        out["motivo_descarte"] = "superficie_menor_prefiltro"
        return out
    if fot == 0:
        out["motivo_descarte"] = "fot_cero"
        return out
    m2 = sup * fot
    inc = price / m2
    out["m2_construibles"] = round(m2)
    out["incidencia_usd_m2"] = round(inc, 1)
    if m2 > c["m2_construibles_min"] and inc < c["incidencia_max_usd"]:
        out["resultado"] = "oportunidad"
    elif m2 > c["m2_construibles_min"] and inc < c["incidencia_casi_max_usd"]:
        out["resultado"] = "casi"
    else:
        out["motivo_descarte"] = "m2_insuficientes" if m2 <= c["m2_construibles_min"] else "incidencia_alta"
    return out


# ---------------------------------------------------------------- Fase 4: products

def _f(v) -> float | None:
    try:
        return float(v) if v not in (None, "") else None
    except ValueError:
        return None


def _floor(x: float) -> int:
    return math.floor(x + 1e-9)          # every partial result is rounded down (INT of the Excel)


def multifamiliar(zone: dict, s: float, p: dict) -> str:
    """'Sí' / 'Condicional' / 'No' of the zone for this lot: some zones admit it only above a lot size
    (productos.multifamiliar_sup_min, e.g. Tigre R4 from 1.000 m2)."""
    min_area = (p.get("multifamiliar_sup_min") or {}).get(zone["zona"])
    return "No" if min_area and s < min_area else zone["multifamiliar"]


def houses_cap(steps: str, s: float) -> int | None:
    """Houses one lot takes by its surface (casas_por_lote "400:2;550:3;700:", San Fernando Código 3.5.6.7): the n of
    the largest area the lot exceeds, None = no cap (the density decides), 1 below the first."""
    cap = 1
    for step in steps.split(";"):
        area, _, n = step.partition(":")
        if s > float(area):
            cap = int(n) if n.strip() else None
    return cap


def density_boost(zone: dict, s: float, front: float | None, p: dict) -> float:
    """Premios raise the density in the same % as the FOT where the code says so (San Fernando, Código 3.20.4:
    productos.premio_ley_8912.densidad): fot_max / fot when the premios are feasible on this lot, else 1."""
    if not (p.get("premio_ley_8912") or {}).get("densidad") or not premio_factible(zone, s, front, p):
        return 1.0
    return _f(zone["fot_max"]) / _f(zone["fot"]) if _f(zone["fot"]) else 1.0


def units(zone: dict, s: float, front: float | None, p: dict) -> dict:
    """Units of each product for one row of normativa_zonas.csv. None = the zone doesn't allow that product.
    Unknown front: surface only (never lose an opportunity; the Excel shows 'sin frente' instead)."""
    out = dict.fromkeys(PRODUCTS)
    out["requiere_cloaca"] = False
    if zone["regla_unidades"] != NO_HOUSING:
        lot_area, lot_width = _f(zone["subdiv_sup_min"]), _f(zone["subdiv_ancho_min"])
        unit_area, unit_width = _f(zone["m2_terreno_por_unidad"]), _f(zone["ancho_min_unidad"])
        boost = density_boost(zone, s, front, p)
        if lot_area and lot_width:
            out["lotes_frente_propio"] = _floor(s / lot_area) if front is None else \
                min(_floor(s / lot_area), _floor(front / lot_width))
        if lot_area and s >= p["sup_min_loteo_calle"]:
            out["lotes_calle_interna"] = _floor(s * (1 - p["pct_calle"]) / lot_area)
        steps = zone.get("casas_por_lote") or ""
        if steps and unit_area:  # San Fernando (Gonzalo, 26/11/2026): houses on the lot by right, by its surface and
            by_density = _floor(s * boost / unit_area)                      # the density (Código 3.5.6.7, 3.9.1.13)
            cap = houses_cap(steps, s)
            out["agrupadas_calle"] = by_density if cap is None else min(cap, by_density)
        elif unit_area and unit_width:
            out["agrupadas_calle"] = _floor(s / unit_area) if front is None else \
                min(_floor(s / unit_area), _floor(front / unit_width))
        if unit_area:            # Tigre, Código art. 71: a condominium of houses needs 400 m2 per house with water and
            common = _f(zone.get("m2_unidad_acceso_comun")) or \
                max(unit_area, p.get("m2_min_agrupadas_acceso_comun") or 0)  # sewers (Gonzalo, 24/11/2026)
            out["agrupadas_acceso_comun"] = _floor(s / common)
        if multifamiliar(zone, s, p) == "Sí":
            potential, net = _f(zone["densidad_neta_potencial"]), _f(zone["densidad_neta"])
            if "N = sup/" in zone["regla_unidades"] and unit_area:          # Rm4: N = sup/150 even multifamiliar
                out["multifamiliar_unidades"] = _floor(s / unit_area)
            elif potential or net:
                out["multifamiliar_unidades"] = _floor((potential or net) * boost * s / 10000 /
                                                       p["personas_por_unidad"])
                out["requiere_cloaca"] = bool(potential)                   # potential density needs sewers
            elif unit_area:
                out["multifamiliar_unidades"] = _floor(s / unit_area)
        ue = _f(zone["densidad_ue"])
        if ue and s >= p["sup_min_ue"]:
            out["ue_unidades"] = _floor(ue * s / 10000 / p["personas_por_unidad"])
    out["unidades_por_derecho"] = max(out[k] or 0 for k in BY_RIGHT)
    out["unidades_con_aprobacion"] = max([out["unidades_por_derecho"]] + [out[k] or 0 for k in WITH_APPROVAL])
    return out


def best_product(u: dict) -> str:
    if u["unidades_por_derecho"]:
        return PRODUCT_NAMES[max(BY_RIGHT, key=lambda k: u[k] or 0)]
    if u["unidades_con_aprobacion"]:
        return PRODUCT_NAMES[max(WITH_APPROVAL, key=lambda k: u[k] or 0)] + " (con aprobación)"
    return ""


def premio_factible(zone: dict, s: float, front: float | None, p: dict) -> bool:
    """Premios of Art. 47 Ley 8912 (fot_max of the zone, flag premio_ley_8912) count when the lot is big enough to
    earn them (wide lot, free perimeter, setbacks): surface >= N minimum lots and, if the front is known, front >=
    N minimum fronts (productos.premio_ley_8912.parcelas_min; without that key premios never count)."""
    n = (p.get("premio_ley_8912") or {}).get("parcelas_min")
    if not n or "premio_ley_8912" not in zone["flags"] or not _f(zone["fot_max"]):
        return False
    lot_area, lot_width = _f(zone["subdiv_sup_min"]), _f(zone["subdiv_ancho_min"])
    return (not lot_area or s >= n * lot_area) and (front is None or not lot_width or front >= n * lot_width)


def _fot_multi(zone: dict, s: float = 0, front: float | None = None, p: dict | None = None) -> float | None:
    """FOT for multifamiliar. Where the maximum only needs sewers (Rma5, Cma4: flag requiere_cloaca_para_max) the
    maximum is used, like the potential density, and the listing carries that flag. Same with feasible premios of
    the Ley 8912 (Tigre)."""
    use_max = "requiere_cloaca_para_max" in zone["flags"] or premio_factible(zone, s, front, p or {})
    return _f(zone["fot_max" if use_max else "fot"]) or _f(zone["fot"])


def fos_by_setbacks(zone: dict, s: float, front: float | None) -> float | None:
    """FOS the setbacks of the zone sheet leave on this lot (Tigre, Gonzalo 24/11/2026), or None if unknown (no front,
    or the zone has no setbacks in normativa_zonas.csv). Rear: (depth - base) / 2, at least 3 m and at most 15 m in
    residential zones / 20 m elsewhere (Código, art. 46), down to retiro_fondo_min where the sheet lets the building
    take the rear setback to complete the FOS. Side: retiro_bilateral on each side, or max(min, % of the width) on one
    side for lots wider than 11 m."""
    base, ahead = _f(zone.get("retiro_fondo_base")), _f(zone.get("retiro_frente"))
    if not front or not s or base is None or ahead is None:
        return None
    depth = s / front
    rear = min(max(3.0, (depth - base) / 2), 15.0 if zone["zona"].startswith("R") else 20.0)
    if _f(zone.get("retiro_fondo_min")) is not None:
        rear = min(rear, _f(zone["retiro_fondo_min"]))
    both, share, least = _f(zone.get("retiro_bilateral")), _f(zone.get("retiro_lateral_pct")), _f(zone.get("retiro_lateral_min"))
    side = 2 * both if both else max(least or 0, share / 100 * front) if share and front > 11 else 0.0
    return max(0.0, front - side) * max(0.0, depth - ahead - rear) / s


def _caps(zone: dict, fot: float, r: dict, cfg: dict, s: float | None = None,
          front: float | None = None) -> tuple[float, list[str], bool]:
    """(FOT that can really be built, why it is lower than the zone's, multifamiliar forbidden by the sector).
      height   zonificacion.alturas_yaml (Tigre, Ord. 4448/26): FOS x (N + 1) levels of "PB + N", where the FOS is the
               effective one (Gonzalo, 24/11/2026): at most 1 - the absorbent share the sector demands (art. 12 g)
               and what the zone's setbacks leave; and N at most what the width of the street allows (art. 12 k:
               productos.art_12k)
      density  productos.m2_por_habitante (Tigre, Gonzalo 19/11/2026: 30; San Fernando 26/11/2026): inhabitants
               of the zone's density (with sewers if it has a potential one; raised by feasible premios where
               productos.premio_ley_8912.densidad) x m2 per inhabitant
    Without those keys (San Isidro) the FOT doesn't change."""
    limits, forbidden = [], False
    lat, lon = r.get("lat_usada") or r.get("lat"), r.get("lon_usada") or r.get("lon")
    heights = alturas.for_config(cfg)
    cap = heights.cap(zone["zona"], r.get("localidad"), lat, lon) if heights else None
    alerts, extra = r.setdefault("alertas", []), r.setdefault("flags_extra", [])
    if cap:
        forbidden = cap["sin_multifamiliar"]
        fos = _f(zone["fos"])
        fos_eff, why = fos, []
        if fos and cap.get("fas") and 1 - cap["fas"] < fos_eff:
            fos_eff = 1 - cap["fas"]
            why.append(f"{cap['fas']:.0%} absorbente")
        by_setbacks = fos_by_setbacks(zone, s, front)
        if fos and by_setbacks is not None and by_setbacks < fos_eff:
            fos_eff = by_setbacks
            why.append("retiros de la zona")
        if fos_eff is not None:
            r["fos_efectivo"] = round(fos_eff, 2)
        pb, k12 = cap["pb"], cfg["productos"].get("art_12k")
        env = entorno.for_config(cfg) if k12 else None
        if env:
            street_pb, kind = env.street_cap(lat, lon)
            if street_pb is not None and street_pb < pb:
                pb = street_pb
                extra.append("art_12k_ancho_de_calle")
                alerts.append(f"art_12k_ancho_de_calle ({kind}: PB+{street_pb} en vez de PB+{cap['pb']})")
            if cap["pb"] >= k12["pb_escalonamiento_min"]:
                d = env.avenue_m(lat, lon)
                if d is None or d > 50:
                    extra.append("art_12k_lejos_de_avenida")
                    alerts.append("art_12k_lejos_de_avenida (" + (f"{d:.0f} m" if d is not None else "más de 200 m")
                                  + " de la avenida: entre 50 y 100 m rige una altura intermedia y a más de 100 m la "
                                    "mínima del sector)")
        by_height = fos_eff * (pb + 1) if fos_eff else None
        if by_height and by_height < fot:
            fot = by_height
            used = f"FOS {fos_eff:.2f} ({', '.join(why)})" if why else f"FOS {fos:g}"
            limits.append(f"altura Ord. 4448 PB+{pb} ({cap['fuente']}): {used} x {pb + 1} niveles")
        if cap["aviso"]:
            alerts.append(cap["aviso"])
        if cap["condiciones"]:
            alerts.append(f"condiciones_ord_4448 ({cap['condiciones']})")
        if forbidden:
            alerts.append(f"multifamiliar_prohibido_ord_4448 ({cap['fuente']})")
    per_person = cfg["productos"].get("m2_por_habitante")
    density = (_f(zone["densidad_neta_potencial"]) or _f(zone["densidad_neta"]) or 0) * \
        density_boost(zone, s or 0, front, cfg["productos"])
    if per_person and density and density * per_person / 10000 < fot:
        fot = density * per_person / 10000
        limits.append(f"densidad {density:g} hab/ha x {per_person:g} m2/hab")
    return fot, limits, forbidden


def _lots(u: dict) -> int:
    return max(u[k] or 0 for k in LOTS)


def _lots_approval(u: dict) -> int:
    return max([_lots(u)] + [u[k] or 0 for k in WITH_APPROVAL])


def front_matters(r: dict, normativa: dict, p: dict) -> bool:
    """A nearby zone counts lots or houses and the surface alone gives enough of them: the front can decide."""
    rows = [row for z in (r.get("zonas_candidatas") or "").split(",") if z for row in normativa.get(z, [])]
    return any(_lots(units(x, r["superficie_m2"], None, p)) >= p["unidades_min"] for x in rows)


def lot_product(r: dict) -> str:
    """Houses or lots: the product behind unidades_loteo."""
    if (r.get("agrupadas_calle") or 0) >= (r.get("lotes_frente_propio") or 0):
        return PRODUCT_NAMES["agrupadas_calle"]
    return PRODUCT_NAMES["lotes_frente_propio"]


def _evaluate_products(r: dict, cfg: dict, normativa: dict, medians: dict) -> dict:
    c, p = cfg["criterio"], cfg["productos"]
    out = {"m2_construibles": None, "incidencia_usd_m2": None, "resultado": "descartado", "via": ""}
    if r.get("motivo_descarte"):
        return out
    s, price, front = r["superficie_m2"], r["precio_usd"], r.get("frente_m")
    if s < cfg["zonificacion"]["superficie_min_prefiltro"]:
        out["motivo_descarte"] = "superficie_menor_prefiltro"
        return out
    rows = [row for z in (r.get("zonas_candidatas") or "").split(",") if z for row in normativa.get(z, [])]
    lat, lon = r.get("lat_usada") or r.get("lat"), r.get("lon_usada") or r.get("lon")
    heights = alturas.for_config(cfg)

    def in_sector(x: dict) -> bool:
        """Rows valid only inside a sector of the Ord. 4448 with height (Tigre R1a / R3b, Gonzalo 24/11/2026)."""
        if "solo_en_sector_4448" not in x["flags"]:
            return True
        cap = heights.cap(x["zona"], r.get("localidad"), lat, lon) if heights else None
        return bool(cap and cap["en_poligono"] and not cap["sin_multifamiliar"] and cap["pb"] >= 3)
    rows = [x for x in rows if in_sector(x)]
    if not rows:
        out["motivo_descarte"] = "zona_sin_normativa"
        return out
    extra = r.setdefault("flags_extra", [])
    total = s
    sirga, env = p.get("sirga"), entorno.for_config(cfg)
    water = env.water_m(lat, lon) if sirga and env else None
    if water:        # camino de sirga (Gonzalo, 24/11/2026): the 15 m strip along the bank is not usable
        strip = min(sirga["ancho_m"] * (front or math.sqrt(s)), sirga["descuento_max"] * s)
        s = total - strip
        out["superficie_util_m2"] = round(s)
        extra.append("camino_de_sirga")
        r.setdefault("alertas", []).append(
            f"camino_de_sirga ({water[1]} a {water[0]:.0f} m del punto: se descuentan {strip:.0f} m2 de la franja de "
            f"{sirga['ancho_m']:g} m desde la ribera; verificar si el lote es frentista)")
    housing = [x for x in rows if x["regla_unidades"] != NO_HOUSING]
    evals = [(x, units(x, s, front, p)) for x in rows]
    hits, near = [], []

    # vía multifamiliar: highest FOT among the nearby zones that allow it (Condicional: at most a near miss)
    multi = [(x, u) for x, u in evals if multifamiliar(x, s, p) == "Sí" and _fot_multi(x, s, front, p)] or \
            [(x, u) for x, u in evals if multifamiliar(x, s, p) == "Condicional" and _fot_multi(x, s, front, p)]
    zm, um = max(multi, key=lambda t: _fot_multi(t[0], s, front, p)) if multi else (None, None)
    if zm:
        out["zona_fot_usado"], out["fot_usado"] = zm["zona"], _fot_multi(zm, s, front, p)
        if premio_factible(zm, s, front, p):
            r.setdefault("alertas", []).append("premio_ley_8912_aplicado")
    elif normativa.get(r.get("zona_fot_usado") or ""):         # no multifamiliar nearby: FOT only as a reference
        out["zona_fot_usado"] = normativa[r["zona_fot_usado"]][0]["zona"]
    fot = out.get("fot_usado") or r.get("fot_usado")
    forbidden = False
    if zm and fot:                   # height (Tigre: Ord. 4448/26) and density can leave part of the FOT unused
        fot, limits, forbidden = _caps(zm, fot, r, cfg, s, front)
        out["fos_efectivo"] = r.pop("fos_efectivo", None)
        out["fot_efectivo"], out["limite_fot"] = round(fot, 2), "; ".join(limits)
    if fot:
        out["m2_construibles"], out["incidencia_usd_m2"] = round(s * fot), round(price / (s * fot), 1)
    why_multi = "no_admite_multifamiliar"
    if zm and forbidden:
        why_multi = "multifamiliar_prohibido_ord_4448"
    elif zm:
        allowed = multifamiliar(zm, s, p) == "Sí"
        m2, inc = s * fot, price / (s * fot)
        if m2 <= c["m2_construibles_min"]:
            why_multi = "m2_insuficientes"
        elif inc < c["incidencia_max_usd"]:
            (hits if allowed else near).append("multifamiliar" if allowed else "multifamiliar condicional")
        elif inc < c["incidencia_casi_max_usd"] and allowed:
            near.append("multifamiliar")
        else:
            why_multi = "incidencia_alta"

    # vía loteo / agrupadas: lots or houses (flats have their own vía, with its 1.300 m2 minimum), in the nearby
    # zone that yields the most of them
    with_lots = [(x, u) for x, u in evals if any(u[k] is not None for k in LOTS)]
    zl, ul = max(with_lots, key=lambda t: (_lots(t[1]), _lots_approval(t[1]))) if with_lots else (None, None)
    if zl and density_boost(zl, s, front, p) > 1 and "premio_ley_8912_aplicado" not in r.get("alertas", []):
        r.setdefault("alertas", []).append("premio_ley_8912_aplicado")      # San Fernando: more houses (3.20.4)

    # units of every product (Excel: 'Unidades por derecho' / 'con O.T./UE'): the best of both vías
    for k in ("lotes_frente_propio", "lotes_calle_interna", "agrupadas_calle", "agrupadas_acceso_comun"):
        out[k] = ul[k] if ul else None
    out["multifamiliar_unidades"] = um["multifamiliar_unidades"] if um else None
    out["ue_unidades"] = max((u["ue_unidades"] or 0 for u in (um, ul) if u), default=0) or None
    by_right = max(out["multifamiliar_unidades"] or 0, _lots(ul) if ul else 0)
    approval = max([by_right] + [out[k] or 0 for k in WITH_APPROVAL])
    out["unidades_por_derecho"], out["unidades_con_aprobacion"] = by_right, approval
    out["mejor_producto"] = best_product({**out, "unidades_por_derecho": by_right, "unidades_con_aprobacion": approval})
    out["usd_por_unidad_derecho"] = round(price / by_right) if by_right else None
    out["usd_por_unidad_aprobacion"] = round(price / approval) if approval else None
    zu = zl or zm
    out["zona_unidades"], out["relevancia"] = (zu["zona"], zu["relevancia"]) if zu else (None, None)
    out["requiere_cloaca"] = bool(zm) and (um["requiere_cloaca"] or "requiere_cloaca" in zm["flags"])    # _para_max or _multifamiliar
    if front is None and ul and _lots(ul):
        r.setdefault("alertas", []).append("frente_desconocido")

    lots = _lots(ul) if ul else 0
    out["unidades_loteo"] = lots or None
    out["usd_por_unidad_loteo"] = round(price / lots) if lots else None
    unit_area = None
    if zl:           # land per unit of the product: a house of the agrupadas, or a lot of the subdivision
        by_house = (ul["agrupadas_calle"] or 0) >= (ul["lotes_frente_propio"] or 0)
        unit_area = (_f(zl["m2_terreno_por_unidad"]) if by_house else None) or _f(zl["subdiv_sup_min"])
    # small lot of the same localidad; with too few of them, of the whole partido
    where = r.get("localidad") if medians.get(r.get("localidad") or "") else PARTIDO
    comp = medians.get(where)
    out["mediana_usd_m2_lote"] = comp["mediana_usd_m2"] if comp else None
    out["comparables_n"] = comp["n"] if comp else 0
    out["comparables"] = f"{where} {comp['mediana_usd_m2']} USD/m2 ({comp['n']} lotes)" if comp else "sin comparables"
    value = round(comp["mediana_usd_m2"] * unit_area) if comp and unit_area else None
    out["valor_lote_estimado"] = value
    out["ratio_compra_reventa"] = round(price / lots / value, 2) if value and lots else None

    def cheap(n_units: int) -> bool:
        return bool(value) and price / n_units / value <= p["umbral_ratio_loteo"]

    why_lot = ""
    if zl:
        if lots >= p["unidades_min"] and cheap(lots):
            hits.append("loteo_agrupadas")
        elif _lots_approval(ul) >= p["unidades_min"] and cheap(_lots_approval(ul)):
            near.append("loteo_agrupadas solo con aprobación")
        else:
            why_lot = "pocas_unidades" if _lots_approval(ul) < p["unidades_min"] else "usd_por_unidad_alto"

    if out.get("agrupadas_acceso_comun") and p.get("m2_min_agrupadas_acceso_comun"):
        extra.append("agrupadas_art_71")
    if p.get("senales_loteo") and out.get("lotes_calle_interna"):     # Tigre, Gonzalo 24/11/2026 (10.7 #5)
        extra += p["senales_loteo"].get("flags") or ["cesion_ley_8912", "relleno_cota_375"]
        if total > p["senales_loteo"]["cerrado_sup_min"]:
            extra.append("cesion_ley_14449")
    out["gran_predio"] = bool(housing) and total >= p["sup_min_gran_predio"]
    if hits:
        out["resultado"], out["via"] = "oportunidad", " + ".join(hits)
    elif near:
        out["resultado"], out["via"] = "casi", " + ".join(near)
    elif out["gran_predio"]:
        out["resultado"], out["via"] = "gran_predio", "gran_predio"
    elif not housing:
        out["motivo_descarte"] = "zona_sin_vivienda"
    else:
        out["motivo_descarte"] = " + ".join(x for x in (why_multi, why_lot) if x)
    return out
