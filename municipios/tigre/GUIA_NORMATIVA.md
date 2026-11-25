# Tigre — guía de normativa para evaluar un lote

Lectura rápida: qué limita lo que se construye en un lote de Tigre, cómo se calcula según la zona y el lote, y qué buscar que el resto no ve. Estudio del 19/11/2026; revisión exhaustiva del 24/11/2026 en la sección 10 (agrupadas, subdivisión, cesiones, agua, plusvalías, Nordelta y decisiones pendientes).

**Estado:** desde el 19/11/2026 el motor de Tigre aplica las decisiones de Gonzalo de la sección 8: planillas por encima de UrbaSIG, alturas de la Ord. 4448 por sector, tope por densidad y señal de proyecto aprobado. La sección 7 cuenta qué cambió y qué quedó afuera. El 24/11/2026 se sumaron las 7 decisiones de la sección 10.7; la sección 10.9 dice qué hace el motor con ellas.

**Fuentes** (PDFs en Drive, `01 - PROYECTOS CLAUDE/scouting-tigre/normativa/`):
- **Código de Zonificación**, Ordenanza 1894/96, texto ordenado con las Ord. 1996/97 y 3344/13.
- **Planillas de indicadores por zona** de tigre.gob.ar (30 planillas). Citan las Ord. 1894/96, 1996/97, 2501/03, 3564/17 y 3776/21.
- **Decreto 165/08** (convalidado por la Ord. 2892/08 y ampliado por la 3324/12).
- **Ordenanza 4448/26**, de límites de altura y perfiles urbanos: promulgada por el Decreto 584 del 05/05/2026 y publicada en el Boletín Oficial 1065 del 07/05/2026. El Boletín dice que se sancionó "el 28 de mayo de 2026", fecha posterior a la promulgación: parece un error de tipeo.
- **Plano de zonificación** (AutoCAD, marzo de 2023).

---

## 1. Conclusiones

1. **En Tigre el FOT sí es un tope** (Ley 8.912 y Código 1894/96), a diferencia de CABA. Pero rara vez es lo único que manda. Para "usar todo el FOT" se tienen que cumplir **las cuatro** condiciones a la vez:
   - **Altura:** FOT ≤ FOS efectivo × niveles. Los niveles salen de la **Ord. 4448/26**, que fija "PB + N" por sector y prevalece sobre el Código en todo lo de alturas (art. 1).
   - **Densidad:** con 2 personas por dormitorio (art. 13 del Código), la densidad de la zona tiene que alcanzar para departamentos del tamaño que se quiere vender.
   - **Servicios:** casi todas las zonas dan el FOT y la densidad altos **solo con agua y cloaca por red**. Sin eso hay FOT y densidad bajos y a veces una sola vivienda por lote.
   - **Cocheras:** **1 por unidad, dentro del lote**, en todo el partido (Ord. 4448, art. 12 e). Los pisos de cocheras sobre la PB no cuentan para el FOT ni para la altura.
2. **Con los FOT de base, la altura de la 4448 casi nunca es la que corta**: con FOS 0,6 alcanza PB+3 para un FOT 2,4. **Corta los premios**: el motor usa FOT 3,6, 3,75 o 4,5, y eso pide PB+5 a PB+7 con FOS pleno.
3. **Donde corta la densidad:** en **C5** (FOT 1,8 con 400 hab/ha) da unos 45 m² cubiertos por habitante, el doble de lo que ocupa un departamento típico. Ahí no se usa todo el FOT con unidades chicas. En C6, R8, RM1, R2, R3 y R4 queda justo (unos 30 m² por habitante).
4. **El FOT residencial de C2a, C2b y Tc es 2,50, no 3,00.** El 3,00 es para el uso comercial dominante, y el motor usa 3,00 con premio a 4,5.
5. **R2, R3 y R5 admiten multifamiliar con agua y cloaca** (densidad 400, hasta 12 m con PB libre, Decreto 1000/16). El motor los trata como "una vivienda cada X m²". Es tierra barata en Pacheco, El Talar, Don Torcuato y Benavídez, pero no en R2c, R2d ni "La Bota", donde la 4448 lo prohíbe.

## 2. Indicadores por zona (planillas de tigre.gob.ar)

FOT y densidad "con infra" significa con agua y cloaca por red. Retiros: F = frente, L = largo del lote, Lat = lateral.

