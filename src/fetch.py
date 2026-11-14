"""Own scraper: download the portals' search-result pages and keep the raw listings.

Zonaprop: each results page embeds ~30 listings as JSON (price, surface, address, lat/lon); no detail pages.
Mercado Libre: results pages give price and address only; total surface and lat/lon come from the detail
page, which is fetched once per listing and cached (data/cache_mercadolibre.json), so a normal week only
opens the new listings.
Traffic is kept low: one weekly run, sequential requests, a pause between requests.
"""

import json
import random
import re
import time
from pathlib import Path

import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-AR,es;q=0.9",
}
BLOCK_MARKERS = ("Just a moment", "cf-chl", "Attention Required", "captcha-delivery", "awswaf",
                 "challenge-container", "account-verification")


class PortalHealth:
    """What went wrong while scraping a portal; anything here is reported as a failure, not as 'no news'."""

    def __init__(self, portal: str):
        self.portal = portal
        self.pages_ok = 0
        self.errors: list[str] = []
        self.listings = 0
        self.warnings: list[str] = []      # minor issues: shown in resumen.txt, never a failure

    @property
    def failed(self) -> bool:
        return bool(self.errors) or self.listings == 0

    def as_dict(self) -> dict:
        return {"portal": self.portal, "paginas_ok": self.pages_ok, "avisos": self.listings,
                "errores": self.errors, "avisos_menores": self.warnings, "falla": self.failed}


class BlockedError(RuntimeError):
    """The portal answered with a 403/429 or an anti-bot challenge: don't insist, try again later."""


def _get(session: requests.Session, url: str, cfg: dict) -> str:
    """GET with retries. A 403/429 means the portal is rate-limiting us: wait long, then try again."""
    last, blocks = "", 0
    max_blocks = cfg.get("reintentos_bloqueo", cfg["reintentos"])
    for attempt in range(cfg["reintentos"] + 1):
        blocked = False
        try:
            r = session.get(url, headers=HEADERS, timeout=45)
            blocked = r.status_code in (403, 429) or any(m in r.text[:5000] for m in BLOCK_MARKERS)
            if r.status_code == 200 and not blocked:
                return r.text
            last = f"HTTP {r.status_code}" + (" (bloqueo)" if blocked else "")
        except requests.RequestException as e:
            last = type(e).__name__
        if blocked:
            blocks += 1
            if blocks > max_blocks:          # insisting is what makes the portal harden the block
                raise BlockedError(f"{url}: {last}")
        if attempt < cfg["reintentos"]:
            wait = cfg["espera_bloqueo_s"] if blocked else cfg["pausa_reintento_s"] * (attempt + 1)
            print(f"    {last} en {url.rsplit('/', 1)[-1]}; espero {wait}s y reintento")
            time.sleep(wait)
    raise (BlockedError if blocks else RuntimeError)(f"{url}: {last}")


def _zonaprop_page(html: str) -> tuple[list[dict], dict]:
    key = '"listPostings":'
    i = html.find(key)
    if i < 0:
        raise ValueError("no se encontró listPostings (¿cambió el formato de la página?)")
    decoder = json.JSONDecoder()
    postings = decoder.raw_decode(html[i + len(key):])[0]
    j = html.find('"paging":')
    paging = decoder.raw_decode(html[j + len('"paging":'):])[0] if j >= 0 else {}
    return postings, paging


def _page_url(url: str, n: int) -> str:
    return url if n == 1 else re.sub(r"\.html$", f"-pagina-{n}.html", url)


def _usd_price(post: dict) -> float | None:
    for op in post.get("priceOperationTypes") or []:
        for pr in op.get("prices") or []:
            if (pr.get("currency") or "").upper() == "USD" and pr.get("amount"):
                return float(pr["amount"])
    return None


