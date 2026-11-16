# Scouting de tierra San Isidro — ZANARA

## Qué es
Script que corre solo una vez por semana y detecta inmuebles en venta en el partido de San Isidro que sean oportunidad de compra para desarrollo propio de ZANARA. Manda un mail con las novedades. El usuario (Gonzalo) no tiene que intervenir en régimen: solo lee el mail.

## Reglas de negocio (no cambiar sin que Gonzalo lo pida)
Cada aviso se evalúa por los productos de ZANARA (Fase 4, aprobada por Gonzalo el 28/09/2026). Normativa por zona en `data/normativa_zonas.csv` (C.O.U. T.O. 2022); fórmulas de la pestaña "Calculadora" de `docs/Zonificacion_San_Isidro_COU2022_v2.xlsx`. Todas las unidades se redondean hacia abajo.
- **Unidades por derecho**: lotes con frente propio = mín(superficie ÷ parcela mínima, frente ÷ ancho mínimo); agrupadas a la calle = mín(superficie ÷ m² de terreno por unidad, frente ÷ ancho por unidad); multifamiliar (solo si la zona lo admite) = densidad × superficie ÷ 10.000 ÷ 4 personas (en Rm4: superficie ÷ 150).
- **Unidades con aprobación** (O.T. o Urbanización Especial): loteo con calle interna (≥ 5.000 m², se pierde 25% en calle), agrupadas con acceso común (superficie ÷ m² por unidad), Urbanización Especial (≥ 1 ha, densidad UE).
- **Frente**: el mayor entre el del catastro de ARBA (suma de los lados FRENTE de la parcela, así una esquina o un lote pasante suman las dos calles) y el que dice el aviso. Sin frente se calcula solo con la superficie y el mail lo avisa.
- **Oportunidad multifamiliar**: zona que admite multifamiliar, m² construibles (superficie × FOT) > 1300 **y** incidencia (precio USD ÷ m² construibles) < 400 USD/m². En Rma5 y Cma4 el FOT es 1,8 (el máximo, que exige cloaca; se marca), como la densidad potencial.
- **Oportunidad loteo / agrupadas**: 4 lotes o casas por derecho o más (no cuenta departamentos, que tienen su propia vía) **y** USD por unidad ≤ 0,6 × valor de un lote chico = mediana USD/m² de lotes de 150–600 m² de la localidad (con menos de 5, la del partido) × m² de terreno por unidad.
- **Gran predio**: 3.000 m² o más en zona con vivienda; se reporta siempre en su sección, a cualquier precio.
- **Casi-oportunidad** (se reporta aparte, no se alerta como hit): multifamiliar con incidencia entre 400 y 500; multifamiliar en zona "condicional" (Rm1, Cm1, Cmb1, Rmb4…) con incidencia < 400; loteo que solo cierra con las unidades con aprobación.
- Cada vía se evalúa en la zona más favorable cerca del punto (mismo radio que el FOT: 30 m, o 150 m si no cae en zona con FOT). Las zonas sin vivienda (CE1, IE, Ec, E, DUP1, IP, Rma, Ru, AR) no dan producto.
- Cada hit lleva sus flags (incentivos y trampas del C.O.U. con su artículo) y una línea de checklist manual: radio con parcela especial, prolongación de calles, forestación, predio interno, pulmón de manzana, barranca.
- Tipologías incluidas: terreno/lote, casa, quinta, galpón, edificio en block.
- Tipologías excluidas: PH, departamento, oficina, local, cochera, cualquier unidad funcional. (Un PH sobre lote grande da incidencia falsa bajísima.)
- Se valora por lo construible según código, no por lo edificado hoy.
- Precisión: se aceptan errores. Priorizar no perder oportunidades (falsos negativos) sobre evitar falsos positivos, porque cada hit se verifica a mano.