| Zona | Lote mín. (frente × fondo / sup.) | FOS | FOT | Densidad (hab/ha) | Retiros | Multifamiliar |
|---|---|---|---|---|---|---|
| C1 | 12 × 25 / 300 | 0,6 | 1,2 sin infra · **2,4 con infra** | 150 · **2.000** con infra · 400 con planta de tratamiento | F 0 · fondo (L−15)/2 | Sí, con infra |
| C2 (a, b) | 12 × 25 / 300 | 0,6 | 1,4 · 3,0 comercial · **2,5 residencial** | 150 · **2.000** | F 0 · (L−15)/2 | Sí, con infra |
| C3 | 12 × 25 / 300 | 0,6 | 1,4 · 2,4 | 150 · **800** | F 0 · (L−15)/2 | Sí, con infra |
| C4 (a, b, c) | 12 × 25 / 300 | 0,6 | 1,4 · 2,4 | 150 · **2.000** | F 0 · (L−15)/2 | Sí; sin infra solo dúplex |
| C5 | 15 × 25 / 375 | 0,6 | 1,8 | **400** | (L−15)/2 | Sí |
| C6 | 15 × 25 / 375 | 0,6 | 1,2 | 400 | F 3 · (L−15)/2 | Sí |
| C7 | 30 × 30 / 900 | 0,6 | 1,4 · 2,4 | 1.500 con todos los servicios · 150 solo agua | (L−15)/2 | Sí; sin agua ni cloaca, 1 vivienda. Fondo Hábitat ≥ 10% |
| Tc | 30 × 30 / 900 | 0,6 | 3,0 comercial · **2,5 torre residencial** | 2.000 | Torre: F 5 · (L−20)/2 · Lat H/10 ≥ 4 m · basamento 7 m | Sí (torre con basamento) |
| Tr | 25 × 40 / 1.000 | 0,6 | 2,5 | 2.000 | Igual que Tc | Sí (uso dominante) |
| R6 | 25 × 30 / 750 | 0,6 | 2,4 | 1.000 | (L−15)/2; puede ocupar el fondo hasta dejar 10 m | Sí (uso dominante) |
| R7 | 20 × 30 / 600 | 0,6 | 1,8 | 600 | F 3 · (L−15)/2 · Lat 20% del ancho, mín. 2,5 | Sí |
| R8 | 15 × 30 / 450 | 0,6 | 1,2 | 400 | F 3 · (L−15)/2 · Lat 20%, mín. 2,5 | Sí |
| RM1 | 15 × 30 / 450 | 0,6 | 1,2 | 400 | F 3 · (L−15)/2 · Lat 20%, mín. 2,5 | Sí (complementario) |
| RM2 | 20 × 30 / 600 | 0,6 | 1,2 | 600 con todos los servicios | F 3 · (L−15)/2 · Lat 20% | Con agua y cloaca, hasta PB+6. Fondo Hábitat ≥ 10% |
| R4 | 15 × 30 / 450 | 0,6 | 1,2 | 400 | F 3 · (L−15)/2 · Lat 20%, mín. 2,5 (no en lotes ≤ 11 m) | Solo en lotes ≥ 1.000 m² (planilla); el Decreto 165/08 dice solo dúplex fuera del corredor |
| R4 bis (corredor Lavalle–Victorica) | — | 0,6 | 2,5 | 400 | F 3 · 0,5 (L−20) · bilateral 4 m | Sí; PB libre o cocheras; estética de la costa |
| R1u | 15 × 30 / 450 | 0,6 | 1,2 | 400 | F 3 · (L−15)/2 · Lat 20% | En lotes ≥ 600 m², 1 vivienda cada 300 m², con agua y cloaca (Ord. 3749/20) |
| R1 | 15 × 40 / 600 | 0,6 | 1,2 | 100 · 150 con agua · 400 con cloaca | F 3 · (L−20)/2 · Lat 20% | Ver punto 11.5 de la planilla |
| R2 | 15 × 30 / 450 | 0,6 | 1,2 | 140 · 150 con agua · **400 con cloaca** | F 3 · (L−15)/2 · Lat 25%, mín. 2,5 | **Con agua y cloaca; 12 m con PB libre** |
| R3 | 12 × 25 / 300 | 0,6 | 1,2 | 140 · 150 · **400** | F 3 · (L−15)/2 | **Con agua y cloaca; 12 m con PB libre** |
| R5 | 12 × 25 / 300 | 0,6 | 1,2 | 140 · 150 · **400** | F 3 · (L−15)/2 | **Con agua y cloaca; 12 m con PB libre** |
| RP | 20 × 40 / 800 | 0,4 | 0,8 | 90 | F 6 · (L−20)/2 · Lat 3 o 6 | No (unifamiliar) |
| E | 30 × 60 / 1.800 | 0,45 | 0,9 | 40 | F 6 · fondo 20 · Lat 6 | No |
| I1 / Ip / A | — | 0,6 / 0,4 | 1,2 / 0,8 | 20–100 | Grandes | No (industrial o rural) |

**Reglas generales del Código 1894/96:**
- **Retiro de fondo (art. 46):** nunca menos de 3 m. En zonas residenciales se puede tomar como máximo 15 m, y 20 m en el resto.
- **Esquinas:** en C1, C2, C3 y el basamento de Tc no hay retiro de fondo (art. 51). Una esquina con dos zonas elige la más favorable (art. 53 I).
- **FOS (definición):** excluye solo los balcones de menos de 1,30 m de vuelo.
- **FOT (definición):** superficie cubierta máxima. Las ocupaciones de fondo (quinchos, art. 47) computan.
- **Patios internos:** no sirven para locales de primera clase (art. 56). Los patios auxiliares miden 12 m² y 3 m de lado como mínimo.

## 3. Alturas — Ordenanza 4448/26

Fija "PB + N" por sector en cada localidad (arts. 2 a 11), con prioridad sobre el Código (art. 1). Resumen del **máximo por zona y localidad**. Dentro de cada localidad hay sectores más bajos: el detalle por calles está en el texto de la ordenanza.

