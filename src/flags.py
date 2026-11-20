"""Incentives and traps of the C.O.U. that change a lot's potential, detected with the data the pipeline has.

Each flag carries its article (Excel, tab 'Incentivos y trampas'). They inform the manual check of each hit:
they never change the units, because they are discretionary or need to be verified by hand.
"""

import re

from .locate import _plain

ARTICLES = {
    "galpon_no_conforme": "hasta +30% de FOT y unidades, Art. 1.2.4.3 C",
    "pasivo_ambiental": "Art. 1.2.2.15 inc. 10",
    "gran_predio_3000": "Art. 1.2.1.19",
    "manzana_7400": "Arts. 1.2.3.1 y 1.2.1.14 inc. 2",
    "ue_10000": "Art. 1.2.1.1",
    "frentista_via_rapida": "hasta +100% de agrupadas, Art. 1.2.1.16",
    "lindero_zona_c_o_i": "Arts. 1.2.1.16 y 1.2.1.20 a",
    "borde_de_zona": "posible predio en dos zonas, Art. 1.2.2.7",
    "requiere_cloaca_para_max": "multifamiliar solo con agua y cloaca, hoja de zona",
    "barranca": "Arts. 1.2.1.10.2 d y 1.2.1.20 b",
    "cota_ign": "cota mínima de edificación, hoja de zona",
    "inundable": "hoja de zona",
    "relleno_sanitario": "hoja de zona",
    "patrimonial": "tratamiento particular, hoja de zona",
    "proyecto_integral_7400": "Art. 1.2.1.14 inc. 2",
    "dos_frentes": "esquina o doble frente: más frente a la calle que el informado",
}
INDUSTRIAL = re.compile(r"galp[oó]n|f[aá]brica|dep[oó]sito|nave industrial|planta industrial|industrial", re.I)
TWO_FRONTS = re.compile(r"doble frente|dos frentes|esquina|salida a dos calles|contrafrente sobre (la )?calle", re.I)


def _rules(zone: str, normativa: dict) -> set:
    return {(x["fot"], x["regla_unidades"], x["multifamiliar"]) for x in normativa.get(zone, [])}


def _two_zones(r: dict, normativa: dict, max_m: float) -> bool:
    """Near the border of its zone and the zone next door has other indicators (outside every zone: unknown)."""
    if r.get("distancia_borde_m") is None:
        return True
    near = [z for z in (r.get("zonas_cercanas") or "").split(",") if z]
    return r["distancia_borde_m"] <= max_m and any(_rules(z, normativa) != _rules(r.get("zona"), normativa)
                                                    for z in near)


def flags(r: dict, normativa: dict, cfg: dict) -> list[str]:
    """'name (article)' for every incentive or trap that applies to an evaluated listing."""
    p, f = cfg["productos"], cfg["productos"]["flags"]
    s = r.get("superficie_m2") or 0
    by_name = {row["zona"]: row for rows in normativa.values() for row in rows}
    zones = [by_name[z] for z in dict.fromkeys((r.get("zona_unidades"), r.get("zona_fot_usado"))) if z in by_name]
    zone = zones[0]["zona"] if zones else ""
    point_zone = r.get("zona") or ""
    out = []
    industrial = r.get("tipologia") == "galpon" or \
        (r.get("tipologia") != "casa" and bool(INDUSTRIAL.search(r.get("titulo") or "")))   # not "casa con depósito"
    if industrial and zone and not zone.startswith("I"):
        out.append("galpon_no_conforme")
    if industrial or any("pasivo_ambiental" in z["flags"] for z in zones):
        out.append("pasivo_ambiental")
    if s >= p["sup_min_gran_predio"]:
        out.append("gran_predio_3000")
    if s >= p["sup_min_manzana"]:
        out.append("manzana_7400")
    if s >= p["sup_min_ue"]:
        out.append("ue_10000")
    if (zone.startswith("Rb") or zone == "Rmb2") and any(c in _plain(r.get("direccion") or "") for c in f["calles_via_rapida"]):
        out.append("frentista_via_rapida")
    if point_zone.startswith("R") and point_zone != "Ru" and r.get("distancia_zona_c_o_i_m") is not None:
        out.append("lindero_zona_c_o_i")
    if r.get("flag_confianza") in ("exacta", "geocodificada") and _two_zones(r, normativa, f["distancia_borde_zona_m"]):
        out.append("borde_de_zona")
    text = f"{r.get('titulo') or ''} {r.get('descripcion') or ''}"
    if TWO_FRONTS.search(text):
        out.append("dos_frentes")
    for name, pattern in (f.get("patrones_texto") or {}).items():     # per municipio (Tigre: proyecto aprobado)
        if re.search(pattern, text, re.I):
            out.append(name)
    for z in zones:
        out += [x for x in z["flags"].split(";") if x and x not in ("pasivo_ambiental", "requiere_cloaca_multifamiliar")]
    if r.get("requiere_cloaca"):
        out.append("requiere_cloaca_para_max")
    if "premio_ley_8912_aplicado" in (r.get("alertas") or []):
        out.append("premio_ley_8912_aplicado")
    arts = {**ARTICLES, **(f.get("articulos") or {})}          # each municipio cites its own code
    return [f"{x} ({arts[x]})" if arts.get(x) else x for x in dict.fromkeys(out)]
