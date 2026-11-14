"""Coordinates -> zona -> FOT.

Location confidence (flag_confianza):
  exacta             the portal gave lat/lon inside the partido
  geocodificada      the address was geocoded (Google if GOOGLE_GEOCODING_KEY, else Nominatim)
  aproximada_barrio  only the barrio/localidad is known -> max FOT of the zones touching it
"""

import csv
import difflib
import json
import os
import re
import time
import unicodedata

import pyproj
import requests
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree

from .config import path

_TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform


def _plain(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode()
    return " ".join(s.lower().split())


# words that don't identify a street ("Av.", "Gral.", "Intendente", ...)
_STREET_NOISE = {"av", "avda", "avenida", "calle", "pasaje", "pje", "gral", "general", "int", "intendente",
                 "dr", "doctor", "cnel", "coronel", "tte", "teniente", "cap", "capitan", "obispo", "pte",
                 "presidente", "ing", "ingeniero", "alte", "almirante", "sgto", "sargento", "cmte",
                 "comandante", "del", "de", "la", "el", "los", "las", "al", "n", "nro", "bis"}


def _street_tokens(s: str) -> frozenset:
    words = re.sub(r"[^a-z ]", " ", _plain(s)).split()
    return frozenset(w for w in words if w not in _STREET_NOISE and len(w) > 1)


def load_normativa(cfg: dict) -> dict[str, list[dict]]:
    """Zone name of the layer -> its rows in normativa_zonas.csv (C.O.U. T.O. 2022), through alias_zonas."""
    p = cfg["productos"]
    with open(path(p["normativa_csv"]), encoding="utf-8") as fh:
        rows = {r["zona"]: r for r in csv.DictReader(fh)}
    fc = json.loads(path(cfg["zonificacion"]["zonas_geojson"]).read_text(encoding="utf-8"))
    names = {f["properties"]["zona"] for f in fc["features"]} | set(rows)
    return {z: [rows[n] for n in p["alias_zonas"].get(z, [z]) if n in rows] for z in names}


class Locator:
    def __init__(self, cfg: dict):
        z = cfg["zonificacion"]
        self.cfg = cfg
        self.radius = z["radio_busqueda_zona_m"]
        self.radius_outside = z["radio_max_sin_zona_m"]
        if cfg["productos"]["activo"]:
            # FOT of a layer zone = the highest of its normativa rows (CR1: sectors A and B)
            self.normativa = load_normativa(cfg)
            self.table = {name: {"fot": max((float(r["fot"]) for r in rows if r["fot"]), default="")}
                          for name, rows in self.normativa.items()}
        else:
            self.normativa = None
            with open(path(z["fot_csv"]), encoding="utf-8") as fh:
                self.table = {r["zona"]: r for r in csv.DictReader(fh)}
        fc = json.loads(path(z["zonas_geojson"]).read_text(encoding="utf-8"))
        self.zones = [(transform(_TO_M, shape(f["geometry"])), f["properties"]["zona"]) for f in fc["features"]]
        self.tree = STRtree([g for g, _ in self.zones])
        bc = json.loads(path(z["barrios_geojson"]).read_text(encoding="utf-8"))
        self.barrios = {_plain(f["properties"]["barrio"]): transform(_TO_M, shape(f["geometry"])) for f in bc["features"]}
        self.barrio_names = {_plain(f["properties"]["barrio"]): f["properties"]["barrio"] for f in bc["features"]}
        # partido boundary = union of its localidades (OSM); pins within the margin still count (border lots)
        self.partido_strict = unary_union(list(self.barrios.values()))
        self.partido = self.partido_strict.buffer(z["margen_partido_m"])
        self.aliases = {_plain(k): _plain(v) for k, v in cfg["geocodificacion"]["alias_barrios"].items()}
        sc = json.loads(path(z["calles_geojson"]).read_text(encoding="utf-8"))
        by_name = {}
        for f in sc["features"]:
            by_name.setdefault(f["properties"]["nombre"], []).append(transform(_TO_M, shape(f["geometry"])))
        self.streets = {name: (_street_tokens(name), unary_union(parts)) for name, parts in by_name.items()}
        self._last_nominatim = 0.0

    # ---------- helpers ----------
    def fot(self, zona):
        v = self.table.get(zona, {}).get("fot")
        return float(v) if v not in (None, "") else None

    def _inside(self, lat, lon) -> bool:
        return lat is not None and self.partido.contains(Point(_TO_M(lon, lat)))

    def geocode(self, address: str):
        if not address:
            return None
        q = address + self.cfg["geocodificacion"]["sufijo_direccion"]
        key = os.environ.get("GOOGLE_GEOCODING_KEY")
        try:
            if key:
                r = requests.get("https://maps.googleapis.com/maps/api/geocode/json",
                                 params={"address": q, "key": key, "region": "ar"}, timeout=20).json()
                if r.get("results"):
                    res = r["results"][0]
                    if res["geometry"]["location_type"] in ("ROOFTOP", "RANGE_INTERPOLATED"):
                        loc = res["geometry"]["location"]
                        return loc["lat"], loc["lng"]
                return None
            wait = 1.1 - (time.time() - self._last_nominatim)
            if wait > 0:
                time.sleep(wait)
            self._last_nominatim = time.time()
            r = requests.get("https://nominatim.openstreetmap.org/search",
                             params={"q": q, "format": "json", "limit": 1, "countrycodes": "ar"},
                             headers={"User-Agent": self.cfg["geocodificacion"]["user_agent"]}, timeout=20).json()
            if r and r[0].get("class") in ("place", "building", "highway") and r[0].get("addresstype") != "suburb":
                return float(r[0]["lat"]), float(r[0]["lon"])
        except (requests.RequestException, ValueError, KeyError):
            return None
        return None

    def _barrio_polygon(self, barrio_text: str):
        t = _plain(barrio_text)
        for alias, target in self.aliases.items():
            if alias in t:
                return target, self.barrios.get(target)
        for name, poly in sorted(self.barrios.items(), key=lambda kv: -len(kv[0])):
            if name in t:
                return name, poly
        return None, None

    def zone_at(self, lat, lon) -> dict:
        p = Point(_TO_M(lon, lat))
        idx = self.tree.query(p)
        hit = [self.zones[i] for i in idx if self.zones[i][0].contains(p)]
        zona_punto = hit[0][1] if hit else None
        # no zone, or a zone without FOT (Ru, AR, EPR: usually a border error of the layer) -> look wider
        rad = self.radius if hit and self.fot(zona_punto) is not None else self.radius_outside
        near = [self.zones[i] for i in self.tree.query(p.buffer(rad)) if self.zones[i][0].distance(p) <= rad]
        cands = [(z, self.fot(z)) for _, z in near if self.fot(z) is not None]
        zona_fot, fot = max(cands, key=lambda t: t[1]) if cands else (None, None)
        # commercial or industrial zone next to the point (incentives of Arts. 1.2.1.16 and 1.2.1.20 a)
        ci_rad = self.cfg["productos"]["flags"]["distancia_zona_c_o_i_m"]
        ci = [self.zones[i][0].distance(p) for i in self.tree.query(p.buffer(ci_rad))
              if self.zones[i][1][0] in "CI"]
        return {
            "zona": zona_punto,
            "fot_zona": self.fot(zona_punto) if zona_punto else None,
            "distancia_borde_m": round(hit[0][0].boundary.distance(p)) if hit else None,
            "zonas_cercanas": ",".join(sorted({z for _, z in near} - {zona_punto})),
            "zonas_candidatas": ",".join(sorted({z for _, z in near})),
            "distancia_zona_c_o_i_m": round(min(ci)) if ci and min(ci) <= ci_rad else None,
            "zona_fot_usado": zona_fot,
            "fot_usado": fot,
            "fot_fuente": ("punto" if zona_fot == zona_punto else f"max_{rad}m") if fot is not None else "",
        }

    # ---------- main entry ----------
    def locate(self, r: dict) -> dict:
        out = {"flag_confianza": "", "barrio_usado": ""}
        lat, lon = r.get("lat"), r.get("lon")
        exact = (r.get("direccion_visibilidad") or "EXACT").upper() == "EXACT"
        if lat is not None and exact and not self._inside(lat, lon):
            if self._misplaced_pin(r, lat, lon):
                r.setdefault("alertas", []).append("pin_del_portal_fuera_del_partido")
                return self._by_street(r, out) or self._by_barrio(r, out)
            # the portal pins it precisely outside San Isidro: trust the pin, don't geocode it back in
            out["motivo_descarte"] = "fuera_del_partido"
            return out
        if lat is not None and exact:
            out["flag_confianza"] = "exacta"
            if not self.partido_strict.contains(Point(_TO_M(lon, lat))):
                r.setdefault("alertas", []).append("pin_en_el_borde_del_partido")
        else:
            if lat is not None:
                r.setdefault("alertas", []).append("coordenadas_no_exactas_en_portal")
            address = r.get("direccion") or ""
            # without a street number the geocoder returns an arbitrary point of the street: use the barrio
            g = self.geocode(re.sub(r"\s+al\s+", " ", address)) if re.search(r"\d", address) else None
            if g and self._inside(*g):
                lat, lon = g
                out["flag_confianza"] = "geocodificada"
            else:
                lat = lon = None
        if lat is not None:
            out.update(self.zone_at(lat, lon))
            out["lat_usada"], out["lon_usada"] = lat, lon
            if out["fot_usado"] is not None:
                return out
            r.setdefault("alertas", []).append("sin_zona_cercana_se_usa_barrio")
        return self._by_street(r, out) or self._by_barrio(r, out)

    def _misplaced_pin(self, r: dict, lat: float, lon: float) -> bool:
        """Mercado Libre sometimes drops the pin just outside the partido for a listing that states a
        San Isidro localidad: treat it as a loading error (only near the border, only real localidades)."""
        z = self.cfg["zonificacion"]
        if r.get("portal") not in z["portales_pin_fuera_revisar"]:
            return False
        if _plain(r.get("barrio") or "") not in self.barrios:
            return False
        return self.partido_strict.distance(Point(_TO_M(lon, lat))) <= z["distancia_max_pin_fuera_m"]

    # ---------- hidden street number: use the street (or corner) ----------
    def _match_street(self, text: str):
        """OSM streets whose name matches `text` (all its words present, or a close spelling)."""
        tokens = _street_tokens(text)
        if not tokens:
            return []
        exact = [g for toks, g in self.streets.values() if tokens <= toks]
        if exact:
            return exact
        joined = " ".join(sorted(tokens))
        return [g for toks, g in self.streets.values()
                if toks and difflib.SequenceMatcher(None, joined, " ".join(sorted(toks))).ratio() >= 0.85]

    def _max_fot_near(self, geom, radius):
        """(zone with the highest FOT, its FOT, every zone name) within `radius` of `geom`."""
        near = [self.zones[i] for i in self.tree.query(geom.buffer(radius)) if self.zones[i][0].distance(geom) <= radius]
        cands = [(z, self.fot(z)) for _, z in near if self.fot(z) is not None]
        zona_fot, fot = max(cands, key=lambda t: t[1]) if cands else (None, None)
        return zona_fot, fot, sorted({z for _, z in near})

    def _by_street(self, r: dict, out: dict):
        address = re.split(r"\s+(?:entre|e/)\s+", r.get("direccion") or "", flags=re.I)[0]   # "X al 100 e/ A y B"
        address = re.sub(r"\d+", " ", address)
        if not address.strip() or _plain(address).startswith("barrio"):
            return None
        parts = [p for p in re.split(r"\s+(?:y|e|esq\.?|esquina)\s+|/", address, flags=re.I) if p.strip()]
        matches = [self._match_street(p) for p in parts[:2]]
        if not all(matches):
            return None
        lines = [unary_union(m) for m in matches]
        # restrict to the localidad when the portal gives one (not for sub-barrios like "Lomas de San Isidro")
        # ("San Isidro" is ambiguous: Zonaprop uses it both for the localidad and the whole partido)
        loc = self.barrios.get(_plain(r.get("barrio") or ""))
        if loc is not None and _plain(r.get("barrio") or "") != "san isidro":
            clipped = [ln.intersection(loc.buffer(200)) for ln in lines]
            if all(not c.is_empty for c in clipped):
                lines = clipped
        geom, source = unary_union(lines), "max_calle"
        if len(lines) == 2:
            corner = lines[0].buffer(15).intersection(lines[1].buffer(15))
            if not corner.is_empty:
                geom, source = corner.centroid, "esquina"
        zona_fot, fot, names = self._max_fot_near(geom, self.radius)
        if fot is None:
            return None
        c = transform(pyproj.Transformer.from_crs(5347, 4326, always_xy=True).transform, geom.centroid)
        out.update({"flag_confianza": "aproximada_barrio", "barrio_usado": " y ".join(p.strip() for p in parts[:2]),
                    "zona": None, "fot_zona": None, "distancia_borde_m": None, "zonas_cercanas": "",
                    "zonas_candidatas": ",".join(names), "distancia_zona_c_o_i_m": None,
                    "zona_fot_usado": zona_fot, "fot_usado": fot, "fot_fuente": source,
                    "lat_usada": c.y, "lon_usada": c.x})
        return out

    def _by_barrio(self, r: dict, out: dict) -> dict:
        """Fallback: max FOT of the zones touching the barrio/localidad (never lose an opportunity)."""
        name, poly = self._barrio_polygon(r.get("barrio") or r.get("direccion") or "")
        if poly is None:
            out["motivo_descarte"] = "sin_ubicacion"
            return out
        touching = [z for g, z in self.zones if g.intersects(poly)]
        cands = [(z, self.fot(z)) for z in touching if self.fot(z) is not None]
        zona_fot, fot = max(cands, key=lambda t: t[1])
        c = transform(pyproj.Transformer.from_crs(5347, 4326, always_xy=True).transform, poly.centroid)
        out.update({"flag_confianza": "aproximada_barrio", "barrio_usado": name, "zona": None, "fot_zona": None,
                    "distancia_borde_m": None, "zonas_cercanas": "", "zonas_candidatas": ",".join(sorted(set(touching))),
                    "distancia_zona_c_o_i_m": None, "zona_fot_usado": zona_fot,
                    "fot_usado": fot, "fot_fuente": "max_barrio", "lat_usada": c.y, "lon_usada": c.x})
        return out

    def localidad(self, r: dict) -> str:
        """Localidad of a listing (for the small-lot comparables): from its point, else from the barrio text."""
        lat, lon = r.get("lat_usada") or r.get("lat"), r.get("lon_usada") or r.get("lon")
        if lat is not None and lon is not None:
            p = Point(_TO_M(lon, lat))
            for name, poly in self.barrios.items():
                if poly.contains(p):
                    return self.barrio_names[name]
        name, _ = self._barrio_polygon(r.get("barrio") or "")
        return self.barrio_names.get(name, "")
