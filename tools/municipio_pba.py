"""Build the data of a Provincia de Buenos Aires partido for the 'zonas' engine (Fase 0 of a new municipio).

Sources (public, one download each; re-run to refresh):
  - Zoning: UrbaSIG of the Provincia (WFS urbasig:_zonificacion, filter partido='<code>'): zone polygons with
    FOS, FOT, density (hab/ha), minimum lot area and front, units per m2 of lot, observations, ordinance.
  - Localidades and streets: OpenStreetMap (Overpass), for the partido boundary, the comparables per localidad
    and listings without street number.

Usage:
    python tools/municipio_pba.py tigre
    python tools/municipio_pba.py san_fernando
    python tools/municipio_pba.py tigre --solo-normativa    # only normativa_zonas.csv, from the saved raw layer
Output (municipios/<slug>/):
    fuentes/urbasig_zonificacion.geojson   raw layer, as downloaded
    zonas.geojson                          one feature per zone polygon: {zona}
    normativa_zonas.csv                    same columns as data/normativa_zonas.csv (San Isidro), from UrbaSIG
    localidades.geojson                    {barrio}: OSM localidades, clipped to the zoned (continental) area
    calles.geojson                         {nombre}: named OSM streets of the partido

How a UrbaSIG zone becomes a normativa row (ZANARA's products, values of each partido; decisions to validate
with Gonzalo, listed in the municipio's NORMATIVA.md):
  - FOT = max(FOT actual, FOT potencial); density = max(density actual, potential). Premiums (fotp_prem,
    denp_prem: Art. 47 Ley 8912) are NOT used for the units: they go as the flag premio_ley_8912.
  - FOT 0 or no data -> no housing as a product (parks, uso específico, barrios cerrados, clubes de campo...).
  - Multifamiliar: by MULTI_RULES of the partido (designation prefixes), else by density:
    >= 300 hab/ha 'Sí', 150-299 'Condicional' (a hit there is at most a near miss), < 150 'No'.
  - Lots with own front: minimum lot area (sm) and front (lm) of the zone.
  - Houses grouped on the lot (agrupadas): only where UrbaSIG gives 'una vivienda cada X m2 de lote' (um2),
    with a 5 m own front per house (the same minimum ZANARA used in San Isidro).
"""

import csv
import json
import sys
from pathlib import Path

import requests
from shapely.geometry import mapping, shape
from shapely.ops import linemerge, polygonize, unary_union

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "zanara-scouting/0.2"}
URBASIG = "https://urbasig.mgob.gba.gob.ar/geoserver/urbasig/wfs"
OVERPASS = "https://overpass-api.de/api/interpreter"
NO_HOUSING = "Sin vivienda como producto"
COLUMNS = ["zona", "grupo", "relevancia", "fot", "fot_max", "fos", "altura_max", "multifamiliar", "regla_unidades",
           "m2_terreno_por_unidad", "ancho_min_unidad", "sup_propia_min_unidad", "acceso_directo_requerido",
           "subdiv_ancho_min", "subdiv_sup_min", "densidad_neta", "densidad_neta_potencial", "densidad_ue", "flags",
           "fuente", "notas"]
ANCHO_CASA_AGRUPADA = 5

