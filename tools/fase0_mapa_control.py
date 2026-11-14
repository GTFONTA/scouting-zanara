"""Phase 0: HTML control map for the zoning layer.

Layers: zone polygons coloured by FOT (tooltip: zona, FOT, asignación), the original 2022 plano
warped onto the map (to compare edges), and the older UrbaSIG 2021 layer for reference.

Usage:
    python tools/fase0_mapa_control.py
Output:
    data/mapa_zonas_control.html
"""

import base64
import csv
import json
from pathlib import Path

import cv2
import folium
import numpy as np
import pymupdf
import pyproj

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PLANO = DATA / "fuentes" / "plano-de-zonificacion.pdf"
URBASIG = DATA / "fuentes" / "urbasig_zonificacion_san_isidro_2021.geojson"
T = np.load(ROOT / "tools" / "georef_plano_T.npy")
DPI = 150


def fot_colour(fot):
    if fot is None:
        return "#9e9e9e"
    for limit, colour in [(0.6, "#fff5b1"), (0.9, "#fed976"), (1.0, "#fd8d3c"), (1.2, "#f03b20"),
                          (1.8, "#bd0026"), (99, "#54278f")]:
        if fot <= limit:
            return colour


def warped_plano(bounds, width=2400):
    """Resample the plano onto a lon/lat grid so it can be used as an ImageOverlay."""
    page = pymupdf.open(PLANO)[0]
    z = DPI / 72
    pix = page.get_pixmap(matrix=pymupdf.Matrix(z, z), alpha=False)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
    lon0, lat0, lon1, lat1 = bounds
    height = int(width * (lat1 - lat0) / ((lon1 - lon0) * np.cos(np.radians((lat0 + lat1) / 2))))
    lons = np.linspace(lon0, lon1, width)
    lats = np.linspace(lat1, lat0, height)
    LON, LAT = np.meshgrid(lons, lats)
    X, Y = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform(LON, LAT)
    A = np.linalg.inv(np.vstack([T, [0, 0, 1]]))
    xp = A[0, 0] * X + A[0, 1] * Y + A[0, 2]
    yp = -(A[1, 0] * X + A[1, 1] * Y + A[1, 2])
    out = cv2.remap(img, (xp * z).astype(np.float32), (yp * z).astype(np.float32),
                    cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(255, 255, 255))
    ok, png = cv2.imencode(".png", out[:, :, ::-1])
    return "data:image/png;base64," + base64.b64encode(png.tobytes()).decode()


def main():
    fc = json.loads((DATA / "zonas_san_isidro.geojson").read_text(encoding="utf-8"))
    with open(DATA / "fot_por_zona.csv", encoding="utf-8") as fh:
        table = {r["zona"]: r for r in csv.DictReader(fh)}
    for f in fc["features"]:
        p = f["properties"]
        row = table.get(p["zona"], {})
        p["fot"] = float(row["fot"]) if row.get("fot") else None
        p["fot_txt"] = row.get("fot") or "s/d"
        p["notas"] = row.get("notas", "")

    m = folium.Map(location=[-34.488, -58.537], zoom_start=13, tiles="OpenStreetMap")
    bounds = (-58.605, -34.535, -58.470, -34.440)
    folium.raster_layers.ImageOverlay(
        warped_plano(bounds), bounds=[[bounds[1], bounds[0]], [bounds[3], bounds[2]]],
        opacity=0.75, name="Plano de zonificación 2022 (PDF georreferenciado)", show=False,
    ).add_to(m)

    folium.GeoJson(
        fc, name="Zonas vectorizadas (color = FOT)",
        style_function=lambda f: {
            "fillColor": fot_colour(f["properties"]["fot"]), "color": "#333",
            "weight": 2.5 if f["properties"]["asignacion"] != "etiqueta" else 0.8,
            "dashArray": "6 4" if f["properties"]["asignacion"] != "etiqueta" else None,
            "fillOpacity": 0.45},
        tooltip=folium.GeoJsonTooltip(fields=["zona", "fot_txt", "asignacion", "notas"],
                                      aliases=["Zona", "FOT", "Asignación", "Notas"]),
    ).add_to(m)

    if URBASIG.exists():
        folium.GeoJson(
            json.loads(URBASIG.read_text(encoding="utf-8")), name="UrbaSIG 2021 (referencia)", show=False,
            style_function=lambda f: {"color": "#1565c0", "weight": 1.5, "fillOpacity": 0},
            tooltip=folium.GeoJsonTooltip(fields=["designacio", "fota"], aliases=["Zona 2021", "FOT 2021"]),
        ).add_to(m)

    legend = """
    <div style="position:fixed;bottom:24px;left:12px;z-index:9999;background:#fff;padding:8px 10px;
    border:1px solid #999;border-radius:4px;font:12px sans-serif;line-height:1.6">
    <b>FOT</b><br>
    <i style="background:#fff5b1;padding:0 8px"></i> &le; 0,6<br>
    <i style="background:#fed976;padding:0 8px"></i> 0,8 &ndash; 0,9<br>
    <i style="background:#fd8d3c;padding:0 8px"></i> 1,0<br>
    <i style="background:#f03b20;padding:0 8px"></i> 1,2<br>
    <i style="background:#bd0026;padding:0 8px"></i> 1,5 &ndash; 1,8<br>
    <i style="background:#54278f;padding:0 8px"></i> 2,2 &ndash; 3,0<br>
    <i style="background:#9e9e9e;padding:0 8px"></i> sin dato<br>
    Borde punteado = asignación dudosa
    </div>"""
    m.get_root().html.add_child(folium.Element(legend))
    folium.LayerControl(collapsed=False).add_to(m)
    out = DATA / "mapa_zonas_control.html"
    m.save(out)
    print(f"Map: {out} ({out.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
