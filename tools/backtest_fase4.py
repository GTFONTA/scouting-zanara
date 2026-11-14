"""Fase 4 backtest: the product evaluation (productos.activo) against the Fase 2 rule, on raw downloads that are
already on disk. No portal requests, no Sheet, no mail (only the dollar API and, for a few listings without a pin,
the geocoder).

Usage:
    python tools/backtest_fase4.py [runs/<carpeta> ...]        # default: the two downloads of 26/09/2026
    python tools/backtest_fase4.py --comparar-excel            # after tools/calculadora_excel.ps1
Output (runs/backtest_fase4/):
    resultado_fase2.csv, resultado_fase4.csv   every listing under each rule
    comparacion.csv       every hit of either rule: nuevo | desaparece | cambia | igual
    comparables.csv       small lots found in the downloads (the searches start at 400 m2: only 400-600 m2)
    sensibilidad.csv      loteo/agrupadas hits for other values of the two pending thresholds
    casos_excel.csv       10 cases for the Excel's 'Calculadora' (+ the system's result)
    comparacion_excel.csv system vs Excel, product by product (--comparar-excel)
    mail_fase4.html       the new mail, not sent
    resumen.txt
    backtest_fase4.xlsx   all of the above in one workbook, to review
"""

import argparse
import copy
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import load_config                                  # noqa: E402
from src.dedupe import dedupe                                       # noqa: E402
from src.comparables import PARTIDO                                 # noqa: E402
from src.evaluate import PRODUCTS, sections, units                  # noqa: E402
from src.locate import load_normativa                               # noqa: E402
from src.main import COLUMNS, process                               # noqa: E402
from src.notify import render_report                                # noqa: E402

OUT = ROOT / "runs" / "backtest_fase4"
DEFAULT_RUNS = ["runs/2026-09-26_parcial_bloqueada", "runs/2026-09-26"]
ID_KEY = {"zonaprop": "postingId", "mercadolibre": "id"}
SHOWN = ("oportunidad", "casi", "gran_predio")
# Excel 'Productos ZANARA' names of the rows that group two zones
EXCEL_ZONE = {"Rma2": "Rma2 / Rma2-AC", "Rma2-AC": "Rma2 / Rma2-AC", "Ca1": "Ca1 / Ca1-AC", "Ca1-AC": "Ca1 / Ca1-AC",
              "CR1-A": "CR1 – Sector A", "CR1-B": "CR1 – Sector B", "Ru": "Ru / AR", "AR": "Ru / AR"}
EXCEL_FIELDS = ["m2_fot", "lotes_frente_propio", "lotes_calle_interna", "agrupadas_calle", "agrupadas_acceso_comun",
                "multifamiliar_unidades", "ue_unidades", "unidades_por_derecho", "unidades_con_aprobacion",
                "usd_por_unidad_derecho", "usd_por_unidad_aprobacion"]


def load_items(run_dirs: list[str]) -> tuple[dict, list[dict]]:
    """Raw listings of several downloads, one per portal id (the latest download wins)."""
    items, health = {}, []
    for d in run_dirs:
        folder = ROOT / d
        for portal, key in ID_KEY.items():
            raw = folder / f"raw_{portal}.json"
            if raw.exists():
                for it in json.loads(raw.read_text(encoding="utf-8")):
                    items.setdefault(portal, {})[str(it.get(key))] = it
        if (folder / "salud.json").exists():
            health = json.loads((folder / "salud.json").read_text(encoding="utf-8"))
    return {p: list(v.values()) for p, v in items.items()}, health


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def ids(r: dict) -> set:
    return {r["id"], *(r.get("ids_duplicados") or "").split()}


def compare(old: list[dict], new: list[dict]) -> list[dict]:
    """Every listing that is a hit under either rule, matched through its duplicates' ids."""
    by_id = {}
    for r in new:
        for i in ids(r):
            by_id[i] = r
    out, seen = [], set()
    for o in old:
        n = next((by_id[i] for i in ids(o) if i in by_id), None)
        old_hit, new_hit = o["resultado"] in ("oportunidad", "casi"), n is not None and n["resultado"] in SHOWN
        if not (old_hit or new_hit):
            continue
        if n is not None:
            seen.add(n["id"])
        if old_hit and not new_hit:
            change = "desaparece"
        elif new_hit and not old_hit:
            change = "nuevo"
        else:
            change = "igual" if o["resultado"] == n["resultado"] else "cambia"
        out.append(_line(o, n, change))
    out += [_line(None, n, "nuevo") for n in new if n["resultado"] in SHOWN and n["id"] not in seen]
    order = {"nuevo": 0, "cambia": 1, "desaparece": 2, "igual": 3}
    return sorted(out, key=lambda x: (order[x["cambio"]], x["resultado_fase4"], x["titulo"]))