PARTIDOS = {
    "tigre": {
        "codigo": "057", "osm": 2411762,
        # designation prefix -> multifamiliar (first match wins). Central zones admit it although UrbaSIG also
        # gives um2 for them. Gonzalo, 14/11/2026: C1-C4 only with water and sewers (flag); R4 only on lots
        # > 1.000 m2 (productos.multifamiliar_sup_min in municipio.yaml).
        "multi": [("TC", "Sí"), ("Tr", "Sí"), ("C", "Sí"), ("UR", "Sí"), ("RM", "Sí"), ("R5", "Sí"), ("R6", "Sí"),
                  ("R7", "Sí"), ("R8", "Sí"), ("R4", "Sí"), ("R1u", "No"), ("R2", "No"), ("R3", "No"),
                  ("RP", "No"), ("I", "No"), ("E", "No"), ("A", "No")],
        # never housing as a product: barrios cerrados and clubes de campo already subdivided, parks, special uses
        "cloaca": ["C1", "C2", "C3", "C4"],      # multifamiliar needs water and sewers (observation of the zone)
        "sin_vivienda": ["CC", "R1a", "R1b", "R3b", "PR", "PU", "PT", "PA", "UE", "P"],
        # Gonzalo, 19/11/2026: the official zone sheets of tigre.gob.ar ("Planillas de indicadores urbanísticos",
        # municipios/tigre/GUIA_NORMATIVA.md) override UrbaSIG. Designation prefix -> columns (first match wins).
        #   C1-C4: FOT with water and sewers; density 150 without them, 2.000 with them (C3: 800)
        #   C2 and TC: the residential FOT is 2,5 (3,0 is for the commercial use); premios x1,5 like the others
        #   R1u: multifamiliar on lots from 600 m2 (productos.multifamiliar_sup_min), one dwelling every 300 m2,
        #        with water and sewers (Ord. 3749/20)
        #   R2, R3, R5: multifamiliar with water and sewers, density 400 (12 m with free ground floor, Dec. 1000/16)
        #   R4: density 400 (UrbaSIG says 140)
        "planillas": [
            ("C1", {"fot": 2.4, "fot_max": 3.6, "densidad_neta": 150, "densidad_neta_potencial": 2000}),
            ("C2", {"fot": 2.5, "fot_max": 3.75, "densidad_neta": 150, "densidad_neta_potencial": 2000}),
            ("C3", {"fot": 2.4, "fot_max": 3.6, "densidad_neta": 150, "densidad_neta_potencial": 800}),
            ("C4", {"fot": 2.4, "fot_max": 3.6, "densidad_neta": 150, "densidad_neta_potencial": 2000}),
            ("TC", {"fot": 2.5, "fot_max": 3.75}),
            ("R4", {"densidad_neta": 400}),        # planilla: 400 hab/ha (UrbaSIG dice 140)
            ("R1u", {"multifamiliar": "Sí", "m2_terreno_por_unidad": 300,
                     "regla_unidades": "N = sup/300 (multifamiliar con agua y cloaca, Ord. 3749/20)",
                     "flags+": "requiere_cloaca_multifamiliar"}),
            ("R2", {"multifamiliar": "Sí", "densidad_neta": 140, "densidad_neta_potencial": 400,
                    "regla_unidades": "Densidad neta de la zona (multifamiliar)", "flags+": "requiere_cloaca_multifamiliar"}),
            ("R3", {"multifamiliar": "Sí", "densidad_neta": 140, "densidad_neta_potencial": 400,
                    "regla_unidades": "Densidad neta de la zona (multifamiliar)", "flags+": "requiere_cloaca_multifamiliar"}),
            ("R5", {"multifamiliar": "Sí", "densidad_neta": 140, "densidad_neta_potencial": 400,
                    "regla_unidades": "Densidad neta de la zona (multifamiliar)", "flags+": "requiere_cloaca_multifamiliar"}),
        ],
    },
    "san_fernando": {
        "codigo": "096", "osm": 2443418,
        # Gonzalo, 14/11/2026 (checked in the code): C3/C3A admit multifamiliar, R3/R3A/R3B/R4 don't
        "multi": [("C3", "Sí"), ("R3", "No"), ("R4", "No"), ("DUE", "Condicional"), ("BPN", "No"), ("RRE", "No")],
        "sin_vivienda": ["I1", "IE", "UE", "ESECS", "EVUP", "RC2", "Z C", "ACCESO", "AREA DE ISLAS", "R4Ue"],
    },
}


def _f(v):
    try:
        return float(v) if v not in (None, "", "-") else 0.0
    except (TypeError, ValueError):
        return 0.0


