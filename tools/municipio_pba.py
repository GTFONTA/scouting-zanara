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
    python tools/municipio_pba.py tigre --solo-calles       # only calles.geojson (one Overpass query)
    python tools/municipio_pba.py san_fernando --solo-rios  # only fuentes/rios_osm.geojson (camino de sirga)
Output (municipios/<slug>/):
    fuentes/urbasig_zonificacion.geojson   raw layer, as downloaded
    zonas.geojson                          one feature per zone polygon: {zona}
    normativa_zonas.csv                    same columns as data/normativa_zonas.csv (San Isidro), from UrbaSIG
    localidades.geojson                    {barrio}: OSM localidades, clipped to the zoned (continental) area
    calles.geojson                         {nombre, tipo, ancho}: named OSM streets of the partido (tipo = OSM
                                           highway class, ancho = OSM width tag when mapped: Ord. 4448 art. 12 k)
    fuentes/rios_osm.geojson               {nombre, tipo}: OSM rivers, canals and streams (--solo-rios; San Fernando)

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
           "fuente", "notas",
           # setbacks of the zone sheet, for the effective FOS (Tigre, Gonzalo 24/11/2026; empty = unknown):
           #   frente m; fondo (L - base)/2, at least 3 m and at most 15 m (residential) / 20 m (Código, art. 46);
           #   fondo_min: the sheet lets the building take the rear setback down to this to complete the FOS;
           #   lateral: max(min, % of the width) on one side (none on lots up to 11 m), or `bilateral` m each side
           "retiro_frente", "retiro_fondo_base", "retiro_fondo_min", "retiro_lateral_pct", "retiro_lateral_min",
           "retiro_bilateral",
           # houses on one lot by right (San Fernando, Gonzalo 26/11/2026): "area:n;..." = lots of more than `area` m2
           # take up to n houses (empty n: as many as the density gives, one every m2_terreno_por_unidad); smaller
           # lots one. m2_unidad_acceso_comun: land per house of the condominium with approval (empty: as by right)
           "casas_por_lote", "m2_unidad_acceso_comun"]
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
            # Gonzalo, 24/11/2026 (GUIA_NORMATIVA.md, 10.7 #2): inside Nordelta's neighbourhoods (UR 4.x) the private
            # rules allow one house per lot; every UR zone carries the flag to check Nordelta's plan
            ("UR 4", {"multifamiliar": "No", "regla_unidades": "Unifamiliar por parcela", "relevancia": "Media",
                      "flags+": "verificar_reglamento_nordelta"}),
            ("UR", {"flags+": "verificar_reglamento_nordelta"}),
        ],
        # Setbacks of the zone sheets (planillas; GUIA_NORMATIVA.md, section 2). Prefix -> columns, first match wins.
        "retiros": [
            ("TC", {"retiro_frente": 5, "retiro_fondo_base": 20, "retiro_bilateral": 4}),     # tower on a base
            ("Tr", {"retiro_frente": 5, "retiro_fondo_base": 20, "retiro_bilateral": 4}),
            ("C6", {"retiro_frente": 3, "retiro_fondo_base": 15}),
            ("C", {"retiro_frente": 0, "retiro_fondo_base": 15}),
            ("R6", {"retiro_frente": 0, "retiro_fondo_base": 15, "retiro_fondo_min": 10}),
            ("R1u", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_fondo_min": 5, "retiro_lateral_pct": 20,
                     "retiro_lateral_min": 2.5}),
            ("R2", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_fondo_min": 5, "retiro_lateral_pct": 25,
                    "retiro_lateral_min": 2.5}),
            ("R3", {"retiro_frente": 3, "retiro_fondo_base": 15}),
            ("R4", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_fondo_min": 5, "retiro_lateral_pct": 20,
                    "retiro_lateral_min": 2.5}),
            ("R5", {"retiro_frente": 3, "retiro_fondo_base": 15}),
            ("R7", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_lateral_pct": 20, "retiro_lateral_min": 2.5}),
            ("R8", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_lateral_pct": 20, "retiro_lateral_min": 2.5}),
            ("RM", {"retiro_frente": 3, "retiro_fondo_base": 15, "retiro_lateral_pct": 20, "retiro_lateral_min": 2.5}),
            ("RP", {"retiro_frente": 6, "retiro_fondo_base": 20, "retiro_fondo_min": 6, "retiro_bilateral": 3}),
        ],
        # Rows that the layer doesn't give (Gonzalo, 24/11/2026, GUIA_NORMATIVA.md 10.7 #1 and #2):
        #   R1a / R3b  UrbaSIG marks them as gated neighbourhoods, but the Ord. 4448 gives them height in some
        #              sectors (Benavídez, Dique Luján): there they are valued with the R1 / R3 sheets. The flag
        #              solo_en_sector_4448 makes the engine use the row only inside one of those polygons.
        #   UE 8       Nordelta's Centro Cívico (UM2 of the 4448, PB+12): the indicators of UR 1 C until the plans
        #              particularizados (Ord. 3982/22, 4077/23, 4126/23) are read
        "filas_extra": [
            {"zona": "R1a", "grupo": "R1 (planilla) en sector de la Ord. 4448", "relevancia": "Alta", "fot": 1.2,
             "fos": 0.6, "multifamiliar": "Sí", "regla_unidades": "Densidad neta de la zona (multifamiliar)",
             "m2_terreno_por_unidad": 600, "ancho_min_unidad": 5, "subdiv_ancho_min": 15, "subdiv_sup_min": 600,
             "densidad_neta": 100, "densidad_neta_potencial": 400,
             "flags": "solo_en_sector_4448;requiere_cloaca_multifamiliar",
             "fuente": "planilla R1 tigre.gob.ar + Ord. 4448/26 art. 4 y 5 (24/11/2026)",
             "notas": "Multifamiliar con agua y cloaca (planilla R1, 11.2 d); solo dentro de los sectores R1a con altura",
             "retiro_frente": 3, "retiro_fondo_base": 20, "retiro_fondo_min": 6, "retiro_lateral_pct": 20,
             "retiro_lateral_min": 2.5},
            {"zona": "R3b", "grupo": "R3 (planilla) en sector de la Ord. 4448", "relevancia": "Alta", "fot": 1.2,
             "fot_max": 1.8, "fos": 0.6, "multifamiliar": "Sí", "regla_unidades": "Densidad neta de la zona (multifamiliar)",
             "m2_terreno_por_unidad": 300, "ancho_min_unidad": 5, "subdiv_ancho_min": 12, "subdiv_sup_min": 300,
             "densidad_neta": 140, "densidad_neta_potencial": 400,
             "flags": "solo_en_sector_4448;premio_ley_8912;requiere_cloaca_multifamiliar",
             "fuente": "planilla R3 tigre.gob.ar + Ord. 4448/26 art. 4 (24/11/2026)",
             "notas": "Multifamiliar con agua y cloaca (planilla R3, 11.1 d); solo dentro del sector R3b PB+5",
             "retiro_frente": 3, "retiro_fondo_base": 15},
            {"zona": "UE 8", "grupo": "Centro Cívico Nordelta (UM2, Ord. 4448/26 art. 11)", "relevancia": "Alta",
             "fot": 3, "fos": 0.6, "multifamiliar": "Sí", "regla_unidades": "Densidad neta de la zona (multifamiliar)",
             "densidad_neta": 2000, "flags": "verificar_plan_centro_civico",
             "fuente": "indicadores de UR 1 C (UrbaSIG) a falta de los planes particularizados (24/11/2026)",
             "notas": "Planes particularizados Ord. 3982/22, 4077/23 y 4126/23 sin leer"},
        ],
    },
    "san_fernando": {
        "codigo": "096", "osm": 2443418,
        # Gonzalo, 14/11/2026 (checked in the code): C3/C3A admit multifamiliar, R3/R3A/R3B/R4 don't
        "multi": [("C3", "Sí"), ("R3", "No"), ("R4", "No"), ("DUE", "Condicional"), ("BPN", "No"), ("RRE", "No")],
        # Gonzalo, 26/11/2026 (GUIA_NORMATIVA.md 9, #5 and #6): I2, I2A and DI admit a house only as an annex of the
        # industry (Código 3.5.10.1 and 3.5.10.7); DDP is a finished conjunto that can't be changed (3.14.3)
        "sin_vivienda": ["I1", "IE", "UE", "ESECS", "EVUP", "RC2", "Z C", "ACCESO", "AREA DE ISLAS", "R4Ue",
                         "I2", "DI", "DDP"],
        # Gonzalo, 26/11/2026: the Código de Edificación y Zonificación (Ord. 3603/91, texto ordenado; GUIA_NORMATIVA.md)
        # over UrbaSIG. Designation prefix -> columns (first match wins; "_vivienda": housing although UrbaSIG has no FOT)
        "fuente_planillas": "Código Ord. 3603/91 (26/11/2026)",
        "planillas": [
            # #1: several houses per lot (3.5.6.7): 2 above 400 m2 (the U00 subzone; U0/U1/U2 allow it from 330/250,
            # below the prefilter), 3 above 550, more above 700 by the density (4 people per house): R3A 170 hab/ha
            # = 1 every 235 m2, R3 250 = 160 m2. With approval (PH ordinances in R3: Los Sauces 6003/95, Los Plátanos
            # 6315/96) 320 hab/ha = 125 m2. #3: FOT 1 -> 1,2 with premios (3.5.6.3), density in the same %
            ("R3A", {"relevancia": "Alta", "regla_unidades": "Varias viviendas por lote (Código 3.5.6.7)",
                     "m2_terreno_por_unidad": 235, "casas_por_lote": "400:2;550:3;700:", "m2_unidad_acceso_comun": 125,
                     "fot_max": 1.2,
                     "flags+": "casas_por_lote_3567;uso_complementario_estudio_especial;requiere_cloaca_casas;premio_ley_8912",
                     "notas": "Hasta 2 viviendas > 400 m2, 3 > 550 m2, más > 700 m2 según FOS/FOT/densidad (3.5.6.7); "
                              "densidad 170 hab/ha; FOT 1 hasta 1,2 con premios (3.5.6.3, 3.20)"}),
            ("R3", {"relevancia": "Alta", "regla_unidades": "Varias viviendas por lote (Código 3.5.6.7)",
                    "m2_terreno_por_unidad": 160, "casas_por_lote": "400:2;550:3;700:", "m2_unidad_acceso_comun": 125,
                    "fot_max": 1.2,
                    "flags+": "casas_por_lote_3567;uso_complementario_estudio_especial;requiere_cloaca_casas;premio_ley_8912",
                    "notas": "Hasta 2 viviendas > 400 m2, 3 > 550 m2, más > 700 m2 según FOS/FOT/densidad (3.5.6.7); "
                             "densidad 250 hab/ha con cloaca, 150 con agua sin cloaca; FOT 1 hasta 1,2 con premios"}),
            # #4: BPN, individual or grouped houses (3.9.1.2, 3.9.1.13): FOS 0,35, FOT 0,70, 160 hab/ha = 1 every 250 m2
            ("BPN", {"relevancia": "Alta", "regla_unidades": "Viviendas agrupadas (Código 3.9.1.13)",
                     "m2_terreno_por_unidad": 250, "casas_por_lote": "0:", "fot": 0.7, "fos": 0.35,
                     "flags+": "agrupadas_bpn_3913;saneamiento_obligatorio_bpn",
                     "notas": "Viviendas individuales o agrupadas: FOS 0,35, FOT 0,70 (sin espejos de agua ni "
                              "circulaciones), 160 hab/ha con infraestructura, PB+2 y 10,50 m; 1,5 cocheras y 1 amarra "
                              "por vivienda; saneamiento obligatorio (art. 84 Ley 8912)"}),
            # #6: C4Ue, multifamiliar with free ground floor and 9 m: two floors x FOS 0,6 = 1,2 (3.15.6, 3.15.7); from
            # 15 m and 450 m2 (productos.multifamiliar_sup_min; the front goes as a flag)
            ("C4Ue", {"fot": 1.2, "flags+": "c4ue_multifamiliar_3152",
                      "notas": "FOT 2 para multifamiliar, pero con PB libre para estacionamiento y 9 m: 2 pisos x FOS "
                               "0,6 = 1,2 (3.15.6 y 3.15.7); multi solo con frente >= 15 m y >= 450 m2; deptos de 3 "
                               "ambientes >= 70 m2"}),
            # #7: Parque de la Reconquista (Ord. 5951/95): the residential sector RUM (houses on 18 x 500; multifamiliar
            # FOT 0,8, 600 hab/ha, from 3.000 m2); the layer can't tell the subzones apart (flag)
            ("RR: RUM", {"_vivienda": True, "relevancia": "Media", "fot": 0.8, "fos": 0.3, "multifamiliar": "Sí",
                         "regla_unidades": "Densidad neta de la zona (multifamiliar)", "densidad_neta": 600,
                         "subdiv_ancho_min": 18, "subdiv_sup_min": 500, "flags+": "verificar_subzona_reconquista",
                         "notas": "Indicadores del sector RUM de la Ord. 5951/95 (uni 18 x 500 m2, FOS 0,4, FOT 0,6; "
                                  "multi desde 3.000 m2, FOS 0,3, FOT 0,8, 600 hab/ha, PB+4); el resto de las "
                                  "subzonas (CR, VOAD, ZEU, ZUM, CRP) tiene otros indicadores"}),
            ("RRE", {}),
            # #6: RR (3.5.8): multifamiliar only on lots from 3.000 m2 (FOS 0,2, FOT 1,4, 400 hab/ha, 30 m); smaller
            # lots one house (FOT 0,6)
            ("RR", {"fot": 1.4, "fos": 0.2, "densidad_neta": 400, "multifamiliar": "Sí",
                    "regla_unidades": "Densidad neta de la zona (multifamiliar)", "flags+": "rr_multifamiliar_3000",
                    "notas": "Multifamiliar solo en lotes >= 3.000 m2: FOS 0,2, FOT 1,4, 400 hab/ha, h 30 m (3.5.8.8 "
                             "a 3.5.8.13); unifamiliar una por lote, FOS 0,4, FOT 0,6, 200 hab/ha"}),
            # #3: premios of 3.20 where the height leaves room: R2 x1,25 (lot width) inside PB+3 with FOS 0,6 (2,4);
            # towers of R1 (31,80 m) and C1 (38,40 m): width + 4 m side setbacks
            ("R2", {"fot_max": 2.25, "flags+": "premio_ley_8912",
                    "notas": "FOT 1,8 'que se incrementará' con premios (3.5.5.3, 3.20): x1,25 por ancho de parcela "
                             "entra en 11,20 m (PB+3)"}),
            ("R1", {"fot_max": 3.1, "flags+": "premio_ley_8912",
                    "notas": "Torre 2,4 + premios (3.5.4.3, 3.20): ancho y retiros laterales de 4 m, h 31,80 m"}),
            ("C1", {"fot_max": 3.9, "flags+": "premio_ley_8912",
                    "notas": "Torre 3 + premios (3.5.1.3, 3.20): ancho y retiros laterales de 4 m, h 38,40 m"}),
        ],
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
    fix = next((cols for pre, cols in conf.get("planillas", []) if name.startswith(pre)), None)
    housing = (fot > 0 or bool((fix or {}).get("_vivienda"))) and not _starts(name, conf["sin_vivienda"])
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
    fix = fix if housing else None
    if fix:
        for col, value in fix.items():
            if col == "_vivienda":
                continue
            if col == "flags+":
                row["flags"] = ";".join(dict.fromkeys(x for x in row["flags"].split(";") + [value] if x))
            else:
                row[col] = _num(value) if isinstance(value, (int, float)) else value
        if row["multifamiliar"] == "Sí":
            row["relevancia"] = "Alta"
        row["fuente"] += " + " + conf.get("fuente_planillas", "planilla tigre.gob.ar (19/11/2026)")
    setbacks = next((cols for pre, cols in conf.get("retiros", []) if name.startswith(pre)), None) if housing else None
    for col, value in (setbacks or {}).items():
        row[col] = _num(value) if value else "0"
    return row


def extra_row(spec: dict) -> dict:
    """A row the layer doesn't give (conf['filas_extra']), with the same columns."""
    row = dict.fromkeys(COLUMNS, "")
    row.update({"acceso_directo_requerido": "no"})
    for col, value in spec.items():
        row[col] = (_num(value) if value else "0") if isinstance(value, (int, float)) else value
    return row


def streets(slug: str, out: Path) -> int:
    conf = PARTIDOS[slug]
    ways = overpass(f"""[out:json][timeout:240];
rel({conf['osm']});map_to_area->.p;
way(area.p)["highway"]["name"];
out geom;""")
    feats = [{"type": "Feature",
              "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in w["geometry"]]},
              "properties": {"nombre": w["tags"]["name"], "tipo": w["tags"].get("highway", ""),
                             "ancho": w["tags"].get("width", "")}}
             for w in ways if w.get("geometry") and len(w["geometry"]) > 1]
    (out / "calles.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False),
                                        encoding="utf-8")
    return len(feats)


def rivers(slug: str, out: Path) -> int:
    """OSM rivers, canals and streams around the continental partido (its localidades plus ~1 km: the whole partido
    takes in the Delta and the query fails), for the camino de sirga (src/entorno.py). Only named rivers and named
    canals ("Canal ..."): the sirga is for waterways used for navigation (art. 1974 CCyC), not for the unnamed
    drainage ditches or the canalized arroyos (Pavón) that cross Virreyes and Victoria."""
    locs = json.loads((out / "localidades.geojson").read_text(encoding="utf-8"))
    w, s, e, n = unary_union([shape(f["geometry"]) for f in locs["features"]]).buffer(0.01).bounds
    ways = overpass(f"""[out:json][timeout:240];
way["waterway"~"^(river|canal|stream)$"]({s},{w},{n},{e});
out geom;""")
    feats = [{"type": "Feature",
              "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in w["geometry"]]},
              "properties": {"nombre": w["tags"].get("name", ""), "tipo": w["tags"]["waterway"]}}
             for w in ways if w.get("geometry") and len(w["geometry"]) > 1 and w["tags"].get("name")
             and (w["tags"]["waterway"] == "river" or w["tags"]["name"].startswith("Canal"))]
    (out / "fuentes" / "rios_osm.geojson").write_text(
        json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    return len(feats)


def main(slug: str, only_normativa: bool = False, only_streets: bool = False, only_rivers: bool = False) -> None:
    conf = PARTIDOS[slug]
    out = ROOT / "municipios" / slug
    (out / "fuentes").mkdir(parents=True, exist_ok=True)
    if only_streets:
        print(f"{slug}: {streets(slug, out)} tramos de calle -> {out / 'calles.geojson'}")
        return
    if only_rivers:
        print(f"{slug}: {rivers(slug, out)} tramos de río, canal o arroyo -> {out / 'fuentes' / 'rios_osm.geojson'}")
        return
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
    rows += [extra_row(spec) for spec in conf.get("filas_extra", [])]
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
    n_streets = streets(slug, out)
    print(f"{slug}: {len(feats)} polígonos, {len(rows)} zonas, {len(locs)} localidades "
          f"({', '.join(sorted(l['properties']['barrio'] for l in locs))}), {n_streets} tramos de calle -> {out}")


if __name__ == "__main__":
    main(sys.argv[1], "--solo-normativa" in sys.argv[2:], "--solo-calles" in sys.argv[2:], "--solo-rios" in sys.argv[2:])
