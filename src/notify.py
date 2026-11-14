"""Weekly mail (Gmail SMTP + app password). Always sent, even with 0 opportunities, so silence means trouble.

Env: GMAIL_USER, GMAIL_APP_PASSWORD, MAIL_TO (comma-separated).
Order: health line (red if a portal failed) -> new opportunities -> price drops -> new near-misses ->
new hits without street number ("Sin dirección — revisar") -> run summary + Sheet link.
With productos.activo (Fase 4): health -> multifamiliar -> loteo/agrupadas (by USD per unit) -> price drops ->
large lots -> near-misses -> without street number -> summary; each hit with its flags and a manual checklist.
"""

import html
import os
import re
import smtplib
from collections import Counter
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from .comparables import PARTIDO
from .evaluate import lot_product, sections

CHECKLIST = ("Verificar a mano: radio con parcela mínima especial · prolongación de calles · forestación · "
             "predio interno · pulmón de manzana · barranca")


def _env(name: str) -> str:
    v = os.environ.get(name, "").strip()
    if not v:
        raise RuntimeError(f"falta la variable de entorno {name}")
    return v


def _send(subject: str, body_html: str) -> None:
    user = _env("GMAIL_USER")
    to = [a.strip() for a in re.split(r"[,;]", os.environ.get("MAIL_TO_OVERRIDE") or _env("MAIL_TO")) if a.strip()]
    msg = MIMEMultipart("alternative")
    msg["Subject"], msg["From"], msg["To"] = subject, user, ", ".join(to)
    msg.attach(MIMEText(body_html, "html", "utf-8"))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=60) as s:
        s.login(user, _env("GMAIL_APP_PASSWORD"))
        s.sendmail(user, to, msg.as_string())
    print(f"Mail enviado a {', '.join(to)}: {subject}")


def test_prefix(cfg: dict) -> str:
    """A municipio in its trial weeks: the subject says so (the mail only goes to mail.para)."""
    return "[EN PRUEBA] " if cfg.get("municipio", {}).get("en_prueba") else ""


def _maps(r):
    return f"https://www.google.com/maps?q={r['lat_usada']:.6f},{r['lon_usada']:.6f}" if r.get("lat_usada") else ""


