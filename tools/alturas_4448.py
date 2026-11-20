"""Polygons of the height sectors of Tigre's Ordenanza 4448/26 (municipios/tigre/alturas_4448.yaml).

    python tools/alturas_4448.py            # writes municipios/tigre/alturas_4448.geojson and prints a report

Each sector is described with streets, rivers and railways (OSM: calles.geojson, fuentes/rios_y_vias_osm.geojson),
always inside its localidad (localidades.geojson, +300 m):
  frentista  the street between the points nearest to `desde` and `hasta`, buffered by FRENTE_M (both sides)
  area       the face of the network of `limites` that touches every one of them
  manual     not built: the engine uses the zone's highest height in the localidad and says so
A sector that can't be built is reported and left out: never a guessed polygon.
"""

import json
import sys
from pathlib import Path

import pyproj
import yaml
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.validation import make_valid
from shapely.ops import linemerge, nearest_points, polygonize, substring, transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.locate import _plain, _street_tokens  # noqa: E402

DIR = ROOT / "municipios" / "tigre"
FRENTE_M = 40          # a frentista lot: its pin is within ~40 m of the street axis
TOUCH_M = 25           # a face "touches" a limit when this close along at least TOUCH_LEN_M
TOUCH_LEN_M = 30
EXTEND_M = 120     # limits are prolonged this much to close the polygon
MAX_GAP_M = 250    # corner polygon: two consecutive limits farther apart than this don't meet
MAX_AREA_M2 = 3_000_000
MIN_SHARE = 0.15   # a sector with less of its surface inside its zone is badly placed
_TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform
_TO_DEG = pyproj.Transformer.from_crs(5347, 4326, always_xy=True).transform
ALIASES = {"ffcc mitre": ("ffcc", "mitre"), "tren de la costa": ("ffcc", "costa")}


def _load_lines():
    out = []
    for f in json.loads((DIR / "calles.geojson").read_text(encoding="utf-8"))["features"]:
        out.append((_street_tokens(f["properties"]["nombre"]), "calle", "", transform(_TO_M, shape(f["geometry"]))))
    for f in json.loads((DIR / "fuentes" / "rios_y_vias_osm.geojson").read_text(encoding="utf-8"))["features"]:
        p = f["properties"]
        out.append((_street_tokens(p["nombre"]), p["tipo"], _plain(f"{p['nombre']} {p['ramal']}"),
                    transform(_TO_M, shape(f["geometry"]))))
    return out


def _localidades():
    fc = json.loads((DIR / "localidades.geojson").read_text(encoding="utf-8"))
    return {_plain(f["properties"]["barrio"]): transform(_TO_M, shape(f["geometry"])) for f in fc["features"]}


def find(name: str, lines, region):
    """Union of the OSM lines called `name` inside `region` (None if there is none)."""
    key = _plain(name)
    if key in ALIASES:
        kind, word = ALIASES[key]
        geoms = [g for _, t, text, g in lines if t == kind and word in text]
    else:              # rivers by their name; any other name is a street (never the "FC Mitre" railway)
        tokens = _street_tokens(name)
        water = key.split()[0] in ("rio", "arroyo", "canal")
        geoms = [g for toks, kind, _, g in lines
                 if tokens and tokens <= toks and (kind != "calle" if water else kind == "calle")]
    geoms = [g.intersection(region) for g in geoms if g.intersects(region)]
    geoms = [g for g in geoms if not g.is_empty]
    return unary_union(geoms) if geoms else None


def _cut_point(line, other):
    """Where `other` crosses `line`, or the point of `line` nearest to it."""
    x = line.intersection(other)
    if not x.is_empty:
        return x.centroid if x.geom_type != "Point" else x
    return nearest_points(line, other)[0]


def frentista(s: dict, lines, region):
    street = find(s["calle"], lines, region)
    if street is None:
        return None, f"no está la calle {s['calle']!r}"
    if not s.get("desde") and not s.get("hasta"):
        return street.buffer(FRENTE_M), "toda la calle en la localidad"
    ends = []
    for k in ("desde", "hasta"):
        if s.get(k):
            g = find(s[k], lines, region)
            if g is None:
                return None, f"no está {s[k]!r}"
            ends.append(_cut_point(street, g))
    if len(ends) == 1:              # only one end: from it to the end of the street in the localidad
        return street.buffer(FRENTE_M), "un solo límite: toda la calle en la localidad"
    a, b = ends
    merged = linemerge(street) if street.geom_type == "MultiLineString" else street
    if merged.geom_type == "LineString":
        d1, d2 = sorted((merged.project(a), merged.project(b)))
        seg = substring(merged, d1, d2)
    else:                            # broken in pieces: the part of the street near the straight segment a-b
        chord = LineString([a, b])
        seg = street.intersection(chord.buffer(max(80, 0.25 * chord.length)))
    if seg.is_empty or seg.length < 10:
        return None, "el tramo entre los límites quedó vacío"
    return seg.buffer(FRENTE_M), f"tramo de {seg.length:.0f} m"


