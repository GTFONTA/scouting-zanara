# Resumen del proyecto y del nivel — Scouting San Isidro (ZANARA)

Escrito el 15/10/2026 a partir de: código (`src/`, `tools/`), `CLAUDE.md`, los cinco `PROMPT_FASE_N.md`, `config.yaml`, las corridas en `runs/` y los transcripts de las 5 sesiones de Claude Code guardados en `~/.claude/projects/...`.

**Aclaración importante:** el proyecto **no es un repositorio git** (no hay `.git`). No existe historial de commits. Todo lo que digo sobre la evolución del proyecto sale de los transcripts de las sesiones y de las fechas de los archivos, no de git.

---

## 1. Qué hace y con qué está hecho

Un script en Python que corre una vez por semana en la PC de Gonzalo. Hace lo siguiente:
1. Baja los avisos de venta de terrenos, casas, galpones y edificios de más de 400 m² en San Isidro, de Zonaprop y Mercado Libre.
2. Ubica cada uno en el plano de zonificación.
3. Calcula qué se puede construir según el C.O.U. 2022: m² FOT, departamentos, casas agrupadas, lotes y Urbanización Especial.
4. Lo clasifica como oportunidad, casi-oportunidad, gran predio o descartado.
5. Guarda el histórico en una Google Sheet y manda un mail.

| Pieza | Qué se usa |
|---|---|
| Lenguaje | Python 3.14 (unas 2.500 líneas en `src/` y 900 en `tools/`), más 2 scripts de PowerShell |
| Librerías | `requests`, `pyyaml`, `shapely`, `pyproj`, `gspread`, `google-auth`. Sin frameworks. |
| Base de datos | Ninguna. El histórico va a una Google Sheet. Hay cachés en JSON (`data/cache_*.json`) y crudos en `runs/`. |
| Fuentes de datos | Scraping HTML propio de Zonaprop y Mercado Libre. WFS público de ARBA para el catastro. dolarapi.com para el dólar MEP. OpenStreetMap para las calles (lo bajó una sola vez `tools/calles_osm.py`). |
| Zonificación | Capa vectorizada a mano a partir del plano PDF 2022 (`tools/fase0_vectorizar_plano.py`), porque el GIS municipal no responde |
| Normativa | `data/normativa_zonas.csv`, sacada del Excel `docs/Zonificacion_San_Isidro_COU2022_v2.xlsx` |
| Mail | Gmail SMTP con contraseña de aplicación |
| Deploy | Programador de tareas de Windows (`correr_semanal.ps1`, los lunes a las 10:30). Sin nube, sin CI y sin contenedores. |
| Tests | **No hay.** Hay un backtest (`tools/backtest_fase4.py`) y una comparación contra la Calculadora del Excel (`tools/calculadora_excel.ps1`), pero no son tests automáticos. |

## 2. Arquitectura

Es un pipeline lineal que orquesta `src/main.py`:

```
fetch.py ──► normalize.py ──► locate.py ──► catastro.py ──► comparables.py ──► evaluate.py + flags.py ──► dedupe.py ──► store.py ──► notify.py
(HTML de     (USD, m², tipo,   (pin → zona,   (frente real     (USD/m² de lote    (unidades por         (mismo inmueble  (Sheet)       (mail)
 portales)    frente del        FOT; calle o   por ARBA WFS)    chico por          producto, vía,        en varios
              texto, descartes) localidad)                      localidad)         flags del C.O.U.)     portales)
```

- `config.yaml` concentra los umbrales, las URLs de búsqueda, las pausas y los radios. `src/config.py` lo carga y lee los secretos de `~/Desktop/Scouting/.env`.
- `data/` tiene la geografía (zonas, barrios, calles), las tablas normativas y las cachés.
- `runs/<fecha>/` guarda de cada corrida el crudo bajado, `resultado.csv`, `resumen.txt` y `salud.json`. `python -m src.main --reusar runs/<fecha>` reprocesa sin volver a consultar los portales, y eso es lo que permite hacer el backtest.
- `productos.activo` en `config.yaml` cambia entre la regla de Fase 2 (FOT e incidencia) y la de Fase 4 (por producto). Las dos conviven en `evaluate.py`.
- `tools/` tiene scripts que se corren una vez: la vectorización del plano, el mapa de control, las calles de OSM, el backtest y la Calculadora.