## Stack (deliberadamente simple)
- Python 3.11+ (en la PC de Gonzalo está 3.14), un solo repo, sin frontend, sin base de datos.
- Avisos: **scraper propio** con `requests` sobre las páginas de resultados de Zonaprop, Argenprop y Mercado Libre (cada página de resultados ya trae precio, superficie y coordenadas de ~30 avisos). **Sin Apify ni ningún servicio pago de scraping, y sin respaldo**: Gonzalo no quiere cuenta de Apify.
- Geografía: `shapely` + GeoJSON en disco (no PostGIS).
- Histórico: Google Sheet vía `gspread` con service account.
- Mail: Gmail SMTP con contraseña de aplicación.
- Ejecución: **en la PC de Gonzalo con el Programador de tareas de Windows**, no en GitHub Actions (Cloudflare de los portales suele bloquear IPs de datacenter; desde la IP de la casa funciona). La PC está prendida de lunes a viernes de 10 a 18: la tarea corre una vez por semana en ese horario (por defecto lunes 10:30) y, si se perdió porque la PC estaba apagada, corre apenas se prenda.
- Secretos en `C:\Users\ZN - GF\Desktop\Scouting\` (`.env` + JSON de la service account), fuera de la carpeta de Google Drive; la ruta está en `config.yaml` (`archivos_secretos`). Nunca en el código ni en la carpeta del proyecto.
- Tráfico a los portales: bajo y espaciado (una corrida semanal, pausa entre páginas, sin paralelismo).

## Estructura
```
data/zonas_san_isidro.geojson   # polígonos de zonificación en EPSG:4326
data/fot_por_zona.csv           # zona, FOT, FOS, altura_max, fuente, notas (regla de Fase 2)
data/normativa_zonas.csv        # Fase 4: normativa por zona del C.O.U. T.O. 2022 (productos, densidades, parcela mínima, flags)
data/cache_catastro.json        # Fase 4: parcela de ARBA encontrada para cada aviso (se consulta una sola vez)
data/cotizacion_dolar.json      # última cotización del dólar MEP que dio la API (respaldo si no responde)
data/barrios_san_isidro.geojson # centroides/polígonos de barrios (fallback de ubicación)
data/fuentes/                   # plano PDF 2022 y capa UrbaSIG 2021 (origen de la zonificación)
docs/Zonificacion_San_Isidro_COU2022_v2.xlsx  # origen de normativa_zonas.csv; pestaña "Calculadora" para verificar hits
tools/             # scripts de Fase 0 (vectorización del plano, mapa de control) y de Fase 4 (backtest, Calculadora)
src/fetch.py       # scraper propio: baja páginas de resultados de cada portal
src/normalize.py   # precio USD, superficie, tipología, frente/fondo del texto, descartes
src/locate.py      # coordenadas → zona → FOT
src/evaluate.py    # cálculo e incidencia, unidades por producto (Fase 4), clasificación
src/comparables.py # Fase 4: valor de un lote chico por localidad
src/catastro.py    # Fase 4: parcela real del aviso en el catastro de ARBA (frente, superficie, partida)
src/flags.py       # Fase 4: incentivos y trampas del C.O.U., cada uno con su artículo
src/dedupe.py      # deduplicación entre portales
src/store.py       # Google Sheet
src/notify.py      # mail
src/main.py        # orquesta todo
config.yaml        # umbrales, URLs de búsqueda por portal, parámetros
runs/<fecha>/      # crudo bajado + resultado.csv de cada corrida (excluido de git)
```

## Convenciones
- Cálculos explícitos: guardar en la Sheet cada valor intermedio (superficie usada, FOT usado, fuente del FOT, m² construibles, incidencia).
- Cada aviso lleva un `flag_confianza`: `exacta` | `geocodificada` | `aproximada_barrio`.
- Umbrales y parámetros en `config.yaml`, nunca hardcodeados.
- Idioma de código: inglés. Idioma de columnas de la Sheet y del mail: español.
- Trabajar por fases (archivos PROMPT_FASE_N.md). No avanzar de fase sin que la anterior esté validada por Gonzalo.
- Salud del scraper: si un portal devuelve 0 avisos, una página no se puede interpretar o hay señales de bloqueo, eso se reporta como **falla** (en consola y en la línea roja del mail), nunca como "semana sin novedades".
- API del dólar (avisos en pesos): se reintenta (`normalizacion.dolar_intentos`, con pausa creciente `dolar_pausa_s`). Si igual no responde, se usa la última cotización guardada en `data/cotizacion_dolar.json` si tiene hasta `dolar_respaldo_max_dias` de antigüedad (cada aviso lleva la alerta `cotizacion_guardada (fecha)`); si no hay, los avisos en pesos se descartan como `sin_cotizacion_dolar`. En los dos casos sale como falla ("dólar MEP") en la línea roja del mail y en la pestaña corridas, y nunca corta la corrida.

## Decisiones que prevalecen sobre los PROMPT_FASE_N.md
- Donde un prompt diga "actor de Apify", usar el scraper propio de ese portal (misma salida: esquema normalizado común).
- Fase 2, paso 5 (GitHub Actions): reemplazado por una tarea del Programador de tareas de Windows (ver Stack). Si la corrida falla, igual intenta mandar el mail avisando el error.
- Fase 2, formato condicional de la Sheet: usar los umbrales vigentes de `config.yaml` (verde < 400, amarillo 400–500), no los 200/250 originales.
- Fase 3, punto 6 (costo de Apify): no aplica; en su lugar reportar corridas fallidas o bloqueadas por portal.
- Zonificación: el GIS municipal no responde; la capa sale de vectorizar el plano PDF 2022 (Fase 0). FOT usado = el más alto de las zonas a ≤ 30 m del punto (o ≤ 150 m si el punto no cae en ninguna zona o cae en una sin FOT), por el error de ubicación.
- Avisos sin altura (Fase 1, decidido por Gonzalo): en vez del FOT máximo de toda la localidad, se usa el máximo de las zonas que toca la calle informada (recortada a la localidad si el portal la da) o el de la esquina si informa dos calles (`data/calles_san_isidro.geojson`, de OpenStreetMap). Solo si no hay calle identificable se usa la localidad. Siguen con `flag_confianza = aproximada_barrio`, y en el mail y la Sheet van en un bloque aparte "Sin dirección — revisar", debajo de las oportunidades con dirección.
- Control de datos (no es regla de negocio): superficie con precio < USD 50/m² de terreno se descarta como `superficie_implausible`; precio < USD 10.000 se trata como "consultar". Ambos valores en `config.yaml`.
- Zonaprop: pide un desafío de navegador desde la página 10 de cualquier búsqueda; las búsquedas grandes se recorren por tramos de precio.
- Argenprop: deshabilitado. Responde con un desafío anti-bot (AWS WAF) aun a una consulta cada 45 s; no se intenta sortearlo.
- Fase 4 activa desde el 28/09/2026 (`productos.activo` en `config.yaml`; en `false` vuelve exactamente a la regla de Fase 2). `python tools/backtest_fase4.py` compara las dos reglas sobre crudos ya bajados (salida en `runs/backtest_fase4/`, con los 10 casos pasados por la Calculadora del Excel vía `tools/calculadora_excel.ps1`). Decisiones de Gonzalo: umbral de loteo 0,6; sin comparables en la localidad se usa la mediana del partido (no un monto fijo por unidad); el umbral multifamiliar es el vigente de `config.yaml` (400/500), no los 200 del prompt. En el mail se mantienen "Bajas de precio" y "Sin dirección — revisar" además del orden del prompt.
- Catastro (Fase 4, Paso 2): el GIS municipal sigue caído; el frente sale del WFS público de ARBA (`idera:Parcela` y `idera:Lado_Catastral`). Emparejamiento aviso → parcela calibrado con 37 avisos que dicen su frente: parcela (o hasta 3 linderas) a ≤ 10 m del pin con superficie ±5% (±3% si son varias). Con el pin más lejos suele ser otro lote, así que se deja el frente del texto. Si ARBA no responde se reporta como falla en la línea roja del mail. Si el mismo lote tiene varias publicaciones, el frente encontrado para una sirve para las otras.
- Comparables: la búsqueda extra de lotes chicos (150–400 m²) está activa en Mercado Libre (4 páginas, sin fichas). La de Zonaprop falta: probar el formato de URL con superficie máxima (1–2 consultas) después de una corrida semanal, nunca antes, para no arriesgar un bloqueo.
- Mercado Libre: la API pública ahora exige login, así que se leen las páginas de resultados; superficie y coordenadas salen de la ficha, abierta una vez por aviso y cacheada en `data/cache_mercadolibre.json`. Sus pines dentro del partido son tan buenos como los de Zonaprop (603 inmuebles publicados en ambos: mediana 5 m, 87% a menos de 100 m) y se toman como `exacta`. Excepción: pin afuera del partido a menos de 1,5 km con localidad de San Isidro en el aviso = error de carga, se ubica por calle/localidad. En la deduplicación, además de la regla de 150 m, misma calle + precio y superficie ±5% a menos de 3 km cuenta como el mismo inmueble (cubre el ~10% de pares con pines más separados).
- Arreglos del 13/11/2026 (salud y bloqueos; respaldo de los originales en `runs/_respaldo_pre_arreglos_2026-11-13/`):
  - Salud en dos niveles: `errores` (falla, línea roja del mail) y `avisos_menores` (solo en `resumen.txt` y `salud.json`). Son avisos menores: avisos repetidos por el portal dentro de una búsqueda, una búsqueda bloqueada que se recuperó al final, y fichas sueltas de Mercado Libre que no abren (hasta `errores_fichas_max`; más que eso, o un bloqueo abriendo fichas, es falla).
  - Cobertura de Zonaprop: se compara con las filas recibidas, no con los `postingId` únicos (el total del portal cuenta los destacados repetidos entre páginas; eso daba "50 de 54" como falla falsa).
  - Bloqueos (403/429/desafío): un solo reintento (`reintentos_bloqueo`); si sigue, la búsqueda pasa al final de la corrida y se reintenta una vez tras `espera_recupero_s` (25 min). El 19/10 el bloqueo de terrenos se destrabó ~40 min después del primer 403.
  - Mercado Libre: los avisos patrocinados traen una URL de clics de publicidad (`click1.../brand_ads/...`). Nunca se abre (contaría como clic al anuncio): se usa la URL canónica `https://articulo.mercadolibre.com.ar/MLA-<n>`.
  - `main.py` impide que Windows suspenda la PC mientras dura la corrida (`SetThreadExecutionState`). `correr_semanal.ps1` usa el lanzador `py -3` si la ruta fija de Python ya no existe.
