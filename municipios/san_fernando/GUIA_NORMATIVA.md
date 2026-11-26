# San Fernando — guía de normativa para evaluar un lote

Esta guía es una lectura rápida de qué limita lo que se construye en un lote de San Fernando, de cómo se calcula según la zona y el lote, y de qué hace hoy el motor. Es el estudio del 26/11/2026, que se hizo leyendo el texto completo del Código y comparándolo con `normativa_zonas.csv`, armado desde UrbaSIG el 14/11.

**Estado:** el 26/11/2026 Gonzalo aprobó las 8 propuestas de la sección 9. La sección 9.1 dice qué hace el motor con cada una.

**Fuentes** (PDFs en Drive, `01 - PROYECTOS CLAUDE/scouting-san-fernando/normativa/`):
- **Código de Edificación y Zonificación**, Ordenanza 3603/91. El texto ordenado (2ª edición, 163 páginas) es el del sitio del municipio (`sanfernando.gob.ar/uploads/adjuntos/UNOOK.pdf`) y lo convalidó el Decreto provincial 2788/96. La Sección III (págs. 27 a 69) es la zonificación. Los anexos traen los barrios privados y las ordenanzas sueltas: Parque de la Reconquista (Ord. 5951/95), C2B (Ord. 8035/03), Punta Chica Village (Ord. 6587/97) y urbanizaciones en PH dentro de R3.
- **Ordenanza 13.667/24**, en el Boletín Municipal 53/2024. Pasa una parcela de BPN (Circ. V, Fr. 1, Parc. 6) a **UE 9, Reserva Ecológica**. Sus considerandos hablan de "actualizar el Código", pero **no hay código nuevo**: la 3603/91 sigue vigente.
- **UrbaSIG** (`urbasig:_zonificacion`, partido 096), con la capa del 03-2026. Es lo que usa hoy el motor.
- **No conseguido:** el texto de la **Ord. 13.017/21**, que crea el Agrupamiento Industrial San Fernando y define el DI y el DRC. Solo aparece citada en las ordenanzas fiscales, por la exención de derechos de construcción en el DI. Tampoco conseguí las Resoluciones provinciales 833/22 y 877/23 que la homologan.

---

## 1. Conclusiones

1. **En R3 y R3A se pueden hacer varias casas por lote, y eso hoy el motor no lo ve.** El art. 3.5.6.7 permite dos viviendas en lotes de más de 250, 330 o 400 m² según el subdistrito de uso, tres en lotes de más de 550 m² y más de tres desde 700 m², con la cantidad que den el FOS, el FOT y la densidad. Además admite dúplex en cualquier parcela. Con 250 hab/ha (R3) o 170 hab/ha (R3A) y 4 personas por vivienda salen **una casa cada 160 m² en R3 y una cada 235 m² en R3A**. **R3 y R3A suman 767 ha, más de la mitad del suelo residencial continental del partido**: Virreyes, San Fernando oeste y Victoria. Ejemplo: en un lote de 1.000 m² en R3A con 20 m de frente, el motor cuenta hoy 1 lote y la norma permite 4 casas; en R3, 6.
2. **La densidad corta mucho más que el FOT en C2A y C3.** Con 30 m² cubiertos por habitante (el tope que Gonzalo aprobó para Tigre):
   - **C2A** (47 ha): tiene FOT 3 pero 300 hab/ha, que da unos **0,9** usables.
   - **C3 y C3A** (54 ha): tienen FOT 1,2 (1,8 frente a Av. Avellaneda) y 200 hab/ha, que dan **0,6**.
   - **Sin el tope**, el motor marcaría como oportunidad multifamiliar lotes de C2A que no rinden.