def _line(o: dict | None, n: dict | None, change: str) -> dict:
    r = n or o
    out = {"cambio": change, "titulo": r["titulo"][:70], "direccion": r.get("direccion"), "precio_usd": r["precio_usd"],
           "superficie_m2": r["superficie_m2"], "tipologia": r.get("tipologia"),
           "resultado_fase2": o["resultado"] if o else "", "zona_fase2": o.get("zona_fot_usado") if o else "",
           "fot_fase2": o.get("fot_usado") if o else "", "incidencia_fase2": o.get("incidencia_usd_m2") if o else ""}
    if n:
        out.update({k: n.get(k) for k in (
            "via", "mejor_producto", "zona_fot_usado", "fot_usado", "incidencia_usd_m2", "zona_unidades",
            "unidades_por_derecho", "unidades_con_aprobacion", "usd_por_unidad_derecho", "unidades_loteo",
            "usd_por_unidad_loteo", "valor_lote_estimado", "ratio_compra_reventa", "frente_m", "frente_fuente",
            "localidad", "flag_confianza", "flags")})
        out["resultado_fase4"] = n["resultado"]
        out["motivo_fase4"] = n.get("motivo_descarte") or ""
    else:
        out["resultado_fase4"] = "(no evaluado)"
    out["url"] = r["url"]
    return out


COMPARE_FIELDS = ["cambio", "resultado_fase2", "resultado_fase4", "via", "motivo_fase4", "titulo", "direccion",
                  "precio_usd", "superficie_m2", "tipologia", "frente_m", "frente_fuente", "zona_fase2", "fot_fase2",
                  "incidencia_fase2", "zona_fot_usado", "fot_usado", "incidencia_usd_m2", "zona_unidades",
                  "mejor_producto", "unidades_por_derecho", "unidades_con_aprobacion", "usd_por_unidad_derecho",
                  "unidades_loteo", "usd_por_unidad_loteo", "valor_lote_estimado", "ratio_compra_reventa", "localidad",
                  "flag_confianza", "flags", "url"]


def sensitivity(rows: list[dict], cfg: dict) -> list[dict]:
    """Loteo/agrupadas hits (by right) for other values of the ratio against a small lot."""
    cands = [r for r in rows if (r.get("unidades_loteo") or 0) >= cfg["productos"]["unidades_min"]
             and r.get("ratio_compra_reventa") is not None]
    out = []
    for ratio in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 1.0):
        hits = [r for r in cands if r["ratio_compra_reventa"] <= ratio]
        out.append({"umbral_ratio_loteo": ratio, "hits_loteo": len(hits),
                    "con_mediana_del_partido": sum(1 for r in hits if r["comparables"].startswith(PARTIDO)),
                    "frente_desconocido": sum(1 for r in hits if r.get("frente_fuente") == "desconocido")})
    return out


def pick_cases(rows: list[dict], normativa: dict, p: dict, n: int = 10) -> list[dict]:
    """Varied cases for the Excel check: different zones and products, known front first."""
    by_name = {row["zona"]: row for rs in normativa.values() for row in rs}
    pool = [r for r in rows if r["resultado"] in SHOWN and r.get("zona_unidades") in by_name]
    pool.sort(key=lambda r: (r.get("frente_fuente") == "desconocido", -r["superficie_m2"]))
    wanted = [lambda r: r["superficie_m2"] >= 10000, lambda r: 5000 <= r["superficie_m2"] < 10000,
              lambda r: r["zona_unidades"] in ("Rma5", "Cma4", "Cma3"), lambda r: r["zona_unidades"] == "Rm4",
              lambda r: r["zona_unidades"].startswith("Rb") or r["zona_unidades"] in ("Rmb2", "RmbB", "Cb1"),
              lambda r: r["zona_unidades"].startswith(("Ra", "Ca", "Cma1", "Cma2", "Rma1", "Rma2", "Rma3")),
              lambda r: r.get("frente_fuente") == "desconocido"]
    chosen = []
    for want in wanted:
        r = next((r for r in pool if want(r) and r not in chosen), None)
        if r:
            chosen.append(r)
    for r in pool:                                   # then other zones, one each
        if len(chosen) >= n:
            break
        if r not in chosen and r["zona_unidades"] not in {c["zona_unidades"] for c in chosen}:
            chosen.append(r)
    for r in pool:
        if len(chosen) >= n:
            break
        if r not in chosen:
            chosen.append(r)
    out = []
    for r in chosen[:n]:
        zone = by_name[r["zona_unidades"]]
        front = r.get("frente_m") if r.get("frente_fuente") != "desconocido" else None
        u = units(zone, r["superficie_m2"], front, p)
        fot = float(zone["fot"]) if zone["fot"] else None
        out.append({"id": r["id"], "titulo": r["titulo"][:60], "url": r["url"], "zona": zone["zona"],
                    "zona_excel": EXCEL_ZONE.get(zone["zona"], zone["zona"]), "superficie_m2": r["superficie_m2"],
                    "frente_m": front or "", "precio_usd": r["precio_usd"],
                    "sistema_m2_fot": round(fot * r["superficie_m2"]) if fot else "",
                    **{f"sistema_{k}": u[k] if u[k] is not None else "" for k in PRODUCTS},
                    "sistema_unidades_por_derecho": u["unidades_por_derecho"],
                    "sistema_unidades_con_aprobacion": u["unidades_con_aprobacion"],
                    "sistema_usd_por_unidad_derecho": round(r["precio_usd"] / u["unidades_por_derecho"])
                    if u["unidades_por_derecho"] else "",
                    "sistema_usd_por_unidad_aprobacion": round(r["precio_usd"] / u["unidades_con_aprobacion"])
                    if u["unidades_con_aprobacion"] else ""})
    return out