class _Crawler:
    def __init__(self, cfg: dict, health: PortalHealth):
        self.cfg, self.health, self.session = cfg, health, requests.Session()

    def html(self, url: str) -> str:
        time.sleep(self.cfg["pausa_entre_paginas_s"] + random.uniform(0, self.cfg["pausa_entre_paginas_s"]))
        text = _get(self.session, url, self.cfg)
        self.health.pages_ok += 1
        return text

    def page(self, url: str) -> tuple[list[dict], dict]:
        """A Zonaprop results page: (postings, paging)."""
        return _zonaprop_page(self.html(url))

    def pages(self, url: str, first: tuple[list[dict], dict] | None = None) -> tuple[list[dict], dict]:
        """All pages of one search (only valid when it has <= max_paginas_por_busqueda pages)."""
        postings, paging = first or self.page(url)
        out = list(postings)
        for n in range(2, int(paging.get("totalPages") or 1) + 1):
            out.extend(self.page(_page_url(url, n))[0])
        return out, paging


def _search(crawler: _Crawler, url: str, max_pages: int) -> tuple[list[dict], int]:
    """Zonaprop challenges page >= 10 of any search, so each request list can only reach ~270 listings.
    Bigger searches are walked in price slices: sorted by price ascending, then 'price >= last price seen'."""
    first = crawler.page(url)
    total, total_pages = first[1].get("total", "?"), int(first[1].get("totalPages") or 1)
    print(f"  {url.rsplit('/', 1)[-1]}: {total} avisos en {total_pages} páginas")
    if total_pages <= max_pages:
        return crawler.pages(url, first)[0], int(first[1].get("total") or 0)
    items, floor, slice_no = [], None, 0
    base = url[:-len(".html")]
    while True:
        slice_no += 1
        s_url = base + (f"-mas-{int(floor)}-dolar" if floor else "") + "-orden-precio-ascendente.html"
        s_first = crawler.page(s_url)
        s_pages = int(s_first[1].get("totalPages") or 1)
        if s_pages <= max_pages:
            items.extend(crawler.pages(s_url, s_first)[0])
            print(f"    tramo {slice_no}: desde USD {floor or 0:,.0f}, {s_first[1].get('total')} avisos (último)")
            return items, int(first[1].get("total") or 0)
        chunk = list(s_first[0])
        for n in range(2, max_pages + 1):
            chunk.extend(crawler.page(_page_url(s_url, n))[0])
        items.extend(chunk)
        prices = [p for p in (_usd_price(c) for c in chunk) if p]
        new_floor = max(prices) if prices else None
        print(f"    tramo {slice_no}: desde USD {floor or 0:,.0f}, siguiente desde USD {new_floor or 0:,.0f}")
        if new_floor is None or (floor is not None and new_floor <= floor):
            raise ValueError(f"{url}: no se pudo avanzar por tramos de precio (tope USD {floor})")
        floor = new_floor


def fetch_zonaprop(cfg: dict, run_dir: Path) -> tuple[list[dict], PortalHealth]:
    p, prod = cfg["portales"]["zonaprop"], cfg["productos"]
    health = PortalHealth("zonaprop")
    crawler = _Crawler(p, health)
    items: list[dict] = []
    urls = list(p["start_urls"])
    if prod["activo"]:           # small lots (comparables for loteo), after the main searches
        urls += prod["comparables"].get("busquedas_zonaprop") or []

    def run_search(url: str) -> None:
        found, expected = _search(crawler, url, p["max_paginas_por_busqueda"])
        # The portal's total counts repeated postings (featured ones show up on more than one page), so the
        # coverage check uses the rows received; repeated postings are only a minor note.
        rows, unique = len(found), len({f.get("postingId") for f in found})
        if rows < p["cobertura_minima"] * expected:
            health.errors.append(f"{url}: se bajaron {rows} de {expected} avisos")
        elif unique < rows:
            health.warnings.append(f"{url}: {rows} avisos, {rows - unique} repetidos por el portal")
        for post in found:
            post["_search_url"] = url
        items.extend(found)

    deferred = []
    for url in urls:
        try:
            run_search(url)
        except BlockedError as e:
            print(f"    bloqueo en {url.rsplit('/', 1)[-1]}: se reintenta al final de la corrida")
            deferred.append((url, str(e)))
        except (RuntimeError, ValueError) as e:
            health.errors.append(str(e))
    if deferred:                 # on 19/10/2026 the block lifted ~40 min after the first 403
        wait = p.get("espera_recupero_s", 1500)
        print(f"  {len(deferred)} búsqueda(s) bloqueada(s): espero {wait}s y las reintento una vez")
        time.sleep(wait)
        for url, first_error in deferred:
            try:
                run_search(url)
                health.warnings.append(f"{url}: bloqueada al principio, recuperada al final ({first_error})")
            except (RuntimeError, ValueError) as e:
                health.errors.append(f"{e} (también falló el reintento al final de la corrida)")
    health.listings = len({i.get("postingId") for i in items})
    raw_path = run_dir / "raw_zonaprop.json"
    raw_path.write_text(json.dumps(items, ensure_ascii=False), encoding="utf-8")
    print(f"zonaprop: {len(items)} avisos en {health.pages_ok} páginas, {len(health.errors)} errores -> {raw_path}")
    return items, health