3. **Los premios del Ley 8912 están reglamentados en el art. 3.20.** Suman hasta 70%, y la densidad sube en el mismo porcentaje (3.20.4):
   - **Por zona:** donde se nota es en **R2** (73 ha, FOT 1,8 que "se incrementará"), en las **torres de R1 y C1** y en **R3**, que llega hasta 1,2.
   - **Lo que lo limita en R2:** la altura (11,20 m, PB+3). Por eso lo realista en R2 es FOT **2,25** con el premio por ancho de parcela.
4. **El motor no conoce las alturas del Código**, porque UrbaSIG no las trae en casi ninguna zona. Con FOS 0,6 casi nunca cortan el FOT de base. Cortan en un caso: **C4Ue**, donde el multifamiliar tiene FOT 2 pero exige planta baja libre y 9 m de altura. Da unos 1,2.
5. **I2, I2A y DI no son zonas de vivienda.** Hoy el motor les cuenta lotes de vivienda. La vivienda unifamiliar va solo como anexo de la industria o el depósito (3.5.10.1), y en lotes de 300 m² comprados antes de 1979 (3.5.10.7). Entre las tres suman 206 ha.
6. **BPN (barrio náutico, 127 ha sobre el río) admite viviendas agrupadas por derecho:**
   - **Indicadores** (3.9.1.13): FOS 0,35, FOT 0,70, 160 hab/ha con infraestructura y PB+2. Da **una casa cada 250 m²**.
   - **Exigencias:** 1,5 cocheras y 1 amarra por vivienda, saneamiento obligatorio (relleno por el art. 84 de la Ley 8912) y factibilidad hidráulica.
7. **Lo demás que da UrbaSIG coincide con el Código.** Las diferencias:
   - **DDP:** es un conjunto ya construido que no se puede modificar.
   - **RR:** multifamiliar solo desde 3.000 m².
   - **C4Ue:** multifamiliar solo con 15 m de frente y 450 m².
   - **Parque de la Reconquista:** tiene subzonas con multifamiliar que hoy quedan sin producto.

## 2. Indicadores por zona (Código 3603/91 vs. lo que usa el motor)

Columnas: Dens. = densidad neta en hab/ha; Altura = altura máxima (cumbrera / techo plano); Parcela = mínima, frente × superficie. **En negrita**, lo que hoy el motor usa distinto o no usa.