| Localidad (art.) | Alturas máximas |
|---|---|
| **Tigre** (2) | **R1u** PB+3 (con estudio hidráulico y 40% absorbente) · **R4** PB+2 · **R4 bis** PB+3 · **R4 ter** (Liniers y Libertador) PB+4 · **R6** PB+4, PB+6 sobre Dardo Rocha y PB+10 entre Morales, Mitre, Vivanco y Montes de Oca · **R8** PB+3 · **Tc** PB+8 / PB+10 · **Tr** PB+4 / +6 / +8 / +10 · **C4a** PB+12 (Luis García / RP27) · **C6** PB+3 · **C7** PB+6 / PB+10 · **E** PB+4 · **UE** PB+3 / +4 |
| **Rincón de Milberg** (3) | **C4c** PB+5 / +6 · **C5** PB+6 · **R5 bis** PB+2 · **R7** PB+2 / PB+6 · **RM1** PB+2 / +3 / +6 · **E** PB+3 · **UE** PB+3 |
| **Benavídez** (4) | **C1** PB+5 · **C4a** PB+5 / PB+8 · **C4b** PB+5 / +6 · **C5** PB+6 · **R1a** PB+5, y **PB+2 en "La Bota"**, donde se prohíben torres y densificación y no hay excepciones · **R3b** PB+5 · **RM1** PB+2 a PB+6 · **E** PB+3 |
| **Dique Luján** (5) | Todo PB+3: R1a, E, C1, C3, RM1 y R2g |
| **Ricardo Rojas** (6) | **C1** PB+4 / +5 · **C4a** PB+4 · **C4b** PB+5 / PB+8 |
| **General Pacheco** (7) | **C1** PB+6 · **C2a** PB+6 (30% absorbente, accesos solo por la avenida) · **C2b** PB+6 · **C4a** PB+5 · **C4b** PB+8 · **R2c y R2d PB+2, sin multifamiliar de media o alta densidad** |
| **El Talar** (8) | **C1** PB+5, con PB+3 de transición · **C2b** PB+6 · **C4a** PB+5 |
| **Troncos del Talar** (9) | **C3** PB+6 · **C4a** PB+5 · **UE** PB+2 / +3 (estudio hidráulico, 40% absorbente) |
| **Don Torcuato** (10) | **C1** PB+5 · **C2a** PB+5 (PB+3 de transición) · **C2b** PB+5 · **C4a** PB+5 · **R2g** PB+5 |
| **Nordelta** (11) | **C5** PB+6 · **UE** PB+3 · **UM2** PB+12 (con los planes particularizados del Centro Cívico) |

**Reglas generales de la 4448 (art. 12):**
- **Escalonamiento (inc. k):**
  - **por distancia a la avenida:** hasta 50 m se toma la altura máxima del sector, entre 50 y 100 m una intermedia, y a más de 100 m la mínima del sector;
  - **por ancho de calle:** menos de 12 m, PB+6 como máximo; entre 12 y 20 m, PB+8; más de 20 m, lo que diga la zona;
  - junto a tejido más bajo hay que escalonar.
- **Cocheras (inc. e):** 1 por unidad, dentro del lote, sin compensación afuera. Esto deja sin efecto el radio de 200 m del art. 65 c del Código. Los pisos de cocheras sobre la PB no computan FOT ni altura.
- **Torres:** no se admiten torres aisladas sobre basamento libre en tejido residencial. Junto a tejido de menor escala, transición volumétrica.
- **Estudios:** de impacto urbano, hidráulico (define la cota de PB; subsuelos solo si el estudio lo aprueba), de impacto vial, de capacidad de redes (pueden pedir obras) y ambiental, según el sector.
- **Silencio positivo:** si la Municipalidad no responde en 60 días hábiles con el proyecto completo, queda aprobado en lo urbanístico (inc. i).
- **Unificación de lotes:** el perfil urbano solo se concede si los lotes cumplen el art. 53 del Código.
- **Zonas industriales sin altura** que pasen a residencial: necesitan el Concejo Deliberante (art. 13).
- **Altura dentro de barrios cerrados o clubes de campo:** informe vinculante y Concejo Deliberante (art. 14).
- **Transición (art. 17.1):** quedan con la norma anterior los proyectos con expediente presentado **antes del 05/11/2025**, o con prefactibilidad, factibilidad o permiso otorgados.
- **Interpretación (art. 16 bis):** ante la duda, la solución más restrictiva, y no hay excepciones particulares.

**Decreto 165/08:**
- En alturas lo reemplaza la 4448.
- **Sigue rigiendo en usos:** en R1u y R4, fuera de los corredores de Lavalle, Victorica y Libertador, el multifamiliar es solo de tipo dúplex. Las planillas posteriores de R1u (Ord. 3749/20) y R4 (≥ 1.000 m²) lo abren; hay que verificarlo caso por caso.
- **Exige** la factibilidad de AySA.
- **Mide la altura desde la cota +4,00 IGM** si el lote está más bajo (art. 8 c).

## 4. Premios del FOT y la densidad (Código, art. 54)

Se pueden sumar hasta un **+70%** sobre el FOT y la densidad máximos:

| Motivo | Premio |
|---|---|
| Ancho de parcela (en esquina, el lado menor) | +2,5% por metro sobre 10 m, hasta +25% (con 20 m de frente) |
| Edificio separado de los ejes laterales, con un mínimo de 4 m | +3% por metro y por eje, hasta +30% |
| Retiro de frente voluntario, más allá del obligatorio | +3% por metro, hasta +15% |
| Ocupar menos que el FOS máximo | Proporcional, hasta +10% |
| Espacio público al frente (desde la L.M. al eje), más de 10 m | +0,5% por metro, hasta +10% |

- **En la práctica,** un lote de 20 m o más con retiros laterales llega a +50/55%. Es el ×1,5 que usa el motor.
- **Ese premio necesita más niveles**, porque los retiros laterales bajan el FOS efectivo. Con la 4448 suele quedar cortado por la altura.

## 5. Cómo se calcula lo construible (vigente desde el 19/11/2026)

Para cada aviso, con la zona del punto:

