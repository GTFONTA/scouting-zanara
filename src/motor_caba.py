"""Engine for the Ciudad de Buenos Aires: buildable m2 per PARCEL from Ciudad 3D (Código Urbanístico), not per zone.

For each listing with a pin (or an address USIG can geocode):
  1. parcel at the pin: epok /catastro/parcela/?lng&lat -> SMP, catastro surface and front
  2. edificabilidad of the SMP: epok /cur3d/seccion_edificabilidad -> height of the unit and of its plano
     límite, buildable footprint, FOT (only for the plusvalía), district, Ley 6062 land incidence (UVA/m2),
     catalogación, afectaciones (ensanche, apertura, riesgo hídrico), APH
  3. buildable m2 = the Código Urbanístico envelope (arts. 6.2-6.4, see municipios/caba/GUIA_NORMATIVA.md):
     footprint x efficiency x floors (2,90 m) + the two set-back floors + the basamento of C.A./C.M.
     The FOT is NOT a right to build in CABA (decided by Gonzalo, 19/11/2026)
  4. plusvalía (derecho de desarrollo urbano, Ley 6062 as worded by Ley 6710), computed here:
     max(0, 0,8 x m2 - FOT x superficie) x incidencia UVA x alícuota; it matched the 1.066 cached answers of
     /cur3d/calcular_plusvalia exactly. To USD with the UVA of the BCRA and the dólar MEP
  5. hits only: the side neighbours (catastro floors, unit height) -> "potencial extra, revisar por completamiento
     y esquina" (arts. 6.5.5 and 6.4.6); a flag, it doesn't change the m2
Everything is cached by pin / SMP in data/cache_caba.json (one query per parcel, ever).

Classification (municipios/caba/municipio.yaml):
  m2 construibles = envolvente
  incidencia total = (precio + plusvalía) / m2 construibles
  incidencia de referencia = incidencia de la Ley 6062 para el distrito (UVA/m2 -> USD/m2): the City's own
      valuation of a buildable m2 of land there, so the threshold follows the barrio by itself
  oportunidad   m2 > m2_construibles_min and incidencia total <= ratio_oportunidad x referencia
  casi          incidencia total <= ratio_casi x referencia, or an opportunity on a catalogued (cautelar) building
  gran predio   superficie >= sup_min_gran_predio, always reported
"""

import copy
import csv
import html
import json
import math
import re
import time
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlencode

import pyproj
import requests

from . import rentabilidad
from .config import path
from .locate import _street_tokens
from .dedupe import dedupe, share_surface
from .normalize import FIELDS, SEVERAL_LOTS, dolar_mep, from_mercadolibre, from_zonaprop, normalize

MAPPERS = {"zonaprop": from_zonaprop, "mercadolibre": from_mercadolibre}
# USIG geocodes in Gauss-Krüger Buenos Aires
_GKBA = pyproj.Transformer.from_crs(
    "+proj=tmerc +lat_0=-34.6297166 +lon_0=-58.4627 +k=1 +x_0=100000 +y_0=100000 +ellps=intl +units=m +no_defs",
    4326, always_xy=True).transform
SPECIAL = re.compile(r"^\s*(APH|AE|U\s*\d|UBP|RUA|ARE)", re.I)     # districts with their own rules
BLOCKING = ("INTEGRAL", "ESTRUCTURAL")          # catalogued: the building can't be demolished
CAUTION = ("CAUTELAR",)

COLUMNS = FIELDS + [
    "resultado", "via", "motivo_descarte", "alertas", "flags", "cantidad_publicaciones", "otros_links", "ids_duplicados",
    "precio_original", "cotizacion_usada", "superficie_fuente", "superficie_terreno_m2", "superficie_total_m2",
    "superficie_cubierta_m2", "flag_confianza", "lat_usada", "lon_usada",
    "smp", "direccion_catastro", "superficie_catastro_m2", "frente_catastro_m", "parcela_coincide",
    "emparejamiento", "parcelas_emparejadas",
    "distrito_cpu", "fot_medianera", "fot_semi_libre", "fot_perim_libre", "fot_usado", "tipo_fot", "altura_max_m",
    "altura_unidad_m", "pisos", "planta_edificable_m2", "eficiencia_planta", "m2_sin_plusvalia", "m2_construibles", "incidencia_usd_m2", "plusvalia_uva", "uva_ars", "plusvalia_usd", "incidencia_total_usd_m2",
    "incidencia_ley6062_uva", "incidencia_referencia_usd_m2", "ratio_incidencia", "proteccion", "afectaciones",
    "gran_predio", "potencial_extra", "tipologia_portal",
] + rentabilidad.COLUMNS


