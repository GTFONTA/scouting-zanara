# FASE 4 — Evaluar cada aviso por producto: multifamiliar, agrupadas, loteo y barrio

> **BORRADOR — no ejecutar hasta que Gonzalo lo apruebe y actualice las reglas de negocio de CLAUDE.md.**
> Requisito: Fase 2 funcionando (pipeline semanal, Sheet y mail).

Leé CLAUDE.md. Objetivo: que el sistema deje de medir todo con una sola vara (m² FOT) y evalúe cada aviso por los productos que ZANARA desarrolla: edificio multifamiliar, vivienda agrupada (casas a la calle o con acceso común), loteo abierto y barrio/conjunto (Urbanización Especial). La base normativa es `data/normativa_zonas.csv`, extraído del C.O.U. de San Isidro (T.O. 2022). El detalle legal de cada regla está en el Excel `Zonificacion_San_Isidro_COU2022_v2.xlsx`, pestañas "Productos ZANARA" e "Incentivos y trampas".

## Por qué
- En las zonas de casas a la calle (Art. 1.2.1.14 inc. 1) cada vivienda necesita **acceso directo desde la vía pública y frente propio de 5 m (o 6,50 m)**. El que limita las unidades es el frente, no la superficie. Hoy el sistema no lee el frente.
- En zonas de 1 vivienda por parcela mínima (Rb, Rmb2, etc.) un lote grande se puede convertir en agrupadas (superficie ÷ parcela mínima, Art. 1.2.1.14 inc. 3). Hoy esos lotes no pasan el filtro de m² construibles aunque sirvan para loteo.
- Los predios de ≥1 ha pueden ir como Urbanización Especial (Art. 1.2.1.1), con mucha más densidad en Rm, Rmb, Cm e I (300 hab/ha).
- La incidencia en USD/m² FOT no sirve para loteo: para loteo la métrica correcta es USD por unidad contra el precio de mercado de un lote chico en el mismo barrio.

## Paso 1 — Tabla normativa
- Reemplazar `data/fot_por_zona.csv` por `data/normativa_zonas.csv` (adjunto en el proyecto como `claude/normativa_zonas_san_isidro.csv`). Conserva `zona, fot, fos, altura_max`, así que `locate.py` sigue funcionando.
- Columnas nuevas: `multifamiliar, regla_unidades, m2_terreno_por_unidad, ancho_min_unidad, sup_propia_min_unidad, acceso_directo_requerido, subdiv_ancho_min, subdiv_sup_min, densidad_neta, densidad_neta_potencial, densidad_ue, flags`.
- Cruzar los códigos contra los nombres de zona de la capa GIS (como en Fase 0) y listarme los que no matchean. Ojo con `Rma2-AC`, `Ca1-AC`, `CR1-A/B`.

## Paso 2 — Frente del lote (`normalize.py`)
- Extraer frente y fondo del título y la descripción: patrones tipo `12 x 40`, `12x40`, `12,5 × 38`, `frente 20 m`, `20 mts de frente`, `fondo 45`. Si hay superficie y solo fondo, frente = superficie ÷ fondo.
- Campos nuevos: `frente_m, fondo_m, frente_fuente` (`aviso` | `calculado` | `desconocido`).
- Reportame en qué % de los avisos se pudo sacar el frente.
- **Investigación, sin construir:** revisar si el ArcGIS de San Isidro publica una capa de parcelas catastrales. Si existe, mostrame campos y un ejemplo. Con esa capa el frente y la superficie salen del polígono real y no del aviso. No avanzar sin mi OK.

## Paso 3 — Evaluación por producto (`evaluate.py`)
Para cada aviso, con S = superficie y F = frente (vacío si es desconocido):
- `lotes_frente_propio` = mín(S ÷ subdiv_sup_min, F ÷ subdiv_ancho_min)
- `lotes_calle_interna` = S × (1 − pct_calle) ÷ subdiv_sup_min, solo si S ≥ `sup_min_loteo_calle`
- `agrupadas_calle` = mín(S ÷ m2_terreno_por_unidad, F ÷ ancho_min_unidad)
- `agrupadas_acceso_comun` = S ÷ m2_terreno_por_unidad (requiere O.T.)
- `multifamiliar_unidades` = densidad × S ÷ 10.000 ÷ personas_por_unidad (usar `densidad_neta_potencial` si existe y marcar `requiere_cloaca`), o S ÷ m2_terreno_por_unidad si la regla es "N = sup/150"
- `ue_unidades` = densidad_ue × S ÷ 10.000 ÷ personas_por_unidad, solo si S ≥ 10.000
- `unidades_por_derecho` = máx(lotes_frente_propio, agrupadas_calle, multifamiliar_unidades)
- `unidades_con_aprobacion` = máx(unidades_por_derecho, lotes_calle_interna, agrupadas_acceso_comun, ue_unidades)
- `usd_por_unidad_derecho`, `usd_por_unidad_aprobacion`, `mejor_producto`
- Todos los resultados parciales se redondean hacia abajo (número entero).
- Si F es desconocido: calcular con la superficie sola y marcar `frente_desconocido` (criterio de no perder oportunidades). En el mail va con aviso.
- Todos los parámetros en `config.yaml`: `pct_calle` (0,25), `sup_min_loteo_calle` (5.000), `sup_min_ue` (10.000), `personas_por_unidad` (4), `unidades_min` (4).

