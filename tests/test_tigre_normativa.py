"""Tigre: the seven decisions of Gonzalo on 24/11/2026 (municipios/tigre/GUIA_NORMATIVA.md, section 10.7)."""

import json

import pyproj
from shapely.geometry import shape
from shapely.ops import transform

from src.config import load_config
from src.evaluate import fos_by_setbacks, units
from tests.test_municipios import _normativa, _point_in_zone, _tigre_row

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform
TO_LL = pyproj.Transformer.from_crs(5347, 4326, always_xy=True).transform


def _geo(rel):
    return json.loads((ROOT / rel).read_text(encoding="utf-8"))["features"]


def _zone_m(zone):
    return [transform(TO_M, shape(f["geometry"])) for f in _geo("municipios/tigre/zonas.geojson")
            if f["properties"]["zona"] == zone]


def _ll(p):
    lon, lat = TO_LL(p.x, p.y)
    return lat, lon


def test_r1a_counts_only_inside_its_4448_sector(monkeypatch, tmp_path):
    """#1: R1a frente a la colectora de Panamericana (sector 4-R1a-PB5-60) is valued with the R1 sheet; the rest of
    the R1a zone stays a gated neighbourhood without product."""
    sector = next(transform(TO_M, shape(f["geometry"])) for f in _geo("municipios/tigre/alturas_4448.geojson")
                  if f["properties"]["id"].startswith("4-R1a-PB5"))
    inside = next(z.intersection(sector) for z in _zone_m("R1a") if z.intersection(sector).area > 100)
    r = _tigre_row(monkeypatch, tmp_path, *_ll(inside.representative_point()), 3000, 400000)
    assert r["zona_unidades"] == "R1a" and r["multifamiliar_unidades"] == 30          # 400 hab/ha x 0,3 ha / 4
    assert "solo_en_sector_4448" in r["flags"]
    out = _tigre_row(monkeypatch, tmp_path, *_point_in_zone("tigre", "R1a"), 3000, 400000)
    assert not out.get("multifamiliar_unidades") and out["resultado"] == "descartado"


def test_nordelta():
    """#2: UR 4.x without multifamiliar (Nordelta's neighbourhoods); the Centro Cívico (UE 8, UM2) with it."""
    tigre = _normativa("tigre")
    assert all(tigre[z]["multifamiliar"] == "No" for z in ("UR 4 M", "UR 4.1", "UR 4.3", "UR 4.4"))
    assert tigre["UR 1 C"]["multifamiliar"] == "Sí" and "verificar_reglamento_nordelta" in tigre["UR 1 C"]["flags"]
    assert tigre["UE 8"]["multifamiliar"] == "Sí" and tigre["UE 8"]["fot"] == "3"


def test_effective_fos_by_setbacks():
    """#3: a TC tower on 25 x 40 leaves 17 x 25 = 425 m2 of plan (5 m ahead, 10 m behind, 4 m each side): FOS 0,425.
    R2 on 15 x 40 can take the rear down to 5 m: 11,25 x 32 = 360 m2, the full 0,6."""
    tigre = _normativa("tigre")
    assert round(fos_by_setbacks(tigre["TC"], 1000, 25), 3) == 0.425
    assert round(fos_by_setbacks(tigre["R2a"], 600, 15), 3) == 0.6
    assert fos_by_setbacks(tigre["TC"], 1000, None) is None                       # no front: unknown


def test_agrupadas_with_common_access_need_400_m2():
    """#4: Código art. 71, one house every 400 m2 with water and sewers; R2d's sheet says 200 for houses with front."""
    tigre, p = _normativa("tigre"), load_config("tigre")["productos"]
    u = units(tigre["R2d"], 2000, None, p)
    assert u["agrupadas_acceso_comun"] == 5 and u["agrupadas_calle"] == 10


def test_loteo_flags(monkeypatch, tmp_path):
    """#5: a lot that admits a subdivision with internal street carries the cessions and the fill to +3,75."""
    r = _tigre_row(monkeypatch, tmp_path, *_point_in_zone("tigre", "R2a"), 8000, 600000)
    for flag in ("cesion_ley_8912", "relleno_cota_375", "cesion_ley_14449"):
        assert flag in r["flags"], flag


def test_camino_de_sirga(monkeypatch, tmp_path):
    """#6: a point 15-25 m from a river or canal loses the 15 m strip (front unknown: 15 x sqrt(surface))."""
    rivers = [transform(TO_M, shape(f["geometry"])) for f in _geo("municipios/tigre/fuentes/rios_y_vias_osm.geojson")
              if f["properties"]["tipo"] in ("river", "canal", "stream")]
    point = None
    for zone in ("R2a", "R2b", "R3a", "C4a", "RM1"):
        for z in _zone_m(zone):
            for river in rivers:
                band = z.intersection(river.buffer(25)).difference(river.buffer(15))
                if band.area > 50:
                    point = band.representative_point()
                    break
            if point:
                break
        if point:
            break
    assert point is not None
    r = _tigre_row(monkeypatch, tmp_path, *_ll(point), 900, 100000)
    assert r["superficie_util_m2"] == 900 - 450 and "camino_de_sirga" in r["flags"]      # 15 x 30 = 450


def test_street_width_caps_the_height():
    """#7: Ord. 4448 art. 12 k, a point on a residential street only: PB+6 at most; next to an avenue: no cap."""
    from src import entorno
    env = entorno.for_config(load_config("tigre"))
    streets = _geo("municipios/tigre/calles.geojson")
    found = {}
    for f in streets:
        kind = f["properties"]["tipo"]
        if kind in ("residential", "secondary") and kind not in found:
            mid = shape(f["geometry"]).interpolate(0.5, normalized=True)
            cap = env.street_cap(mid.y, mid.x)
            if (kind == "residential" and cap[0] == 6) or (kind == "secondary" and cap[0] is None):
                found[kind] = cap
        if len(found) == 2:
            break
    assert found["residential"][0] == 6 and found["secondary"] == (None, "avenida")