El diseño es coherente y está bien separado. Lo que más se repite es `main.py`, que mezcla orquestación, columnas de salida y lógica del catastro.

## 3. Funciones de Claude Code: cuáles se usaron

| Función | ¿Se usó? | Evidencia |
|---|---|---|
| **CLAUDE.md** | **Sí, y mucho.** Es el centro del proyecto. | Tiene 12 KB con reglas de negocio, stack y "decisiones que prevalecen sobre los PROMPT". Claude lo editó unas 15 veces, casi siempre a pedido de Gonzalo ("actualizá Claude.md con esa información"). |
| **Archivos PROMPT por fases** | Sí | `PROMPT_FASE_0..4.md`. Se ejecutaban con mensajes como "Ejecutá PROMPT_FASE_0.md" o "Iniciar fase 4". |
| **Memoria** | Sí, poco | 3 archivos. Uno lo pidió Gonzalo (hablar en rioplatense) y los otros dos los guardó Claude. |
| **Sesiones en paralelo** | Una vez | El arreglo del dólar MEP (27/09) se lanzó como sesión aparte. Lo propuso Claude y Gonzalo lo arrancó. |
| **Comandos en segundo plano** | Sí | 7 corridas largas: descargas, espera a que Zonaprop desbloquee y la corrida completa. |
| **Navegador integrado (MCP)** | Marginal | Unas 8 llamadas en Fase 0, para el mapa de control (`.claude/launch.json` sirve `data/` en el puerto 8765). |
| **Plan mode** | **No** | No hay ninguna llamada en los transcripts. Las fases funcionaron como plan, pero escrito a mano en los PROMPT. |
| **Subagents** (herramienta Agent) | **No** | |
| **Skills** | **No** | No hay skills propias ni invocadas. |
| **Hooks** | **No** | `.claude/` tiene solo `launch.json`, y `~/.claude/settings.json` no define hooks. |
| **Slash commands** | **No** | Ningún mensaje del usuario empieza con `/`. |
| **MCP servers propios** | **No** | Solo se usaron los que trae la app (navegador y sesiones). |
| **GitHub / git** | **No** | No hay repo, commits ni PRs. La Fase 2 preveía GitHub Actions y se reemplazó por el Programador de tareas. |

En resumen: un uso de Claude Code "conversacional + CLAUDE.md". No se aprovechó nada de automatización ni de control de versiones.

## 4. Señales del nivel del usuario

**Hay que distinguir dos cosas.** En el dominio (desarrollo inmobiliario y normativa urbana) Gonzalo es claramente experto. En lo técnico (software) delega casi todo. Los transcripts muestran que nunca editó código él mismo.

### Decisiones que tomó él (constan en los transcripts)
- **El diseño por fases con validación entre fases**: "no avanzar sin mi OK", backtest antes de tocar producción, 10 casos pasados por la Calculadora del Excel. Los PROMPT se crearon el 25/09 a las 00:32, antes de la primera sesión, o sea fuera de Claude Code. **No puedo saber** si los escribió solo o con ayuda de un chat de IA. Por el estilo y por la referencia a `claude/normativa_zonas_san_isidro.csv`, probablemente se armaron en un proyecto de claude.ai.
- **El conocimiento normativo**: el Excel del C.O.U. 2022 con las pestañas "Productos ZANARA", "Incentivos y trampas" y "Calculadora", y las reglas de Fase 4 (frente propio de 5 m, parcela mínima, UE de 1 ha). Es la parte más valiosa del proyecto y es suya.
- **Umbrales**: subió la incidencia de 200 a **400 USD/m²**, puso la banda de casi en **400–500**, el ratio de loteo en **0,6** y la mediana del partido cuando faltan comparables.
- **Validación manual**: pasó 10 a 15 links reales de Zonaprop y aprobó la tabla ("están todas bien, vamos a la fase 1").
- **Restricciones de stack**: "No me quiero hacer una cuenta de Apify… no quiero tener respaldo", y correr en su PC de lunes a viernes de 10 a 18.
- **Fallback por barrio**: pidió que se lo explicaran mejor antes de decidir y eligió "B + C", que era la recomendación de Claude.

