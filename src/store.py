"""Google Sheet history (gspread + service account).

Tabs:
  oportunidades  opportunities and near-misses, cumulative. A listing is new if neither its id nor any of its
                 duplicates' ids is already there; if it was there and the price went down it is marked as a
                 price drop. The `estado` column (and any column Gonzalo adds) is never overwritten.
  corridas       one row per run with its summary.
  comparables    (productos.activo) small lots of the last weeks, the yardstick for loteo (comparables.py).
With productos.activo the large lots are stored too, and the product columns go right after `incidencia`; the
first run with it moves the existing columns to that order (Gonzalo's own columns stay, at the end).
Credentials: GOOGLE_SA_JSON = path to the service-account JSON file (or the JSON itself).
"""

import json
import os
from collections import Counter
from datetime import date

import gspread

from . import comparables
from .evaluate import sections

OPP_COLUMNS = [
    "fecha_deteccion", "clasificacion", "incidencia", "m2_construibles", "precio_usd", "superficie_m2", "zona",
    "fot", "fot_fuente", "flag_confianza", "superficie_dudosa", "tipologia", "barrio", "direccion", "url",
    "otros_links", "maps_link", "estado",
    # traceability (after the columns Gonzalo reads)
    "novedad", "precio_anterior", "fecha_ultima_vista", "seccion", "portal", "titulo", "alertas", "id", "ids_duplicados",
]
OPP_COLUMNS_PRODUCTS = [
    "fecha_deteccion", "clasificacion", "incidencia", "via", "mejor_producto", "unidades_por_derecho",
    "unidades_con_aprobacion", "usd_por_unidad_derecho", "valor_lote_estimado", "ratio_compra_reventa",
    "unidades_loteo", "comparables", "m2_construibles", "precio_usd", "superficie_m2", "frente_m", "frente_fuente",
    "zona", "fot", "fot_fuente",
    "zona_unidades", "flag_confianza", "superficie_dudosa", "tipologia", "barrio", "direccion", "url",
    "otros_links", "maps_link", "estado", "flags",
    "novedad", "precio_anterior", "fecha_ultima_vista", "seccion", "portal", "titulo", "alertas", "partidas_catastro",
    "id", "ids_duplicados",
]
RUN_COLUMNS = ["fecha", "avisos_por_portal", "portales_con_falla", "avisos_distintos", "oportunidades", "casi",
               "oportunidades_nuevas", "casi_nuevas", "bajas_de_precio", "descartes_por_motivo", "errores"]
RUN_COLUMNS_PRODUCTS = RUN_COLUMNS + ["oportunidades_multifamiliar", "oportunidades_loteo", "grandes_predios",
                                      "comparables_por_localidad"]
KEEP = {"estado", "fecha_deteccion"}          # never overwritten once written


def _client() -> gspread.Client:
    raw = os.environ.get("GOOGLE_SA_JSON", "").strip()
    if not raw:
        raise RuntimeError("falta la variable GOOGLE_SA_JSON (ruta al JSON de la service account)")
    if raw.startswith("{"):
        return gspread.service_account_from_dict(json.loads(raw))
    return gspread.service_account(filename=raw)


