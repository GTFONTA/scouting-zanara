# FASE 2 — Todos los portales, histórico, mail y ejecución automática

Leé CLAUDE.md. Requisito: Fase 1 funcionando. Objetivo: el sistema corre solo cada semana y me manda un mail.

## Paso 1 — Sumar portales
Agregar actores de Apify para Argenprop y Mercado Libre Inmuebles, con el mismo criterio de elección que en Fase 1. Cada uno mapea al esquema normalizado. Si un portal falla, el resto sigue.

## Paso 2 — dedupe.py
Mismo inmueble en varios portales o con varias inmobiliarias:
- Duplicado si: superficie ±5% **y** precio ±5% **y** distancia < 150 m (o mismo barrio si alguno es `aproximada_barrio`).
- Quedarse con el registro de mejor `flag_confianza`; guardar los links de todos los duplicados en una columna `otros_links`.

## Paso 3 — store.py (Google Sheet)
- Service account de Google; credencial en `GOOGLE_SA_JSON`. Guiame paso a paso para crearla y compartir la Sheet.
- Pestaña `oportunidades`: oportunidades y casi, acumulado histórico. Columnas: fecha_deteccion, clasificacion, incidencia, m2_construibles, precio_usd, superficie_m2, zona, fot, fot_fuente, flag_confianza, superficie_dudosa, tipologia, barrio, direccion, url, otros_links, maps_link, estado (vacía, la uso yo).
- Pestaña `corridas`: una fila por corrida con el resumen (bajados por portal, descartados por motivo, hits).
- Un aviso es "nuevo" si su id (o el de algún duplicado) no está en la Sheet. Si ya estaba y bajó de precio, marcarlo como `bajó de precio`.
- Formato: encabezado fijo, incidencia con formato condicional (verde < 200, amarillo 200–250).

## Paso 4 — notify.py (mail)
- Gmail SMTP con contraseña de aplicación (`GMAIL_USER`, `GMAIL_APP_PASSWORD`, `MAIL_TO`). Guiame para crearla.
- Asunto: `Scouting San Isidro — N oportunidades nuevas (fecha)`.
- Cuerpo HTML simple:
  1. **Chequeo de salud primero:** si algún portal devolvió 0 avisos o falló, una línea roja arriba de todo.
  2. Oportunidades nuevas ordenadas por incidencia: link, precio, superficie, zona, FOT, m² construibles, incidencia, flag, link a Maps.
  3. Bajas de precio.
  4. Casi-oportunidades nuevas.
  5. Resumen de la corrida y link a la Sheet.
- Mandar el mail **siempre**, aunque haya 0 oportunidades (así sé que el sistema está vivo).

## Paso 5 — GitHub Actions
- Repo privado. Workflow semanal, lunes 7:00 hora Argentina (`cron: '0 10 * * 1'` UTC), más disparo manual (`workflow_dispatch`).
- Secretos en GitHub Secrets. Guiame para cargarlos.
- Si el workflow falla, que igual intente mandar un mail avisando el error.

## Entregable
Una corrida disparada a mano desde GitHub, con el mail recibido y la Sheet poblada.