### Decisiones que tomó Claude (y Gonzalo aprobó)
Casi toda la arquitectura técnica: el scraper propio en vez de Apify (Gonzalo preguntó si se podía; el diseño fue de Claude), vectorizar el PDF, recorrer Zonaprop por tramos de precio, usar el WFS de ARBA y su calibración (≤ 10 m, ±5%), Mercado Libre por HTML con caché de fichas, la deduplicación por calle, la caída a la última cotización del dólar, deshabilitar Argenprop y el formato del mail. La respuesta típica de Gonzalo a esas propuestas fue "ok a todo".

### Problemas que hubo que resolver (iteraciones)
| Problema | Iteraciones | Resultado |
|---|---|---|
| GIS municipal inaccesible (Gonzalo tampoco pudo abrirlo desde la PC ni el teléfono) | Se probaron el GIS y UrbaSIG y al final se vectorizó el PDF (6 ediciones del vectorizador) | Resuelto de forma aproximada |
| Zonaprop bloquea desde la página 10 y por volumen (~150 páginas en pocas horas) | Se bloqueó durante el desarrollo (`runs/2026-09-26_parcial_bloqueada`), hubo que esperar consultando cada 5 min y después se armó el recorrido por tramos de precio | Funciona, pero frágil (ver punto 5) |
| API de Mercado Libre con login obligatorio | Se pasó al HTML. Hubo 3 corridas de descarga, una para corregir la paginación | Resuelto |
| Argenprop con AWS WAF | Se probó y se abandonó | **Abandonado** |
| Apify y GitHub Actions (previstos en los PROMPT) | Se descartaron antes de construirlos | **Abandonados** por decisión de Gonzalo y por el bloqueo de IPs de datacenter |
| dolarapi falló por SSL el 27/09 y cortó la corrida entera | Una sesión aparte: reintentos y cotización guardada | Resuelto |
| Regla de Fase 2 reemplazada por la de Fase 4 | Reescritura grande de `evaluate.py`, `notify.py`, `main.py` y `store.py` (unas 120 ediciones en una sesión). Se guardó una copia manual en `runs/_respaldo_pre_fase4_2026-09-27/` porque no había git. | La regla vieja sigue disponible con `activo: false` |
| Corrida del 12/10: la PC se suspendió y Zonaprop dio 403 | Diagnosticado el 13/10. Claude propuso dos arreglos. | **No se aplicaron**: `src/` no cambia desde el 28/09 |

En total, el sistema se construyó en unos 4 días de trabajo intenso (25 al 28/09), en 3 sesiones grandes. En una se llegó al límite de uso.

## 5. Estado real

**Funciona en producción:**
- La tarea programada corrió los tres lunes (28/09, 05/10 y 12/10) y dejó resultados.
- En condiciones normales: unos 1.500 avisos distintos por semana, 34 a 36 oportunidades, 16 casi y 14 grandes predios (`runs/2026-10-05_1047/resumen.txt`).
- Mercado Libre y el catastro de ARBA responden bien.
- El reporte de salud funciona como se diseñó: el 12/10 marcó a Zonaprop como `[FALLA]` en vez de decir "sin novedades".

**Falla o quedó incompleto:**
- **Corrida del 12/10, degradada.** Zonaprop bloqueó 3 de sus 4 búsquedas (entraron 47 avisos contra ~1.530). La PC se suspendió a las 12:07 y el mail salió recién a la noche. Las dos correcciones propuestas (impedir la suspensión durante la corrida y no esperar 30 minutos por búsqueda bloqueada) **están pendientes**. Con la configuración actual, cada búsqueda bloqueada puede tener la corrida parada hasta 30 minutos.
- **Fase 3 (calibración) no empezó.** Pide 4 semanas de datos y hay 3, una de ellas degradada.
- **Comparables de Zonaprop**: la búsqueda de lotes chicos está vacía (`busquedas_zonaprop: []`), a la espera de una prueba que nunca se hizo.
- **Argenprop**: deshabilitado, así que el sistema cubre 2 de los 3 portales previstos.
- **Frente desconocido** en la mayoría de los avisos evaluados: 630 de 925 el 28/09. El catastro solo lo resolvió en 99.
- **No pude verificar** si la Sheet se está poblando bien ni si Gonzalo usa la columna `estado`: no tengo acceso a la Sheet desde acá. Tampoco puedo confirmar que los mails hayan llegado, salvo el primero ("Ya llegó el mail!", 27/09).
- **Algo raro para revisar**: Mercado Libre devolvió exactamente 1.247 avisos el 28/09 y el 05/10, y las "filas crudas" fueron 2.795 las dos semanas aunque Zonaprop cambió de 1.535 a 1.527. Puede ser casualidad, un tope del portal o la caché. No lo pude confirmar.

