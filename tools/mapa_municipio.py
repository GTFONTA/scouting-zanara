"""Control map of a municipio's zones (to validate the normativa by eye before activating it).

Usage:
    python tools/mapa_municipio.py tigre
Output:
    municipios/<slug>/Mapa de control - Zonas.html   (zones coloured by FOT; tooltip: zona, FOT, multifamiliar,
                                                      densidad, parcela mínima, regla; localidades as outlines)
"""

import csv
import json
import sys
from pathlib import Path

import folium

ROOT = Path(__file__).resolve().parent.parent
COLORS = [(0, "#dddddd"), (0.8, "#c6dbef"), (1.2, "#6baed6"), (1.8, "#fdae6b"), (2.4, "#f16913"), (3.0, "#a50f15")]


def color(fot: float) -> str:
    return [c for v, c in COLORS if fot >= v][-1]


def main(slug: str) -> None:
    d = ROOT / "municipios" / slug
    norm = {r["zona"]: r for r in csv.DictReader(open(d / "normativa_zonas.csv", encoding="utf-8"))}
    zones = json.loads((d / "zonas.geojson").read_text(encoding="utf-8"))
    for f in zones["features"]:
        r = norm.get(f["properties"]["zona"], {})
        f["properties"].update(fot=r.get("fot") or "-", multi=r.get("multifamiliar", ""), dens=r.get("densidad_neta", ""),
                               sm=r.get("subdiv_sup_min", ""), regla=r.get("regla_unidades", ""))
    locs = json.loads((d / "localidades.geojson").read_text(encoding="utf-8"))
    from shapely.geometry import shape
    from shapely.ops import unary_union
    c = unary_union([shape(f["geometry"]) for f in locs["features"]]).centroid
    m = folium.Map(location=[c.y, c.x], zoom_start=13, tiles="OpenStreetMap")
    folium.GeoJson(zones, name="Zonas (color = FOT)",
                   style_function=lambda f: {"fillColor": color(float(f["properties"]["fot"]) if f["properties"]["fot"] != "-" else 0),
                                             "color": "#555", "weight": 0.6, "fillOpacity": 0.55},
                   tooltip=folium.GeoJsonTooltip(["zona", "fot", "multi", "dens", "sm", "regla"],
                                                 ["Zona", "FOT", "Multifamiliar", "Densidad hab/ha", "Parcela mín. m²", "Regla"])
                   ).add_to(m)
    folium.GeoJson(locs, name="Localidades", style_function=lambda f: {"fill": False, "color": "#000", "weight": 2},
                   tooltip=folium.GeoJsonTooltip(["barrio"], ["Localidad"])).add_to(m)
    folium.LayerControl().add_to(m)
    out = d / "Mapa de control - Zonas.html"
    m.save(str(out))
    print(f"-> {out}")


if __name__ == "__main__":
    main(sys.argv[1])