def load_raw(run_dir: Path, portal: str) -> list[dict]:
    """Reuse a previous download (python -m src.main --reusar runs/<fecha>)."""
    return json.loads((run_dir / f"raw_{portal}.json").read_text(encoding="utf-8"))


# ---------------------------------------------------------------- Mercado Libre

def _ml_url(meta: dict) -> str:
    """Listing URL from a results card. Sponsored cards carry an ad-click tracking URL (click1.../brand_ads/...)
    that may already include the scheme: never open it (it would count as an ad click); use the item's
    canonical URL instead, which Mercado Libre redirects to the listing."""
    url = re.sub(r"^(https?://)+", "", meta.get("url") or "")
    if not url or "click" in url.split("/", 1)[0] or "brand_ads" in url:
        m = re.match(r"([A-Z]{3})-?(\d+)$", meta.get("id") or "")
        return f"https://articulo.mercadolibre.com.ar/{m.group(1)}-{m.group(2)}" if m else ""
    return "https://" + url


def _ml_cards(html: str) -> tuple[list[dict], str | None, int]:
    """Listings of one Mercado Libre results page, the next page URL and the total announced."""
    decoder = json.JSONDecoder()
    cards, seen = [], set()
    for m in re.finditer(r'"polycard":\{"unique_id"', html):
        pc = decoder.raw_decode(html[m.start() + len('"polycard":'):])[0]
        meta = pc.get("metadata") or {}
        if meta.get("id") in seen:
            continue
        seen.add(meta.get("id"))
        comp = {c.get("type"): c.get(c.get("type")) or {} for c in pc.get("components") or []}
        price = (comp.get("price") or {}).get("current_price") or {}
        cards.append({
            "id": meta.get("id"),
            "url": _ml_url(meta),
            "titulo": (comp.get("title") or {}).get("text", ""),
            "headline": (comp.get("headline") or {}).get("text", ""),
            "precio": price.get("value"),
            "moneda": price.get("currency"),
            "atributos_card": (comp.get("attributes_list") or {}).get("texts") or [],
            "ubicacion": (comp.get("location") or {}).get("text", ""),
        })
    nxt = re.search(r'"next_page":\{"value":"[^"]*","url":"([^"]+)","show":true', html)
    total = re.search(r'"results_limit":(\d+)', html)
    if not cards and '"results"' not in html:
        raise ValueError("no se encontraron avisos (¿cambió el formato de la página?)")
    next_url = json.loads('"' + nxt.group(1) + '"') if nxt else None      # the URL comes JSON-escaped
    return cards, next_url, int(total.group(1)) if total else 0


def _ml_description(html: str) -> str:
    """Listing text (where the lot's front and depth usually are), cut to keep the cache small."""
    m = re.search(r'"description":(?=\{"component_id":"description")', html)
    if not m:
        return ""
    try:
        return (json.JSONDecoder().raw_decode(html[m.end():])[0].get("content") or "")[:3000]
    except ValueError:
        return ""


