"""Turn raw portal items into the common schema and drop what can't be evaluated.

Common schema (shared by every portal):
    id, portal, url, titulo, tipologia, precio_usd, moneda_original, superficie_m2,
    superficie_dudosa, direccion, barrio, lat, lon, fecha_publicacion
plus traceability fields: precio_original, cotizacion_usada, superficie_fuente,
superficie_total_m2, superficie_cubierta_m2, frente_m, fondo_m, frente_fuente, descripcion, alertas,
motivo_descarte.
"""

import html
import json
import re
import time
from datetime import date
from pathlib import Path

import requests

from .config import path

FIELDS = ["id", "portal", "url", "titulo", "tipologia", "precio_usd", "moneda_original",
          "superficie_m2", "superficie_dudosa", "direccion", "barrio", "lat", "lon",
          "fecha_publicacion"]
PESOS = ("ARS", "$", "PESOS")
_quotes: dict[str, dict] = {}             # the dollar rate, asked at most once per run


def dolar_mep(ncfg: dict) -> dict:
    """Dólar MEP for the listings in pesos, asked at most once per run: {'venta', 'fecha', 'error'}.
    Each good answer of the API is saved on disk. If the API doesn't answer, 'error' says why and 'venta' is the
    saved rate, or None if there is none from the last dolar_respaldo_max_dias days."""
    url = ncfg["dolar_api"]
    if url in _quotes:
        return _quotes[url]
    backup = path(ncfg["dolar_respaldo"])
    venta, error = _api_rate(ncfg)
    if venta:
        quote = {"venta": venta, "fecha": date.today().isoformat()}
        try:
            backup.write_text(json.dumps(quote), encoding="utf-8")
        except OSError as e:
            print(f"No se pudo guardar la cotización del dólar en {backup}: {e}")
    else:
        quote = _saved_quote(backup, ncfg["dolar_respaldo_max_dias"]) or {"venta": None, "fecha": ""}
        print(f"Dólar MEP: la API no respondió; cotización guardada: {quote['fecha'] or 'ninguna reciente'}")
    _quotes[url] = {**quote, "error": error}
    return _quotes[url]


def _api_rate(ncfg: dict) -> tuple[float | None, str]:
    """(rate, '') from the API, retried with a growing pause; (None, last error) if it never answers."""
    tries = ncfg["dolar_intentos"]
    for attempt in range(1, tries + 1):
        try:
            r = requests.get(ncfg["dolar_api"], timeout=30)
            r.raise_for_status()
            venta = float(r.json()["venta"])
            if venta > 0:
                return venta, ""
            error = f"venta={venta:g}"
        except Exception as e:                    # noqa: BLE001 - network (e.g. SSLError), HTTP or a bad answer
            error = f"HTTP {e.response.status_code}" if isinstance(e, requests.HTTPError) else type(e).__name__
        print(f"Dólar MEP: {error} (intento {attempt} de {tries})")
        if attempt < tries:
            time.sleep(ncfg["dolar_pausa_s"] * attempt)
    return None, error


def _saved_quote(backup: Path, max_days: int) -> dict | None:
    """The last rate the API gave, if it is at most max_days old."""
    try:
        q = json.loads(backup.read_text(encoding="utf-8"))
        if (date.today() - date.fromisoformat(q["fecha"])).days <= max_days:
            return {"venta": float(q["venta"]), "fecha": q["fecha"]}
    except (OSError, ValueError, KeyError, TypeError):      # none saved yet, or unreadable
        pass
    return None