| Zona | ha | FOS | FOT | Dens. | Altura | Parcela | Vivienda (Código) | Motor hoy |
|---|---|---|---|---|---|---|---|---|
| C1 | 31 | 0,6 | 3 entre medianeras; torre 3 + premios | 1.400 | 15,60 m; torre 38,40 m | 25 × 750 | Multifamiliar dominante | Multifamiliar, FOT 3 |
| C2 | 50 | 0,6 | 3 | 900 | 14,40 m (PB+4) | 25 × 750 | Multifamiliar dominante | Igual |
| C2A | 47 | 0,6 | 3 | **300** | — | 25 × 750 | Multifamiliar | **FOT 3 sin tope por densidad** |
| C2B | 0,6 | 0,6 | 1,2 | 500 | 9,50 m | — | Uni y multifamiliar complementario | Igual |
| C3 / C3A | 54 | 0,6 | 1,2 (Av. Avellaneda 1,8) | **200** | 10,20 m (PB+2) | 15 × 375 | Multifamiliar complementario | **Multifamiliar sin tope por densidad** |
| C4Ue | 6 | 0,6 | 1,2 comercio / **2 multi** / 1 uni | 500 | **multi 9 m con PB libre** | multi **≥ 15 m y 450 m²** | Multi con deptos de 3 ambientes ≥ 70 m² | **FOT 2 sin la altura ni el mínimo** |
| R1 | 9 | 0,6 | 2,4; torre 2,4 + premios | 900 | 14,40 m; torre 31,80 m | 25 × 750 | Multifamiliar dominante | Igual, sin premios |
| R2 | 73 | 0,6 | **1,8 + premios** | 600 | 11,20 m (PB+3) | 20 × 600 | Uni y multifamiliar dominantes | FOT 1,8 sin premios |
| R3 / R3B | 140 | 0,6 | 1 (hasta 1,2 con premios) | 250 (150 sin cloaca) | — | 15 × 375 | **Varias viviendas por lote (3.5.6.7)** | **1 vivienda por parcela** |
| R3A | 627 | 0,6 | 1 (hasta 1,2) | 170 | — | 15 × 375 | **Ídem R3** | **1 vivienda por parcela** |
| R4 | 42 | 0,5 | 1 | 250 | 9,50 m / 6 m (PB+1) | 15 × 450 | Hasta 2 viviendas en lotes ≥ 500 m² | 1 por parcela (no cambia nada: nunca llega a 4) |
| BPN | 127 | 0,35 (+0,10 anexos) | 0,70 | 160 (140 sin infra) | 10,50 m (PB+2) | 17 × 600 | **Individual o agrupada** | **1 vivienda por parcela** |
| RR | 21 | uni 0,4 / **multi 0,2** | uni 0,6 / **multi 1,4** | uni 200 / multi 400 | uni 6 m / multi 30 m | 15 × 375 | Multi **solo en lotes ≥ 3.000 m²** | **FOT 1, 400 hab/ha y multi a cualquier tamaño** |
| RR Reconquista (Ord. 5951/95) | 185 | por subzona | RUM multi 0,8 / VOAD multi 1,4 | RUM 600 / VOAD 1.000 | 18 m / 40 m | uni 18 × 500; multi ≥ 3.000 m² | Barrios abiertos o cerrados | **Sin producto** |
| DDP | 6 | 0,4 | 1,5 | 600 | 11,20 m | — | **Conjunto existente: "no se puede modificar"** | **Multifamiliar, FOT 1,5** |
| DRC | 10 | 0,6 | 1,2 | 600 | 21 m | 40 × 2.000 | Multifamiliar (Ord. 13.017/21, sin leer) | Multifamiliar, FOT 1,2 |
| I2 / I2A / DI | 206 | 0,6 | 1 / 1 / 1,2 | 120–130 | 11 / 15 m | 15 × 450 (I2) | **Vivienda solo como anexo de la industria** | **Lotes de vivienda** |
| RRE | 15 | 0,6 | 0,6 | 60 bruta | — | 20 × 600 | Vivienda no permanente | 1 por parcela |
| DUE 1a / 1b | 13 | 0,6 | 1,2 | 365 | — | 8 × 130 / 5,5 × 80 | Vivienda social unifamiliar (no está en la 3603) | Multifamiliar condicional |

Sin producto, como hoy: I1 e Ie U4 (industria), los UE 1 a 9 (aeródromo, cementerios, clubes, Armada, Yacht Club, Reserva Ecológica), UE (conjunto habitacional municipal), las cesiones, RC2 y Re2 (inundables y de reserva), el Canal San Fernando (Código suspendido por la Ord. 3045/90), R4Ue (Libertador entre Pasteur y V. Montes: comercio especial con lote mínimo de 1.200 m²) y el Área de Islas, con 93.000 ha de Delta que tiene otro régimen.

## 3. Varias viviendas por lote en R3 y R3A (art. 3.5.6.7)

El uso dominante es la vivienda unifamiliar y la multifamiliar es uso complementario (3.5.6.1). El art. 3.5.6.7 dice cuántas viviendas entran en un lote:

| Lote | Viviendas |
|---|---|
| > 400 m² (R3U00), > 330 m² (R3U0) o > 250 m² (R3U1, R3U2) | 2 |
| > 550 m² | hasta 3 |
| > 700 m² | más de 3: las que den el FOS, el FOT y la densidad |
| Cualquier parcela | más de un dúplex, con frente paralelo a la línea municipal y patio de 4 m de lado y 24 m² cada uno |

**Densidad según los servicios** (3.5.6.7 f, que remite al art. 37 de la Ley 8912):
- 250 hab/ha con infraestructura completa;
- 150 hab/ha con agua pero sin cloaca;
- sin agua ni cloaca, una sola vivienda por lote.

