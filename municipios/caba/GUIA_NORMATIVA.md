# CABA — guía de normativa para evaluar un lote

Lectura rápida: conclusiones, cómo se calcula lo construible según el lote y la zona, y qué buscar que el resto no ve. Estudio del 19/11/2026.

**Estado:** desde el 19/11/2026 el motor (`src/motor_caba.py`) aplica el método de la sección 6, con las decisiones de Gonzalo de la sección 8. Lo que cambió respecto del motor anterior está en la sección 7.

**Fuentes** (los PDFs están en Drive, `01 - PROYECTOS CLAUDE/scouting-caba/`):
- Código Urbanístico (CU), texto consolidado al 31/12/2024. Incluye la Ley 6.776 (BOCBA 26/12/2024), que cambió casi todo el Título 6. Está en `codigo_urbanistico/`.
- Código de Edificación (CE), Ley 6.100 con la modificación de la Ley 6.438. Está en `codigo_edificacion/`.
- Plusvalía: Ley 6.062, texto de la Ley 6.710 (arts. 500-501 del Código Fiscal), y el Decreto 105/2019.

---

## 1. Conclusiones

1. **En CABA el FOT no da derecho a construir.** Lo que se puede construir lo define la **envolvente** del CU: altura de la unidad de edificabilidad, dos niveles retirados, área entre la L.O. y la L.F.I., y patios. El FOT que muestra Ciudad 3D viene del viejo Código de Planeamiento y **solo sirve para calcular la plusvalía**.
2. **"Usar todo el FOT"** solo es posible cuando la envolvente es mayor que FOT × superficie. Suele darse en:
   - esquinas;
   - lotes de poca profundidad;
   - zonas con FOT bajo (1 a 1,6) y altura media o alta.

   **No se da** en USAB 2 con FOT viejo alto, como R2a o C3 con FOT de 3,5 a 4,9.
3. **La plusvalía se cobra sobre el 80% de los m².** Hasta **1,25 × FOT × superficie no se paga nada**.
4. **La plusvalía casi nunca define el negocio.** Ronda 5 a 60 USD por m² por encima de ese umbral. **Lo que define es cuántos m² entran en la envolvente**, y ahí el motor tiene el error más grande.
5. **El código de edificación casi no recorta m², pero sí eficiencia.** Lo que pesa es el núcleo (escalera, antecámara, ascensor), los patios y la altura de piso. En lotes angostos el núcleo pesa más.

---

## 2. Unidades de edificabilidad (CU art. 6.2 y 6.3)

| Unidad | Altura máx. sobre L.O. | PB mínima | Retiros por encima | Pisos con 2,80-2,84 m | Pisos con 2,90 m | Patio vertical mín. |
|---|---|---|---|---|---|---|
| C.A. (Corredor Alto) | 38 m | 3,00 m | 2 | PB+12 | PB+12 | 26 m², lado 4 m |
| C.M. (Corredor Medio) | 31,20 m | 3,00 m | 2 | PB+10 | PB+9 | 26 m², lado 4 m |
| U.S.A.A. | 22,80 m | 3,00 m | 2 | PB+7 | PB+6 | 26 m², lado 4 m |
| U.S.A.M. | 17,20 m | 3,00 m | 2 | PB+5 | PB+4 | 26 m², lado 4 m |
| U.S.A.B. 2 | 14,60 m (plano límite) | 2,60 m | ninguno | PB+4 | PB+4 | 20 m², lado 4 m |
| U.S.A.B. 1 | 12 m (plano límite) | 2,60 m | ninguno | PB+3 | PB+3 | 20 m², lado 4 m |
| U.S.A.B. 0 | 9 m (plano límite) | 2,60 m | ninguno | PB+2 | PB+2 | 20 m², lado 4 m |

- **Las alturas del código están pensadas para 2,80-2,84 m entre pisos.** El CE exige 2,60 m libres en locales de primera clase (art. 3.3.1.2.1); con una losa fina da 2,80.
- **Retiros (art. 6.3):**
  - Rigen en C.A., C.M., U.S.A.A. y U.S.A.M., entre medianeras o semilibre.
  - **Primer nivel:** retirado 2 m de la L.O., de hasta 3 m de alto.
  - **Segundo nivel:** retirado 4 m de la L.O. **y** 4 m de la L.F.I., dentro de un plano límite a +7 m de la altura máxima.
  - No hace falta el retiro de 4 m al contrafrente si el lote solo da la banda mínima edificable.
  - Ciudad 3D informa ese plano límite como `altura_max_plano_limite`: 45 / 38,2 / 29,8 / 24,2.
