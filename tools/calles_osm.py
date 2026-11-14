"""Download the named streets of the partido from OpenStreetMap (run once; re-run to refresh).

Used by src/locate.py for listings that hide the street number: the FOT is taken as the highest
among the zones that street (or corner) touches, instead of the whole localidad.

Usage:
    python tools/calles_osm.py
Output:
    data/calles_san_isidro.geojson   (one LineString feature per OSM way: nombre)
"""

import json
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "calles_san_isidro.geojson"
PARTIDO_OSM_RELATION = 1769044     # Partido de San Isidro
QUERY = f"""[out:json][timeout:180];
rel({PARTIDO_OSM_RELATION});map_to_area->.p;
way(area.p)["highway"]["name"];
out geom;"""


def main():
    r = requests.post("https://overpass-api.de/api/interpreter", data={"data": QUERY},
                      headers={"User-Agent": "zanara-scouting-san-isidro/0.1"}, timeout=240)
    r.raise_for_status()
    feats = [{
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": [[p["lon"], p["lat"]] for p in w["geometry"]]},
        "properties": {"nombre": w["tags"]["name"]},
    } for w in r.json()["elements"] if w.get("geometry") and len(w["geometry"]) > 1]
    OUT.write_text(json.dumps({"type": "FeatureCollection", "features": feats}, ensure_ascii=False), encoding="utf-8")
    print(f"{len(feats)} tramos, {len({f['properties']['nombre'] for f in feats})} calles -> {OUT}")


if __name__ == "__main__":
    main()