**R3A** usa 170 hab/ha (3.5.6).

**Lo que cambia para el scouting:**
- Con 4 personas por vivienda, como el resto del motor, sale una casa cada **160 m²** en R3 y R3B y una cada **235 m²** en R3A.
- Las 4 casas por derecho que pide la regla de loteo se alcanzan desde 700 m² en R3 y desde unos 950 m² en R3A.
- Los subdistritos U00, U0, U1 y U2 (plano de usos) solo cambian el mínimo para 2 viviendas. Ese mínimo queda por debajo del prefiltro de 433 m², así que no hace falta el plano.
- **Antecedentes con aprobación:** el HCD aprobó barrios en PH dentro de R3 con FOT 1 a 1,2 y 320 a 360 hab/ha. Son las Ord. 6003/95 y 6315/96 (Los Sauces y Los Plátanos, en los anexos del Código). Ese es el techo "con aprobación".
- **Ojo:** el uso complementario "requiere estudio especial" (3.1.1.3). Es por derecho, pero con plano visado por Planeamiento.

Esto no contradice lo que Gonzalo decidió el 14/11 ("R3, R3A, R3B y R4 no admiten multifamiliar"): son casas, no un edificio de departamentos, y entran en la vía loteo / agrupadas.

## 4. Tope por densidad

La densidad limita los habitantes, no los m². Con el criterio de Tigre (30 m² cubiertos por habitante, unos 2 por dormitorio), el FOT que se puede usar con departamentos vendibles es este:

| Zona | FOT Código | Densidad | FOT por densidad (× 30 m²) | Usable |
|---|---|---|---|---|
| C1 | 3 | 1.400 | 4,2 | 3 |
| C2 | 3 | 900 | 2,7 | **2,7** |
| C2A | 3 | 300 | 0,9 | **0,9** |
| C2B | 1,2 | 500 | 1,5 | 1,2 |
| C3 / C3A | 1,2 (1,8) | 200 | 0,6 | **0,6** |
| C4Ue (multi) | 2 | 500 | 1,5 | **1,2 por altura** (sección 5) |
| R1 | 2,4 | 900 | 2,7 | 2,4 |
| R2 | 1,8 | 600 | 1,8 | 1,8 |
| RR (multi ≥ 3.000 m²) | 1,4 | 400 | 1,2 | **1,2** |
| DRC | 1,2 | 600 | 1,8 | 1,2 |

**Para pasar los 1.300 m² construibles del criterio multifamiliar** hace falta un lote de **1.450 m²** en C2A o de **2.170 m²** en C3. En el Código no encontré cómo se cuentan los habitantes; la regla de 2 por dormitorio es la de la Ley 8912, la misma que usa Tigre.

## 5. Alturas y premios

**Alturas del Código:**
- **Torres:** C1 15,60 m entre medianeras y torre hasta 38,40 m (3.6.1.4); R1 14,40 m entre medianeras y torre 31,80 m sin basamento (3.7.1.4).
- **Edificios entre medianeras:** C2 14,40 m; R2 11,20 m; C3 10,20 m; DDP 11,20 m; C2B 9,50 m.
- **Barrios y casas:** BPN PB+2 y 10,50 m; R4 9,50 m a cumbrera; RR multifamiliar 30 m; Reconquista RUM 18 m y VOAD 40 m; DRC 21 m.

Con FOS 0,6 y la regla de Tigre (FOT ≤ FOS × niveles) **solo corta en C4Ue**. Ahí el multifamiliar exige planta baja libre para estacionamiento y llega a 9 m, o sea dos pisos sobre la PB libre: 0,6 × 2 = 1,2, contra el FOT 2 que usa el motor. C4Ue además pide frente ≥ 15 m, lote ≥ 450 m² y departamentos de 3 ambientes de al menos 70 m², con uno solo de 2 ambientes (50 m²) por piso.