- **Basamento (C.A. y C.M.):** hasta 6 m de altura (PB + 1) entre la L.O. y la **L.I.B.**, pasando la L.F.I. El 80% de lo que queda entre la L.F.I. y la L.I.B. tiene que ser techo verde (art. 6.4.3.3).
- **Por encima del plano límite no se cuentan m² habitables (art. 6.3.1).** Solo van tanques, sala de máquinas, la caja de escalera a la azotea (+2,50 m en USAB, +3,25 m en el resto), parapetos y piscinas descubiertas (+1,20 m).
- **Subsuelo:** se puede construir hasta la L.I.B. (art. 6.6).

## 3. Área edificable en planta (CU art. 6.4)

- **Profundidad edificable.** La **L.F.I.** está a ¼ de la distancia entre las L.O. opuestas de la manzana: en una manzana típica de 86,6 m queda a 21,65 m. La **L.I.B.** está a ⅓ (28,9 m).
- **Banda mínima garantizada:** 16 m desde la L.O. (art. 6.4).
- **Manzanas atípicas** (semisuma de lados menor a 62 m, menos de 4.000 m², o 3, 5 o más lados): la L.F.I. la fija un acto administrativo. Ciudad 3D lo informa en `manzanas_atipicas`.
- **Esquina:** la planta llega hasta la L.O.E. Se pierde el triángulo de la ochava, que según el ángulo y el ancho de las calles mide 4 a 7 m (cuadro 6.4.1.3.1). Por encima de 3 m se puede volar hasta el encuentro de las L.O.
- **Lote pasante (art. 6.4.7):** cada frente se calcula por separado, como si fueran dos lotes virtuales.
- **Lotes que no llegan a la L.F.I.:** hay que dejar libre el fondo: 4 m en USAB, 6 m en USAM y USAA, 8 m en C.M. y C.A. (art. 6.4.2.4).
- **Compensar la L.F.I. (art. 6.4.2.2):** si el lindero ya construyó más allá de la L.F.I., se la puede pasar compensando superficie. Hay límites según el frente (10 m) y no se puede en USAB 0.
- **Espacio urbano entre volúmenes de la misma parcela:** lado mínimo 4 m y altura/distancia ≤ 1,5. Los locales de primera clase solo pueden ventilar a patio vertical desde la altura máxima para arriba (CE art. 3.3.2.3).
- **Ciudad 3D:** `sup_edificable_planta` sigue razonablemente a la profundidad del lote. Vale la parcela entera en lotes de menos de 20 m de fondo, y alrededor de 0,6-0,7 de la parcela en los de más de 35 m. Sirve como planta edificable (P). En cambio, `sup_max_edificable` no es confiable: en USAB 0 (9 m) da el equivalente a 4,8 pisos.

## 4. Tipologías (CU art. 6.5)

- **Entre medianeras:** es el caso general.
- **Perímetro semilibre:**
  - **Obligatorio** si el frente supera 12 m y el lote está flanqueado por espacio urbano de edificios de perímetro libre o semilibre.
  - **Opcional** en USAB, o si linda con ese tipo de espacio urbano o con espacio público.
  - **Separación lateral:** 3 m si el frente es de hasta 10 m; 4 m entre 10 y 14 m; 6 m de 14 m en adelante (4 m como máximo en USAB).
- **Perímetro libre:**
  - **Dónde va:** en C.A., C.M., U.S.A.A. y U.S.A.M. solo si el lote está flanqueado por edificios de perímetro libre o semilibre **y** tiene 26 m de frente o más. En USAB se permite siempre. También va en una parcela única en la manzana.
  - **Planos límite, sin retiros:** C.A. 45 m, C.M. 38,20 m, U.S.A.A. 29,80 m, U.S.A.M. 24,20 m.
  - **Separaciones:** 6 m a las medianeras (4 m en USAB) y 12 m entre volúmenes de la misma parcela.
- **Combinación de tipologías (6.5.4):**
  - con un frente de más de 30 m, si el lote está flanqueado por un perímetro libre o semilibre y por uno entre medianeras;
  - con un frente de más de 34 m, si está entre dos edificios entre medianeras.

## 5. Plusvalía — Derecho para el Desarrollo Urbano (Ley 6.062 / 6.710)