1. **Servicios:** sin dato de agua y cloaca se toma el FOT y la densidad "con infra" y se marca `requiere_agua_y_cloaca`, como hoy. Así no se pierden oportunidades; se verifica a mano.
2. **FOT de la zona:** el residencial de la planilla. Ojo con C2 y Tc: es 2,5.
3. **Premio art. 54:** si el lote tiene al menos 2 parcelas mínimas (regla actual de Gonzalo), FOT × 1,5, con tope en el +70%.
4. **Tope de altura de la 4448:** niveles = N + 1, tomando la máxima de la zona en esa localidad. Si la zona no figura en la 4448, rige el art. 12 k (calle de menos de 12 m: PB+6).
5. **FOS efectivo** (todavía no en el motor, que usa el FOS de la zona): FOS, salvo que los retiros lo achiquen. Se estima la planta posible como (frente − retiros laterales) × (fondo − retiro de frente − retiro de fondo), y se toma la menor entre eso y FOS × superficie. Varias zonas permiten ocupar parte del retiro de fondo para completar el FOS (R6 hasta dejar 10 m, R1u, R2 y R4 hasta 5 m, R1 y RP hasta 6 m).
6. **FOT alcanzable** = min(FOT con o sin premio, FOS efectivo × niveles).
7. **Tope por densidad:**
   - habitantes = densidad × superficie ÷ 10.000;
   - m² posibles = habitantes × **30 m² cubiertos por habitante** (Gonzalo, 19/11/2026), por ejemplo 2 ambientes de 60 m² brutos para 2 personas;
   - **m² construibles** = min(superficie × FOT alcanzable, m² por densidad).
8. **Incidencia** = precio ÷ m² construibles, con los umbrales de Tigre (350 / 450 USD/m²).

**Ejemplos:**

| Caso | FOT motor | Altura 4448 | FOT alcanzable | Densidad | m² construibles |
|---|---|---|---|---|---|
| C1 en Ricardo Rojas, lote de 25 × 40 = 1.000 m² | 3,6 (premio) | PB+4 → 5 × 0,6 = 3,0 | 3,0 | 2.000 → 200 hab → 6.000 m² (no corta) | **3.000 m²** (motor 3.600) |
| C5 en Benavídez, 1.000 m² | 1,8 | PB+6 → 4,2 | 1,8 | 400 → 40 hab × 30 = 1.200 m² | **1.200 m²** (motor 1.800) |
| C2a en Pacheco, 1.200 m² | 4,5 (premio) | PB+6 → 4,2 | 2,5 × 1,5 = 3,75 | 2.000 (no corta) | **4.500 m²** (motor 5.400) |
| R3 en El Talar, 1.500 m², con cloaca | sin multifamiliar | 12 m con PB libre | 1,2 | 400 → 60 hab × 30 = 1.800 (no corta) | **1.800 m²** (motor: no lo evalúa como multifamiliar) |

## 6. Oportunidades que pasan desapercibidas

1. **Proyectos con aprobaciones anteriores a la 4448** (art. 17.1). Un lote con expediente presentado antes del 05/11/2025, o con prefactibilidad o factibilidad otorgada, conserva la altura anterior. Por ejemplo, el Decreto 165/08 daba **PB+20 (60 m)** en el sector Tr entre Dardo Rocha, el río Tigre, Enciso y Bourdieu, donde hoy hay PB+10. Los avisos que dicen "proyecto aprobado", "factibilidad" o "planos aprobados" en Tigre valen más de lo que parece. **El scouting podría marcarlos buscando esas palabras en el texto.**
2. **R2, R3 y R5 con agua y cloaca:** multifamiliar de 12 m con PB libre, sobre tierra de zona "semiurbanizada". Hoy el motor no los evalúa como multifamiliar. Quedan afuera R2c y R2d en Pacheco y "La Bota" en Benavídez.
3. **Cocheras en altura que no computan** (4448, art. 12 e 5). En lotes chicos, poner las cocheras en un primer piso libera la PB y no consume FOT ni altura.
4. **Premios del art. 54 en lotes anchos:** con 20 m o más de frente se suma +25% solo por el ancho. Con laterales de 4 m, hasta +24% más.
5. **Esquinas en C1, C2, C3 y Tc** (sin retiro de fondo) y **esquinas con dos zonas** (se elige la mejor, art. 53).
6. **Primeros 50 m desde la avenida** (art. 12 k): toman la altura máxima del sector.
7. **Galpones en zonas industriales cercanas a centros** (art. 13): el cambio a residencial es posible, pero va al Concejo Deliberante. Es largo, pero es un valor que el precio del galpón no incluye.
8. **Lotes de 7.500 m² o más** (art. 50 del Código): pueden pedir una urbanización especial, con otros usos e indicadores, al Concejo.
9. **Silencio positivo de 60 días hábiles:** acorta los plazos de aprobación frente a otros municipios.

## 7. Qué cambió en el motor (19/11/2026)

| Tema | Antes (UrbaSIG 09-2022) | Ahora | Dónde |
|---|---|---|---|
| FOT de C2a, C2b y Tc | 3,0 (premio 4,5) | 2,5 residencial (premio 3,75) | `tools/municipio_pba.py` → `normativa_zonas.csv` |
| Densidad de C1 a C4 | 150 | 150 sin cloaca; con cloaca 2.000 (C3: 800), con la señal "requiere agua y cloaca" | ídem |
| Densidad de R4 | 140 | 400 (planilla) | ídem |
| R2, R3 y R5 | Sin multifamiliar (R5: sin la señal) | Multifamiliar con agua y cloaca, 400 hab/ha, con la señal | ídem |
| R1u | Sin multifamiliar | Multifamiliar desde 600 m², 1 vivienda cada 300 m², con agua y cloaca | ídem + `municipio.yaml` |
| Altura | Sin tope | **Ord. 4448/26 por sector:** FOT ≤ FOS × (N + 1) | `alturas_4448.yaml` → `tools/alturas_4448.py` → `alturas_4448.geojson`; `src/alturas.py` |
| Densidad como tope de m² | No | m² ≤ densidad × superficie ÷ 10.000 × 30 | `productos.m2_por_habitante` |
| Proyecto aprobado antes de la 4448 | No | Señal `proyecto_aprobado_previo` si el aviso dice "proyecto aprobado", "planos aprobados", "factibilidad", "permiso de obra" | `productos.flags.patrones_texto` |
| Prohibición de multifamiliar (R2c de Pacheco y otras) | No | Si el aviso cae en el polígono del sector, el multifamiliar queda descartado ("multifamiliar_prohibido_ord_4448") | `alturas_4448.yaml` (`sin_multifamiliar`) |