**Premios del art. 3.20** (Ley 8912 art. 47). Valen para el FOT y la densidad de todas las zonas y suman como máximo 70%:

| Premio | Cuánto | Tope |
|---|---|---|
| Ancho de parcela | 2% por metro sobre 10 m en los primeros 10 m, después 1% por metro | 25% (20% en industria) |
| Separación de ejes laterales | 3% desde 4 m y 3% por metro adicional | 15% por eje, 30% en total |
| Retiro voluntario de frente o fondo | 3% por metro | 15% |
| FOS menor que el máximo | 1% por cada punto menos | 10% |
| Espacio público al frente | 0,5% por metro desde 10 m | 10% |

En industria la suma tiene tope de 15% (I2) o de 30% (las demás zonas industriales).

**Lo factible por zona**, con el criterio de Tigre (lote de al menos 2 parcelas mínimas):
- **R2:** FOT 1,8 × 1,25 = **2,25**, que entra en PB+3 con FOS 0,6 (2,4). La densidad sube a 750.
- **R3:** hasta **1,2** (3.5.6.3).
- **R1 y C1 en torre:** ancho + separación lateral (la torre ya exige 4 m por lado) dan **R1 ~3,1 y C1 ~3,9**. Pero hacen falta lotes de 1.500 m² y 50 m de frente, que en el centro casi no hay.
- **C2 y C1 entre medianeras:** no ganan nada, porque la altura ya topea en 3.
- **C2A y C3:** los sigue cortando la densidad, aun con el premio.

## 6. Agua, ribera y aeródromo

- **BPN** es zona de "saneamiento obligatorio" (art. 84 de la Ley 8912), con relleno y desagües a cargo del propietario. Pide factibilidad hidráulica para los proyectos de conjunto (3.9.1.34; antecedente: Punta Chica Village). En BPN Especial, UE y RRE, los locales habitables van sobre la cota +4,00 IGM.
- **Camino de sirga** (Código Civil y Comercial, art. 1974): 15 m sobre el Río Luján y el Canal San Fernando. Afecta los lotes de BPN sobre el agua. El motor ya lo calcula en Tigre (`productos.sirga`); en San Fernando falta la capa de ríos.
- **RC2 y Re2** son inundables o de reserva y necesitan estudio hidráulico aprobado por la Provincia (3.13). Sin producto, como hoy.
- **Aeródromo San Fernando** (UE 2, 166 ha, en el medio del partido). Toda construcción en su entorno queda sujeta a las pendientes de aproximación, con autorización aeronáutica (3.8.1, Código Aeronáutico art. 197). Pesa para una torre de R1 o C1, o para los 21 m del DRC, que está a unos 1,5 km.

## 7. Loteo, cocheras y otras señales

- **Loteo:**
  - Toda subdivisión de más de 10.000 m², o de una manzana entera, pide un anteproyecto de conjunto (3.2.1.1).
  - El plano se aprueba recién con pavimento de hormigón, agua corriente, electricidad y desagües hechos o habilitados (3.2.1.3).
  - Las parcelas nuevas tienen que tener una relación ancho/fondo de al menos 1/3 (3.2.1.4). Las cesiones son las del art. 56 de la Ley 8912 (señal ya en Tigre).
- **Cocheras:**

  | Zonas | Exigencia |
  |---|---|
  | C1, C2, R1, R2 y DDP (multifamiliar y oficinas) | 3,5 m² por habitante. Se pueden resolver con servidumbre en otro predio a menos de 200 m. No se exigen con frente < 12 m o lote < 360 m² (3.5.1.5) |
  | RR | 50% de las unidades |
  | Reconquista | 75% de las unidades |
  | BPN | 1,5 por vivienda |