```
plusvalía (UVA) = max(0, 0,8 × m² sobre cota de parcela − FOT × superficie) × incidencia (UVA/m²) × alícuota
```
- **Lo que no computa:** balcones, lo construido por encima del plano límite según el art. 6.3.1, y los m² comprados como capacidad constructiva transferible o adicional.
- **Incidencia y alícuota:** salen de Ciudad 3D (`incidencia_uva`, `alicuota`). Las alícuotas son 10/18/27/35% según la zona (texto de 2018; la API devuelve la vigente). En la caché, la incidencia va de 40 a 140 UVA/m².
- **Si la parcela tiene varios FOT** (medianera, semilibre, libre), se usa el de la tipología del proyecto.
- **Verificado:** las 1.066 respuestas de `/cur3d/calcular_plusvalia` en caché coinciden exacto con esta fórmula. Da 0 en todos los casos con m² ≤ 1,25 × FOT × superficie.
- **Cuándo se paga:** con los derechos de delineación y construcción, al pedir el permiso. No hay exenciones generales.

## 6. Método de cálculo (vigente desde el 19/11/2026)

Para cada aviso con parcela de Ciudad 3D:

1. **P** = `sup_edificable_planta`. Si no viene, se usa frente × min(fondo, máx(16, distancia a la L.F.I.)). En una esquina, toda la parcela menos la ochava.
2. **Planta neta** = P × eficiencia: 0,85 con frente de hasta 10 m y 0,75 con frente mayor, para descontar patios y espacio urbano lateral. Sin frente conocido se usa 0,85, para no perder oportunidades. El frente es el del catastro si la parcela coincide con el aviso, y si no, el del texto.
3. **Pisos completos** = 1 + piso((altura máx. − PB) ÷ 2,90 m), con la columna "2,90 m" de la sección 2.
4. **Retiros** (C.A., C.M., U.S.A.A., U.S.A.M.):
   - primero: planta con 2 m menos de fondo;
   - segundo: planta con 8 m menos de fondo, o 4 m menos si el lote solo da la banda mínima.
5. **Basamento** (C.A. y C.M.): suma la franja entre la L.F.I. y la L.I.B. en PB y primer piso. Se toman 7,2 m de fondo extra y solo si se conoce el frente.
6. **m² construibles** = la suma de todo lo anterior. **Ya no se usa FOT × superficie como m² construibles.**
7. **Plusvalía** con la fórmula de la sección 5, calculada en el motor con los datos de Ciudad 3D (no consulta la API de plusvalía). El FOT es el de entre medianeras.
8. **Incidencia** = (precio + plusvalía) ÷ m² construibles.
9. **Señal de linderos**, solo en oportunidades, casi y grandes predios. Para cada lindero lateral se consulta su catastro (pisos) y su unidad de edificabilidad:
   - si el lindero es más alto que la unidad por más de 1,40 m (y la unidad no es USAB 0 ni distrito especial), sale "potencial extra, revisar por completamiento y esquina" con el detalle;
   - lo mismo si el lindero está en una unidad más alta.

   **No cambia los m²:** se revisa a mano.

**Ejemplo:** lote típico de 8,66 × 43,30 m (375 m²) en U.S.A.M., en una manzana estándar.
- P = 8,66 × 21,65 = **187,5 m²**. Planta neta con 0,85: **159 m²**.
- Pisos completos PB+4 = 5 × 159 = 796 m².
- Retiro 1 (fondo 19,65 m): 145 m². Retiro 2 (fondo 13,65 m): 100 m².
- **Total ≈ 1.040 m², unas 2,8 veces el terreno.**
- Con un FOT viejo de 1,6, no se paga plusvalía hasta 750 m². Sobre lo que pasa: (0,8 × 1.040 − 600) = 232 m² gravados. Con 100 UVA × 27% da unas 6.300 UVA, del orden de USD 9.000, unos 9 USD por m² construible.

**Lo que el código de edificación agrega a la eficiencia:**
- caja de escalera obligatoria desde 12 m de altura en vivienda (art. 3.4.6.3);
- antecámara de escalera en vivienda de más de 30 m;
- dos escaleras si una planta supera los 600 m² (art. 3.4.7.6), y ningún punto a más de 30 m de un medio de salida;
- unidad de vivienda mínima de 18 a 25,5 m², hasta el 50% de las unidades (art. 3.8.9.1);
- en lotes de hasta 8,66 m de ancho, los pasillos internos pueden bajar a 0,95 m.