def _extended(g, ext: float):
    """Each piece of a line, prolonged `ext` meters at both ends: a street that stops short of a river or of the
    other limit ("proyección de la calle X") still closes the polygon."""
    out = []
    for ln in getattr(g, "geoms", [g]):
        if ln.geom_type != "LineString" or len(ln.coords) < 2:
            continue
        c = list(ln.coords)

        def push(a, b):          # point `ext` beyond b, in the direction a -> b
            dx, dy = b[0] - a[0], b[1] - a[1]
            n = (dx * dx + dy * dy) ** 0.5 or 1
            return (b[0] + dx / n * ext, b[1] + dy / n * ext)
        out.append(LineString([push(c[1], c[0])] + c + [push(c[-2], c[-1])]))
    return unary_union(out)


def area(s: dict, lines, region):
    limits = []
    for name in s["limites"]:
        g = find(name, lines, region)
        if g is None:
            return None, f"no está {name!r}"
        limits.append(g)
    faces = list(polygonize(unary_union([_extended(g, EXTEND_M) for g in limits])))

    def touches(face, g):
        return face.exterior.buffer(TOUCH_M).intersection(g).length >= TOUCH_LEN_M
    good = [f for f in faces if all(touches(f, g) for g in limits)]
    if good:
        best = min(good, key=lambda f: f.area)
        return best, f"{best.area / 10000:.1f} ha (cara de la red)"
    # no single face (pieces of street, crossings that split it): the polygon of the corners, where each limit
    # meets the next one (or their nearest points)
    corners = []
    for g, h in zip(limits, limits[1:] + limits[:1]):
        x = g.intersection(h)
        if not x.is_empty:
            corners.append(x.centroid)
        else:
            a, b = nearest_points(g, h)
            if a.distance(b) > MAX_GAP_M:
                return None, f"{len(faces)} caras; los límites no se tocan (hueco de {a.distance(b):.0f} m)"
            corners.append(Point((a.x + b.x) / 2, (a.y + b.y) / 2))
    poly, fixed = Polygon([(c.x, c.y) for c in corners]), ""
    if not poly.is_valid:            # a corner taken from a street that crosses twice: keep the polygonal part
        poly, fixed = make_valid(poly), ", corregido"
        parts = [g for g in getattr(poly, "geoms", [poly]) if g.geom_type == "Polygon"]
        poly = unary_union(parts) if parts else Polygon()
    if poly.is_empty or poly.area < 1000 or poly.area > MAX_AREA_M2:
        return None, f"{len(faces)} caras; el polígono de esquinas no sirve ({poly.area / 10000:.1f} ha)"
    return poly, f"{poly.area / 10000:.1f} ha (esquinas{fixed})"


def main():
    sectors = yaml.safe_load((DIR / "alturas_4448.yaml").read_text(encoding="utf-8"))
    lines, locs = _load_lines(), _localidades()
    zones = {}
    for f in json.loads((DIR / "zonas.geojson").read_text(encoding="utf-8"))["features"]:
        zones.setdefault(f["properties"]["zona"].lower(), []).append(transform(_TO_M, shape(f["geometry"])))
    zones = {k: unary_union(v).buffer(0) for k, v in zones.items()}
    feats, report = [], []
    for i, s in enumerate(sectors, 1):
        sid = f"{s['art']}-{s['zona']}-PB{s['pb']}-{i}"
        loc = locs.get(_plain(s["localidad"]))
        if loc is None:
            report.append(f"FALTA {sid}: localidad {s['localidad']!r} no está en localidades.geojson")
            continue
        region = loc.buffer(300)
        if s["tipo"] == "manual":
            report.append(f"manual {sid} ({s['localidad']})")
            continue
        geom, why = (frentista if s["tipo"] == "frentista" else area)(s, lines, region)
        if geom is None:
            report.append(f"FALLA  {sid} ({s['localidad']}, {s['tipo']}): {why}")
            continue
        zone = zones.get(s["zona"].lower())
        share = geom.intersection(zone).area / geom.area if zone is not None else 0
        if share < MIN_SHARE:           # the street of the text isn't where UrbaSIG draws the zone: not used
            report.append(f"FALLA  {sid} ({s['localidad']}, {s['tipo']}): solo {share:.0%} cae en la zona {s['zona']}")
            continue
        report.append(f"ok     {sid} ({s['localidad']}, {s['tipo']}): {why}, {share:.0%} en la zona")
        props = {"id": sid, "art": s["art"], "localidad": s["localidad"], "zona": s["zona"], "pb": s["pb"],
                 "tipo": s["tipo"], "sin_multifamiliar": bool(s.get("sin_multifamiliar")),
                 "condiciones": s.get("condiciones", ""), "nota": s.get("nota", "")}
        feats.append({"type": "Feature", "geometry": mapping(transform(_TO_DEG, geom)), "properties": props})
    (DIR / "alturas_4448.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                         ensure_ascii=False), encoding="utf-8")
    print("\n".join(report))
    n = {k: sum(1 for x in report if x.startswith(k)) for k in ("ok", "FALLA", "manual", "FALTA")}
    print(f"\n{len(sectors)} sectores: {n['ok']} armados, {n['FALLA']} fallas, {n['manual']} manuales, {n['FALTA']} sin localidad")


if __name__ == "__main__":
    main()