- Repositorio (13/11/2026, Fase A del escalado): el código vive en git en `C:\Users\ZN - GF\Proyectos\scouting-zanara`, fuera de Google Drive (Drive rompe los archivos internos de `.git`), con copia en un GitHub privado. La tarea programada corre desde ahí. La carpeta vieja de Drive (`G:\Mi unidad\01 - PROYECTOS CLAUDE\scouting-san-isidro`) queda como archivo con las corridas hasta el 09/11: no editarla. Fuera de git: `runs/`, cachés de `data/` y secretos. Todo cambio va en un commit.

## Multi-municipio (14/11/2026, rama `dev`; detalle en "RESUMEN - Escalado a CABA Tigre y San Fernando.md")
- `config.yaml` sigue siendo San Isidro. Cada otro municipio tiene `municipios/<slug>/municipio.yaml`, que se superpone a `config.yaml` (los dicts se mezclan; una clave con `!` al final reemplaza). `python -m src.main --municipio <slug>`; `correr_semanal.ps1 -Municipio <slug>`. Corridas en `runs/<slug>/<fecha>`.
- Motores: `zonas` (capa de zonas + `normativa_zonas.csv`: San Isidro, Tigre, San Fernando) y `caba` (`src/motor_caba.py`: parcela y edificabilidad de Ciudad 3D, plusvalía Ley 6062).
- Tigre y San Fernando: zonas y normativa de UrbaSIG (Provincia) con `tools/municipio_pba.py`; localidades y calles de OSM. Cada uno documenta sus decisiones en `municipios/<slug>/NORMATIVA.md` (a validar por Gonzalo). Mapa de control: `tools/mapa_municipio.py <slug>`.
- Municipios nuevos en modo prueba (`municipio.en_prueba: true`): mail con asunto "[EN PRUEBA]" solo a `mail.para` (o la primera dirección de `MAIL_TO`), sin Sheet propia (`sheet.id` vacío = `--sin-sheet`).
- Volumen de búsquedas: `tools/medir_busquedas.py <slug>` abre solo la primera página de cada búsqueda. Nunca antes de una corrida semanal.
- Tests: `python -m pytest` (golden tests de San Isidro con crudos del 09/11 y 02/11, scraper, municipios). Todo cambio tiene que pasarlos; si un cambio de regla pedido por Gonzalo cambia resultados, `pytest tests/test_golden.py --regenerar` y revisar el diff.