**Cocheras (CU art. 3.14.8.1):** son optativas si se cumple alguna de estas condiciones:
- el ancho libre es menor de 10 m;
- la superficie es menor de 300 m²;
- es vivienda social;
- el edificio está protegido;
- es USAB al sur del eje San Juan–Directorio–Olivera–Pedro Goyena–Alberdi.

## 7. Qué corrigió el cambio del 19/11/2026 (motor anterior, corrida del 19/11 a las 3:00)

| Tema | Motor anterior | Normativa | Efecto |
|---|---|---|---|
| Escenario "FOT" | m² = superficie × el mayor FOT, sin plusvalía, y se queda con el escenario de menor incidencia | El FOT no es un derecho; manda la envolvente | **Falsos positivos:** 102 de 182 oportunidades salen de ese escenario, y 72 quedan afuera si se recalculan con la envolvente |
| Plusvalía cuando la API da 0 | Cobra (m² − FOT × sup) × incidencia × alícuota y marca `plusvalia_estimada` | El 0 es correcto: hasta 1,25 × FOT no se paga, y sobre el resto rige el 80% | **Falsos negativos:** 29 hits con plusvalía de más; unos 54 "casi" podrían pasar a oportunidad |
| Pisos | altura del plano límite ÷ 3 m, todos con planta completa | PB de 3 o 2,6 m + pisos de 2,80-2,90 m; los retiros son más chicos | USAB 2 queda corto (4 pisos en vez de 5); USAM queda un poco largo |
| Planta | `sup_edificable_planta` × 0,65 | Patios de 20-26 m²: alrededor de 0,85 en lotes angostos | Subestima m² en lotes típicos |
| `sup_max_edificable` de Ciudad 3D | Se usa cuando viene (161 parcelas) | Da valores imposibles (4,8 pisos en 9 m) | **Falsos positivos** en esas parcelas |
| FOT de perímetro libre (7,0) | Se usa si es el mayor | Exige un frente de 26 m o más y linderos de perímetro libre | **Falsos positivos** |

## 8. Decisiones de Gonzalo (19/11/2026)

1. **Altura entre pisos:** 2,90 m.
2. **Eficiencia de planta:** 0,85 con frente de hasta 10 m y 0,75 con frente mayor.
3. **Escenario FOT:** se saca. Los m² salen siempre de la envolvente, con la plusvalía bien calculada (80%).
4. **Completamiento y lindero a esquina:** van como señal, "potencial extra, revisar por completamiento y esquina". No se suman a los m².
5. **Sin decidir:** si los m² construibles son brutos o vendibles. Siguen siendo brutos, cubiertos, como antes.

Los parámetros están en `municipios/caba/municipio.yaml`, sección `caba`.

## 9. Oportunidades que pasan desapercibidas

1. **Completamiento de tejido (art. 6.5.5).** Si un lindero supera la altura de la unidad, el edificio nuevo se adosa y puede igualar sus niveles.
   - **Tipo A, linderos de igual altura** (diferencia de hasta 1,40 m) y separados hasta 26 m sobre la L.O.: se iguala la altura en cualquiera de las parcelas del medio. Rige en U.S.A.M., U.S.A.A., C.M. y C.A.
   - **Tipo B, linderos de distinta altura:**
     - con frente de hasta 10 m, hay que dejar 3 m con la altura menor;
     - con frente de 10 a 26 m, la altura mayor puede ocupar hasta ⅔ del frente y hasta 13 m;
     - **en USAB 1 y 2 se llega hasta el doble de la altura de la unidad**, adosado al lindero alto en hasta 5 m de frente.
   - **Esquinas:** si un lindero es más alto, se toma su altura dejando 3 m con el lindero más bajo.
   - **No rige en USAB 0, ni en las APH y urbanizaciones determinadas**, que tienen normas propias.
   - **Cómo detectarlo:** Ciudad 3D da `parcelas_linderas`, y el catastro de cada lindero da `pisos_sobre_rasante`.
2. **Lote lindero a una esquina de mayor altura (art. 6.4.6).** Si en una esquina las dos calles tienen distinta altura, la mayor (por ejemplo, la de la avenida) se extiende por la calle transversal hasta la prolongación de la L.F.I. La parcela que corta esa línea se queda con al menos 5 m de banda con la altura mayor. Esos lotes se publican como USAB o USAM.
3. **Edificio existente con más m² que la envolvente.** Edificios y galpones viejos hechos con el código anterior pueden tener más m² que los que hoy entran en una obra nueva. Reciclar los conserva:
   - en una reforma de menos del 50% que no toca la planta baja, no se exigen cocheras (art. 3.15.1);
   - en una reconversión, el Consejo puede elevar el arranque del espacio urbano (art. 6.4.4.2);
   - el catastro ya trae `superficie_cubierta` y `pisos_sobre_rasante`.