- **Retiros por trama viaria** (3.3), de 1,50 a 2 m desde la línea municipal: Alvear, 9 de Julio, Ayacucho, Constitución, Perón (entre Colón y H. Dunant), 3 de Febrero, Libertador, H. Yrigoyen (9 m a eje) y Uruguay (8 m).
- **Excepciones del HCD:** salen en casi todos los boletines, pero son regularizaciones de obras hechas (con "recargo proporcional al beneficio") o habilitaciones comerciales. No son una vía para proyectos nuevos, salvo los barrios en PH de la sección 3.

## 8. Lo que falta

- **DRC y DI (Ord. 13.017/21).** El motor usa lo de UrbaSIG: DRC con FOT 1,2, 600 hab/ha, 21 m y retiros "según la ordenanza". FOT 1,2 con 21 m de altura parece bajo; puede haber un FOT mayor en la ordenanza. Hay que pedir el texto al municipio o buscarlo en el Boletín de 2021.
- **DUE 1a y 1b** no figuran en la 3603. Son de vivienda social con lotes de 80 a 130 m² y quedan debajo del prefiltro.
- **Reconquista:** UrbaSIG da un solo polígono para todas las subzonas (RUM, CR, VOAD, ZEU, ZUM, CRP). Asignar una subzona a un aviso necesita el plano del Anexo 1 de la Ord. 5951/95, que no está en el PDF.
- **Las Islas** (Delta de San Fernando) tienen su propio régimen y quedan fuera del alcance.

## 9. Decisiones para Gonzalo

| # | Propuesta | Qué cambia | Superficie |
|---|---|---|---|
| 1 | **R3, R3A y R3B: varias casas por lote** (3.5.6.7) | Casas por derecho = mín(escalón por superficie, densidad × sup ÷ 4): R3 1 cada 160 m², R3A 1 cada 235 m². Desde 4 cuentan para la vía loteo. Flags `requiere_cloaca` (sin cloaca, 150 hab/ha) y `uso_complementario_estudio_especial`. La vía "con aprobación" usa 320–360 hab/ha (antecedentes en PH) | 767 ha |
| 2 | **Tope por densidad de 30 m²/hab**, como en Tigre | C2A 3 → 0,9; C3 1,2 → 0,6; C2 3 → 2,7; RR 1,4 → 1,2 | 150 ha |
| 3 | **Premios del art. 3.20** donde son factibles (lote ≥ 2 parcelas mínimas, como en Tigre) | R2 1,8 → 2,25 (densidad 750); R3 → 1,2; torres R1 ~3,1 y C1 ~3,9 | 220 ha |
| 4 | **BPN: viviendas agrupadas** (3.9.1.13) | Casas por derecho = 160 hab/ha × sup ÷ 4 (1 cada 250 m²), FOT 0,70. Flags de saneamiento obligatorio y relleno, factibilidad hidráulica, 1,5 cocheras y 1 amarra por casa, y sirga | 127 ha |
| 5 | **I2, I2A y DI sin producto de vivienda** (3.5.10.1, 3.5.10.7) | Dejan de contar lotes de vivienda. Los galpones ahí siguen como uso conforme | 206 ha |
| 6 | **Correcciones puntuales del Código** | C4Ue multi con FOT 1,2 (altura y PB libre) y solo con frente ≥ 15 m y ≥ 450 m²; RR multi solo desde 3.000 m² (FOS 0,2, FOT 1,4), y por debajo 1 casa con FOT 0,6; DDP sin producto (conjunto que no se modifica) | 33 ha |
| 7 | **Parque de la Reconquista**: dar producto a la subzona residencial | Hoy sin producto. Opción: RUM (casas en lotes de 500 m²; multi FOT 0,8 y 600 hab/ha desde 3.000 m²) con flag `verificar_subzona_reconquista` | 185 ha (25 ha residenciales) |
| 8 | **Señales sin cambio de números** | Aeródromo (torres y DRC), anteproyecto de conjunto > 10.000 m², infraestructura para aprobar el loteo, cotas IGM en la ribera, y la capa de ríos para la sirga | — |

