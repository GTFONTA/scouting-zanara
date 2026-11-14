# FASE 0 — Zonificación y validación manual

Leé CLAUDE.md antes de empezar. Objetivo de esta fase: tener `data/zonas_san_isidro.geojson` y `data/fot_por_zona.csv` confiables, y validar el criterio sobre avisos reales. Sin esto no se construye nada más.

## Paso 1 — Encontrar la capa ZONAS
San Isidro tiene un Portal GIS oficial (ArcGIS) en `msi-gis.gestionmsi.gob.ar` con una capa pública llamada "ZONAS" (polígonos de zonificación).
1. Explorá el REST directory del servidor (probar `/server/rest/services`, `/arcgis/rest/services` y variantes) y encontrá el servicio y el ID de la capa ZONAS.
2. Mostrame la URL exacta de la capa y la lista completa de campos (nombre, tipo, alias).
3. **Pregunta clave:** ¿los polígonos traen FOT, FOS y altura como atributos, o solo el nombre/código de zona? Reportalo antes de seguir.

Si el servidor bloquea el acceso desde script, pedime que abra la URL en el navegador y te pegue lo que ve.

## Paso 2 — Extraer como GeoJSON en coordenadas estándar
Consultar la capa con:
`<url_capa>/query?where=1=1&outFields=*&f=geojson&outSR=4326`
- `outSR=4326` hace que el servidor reproyecte de Gauss-Krüger a lat/lon; así evitamos reproyectar localmente. Verificar igual que las coordenadas caigan en San Isidro (lat ≈ -34.47, lon ≈ -58.52).
- Si hay más features que el límite del servidor (`maxRecordCount`), paginar con `resultOffset`.
- Guardar en `data/zonas_san_isidro.geojson`.
- Generar un HTML simple con los polígonos sobre un mapa (folium) para que yo lo mire y confirme que está bien.

## Paso 3 — Tabla FOT por zona
- Si la capa trae FOT: armar `data/fot_por_zona.csv` a partir de ella.
- Si no: te voy a pasar el PDF del Código de Ordenamiento Urbano de San Isidro. Extraé para cada zona: FOT, FOS, altura máxima. Columnas: `zona, fot, fos, altura_max, fuente, notas`.
- Listame las zonas de la capa que no matchean con ninguna fila de la tabla (y viceversa).
- Calcular y guardar en config: `fot_max` del partido y `superficie_min_prefiltro = 1300 / fot_max`.

## Paso 4 — Validación manual
Te voy a pasar 10–15 links de avisos reales. Para cada uno calculá a mano con los datos de este paso: zona, FOT, m² construibles, incidencia, y si es oportunidad según CLAUDE.md. Presentalo en una tabla. Yo voy a marcar dónde el resultado no coincide con mi criterio, y con eso ajustamos antes de la Fase 1.

## Entregable
- `data/zonas_san_isidro.geojson`, `data/fot_por_zona.csv`, mapa HTML de control, tabla de validación.
- Un resumen de 5 líneas: qué funcionó, qué quedó dudoso.
