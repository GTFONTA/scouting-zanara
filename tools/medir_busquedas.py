"""How big are a municipio's searches? Opens ONLY the first page of each search (one request per search, with
the usual pause) and reports listings and pages announced by the portal. Run it before activating a municipio,
and never right before a weekly run (it adds traffic to the portals).

Usage:
    python tools/medir_busquedas.py caba
    python tools/medir_busquedas.py tigre --solo zonaprop
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src import fetch  # noqa: E402
from src.config import load_config  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("municipio")
    ap.add_argument("--solo", choices=["zonaprop", "mercadolibre"])
    args = ap.parse_args()
    cfg = load_config(args.municipio)
    total_pages = {}
    if args.solo in (None, "zonaprop"):
        p = cfg["portales"]["zonaprop"]
        crawler = fetch._Crawler(p, fetch.PortalHealth("zonaprop"))
        n = 0
        for url in p["start_urls"]:
            try:
                posts, paging = crawler.page(url)
                pages = int(paging.get("totalPages") or 1)
                n += pages
                slices = "" if pages <= p["max_paginas_por_busqueda"] else " (por tramos de precio)"
                print(f"zonaprop      {paging.get('total', '?'):>6} avisos {pages:>4} páginas{slices}  {url}")
            except (RuntimeError, ValueError) as e:
                print(f"zonaprop      ERROR {e}  {url}")
                if isinstance(e, fetch.BlockedError):
                    print("Bloqueo: se corta acá (no insistir).")
                    break
        total_pages["zonaprop"] = n
    if args.solo in (None, "mercadolibre"):
        p = cfg["portales"]["mercadolibre"]
        crawler = fetch._Crawler(p, fetch.PortalHealth("mercadolibre"))
        n = 0
        for s in p["busquedas"]:
            try:
                cards, _, total = fetch._ml_cards(crawler.html(s["url"]))
                pages = math.ceil(total / max(len(cards), 1)) if total else 1
                n += pages
                print(f"mercadolibre  {total:>6} avisos {pages:>4} páginas  {s['url']}")
            except (RuntimeError, ValueError) as e:
                print(f"mercadolibre  ERROR {e}  {s['url']}")
                if isinstance(e, fetch.BlockedError):
                    break
        total_pages["mercadolibre"] = n
    print("Páginas de resultados por corrida completa:", total_pages,
          "(+ fichas nuevas de Mercado Libre, solo la primera vez)")


if __name__ == "__main__":
    main()
