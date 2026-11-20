"""Weekly run: fetch -> normalize -> locate -> evaluate -> dedupe -> Sheet -> mail.

    python -m src.main                              # full run (what the scheduled task executes)
    python -m src.main --reusar runs/2026-09-26     # reprocess a previous download, no portal requests
    python -m src.main --sin-sheet --sin-mail       # local only: runs/<fecha>/resultado.csv + console
"""

import argparse
import csv
import json
import os
import re
import traceback
from collections import Counter
from datetime import datetime
from pathlib import Path

from . import comparables, fetch
from .catastro import Catastro
from .config import DEFAULT_MUNICIPIO, ROOT, load_config, path
from .dedupe import dedupe, share_front
from .evaluate import address_unknown, evaluate, front_matters, lot_product, sections
from .flags import flags
from .locate import Locator
from .normalize import FIELDS, dollar_health, from_mercadolibre, from_zonaprop, normalize

COLUMNS = FIELDS + [
    "resultado", "via", "motivo_descarte", "alertas", "flags", "cantidad_publicaciones", "otros_links", "ids_duplicados",
    "precio_original", "cotizacion_usada",
    "superficie_fuente", "superficie_terreno_m2", "superficie_total_m2", "superficie_cubierta_m2",
    "frente_m", "fondo_m", "frente_fuente", "frente_catastro_m", "superficie_catastro_m2", "partidas_catastro",
    "flag_confianza", "lat_usada", "lon_usada", "barrio_usado", "localidad",
    "zona", "fot_zona", "distancia_borde_m", "zonas_cercanas", "zonas_candidatas", "distancia_zona_c_o_i_m",
    "zona_fot_usado", "fot_usado", "fot_fuente", "fot_efectivo", "limite_fot", "m2_construibles", "incidencia_usd_m2",
    # Fase 4 (productos.activo): units per product in the most favorable nearby zone
    "zona_unidades", "relevancia", "mejor_producto", "lotes_frente_propio", "lotes_calle_interna", "agrupadas_calle",
    "agrupadas_acceso_comun", "multifamiliar_unidades", "ue_unidades", "unidades_por_derecho",
    "unidades_con_aprobacion", "usd_por_unidad_derecho", "usd_por_unidad_aprobacion", "unidades_loteo",
    "usd_por_unidad_loteo", "mediana_usd_m2_lote", "comparables_n", "comparables", "valor_lote_estimado",
    "ratio_compra_reventa",
    "requiere_cloaca", "gran_predio",
    "tipologia_portal",
]
MAPPERS = {"zonaprop": from_zonaprop, "mercadolibre": from_mercadolibre}


def _use_cadastre(r: dict, cat: dict | None) -> None:
    """The lot's street front from ARBA: all its FRENTE sides, so a corner adds both streets. The text wins only
    if it states a longer front (the match may be a neighbouring parcel)."""
    if not cat:
        return
    r["frente_catastro_m"], r["superficie_catastro_m2"] = cat["frente"], cat["superficie"]
    r["partidas_catastro"] = " ".join(cat["partidas"])
    if not cat["frente"]:
        r["alertas"].append("catastro_sin_frente (posible predio interno)")
    elif cat["frente"] >= (r.get("frente_m") or 0):
        r["frente_m"], r["frente_fuente"] = cat["frente"], "catastro"