**Columnas nuevas** en `resultado.csv`:
- `fot_efectivo`: el FOT que de verdad entra.
- `limite_fot`: por qué es menor que el de la zona, si lo es.

En San Isidro las dos salen iguales al FOT y vacías; no cambia ningún resultado (verificado con los tests de las corridas del 02/11 y el 09/11).

**Sectores de la 4448** (`python tools/alturas_4448.py` imprime el detalle): de 90, **54 tienen polígono** y se aplican por ubicación. El resto queda **sin polígono**:
- **26 "manuales":** sus límites son parcelas catastrales, o la zona tiene una sola altura en la localidad.
- **10 fallas:** las calles no cierran, o el polígono no cae en su zona.

Un aviso que no cae en ningún polígono usa **la altura máxima de su zona en esa localidad**, para no perder oportunidades, con el aviso `altura_4448_sector_no_identificado`. Donde más pesa:
- en **Tigre centro**, R6, Tc y Tr con PB+10 como máxima. Las áreas PB+4 de R6 y Tr sí tienen polígono;
- en **RM1 de Rincón y Benavídez**.

**Todavía no está en el motor:**
- el FOS efectivo por retiros (sección 5, paso 5);
- la transición "PB+3" junto a corredores de El Talar y Don Torcuato;
- el escalonamiento por distancia a la avenida y ancho de calle (art. 12 k);
- las cocheras.

## 8. Decisiones de Gonzalo (19/11/2026)

1. **Altura de la 4448:** cargar los sectores calle por calle.
2. **Densidad como tope de m²:** sí, con 30 m² por habitante.
3. **R2, R3 y R5:** habilitar el multifamiliar con la señal "requiere agua y cloaca".
4. **FOT de 2,5 en C2a, C2b y Tc:** corregirlo.
5. **Señal de proyecto aprobado antes de la 4448**, a partir del texto del aviso: agregarla.
6. **R4 y R1u:** valen las planillas que abren el multifamiliar, no el Decreto 165/08 (solo dúplex).

## 9. Trampas

- **Sin agua y cloaca:**
  - el FOT baja (C1 1,2; C2, C3 y C4 1,4);
  - la densidad baja a 150 (o 400 con planta de tratamiento aprobada por Hidráulica);
  - en C7 y RM2 hay una sola vivienda por lote.
  - Exige la factibilidad de AySA (Decreto 165/08, art. 11).
- **Estudio hidráulico y suelo absorbente del 40-50%:** rige en R1u de Tigre centro, "La Bota", UE y Troncos del Talar. Baja el FOS efectivo, y los subsuelos solo se aprueban si el estudio lo permite.
- **Cota +4,00 IGM:** los lotes bajos miden la altura desde ahí. Hay que rellenar o elevar la PB.
- **Fondo Municipal para la Mejora del Hábitat** (C7, RM2): al menos el 10% de la valorización cuando aumenta la capacidad constructiva.
- **Barrios cerrados y clubes de campo:** la altura va al Concejo con un informe vinculante (art. 14).
- **Interpretación restrictiva y sin excepciones** (art. 16 bis): no conviene contar con excepciones particulares.
- **Delta:** excluido; tiene normas propias.

---

## 10. Revisión exhaustiva (24/11/2026): lo que faltaba

Segunda pasada, ahora sobre todo el marco que pesa en un lote de Tigre:
- el Código 1894/96 completo: subdivisión, art. 71, cotas y Anexo del Delta;
- la Ord. 4448/26: definiciones y art. 12;
- el Decreto-Ley 8912/77, texto ordenado de normas.gba.gob.ar;
- la Ley 14.449 de Acceso Justo al Hábitat.

Las fuentes nuevas están al final.

### 10.1 Estado de la Ord. 4448/26

- **Sanción:** el Concejo la aprobó a fines de abril de 2026, 18 votos a 6. Se publicó en el Boletín Oficial 1065 del 07/05/2026. Sobre la promulgación hay una discrepancia: la prensa menciona el Decreto 606/26, y nuestra copia dice 584. Hay que verificarlo en el Digesto, que hoy no responde.
- **Cautelar previa:** en noviembre de 2025, vecinos obtuvieron una cautelar que frenaba las nuevas habilitaciones hasta que hubiera una norma nueva. No encontré ninguna cautelar contra la 4448 ni contra su art. 17, aunque la oposición anunció que podría pedirla. **Riesgo:** un aviso que dependa de la transición del art. 17 puede quedar trabado en la Justicia.
- **La transición del art. 17 ya se usa:**
  - **El caso:** en 2026 el Concejo dio viabilidad urbanística a un complejo de 59,90 m en RM1 de Rincón de Milberg, frente a Nordelta (Sausalito y Los Lirios, 5.289 m²). Son dos bloques de 17 niveles.
  - **Por qué entra:** el expediente es de octubre de 2025 e inició bajo la Ord. 3749/20. Hoy la 4448 da PB+6 en esa zona.
  - **Qué confirma:** la señal `proyecto_aprobado_previo` vale plata.
