"""Fase C: incremental Zonaprop download, against a fake portal (no network)."""

import re
from datetime import date

import pytest

from src import fetch
from src.config import load_config

SEARCH = "https://www.zonaprop.com.ar/terrenos-venta-capital-federal-mas-200-m2.html"
URL_RE = re.compile(r"^(?P<base>.*?)(?:-mas-(?P<floor>\d+)-dolar)?(?P<order>-orden-precio-ascendente|"
                    r"-orden-publicado-descendente)?(?:-pagina-(?P<n>\d+))?\.html$")


class FakePortal:
    """Listings with distinct prices; 30 per page; challenges any page >= 10 like the real one."""

    def __init__(self, n):
        self.listings = [{"id": i, "price": 1000 * (i + 1), "date": i} for i in range(n)]
        self.block_after = None          # raise BlockedError after this many pages
        self.served = 0

    def page(self, crawler, url):
        self.served += 1
        if self.block_after is not None and self.served > self.block_after:
            raise fetch.BlockedError(f"{url}: HTTP 403 (bloqueo)")
        crawler.health.pages_ok += 1
        m = URL_RE.match(url)
        n = int(m["n"] or 1)
        assert n <= 9, "Zonaprop challenges page 10"
        rows = list(self.listings)
        if m["order"] == "-orden-publicado-descendente":
            rows.sort(key=lambda x: -x["date"])
        else:
            rows.sort(key=lambda x: x["price"])
            if m["floor"]:
                rows = [x for x in rows if x["price"] >= int(m["floor"])]
        pages = max(1, -(-len(rows) // 30))
        chunk = rows[(n - 1) * 30:n * 30]
        posts = [{"postingId": str(x["id"]),
                  "priceOperationTypes": [{"prices": [{"currency": "USD", "amount": x["price"]}]}]} for x in chunk]
        return posts, {"total": len(rows), "totalPages": pages}


@pytest.fixture
def setup(monkeypatch, tmp_path):
    cfg = load_config("caba")
    cfg["portales"]["zonaprop"]["start_urls"] = [SEARCH]
    cfg["incremental"]["estado"] = str(tmp_path / "estado{sufijo}.json.gz")
    portal = FakePortal(600)                                   # 20 pages: more than one run of 12 pages
    monkeypatch.setattr(fetch._Crawler, "page", lambda self, url: portal.page(self, url))
    cfg["incremental"]["paginas_por_corrida"] = 12
    return cfg, portal, tmp_path


def _run(cfg, tmp_path):
    items, health = fetch.fetch_zonaprop(cfg, tmp_path)
    return {i["postingId"] for i in items}, health


def test_seed_over_several_runs_then_news_and_removals(setup, monkeypatch):
    cfg, portal, tmp = setup
    ids, h = _run(cfg, tmp)                                    # run 1: one slice of 9 pages (270 listings)
    assert len(ids) == 270 and h.pages_ok == 9 and not h.errors
    assert any("primera descarga en curso" in w for w in h.warnings)
    ids, h = _run(cfg, tmp)                                    # run 2: second slice
    ids, h = _run(cfg, tmp)                                    # run 3: last slice -> cycle closed
    assert len(ids) == 600 and not h.errors and not any("primera descarga" in w for w in h.warnings)

    # a new listing (newest) and one sold
    portal.listings.append({"id": 9999, "price": 777_777, "date": 10_000})
    portal.listings = [x for x in portal.listings if x["id"] != 5]
    ids, h = _run(cfg, tmp)
    assert "9999" in ids                                       # found by the news pages
    assert h.pages_ok <= 12


def test_removed_listing_is_dropped_after_a_full_cycle(setup, monkeypatch):
    cfg, portal, tmp = setup
    days = iter(["2026-11-17", "2026-11-18", "2026-11-19", "2026-11-24", "2026-11-25", "2026-11-26", "2026-11-27"])

    class D(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(current[0])
    current = [next(days)]
    monkeypatch.setattr(fetch, "_date", D)
    for _ in range(3):                                         # seed: 3 runs
        _run(cfg, tmp)
        current[0] = next(days)
    portal.listings = [x for x in portal.listings if x["id"] != 5]
    for _ in range(4):                                         # next sweep (news pages eat part of the budget)
        ids, h = _run(cfg, tmp)
        current[0] = next(days, current[0])
    assert "5" not in ids and len(ids) == 599


def test_block_keeps_progress_and_is_a_failure(setup):
    cfg, portal, tmp = setup
    portal.block_after = 4
    ids, h = _run(cfg, tmp)
    assert h.failed and "se sigue en la próxima corrida" in h.errors[0]
    assert ids == set()                                       # the slice wasn't finished: nothing kept yet
    portal.block_after, portal.served = None, 0
    ids, h = _run(cfg, tmp)
    assert len(ids) == 270 and not h.errors


def test_san_isidro_stays_on_full_download():
    assert load_config()["incremental"]["activo"] is False
