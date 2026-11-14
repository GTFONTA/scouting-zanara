"""The real lot behind a listing, from the provincial cadastre (ARBA, public WFS of IDERA): its parcel(s), area,
partida and street front, the sum of its FRENTE sides (a corner lot or a lot between two streets adds both).

Matching, calibrated on 37 listings that state their front (27-28/09/2026): the parcel, or up to `max_parcelas`
adjacent parcels, within `radio_m` of the pin whose area matches the listing's surface (±5% for one parcel, ±3% for
several); the closest and simplest group wins. With the pin 20 m or more away, a parcel of similar area is often
another lot, so those listings keep the front stated in the text (or none).
Asked only for the listings where the front can change the units; results are cached per listing
(data/cache_catastro.json), so a normal week only asks for the new ones.
"""

import json
import math
import time
from datetime import date

import pyproj
import requests
from shapely.geometry import Point, shape
from shapely.ops import transform, unary_union

from .config import path

_TO_M = pyproj.Transformer.from_crs(4326, 5347, always_xy=True).transform
SHARED_EDGE_M2 = 2          # two 0,5 m buffers overlapping on a shared edge of 2 m or more: adjacent parcels
SCORE_PER_PARCEL, SCORE_PER_ERROR = 40, 300     # a lot of fewer parcels, closer to the pin, with the closest area


class Catastro:
    def __init__(self, cfg: dict):
        self.c = cfg["productos"]["catastro"]
        self.file = path(self.c["cache"])
        self.cache = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {}
        self.session = requests.Session()
        self.asked, self.found, self.errors, self.failed_in_a_row = 0, 0, [], 0

    def lookup(self, r: dict) -> dict | None:
        """Parcel(s) of the listing, or None (no match, or the cadastre didn't answer)."""
        s, lat, lon = r["superficie_m2"], r["lat_usada"], r["lon_usada"]
        cached = self.cache.get(r["id"])
        if cached and abs(cached["superficie"] - s) <= 0.01 * s and \
                _meters(cached["lat"], cached["lon"], lat, lon) <= 5:
            result = cached["resultado"]
        else:
            if self.asked >= self.c["max_consultas_por_corrida"] or self.failed_in_a_row >= self.c["errores_max"]:
                return None
            try:
                result = self._match(lat, lon, s)
                self.failed_in_a_row = 0
            except (requests.RequestException, ValueError, KeyError) as e:
                self.failed_in_a_row += 1
                self.errors.append(f"{r['id']}: {type(e).__name__}: {str(e)[:120]}")
                return None
            self.cache[r["id"]] = {"superficie": s, "lat": lat, "lon": lon, "fecha": date.today().isoformat(),
                                   "resultado": result}
        self.found += bool(result)
        return result

    def save(self) -> None:
        self.file.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def health(self) -> dict:
        """Reported with the portals: if the cadastre stops answering it shows as a failure in the mail."""
        errors = self.errors[:3] + ([f"... y {len(self.errors) - 3} errores más"] if len(self.errors) > 3 else [])
        if self.failed_in_a_row >= self.c["errores_max"]:
            errors.append("demasiados errores seguidos: se dejó de consultar")
        return {"portal": "catastro ARBA", "paginas_ok": self.asked, "avisos": self.found, "errores": errors,
                "falla": bool(self.errors)}

    # ---------- WFS
    def _get(self, params: dict) -> dict:
        time.sleep(self.c["pausa_s"])
        self.asked += 1
        resp = self.session.get(self.c["wfs"], timeout=60, params={
            "service": "WFS", "version": "2.0.0", "request": "GetFeature", "outputFormat": "application/json",
            "srsName": "EPSG:4326", **params})
        resp.raise_for_status()
        return resp.json()

    def _match(self, lat: float, lon: float, s: float) -> dict | None:
        radius = max(self.c["radio_consulta_m"], 1.5 * math.sqrt(s))     # the whole lot around the pin
        d_lat, d_lon = radius / 111320, radius / (111320 * math.cos(math.radians(lat)))
        fc = self._get({"typeNames": "idera:Parcela",
                        "bbox": f"{lat - d_lat},{lon - d_lon},{lat + d_lat},{lon + d_lon},urn:ogc:def:crs:EPSG::4326"})
        parcels = [{"cca": f["properties"]["cca"], "pda": f["properties"]["pda"], "area": f["properties"]["ara1"],
                    "g": transform(_TO_M, shape(f["geometry"]))}
                   for f in fc["features"] if f.get("geometry") and f["properties"].get("ara1")]
        group = _best_group(parcels, Point(_TO_M(lon, lat)), s, self.c)
        if not group:
            return None
        ccas = [p["cca"] for p in group["parcels"]]
        sides = self._get({"typeNames": "idera:Lado_Catastral",
                           "CQL_FILTER": "cca IN (" + ",".join(f"'{c}'" for c in ccas) + ")"})["features"]
        front = sum(float(f["properties"]["lzn"] or 0) for f in sides if f["properties"]["tdl"] == "FRENTE")
        return {"frente": round(front, 2), "superficie": round(group["area"]), "partidas": [p["pda"] for p in group["parcels"]],
                "parcelas": len(ccas), "distancia_m": round(group["distance"]), "error_superficie": round(group["error"], 3)}


def _meters(lat1, lon1, lat2, lon2) -> float:
    return Point(_TO_M(lon1, lat1)).distance(Point(_TO_M(lon2, lat2)))


def _best_group(parcels: list[dict], pin: Point, s: float, c: dict) -> dict | None:
    """The parcel, or group of adjacent parcels, that best explains a lot of `s` m2 at `pin`."""
    tol_one, tol_many = c["tolerancia_una_parcela"], c["tolerancia_varias_parcelas"]
    parcels = [p for p in parcels if p["area"] <= s * (1 + tol_one)]
    neighbors: dict[int, set] = {}

    def adjacent(i: int) -> set:
        if i not in neighbors:
            a = parcels[i]["g"]
            neighbors[i] = {j for j, p in enumerate(parcels) if j != i and a.distance(p["g"]) < 1
                            and a.buffer(0.5).intersection(p["g"].buffer(0.5)).area > SHARED_EDGE_M2}
        return neighbors[i]

    best, seen = None, set()
    level = [frozenset([i]) for i, p in enumerate(parcels) if p["g"].distance(pin) <= c["radio_m"]]
    for size in range(1, c["max_parcelas"] + 1):
        grown = []
        for group in level:
            if group in seen:
                continue
            seen.add(group)
            area = sum(parcels[i]["area"] for i in group)
            error = abs(area - s) / s
            if error <= (tol_one if size == 1 else tol_many):
                distance = unary_union([parcels[i]["g"] for i in group]).distance(pin)
                score = distance + SCORE_PER_PARCEL * (size - 1) + SCORE_PER_ERROR * error
                if best is None or score < best["score"]:
                    best = {"score": score, "parcels": [parcels[i] for i in group], "area": area,
                            "error": error, "distance": distance}
            if area < s * (1 - tol_many):          # room for one more parcel
                grown += [group | {j} for i in group for j in adjacent(i) - group]
        level = grown
    return best