def process(items_by_portal: dict[str, list[dict]], cfg: dict, comps_history: list[dict] | None = None,
            health: list[dict] | None = None) -> tuple[list[dict], list[dict]]:
    """Normalize, locate and evaluate every listing: (rows, this run's small-lot comparables).
    With productos.activo the cadastre's state is added to `health`; the dollar API's too, if it failed."""
    z, c, p = cfg["zonificacion"], cfg["criterio"], cfg["productos"]
    locator = Locator(cfg)
    cadastre = Catastro(cfg) if p["activo"] else None
    normalized, seen = [], set()
    for portal, items in items_by_portal.items():
        for item in items:
            r = normalize(MAPPERS[portal](item), cfg)
            if r["id"] in seen:                      # same posting found by two searches
                continue
            seen.add(r["id"])
            normalized.append(r)
    comps, medians = [], {}
    if p["activo"]:                                  # small lots, before the surface prefilter drops them
        comps = comparables.collect(normalized, locator, cfg)
        medians = comparables.medians(comparables.merge(comps_history or [], comps, cfg), cfg)
        share_front(normalized, cfg)
    for r in normalized:
        sup, price = r.get("superficie_m2"), r.get("precio_usd")
        if not r["motivo_descarte"] and sup < z["superficie_min_prefiltro"]:
            r["motivo_descarte"] = "superficie_menor_prefiltro"
        big = p["activo"] and not r["motivo_descarte"] and sup >= p["sup_min_gran_predio"]   # reported at any price
        if not r["motivo_descarte"] and r.get("lat") is None and not big and \
                price / (sup * z["fot_max"]) >= c["incidencia_casi_max_usd"]:
            # no pin and not a hit even in the best zone of the partido: skip geocoding
            r["motivo_descarte"] = "incidencia_alta_aun_con_fot_max"
        if not r["motivo_descarte"]:
            loc = locator.locate(r)
            r["motivo_descarte"] = loc.pop("motivo_descarte", "")
            r.update(loc)
        if p["activo"] and not r["motivo_descarte"]:
            r["localidad"] = locator.localidad(r)
            if r.get("flag_confianza") in ("exacta", "geocodificada") and front_matters(r, locator.normativa, p):
                _use_cadastre(r, cadastre.lookup(r))
    if p["activo"]:          # the parcel found for one publication of a lot serves the others (other pins)
        share_front([r for r in normalized if not r["motivo_descarte"]], cfg)
    rows = []
    for r in normalized:
        ev = evaluate(r, cfg, locator.normativa, medians)
        r["motivo_descarte"] = r["motivo_descarte"] or ev.pop("motivo_descarte", "")
        ev.pop("motivo_descarte", None)
        r.update(ev)
        if p["activo"] and r.get("zonas_candidatas"):
            r["flags"] = "; ".join(flags(r, locator.normativa, cfg))
        r["alertas"] = "; ".join(r["alertas"])
        rows.append(r)
    if cadastre:
        cadastre.save()
        if health is not None:
            health.append(cadastre.health())
    if health is not None:
        health.extend(dollar_health(rows, cfg))
    return rows, comps


def summary(n_raw: int, rows: list[dict], health: list[dict], cfg: dict | None = None) -> str:
    res = Counter(r["resultado"] for r in rows)
    why = Counter(r["motivo_descarte"].split(" (")[0] for r in rows if r["resultado"] == "descartado")
    conf = Counter(r.get("flag_confianza") or "-" for r in rows if r.get("fot_usado") is not None)
    lines = []
    for h in health:
        state = "FALLA" if h["falla"] else "ok"
        lines.append(f"[{state}] {h['portal']}: {h['avisos']} avisos, {h['paginas_ok']} páginas"
                     + "".join(f"\n  ! {e}" for e in h["errores"])
                     + "".join(f"\n  · {w}" for w in h.get("avisos_menores") or []))
    lines += [f"Filas crudas: {n_raw} | avisos distintos (sin repetidos): {len(rows)}",
              f"Oportunidades: {res['oportunidad']} | casi: {res['casi']} | "
              + (f"grandes predios: {res['gran_predio']} | " if cfg and cfg["productos"]["activo"] else "")
              + f"descartados: {res['descartado']}",
              "Descartes por motivo:"]
    lines += [f"  {k:32} {v}" for k, v in why.most_common()]
    lines.append("Ubicación de los evaluados: " + ", ".join(f"{k}={v}" for k, v in conf.items()))
    if cfg and cfg["productos"]["activo"]:
        return "\n".join(lines + _summary_products(rows))

    def fmt(r):
        rep = f" | x{r['cantidad_publicaciones']}" if r.get("cantidad_publicaciones", 1) > 1 else ""
        return (f"[{r['resultado'].upper()}] {r['titulo'][:60]} | {r['direccion']} | USD {r['precio_usd']:,.0f} | "
                f"{r['superficie_m2']:.0f} m2 ({r['superficie_fuente']}) | {r['zona_fot_usado']} FOT {r['fot_usado']} "
                f"({r['fot_fuente']}) | {r['m2_construibles']} m2c | {r['incidencia_usd_m2']} USD/m2c | "
                f"{r['flag_confianza']}{rep} | {r['url']}")

    hits = [r for r in rows if r["resultado"] in ("oportunidad", "casi")]
    for kind in ("oportunidad", "casi"):
        lines += [fmt(r) for r in sorted((r for r in hits if r["resultado"] == kind and not address_unknown(r)),
                                         key=lambda r: r["incidencia_usd_m2"])]
    unknown = sorted((r for r in hits if address_unknown(r)), key=lambda r: r["incidencia_usd_m2"])
    if unknown:
        lines.append(f"--- SIN DIRECCIÓN — REVISAR ({len(unknown)}): el aviso no da la altura; "
                     "FOT = máximo de la calle/esquina o de la localidad ---")
        lines += [fmt(r) for r in unknown]
    return "\n".join(lines)