**Deuda técnica:**
1. **Sin control de versiones.** El código vive en Google Drive. El único respaldo es una copia manual de antes de la Fase 4.
2. **Sin tests automáticos.** Un cambio en las reglas solo se valida corriendo el backtest a mano.
3. **Scraping de HTML.** Si Zonaprop o Mercado Libre cambian su página, se rompe. Se va a reportar como falla, pero hay que arreglarlo a mano.
4. **Dependencia de la PC**: tiene que estar prendida, no suspenderse y salir por la IP de la casa.
5. **La zonificación sale de vectorizar un PDF.** Los bordes de zona tienen error, y por eso existen los radios de 30 y 150 m.
6. **`main.py` y `notify.py` crecieron por acumulación** (20 y 18 ediciones en la sesión de Fase 4).
7. **La ruta de Python está fija** en `correr_semanal.ps1`. Si se actualiza Python, la tarea deja de correr.

## 6. Tres cosas que probablemente no entendés de tu propio proyecto

**1. Las oportunidades salen de sumar varios supuestos optimistas.** Cada uno, por separado, está justificado por "no perder oportunidades", pero se acumulan:
- Para cada vía se usa la **zona más favorable** en 30 m (o 150 m) a la redonda, no la zona del lote.
- En Rma5 y Cma4 se usa el **FOT máximo**, el que exige cloaca.
- Cuando **no se conoce el frente** (alrededor de 2 de cada 3 avisos), las casas y los lotes se calculan solo con la superficie, como si el frente alcanzara siempre.
- Entre el frente del catastro y el del aviso se toma **el mayor**.

Las ~35 oportunidades por semana son entonces un **techo**, no una estimación. Es lo que pediste, pero conviene tenerlo presente al leer el número: un lote que aparece con "8 casas por derecho" puede dar 3 cuando se mira el frente real.

**2. El umbral de loteo y el "valor de un lote chico" son más blandos de lo que parecen.**
- La mediana sale de **precios de publicación** (lo que se pide, no lo que se cobra) de lotes de 150–600 m². La búsqueda extra de lotes chicos es solo de Mercado Libre: la de Zonaprop nunca se activó.
- Cuando una localidad tiene menos de 5 lotes, se usa la mediana de todo el partido, que mezcla Las Lomas con Boulogne.
- El 0,6 se eligió viendo **cuántos hits daba** en el backtest (0,5 → 7, 0,6 → 19, 0,7 → 37), no por un margen de negocio calculado.

O sea, el criterio de loteo está calibrado por volumen de alertas, no por rentabilidad. La Fase 3 es la oportunidad de corregirlo con lo que marques como bueno o malo en la Sheet.

**3. El sistema depende de que Zonaprop "no se dé cuenta", y no tiene margen.**
- El bloqueo no es un error que se arregla una vez: Zonaprop corta por volumen y desde la página 10, y el 12/10 bloqueó igual una corrida de ~57 páginas espaciadas.
- Cualquier corrida manual extra (por ejemplo, probar algo un domingo) aumenta el riesgo de que el lunes falle.
- Cuando falla, Zonaprop es la mitad de la cobertura: esa semana el mail llega con la línea roja y con oportunidades casi solo de Mercado Libre.
- Los arreglos que se propusieron el 13/10 siguen sin hacerse, y no hay plan B si Zonaprop endurece el bloqueo. Descartaste Apify y el respaldo, y Argenprop ya está bloqueado.

Es una decisión válida (costo cero), pero la consecuencia es que **"el mail llegó" no quiere decir "se miró todo el mercado"**. Hay que leer la línea roja cada semana.