class Ciudad3D:
    """epok.buenosaires.gob.ar (the API behind Ciudad 3D), USIG and the BCRA's UVA; all cached."""

    def __init__(self, cfg: dict):
        self.c = cfg["caba"]
        self.file = path(self.c["cache"])
        self.cache = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {}
        for k in ("pin", "smp", "plusvalia", "geo", "catastro_smp"):
            self.cache.setdefault(k, {})
        self.session = requests.Session()
        self.asked, self.errors, self.failed_in_a_row, self.recoveries = 0, [], 0, 0
        self.stopped = 0                         # queries skipped after giving up (summarised, not one error each)
        self.capped = 0                          # queries skipped because the run reached its query cap
        # the main pass leaves consultas_reservadas_linderos for the neighbours of the hits (extra_potential)
        self.limit = self.c["max_consultas_por_corrida"] - self.c.get("consultas_reservadas_linderos", 0)
        self._uva = None

    def _get(self, url: str, params: dict | None = None) -> dict | list:
        """One query, with retries for the server's hiccups (503, connection reset). After `errores_max` failures in
        a row it waits `espera_recupero_s` and tries again, up to `recuperos_max` times; then it gives up for the run.
        First night run (18/11/2026): a short outage tripped the old stop for good and left 1.719 listings unchecked."""
        if self.asked >= self.limit:
            self.capped += 1
            raise RuntimeError("se dejó de consultar (tope de consultas)")
        if self.failed_in_a_row >= self.c["errores_max"]:
            if self.recoveries >= self.c.get("recuperos_max", 3):
                self.stopped += 1
                raise RuntimeError("se dejó de consultar (Ciudad 3D no responde)")
            self.recoveries += 1
            time.sleep(self.c.get("espera_recupero_s", 180))
            self.failed_in_a_row = 0
        waits = list(self.c.get("reintentos_s", [10, 30]))
        while True:
            time.sleep(self.c["pausa_s"])
            self.asked += 1
            try:
                r = self.session.get(url, params=params, timeout=60)
                if getattr(r, "status_code", 200) >= 500 and waits:
                    time.sleep(waits.pop(0))
                    continue
                r.raise_for_status()
                out = r.json()
                self.failed_in_a_row = 0
                return out
            except (requests.ConnectionError, requests.Timeout) as e:
                if waits:
                    time.sleep(waits.pop(0))
                    continue
                self.failed_in_a_row += 1
                raise RuntimeError(f"{type(e).__name__}: {str(e)[:150]}") from e
            except (requests.RequestException, ValueError) as e:
                self.failed_in_a_row += 1
                raise RuntimeError(f"{type(e).__name__}: {str(e)[:150]}") from e

    def parcel(self, lat: float, lon: float) -> dict | None:
        """Parcel at the pin; a pin on the street (no parcel) tries 8 points around it, 12 m away."""
        key = f"{lat:.6f},{lon:.6f}"
        if key not in self.cache["pin"]:
            found = None
            d_lat, d_lon = 12 / 111_000, 12 / (111_000 * math.cos(math.radians(lat)))
            for i, j in [(0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]:
                d = self._get(f"{self.c['api']}/catastro/parcela/", {"lng": lon + j * d_lon, "lat": lat + i * d_lat})
                if isinstance(d, dict) and d.get("smp"):
                    found = {**d, "desplazado": bool(i or j)}
                    break
            self.cache["pin"][key] = found
        return self.cache["pin"][key]

    def buildable(self, smp: str) -> dict:
        if smp not in self.cache["smp"]:
            self.cache["smp"][smp] = self._get(f"{self.c['api']}/cur3d/seccion_edificabilidad/", {"smp": smp})
        return self.cache["smp"][smp]

    def parcel_by_smp(self, smp: str) -> dict | None:
        """Catastro of a parcel by SMP (floors above ground, covered area): used for the side neighbours."""
        if smp not in self.cache["catastro_smp"]:
            d = self._get(f"{self.c['api']}/catastro/parcela/", {"smp": smp})
            self.cache["catastro_smp"][smp] = d if isinstance(d, dict) and d.get("smp") else None
        return self.cache["catastro_smp"][smp]

    def plusvalia(self, smp: str, area: float) -> dict:
        key = f"{smp}|{round(area)}"
        if key not in self.cache["plusvalia"]:
            self.cache["plusvalia"][key] = self._get(f"{self.c['api']}/cur3d/calcular_plusvalia/",
                                                     {"smp": smp, "area_edificar": round(area)})
        return self.cache["plusvalia"][key]

    def geocode(self, address: str) -> tuple[float, float] | None:
        """USIG: street and number in CABA -> (lat, lon); None if it isn't an exact address.
        The service wants street and number apart (calle=Moldes&altura=2477); with the whole address in `calle`
        it answers the JSON string "Parametros incorrectos." (first night run, 17/11/2026)."""
        m = ADDRESS.match(address or "")
        if not m:
            return None
        street, number = m.group(1).strip(" ,."), int(m.group(2))
        key = f"{street.lower()}|{number}"
        if key not in self.cache["geo"]:
            try:
                d = self._get(f"{self.c['usig']}/rest/normalizar_y_geocodificar_direcciones",
                              {"calle": street, "altura": number, "desambiguar": 1})
                g = (d.get("GeoCodificacion") if isinstance(d, dict) else None) or {}
                self.cache["geo"][key] = list(_GKBA(float(g["x"]), float(g["y"])))[::-1] if g.get("x") else None
            except (RuntimeError, ValueError, KeyError, TypeError) as e:
                self.errors.append(f"geocodificación {address[:40]}: {e}")
                return None
        g = self.cache["geo"][key]
        return tuple(g) if g else None

    def uva(self) -> float | None:
        """Last UVA value (ARS) published by the BCRA up to today."""
        if self._uva is None:
            try:
                d = self._get(self.c["uva_api"], {"hasta": date.today().isoformat(), "limit": 1})
                self._uva = float(d["results"][0]["detalle"][0]["valor"])
                self.cache["uva"] = {"valor": self._uva, "fecha": d["results"][0]["detalle"][0]["fecha"]}
            except (RuntimeError, KeyError, IndexError, ValueError) as e:
                self.errors.append(f"UVA del BCRA: {e}")
                saved = self.cache.get("uva")
                self._uva = saved["valor"] if saved else 0.0
        return self._uva or None

    def save(self) -> None:
        self.file.write_text(json.dumps(self.cache, ensure_ascii=False), encoding="utf-8")

    def health(self) -> dict:
        real = [e for e in self.errors if "se dejó de consultar" not in e]
        errors = real[:3] + ([f"... y {len(real) - 3} errores más"] if len(real) > 3 else [])
        if self.stopped:
            errors.append(f"se dejó de consultar: {self.stopped} consultas sin hacer"
                          f" (Ciudad 3D no respondió tras {self.recoveries} esperas)")
        if self.capped:                          # not an outage: the rest waits for the next run (cache)
            errors.append(f"tope de {self.c['max_consultas_por_corrida']} consultas por corrida: {self.capped} "
                          f"consultas quedan para la próxima corrida")
        return {"portal": "Ciudad 3D", "paginas_ok": self.asked, "avisos": len(self.cache["smp"]), "errores": errors,
                "falla": bool(self.errors)}


def _f(v) -> float:
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def listed_covered(r: dict, q: dict, s: float, k: dict) -> bool:
    """The listing's surface is the covered area of catastro parcel q (CABA error #10, Gonzalo 24/11/2026: "Casa
    en Palermo Soho" with 365 m2 tot. / 345 cub. on a 200 m2 lot whose catastro covered area is 354): q's covered
    m2 within tolerancia_cubierta of the listing's total or covered surface, q's lot smaller, same street."""
    if r.get("superficie_aviso_m2"):
        return False                 # the surface was already corrected to the lot from the text (galpón #9)
    cov, lot = _f(q.get("superficie_cubierta")), _f(q.get("superficie_total"))
    tol = k.get("tolerancia_cubierta", 0.05)
    if not cov or not lot or lot > (1 - tol) * s:      # galpón #9: 562 m2 covered on a 525 lot
        return False
    if not any(v and abs(cov - v) <= tol * v for v in (s, _f(r.get("superficie_cubierta_m2")))):
        return False
    street = re.split(r"\b(?:entre|e/|esq(?:uina)?\.?)\s", r.get("direccion") or "", flags=re.I)[0]   # not the cross streets
    mine = _street_tokens(re.sub(r"\d+", " ", street))
    theirs = _street_tokens(re.sub(r"\d+", " ", q.get("direccion") or ""))
    return bool(mine & theirs)


def evaluate(r: dict, c3d: Ciudad3D, cfg: dict, mep: float | None, try_match: bool = False) -> None:
    """Fill r in place with the parcel, buildable m2, plusvalía, incidence and classification."""
    k = cfg["caba"]
    r.update(resultado="descartado", via="")
    s, price = r.get("superficie_m2"), r.get("precio_usd")
    if r["motivo_descarte"]:
        return
    if s < cfg["zonificacion"]["superficie_min_prefiltro"]:
        r["motivo_descarte"] = "superficie_menor_prefiltro"
        return
    lat, lon = r.get("lat"), r.get("lon")
    exact = (r.get("direccion_visibilidad") or "EXACT").upper() == "EXACT" and not r.get("pin_generico")
    if r.get("pin_generico"):
        r["alertas"].append("pin_generico (el mismo punto en varios avisos distintos: se ubica por la dirección)")
    r["flag_confianza"] = "exacta" if lat is not None and exact else ""
    if not r["flag_confianza"]:
        g = c3d.geocode(r.get("direccion") or "")
        if g:
            (lat, lon), r["flag_confianza"] = g, "geocodificada"
    if not r["flag_confianza"]:
        r["motivo_descarte"] = "sin_ubicacion"
        return
    lo, la = k["bbox"]
    if not (lo[0] <= lon <= lo[1] and la[0] <= lat <= la[1]):
        r["motivo_descarte"] = "fuera_del_municipio"
        return
    r["lat_usada"], r["lon_usada"] = lat, lon
    try:
        p = c3d.parcel(lat, lon)
        if not p:
            r["motivo_descarte"] = "fuera_del_municipio (sin parcela en el pin)"
            return
        e = c3d.buildable(p["smp"])
    except RuntimeError as ex:
        c3d.errors.append(f"{r['id']}: {ex}")
        r["motivo_descarte"] = "ciudad3d_sin_respuesta"
        return
    sup_cat = _f(p.get("superficie_total")) or _f(e.get("superficie_parcela"))
    r.update(smp=p["smp"], direccion_catastro=p.get("direccion", ""), superficie_catastro_m2=sup_cat or None,
             frente_catastro_m=_f(p.get("frente")) or None)
    r["parcela_coincide"] = bool(sup_cat) and abs(sup_cat - s) <= k["tolerancia_superficie"] * s
    if r["parcela_coincide"] and (r.get("pin_generico") or r.get("flag_confianza") == "geocodificada"):
        mine = _street_tokens(re.sub(r"\d+", " ", r.get("direccion") or ""))
        theirs = _street_tokens(re.sub(r"\d+", " ", p.get("direccion") or ""))
        if mine and theirs and not mine & theirs:     # CABA error #7: Formosa 50 fell on Av. La Plata 541
            r["parcela_coincide"] = False
            r["alertas"].append(f"parcela_en_otra_calle (catastro: {p.get('direccion', '')})")
    if not r["parcela_coincide"] and listed_covered(r, p, s, k):
        r["alertas"].append(f"superficie_es_la_cubierta (el aviso dice {s:.0f} m2; el catastro da "
                            f"{_f(p.get('superficie_cubierta')):.0f} m2 cubiertos sobre un lote de {sup_cat:.0f} m2: "
                            f"se usa el lote)")
        s = r["superficie_m2"] = sup_cat
        r["superficie_fuente"], r["parcela_coincide"] = "catastro (el aviso daba la cubierta)", True
    if r.get("pin_generico") and not r["parcela_coincide"]:
        r["motivo_descarte"] = "ubicacion_dudosa (pin genérico del portal y la parcela de la dirección no coincide)"
        return
    group, pending = None, False      # parcels of the listing when the pin's alone doesn't match its surface
    if not r["parcela_coincide"]:
        try:
            stated_front = _f(r.get("frente_m")) if r.get("frente_fuente") == "aviso" else None
            group = match_parcels(p, e, s, c3d, k, stated_front, r) if try_match else None
        except RuntimeError as ex:
            pending = True                          # query cap or outage: tried again in the next run (cache)
            if "tope de consultas" not in str(ex):
                c3d.errors.append(f"{r['id']}: {ex}")
        if group and group["tipo"] == "vecina":      # the pin fell on the next parcel: that one is the listing's
            p, e, sup_cat = group["parcelas"][0]
            if group.get("cubierta"):                # ... and the listing's surface was its covered area
                r["alertas"].append(f"superficie_es_la_cubierta (el aviso dice {s:.0f} m2; el catastro da "
                                    f"{_f(p.get('superficie_cubierta')):.0f} m2 cubiertos sobre un lote de "
                                    f"{sup_cat:.0f} m2: se usa el lote)")
                s = r["superficie_m2"] = sup_cat
                r["superficie_fuente"] = "catastro (el aviso daba la cubierta)"
            r.update(smp=p["smp"], direccion_catastro=p.get("direccion", ""), superficie_catastro_m2=sup_cat,
                     frente_catastro_m=_f(p.get("frente")) or None)
        if group:
            r["emparejamiento"] = group["tipo"]
            r["parcelas_emparejadas"] = " + ".join(x[0]["smp"] for x in group["parcelas"])
            r["alertas"].append(f"parcela_emparejada ({group['tipo']}: {r['parcelas_emparejadas']}, "
                                f"{group['superficie']:.0f} m2 en catastro)")
        elif pending:
            r["alertas"].append(f"parcela_del_pin_no_coincide (catastro {sup_cat:.0f} m2): vecinas sin consultar "
                                f"por el tope de consultas, se reintenta en la próxima corrida; como mucho casi")
        else:
            r["alertas"].append(f"parcela_del_pin_no_coincide (catastro {sup_cat:.0f} m2, ninguna vecina suma la "
                                f"superficie del aviso): como mucho casi")
    matched = r["parcela_coincide"] or bool(group)
    fot = e.get("fot") or {}
    options = {"medianera": _f(fot.get("fot_medianera")), "semi libre": _f(fot.get("fot_semi_libre")),
               "perímetro libre": _f(fot.get("fot_perim_libre"))}
    r["fot_medianera"], r["fot_semi_libre"], r["fot_perim_libre"] = options["medianera"], options["semi libre"], \
        options["perímetro libre"]
    # the envelope is built between party walls, so its plusvalía uses the FOT entre medianeras
    r["tipo_fot"], r["fot_usado"] = ("medianera", options["medianera"]) if options["medianera"] else \
        max(options.items(), key=lambda t: t[1])
    pv = e.get("plusvalia") or {}
    r["distrito_cpu"] = pv.get("distrito_cpu") or ""
    unit_h, limit_h = unit_height(e), _f(e.get("altura_max_plano_limite"))
    r["altura_unidad_m"], r["altura_max_m"] = unit_h or limit_h or None, limit_h or unit_h or None
    cat = e.get("catalogacion") or {}
    r["proteccion"] = (cat.get("proteccion") or "").upper() if (cat.get("proteccion") or "").upper() != "DESESTIMADO" else ""
    af = e.get("afectaciones") or {}
    r["afectaciones"] = ", ".join(x for x in ("ensanche", "apertura", "riesgo_hidrico", "lep", "ci_digital") if af.get(x))
    flags = []
    if r["proteccion"]:
        flags.append(f"catalogado ({r['proteccion']})")
    if (cat.get("ley_3056") or "").upper() == "SI" and (cat.get("proteccion") or "").upper() != "DESESTIMADO":
        flags.append("anterior_a_1941 (Ley 3056: consulta al CAAP antes de demoler)")
    if any((d or {}).get("distrito_especifico") for d in e.get("distrito_especial") or []):
        flags.append("distrito_especial (APH / U / ARE: ver Ciudad 3D)")
    if af.get("ensanche") or af.get("apertura"):
        flags.append("afectacion_vial (ensanche/apertura)")
    if af.get("riesgo_hidrico"):
        flags.append("riesgo_hidrico")
    if e.get("tipica") and e.get("tipica") != "T":
        flags.append("manzana_atipica")
    if (e.get("parcelas_linderas") or {}).get("aph_linderas"):
        flags.append("lindero_APH")
    if e.get("cca") == "R-CCA":
        flags.append("receptora_CCA (puede superar el plano límite comprando capacidad constructiva, art. 10.1.4)")
    elif e.get("cca") == "E-CCA":
        flags.append("emisora_CCA (la obra nueva genera certificados vendibles, art. 10.1.3)")
    r["gran_predio"] = s >= k["sup_min_gran_predio"]
    # Buildable m2: the envelope of the Código Urbanístico. The footprint is Ciudad 3D's (L.O. to L.F.I.), scaled
    # to the listing's surface; the front is the catastro's when the parcel matches, else the one in the text.
    front = (r["frente_catastro_m"] if matched else None) or _f(r.get("frente_m")) or None
    plan_c3d = _f(e.get("sup_edificable_planta"))
    if group and group["tipo"] == "varias":        # several lots together: the sum of their footprints
        plan_total = sum(min(_f(ei.get("sup_edificable_planta")) or si, si) for _, ei, si in group["parcelas"])
        plan = s * min(plan_total / group["superficie"], 1.0)
        front = sum(_f(pi.get("frente")) for pi, _, _ in group["parcelas"]) or front
    elif plan_c3d and sup_cat:
        plan = s * min(plan_c3d / sup_cat, 1.0)
    elif front:
        plan = min(s, front * max(k["banda_minima_m"], k["fondo_tipico_m"]))
    else:
        plan = s
        r["alertas"].append("planta_sin_dato (se usó toda la superficie)")
    env = envelope(s, plan, unit_h, limit_h, front, k)
    r.update(pisos=env["pisos"], planta_edificable_m2=round(plan), eficiencia_planta=env["eficiencia"])
    m2 = env["m2"]
    if not m2:
        r["flags"] = "; ".join(flags)
        r["motivo_descarte"] = "parcela_sin_edificabilidad"
        return r.__setitem__("resultado", "gran_predio") if r["gran_predio"] else None
    uva, inc_uva = c3d.uva(), _f(pv.get("incidencia_uva"))
    r["uva_ars"], r["incidencia_ley6062_uva"] = uva, inc_uva or None
    frac = k["plusvalia_fraccion_m2"]
    if r["fot_usado"]:
        r["m2_sin_plusvalia"] = round(r["fot_usado"] * s / frac)
        plus_uva = max(0.0, frac * m2 - r["fot_usado"] * s) * inc_uva * _f(pv.get("alicuota"))
    else:
        plus_uva = 0.0
        r["alertas"].append("sin_fot (plusvalía no calculada: verificar en Ciudad 3D)")

    def usd(uvas):
        return uvas * uva / mep if uva and mep else None
    r["m2_construibles"], r["incidencia_usd_m2"] = round(m2), round(price / m2, 1)
    r["plusvalia_uva"] = round(plus_uva)
    r["plusvalia_usd"] = round(usd(plus_uva)) if usd(plus_uva) is not None else None
    if r["plusvalia_usd"] is not None or not plus_uva:
        r["incidencia_total_usd_m2"] = round((price + (r["plusvalia_usd"] or 0)) / m2, 1)
    if inc_uva and usd(inc_uva):
        r["incidencia_referencia_usd_m2"] = round(usd(inc_uva), 1)
    total = r.get("incidencia_total_usd_m2") or r["incidencia_usd_m2"]
    if r.get("incidencia_total_usd_m2") is None:
        r["alertas"].append("sin_plusvalia (UVA o dólar no disponibles: incidencia sin el derecho de desarrollo urbano)")
    ref = r.get("incidencia_referencia_usd_m2")
    r["ratio_incidencia"] = round(total / ref, 2) if ref else None
    r["flags"] = "; ".join(flags)
    if r["proteccion"] in BLOCKING:
        r["motivo_descarte"] = f"edificio_catalogado ({r['proteccion']})"
    elif ref is None:
        r["motivo_descarte"] = "sin_incidencia_de_referencia"
    elif m2 <= k["m2_construibles_min"]:
        r["motivo_descarte"] = "m2_insuficientes"
    elif r["ratio_incidencia"] <= k["ratio_oportunidad"]:
        r["resultado"], r["via"] = ("casi", "multifamiliar (catalogado cautelar)") if r["proteccion"] in CAUTION \
            else ("oportunidad", "multifamiliar")
    elif r["ratio_incidencia"] <= k["ratio_casi"]:
        r["resultado"], r["via"] = "casi", "multifamiliar"
    else:
        r["motivo_descarte"] = "incidencia_alta"
    # Gonzalo, 20/11/2026: without a reliable parcel, or in a special district with no FOT (own rules), at most casi
    special = any((d or {}).get("distrito_especifico") for d in e.get("distrito_especial") or []) or \
        bool(SPECIAL.match(r["distrito_cpu"] or ""))
    # CABA errors #1, #2, #5, #6 (23/11/2026): with up to 6 neighbours, some sum of 2 or 3 parcels falls within ±5%
    # of almost any inflated surface; "varias" only counts when the listing says it sells several lots
    loose = bool(group) and group["tipo"] == "varias" and \
        not SEVERAL_LOTS.search(f"{r.get('titulo') or ''} || {r.get('descripcion') or ''}")
    if loose:
        r["alertas"].append("suma_de_parcelas_sin_mencion (el aviso no dice que sean varios lotes: la superficie "
                            "puede ser construible o cubierta; como mucho casi)")
    doubt = "parcela sin emparejar" if not matched else \
        "suma de parcelas sin mención de varios lotes" if loose else \
        f"distrito especial {r['distrito_cpu']} sin FOT: reglas propias" if special and not r["fot_usado"] else ""
    if doubt and r["resultado"] == "oportunidad":
        r["resultado"], r["via"] = "casi", f"multifamiliar ({doubt})"
    if special and not r["fot_usado"]:
        r["flags"] = "; ".join(x for x in (r["flags"], f"distrito_especial_sin_fot ({r['distrito_cpu']}: verificar sus reglas)") if x)
    if r["resultado"] == "descartado" and r["gran_predio"] and not r["proteccion"] in BLOCKING:
        r["resultado"], r["via"], r["motivo_descarte"] = "gran_predio", "gran_predio", ""


def match_parcels(p: dict, e: dict, s: float, c3d: Ciudad3D, k: dict, front: float | None = None,
                  r: dict | None = None) -> dict | None:
    """The parcels of a listing whose surface doesn't match the pin's parcel (sample of 60 hits, 20/11/2026: 12%
    the pin fell on the next parcel, 43% several lots together). Neighbours: the side ones of Ciudad 3D and the
    previous/next of the catastro. Within tolerancia_superficie of the listing's surface, in this order:
      vecina   one neighbour alone (the pin was misplaced)
      varias   the pin's parcel + 1 or 2 neighbours (the closest total)
    With the listing's stated front, the matched parcels must have a similar total front (CABA errors #1, #2, #5,
    23/11/2026: inflated surfaces found casual sums of parcels with 3 to 5 times the front of the lot).
    -> {'tipo', 'parcelas': [(catastro, edificabilidad, superficie)], 'superficie'} or None."""
    tol = k["tolerancia_superficie"] * s
    sup0 = _f(p.get("superficie_total")) or _f(e.get("superficie_parcela"))
    smps = [*((e.get("parcelas_linderas") or {}).get("smp_linderas") or []), p.get("smp_anterior"), p.get("smp_siguiente")]
    seen = {p["smp"].upper()}
    neigh = []
    for smp in smps:
        if not smp or smp.upper() in seen:
            continue
        seen.add(smp.upper())
        if len(seen) > k.get("vecinas_max", 6) + 1:
            break
        q = c3d.parcel_by_smp(smp)
        if q and _f(q.get("superficie_total")) and (q.get("smp") or smp).upper() not in {x["smp"].upper() for x, _ in neigh}:
            neigh.append((q, _f(q["superficie_total"])))

    def front_ok(parcels):
        fronts = [_f(x.get("frente")) for x in parcels]
        if not front or not all(fronts):
            return True
        total = sum(fronts)
        return 0.6 * front <= total <= max(1.6 * front, front + 8)
    covered = [q for q, _ in neigh if r is not None and listed_covered(r, q, s, k)]
    if len(covered) == 1:                       # a neighbour on the listing's street whose covered m2 is the listing's
        q = covered[0]
        return {"tipo": "vecina", "parcelas": [(q, c3d.buildable(q["smp"]), _f(q["superficie_total"]))],
                "superficie": _f(q["superficie_total"]), "cubierta": True}
    single = [(abs(sq - s), q, sq) for q, sq in neigh if abs(sq - s) <= tol and front_ok([q])]
    if single:
        _, q, sq = min(single, key=lambda t: t[0])
        return {"tipo": "vecina", "parcelas": [(q, c3d.buildable(q["smp"]), sq)], "superficie": sq}
    combos = [((q,), sq) for q, sq in neigh] + \
        [((a, b), sa + sb) for i, (a, sa) in enumerate(neigh) for b, sb in neigh[i + 1:]]
    combos = [(abs(sup0 + extra - s), qs, sup0 + extra) for qs, extra in combos
              if abs(sup0 + extra - s) <= tol and front_ok([p, *qs])]
    if not combos:
        return None
    _, qs, total = min(combos, key=lambda t: t[0])
    parcels = [(p, e, sup0)] + [(q, c3d.buildable(q["smp"]), _f(q["superficie_total"])) for q in qs]
    return {"tipo": "varias", "parcelas": parcels, "superficie": total}


def unit_height(e: dict) -> float:
    """Height of the unit of edificabilidad over the L.O. (38, 31,2, 22,8, 17,2, 14,6, 12, 9 m)."""
    return max(map(_f, e.get("unidad_edificabilidad") or e.get("altura_max") or [0]), default=0.0)


def envelope(s: float, plan: float, unit_h: float, limit_h: float, front: float | None, k: dict) -> dict:
    """Buildable m2 of the Código Urbanístico envelope, between party walls (arts. 6.2, 6.3 and 6.4.3).

    floors     1 + floor((unit height - PB) / altura_piso_m): PB 3 m, or 2,60 m in the U.S.A.B. (14,6 m or less)
    set-backs  where the plano límite is above the unit height (C.A., C.M., U.S.A.A., U.S.A.M.): one floor 2 m
               shorter and one 8 m shorter (4 m if the lot only gives the 16 m minimum band)
    basamento  C.A. and C.M.: PB and 1st floor go on from the L.F.I. to the L.I.B. (only with a known front)
    efficiency patios and side urban space: 0,85 with a front up to 10 m, 0,75 wider
    """
    h = unit_h or limit_h
    if not h or not plan:
        return {"m2": 0.0, "pisos": "", "eficiencia": None}
    pb = k["pb_baja_m"] if h <= k["altura_max_usab_m"] + 1e-6 else k["pb_alta_m"]
    floors = 1 + math.floor((h - pb) / k["altura_piso_m"] + 1e-9) if h >= pb else 0
    eff = k["eficiencia_planta_sin_frente"] if not front else \
        k["eficiencia_planta_angosta"] if front <= k["frente_angosto_m"] else k["eficiencia_planta_ancha"]
    net = plan * eff
    m2, label = net * floors, f"PB+{floors - 1}"
    if limit_h and limit_h > h + 0.5:
        depth = plan / front if front else k["fondo_tipico_m"]
        back = k["retiro_2_banda_minima_m"] if depth <= k["banda_minima_m"] + 0.5 else k["retiro_2_m"]
        m2 += net * (max(0.0, depth - k["retiro_1_m"]) + max(0.0, depth - back)) / depth
        label += " + 2 retiros"
    if h >= k["altura_min_basamento_m"] and front:
        extra = min(max(0.0, s - plan), front * k["fondo_basamento_m"])
        if extra:
            m2 += extra * eff * 2
            label += " + basamento"
    return {"m2": m2, "pisos": label, "eficiencia": eff}


def extra_potential(r: dict, c3d: Ciudad3D, cfg: dict) -> None:
    """Flag a hit whose side neighbours allow more than the envelope: a neighbour taller than the unit
    (completamiento de tejido, art. 6.5.5; not in U.S.A.B. 0 nor in APH) or a neighbour in a taller unit
    (lot next to a corner of a taller street, art. 6.4.6). Doesn't change the m2: Gonzalo checks it by hand."""
    k = cfg["caba"]
    e = c3d.cache["smp"].get(r.get("smp")) or {}
    h = r.get("altura_unidad_m") or 0
    neighbours = (e.get("parcelas_linderas") or {}).get("smp_linderas") or []
    if not h or not neighbours:
        return
    can_complete = h > 9.0 + 1e-6 and "distrito_especial" not in (r.get("flags") or "")
    found = []
    for smp in neighbours:
        if c3d.asked + 2 > c3d.limit:
            r["alertas"].append("linderos_sin_consultar (tope de consultas)")
            break
        try:
            cat = c3d.parcel_by_smp(smp) or {}
            floors = int(_f(cat.get("pisos_sobre_rasante")))
            tall = k["pb_alta_m"] + floors * k["altura_piso_m"]       # catastro counts the floors above the PB
            if can_complete and floors and tall > h + k["completamiento_diferencia_m"]:
                found.append(f"lindero {smp} con PB+{floors} (~{tall:.0f} m; la unidad da {h:g} m)")
            other = unit_height(c3d.buildable(smp))
            if other > h + k["esquina_diferencia_m"]:
                found.append(f"lindero {smp} en una unidad de {other:g} m (esquina, art. 6.4.6)")
        except RuntimeError:
            r["alertas"].append(f"lindero {smp} sin consultar")
    if found:
        r["potencial_extra"] = "potencial extra, revisar por completamiento y esquina: " + "; ".join(found)
        r["flags"] = "; ".join(x for x in (r.get("flags"), r["potencial_extra"]) if x)


ADDRESS = re.compile(r"^\s*(.*?[A-Za-zÁÉÍÓÚÑáéíóúñ.].*?)\s+(?:al\s+|n[°º]\s*)?(\d{1,5})\b", re.I)


def _mark_generic_pins(rows: list[dict], min_listings: int) -> None:
    """A point shared by `min_listings` or more listings with different addresses is the portal's default pin
    (e.g. Congreso or the Obelisco for 'Capital Federal'), not the lot's position."""
    by_point = {}
    for r in rows:
        if r.get("lat") is not None and r.get("lon") is not None:
            by_point.setdefault((round(r["lat"], 5), round(r["lon"], 5)), []).append(r)
    for group in by_point.values():
        if len({(r.get("direccion") or "").strip().lower() for r in group}) >= min_listings:
            for r in group:
                r["pin_generico"] = True


def _far_from_barrio(rows: list[dict], km: float, min_listings: int = 5) -> dict[str, float]:
    """id -> km from the median pin of the listings of its barrio, for the pins farther than `km`.
    CABA error #1 (23/11/2026): a lot in Congreso with its pin on Av. Cabildo 2495, 8,5 km away."""
    by_barrio = {}
    for r in rows:
        if r.get("lat") is not None and r.get("lon") is not None and r.get("barrio"):
            by_barrio.setdefault(r["barrio"].strip().lower(), []).append(r)
    far = {}
    for group in by_barrio.values():
        if len(group) < min_listings:
            continue
        lats, lons = sorted(r["lat"] for r in group), sorted(r["lon"] for r in group)
        lat0, lon0 = lats[len(lats) // 2], lons[len(lons) // 2]
        for r in group:
            d = math.hypot((r["lat"] - lat0) * 111.0, (r["lon"] - lon0) * 92.0)
            if d > km:
                far[r["id"]] = d
    return far


def _demote_far_pins(rows: list[dict], far: dict[str, float]) -> None:
    """An opportunity whose pin is far from its barrio and whose catastro street isn't the listing's: at most casi."""
    for r in rows:
        if r["resultado"] != "oportunidad" or r["id"] not in far:
            continue
        mine = _street_tokens(re.sub(r"\d+", " ", r.get("direccion") or ""))
        theirs = _street_tokens(re.sub(r"\d+", " ", r.get("direccion_catastro") or ""))
        if mine and mine & theirs:
            continue                                 # a big barrio (Palermo): the address confirms the pin
        r["resultado"], r["via"] = "casi", "multifamiliar (pin lejos del barrio del aviso)"
        r["alertas"].append(f"pin_lejos_del_barrio ({far[r['id']]:.1f} km del centro de los avisos de "
                            f"{r['barrio']}; catastro: {r.get('direccion_catastro') or 'sin dato'}): como mucho casi")


def process(items_by_portal: dict, cfg: dict, health: list | None = None) -> list[dict]:
    c3d = Ciudad3D(cfg)
    rows, seen = [], set()
    for portal, items in items_by_portal.items():
        for item in items:
            r = normalize(MAPPERS[portal](item), cfg)
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            rows.append(r)
    share_surface(rows, cfg)                         # a lot corrected from one publication's text serves the others
    _mark_generic_pins(rows, cfg["caba"].get("pin_generico_min_avisos", 4))
    mep = None
    if any(not r["motivo_descarte"] for r in rows):
        mep = dolar_mep(cfg["normalizacion"])["venta"]
    broken = 0
    for i, r in enumerate(rows, 1):
        try:
            before = copy.deepcopy(r)
            evaluate(r, c3d, cfg, mep)
            # the neighbours are looked up only for the listings that would be a hit with the pin's parcel: matching
            # every unmatched listing would cost ~15.000 queries (20/11/2026)
            if r.get("smp") and not r.get("parcela_coincide") and r["resultado"] in ("oportunidad", "casi", "gran_predio"):
                r.clear()
                r.update(before)
                evaluate(r, c3d, cfg, mep, try_match=True)
        except Exception as e:                       # noqa: BLE001 - one odd listing must never stop the run
            broken += 1
            r["resultado"], r["motivo_descarte"] = "descartado", f"error_evaluacion ({type(e).__name__})"
            c3d.errors.append(f"aviso {r.get('id')}: {type(e).__name__}: {str(e)[:120]}")
        if i % 100 == 0:
            c3d.save()                               # a crash later doesn't lose the API answers
    _demote_far_pins(rows, _far_from_barrio(rows, cfg["caba"].get("pin_lejos_barrio_km", 2.5)))
    c3d.limit = cfg["caba"]["max_consultas_por_corrida"]     # the reserve, for the neighbours of the hits
    order = {"oportunidad": 0, "gran_predio": 1, "casi": 2}     # the reserve goes to the opportunities first
    for r in sorted((x for x in rows if x["resultado"] in order), key=lambda x: order[x["resultado"]]):
        try:
            extra_potential(r, c3d, cfg)
        except Exception as e:                       # noqa: BLE001 - a flag must never stop the run
            r["alertas"].append(f"linderos_sin_revisar ({type(e).__name__})")
    for r in rows:
        r["alertas"] = "; ".join(r["alertas"]) if isinstance(r["alertas"], list) else r["alertas"]
    c3d.save()
    if health is not None:
        health.append(c3d.health())
    return rows


# ---------------------------------------------------------------- outputs

def summary(n_raw: int, rows: list[dict], health: list[dict], cfg: dict) -> str:
    res = Counter(r["resultado"] for r in rows)
    why = Counter(r["motivo_descarte"].split(" (")[0] for r in rows if r["resultado"] == "descartado")
    lines = [f"[{'FALLA' if h['falla'] else 'ok'}] {h['portal']}: {h['avisos']} avisos, {h['paginas_ok']} páginas"
             + "".join(f"\n  ! {e}" for e in h["errores"]) + "".join(f"\n  · {w}" for w in h.get("avisos_menores") or [])
             for h in health]
    lines += [f"Filas crudas: {n_raw} | avisos distintos (sin repetidos): {len(rows)}",
              f"Oportunidades: {res['oportunidad']} | casi: {res['casi']} | grandes predios: {res['gran_predio']} | "
              f"descartados: {res['descartado']}", "Descartes por motivo:"]
    lines += [f"  {k:32} {v}" for k, v in why.most_common()]
    for kind in ("oportunidad", "casi", "gran_predio"):
        block = sorted((r for r in rows if r["resultado"] == kind), key=_order(cfg))
        lines.append(f"--- {kind.upper()} ({len(block)}) ---")
        lines += [_line(r) for r in block]
    return "\n".join(lines)


def _line(r: dict) -> str:
    rep = f" | x{r['cantidad_publicaciones']}" if r.get("cantidad_publicaciones", 1) > 1 else ""
    return (f"[{r['resultado'].upper()}] {r['titulo'][:55]} | {r['direccion']} | USD {r['precio_usd']:,.0f} | "
            f"{r['superficie_m2']:.0f} m2 | SMP {r.get('smp')} {r.get('distrito_cpu')} {r.get('altura_unidad_m')} m "
            f"{r.get('pisos')} -> {r.get('m2_construibles')} m2c | inc {r.get('incidencia_usd_m2')} + plusvalía "
            f"= {r.get('incidencia_total_usd_m2')} USD/m2c vs ref. {r.get('incidencia_referencia_usd_m2')} "
            f"(ratio {r.get('ratio_incidencia')}) | {r['flag_confianza']}{rep} | {r.get('flags') or ''} | {r['url']}")


def _order(cfg: dict):
    """Expected profit per m2 first (rentabilidad.activo, Gonzalo 23/11/2026), else the incidence ratio."""
    if (cfg.get("rentabilidad") or {}).get("activo"):
        return rentabilidad.order_key
    return lambda r: r.get("ratio_incidencia") or 9


def _n(v, unit=""):
    return "" if v in (None, "") else (f"{v:,.0f}".replace(",", ".") + unit if isinstance(v, (int, float)) else str(v))


def map_links(r: dict) -> str:
    """Google Maps at the pin and the city's catastro map at the matched parcel (Gonzalo, 24/11/2026: he checks each
    hit's lot, covered area and photo in mapa.buenosaires.gob.ar)."""
    if not r.get("lat_usada"):
        return ""
    lat, lon = r["lat_usada"], r["lon_usada"]
    out = f"<br><a href='https://www.google.com/maps?q={lat:.6f},{lon:.6f}'>mapa</a>"
    q = {"lat": f"{lat:.6f}", "lng": f"{lon:.6f}", "zl": 18, "modo": "transporte"}
    if r.get("direccion_catastro"):
        q["dir"] = r["direccion_catastro"]
    return out + f" · <a href='https://mapa.buenosaires.gob.ar/informacion/?{html.escape(urlencode(q))}'>catastro</a>"


def render(rows: list[dict], health: list[dict], n_raw: int, cfg: dict) -> tuple[str, str]:
    from .notify import RENT_COLUMNS, _health, rent_note, test_prefix
    today = date.today().strftime("%d/%m/%Y")
    k = cfg["caba"]
    parts, failed = _health(health, None)
    cols = [("Inmueble", lambda r: f"<a href='{html.escape(r['url'])}'>{html.escape(r['titulo'][:60])}</a><br>"
                                   f"<span style='color:#666'>{html.escape(r['direccion'] or '')} · SMP {r.get('smp')}</span>"
                                   f"{map_links(r)}"),
            ("Precio USD", lambda r: _n(r["precio_usd"])), ("m² terreno", lambda r: _n(r["superficie_m2"])),
            ("Unidad / pisos", lambda r: f"{r.get('altura_unidad_m')} m · {r.get('pisos')}"),
            ("m² construibles", lambda r: _n(r.get("m2_construibles"))),
            ("Plusvalía USD", lambda r: _n(r.get("plusvalia_usd"))),
            ("Incidencia c/plusvalía", lambda r: _n(r.get("incidencia_total_usd_m2"))),
            ("Referencia Ley 6062", lambda r: _n(r.get("incidencia_referencia_usd_m2"))),
            ("Ratio", lambda r: r.get("ratio_incidencia")), ("Flags", lambda r: html.escape(r.get("flags") or ""))]
    profit = (cfg.get("rentabilidad") or {}).get("activo")
    if profit:                       # Gonzalo, 23/11/2026: profit per m2 right after the listing
        cols = cols[:1] + RENT_COLUMNS + cols[1:]
        parts.append(rent_note(cfg))

    def table(block):
        if not block:
            return "<p style='color:#666'>Ninguna.</p>"
        head = "".join(f"<th style='text-align:left;border-bottom:1px solid #ccc;padding:4px'>{c}</th>" for c, _ in cols)
        body = "".join("<tr>" + "".join(f"<td style='padding:4px;border-bottom:1px solid #eee'>{f(r)}</td>" for _, f in cols)
                       + "</tr>" for r in block)
        return f"<table style='border-collapse:collapse;font-size:13px'><tr>{head}</tr>{body}</table>"

    by = lambda kind: sorted((r for r in rows if r["resultado"] == kind), key=_order(cfg))  # noqa: E731
    opp, near, big = by("oportunidad"), by("casi"), by("gran_predio")
    parts += [f"<h2>Oportunidades multifamiliar ({len(opp)})</h2>",
              f"<p style='color:#666'>m² construibles &gt; {k['m2_construibles_min']} e incidencia con plusvalía ≤ "
              f"{k['ratio_oportunidad']:g} × la incidencia de la Ley 6062 del distrito.</p>", table(opp),
              f"<h2>Casi-oportunidades ({len(near)})</h2>", table(near),
              f"<h2>Grandes predios (≥ {k['sup_min_gran_predio']} m², sin filtro de precio) ({len(big)})</h2>", table(big)]
    res = Counter(r["resultado"] for r in rows)
    parts.append(f"<h2>Resumen de la corrida</h2><p>Avisos bajados: {n_raw} · distintos: {len(rows)} · "
                 f"descartados: {res['descartado']}</p>")
    n = len(opp)
    subject = test_prefix(cfg) + cfg["mail"]["asunto"].format(n=n, fecha=today)
    if failed:
        subject += " — ⚠ falla en " + ", ".join(h["portal"] for h in failed)
    return subject, "<div style='font:14px Arial'>" + "\n".join(parts) + "</div>"


def run_caba(items: dict, health: list, run_dir: Path, cfg: dict, args) -> None:
    rows = dedupe(process(items, cfg, health), cfg)
    rentabilidad.apply_all(rows, cfg)
    rows.sort(key=lambda r: ({"oportunidad": 0, "casi": 1, "gran_predio": 2}.get(r["resultado"], 3), _order(cfg)(r)))
    with open(run_dir / "resultado.csv", "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_raw = sum(len(v) for v in items.values())
    text = summary(n_raw, rows, health, cfg)
    (run_dir / "resumen.txt").write_text(text, encoding="utf-8")
    print(text)
    subject, body = render(rows, health, n_raw, cfg)
    (run_dir / "mail.html").write_text(f"<h1>{html.escape(subject)}</h1>{body}", encoding="utf-8")
    if not args.sin_mail:
        from .notify import _send
        _send(subject, body)