def write_book() -> None:
    """The CSVs of OUT in one workbook (one tab each), plus the summary."""
    from openpyxl import Workbook
    from openpyxl.styles import Font
    tabs = [("Comparación", "comparacion.csv"), ("Casos Excel", "casos_excel_resultado.csv"),
            ("Sensibilidad", "sensibilidad.csv"), ("Comparables", "comparables.csv")]
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"
    for line in (OUT / "resumen.txt").read_text(encoding="utf-8").splitlines():
        ws.append([line])
    ws.column_dimensions["A"].width = 120
    for title, name in tabs:
        if not (OUT / name).exists():
            continue
        rows = list(csv.reader(open(OUT / name, encoding="utf-8-sig")))
        if name == "casos_excel_resultado.csv":         # system and Excel side by side, field by field
            head = rows[0]
            keep = [c for c in head if not c.startswith(("sistema_", "excel_"))]
            pairs = [c for f in EXCEL_FIELDS for c in (f"sistema_{f}", f"excel_{f}")]
            order = [head.index(c) for c in keep + pairs]
            rows = [[r[i] for i in order] for r in rows]
        ws = wb.create_sheet(title)
        for i, r in enumerate(rows):
            ws.append([float(v) if i and v.replace(".", "", 1).replace("-", "", 1).isdigit() else v for v in r])
        for c in ws[1]:
            c.font = Font(bold=True)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(45, max(len(str(c.value or "")) for c in col) + 2)
    wb.save(OUT / "backtest_fase4.xlsx")