def dollar_health(rows: list[dict], cfg: dict) -> list[dict]:
    """The dollar API in the run's health, next to the portals, only if it failed: the mail shows it in red."""
    ncfg = cfg["normalizacion"]
    q = _quotes.get(ncfg["dolar_api"])
    if not q or not q["error"]:
        return []
    why = f"la API del dólar no respondió en {ncfg['dolar_intentos']} intentos ({q['error']})"
    if q["venta"]:
        rate = f"{q['venta']:,.0f}".replace(",", ".")
        why += (f": se usó la cotización guardada del {date.fromisoformat(q['fecha']):%d/%m/%Y} ({rate} ARS/USD) "
                "para los avisos en pesos")
    else:
        why += (f" y no hay cotización guardada de los últimos {ncfg['dolar_respaldo_max_dias']} días: "
                "se descartaron los avisos en pesos")
    n = sum(1 for r in rows if r.get("precio_original") and (r.get("moneda_original") or "").upper() in PESOS)
    return [{"portal": "dólar MEP", "paginas_ok": 0, "avisos": n, "errores": [why], "falla": True}]


def _num(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    m = re.search(r"\d[\d.,]*", str(v))
    if not m:
        return None
    s = m.group(0)
    if "," in s and "." in s:          # 1.234,5
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:                      # 1234,5
        s = s.replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", s):   # 1.234 (thousands)
        s = s.replace(".", "")
    return float(s)


def _get(d, *path):
    for k in path:
        if not isinstance(d, dict):
            return None
        d = d.get(k)
    return d


def _features(obj, out=None) -> dict:
    """Collect every {'label': ..., 'value': ...} block found anywhere in the item."""
    out = {} if out is None else out
    if isinstance(obj, dict):
        label = obj.get("label") or obj.get("name")
        if isinstance(label, str) and "value" in obj and not isinstance(obj["value"], (dict, list)):
            out.setdefault(label.strip().lower(), obj["value"])
        for v in obj.values():
            _features(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _features(v, out)
    return out


def _pick(feats: dict, patterns) -> float | None:
    for pat in patterns:
        for label, value in feats.items():
            if re.search(pat, label):
                n = _num(value)
                if n:
                    return n
    return None


# ---------------------------------------------------------------- lot front and depth from the listing text
# Zonaprop's text writes decimals with a space ("19, 48 metros", "21. 90 m de frente")
_NUM = r"(?<![\d.,])(\d{1,3}(?:[.,] ?\d{1,2})?)(?![\d]|[.,]\d)"
_UNIT = r"(?:\s*(?:metros|mtrs|mts|mt|ml|m)\b\.?)"
# "20 mts de frente", "25m. De Frente"; but "217 mts. Frente de 8,50": a dot not followed by "de" ends the phrase
_BEFORE = r"(?:" + _UNIT + r"\s*de\s+|(?:\s*(?:metros|mtrs|mts|mt|ml|m)\b)?\s*(?:lineales\s+)?(?:de\s+)?)"
_DIMS = re.compile(_NUM + _UNIT + r"?\s*(?:[x×*]|por)\s*" + _NUM + _UNIT + "?", re.I)
_FRONT = [re.compile(r"\bfrente\s*(?:de\s+|:\s*)?" + _NUM + _UNIT, re.I),     # "frente 20 m", "frente: 20 mts"
          re.compile(r"\bfrente\s*:\s*" + _NUM, re.I),                         # "Frente: 20"
          re.compile(_NUM + _BEFORE + r"frente\b", re.I)]
_DEPTH = [re.compile(r"\bfondo\s*(?:de\s+|:\s*)?" + _NUM + _UNIT, re.I),
          re.compile(r"\bfondo\s*:\s*" + _NUM, re.I),
          re.compile(_NUM + _BEFORE + r"fondo\b(?!\s*libre)", re.I)]
FRONT_RANGE, DEPTH_RANGE = (6, 400), (8, 1000)
DIMS_TOLERANCE = 0.35            # "a x b" counts only if a*b is within ±35% of the surface (not a pool or a room)
PARTIAL = 0.5                    # stated front x depth under half the surface: measures of one of several lots


def _dec(s: str) -> float | None:
    return _num(s.replace(" ", ""))


PAIR_GAP = 80                    # "20 m de frente por 45 de fondo": the depth comes right after the front


def _matches(patterns, text: str, lo: float, hi: float) -> list[tuple[int, float]]:
    """(position, value) of every stated measure, in text order; setbacks ("Retiros: frente 4 m") are skipped."""
    out = {}
    for pat in patterns:
        for m in pat.finditer(text):
            if "retiro" in text[max(0, m.start() - 25):m.start()].lower():
                continue
            v = _dec(m.group(1))
            if v and lo <= v <= hi:
                out.setdefault(m.start(), v)
    return sorted(out.items())


def front_depth(text: str, surface: float | None) -> tuple[float | None, float | None]:
    """Front and depth stated in the text: '12 x 40', '12,5 × 38', 'frente 20 m', '20 mts de frente', 'fondo 45'.
    A text may describe the building and the lot, or several lots: the pair that matches the surface wins."""
    fronts, depths = _matches(_FRONT, text, *FRONT_RANGE), _matches(_DEPTH, text, *DEPTH_RANGE)
    stated = [(pos, f, next((d for p, d in depths if pos <= p <= pos + PAIR_GAP), None)) for pos, f in fronts]
    dims = []
    for m in _DIMS.finditer(text):
        a, b = _dec(m.group(1)), _dec(m.group(2))
        if a and b and FRONT_RANGE[0] <= a <= FRONT_RANGE[1] and DEPTH_RANGE[0] <= b <= DEPTH_RANGE[1]:
            dims.append((m.start(), a, b))
    fits = lambda f, d: surface and abs(f * d - surface) <= DIMS_TOLERANCE * surface          # noqa: E731
    for _, f, d in sorted(stated + dims):
        if d and fits(f, d):
            return f, d
    if len({f for _, f, _ in stated}) > 1:
        return None, None                 # several lots or buildings described and none matches the surface
    if surface and any(d and not fits(f, d) for _, f, d in stated):
        return None, None                 # "9,14 m de frente x 51 m" of one of two parcels: part of the lot
    if stated:
        f = stated[0][1]
        return f, next((d for _, d in depths if not surface or fits(f, d)), None)
    if not surface and dims:
        return dims[0][1], dims[0][2]      # "a x b" room sizes are ruled out only by the surface
    return None, depths[0][1] if depths else None


# ---------------------------------------------------------------- listings that load the buildable m2 as the lot
# Gonzalo, 23/11/2026 (CABA errors #1-#7 in municipios/caba/REGISTRO_ERRORES.md): many listings put the buildable,
# sellable or "capacidad constructiva" m2 where the lot surface goes; the lot is in the text or in front x depth.
_BIG = r"(\d{1,3}(?:\. ?\d{3})+|\d{2,6})(?:, ?\d+)?"      # "1.700", "1. 116" (Zonaprop), "2056", "1200,50"
_M2 = r"\s*(?:m2|m²|mts2|mt2|mts\.?|metros(?:\s+cuadrados)?|m)\b"
_BUILT = r"(?:construibles?|vendibles?|edificables?|a\s+construir|de\s+construcci[oó]n|capacidad\s+constructiva|cap\.?\s*constr\.?)"
# the number of the buildable m2 is the one right next to the word: "1.700 metros cuadrados construibles",
# "Sup vendible 2056 mts", "capacidad constructiva 1200", "cap constr 1200" (not "lote 480 m2 ... 550 construibles")
_BUILT_NUM = [re.compile(_BIG + r"(?:" + _M2 + r")?\s*(?:totales\s+|cubiertos\s+)?" + _BUILT, re.I),
              re.compile(_BUILT + r"(?:\s+(?:de|total(?:es)?|estimada|aprox\.?|hasta))*\s*:?\s*" + _BIG, re.I),
              re.compile(r"(?:sup(?:erficie)?\.?\s+)" + _BUILT + r"\s*:?\s*" + _BIG, re.I)]
_LOT_STATED = [
    re.compile(r"\b(?:superficie|sup\.?)\s+(?:de(?:l)?\s+)?(?:la\s+)?(?:parcela|terreno|lote)\s*[:=]?\s*" + _BIG + _M2, re.I),
    re.compile(r"\b(?:lote|terreno)\s+(?:de\s+)?" + _BIG + _M2, re.I),
]
# several lots sold together: "2 lotes", "dos parcelas", "lotes linderos", "unificados" (not "tenemos más lotes")
SEVERAL_LOTS = re.compile(r"\b(?:dos|tres|cuatro|2|3|4|varios|ambos)\s+(?:lotes|terrenos|parcelas)\b"
                          r"|\blotes\s+(?:linderos|contiguos|unificad|juntos|en\s+block)|\bunificad[oa]s?\b"
                          r"|\bparcelas\s+(?:linderas|contiguas|unificad)|lotes?\s+(?:n[°ºo]?\.?\s*)?\d+\s+y\s+\d+"   # "isidrolote N° 11 y 12"
                          r"|\bpor\s+separado\b"
                          r"|\bse\s+venden\s+(?:en\s+)?(?:block|conjunto|juntos)\b|\ben\s+conjunto\b", re.I)   # not "edificio en block"
# "galpón de 562 M2 cubiertos sobre lote de 525", "354 m² cubiertos sobre lote propio" (CABA errors #9, #10)
_COVERED_NUM = re.compile(_BIG + r"(?:" + _M2 + r")?\s*(?:totales\s+)?cubiert", re.I)
SAME = 0.03                      # a number of the text "is" the listing's surface within ±3%
_PART = re.compile(r"descubiert|libre|parquizad|patio|jard[ií]n|verde", re.I)


def _big(s: str) -> float | None:
    return _num(s.replace(".", "").replace(" ", ""))


def clean_numbers(text: str) -> str:
    """Zonaprop's normalized text: "25oo M2" -> "2500 M2"."""
    return re.sub(r"(?<=\d)[oO]{2}\b", "00", text)


def _built_numbers(text: str) -> list[float]:
    """Numbers stated as buildable or sellable m2 ('1.700 m2 construibles', 'capacidad constructiva 1200')."""
    return [v for pat in _BUILT_NUM for m in pat.finditer(text) if (v := _big(m.group(1)))]


def lot_from_text(r: dict, surface: float, portal_front: float | None, portal_depth: float | None) -> tuple:
    """(lot m2, source) when the listing's surface is the buildable m2 and the real lot can be read, or
    (None, 'construible') when it is clearly the buildable m2 but no lot is stated, or (None, '')."""
    text = clean_numbers((r.get("titulo") or "") + " || " + (r.get("descripcion") or ""))  # "Lote || 1.500 m2" isn't "lote 1.500 m2"
    built = any(abs(v - surface) <= SAME * surface for v in _built_numbers(text))
    # the listing's surface is the covered area: the portal's covered m2 or "562 M2 cubiertos" in the text
    # (CABA errors #8-#10, Gonzalo 24/11/2026: "1400 m² tot. / 1400 m² cub." on a 7,50 x 30 lot)
    cov = r.get("superficie_cubierta_m2")
    covered = not built and (bool(cov and abs(cov - surface) <= SAME * surface)
                             or any(abs(_big(m.group(1)) - surface) <= SAME * surface for m in _COVERED_NUM.finditer(text)))
    larger = built or covered        # the surface is bigger than the lot: any smaller lot stated is the lot
    several = bool(SEVERAL_LOTS.search(text))
    # under half the surface; when the surface is the buildable or covered m2, anything smaller
    small = lambda v: v and 50 <= v < ((1 - SAME) if larger else PARTIAL) * surface            # noqa: E731
    note = " (la superficie del aviso es la cubierta)" if covered else ""
    # "Terreno de 250m2 aprox descubierto": the yard of a bigger property, not the lot
    stated = [v for pat in _LOT_STATED for m in pat.finditer(text) if (v := _big(m.group(1)))
              and not _PART.search(text[m.end():m.end() + 30])]
    if not covered and any(abs(v - surface) <= 0.1 * surface for v in stated):   # covered 562 on a 525 lot
        return None, ""                        # the text also states the listing's surface as the lot: it is right
    for v in stated:                           # "Superficie de parcela: 212m2", "LOTE 110 mts"
        if small(v) and (larger or not several):             # "2 lotes ... lote de 522 m2": one of them
            return v, "superficie del lote en el texto" + note
    if portal_front and portal_depth and small(portal_front * portal_depth) and (larger or not several):
        return portal_front * portal_depth, "frente x largo del aviso" + note
    dims = [(m, _dec(m.group(1)), _dec(m.group(2))) for m in _DIMS.finditer(text)]
    dims = [(m, a, b) for m, a, b in dims
            if a and b and FRONT_RANGE[0] <= a <= FRONT_RANGE[1] and DEPTH_RANGE[0] <= b <= DEPTH_RANGE[1]]
    if covered and any(abs(a * b - surface) <= 0.1 * surface for _, a, b in dims):
        return None, ""                        # "lote de 17,32 x 68,60, total: 1188 m2": the surface is the lot
    for m, a, b in dims:                       # "LOTE 7.68 X 34.77", "8.67 x 39.97 mts"
        same_front = portal_front and abs(a - portal_front) <= 0.15 * portal_front
        # only covered: the measures must be the lot's ("lote de 25x10"), not a room's ("Play Room (6x9)")
        lot_word = bool(re.search(r"lote|terreno|parcela", text[max(0, m.start() - 30):m.start()], re.I))
        if small(a * b) and (built or (covered and lot_word) or (same_front and not several)):
            return a * b, "medidas del texto" + note
    return (None, "construible") if built else (None, "")


def _zonaprop_price(item):
    """Sale price; USD preferred when a listing shows more than one currency."""
    prices = [p for op in item.get("priceOperationTypes") or []
              if (_get(op, "operationType", "name") or "").lower() == "venta" for p in op.get("prices") or []]
    if not prices:
        return None, ""
    usd = [p for p in prices if (p.get("currency") or "").upper() in ("USD", "U$S")]
    p = usd[0] if usd else prices[0]
    return _num(p.get("amount")), (p.get("currency") or "").upper()


def from_zonaprop(item: dict) -> dict:
    """Map one posting from a Zonaprop results page (listStore.listPostings) to the common schema."""
    feats = _features({"m": item.get("mainFeatures"), "g": item.get("generalFeatures")})
    total = _pick(feats, [r"superficie total", r"^tot\.?$"])
    covered = _pick(feats, [r"superficie cubierta", r"^cub\.?$"])
    land = _pick(feats, [r"superficie (del |de )?terreno", r"^sup.*terreno"])
    front = _pick(feats, [r"frente del terreno"])
    depth = _pick(feats, [r"largo del terreno", r"fondo del terreno"])
    price, currency = _zonaprop_price(item)
    loc = item.get("postingLocation") or {}
    geo = _get(loc, "postingGeolocation", "geolocation") or {}
    kind = _get(item, "realEstateType", "name") or ""
    if item.get("postingType") and item["postingType"] != "PROPERTY":
        kind = f"emprendimiento ({kind})"
    return {
        "id": f"zonaprop-{item.get('postingId')}",
        "portal": "zonaprop",
        "url": "https://www.zonaprop.com.ar" + (item.get("url") or ""),
        "titulo": html.unescape(item.get("title") or item.get("generatedTitle") or ""),
        "tipologia_portal": kind,
        "precio_original": price,
        "moneda_original": currency,
        "superficie_terreno_m2": land,
        "superficie_total_m2": total,
        "superficie_cubierta_m2": covered,
        "frente_m": front,
        "fondo_m": depth,
        "direccion": _get(loc, "address", "name"),
        "direccion_visibilidad": _get(loc, "address", "visibility"),
        "barrio": _get(loc, "location", "name"),
        "lat": _num(geo.get("latitude")),
        "lon": _num(geo.get("longitude")),
        "fecha_publicacion": (item.get("modified_date") or "")[:10],
        "descripcion": item.get("descriptionNormalized") or "",
    }


def from_mercadolibre(item: dict) -> dict:
    """Map one Mercado Libre card (+ cached detail page, if it was opened) to the common schema."""
    det = item.get("detalle") or {}
    card = {}
    for t in item.get("atributos_card") or []:
        m = re.match(r"([\d.,]+)\s*m²\s*(totales|cubiertos)", t)
        if m:
            card[m.group(2)] = _num(m.group(1))
    parts = [p.strip() for p in (item.get("ubicacion") or "").split(",")]
    has_pin = det.get("lat") is not None
    return {
        "id": f"mercadolibre-{item.get('id')}",
        "portal": "mercadolibre",
        "url": (item.get("url") or "").split("#")[0],
        "titulo": item.get("titulo") or "",
        "tipologia_portal": item.get("tipologia_busqueda") or "",
        "precio_original": _num(item.get("precio")),
        "moneda_original": (item.get("moneda") or "").upper(),
        "superficie_terreno_m2": _num(det.get("superficie_terreno")),
        "superficie_total_m2": _num(det.get("superficie_total")) or card.get("totales"),
        "superficie_cubierta_m2": _num(det.get("superficie_cubierta")) or card.get("cubiertos"),
        "frente_m": None,
        "fondo_m": None,
        "direccion": det.get("direccion") or (parts[0] if parts else ""),
        "direccion_visibilidad": "EXACT" if has_pin else "SIN_PIN",
        "barrio": parts[1] if len(parts) > 1 else "",
        "lat": det.get("lat"),
        "lon": det.get("lon"),
        "fecha_publicacion": "",
        "descripcion": det.get("descripcion") or "",      # only in details cached since 27/09/2026
    }


def normalize(raw: dict, cfg: dict) -> dict:
    """Fill the common schema; sets motivo_descarte when the listing can't be evaluated."""
    ncfg = cfg["normalizacion"]
    r = dict(raw)
    r["alertas"] = []
    r["motivo_descarte"] = ""

    # lat/lon 0 or missing -> None
    if not r.get("lat") or not r.get("lon"):
        r["lat"] = r["lon"] = None
    elif r["lat"] > 0:            # some portals drop the sign
        r["lat"], r["lon"] = -abs(r["lat"]), -abs(r["lon"])

    # tipología
    tipo = ncfg["tipologias_incluidas"].get((r.get("tipologia_portal") or "").strip().lower())
    r["tipologia"] = tipo or (r.get("tipologia_portal") or "").strip().lower()
    for pat in ncfg["titulo_excluir"]:
        if re.search(pat, r.get("titulo") or "", re.I):
            r["motivo_descarte"] = f"tipologia_excluida_titulo ({pat})"
            break
    if not r["motivo_descarte"] and tipo is None:
        r["motivo_descarte"] = f"tipologia_excluida ({r['tipologia'] or 'sin dato'})"

    # precio
    price, cur = r.get("precio_original"), (r.get("moneda_original") or "").upper()
    r["cotizacion_usada"] = None
    if not price:
        r["precio_usd"] = None
        r["motivo_descarte"] = r["motivo_descarte"] or "sin_precio"
    elif cur in ("USD", "U$S", "US$", "DOLARES"):
        r["precio_usd"] = price
    elif cur in PESOS:
        quote = dolar_mep(ncfg)
        if quote["venta"]:
            r["cotizacion_usada"] = quote["venta"]
            r["precio_usd"] = round(price / quote["venta"])
            if quote["error"]:
                r["alertas"].append(f"cotizacion_guardada ({quote['fecha']})")
        else:
            r["precio_usd"] = None
            r["motivo_descarte"] = r["motivo_descarte"] or "sin_cotizacion_dolar"
    else:
        r["precio_usd"] = None
        r["motivo_descarte"] = r["motivo_descarte"] or f"moneda_desconocida ({cur})"
    if r["precio_usd"] is not None and r["precio_usd"] < ncfg["precio_usd_minimo_valido"]:
        r["motivo_descarte"] = r["motivo_descarte"] or f"precio_simbolico (USD {r['precio_usd']:.0f})"
    elif r["precio_usd"] and not (ncfg["precio_usd_sospechoso_min"] <= r["precio_usd"] <= ncfg["precio_usd_sospechoso_max"]):
        r["alertas"].append("precio_sospechoso")

    # superficie de terreno; frente y fondo del portal o, si no los da, del texto del aviso
    land, total = r.get("superficie_terreno_m2"), r.get("superficie_total_m2")
    front, depth = r.get("frente_m"), r.get("fondo_m")
    # a front or depth of 1.000 m or more in the portal's fields is a lost decimal comma ("Largo: 1730" = 17,30)
    front, depth = [v / 100 if v and v >= 1000 else v for v in (front, depth)]
    portal_front, portal_depth = front, depth
    if not front or not depth:
        f_txt, d_txt = front_depth(f"{r.get('titulo') or ''}\n{r.get('descripcion') or ''}", land or total)
        front, depth = front or f_txt, depth or d_txt
    r["frente_m"], r["fondo_m"] = front, depth
    fxl = front * depth if front and depth else None
    r["superficie_dudosa"] = False
    if land:
        r["superficie_m2"], r["superficie_fuente"] = land, "terreno"
    elif r["tipologia"] == "terreno" and total:
        r["superficie_m2"], r["superficie_fuente"] = total, "total"
    elif total:
        r["superficie_m2"], r["superficie_fuente"] = total, "total"
        r["superficie_dudosa"] = True
    elif fxl:
        r["superficie_m2"], r["superficie_fuente"] = fxl, "frente_x_fondo"
    else:
        r["superficie_m2"], r["superficie_fuente"] = None, ""
        r["motivo_descarte"] = r["motivo_descarte"] or "sin_superficie"
    if r["superficie_m2"]:
        lot, why = lot_from_text(r, r["superficie_m2"], portal_front, portal_depth)
        if lot:
            r["alertas"].append(f"superficie_corregida (el aviso dice {r['superficie_m2']:.0f} m2; {why}: {lot:.0f} m2)")
            r["superficie_aviso_m2"] = r["superficie_m2"]          # for the other publications of the same lot
            r["superficie_m2"], r["superficie_fuente"], r["superficie_dudosa"] = round(lot, 1), why, False
        elif why == "construible":
            r["motivo_descarte"] = r["motivo_descarte"] or                 f"superficie_construible (los {r['superficie_m2']:.0f} m2 del aviso son construibles y no da el lote)"
    if r["superficie_m2"] and fxl and abs(fxl - r["superficie_m2"]) / r["superficie_m2"] > 0.3:
        r["alertas"].append(f"superficie_no_coincide_con_frente_x_fondo ({fxl:.0f})")
    r["frente_fuente"] = "aviso" if front else "desconocido"
    if not front and depth and r["superficie_m2"]:
        # only the depth is stated: front = surface / depth
        calc = r["superficie_m2"] / depth
        if FRONT_RANGE[0] <= calc <= FRONT_RANGE[1]:
            r["frente_m"], r["frente_fuente"] = round(calc, 1), "calculado"
    cov = r.get("superficie_cubierta_m2")
    if r["superficie_m2"] and cov and r["tipologia"] == "casa" and cov > 2.5 * r["superficie_m2"]:
        r["alertas"].append("cubierta_mayor_que_terreno_x2.5")
    if r["superficie_m2"] and r.get("precio_usd"):
        usd_m2 = r["precio_usd"] / r["superficie_m2"]
        if usd_m2 < ncfg["precio_min_usd_m2_terreno"]:
            # e.g. a house loaded with 6.000.000 m2: a typo, not an opportunity
            r["motivo_descarte"] = r["motivo_descarte"] or f"superficie_implausible (USD {usd_m2:.1f}/m2 de terreno)"
    return r