def _row_values(r: dict, today: str) -> dict:
    return {
        "fecha_deteccion": today,
        "clasificacion": r["resultado"],
        "incidencia": r["incidencia_usd_m2"],
        "m2_construibles": r["m2_construibles"],
        "precio_usd": r["precio_usd"],
        "superficie_m2": r["superficie_m2"],
        "zona": r.get("zona_fot_usado") or "",
        "fot": r.get("fot_usado"),
        "fot_fuente": r.get("fot_fuente") or "",
        "flag_confianza": r.get("flag_confianza") or "",
        "superficie_dudosa": "sí" if r.get("superficie_dudosa") else "no",
        "tipologia": r.get("tipologia") or "",
        "barrio": r.get("barrio") or "",
        "direccion": r.get("direccion") or "",
        "url": r["url"],
        "otros_links": r.get("otros_links") or "",
        "maps_link": f"https://www.google.com/maps?q={r['lat_usada']:.6f},{r['lon_usada']:.6f}" if r.get("lat_usada") else "",
        "fecha_ultima_vista": today,
        "seccion": "sin dirección — revisar" if r.get("flag_confianza") == "aproximada_barrio" else "con dirección",
        "portal": r["portal"],
        "titulo": r.get("titulo") or "",
        "alertas": r.get("alertas") or "",
        "id": r["id"],
        "ids_duplicados": r.get("ids_duplicados") or "",
        # Fase 4 (only in the product columns)
        **{k: r.get(k) for k in ("via", "mejor_producto", "unidades_por_derecho", "unidades_con_aprobacion",
                                 "usd_por_unidad_derecho", "valor_lote_estimado", "ratio_compra_reventa",
                                 "unidades_loteo", "comparables", "frente_m", "frente_fuente", "zona_unidades",
                                 "flags", "partidas_catastro")},
    }


def _worksheet(sh, title: str, header: list[str], fresh_setup) -> gspread.Worksheet:
    try:
        return sh.worksheet(title)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(header))
        ws.update([header], "A1", value_input_option="RAW")
        ws.freeze(rows=1)
        ws.format("1:1", {"textFormat": {"bold": True}})
        if fresh_setup:
            fresh_setup(ws)
        return ws


def _incidence_colors(cfg: dict):
    c = cfg["criterio"]

    def setup(ws):
        col = OPP_COLUMNS.index("incidencia")
        rng = {"sheetId": ws.id, "startRowIndex": 1, "startColumnIndex": col, "endColumnIndex": col + 1}
        rules = [
            ("NUMBER_LESS", [c["incidencia_max_usd"]], {"red": 0.72, "green": 0.88, "blue": 0.72}),
            ("NUMBER_BETWEEN", [c["incidencia_max_usd"], c["incidencia_casi_max_usd"]], {"red": 1, "green": 0.93, "blue": 0.6}),
        ]
        ws.spreadsheet.batch_update({"requests": [{"addConditionalFormatRule": {"index": i, "rule": {
            "ranges": [rng],
            "booleanRule": {"condition": {"type": kind, "values": [{"userEnteredValue": str(v)} for v in vals]},
                            "format": {"backgroundColor": color}}}}} for i, (kind, vals, color) in enumerate(rules)]})
    return setup


def read_comparables(cfg: dict) -> list[dict]:
    """Small lots kept by previous runs (tab 'comparables'); empty before the first run with productos.activo."""
    try:
        ws = _client().open_by_key(cfg["sheet"]["id"]).worksheet("comparables")
    except gspread.WorksheetNotFound:
        return []
    return ws.get_all_records()


def _write_comparables(sh, comps: list[dict]) -> None:
    ws = _worksheet(sh, "comparables", comparables.COLUMNS, None)
    out = [comparables.COLUMNS] + [[c.get(k, "") for k in comparables.COLUMNS] for c in comps]
    if len(out) > ws.row_count:
        ws.add_rows(len(out) - ws.row_count + 100)
    ws.update(out, "A1", value_input_option="RAW")
    if len(out) < ws.row_count:
        ws.batch_clear([f"A{len(out) + 1}:H{ws.row_count}"])      # rows older than the kept weeks