def _summary_products(rows: list[dict]) -> list[str]:
    evaluated = [r for r in rows if r.get("zonas_candidatas") and r.get("unidades_por_derecho") is not None]
    front = Counter(r.get("frente_fuente") or "desconocido" for r in evaluated)
    lines = [f"Frente del lote en los evaluados: catastro={front['catastro']}, aviso={front['aviso']}, "
             f"calculado={front['calculado']}, desconocido={front['desconocido']}"]

    def fmt(r):
        rep = f" | x{r['cantidad_publicaciones']}" if r.get("cantidad_publicaciones", 1) > 1 else ""
        frente = f"frente {r['frente_m']} m ({r['frente_fuente']})" if r.get("frente_m") else "frente ?"
        loteo = (f" | loteo {r['unidades_loteo']} u. ({lot_product(r)}, {r['zona_unidades']}) "
                 f"USD {r['usd_por_unidad_loteo']:,.0f}/u." if r.get("unidades_loteo") else "")
        ratio = f" ratio {r['ratio_compra_reventa']}" if r.get("ratio_compra_reventa") is not None else ""
        return (f"[{r['resultado'].upper()}: {r['via']}] {r['titulo'][:55]} | {r['direccion']} | "
                f"USD {r['precio_usd']:,.0f} | {r['superficie_m2']:.0f} m2 | {frente} | "
                f"{r['zona_fot_usado']} FOT {r['fot_usado']} -> {r['incidencia_usd_m2']} USD/m2c | "
                f"{r['unidades_por_derecho']} u. por derecho ({r['mejor_producto']}) / "
                f"{r['unidades_con_aprobacion']} con aprobación{loteo}{ratio} | {r['flag_confianza']}{rep} | "
                f"{r.get('flags') or ''} | {r['url']}")

    titles = {"multifamiliar": "OPORTUNIDADES MULTIFAMILIAR", "loteo_agrupadas": "OPORTUNIDADES LOTEO / AGRUPADAS",
              "gran_predio": "GRANDES PREDIOS (>= 3.000 m2, sin filtro de precio)", "casi": "CASI-OPORTUNIDADES",
              "sin_direccion": "SIN DIRECCIÓN — REVISAR (FOT y unidades de la zona más favorable de la calle o localidad)"}
    for key, block in sections(rows).items():
        lines.append(f"--- {titles[key]} ({len(block)}) ---")
        lines += [fmt(r) for r in block]
    return lines


def download(cfg: dict, run_dir: Path) -> tuple[dict, list[dict]]:
    """Each portal on its own: if one fails, the rest still run."""
    items, health = {}, []
    jobs = {"zonaprop": lambda: fetch.fetch_zonaprop(cfg, run_dir),
            "mercadolibre": lambda: fetch.fetch_mercadolibre(cfg, run_dir, path(cfg["portales"]["mercadolibre"]["cache"]))}
    for portal, job in jobs.items():
        if not cfg["portales"][portal].get("habilitado", True):
            continue
        try:
            found, h = job()
            items[portal] = found
            health.append(h.as_dict())
        except Exception as e:                            # noqa: BLE001 - a portal must never stop the run
            health.append({"portal": portal, "paginas_ok": 0, "avisos": 0, "falla": True,
                           "errores": [f"{type(e).__name__}: {e}"]})
    (run_dir / "salud.json").write_text(json.dumps(health, ensure_ascii=False, indent=1), encoding="utf-8")
    return items, health