- **Fecha de corte:** expedientes anteriores al 05/11/2025 (algunos medios dicen 04/11).

### 10.2 Lo que el motor todavía no aplica y cambia los m²

1. **Superficie absorbente (FAS) de la 4448.** Varios sectores exigen un mínimo de suelo absorbente y un estudio hidráulico:
   - **50%:** "La Bota" y las márgenes del Canal Aliviador; este último pide además un retiro libre desde la ribera;
   - **40%:** R1u en Tigre centro y sectores de Troncos del Talar, El Talar y Don Torcuato;
   - **30%:** C2a de Pacheco.

   Con 50% absorbente, el FOS real queda en 0,5 o menos (0,4 con los accesos). Como la altura está topada, el FOT alcanzable baja: FOT ≤ FOS real × niveles.
2. **FOS efectivo por retiros** (sección 5, paso 5): sigue pendiente.
3. **Escalonamiento del art. 12 k:**
   - **por ancho de calle:** menos de 12 m, PB+6; de 12 a 20 m, PB+8;
   - **por distancia a la avenida:** hasta 50 m, la máxima del sector; de 50 a 100 m, una intermedia; más de 100 m, la mínima.

   Pesa en los sectores de PB+8 a PB+12: Tc, Tr y C4a sobre la RP27.
4. **Cocheras (art. 12 e).** Es 1 por unidad, dentro del lote. En las zonas con estudio hidráulico, el subsuelo solo vale si el estudio lo aprueba. Con 22,5 m² por cochera con circulación (Código, art. 65), un edificio de 50 unidades necesita unos 1.100 m² de cocheras, que van en PB o en pisos altos (estos no computan FOT ni altura).

   No cambia los m² vendibles, pero sí el costo y si el proyecto entra en la parcela. **Sugerencia:** marcar los lotes de menos de 800 m² con más de 20 unidades.

### 10.3 Viviendas agrupadas y loteo: reglas que no estaban

- **Art. 71 del Código (emprendimientos urbanísticos privados, condominio de casas, Ley 13.512).** Donde se admite vivienda, se permite más de una unidad por lote según los servicios:
  - **1 vivienda cada 400 m²** con agua y cloaca por red (400 hab/ha);
  - **1 cada 600 m²** con uno de los dos servicios (150 hab/ha);
  - **1 cada 800 m²** con tratamiento estático (90 hab/ha).

  Además fija FOS 0,6, FOT 1,2, retiro de 5 m entre viviendas, 9 m de altura, calle interna de 7,50 m (calzada de 5,50) y la cota inundable del art. 19.

  **El motor usa los m² por unidad de UrbaSIG:** en R2d, R2f, R2g y R3d da 200 m², la mitad de lo que permite el art. 71. **Propuesta:** en "agrupadas con acceso común", tomar el mayor entre el valor de la zona y 400 m² (600 u 800 sin servicios), con la señal de servicios.
- **Subdivisión (Código, arts. 14 a 27):**
  - **Cota +3,75 IGM (arts. 19 y 27).** Para subdividir hay que **rellenar a +3,75 IGM antes de la aprobación**, con un estudio de la cuenca visado por Hidráulica. Bajo esa cota y sin infraestructura rige la Ley 6.254. **Es un costo grande en Benavídez, Rincón, Dique Luján y la ribera, y el motor no lo ve.**
  - **Calles y manzanas.** Las calles nuevas miden 15 m entre líneas municipales (art. 21). Las manzanas, de 60 a 150 m de lado y mínimo 7.500 m² (art. 23). Por eso un loteo con calle interna pierde más que en San Isidro: con lotes de 15 × 30 a los dos lados de una calle de 15 m, la calle ocupa ~20%. El 25% que usa el motor queda razonable.
  - **Infraestructura (art. 17).** Una fracción de más de 2.000 m² que se divide en más de 3 lotes tiene que hacer la infraestructura del art. 15: agua, pavimento, pluviales, electricidad, alumbrado y cloaca.
  - **Ley 8912:**
    - **art. 56:** al ampliar áreas urbanas, se ceden 3,5 a 6 m² de verde y 1 a 2 m² de equipamiento por habitante. En una reestructuración dentro del área urbana, **hasta 10% de verde y 4% de equipamiento**;
    - **art. 57:** al parcelar manzanas anteriores a la ley, la cesión se compensa con más FOT y densidad;
    - **art. 59:** al crear o ampliar núcleos, franja de 50 m desde la máxima creciente junto a cursos de agua, o de 100 m junto a espejos de agua.

    **En un loteo grande se pierde el ~20–25% de calles más hasta 14% de cesiones.** El motor descuenta solo el 25% de calle.
- **Ley 14.449, art. 51.** Los barrios cerrados, clubes de campo y toda urbanización cerrada en predios de **más de 5.000 m²** ceden el **10% de la superficie** como pago a cuenta, en cualquier zona. Se puede pagar en dinero o en suelo equivalente. **Afecta el producto "loteo con calle interna" cuando es cerrado.**

### 10.4 Agua: sirga, cota y riesgo

- **Camino de sirga.** Es una franja de 15 m desde la línea de ribera, de uso público, sin construcciones ni cercos. La define la 4448 y coincide con el art. 1974 del Código Civil y Comercial.

  **En Tigre hay muchos lotes frentistas a ríos, canales y lagos.** La capa de ríos de OSM ya está en el repo (`municipios/tigre/fuentes/rios_y_vias_osm.geojson`). Con ella se puede marcar cada aviso a menos de ~50 m de un curso de agua y descontar la franja de 15 m de la superficie útil.
