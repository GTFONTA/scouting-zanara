"""Small scraper tests with saved/synthetic pages (no network)."""

import json

import pytest

from src import fetch

CFG = {"reintentos": 2, "reintentos_bloqueo": 1, "espera_bloqueo_s": 0, "pausa_reintento_s": 0,
       "pausa_entre_paginas_s": 0, "max_paginas_por_busqueda": 9, "cobertura_minima": 0.95, "espera_recupero_s": 0,
       "start_urls": []}


class FakeResponse:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text


class FakeSession:
    """Answers each GET with the next response of the list (and records the URLs)."""

    def __init__(self, responses):
        self.responses, self.urls = list(responses), []

    def get(self, url, **kw):
        self.urls.append(url)
        return self.responses.pop(0)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(fetch.time, "sleep", lambda s: None)


# ---------------------------------------------------------------- bloqueos

def test_403_then_403_is_blocked_error():
    s = FakeSession([FakeResponse(403), FakeResponse(403), FakeResponse(200, "ok")])
    with pytest.raises(fetch.BlockedError):
        fetch._get(s, "https://www.zonaprop.com.ar/x.html", CFG)
    assert len(s.urls) == 2                       # one retry only: never insist a third time


def test_403_then_ok_recovers():
    s = FakeSession([FakeResponse(403), FakeResponse(200, "<html>ok</html>")])
    assert fetch._get(s, "https://x/y.html", CFG) == "<html>ok</html>"


def test_challenge_page_counts_as_block():
    s = FakeSession([FakeResponse(200, "<title>Just a moment...</title>")] * 2)
    with pytest.raises(fetch.BlockedError):
        fetch._get(s, "https://x/y.html", CFG)


def test_server_error_is_not_a_block():
    s = FakeSession([FakeResponse(500)] * 3)
    with pytest.raises(RuntimeError) as e:
        fetch._get(s, "https://x/y.html", CFG)
    assert not isinstance(e.value, fetch.BlockedError)


# ---------------------------------------------------------------- Zonaprop

def _zp_page(ids, total, pages):
    posts = [{"postingId": i, "priceOperationTypes": [{"prices": [{"currency": "USD", "amount": 100000 + n}]}]}
             for n, i in enumerate(ids)]
    return f'<script>var x = {{"listPostings":{json.dumps(posts)},"paging":{{"total":{total},"totalPages":{pages}}}}}</script>'


def test_zonaprop_repeated_featured_is_minor_warning(monkeypatch, tmp_path):
    """02/11 and 09/11: the portal repeats 4 featured postings between pages; 54 rows arrive for a total of 54.
    That must be a minor note, not a failure ('50 de 54')."""
    page1 = _zp_page(list(range(1, 31)), 54, 2)
    page2 = _zp_page(list(range(31, 51)) + [1, 2, 3, 4], 54, 2)
    s = FakeSession([FakeResponse(200, page1), FakeResponse(200, page2)])
    monkeypatch.setattr(fetch.requests, "Session", lambda: s)
    cfg = {"portales": {"zonaprop": {**CFG, "start_urls": ["https://www.zonaprop.com.ar/edificios-venta-san-isidro.html"]}},
           "productos": {"activo": False}}
    items, health = fetch.fetch_zonaprop(cfg, tmp_path)
    assert health.errors == []
    assert not health.failed
    assert len(health.warnings) == 1 and "4 repetidos" in health.warnings[0]
    assert health.listings == 50
    assert s.urls[1].endswith("edificios-venta-san-isidro-pagina-2.html")


def test_zonaprop_blocked_search_retried_at_the_end(monkeypatch, tmp_path):
    ok = _zp_page([1, 2, 3], 3, 1)
    s = FakeSession([FakeResponse(403), FakeResponse(403),            # search A blocked (1 retry)
                     FakeResponse(200, ok),                            # search B fine
                     FakeResponse(200, _zp_page([7, 8], 2, 1))])       # A again, at the end: recovered
    monkeypatch.setattr(fetch.requests, "Session", lambda: s)
    urls = ["https://www.zonaprop.com.ar/a.html", "https://www.zonaprop.com.ar/b.html"]
    cfg = {"portales": {"zonaprop": {**CFG, "start_urls": urls}}, "productos": {"activo": False}}
    items, health = fetch.fetch_zonaprop(cfg, tmp_path)
    assert health.errors == []
    assert any("recuperada al final" in w for w in health.warnings)
    assert health.listings == 5
    assert s.urls == [urls[0], urls[0], urls[1], urls[0]]


def test_zonaprop_unparseable_page_is_error():
    with pytest.raises(ValueError):
        fetch._zonaprop_page("<html>sin datos</html>")


# ---------------------------------------------------------------- Mercado Libre

def test_ml_sponsored_card_never_opens_the_ad_url():
    meta = {"id": "MLA2255369417",
            "url": "https://click1.mercadolibre.com.ar/brand_ads/clicks/MLA/count?a=66%2FZW06"}
    assert fetch._ml_url(meta) == "https://articulo.mercadolibre.com.ar/MLA-2255369417"


def test_ml_sponsored_card_with_scheme_twice():
    meta = {"id": "MLA2255369417", "url": "https://https://click1.mercadolibre.com.ar/brand_ads/clicks/MLA/count?a=1"}
    assert fetch._ml_url(meta) == "https://articulo.mercadolibre.com.ar/MLA-2255369417"


def test_ml_normal_card_keeps_its_url():
    meta = {"id": "MLA1878128015", "url": "inmueble.mercadolibre.com.ar/MLA-1878128015-galpon-a-la-venta-en-beccar-_JM"}
    assert fetch._ml_url(meta) == "https://inmueble.mercadolibre.com.ar/MLA-1878128015-galpon-a-la-venta-en-beccar-_JM"


def test_ml_cards_parse_and_dedupe():
    card = {"unique_id": "u", "metadata": {"id": "MLA1", "url": "terreno.mercadolibre.com.ar/MLA-1-x-_JM"},
            "components": [{"type": "title", "title": {"text": "Lote"}},
                           {"type": "price", "price": {"current_price": {"value": 250000, "currency": "USD"}}},
                           {"type": "attributes_list", "attributes_list": {"texts": ["1.200 m² totales"]}}]}
    blob = json.dumps(card)[1:]                    # without the leading '{': the regex anchors on '"polycard":{"unique_id"'
    html = ('"results":[' + '{"polycard":{' + blob + '},' + '{"polycard":{' + blob + '}]'
            + ',"results_limit":42,"next_page":{"value":"2","url":"https:\\/\\/x\\/_Desde_49","show":true}')
    cards, nxt, total = fetch._ml_cards(html)
    assert len(cards) == 1 and cards[0]["precio"] == 250000
    assert fetch._card_total(cards[0]) == 1200
    assert nxt == "https://x/_Desde_49" and total == 42


def test_ml_detail_page():
    html = ('{"id":"Superficie total","text":"1.200 m²"}{"id":"Tipo de inmueble","text":"Terreno"}'
            '"location":{"latitude":"-34.47","longitude":"-58.51"}"item_address":"Rolón 2300"')
    d = fetch._ml_detail(html)
    assert d["superficie_total"] == "1.200 m²" and d["lat"] == -34.47 and d["direccion"] == "Rolón 2300"
