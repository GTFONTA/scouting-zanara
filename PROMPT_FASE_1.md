# FASE 1 — Pipeline de punta a punta con un portal (local)

Leé CLAUDE.md. Requisito: Fase 0 validada. Objetivo: el pipeline completo corriendo en mi PC con un solo portal (Zonaprop), salida a CSV local. Todavía sin Sheet, mail ni cron.

## Paso 1 — Elegir el actor de Apify
- Buscá en Apify Store actores para Zonaprop. Elegí el que tenga más usuarios y actualización reciente. Explicame la elección en 3 líneas (costo estimado por corrida incluido).
- Parametrizar en `config.yaml`: ID del actor, input (partido San Isidro, operación venta, tipologías incluidas, superficie mínima = `superficie_min_prefiltro`).
- Token de Apify en variable de entorno `APIFY_TOKEN`.

## Paso 2 — fetch.py
Correr el actor, bajar resultados, guardar el crudo en `runs/<fecha>/raw_zonaprop.json` (sirve para depurar).

## Paso 3 — normalize.py
- Precio a USD. Si viene en ARS: convertir con dólar MEP de `https://dolarapi.com/v1/dolares/bolsa`. Guardar la cotización usada.
- Descartar: sin precio / "consultar", tipologías excluidas (ver CLAUDE.md, detectar también por palabras en el título: "PH", "depto", "unidad").
- Superficie: usar superficie de terreno. Si solo hay "total" y es casa, usar total y marcar `superficie_dudosa = True`.
- Esquema normalizado común (lo van a usar los otros portales): `id, portal, url, titulo, tipologia, precio_usd, moneda_original, superficie_m2, superficie_dudosa, direccion, barrio, lat, lon, fecha_publicacion`.

## Paso 4 — locate.py
1. Si el aviso trae lat/lon → `flag_confianza = exacta`.
2. Si no, geocodificar la dirección (Google Geocoding API, key en `GOOGLE_GEOCODING_KEY`; si no hay key, Nominatim). Validar que caiga dentro del partido → `geocodificada`.
3. Si no, centroide del barrio → `aproximada_barrio`.
4. Point-in-polygon contra `zonas_san_isidro.geojson` → zona → FOT.
5. Para `aproximada_barrio`: usar el FOT **máximo** de las zonas que intersectan el barrio (criterio de no perder oportunidades). Guardar `fot_fuente = max_barrio`.

## Paso 5 — evaluate.py
Calcular m² construibles e incidencia y clasificar: `oportunidad` | `casi` | `descartado`, con las reglas de CLAUDE.md. Guardar todos los intermedios.

## Paso 6 — main.py
Orquestar y escribir `runs/<fecha>/resultado.csv` con todos los avisos procesados, más un resumen en consola: bajados, descartados por motivo, oportunidades, casi.

## Entregable
Una corrida real. Mostrame el resumen y las oportunidades/casi encontradas, y señalá cualquier cosa rara que veas en los datos (precios absurdos, superficies imposibles).