- **Cotas:**
  - +3,75 IGM para subdividir (Código);
  - +4,00 IGM como base para medir la altura (Decreto 165/08).

  La franja inundable va desde la curva de 5 m IGN hasta el río Luján. Sin un modelo de elevación no se puede automatizar: queda como verificación manual en la línea de checklist.
- **Estudio hidráulico obligatorio** en los sectores de la 4448 que lo piden: define la cota de la PB y si se puede hacer subsuelo.

### 10.5 Plusvalías y fondos

- **Ley 14.449, arts. 46 a 50:**
  - **Cuándo participa el municipio:** rezonificación, mayor aprovechamiento (FOS, FOT o densidad, por excepción o por convenio), grandes desarrollos u obra pública. En esos casos se queda con **al menos el 10% de la valorización**.
  - **Cuándo se cobra:** al pedir el permiso, al cambiar el uso o al transferir.
  - **Cuándo no aplica:** construir dentro del Código vigente.

  Pesa en las jugadas de cambio de norma:
  - galpón a residencial (4448, art. 13);
  - urbanización especial de 7.500 m² o más (Código, art. 50);
  - transferencia de FOT.
- **Fondo Municipal para la Mejora del Hábitat.** Las planillas de C7 y RM2 piden al menos el 10% de la valorización cuando sube la capacidad constructiva. No encontré la ordenanza general de Tigre.
- **Derechos de construcción 2026: pendiente.** No pude leer la Ordenanza Impositiva porque el Digesto municipal y el SIBOM no responden. Hace falta porque entra en el costo total de la rentabilidad.

### 10.6 Oportunidades nuevas que el precio no incluye

1. **Transferencia de capacidad constructiva desde el Delta** (Anexo del Delta, punto 2.2.1.2):
   - **Cómo funciona:** quien engloba las parcelas baldías de un Distrito de Reconversión de las islas (DDr1 a DDr82) puede transferir **hasta +30% de FOT y densidad** a parcelas del continente. Un edificio catalogado transfiere hasta +10%.
   - **Topes:** el FOT máximo de la Ley 8912 (2,5 residencial, 3 comercial) y el FOT ya topado por la altura de la 4448.
   - **Trámite:** se instrumenta por convenio urbanístico, y el crédito se puede ceder.
   - **Dónde sirve:** donde la altura no corta, como C5 o R7 con lotes chicos.
2. **La transición del art. 17** (ver 10.1), ya probada en un caso real.
3. **R1a y R3b fuera de los barrios cerrados.** El motor los ignora porque UrbaSIG los marca como "barrio cerrado"; son 548 ha de R1a en Benavídez y 820 ha de R3b. Pero la 4448 les da altura en sectores concretos:
   - R1a PB+5 sobre la colectora de la Panamericana frente a Chilavert y en el área de Perón y Patricias Argentinas;
   - R3b PB+5 entre Alvear, Marabotto, San Martín y Brasil;
   - R1a PB+3 en Dique Luján.

   **Es probable que haya lotes desarrollables que hoy se pierden.**
4. **Nordelta:**
   - **Base normativa:** el Decreto provincial 1736/92 y el Plan Director de la Ord. 1297/92, con sus prórrogas (2898/08).
   - **Alturas de la 4448 (art. 11):** C5 PB+6, UE PB+3 y **UM2 PB+12**. UM2 rige en el Centro Cívico y en Castaños–Estación, con los planes particularizados de las Ord. 3982/22, 4077/23 y 4126/23.
   - **Zonas UR de UrbaSIG:** UR 1 C con FOT 3, UR 1.1 con 2,4, UR 2.1 con 1,4, etc. La 4448 no las nombra.
   - **Reglamentos privados:** dentro de los barrios de Nordelta suelen limitar a una vivienda.

   **Hay riesgo de falsos positivos en UR 4.x** (FOT 0,5 a 0,65 con multifamiliar "Sí"). **La oportunidad real está en UR 1 C, UR 1.1 y UM2**, que son macrolotes del centro.

### 10.7 Decisiones para Gonzalo

| # | Tema | Propuesta |
|---|---|---|
| 1 | R1a y R3b en los sectores con altura de la 4448 | Evaluarlos con los indicadores de R1 y R3 de las planillas, solo dentro de esos sectores; el resto sigue sin producto |
| 2 | Nordelta | UR 4.x sin multifamiliar (son barrios). UR 1 C, UR 1.1 y UM2 con multifamiliar y la señal "verificar plan particularizado / reglamento Nordelta" |
| 3 | FAS y FOS efectivo | Aplicar el absorbente de la 4448 por sector (FOS ≤ 1 − FAS) y los retiros, como tope del FOT junto con la altura |
| 4 | Agrupadas con acceso común | Tomar el mayor entre los m² de la zona y los del art. 71 (400, 600 u 800 según los servicios) |
| 5 | Loteo con calle interna | Mantener el 25% de calle y agregar señales: cesión de la Ley 8912 (hasta 14%), cesión del 10% de la Ley 14.449 si es cerrado de más de 5.000 m², relleno a cota +3,75 |
| 6 | Camino de sirga | Señal automática con la capa de ríos y descuento de la franja de 15 m de la superficie útil |
| 7 | Art. 12 k (calle y avenida) | Aplicar el tope por ancho de calle cuando se conozca el ancho (OSM) y marcar la distancia a la avenida |

### 10.9 Aplicado en el motor (Gonzalo aprobó las 7 propuestas, 24/11/2026)