def _ml_detail(html: str) -> dict:
    attrs = dict(re.findall(r'\{"id":"([^"]+)","text":"([^"]+)"\}', html))
    loc = re.search(r'"location":\{"latitude":"?(-?[\d.]+)"?,"longitude":"?(-?[\d.]+)', html)
    addr = re.search(r'"item_address":"([^"]*)"', html)
    return {
        "descripcion": _ml_description(html),
        "superficie_total": attrs.get("Superficie total"),
        "superficie_cubierta": attrs.get("Superficie cubierta"),
        "superficie_terreno": attrs.get("Superficie de terreno") or attrs.get("Superficie del terreno"),
        "tipo_inmueble": attrs.get("Tipo de inmueble") or attrs.get("Tipo de casa") or "",
        "lat": float(loc.group(1)) if loc else None,
        "lon": float(loc.group(2)) if loc else None,
        "direccion": addr.group(1) if addr else "",
        "detalle_bajado": time.strftime("%Y-%m-%d"),
    }


def _card_total(card: dict) -> float | None:
    for t in card["atributos_card"]:
        m = re.match(r"([\d.,]+)\s*m²\s*totales", t)
        if m:
            return float(m.group(1).replace(".", "").replace(",", "."))
    return None


def fetch_mercadolibre(cfg: dict, run_dir: Path, cache_path: Path) -> tuple[list[dict], PortalHealth]:
    p = cfg["portales"]["mercadolibre"]
    z, c, prod = cfg["zonificacion"], cfg["criterio"], cfg["productos"]
    health = PortalHealth("mercadolibre")
    crawler = _Crawler(p, health)
    cache = json.loads(cache_path.read_text(encoding="utf-8")) if cache_path.exists() else {}
    items: dict[str, dict] = {}
    searches = list(p["busquedas"])
    if prod["activo"]:           # small lots: comparables for loteo (the card is enough, no detail page)
        searches += [{"url": u, "tipologia": "terreno"} for u in prod["comparables"]["busquedas_mercadolibre"]]
    for search in searches:
        url, expected, got = search["url"], 0, 0
        try:
            while url:
                cards, url, total = _ml_cards(crawler.html(url))
                expected = expected or total
                for card in cards:
                    card["tipologia_busqueda"] = search["tipologia"]
                    items.setdefault(card["id"], card)
                got += len(cards)
        except (RuntimeError, ValueError) as e:
            health.errors.append(f"{search['url']}: {e}")
            continue
        print(f"  {search['url'].split('.ar/', 1)[-1]}: {got} de {expected} avisos")
        if got < p["cobertura_minima"] * expected:
            health.errors.append(f"{search['url']}: se bajaron {got} de {expected} avisos")

    # detail pages: only listings not cached yet that could still be a hit
    todo = []
    for card in items.values():
        if card["id"] in cache:
            continue
        total = _card_total(card)
        price = card["precio"] or 0
        big = prod["activo"] and total is not None and total >= prod["sup_min_gran_predio"]   # reported at any price
        if total is not None and (total < z["superficie_min_prefiltro"]
                                  or (price >= c["incidencia_casi_max_usd"] * total * z["fot_max"] and not big)):
            continue                      # can't be a hit even with the best zone: no need for the detail
        todo.append(card)
    todo = todo[:p["max_detalles_por_corrida"]]
    print(f"  mercadolibre: {len(todo)} fichas nuevas para abrir ({len(cache)} ya en caché)")
    ficha_errors = 0
    for i, card in enumerate(todo, 1):
        try:
            cache[card["id"]] = _ml_detail(crawler.html(card["url"]))
        except BlockedError as e:            # blocked: stop opening detail pages, it is a real failure
            health.errors.append(f"bloqueo abriendo fichas: {e}")
            break
        except (RuntimeError, ValueError) as e:
            # one listing that doesn't open is not a failure of the portal (it's retried next week)
            ficha_errors += 1
            health.warnings.append(f"ficha {card['id']}: {str(e)[:200]}")
            if ficha_errors > p.get("errores_fichas_max", 10):
                health.errors.append(f"{ficha_errors} fichas con error: se corta")
                break
        if i % 50 == 0:
            cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
            print(f"    {i}/{len(todo)} fichas")
    cache_path.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")

    out = [{**card, "detalle": cache.get(card["id"])} for card in items.values()]
    health.listings = len(out)
    (run_dir / "raw_mercadolibre.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"mercadolibre: {len(out)} avisos, {health.pages_ok} páginas, {len(health.errors)} errores")
    return out, health