def _num(x: float) -> str:
    return "" if not x else (f"{x:g}")


def urbasig(code: str) -> dict:
    r = requests.get(URBASIG, params={"service": "WFS", "version": "2.0.0", "request": "GetFeature",
                                      "typeNames": "urbasig:_zonificacion", "outputFormat": "application/json",
                                      "CQL_FILTER": f"partido='{code}'"}, headers=UA, timeout=300)
    r.raise_for_status()
    return r.json()


def overpass(query: str) -> list[dict]:
    r = requests.post(OVERPASS, data={"data": query}, headers=UA, timeout=300)
    r.raise_for_status()
    return r.json()["elements"]


def _relation_polygon(rel: dict):
    lines = [[(p["lon"], p["lat"]) for p in m["geometry"]] for m in rel.get("members", [])
             if m.get("type") == "way" and m.get("role") in ("outer", "") and m.get("geometry")]
    from shapely.geometry import LineString
    merged = linemerge([LineString(ln) for ln in lines if len(ln) > 1])
    return unary_union(list(polygonize(merged)))


def _starts(name: str, prefixes) -> bool:
    return any(name == p or name.startswith(p) for p in prefixes)


def zone_row(name: str, props: list[dict], conf: dict) -> dict:
    """The most favorable version of a designation (a few appear twice with different values)."""
    p = max(props, key=lambda q: (max(_f(q["fota"]), _f(q["fotp"])), max(_f(q["dena"]), _f(q["denp"]))))
    fot = max(_f(p["fota"]), _f(p["fotp"]))
    dens = max(_f(p["dena"]), _f(p["denp"]))
    um2, sm, lm = _f(p["um2"]), _f(p["sm"]), _f(p["lm"])
    prem = max(_f(p.get("fotp_prem")), 0)
    obs = " ".join((p.get("observacio") or "").split())
    housing = fot > 0 and not _starts(name, conf["sin_vivienda"])
    multi = next((m for pre, m in conf["multi"] if name.startswith(pre)), None)
    if multi is None:
        multi = "Sí" if dens >= 300 else "Condicional" if dens >= 150 else "No"
    if not housing:
        multi = "No"
    flags = []
    if housing and prem > fot:
        flags.append("premio_ley_8912")
    if housing and obs:
        flags.append("ver_observacion_zona")
    if housing and multi == "Sí" and _starts(name, conf.get("cloaca", [])):
        flags.append("requiere_cloaca_multifamiliar")
    if not housing:
        rule = NO_HOUSING
    elif multi in ("Sí", "Condicional"):
        rule = "Densidad neta de la zona (multifamiliar)"
    elif um2:
        rule = f"Una vivienda cada {um2:g} m2 de lote"
    else:
        rule = "Unifamiliar por parcela"
    ords = " ".join(x for x in (p.get("ord_ma"), p.get("ord_mod"), p.get("dec_mod")) if x)
    row = {
        "zona": name, "grupo": (p.get("descripcio") or "").strip().title(),
        "relevancia": "Nula" if not housing else "Alta" if multi == "Sí" else "Media",
        "fot": _num(fot) if housing else "", "fot_max": _num(prem) if prem > fot else "", "fos": _num(_f(p["fos"])),
        "altura_max": (p.get("hmax") or "").strip() if isinstance(p.get("hmax"), str) else _num(_f(p.get("hmax"))),
        "multifamiliar": multi, "regla_unidades": rule,
        "m2_terreno_por_unidad": _num(um2) if housing and um2 else "",
        "ancho_min_unidad": str(ANCHO_CASA_AGRUPADA) if housing and um2 else "",
        "sup_propia_min_unidad": "", "acceso_directo_requerido": "no",
        "subdiv_ancho_min": _num(lm) if housing else "", "subdiv_sup_min": _num(sm) if housing else "",
        "densidad_neta": _num(dens) if housing else "", "densidad_neta_potencial": "", "densidad_ue": "",
        "flags": ";".join(flags),
        "fuente": f"UrbaSIG {p.get('fecha_ac') or ''} {ords}".strip(),
        "notas": " | ".join(x for x in (obs, f"premios Art. 47: FOT {prem:g}, densidad {_f(p.get('denp_prem')):g}"
                                        if prem > fot else "", p.get("des_cat") or "") if x),
    }
    fix = next((cols for pre, cols in conf.get("planillas", []) if name.startswith(pre)), None) if housing else None
    if fix:
        for col, value in fix.items():
            if col == "flags+":
                row["flags"] = ";".join(dict.fromkeys(x for x in row["flags"].split(";") + [value] if x))
            else:
                row[col] = _num(value) if isinstance(value, (int, float)) else value
        if row["multifamiliar"] == "Sí":
            row["relevancia"] = "Alta"
        row["fuente"] += " + planilla tigre.gob.ar (19/11/2026)"
    return row