| # | Qué hace ahora el motor | Dónde |
|---|---|---|
| 1 | R1a y R3b tienen una segunda fila (planillas R1 y R3, multifamiliar con agua y cloaca) que solo vale dentro de un polígono de la 4448 con PB+3 o más que no prohíba multifamiliar. Fuera de esos polígonos siguen sin producto. Hoy hay polígono en R1a frente a la colectora de Panamericana, junto al Acceso Chilavert (203 m de frente), y en R3b entre Alvear, Marabotto, San Martín y Brasil (2,2 ha). Quedaron "manuales" porque OSM no tiene sus calles: R1a de Perón y Patricias Argentinas, "La Bota" (PB+2, sin multifamiliar) y los dos sectores R1a de Dique Luján; esos no habilitan nada. Señal `solo_en_sector_4448` | `tools/municipio_pba.py` (`filas_extra`), `alturas_4448.yaml`, `evaluate.py` |
| 2 | UR 4.x sin multifamiliar (unifamiliar por parcela). Todas las UR llevan la señal `verificar_reglamento_nordelta`. UE 8 (Centro Cívico, UM2) tiene una fila con los indicadores de UR 1 C (FOT 3, 2.000 hab/ha), la señal `verificar_plan_centro_civico` y PB+12 como sector manual | ídem |
| 3 | FOS efectivo = el menor entre el FOS de la zona, 1 − el absorbente del sector de la 4448 (solo dentro de su polígono) y lo que dejan los retiros de la planilla (frente, fondo, laterales). Para los retiros hace falta el frente: sin frente no se aplica. Con la altura: FOT ≤ FOS efectivo × niveles. Columnas `fos_efectivo` y `limite_fot` | `normativa_zonas.csv` (columnas `retiro_*`), `evaluate.fos_by_setbacks`, `_caps` |
| 4 | Agrupadas con acceso común: el mayor entre los m² por unidad de la zona y 400 m². "Agrupadas a la calle" sigue con la planilla (R2d, R3d: 200 m²). Señal `agrupadas_art_71` | `productos.m2_min_agrupadas_acceso_comun` |
| 5 | Todo aviso que admite loteo con calle interna lleva `cesion_ley_8912` y `relleno_cota_375`; con más de 5.000 m², también `cesion_ley_14449`. El 25% de calle no cambió | `productos.senales_loteo` |
| 6 | Punto a menos de 50 m de un río, canal o arroyo de OSM: se descuenta la franja de 15 m × frente (sin frente, 15 × √superficie; nunca más de la mitad). Las unidades y los m² se calculan con esa superficie útil, pero el filtro de superficie y el gran predio usan la total. Columna `superficie_util_m2`, señal `camino_de_sirga` | `productos.sirga`, `src/entorno.py` |
| 7 | Con el tipo de calle de OSM (`calles.geojson` ahora trae `tipo`): si la calle más ancha a menos de 25 m del punto es residencial, el tope es PB+6; si es terciaria, PB+8; si es avenida, sin tope. En sectores de PB+8 o más, a más de 50 m de una avenida, se marca `art_12k_lejos_de_avenida` (solo la señal: la altura intermedia y la mínima del sector no están en la ordenanza) | `productos.art_12k`, `src/entorno.py`, `_caps` |

**Medición rápida** (puntos cada 40 m dentro de los sectores de PB+8 y PB+10): por el ancho de calle, el 23% queda en PB+6 y el 28% en PB+8. Más de la mitad de esos puntos está a más de 50 m de una avenida.

**Lo que dio poco:** el absorbente de la 4448. Con 40% o menos, 1 − FAS queda en 0,6 o más y no corta (FOS de las zonas: 0,6). Solo corta con 50% ("La Bota", Canal Aliviador), y esos sectores no tienen polígono o son zonas sin vivienda.

**San Isidro:** sin cambios. Lo comprobé con los golden del 02/11 y el 09/11: 0 celdas distintas; solo se agregan dos columnas vacías.

**Pendiente:**
- los polígonos de los sectores "manuales";
- la altura intermedia y la mínima del escalonamiento;
- las cocheras;
- los derechos de construcción;
- leer los planes del Centro Cívico de Nordelta.

### 10.8 Fuentes nuevas

- [Decreto-Ley 8912/77, texto ordenado (normas.gba.gob.ar)](https://normas.gba.gob.ar/documentos/5B3DztjV.html): arts. 37, 45–47, 52, 56–59, 62 y 64–69.
- [Ley 14.449, texto actualizado (normas.gba.gob.ar)](https://normas.gba.gob.ar/documentos/B3mgaUj0.html): arts. 44–51.
- [Decreto provincial 1736/92, núcleo urbano Nordelta](https://normas.gba.gob.ar/documentos/0zQy76f8.html).
- Prensa sobre la 4448:
  - [Zonales, 29/04/2026](https://zonales.com/polemica-tigre-aprobaron-ordenanza-torres/);
  - [SM Noticias, 28/04/2026](https://www.smnoticias.com/noticias/276401);
  - [La Troncal, complejo de 59,90 m](https://latroncal.com.ar/complejo-60-metros-frente-nordelta-ruta-27/).
- [Trámite de derechos de construcción (tigre.gob.ar)](https://www.tigre.gob.ar/tramites/liquidaciones_derechos_construccion): no publica las alícuotas.
- PDFs en Drive:
  - Código 1894/96: arts. 13–27, 50, 59–61, 65 y 70–71, y Anexo del Delta 2.2.1.2;
  - Ord. 4448/26: definiciones y arts. 2–12;
  - Decreto 165/08.
