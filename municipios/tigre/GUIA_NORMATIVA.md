# Tigre — guía de normativa para evaluar un lote

Lectura rápida: qué limita lo que se construye en un lote de Tigre, cómo se calcula según la zona y el lote, y qué buscar que el resto no ve. Estudio del 19/11/2026.

**Estado:** desde el 19/11/2026 el motor de Tigre aplica las decisiones de Gonzalo de la sección 8: planillas por encima de UrbaSIG, alturas de la Ord. 4448 por sector, tope por densidad y señal de proyecto aprobado. La sección 7 cuenta qué cambió y qué quedó afuera.

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