## Paso 4 — Comparables de lotes chicos (`comparables.py`)
- Objetivo: estimar a cuánto se vende un lote chico en cada barrio, para comparar el USD por unidad de un loteo.
- Fuente: los mismos portales, tipología lote, superficie 150–600 m², San Isidro. **Ojo:** hoy el prefiltro de Apify corta en `superficie_min_prefiltro` (~433 m²), así que hace falta una búsqueda aparte para lotes chicos. Estimame el costo extra de Apify antes de activarla.
- Guardar en una pestaña `comparables` de la Sheet (acumulado de 12 semanas) y calcular, por barrio, la mediana de USD/m² de lote chico (mínimo 5 avisos; si no, `sin_comparables`).
- `valor_lote_estimado` = mediana USD/m² × m2_terreno_por_unidad; `ratio_compra_reventa` = usd_por_unidad_derecho ÷ valor_lote_estimado.

## Paso 5 — Flags de incentivos y trampas (`flags.py`)
Automatizar solo los que se pueden detectar con datos que ya tenemos. Cada flag lleva el artículo:
- `galpon_no_conforme` (tipología galpón/fábrica/depósito fuera de zona I): hasta +30% (Art. 1.2.4.3 C) + `pasivo_ambiental` (Art. 1.2.2.15 inc. 10).
- `gran_predio_3000` (Art. 1.2.1.19), `manzana_7400` (Arts. 1.2.3.1 y 1.2.1.14 inc. 2), `ue_10000` (Art. 1.2.1.1).
- `frentista_via_rapida`: Rb/Rmb2 con dirección en Sucre, Colectora, Panamericana, Camino Real o Patagonia → hasta +100% agrupadas (Art. 1.2.1.16).
- `lindero_zona_c_o_i`: punto a menos de 30 m de un polígono C* o I* → Arts. 1.2.1.16 y 1.2.1.20 a.
- `borde_de_zona`: punto a menos de 25 m del límite de su zona → posible predio en dos zonas (Art. 1.2.2.7).
- Los que vienen de la tabla (`requiere_cloaca_para_max`, `barranca`, `cota_ign`, `relleno_sanitario`, `patrimonial`).

## Paso 6 — Clasificación
Una oportunidad puede calificar por más de un camino. Se guarda el camino (`via`):
- **Multifamiliar**: la regla actual (m² construibles > 1.300 e incidencia < 200 USD/m²), solo si la zona admite multifamiliar.
- **Loteo / agrupadas**: `unidades_por_derecho ≥ unidades_min` y `ratio_compra_reventa ≤ UMBRAL_LOTEO` **(pendiente de definir por Gonzalo)**. Sin comparables: `usd_por_unidad_derecho ≤ UMBRAL_USD_UNIDAD` **(pendiente)**.
- **Gran predio** (≥ 3.000 m² en zona con vivienda): se reporta siempre en su sección, con unidades por derecho y con UE, sin filtro de precio. Son pocos y cada uno merece una mirada.
- **Solo con aprobación**: cumple el umbral únicamente con `unidades_con_aprobacion`. Va como casi-oportunidad, no como hit.

## Paso 7 — Sheet y mail
- Sheet `oportunidades`: sumar `via, mejor_producto, frente_m, frente_fuente, unidades_por_derecho, unidades_con_aprobacion, usd_por_unidad_derecho, valor_lote_estimado, ratio_compra_reventa, flags`.
- Mail, en este orden: salud → oportunidades multifamiliar → oportunidades loteo/agrupadas (ordenadas por `usd_por_unidad_derecho`) → grandes predios → casi-oportunidades → resumen.
- Cada hit lleva una línea de checklist manual con lo que el sistema no ve: radio con parcela especial, prolongación de calles, forestación, predio interno, pulmón de manzana, barranca.

## Paso 8 — Validación
- Correr el pipeline nuevo sobre los crudos de las últimas corridas (`runs/<fecha>/raw_*.json`), sin gastar Apify.
- Mostrame: hits nuevos que aparecen, hits viejos que cambian o desaparecen, y 10 casos calculados a mano con la pestaña "Calculadora" del Excel para comparar.
- No cambiar el mail en producción hasta que yo valide esa tabla.

## Entregable
`normativa_zonas.csv` integrado, frente extraído, evaluación por producto, flags, backtest con la tabla de comparación y un resumen de 5 líneas de qué cambió.