def compare_excel() -> None:
    """casos_excel_resultado.csv (tools/calculadora_excel.ps1) against the system, product by product."""
    cases = list(csv.DictReader(open(OUT / "casos_excel_resultado.csv", encoding="utf-8-sig")))
    num = lambda v: round(float(v)) if v not in ("", "-", "sin frente") else v              # noqa: E731
    lines, bad, expected = [], 0, 0
    for c in cases:
        # unknown front: the Excel shows 'sin frente' (0 by right); the system counts by surface only (Paso 3)
        no_front = not c["frente_m"] and "sin frente" in (c["excel_lotes_frente_propio"], c["excel_agrupadas_calle"])
        for f in EXCEL_FIELDS:
            sys_v, xl_v = c.get(f"sistema_{f}", ""), c.get(f"excel_{f}", "")
            try:
                same = num(sys_v) == num(xl_v) or (sys_v == "" and xl_v in ("-", ""))
            except ValueError:
                same = False
            by_design = not same and no_front and (xl_v == "sin frente" or f in ("unidades_por_derecho",
                                                                              "usd_por_unidad_derecho"))
            bad += not same and not by_design
            expected += by_design
            lines.append({"id": c["id"], "zona": c["zona"], "superficie_m2": c["superficie_m2"],
                          "frente_m": c["frente_m"], "precio_usd": c["precio_usd"], "campo": f,
                          "sistema": sys_v, "excel": xl_v,
                          "coincide": "sí" if same else ("esperado: frente desconocido" if by_design else "NO")})
    write_csv(OUT / "comparacion_excel.csv", lines, list(lines[0]))
    text = (f"{len(cases)} casos, {len(lines)} valores: {len(lines) - bad - expected} iguales, {expected} distintos a "
            f"propósito (frente desconocido), {bad} diferencias")
    summary = (OUT / "resumen.txt").read_text(encoding="utf-8").split("\nCalculadora del Excel:")[0]
    (OUT / "resumen.txt").write_text(summary + f"\nCalculadora del Excel: {text}", encoding="utf-8")
    write_book()
    print(f"{text} -> {OUT / 'comparacion_excel.csv'}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("runs", nargs="*", default=DEFAULT_RUNS, help="carpetas con raw_<portal>.json (la última gana)")
    ap.add_argument("--comparar-excel", action="store_true", help="comparar con casos_excel_resultado.csv")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.comparar_excel:
        compare_excel()
        return

    for stale in ("casos_excel_resultado.csv", "comparacion_excel.csv"):     # the cases may change: check them again
        (OUT / stale).unlink(missing_ok=True)
    items, health = load_items(args.runs)
    n_raw = sum(len(v) for v in items.values())
    cfg_old = load_config()
    cfg_old["productos"]["activo"] = False
    cfg_new = copy.deepcopy(cfg_old)
    cfg_new["productos"]["activo"] = True
    normativa = load_normativa(cfg_new)

    old = dedupe(process(items, cfg_old)[0], cfg_old)
    extra_health = []
    new, comps = process(items, cfg_new, None, extra_health)
    new = dedupe(new, cfg_new)
    write_csv(OUT / "resultado_fase2.csv", old, COLUMNS)
    write_csv(OUT / "resultado_fase4.csv", new, COLUMNS)
    write_csv(OUT / "comparables.csv", comps, list(comps[0]) if comps else ["id"])
    comparison = compare(old, new)
    write_csv(OUT / "comparacion.csv", comparison, COMPARE_FIELDS)
    sens = sensitivity(new, cfg_new)
    write_csv(OUT / "sensibilidad.csv", sens, list(sens[0]))
    cases = pick_cases(new, normativa, cfg_new["productos"])
    write_csv(OUT / "casos_excel.csv", cases, list(cases[0]))
    subject, body = render_report(new, health + extra_health, None, n_raw, cfg_new)
    (OUT / "mail_fase4.html").write_text(f"<p><b>{subject}</b></p>" + body, encoding="utf-8")

    # summary
    evaluated = [r for r in new if r.get("unidades_por_derecho") is not None]
    lines = [f"Crudos: {', '.join(args.runs)} -> " + ", ".join(f"{p} {len(v)}" for p, v in items.items()),
             f"Avisos distintos: Fase 2 {len(old)} | Fase 4 {len(new)}", ""]
    res_old, res_new = Counter(r["resultado"] for r in old), Counter(r["resultado"] for r in new)
    blocks = sections(new)
    lines += ["Fase 2 (regla actual): " + ", ".join(f"{k} {res_old[k]}" for k in ("oportunidad", "casi")),
              "Fase 4: " + ", ".join(f"{k} {res_new[k]}" for k in SHOWN)
              + " | " + ", ".join(f"{k} {len(v)}" for k, v in blocks.items()), ""]
    lines.append("Frente del lote entre los evaluados (>= prefiltro):")
    for portal in items:
        sub = [r for r in evaluated if r["portal"] == portal]
        c = Counter(r.get("frente_fuente") for r in sub)
        known = len(sub) - c["desconocido"]
        lines.append(f"  {portal:13} {known:4} de {len(sub):4} ({100 * known / max(len(sub), 1):.0f}%)  "
                     f"catastro {c['catastro']}, aviso {c['aviso']}, calculado {c['calculado']}")
    shown = [r for r in new if r["resultado"] in SHOWN]
    c = Counter(r.get("frente_fuente") for r in shown)
    lines.append(f"  entre los hits de Fase 4: {len(shown) - c['desconocido']} de {len(shown)} "
                 f"(catastro {c['catastro']}, aviso {c['aviso']}, calculado {c['calculado']})")
    lines += [f"Catastro ARBA: {h['paginas_ok']} consultas, {h['avisos']} avisos con parcela, "
              f"{len(h['errores'])} errores" for h in extra_health]
    lines += ["", "Comparables (lotes de 400-600 m2 de estos crudos, sin repetidos):"]
    lines += [f"  {x}" for x in sorted({r["comparables"] for r in new if r.get("mediana_usd_m2_lote")})]
    ch = Counter(x["cambio"] for x in comparison)
    lines += ["", "Cambios: " + ", ".join(f"{k} {ch[k]}" for k in ("nuevo", "cambia", "desaparece", "igual")),
              f"-> {OUT}"]
    text = "\n".join(lines)
    (OUT / "resumen.txt").write_text(text, encoding="utf-8")
    write_book()
    print(text)


if __name__ == "__main__":
    main()