def main(slug: str, only_normativa: bool = False) -> None:
    conf = PARTIDOS[slug]
    out = ROOT / "municipios" / slug
    (out / "fuentes").mkdir(parents=True, exist_ok=True)
    raw_path = out / "fuentes" / "urbasig_zonificacion.geojson"
    if only_normativa:
        raw = json.loads(raw_path.read_text(encoding="utf-8"))
    else:
        raw = urbasig(conf["codigo"])
        raw_path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    feats, by_name = [], {}
    for f in raw["features"]:
        name = (f["properties"].get("designacio") or "").strip()
        if not name or not f.get("geometry"):
            continue
        by_name.setdefault(name, []).append(f["properties"])
        feats.append({"type": "Feature", "geometry": f["geometry"], "properties": {"zona": name}})
    (out / "zonas.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
                                       encoding="utf-8")
    rows = [zone_row(n, ps, conf) for n, ps in sorted(by_name.items())]
    with open(out / "normativa_zonas.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)
    if only_normativa:
        print(f"{slug}: {len(rows)} zonas -> {out / 'normativa_zonas.csv'}")
        return
    zoned = unary_union([shape(f["geometry"]) for f in feats]).buffer(0.003)        # ~300 m: continental, zoned area

    rels = overpass(f"""[out:json][timeout:240];
rel({conf['osm']});map_to_area->.p;
rel(area.p)["boundary"="administrative"]["admin_level"~"^(8|9)$"];
out geom;""")
    locs = []
    for rel in rels:
        poly = _relation_polygon(rel).intersection(zoned)
        if poly.is_empty or poly.area < 1e-6:
            continue                                   # islands of the Delta, or no zoning at all
        locs.append({"type": "Feature", "geometry": mapping(poly), "properties": {"barrio": rel["tags"]["name"]}})
    if not locs:          # no localidades in OSM: the whole zoned area as one
        partido = _relation_polygon(overpass(f"[out:json];rel({conf['osm']});out geom;")[0]).intersection(zoned)
        locs = [{"type": "Feature", "geometry": mapping(partido), "properties": {"barrio": slug.replace('_', ' ').title()}}]
    (out / "localidades.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": locs}, ensure_ascii=False),
                                             encoding="utf-8")
    ways = overpass(f"""[out:json][timeout:240];
rel({conf['osm']});map_to_area->.p;
way(area.p)["highway"]["name"];
out geom;""")
    streets = [{"type": "Feature",
                "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in w["geometry"]]},
                "properties": {"nombre": w["tags"]["name"]}} for w in ways if w.get("geometry") and len(w["geometry"]) > 1]
    (out / "calles.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": streets}, ensure_ascii=False),
                                        encoding="utf-8")
    print(f"{slug}: {len(feats)} polígonos, {len(rows)} zonas, {len(locs)} localidades "
          f"({', '.join(sorted(l['properties']['barrio'] for l in locs))}), {len(streets)} tramos de calle -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], "--solo-normativa" in sys.argv[2:])