def update_sheet(rows: list[dict], health: list[dict], n_raw: int, cfg: dict, comps: list[dict] | None = None) -> dict:
    """Write this run's hits (and the small-lot comparables); return what is new for the mail."""
    today = date.today().isoformat()
    products = cfg["productos"]["activo"]
    columns = OPP_COLUMNS_PRODUCTS if products else OPP_COLUMNS
    shown = ("oportunidad", "casi", "gran_predio") if products else ("oportunidad", "casi")
    sh = _client().open_by_key(cfg["sheet"]["id"])
    ws = _worksheet(sh, "oportunidades", columns, _incidence_colors(cfg))
    table = ws.get_values(value_render_option="UNFORMATTED_VALUE")
    old = table[0] if table else columns
    records = [dict(zip(old, row + [""] * (len(old) - len(row)))) for row in table[1:]]
    if products and any(c not in old for c in columns):
        header = columns + [c for c in old if c not in columns]      # Fase 4 order, Gonzalo's own columns last
        for rec in records:                   # found under the Fase 2 rule; this week's hits get refreshed below
            rec["via"] = rec.get("via") or "regla Fase 2"
    else:
        header = old + [c for c in columns if c not in old]
    index = {}
    for i, rec in enumerate(records):
        for rid in [rec.get("id")] + str(rec.get("ids_duplicados") or "").split():
            if rid:
                index[rid] = i

    changes = {"nuevas": [], "bajas_de_precio": []}
    for r in rows:
        if r["resultado"] not in shown:
            continue
        ids = [r["id"]] + (r.get("ids_duplicados") or "").split()
        hit = next((index[i] for i in ids if i in index), None)
        values = _row_values(r, today)
        if hit is None:
            values["novedad"] = f"nuevo {today}"
            records.append(values)
            for i in ids:
                index[i] = len(records) - 1
            changes["nuevas"].append(r)
            continue
        rec = records[hit]
        old_price = float(rec.get("precio_usd") or 0)
        if old_price and r["precio_usd"] < old_price * 0.999:
            values["precio_anterior"] = old_price
            values["novedad"] = f"bajó de precio {today}"
            changes["bajas_de_precio"].append({**r, "precio_anterior": old_price})
        # refresh with this run's data (best copy of the group, current zoning rules); keep the row's own id
        # and every id ever seen for it, so it is still recognised next week
        known = set(str(rec.get("ids_duplicados") or "").split()) | set(ids)
        keep_id = rec.get("id") or values["id"]
        rec.update({k: v for k, v in values.items() if k not in KEEP | {"id", "ids_duplicados", "novedad"} or
                    (k == "novedad" and "novedad" in values and values["novedad"].startswith("bajó"))})
        rec["ids_duplicados"] = " ".join(sorted(known - {keep_id}))

    out = [header] + [[rec.get(col, "") if rec.get(col) is not None else "" for col in header] for rec in records]
    if len(out) > ws.row_count:
        ws.add_rows(len(out) - ws.row_count + 100)
    if len(header) > ws.col_count:
        ws.add_cols(len(header) - ws.col_count)
    ws.update(out, "A1", value_input_option="RAW")

    run_columns = RUN_COLUMNS_PRODUCTS if products else RUN_COLUMNS
    runs = _worksheet(sh, "corridas", run_columns, None)
    res = Counter(r["resultado"] for r in rows)
    why = Counter(r["motivo_descarte"].split(" (")[0] for r in rows if r["resultado"] == "descartado")
    new = Counter(r["resultado"] for r in changes["nuevas"])
    line = [
        today,
        "; ".join(f"{h['portal']}={h['avisos']}" for h in health),
        ", ".join(h["portal"] for h in health if h["falla"]) or "ninguno",
        len(rows), res["oportunidad"], res["casi"], new["oportunidad"], new["casi"], len(changes["bajas_de_precio"]),
        "; ".join(f"{k}={v}" for k, v in why.most_common()),
        " | ".join(e for h in health for e in h["errores"])[:5000],
    ]
    if products:
        blocks = sections(rows)
        used = sorted({r["comparables"] for r in rows if r.get("mediana_usd_m2_lote")})
        line += [len(blocks["multifamiliar"]), len(blocks["loteo_agrupadas"]), res["gran_predio"], "; ".join(used)]
        if runs.col_count < len(run_columns):
            runs.add_cols(len(run_columns) - runs.col_count)
        if runs.row_values(1) != run_columns:
            runs.update([run_columns], "A1", value_input_option="RAW")
        if comps:
            _write_comparables(sh, comps)
    runs.append_row(line, value_input_option="RAW")
    changes["sheet_url"] = sh.url
    print(f"Sheet: {len(changes['nuevas'])} nuevas, {len(changes['bajas_de_precio'])} bajas de precio -> {sh.url}")
    return changes