4. **Capacidad constructiva adicional (Título 10).** Ciudad 3D la informa en el campo `cca`.
   - **R-CCA (parcelas receptoras, 24 en caché):** pueden superar el plano límite comprando certificados, hasta 40 a 68 m. Están sobre Cabildo, Córdoba, Rivadavia, Acoyte y Alberdi, y en el entorno Azopardo. No llevan basamento y exigen tipologías según el frente: 20, 25 o 34 m.
   - **E-CCA (parcelas emisoras, 120 en caché):** están en los polígonos del Área de Desarrollo Prioritario Sur: La Boca, Pompeya-Parque Patricios, Constitución, Barracas, Villa Olímpica y Lugano. Una obra nueva que agote su capacidad y destine al menos 60% a vivienda colectiva **genera certificados** por el 100% de los m² de vivienda (el 40% en otros usos, y ×1,1 en Constitución). Los certificados se venden o sirven para pagar plusvalía. **Es un ingreso extra que el aviso no muestra.** Falta averiguar a cuánto se venden.
   - **Área de Desarrollo Prioritario Sur** (campo `adps`, 577 en caché): la vivienda paga 50% menos de derechos de delineación y construcción, salvo en el sector entre San Juan, Huergo, Vélez Sarsfield y Entre Ríos.
5. **Lotes grandes:**
   - desde 2.500 m² se puede redistribuir la capacidad dentro de la parcela (art. 10.4);
   - si los dueños de una manzana juntan 5.000 m² (o más de la mitad, en manzanas de menos de 10.000 m²), pueden pedir un Plan de Detalle con normas propias (art. 10.5);
   - con más de 30 o 34 m de frente se pueden combinar tipologías.
6. **Áreas de Renovación Urbana linderas a autopistas** (art. 7.2.11): si el centro de manzana queda entre las líneas de retiro, se puede ocupar toda la parcela. Ojo con la franja no edificable de 12 m (6 m en la AU7).

## 10. Trampas (bajan el valor o traban el permiso)

- **Catalogación:**
  - integral o estructural: no se puede demoler (el motor ya los descarta);
  - cautelar: va a consulta.
  - Un lindero integral o estructural obliga a un **retiro lateral de 3 m** desde la altura de su fachada (art. 9.1.4.2). Cualquier lindero catalogado obliga a consultar.
- **Ley 3.056 (edificios anteriores a 1941):** sin resolver, piden consulta al CAAP, con demora y riesgo de catalogación. **"DESESTIMADO" ya está libre.** Lo informa `catalogacion.ley_3056` y `estado`.
- **Riesgo hídrico:**
  - no se puede extender el subsuelo bajo el centro de manzana;
  - no se admite el 30% de centro de manzana sin suelo absorbente;
  - no se permite hundir la planta baja.
- **Ensanche o apertura de calle:** se pierde superficie (Título 5). Lo informa `afectaciones`.
- **Cono de Aeroparque y cinturón digital** (más de 35 m): el plano límite lo fija otro organismo (arts. 6.8 y 6.9).
- **USAB 0:** sin completamiento, sin compensación de L.F.I. y sin capacidad constructiva adicional.
- **Lotes de menos de 300 m²:** el Consejo puede evaluar el perfil edificable caso por caso según el entorno (art. 6.3). Puede jugar a favor o en contra, así que hay incertidumbre.
- **Pin del portal sobre otra parcela:** con superficie de catastro distinta en más de ±15%, el cálculo es de la parcela vecina. Ya sale como alerta.

## 11. Checklist manual de un hit

1. Abrir la parcela en Ciudad 3D y confirmar la unidad, la L.F.I., la catalogación y las afectaciones.
2. Revisar los linderos: altura, si están consolidados (art. 6.10.1) y si dan completamiento.
3. Ver si es esquina o lote pasante, y si la manzana es atípica.
4. Revisar la Ley 3.056 y los linderos catalogados.
5. Recalcular los m² con la sección 6 y la plusvalía con la API.
6. Si tiene `cca` o `adps`, sumar el valor de los certificados o la reducción de derechos.