def run(args) -> None:
    cfg = load_config(args.municipio)
    m = cfg["municipio"]
    if m["en_prueba"] and not os.environ.get("MAIL_TO_OVERRIDE"):
        # a municipio in its trial weeks: the mail only to mail.para, or to the first address of MAIL_TO
        to = cfg["mail"].get("para") or re.split(r"[,;]", os.environ.get("MAIL_TO", ""))[0].strip()
        if to:
            os.environ["MAIL_TO_OVERRIDE"] = to
    if args.reusar:
        run_dir = args.reusar if args.reusar.is_absolute() else ROOT / args.reusar
        items = {p: fetch.load_raw(run_dir, p) for p in MAPPERS if (run_dir / f"raw_{p}.json").exists()}
        salud = run_dir / "salud.json"
        health = json.loads(salud.read_text(encoding="utf-8")) if salud.exists() else []
    else:
        base = ROOT / "runs" if m["slug"] == DEFAULT_MUNICIPIO else ROOT / "runs" / m["slug"]
        run_dir = base / datetime.now().strftime("%Y-%m-%d_%H%M")      # never overwrite a previous run
        run_dir.mkdir(parents=True, exist_ok=True)
        items, health = download(cfg, run_dir)
    if not cfg["sheet"].get("id"):                       # municipio without its own Sheet yet
        args.sin_sheet = True
    if m["motor"] == "caba":
        from .motor_caba import run_caba
        return run_caba(items, health, run_dir, cfg, args)
    history = []
    if cfg["productos"]["activo"] and not args.sin_sheet:
        try:
            from .store import read_comparables
            history = read_comparables(cfg)
        except Exception as e:                            # noqa: BLE001 - this week's small lots are still used
            print(f"No se pudo leer el historial de comparables de la Sheet: {e}")
    processed, comps = process(items, cfg, history, health)
    rows = dedupe(processed, cfg)
    rows.sort(key=lambda r: ({"oportunidad": 0, "casi": 1, "gran_predio": 2}.get(r["resultado"], 3), address_unknown(r),
                             r.get("incidencia_usd_m2") or 1e9))
    out = run_dir / "resultado.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    n_raw = sum(len(v) for v in items.values())
    text = summary(n_raw, rows, health, cfg)
    (run_dir / "resumen.txt").write_text(text, encoding="utf-8")
    print(text)
    print(f"\n-> {out}")

    changes = None
    if not args.sin_sheet:
        try:
            from .store import update_sheet
            changes = update_sheet(rows, health, n_raw, cfg, comps and comparables.merge(history, comps, cfg))
        except Exception as e:                            # noqa: BLE001 - the mail must still go out
            print(f"No se pudo actualizar la Sheet: {e}")
            changes = {"error_sheet": f"{type(e).__name__}: {e}"}
    if not args.sin_mail:
        from .notify import send_report
        send_report(rows, health, changes, n_raw, cfg)


def _keep_awake() -> None:
    """Windows: don't let the PC go to sleep while the run is going (on 12/10/2026 it slept at 12:07 and the
    mail went out at night). Lasts until the process ends; no admin rights needed."""
    if os.name == "nt":
        try:
            import ctypes
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)   # CONTINUOUS | SYSTEM_REQUIRED
        except Exception as e:                            # noqa: BLE001 - never stop the run for this
            print(f"No se pudo impedir la suspensión de la PC: {e}")


def main():
    _keep_awake()
    ap = argparse.ArgumentParser()
    ap.add_argument("--reusar", type=Path, help="carpeta de una corrida previa (raw_<portal>.json)")
    ap.add_argument("--sin-sheet", action="store_true", help="no escribir la Google Sheet")
    ap.add_argument("--sin-mail", action="store_true", help="no mandar el mail")
    ap.add_argument("--mail-a", help="mandar el mail solo a esta dirección (pruebas)")
    ap.add_argument("--municipio", default=None, help="slug de municipios/<slug>/ (por defecto san_isidro)")
    args = ap.parse_args()
    if args.mail_a:
        os.environ["MAIL_TO_OVERRIDE"] = args.mail_a
    try:
        run(args)
    except Exception:                                     # noqa: BLE001 - always try to warn by mail
        tb = traceback.format_exc()
        print(tb)
        if not args.sin_mail:
            from .notify import send_error
            send_error(tb, load_config(args.municipio))
        raise


if __name__ == "__main__":
    main()
