"""Height caps by sector (Tigre: Ordenanza 4448/26) for the multifamiliar FOT.

zonificacion.alturas_yaml lists every sector of the ordinance (zone, localidad, "PB + N", conditions);
zonificacion.alturas_geojson has the polygons tools/alturas_4448.py could build from OSM streets. For a listing:
  in a polygon of its zone           that sector's height (the highest if it is in several: never lose a hit)
  zone listed for its localidad      the zone's highest height there, with a warning (sector not identified)
  zone not in the ordinance there    no cap
A sector may also forbid medium/high density multifamiliar (sin_multifamiliar): only a polygon applies it;
without one the listing gets a warning to check it by hand.
"""

import json
from functools import lru_cache

import pyproj
import yaml
from shapely.geometry import Point, shape
from shapely.ops import transform

from .config import path
from .locate import _plain

_TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform


class Alturas:
    def __init__(self, yaml_path: str, geojson_path: str):
        self.sectors = yaml.safe_load(path(yaml_path).read_text(encoding="utf-8")) or []
        fc = json.loads(path(geojson_path).read_text(encoding="utf-8")) if path(geojson_path).exists() else {"features": []}
        self.polygons = [(transform(_TO_M, shape(f["geometry"])), f["properties"]) for f in fc["features"]]

    def cap(self, zona: str, localidad: str, lat: float | None, lon: float | None) -> dict | None:
        """{'pb', 'fuente', 'sin_multifamiliar', 'condiciones', 'aviso'} for a zone at a point, or None."""
        z, loc = (zona or "").lower(), _plain(localidad or "")
        listed = [s for s in self.sectors if s["zona"].lower() == z and _plain(s["localidad"]) == loc]
        if not listed:
            return None
        if lat is not None and lon is not None:
            p = Point(_TO_M(lon, lat))
            inside = [props for g, props in self.polygons
                      if props["zona"].lower() == z and _plain(props["localidad"]) == loc and g.contains(p)]
            if inside:
                best = max(inside, key=lambda q: q["pb"])
                return {"pb": best["pb"], "fuente": f"sector {best['id']}",
                        "sin_multifamiliar": any(q["sin_multifamiliar"] for q in inside),
                        "condiciones": "; ".join(dict.fromkeys(q["condiciones"] for q in inside if q["condiciones"])),
                        "aviso": ""}
        top = max(s["pb"] for s in listed)
        forbids = any(s.get("sin_multifamiliar") for s in listed)
        return {"pb": top, "fuente": "máxima de la zona en la localidad", "sin_multifamiliar": False,
                "condiciones": "",
                "aviso": "altura_4448_sector_no_identificado (se usó la máxima de la zona en la localidad)"
                         + ("; verificar si el sector prohíbe multifamiliar (Ord. 4448)" if forbids else "")}


@lru_cache(maxsize=4)
def _load(yaml_path: str, geojson_path: str) -> Alturas:
    return Alturas(yaml_path, geojson_path)


def for_config(cfg: dict) -> Alturas | None:
    z = cfg["zonificacion"]
    if not z.get("alturas_yaml"):
        return None
    return _load(z["alturas_yaml"], z.get("alturas_geojson") or "")