## Fase 5 (en preparación, `margen.activo: false`)
Plan aprobado por Gonzalo el 15/11/2026: `PLAN - Fase 5 Valor de venta y margen.md`. Costos en `config.yaml` (`margen:`): 1.800 USD por m² vendible para multifamiliar y casas, 30 USD por m² bruto para loteo de barrio cerrado. `src/registro.py` (registro de comparables en `data/registro_comparables*.csv`, local), `src/margin.py` (valor de la zona y margen), `tools/backtest_fase5.py` (offline, sobre corridas guardadas). Con `activo: false` la corrida no cambia; la regla vigente sigue siendo la incidencia hasta que Gonzalo vea el backtest.

## Descarga incremental (Fase C, Gonzalo 16/11/2026)
Para municipios que no entran en una corrida. Medición del 16/11: CABA da 251 páginas de Zonaprop y 92 de Mercado Libre (más ~4.700 fichas la primera vez). `incremental.activo` (solo CABA; San Isidro sigue con descarga completa). `fetch_zonaprop_incremental` guarda un stock en `data/incremental_zonaprop_<slug>.json.gz`; cada corrida gasta hasta `paginas_por_corrida` (45): primero novedades (orden "más recientes", `sufijo_recientes`, **sin probar**) y después sigue el barrido por tramos de precio donde quedó. Al cerrar un barrido, lo que no apareció se da de baja. La primera descarga completa lleva ~6 corridas y es un aviso menor ("primera descarga en curso"); un bloqueo es falla, pero el avance queda guardado. Mercado Libre: `max_detalles_por_corrida: 600` en CABA reparte las fichas en varias corridas.