def _table(rows: list[dict], with_old_price=False) -> str:
    if not rows:
        return "<p style='color:#666'>Ninguna.</p>"
    head = ["Incidencia", "Precio USD"] + (["Antes USD"] if with_old_price else []) + \
           ["Superficie m²", "Zona / FOT", "m² constr.", "Tipo", "Ubicación", "Confianza", "Links"]
    out = ["<table cellpadding='5' style='border-collapse:collapse;font:13px Arial'>",
           "<tr style='background:#eee'>" + "".join(f"<th align='left'>{h}</th>" for h in head) + "</tr>"]
    for r in sorted(rows, key=lambda r: r["incidencia_usd_m2"]):
        links = f"<a href='{html.escape(r['url'])}'>aviso</a>"
        if _maps(r):
            links += f" · <a href='{_maps(r)}'>mapa</a>"
        if r.get("cantidad_publicaciones", 1) > 1:
            links += f" · +{r['cantidad_publicaciones'] - 1} publicaciones"
        dud = " (dudosa)" if r.get("superficie_dudosa") else ""
        cells = [f"<b>{r['incidencia_usd_m2']:.0f}</b>", f"{r['precio_usd']:,.0f}".replace(",", ".")]
        if with_old_price:
            cells.append(f"{r['precio_anterior']:,.0f}".replace(",", "."))
        cells += [f"{r['superficie_m2']:,.0f}".replace(",", ".") + dud, f"{r['zona_fot_usado']} / {r['fot_usado']}",
                  f"{r['m2_construibles']:,.0f}".replace(",", "."), html.escape(r.get("tipologia") or ""),
                  html.escape(f"{r.get('direccion') or ''}, {r.get('barrio') or ''}"),
                  html.escape(r.get("flag_confianza") or ""), links]
        out.append("<tr style='border-top:1px solid #ddd'>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
    out.append("</table>")
    return "\n".join(out)


def _health(health, changes) -> tuple[list[str], list[dict]]:
    parts = []
    if changes and changes.get("error_sheet"):
        parts.append(f"<p style='background:#fdd;color:#900;padding:8px;font-weight:bold'>⚠ No se pudo actualizar la "
                     f"Google Sheet ({html.escape(changes['error_sheet'][:200])}). Abajo van todos los hits vigentes "
                     "como si fueran nuevos.</p>")
    failed = [h for h in health if h["falla"]]
    if failed:
        detail = "; ".join(f"{h['portal']}: {h['avisos']} avisos" + (f" ({h['errores'][0][:150]})" if h["errores"] else "")
                           for h in failed)
        parts.append(f"<p style='background:#fdd;color:#900;padding:8px;font-weight:bold'>⚠ Falló la bajada — {html.escape(detail)}. "
                     "Los resultados de esta semana pueden estar incompletos.</p>")
    else:
        parts.append("<p style='color:#070'>✓ Todos los portales respondieron bien.</p>")
    return parts, failed


def send_report(rows, health, changes, n_raw, cfg) -> None:
    subject, body = render_report(rows, health, changes, n_raw, cfg)
    _send(subject, body)


def render_report(rows, health, changes, n_raw, cfg) -> tuple[str, str]:
    """(subject, HTML body) of the weekly mail."""
    if cfg["productos"]["activo"]:
        return _render_products(rows, health, changes, n_raw, cfg)
    today = date.today().strftime("%d/%m/%Y")
    hits = [r for r in rows if r["resultado"] in ("oportunidad", "casi")]
    sheet_ok = changes and "nuevas" in changes
    new = changes["nuevas"] if sheet_ok else hits          # without Sheet everything counts as new
    drops = changes["bajas_de_precio"] if sheet_ok else []
    located = [r for r in new if r.get("flag_confianza") != "aproximada_barrio"]
    unknown = [r for r in new if r.get("flag_confianza") == "aproximada_barrio"]
    new_opps = [r for r in located if r["resultado"] == "oportunidad"]
    new_near = [r for r in located if r["resultado"] == "casi"]
    n = sum(1 for r in new if r["resultado"] == "oportunidad")

    parts, failed = _health(health, changes)
    c = cfg["criterio"]
    parts += [f"<h2>Oportunidades nuevas ({len(new_opps)})</h2>",
              f"<p style='color:#666'>m² construibles &gt; {c['m2_construibles_min']} e incidencia &lt; USD {c['incidencia_max_usd']}/m².</p>",
              _table(new_opps),
              f"<h2>Bajas de precio ({len(drops)})</h2>", _table(drops, with_old_price=True),
              f"<h2>Casi-oportunidades nuevas ({len(new_near)})</h2>",
              f"<p style='color:#666'>Incidencia entre {c['incidencia_max_usd']} y {c['incidencia_casi_max_usd']}.</p>",
              _table(new_near),
              f"<h2>Sin dirección — revisar ({len(unknown)})</h2>",
              "<p style='color:#666'>El aviso no da la altura. El FOT es el máximo de la calle o esquina informada "
              "(o de la localidad), así que la incidencia puede ser mejor que la real.</p>",
              _table(unknown)]
    res = Counter(r["resultado"] for r in rows)
    why = Counter(r["motivo_descarte"].split(" (")[0] for r in rows if r["resultado"] == "descartado")
    portals = ", ".join(f"{h['portal']} {h['avisos']}" for h in health) or "reprocesado"
    parts.append("<h2>Resumen de la corrida</h2><p>"
                 f"Avisos bajados: {n_raw} ({portals}) · distintos: {len(rows)}<br>"
                 f"Oportunidades vigentes: {res['oportunidad']} · casi: {res['casi']} · descartados: {res['descartado']}<br>"
                 f"Descartes: {html.escape(', '.join(f'{k} {v}' for k, v in why.most_common(6)))}</p>")
    if changes and changes.get("sheet_url"):
        parts.append(f"<p><a href='{changes['sheet_url']}'>Abrir la Google Sheet</a></p>")
    subject = test_prefix(cfg) + cfg["mail"]["asunto"].format(n=n, fecha=today)
    if failed:
        subject += " — ⚠ falla en " + ", ".join(h["portal"] for h in failed)
    return subject, "<div style='font:14px Arial'>" + "\n".join(parts) + "</div>"


# ---------------------------------------------------------------- Fase 4 (productos.activo)

def _n(v, unit="") -> str:
    return "" if v in (None, "") else f"{unit}{v:,.0f}".replace(",", ".")


def _hit_rows(rows: list[dict], columns: list[tuple[str, callable]], with_old_price=False, front_matters=True) -> str:
    """One table row per hit + a grey line below with its flags and the manual checklist."""
    if not rows:
        return "<p style='color:#666'>Ninguna.</p>"
    if with_old_price:
        columns = columns[:1] + [("Antes USD", lambda r: _n(r["precio_anterior"]))] + columns[1:]
    out = ["<table cellpadding='5' style='border-collapse:collapse;font:13px Arial'>",
           "<tr style='background:#eee'>" + "".join(f"<th align='left'>{h}</th>" for h, _ in columns) + "</tr>"]
    for r in rows:
        links = f"<a href='{html.escape(r['url'])}'>aviso</a>"
        if _maps(r):
            links += f" · <a href='{_maps(r)}'>mapa</a>"
        if r.get("cantidad_publicaciones", 1) > 1:
            links += f" · +{r['cantidad_publicaciones'] - 1} publicaciones"
        cells = [fn(r) for _, fn in columns[:-1]] + [links]
        out.append("<tr style='border-top:1px solid #ddd'>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        notes = []
        via = r.get("via") or ""
        if front_matters and "frente_desconocido" in (r.get("alertas") or "") and \
                ("loteo" in via or "multifamiliar" not in via):             # the front doesn't change flats
            notes.append("<b style='color:#b60'>⚠ frente desconocido: unidades calculadas solo por superficie</b>")
        if r.get("partidas_catastro"):
            front = f", frente {r['frente_catastro_m']:g} m" if r.get("frente_catastro_m") else ", sin lado de frente"
            notes.append(f"Catastro ARBA: partida {html.escape(r['partidas_catastro'])} "
                         f"({_n(r['superficie_catastro_m2'])} m²{front})")
        if r.get("flags"):
            notes.append("⚑ " + html.escape(r["flags"]))
        notes.append(CHECKLIST)
        out.append(f"<tr><td colspan='{len(columns)}' style='color:#666;font-size:12px;padding-top:0'>"
                   + "<br>".join(notes) + "</td></tr>")
    out.append("</table>")
    return "\n".join(out)


def _place(r):
    return html.escape(f"{r.get('direccion') or ''}, {r.get('barrio') or ''}")


def _units(r):
    return (f"<b>{r['unidades_por_derecho']}</b> ({html.escape(r.get('mejor_producto') or '-')}) · "
            f"{r['unidades_con_aprobacion']} con aprobación")


def _front(r):
    if not r.get("frente_m"):
        return "?"
    return f"{r['frente_m']:g} m" + {"calculado": " (calc.)", "catastro": " (catastro)"}.get(r.get("frente_fuente"), "")


def _lot_value(r):
    if not r.get("valor_lote_estimado") or r.get("ratio_compra_reventa") is None:
        return "sin comparables"
    where = " · mediana del partido" if (r.get("comparables") or "").startswith(PARTIDO) else ""
    return f"{_n(r['valor_lote_estimado'])} (ratio <b>{r['ratio_compra_reventa']:.2f}</b>{where})"


MULTI_COLUMNS = [
    ("Incidencia", lambda r: f"<b>{r['incidencia_usd_m2']:.0f}</b>"),
    ("Precio USD", lambda r: _n(r["precio_usd"])),
    ("Superficie m²", lambda r: _n(r["superficie_m2"]) + (" (dudosa)" if r.get("superficie_dudosa") else "")),
    ("Zona / FOT", lambda r: f"{r['zona_fot_usado']} / {r['fot_usado']:g}"),
    ("m² constr.", lambda r: _n(r["m2_construibles"])),
    ("Unidades", lambda r: f"{_n(r.get('multifamiliar_unidades'))} multifamiliar"),
    ("Tipo", lambda r: html.escape(r.get("tipologia") or "")),
    ("Ubicación", _place),
    ("Confianza", lambda r: html.escape(r.get("flag_confianza") or "")),
    ("Links", None),
]


def _lot_units(r):
    return (f"<b>{r['unidades_loteo']}</b> {html.escape(lot_product(r))} · "
            f"{r['unidades_con_aprobacion']} con aprobación")


LOT_COLUMNS = [
    ("USD por unidad", lambda r: f"<b>{_n(r['usd_por_unidad_loteo'])}</b>"),
    ("Unidades por derecho", _lot_units),
    ("Valor lote chico USD", _lot_value),
    ("Precio USD", lambda r: _n(r["precio_usd"])),
    ("Superficie m²", lambda r: _n(r["superficie_m2"])),
    ("Frente", _front),
    ("Zona", lambda r: html.escape(r.get("zona_unidades") or "")),
    ("Ubicación", _place),
    ("Confianza", lambda r: html.escape(r.get("flag_confianza") or "")),
    ("Links", None),
]
BIG_COLUMNS = [
    ("Superficie m²", lambda r: f"<b>{_n(r['superficie_m2'])}</b>"),
    ("Precio USD", lambda r: _n(r["precio_usd"])),
    ("USD/m² terreno", lambda r: _n(r["precio_usd"] / r["superficie_m2"])),
    ("Unidades por derecho", _units),
    ("Urbanización Especial", lambda r: _n(r.get("ue_unidades")) or "-"),
    ("Zona", lambda r: html.escape(r.get("zona_unidades") or "")),
    ("Ubicación", _place),
    ("Links", None),
]
NEAR_COLUMNS = [
    ("Por qué", lambda r: html.escape(r.get("via") or "")),
    ("Incidencia", lambda r: _n(r.get("incidencia_usd_m2"))),
    ("USD por unidad (derecho / aprobación)",
     lambda r: f"{_n(r.get('usd_por_unidad_derecho')) or '-'} / {_n(r.get('usd_por_unidad_aprobacion')) or '-'}"),
    ("Unidades por derecho", _units),
    ("Precio USD", lambda r: _n(r["precio_usd"])),
    ("Superficie m²", lambda r: _n(r["superficie_m2"])),
    ("Zona", lambda r: html.escape((r.get("zona_fot_usado") if (r.get("via") or "").startswith("multifamiliar")
                                    else r.get("zona_unidades")) or "")),
    ("Ubicación", _place),
    ("Links", None),
]


def _render_products(rows, health, changes, n_raw, cfg) -> tuple[str, str]:
    today = date.today().strftime("%d/%m/%Y")
    c, p = cfg["criterio"], cfg["productos"]
    sheet_ok = changes and "nuevas" in changes
    shown = [r for r in rows if r["resultado"] in ("oportunidad", "casi", "gran_predio")]
    new = changes["nuevas"] if sheet_ok else shown          # without Sheet everything counts as new
    drops = changes["bajas_de_precio"] if sheet_ok else []
    blocks = sections(new)
    n = sum(1 for r in new if r["resultado"] == "oportunidad")

    parts, failed = _health(health, changes)
    ratio = f"{p['umbral_ratio_loteo']:g}".replace(".", ",")
    parts += [f"<h2>Oportunidades multifamiliar ({len(blocks['multifamiliar'])})</h2>",
              f"<p style='color:#666'>Zona que admite multifamiliar, m² construibles &gt; {c['m2_construibles_min']} e "
              f"incidencia &lt; USD {c['incidencia_max_usd']}/m².</p>",
              _hit_rows(blocks["multifamiliar"], MULTI_COLUMNS, front_matters=False),
              f"<h2>Oportunidades loteo / agrupadas ({len(blocks['loteo_agrupadas'])})</h2>",
              f"<p style='color:#666'>{p['unidades_min']} unidades o más por derecho y USD por unidad hasta "
              f"{ratio} veces el valor de un lote chico de la localidad (con menos de "
              f"{p['comparables']['avisos_min']} lotes chicos en la localidad, la mediana del partido). "
              "Ordenadas por USD por unidad.</p>",
              _hit_rows(blocks["loteo_agrupadas"], LOT_COLUMNS),
              f"<h2>Bajas de precio ({len(drops)})</h2>",
              _hit_rows(drops, NEAR_COLUMNS, with_old_price=True),
              f"<h2>Grandes predios ({len(blocks['gran_predio'])})</h2>",
              f"<p style='color:#666'>{_n(p['sup_min_gran_predio'])} m² o más en zona con vivienda, a cualquier precio "
              "(los que ya son oportunidad van arriba).</p>",
              _hit_rows(blocks["gran_predio"], BIG_COLUMNS),
              f"<h2>Casi-oportunidades ({len(blocks['casi'])})</h2>",
              f"<p style='color:#666'>Multifamiliar con incidencia entre {c['incidencia_max_usd']} y "
              f"{c['incidencia_casi_max_usd']}, multifamiliar condicional, o loteo que cierra solo con aprobación "
              "(O.T. o Urbanización Especial).</p>",
              _hit_rows(blocks["casi"], NEAR_COLUMNS),
              f"<h2>Sin dirección — revisar ({len(blocks['sin_direccion'])})</h2>",
              "<p style='color:#666'>El aviso no da la altura: FOT y unidades de la zona más favorable de la calle, "
              "esquina o localidad, así que pueden ser mejores que los reales.</p>",
              _hit_rows(blocks["sin_direccion"], NEAR_COLUMNS)]
    res = Counter(r["resultado"] for r in rows)
    why = Counter(r["motivo_descarte"].split(" (")[0] for r in rows if r["resultado"] == "descartado")
    portals = ", ".join(f"{h['portal']} {h['avisos']}" for h in health) or "reprocesado"
    evaluated = [r for r in rows if r.get("unidades_por_derecho") is not None]
    known = Counter(r.get("frente_fuente") for r in evaluated)
    comps = sorted({r["comparables"] for r in rows if r.get("mediana_usd_m2_lote")})
    parts.append("<h2>Resumen de la corrida</h2><p>"
                 f"Avisos bajados: {n_raw} ({portals}) · distintos: {len(rows)}<br>"
                 f"Vigentes: {res['oportunidad']} oportunidades · {res['casi']} casi · "
                 f"{res['gran_predio']} grandes predios · {res['descartado']} descartados<br>"
                 f"Frente del lote conocido en {len(evaluated) - known['desconocido']} de {len(evaluated)} evaluados "
                 f"(catastro {known['catastro']}, aviso {known['aviso']}, calculado {known['calculado']})<br>"
                 "Lote chico (mediana USD/m²): " + (html.escape(" · ".join(comps)) or "sin comparables") + "<br>"
                 f"Descartes: {html.escape(', '.join(f'{k} {v}' for k, v in why.most_common(6)))}</p>")
    if changes and changes.get("sheet_url"):
        parts.append(f"<p><a href='{changes['sheet_url']}'>Abrir la Google Sheet</a></p>")
    subject = test_prefix(cfg) + cfg["mail"]["asunto"].format(n=n, fecha=today)
    if failed:
        subject += " — ⚠ falla en " + ", ".join(h["portal"] for h in failed)
    return subject, "<div style='font:14px Arial'>" + "\n".join(parts) + "</div>"


def send_error(tb: str, cfg: dict) -> None:
    today = date.today().strftime("%d/%m/%Y")
    try:
        _send(f"{test_prefix(cfg)}Scouting {cfg.get('municipio', {}).get('nombre', 'San Isidro')} — ERROR en la corrida ({today})",
              "<p style='color:#900;font-weight:bold'>La corrida semanal se cortó con un error. "
              "No hay resultados esta semana.</p><pre style='font-size:12px'>" + html.escape(tb[-4000:]) + "</pre>")
    except Exception as e:                                # noqa: BLE001 - nothing else to do
        print(f"Tampoco se pudo mandar el mail de error: {e}")
