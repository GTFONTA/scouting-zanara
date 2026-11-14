"""Phase 0: download the ZONAS layer from the San Isidro GIS portal and build a control map.

Usage:
    python tools/fase0_zonas.py                  # download from the ArcGIS server
    python tools/fase0_zonas.py --from-file X    # use a GeoJSON saved manually (e.g. from a browser)

Outputs:
    data/zonas_san_isidro.geojson
    data/zonas_layer_fields.json   (layer metadata: fields, maxRecordCount)
    data/mapa_zonas_control.html
"""

import argparse
import json
import sys
from pathlib import Path

import folium
import requests
from shapely.geometry import shape
from shapely.ops import unary_union

LAYER_URL = "https://msi-gis.gestionmsi.gob.ar/server/rest/services/zonificacion/FeatureServer/1"
ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT_GEOJSON = DATA / "zonas_san_isidro.geojson"
OUT_FIELDS = DATA / "zonas_layer_fields.json"
OUT_MAP = DATA / "mapa_zonas_control.html"

# Rough bounding box of San Isidro partido (lon_min, lat_min, lon_max, lat_max).
SAN_ISIDRO_BBOX = (-58.62, -34.53, -58.47, -34.43)
ZONING_FIELD_HINTS = ("fot", "fos", "altura", "alt_max", "h_max", "plano")
TIMEOUT = 60


def fetch_layer_info() -> dict:
    r = requests.get(LAYER_URL, params={"f": "json"}, timeout=TIMEOUT)
    r.raise_for_status()
    info = r.json()
    if "error" in info:
        sys.exit(f"Server error: {info['error']}")
    return info


def report_fields(info: dict) -> None:
    fields = info.get("fields", [])
    print(f"Layer: {info.get('name')} | geometry: {info.get('geometryType')} | "
          f"maxRecordCount: {info.get('maxRecordCount')}")
    print(f"{'name':30} {'type':28} alias")
    for f in fields:
        print(f"{f['name']:30} {f['type']:28} {f.get('alias')}")
    hits = [f["name"] for f in fields if any(h in f["name"].lower() for h in ZONING_FIELD_HINTS)]
    print("\nPossible FOT/FOS/height fields:", hits or "NONE (zone name/code only)")
    OUT_FIELDS.write_text(json.dumps(
        {"layer_url": LAYER_URL, "maxRecordCount": info.get("maxRecordCount"), "fields": fields},
        ensure_ascii=False, indent=2), encoding="utf-8")


def download_features(page_size: int) -> dict:
    features, offset = [], 0
    while True:
        params = {
            "where": "1=1", "outFields": "*", "f": "geojson", "outSR": 4326,
            "resultOffset": offset, "resultRecordCount": page_size, "orderByFields": "OBJECTID",
        }
        r = requests.get(f"{LAYER_URL}/query", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        page = r.json()
        if "error" in page:
            sys.exit(f"Query error: {page['error']}")
        batch = page.get("features", [])
        features.extend(batch)
        print(f"  offset {offset}: {len(batch)} features")
        if len(batch) < page_size and not page.get("exceededTransferLimit"):
            break
        offset += len(batch)
        if not batch:
            break
    return {"type": "FeatureCollection", "features": features}


def check_bbox(fc: dict) -> None:
    geoms = [shape(f["geometry"]) for f in fc["features"] if f.get("geometry")]
    lon_min, lat_min, lon_max, lat_max = unary_union(geoms).bounds
    print(f"Bounds: lon {lon_min:.4f}..{lon_max:.4f}, lat {lat_min:.4f}..{lat_max:.4f}")
    b = SAN_ISIDRO_BBOX
    inside = b[0] <= lon_min and lon_max <= b[2] and b[1] <= lat_min and lat_max <= b[3]
    print("Coordinates inside San Isidro:", "YES" if inside else "NO — check projection")


def build_map(fc: dict) -> None:
    m = folium.Map(location=[-34.475, -58.53], zoom_start=13, tiles="OpenStreetMap")
    props = list(fc["features"][0]["properties"].keys()) if fc["features"] else []
    folium.GeoJson(
        fc,
        style_function=lambda _: {"color": "#c0392b", "weight": 1, "fillOpacity": 0.15},
        tooltip=folium.GeoJsonTooltip(fields=props[:8]) if props else None,
    ).add_to(m)
    m.save(OUT_MAP)
    print(f"Map: {OUT_MAP}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--from-file", type=Path, help="GeoJSON already downloaded")
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)

    if args.from_file:
        fc = json.loads(args.from_file.read_text(encoding="utf-8"))
    else:
        info = fetch_layer_info()
        report_fields(info)
        fc = download_features(int(info.get("maxRecordCount") or 1000))

    print(f"Total features: {len(fc['features'])}")
    OUT_GEOJSON.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    check_bbox(fc)
    build_map(fc)


if __name__ == "__main__":
    main()
