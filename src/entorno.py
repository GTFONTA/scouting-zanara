"""Surroundings of a listing's point that change what can be built (Tigre, Gonzalo 24/11/2026; GUIA_NORMATIVA.md 10.7):

  water    camino de sirga: 15 m from the bank of a river, canal or stream, public use, no buildings or fences
           (Ord. 4448/26 definitions; Código Civil y Comercial art. 1974). zonificacion.rios_geojson (OSM).
  streets  Ord. 4448/26 art. 12 k: a street under 12 m allows PB+6 at most, one of 12 to 20 m PB+8; within 50 m of the
           avenue the sector's highest height, 50-100 m an intermediate one, beyond 100 m the lowest.
           zonificacion.calles_geojson with the OSM highway class (tools/municipio_pba.py --solo-calles); the width
           is almost never mapped, so the class stands for it (residential / living_street: under 12 m; tertiary:
           12-20 m; secondary, primary, trunk: avenue).

Without the config keys (San Isidro) nothing here is used.
"""

import json
from functools import lru_cache

import pyproj
from shapely.geometry import Point, shape
from shapely.ops import transform
from shapely.strtree import STRtree

from .config import path

_TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform
WATER = {"river", "canal", "stream"}


class Entorno:
    def __init__(self, rivers: str | None, streets: str | None, k: dict):
        self.k = k
        self.water = self._lines(rivers, lambda p: p.get("tipo") in WATER)
        self.streets = self._lines(streets, lambda p: bool(p.get("tipo")))

    @staticmethod
    def _lines(file: str | None, keep):
        if not file or not path(file).exists():
            return None
        fc = json.loads(path(file).read_text(encoding="utf-8"))
        geoms, props = [], []
        for f in fc["features"]:
            if keep(f["properties"]):
                geoms.append(transform(_TO_M, shape(f["geometry"])))
                props.append(f["properties"])
        return (STRtree(geoms), geoms, props) if geoms else None

    @staticmethod
    def _near(index, p: Point, radius: float) -> list[tuple[float, dict]]:
        tree, geoms, props = index          # the tree returns envelopes that touch: keep the ones really in range
        near = ((geoms[i].distance(p), props[i]) for i in tree.query(p.buffer(radius)))
        return sorted((x for x in near if x[0] <= radius), key=lambda x: x[0])

    def water_m(self, lat: float, lon: float) -> tuple[float, str] | None:
        """(meters, name) of the nearest river, canal or stream within sirga.distancia_max_m."""
        if self.water is None or lat is None or lon is None:
            return None
        near = self._near(self.water, Point(_TO_M(lon, lat)), self.k["sirga"]["distancia_max_m"])
        return (near[0][0], near[0][1].get("nombre") or "curso de agua") if near else None

    def street_cap(self, lat: float, lon: float) -> tuple[int | None, str]:
        """(max PB+N by the width of the widest street next to the point, its class). Never lose a hit: an avenue
        within the radius means no cap (the lot may front it)."""
        if self.streets is None or lat is None or lon is None:
            return None, ""
        a = self.k["art_12k"]
        near = self._near(self.streets, Point(_TO_M(lon, lat)), a["radio_calle_m"])
        classes = {props.get("tipo") for _, props in near}
        if not classes:
            return None, ""
        if classes & set(a["clases_avenida"]):
            return None, "avenida"
        if classes & set(a["clases_media"]):
            return a["pb_calle_media"], "calle de 12 a 20 m (" + ", ".join(sorted(classes & set(a["clases_media"]))) + ")"
        return a["pb_calle_angosta"], "calle de menos de 12 m (" + ", ".join(sorted(classes)) + ")"

    def avenue_m(self, lat: float, lon: float) -> float | None:
        """Meters to the nearest avenue (art. 12 k), within 200 m."""
        if self.streets is None or lat is None or lon is None:
            return None
        near = [d for d, props in self._near(self.streets, Point(_TO_M(lon, lat)), 200)
                if props.get("tipo") in self.k["art_12k"]["clases_avenida"]]
        return near[0] if near else None


@lru_cache(maxsize=4)
def _load(rivers: str, streets: str, key: str) -> Entorno:
    return Entorno(rivers or None, streets or None, json.loads(key))


def for_config(cfg: dict) -> Entorno | None:
    p, z = cfg["productos"], cfg["zonificacion"]
    if not (p.get("sirga") or p.get("art_12k")):
        return None
    k = {"sirga": p.get("sirga"), "art_12k": p.get("art_12k")}
    return _load(z.get("rios_geojson") or "", z.get("calles_geojson") if p.get("art_12k") else "", json.dumps(k))