Los umbrales de San Fernando (350/450 USD/m², 1.300 m², loteo 0,6) no cambian. Como en Tigre, las propuestas se aplicarían en `tools/municipio_pba.py`, nunca a mano en el CSV, y en `municipio.yaml`.

### 9.1 Qué hace el motor (Gonzalo aprobó las 8 propuestas, 26/11/2026)

Todo sale de `tools/municipio_pba.py` (`PARTIDOS['san_fernando']['planillas']`, que corrige a UrbaSIG con el Código) y de `municipios/san_fernando/municipio.yaml`. Los tests están en `tests/test_san_fernando_normativa.py`.

1. **R3, R3A y R3B.** La columna nueva `casas_por_lote` (`400:2;550:3;700:`) da el tope de casas por superficie. La densidad da una casa cada `m2_terreno_por_unidad` (R3 y R3B 160 m², R3A 235 m²). Las casas son el producto "agrupadas a la calle" por derecho y cuentan para la vía loteo. Con aprobación: una cada 125 m² (`m2_unidad_acceso_comun`, 320 hab/ha). Ejemplos: R3A con 1.000 m² y 20 m de frente da 4 casas (antes, 1 lote); R3 da 6. Flags `casas_por_lote_3567`, `uso_complementario_estudio_especial` y `requiere_cloaca_casas`. Edificio de departamentos, igual que antes: no.
2. **Tope por densidad.** `productos.m2_por_habitante: 30`: C2A pasa de 3 a 0,9 y C3 de 1,2 a 0,6 (`fot_efectivo`, `limite_fot`).
3. **Premios.** `fot_max`: R2 2,25, R1 3,1, C1 3,9 y R3 1,2, con el flag `premio_ley_8912`. Valen en lotes de al menos 2 parcelas mínimas (`premio_ley_8912.parcelas_min: 2`), como en Tigre. Con `premio_ley_8912.densidad: true`, la densidad sube en el mismo % (3.20.4), tanto para el tope por densidad como para las casas y los departamentos. Ejemplo: R3A con 1.000 m² y 30 m de frente da 5 casas.
4. **BPN.** Casas agrupadas por densidad (una cada 250 m², `casas_por_lote: 0:`), con FOT 0,70 y FOS 0,35. Flags `agrupadas_bpn_3913` y `saneamiento_obligatorio_bpn`.
5. **I2, I2A y DI:** sin producto de vivienda (`sin_vivienda`).
6. **Correcciones puntuales:** C4Ue con FOT 1,2 y multifamiliar desde 450 m² (`multifamiliar_sup_min`; el frente de 15 m va en el flag). RR con FOS 0,2, FOT 1,4 y 400 hab/ha, y multifamiliar desde 3.000 m²; por debajo, lotes de 15 × 375. DDP sin producto.
7. **Reconquista.** La designación "RR: RUM-…" tiene ahora las cifras del sector RUM: lotes de 18 × 500 y, desde 3.000 m², multifamiliar con FOT 0,8 y 600 hab/ha. Lleva el flag `verificar_subzona_reconquista`.
8. **Señales:**
   - **Aeródromo:** `cerca_aerodromo` sale cuando el aviso se evalúa en C1, R1, DRC o Reconquista a menos de 3 km de UE 2 (`productos.flags.cerca_de_zona`).
   - **Loteo:** con calle interna, `cesion_ley_8912` e `infraestructura_para_aprobar_loteo`, más `cesion_ley_14449` desde 5.000 m². `manzana_7400` y `ue_10000` citan el anteproyecto de conjunto (3.2.1.1).
   - **Sirga:** se descuenta como en Tigre, con `fuentes/rios_osm.geojson` (`python tools/municipio_pba.py san_fernando --solo-rios`). Solo cuentan los ríos y los canales con nombre: los zanjones sin nombre y el arroyo Pavón no.

Sin medir sobre avisos reales: San Fernando todavía no tuvo su primera corrida. En la agenda va después de CABA y Tigre.
