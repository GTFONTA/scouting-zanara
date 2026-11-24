"""Same property published more than once (several agencies, re-postings, several portals).

Duplicates: surface within ±tol AND price within ±tol AND (distance < max_m, or same barrio when one of
them is only located by barrio, or same street within distancia_max_misma_calle_m: ~10% of the properties published on
both portals have their pins more than 150 m apart). Each group keeps the record with the best flag_confianza (then the lowest
incidencia, so an opportunity is never hidden behind a worse copy); the other links go to `otros_links`
and their ids to `ids_duplicados` (used by store.py to decide what is new).
With productos.activo the best result goes first (oportunidad, casi, gran predio), then the lowest incidencia.
"""

import math
import re

from .locate import _street_tokens

CONFIDENCE_RANK = {"exacta": 0, "geocodificada": 1, "aproximada_barrio": 2, "": 3}
RESULT_RANK = {"oportunidad": 0, "casi": 1, "gran_predio": 2}


def _meters(a: dict, b: dict, lat="lat_usada", lon="lon_usada") -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (a[lat], a[lon], b[lat], b[lon]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


FRONT_KEYS = ("frente_m", "fondo_m", "frente_fuente", "frente_catastro_m", "superficie_catastro_m2", "partidas_catastro")


def share_front(rows: list[dict], cfg: dict) -> None:
    """The same lot published several times: the longest front found for one publication (stated in its text, or
    of the parcel under its pin) serves the others, before the evaluation, so the kept copy is valued with it.
    Same rule as the duplicates, with the portal's pins."""
    d = cfg["deduplicacion"]
    tol, max_m, same_street_m = d["tolerancia"], d["distancia_max_m"], d["distancia_max_misma_calle_m"]
    ok = lambda r: r.get("precio_usd") and r.get("superficie_m2") and r.get("lat") is not None   # noqa: E731
    known = [r for r in rows if ok(r) and r.get("frente_m")]

    def same_lot(r, k):
        if not (_close(r["precio_usd"], k["precio_usd"], tol) and _close(r["superficie_m2"], k["superficie_m2"], tol)):
            return False
        dist = _meters(r, k, "lat", "lon")
        return dist < max_m or (bool(_street(r)) and _street(r) == _street(k) and dist < same_street_m)

    for r in rows:
        if not ok(r):
            continue
        best = max((k for k in known if k is not r and same_lot(r, k)), key=lambda k: k["frente_m"], default=None)
        if best and best["frente_m"] > (r.get("frente_m") or 0):
            for key in FRONT_KEYS:
                r[key] = best.get(key)
            r["alertas"].append(f"frente_de_otra_publicacion ({best['id']})")


def share_surface(rows: list[dict], cfg: dict) -> None:
    """The same lot published several times, one with its surface corrected from the text (the covered or buildable
    m2 loaded as the lot) and another without text to correct it: the corrected lot serves the other (San Isidro,
    24/11/2026: "Galpón - Beccar", 1783 m2 covered on a 1084 m2 lot; the Mercado Libre copies have no description).
    Same price, the other's listed surface equal to the corrected one's original, and the same place."""
    d = cfg["deduplicacion"]
    tol, max_m, same_street_m = d["tolerancia"], d["distancia_max_m"], d["distancia_max_misma_calle_m"]
    ok = lambda r: r.get("precio_usd") and r.get("superficie_m2") and r.get("lat") is not None   # noqa: E731
    fixed = [r for r in rows if ok(r) and r.get("superficie_aviso_m2")]
    for r in rows:
        if not ok(r) or r.get("superficie_aviso_m2"):
            continue
        for k in fixed:
            if not (_close(r["precio_usd"], k["precio_usd"], tol) and _close(r["superficie_m2"], k["superficie_aviso_m2"], tol)):
                continue
            dist = _meters(r, k, "lat", "lon")
            if dist < max_m or (bool(_street(r)) and _street(r) == _street(k) and dist < same_street_m):
                r["alertas"].append(f"superficie_corregida (el aviso dice {r['superficie_m2']:.0f} m2; otra publicación "
                                    f"del mismo inmueble, {k['id']}: {k['superficie_m2']:.0f} m2)")
                r["superficie_aviso_m2"], r["superficie_m2"] = r["superficie_m2"], k["superficie_m2"]
                r["superficie_fuente"], r["superficie_dudosa"] = f"otra publicación ({k['superficie_fuente']})", False
                break


def _close(x, y, tol) -> bool:
    return abs(x - y) <= tol * max(x, y)


def _street(r: dict) -> frozenset:
    return _street_tokens(re.sub(r"\d+", " ", (r.get("direccion") or "").split(",")[0]))


def _same_place(a: dict, b: dict, max_m: float, same_street_m: float) -> bool:
    if "aproximada_barrio" in (a.get("flag_confianza"), b.get("flag_confianza")):
        ba = (a.get("barrio_usado") or a.get("barrio") or "").lower()
        bb = (b.get("barrio_usado") or b.get("barrio") or "").lower()
        if ba and ba == bb:
            return True
    d = _meters(a, b)
    if d < max_m:
        return True
    # some properties are pinned far apart by different portals: same street is enough nearby
    sa, sb = _street(a), _street(b)
    return bool(sa) and sa == sb and d < same_street_m


def dedupe(rows: list[dict], cfg: dict) -> list[dict]:
    d = cfg["deduplicacion"]
    tol, max_m, same_street_m = d["tolerancia"], d["distancia_max_m"], d["distancia_max_misma_calle_m"]
    located = [r for r in rows if r.get("lat_usada") is not None and r.get("precio_usd") and r.get("superficie_m2")]
    others = [r for r in rows if r not in located]
    located.sort(key=lambda r: r["precio_usd"])

    parent = list(range(len(located)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, a in enumerate(located):
        for j in range(i + 1, len(located)):
            b = located[j]
            if b["precio_usd"] > a["precio_usd"] * (1 + tol):
                break                                   # sorted by price: nothing further can match
            if _close(a["superficie_m2"], b["superficie_m2"], tol) and _same_place(a, b, max_m, same_street_m):
                parent[find(j)] = find(i)

    groups: dict[int, list[dict]] = {}
    for i, r in enumerate(located):
        groups.setdefault(find(i), []).append(r)
    products = cfg["productos"]["activo"]

    def rank(r):
        inc = r.get("incidencia_usd_m2") if r.get("incidencia_usd_m2") is not None else 1e9
        conf = CONFIDENCE_RANK.get(r.get("flag_confianza") or "", 3)
        if not products:
            return conf, inc
        return conf, RESULT_RANK.get(r["resultado"], 3), inc

    kept = []
    for members in groups.values():
        members.sort(key=rank)
        best, rest = members[0], members[1:]
        best["otros_links"] = " ".join(r["url"] for r in rest)
        best["ids_duplicados"] = " ".join(r["id"] for r in rest)
        best["cantidad_publicaciones"] = len(members)
        kept.append(best)
    for r in others:
        r.setdefault("otros_links", "")
        r.setdefault("ids_duplicados", "")
        r.setdefault("cantidad_publicaciones", 1)
    return kept + others
