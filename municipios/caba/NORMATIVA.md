# CABA — metodología y decisiones a validar

> **Normativa y método de cálculo:** ver [GUIA_NORMATIVA.md](GUIA_NORMATIVA.md) (Código Urbanístico con la Ley 6.776, Código de Edificación y Ley 6.062). Este archivo resume cómo lo aplica el motor y las decisiones.

**Tipo A** (edificabilidad por parcela). El motor propio está en `src/motor_caba.py` y no usa capa de zonas. Consulta la API pública que usa Ciudad 3D (`epok.buenosaires.gob.ar`), probada el 14/11/2026 con 6 parcelas reales:

| Dato | Endpoint |
|---|---|
| Parcela en el pin → SMP, superficie, frente | `/catastro/parcela/?lng=&lat=` |
| FOT (medianera, semi libre, perímetro libre), altura del plano límite, distrito, incidencia de la Ley 6062 (UVA/m²), catalogación, afectaciones, APH | `/cur3d/seccion_edificabilidad/?smp=` |
| Linderos (solo hits): pisos sobre rasante | `/catastro/parcela/?smp=` |
| Plusvalía para un área dada (ya no se consulta: el motor aplica la misma fórmula) | `/cur3d/calcular_plusvalia/?smp=&area_edificar=` |
| Geocodificación de avisos sin pin | USIG `normalizar_y_geocodificar_direcciones` |
| Valor de la UVA | API del BCRA (variable 31) |

Todo queda en caché en `data/cache_caba.json`: una consulta por parcela, nunca más.

## Cálculo (decidido por Gonzalo el 19/11/2026)

1. **m² construibles = envolvente del Código Urbanístico.** El FOT de Ciudad 3D no da derecho a construir: solo fija la plusvalía.
   - **Pisos:** PB de 3 m (2,60 m en USAB) + pisos de 2,90 m hasta la altura de la unidad. Más los dos niveles retirados en C.A., C.M., U.S.A.A. y U.S.A.M., y el basamento hasta la L.I.B. en C.A. y C.M.
   - **Planta:** la superficie edificable en planta de Ciudad 3D (L.O. a L.F.I.), escalada a la superficie del aviso, × eficiencia: 0,85 con frente de hasta 10 m y 0,75 con frente mayor.
   - Detalle y ejemplo en la sección 6 de la guía.
2. **Plusvalía:** max(0, 0,8 × m² − FOT entre medianeras × superficie) × incidencia UVA × alícuota (Ley 6.062, texto de la Ley 6.710). Se calcula en el motor: coincidió exacto con las 1.066 respuestas de la API. Hasta 1,25 × FOT no se paga.
3. **Incidencia total:** (precio + plusvalía en USD) ÷ m² construibles. La UVA sale del BCRA y el dólar es el MEP.
4. **Umbral por distrito, sin una tabla por barrio:** la incidencia de referencia es la de la Ley 6062 para el distrito de la parcela.
   - **Oportunidad:** más de 1.000 m² construibles e incidencia total ≤ 0,8 × la de referencia.
   - **Casi:** incidencia total ≤ 1,0 × la de referencia.
   - **Gran predio:** desde 1.500 m², a cualquier precio.
5. **Señal de linderos** (solo oportunidades, casi y grandes predios): "potencial extra, revisar por completamiento y esquina". Sale si un lindero lateral es más alto que la unidad (completamiento, art. 6.5.5) o está en una unidad más alta (lindero a esquina, art. 6.4.6). No cambia los m².
6. **Productos:** solo multifamiliar. En CABA no aplican loteo ni casas agrupadas.

**Antes del 19/11/2026** el motor tomaba el mejor de dos escenarios: superficie × el FOT más alto, o una envolvente de 3 m por piso con el 65% de la planta. También cobraba plusvalía sin el 80% cuando la API daba 0. Eso daba falsos positivos (FOT inalcanzable) y falsos negativos (plusvalía de más).

## Trampas

- **Catalogado integral o estructural:** se descarta, porque no se puede demoler.
- **Catalogado cautelar:** como mucho sale como casi.
- **Se marcan con flag:**
  - APH o distrito especial, ensanche o apertura de calle, riesgo hídrico, manzana atípica y lindero a APH;
  - edificio anterior a 1941 sin resolver (Ley 3.056, consulta al CAAP);
  - parcela receptora o emisora de capacidad constructiva adicional.
- **Pin sobre la calle:** se buscan parcelas a 12 m alrededor del pin.
- **Parcela del pin que no coincide con el aviso** (superficie con más de ±15% de diferencia; Gonzalo, 20/11/2026):
  - si el aviso ya daba oportunidad o casi, se buscan las vecinas: una sola que coincida (pin corrido) o el pin más 1 o 2 que sumen la superficie (varios lotes, con la planta sumada);
  - sin pareja, **como mucho "casi"**.
- **Distrito especial sin FOT** (APH, AE, U, UBP, RUA, ARE): como mucho "casi", con el flag `distrito_especial_sin_fot`.
- **Consultas a Ciudad 3D:** tope de 3.000 por corrida, con 400 reservadas para los linderos de los hits.

## Búsquedas

Terrenos desde 200 m², casas y galpones desde 300 m², edificios sin filtro.

**Volumen medido el 16/11/2026:**

| Portal | Búsqueda | Avisos | Páginas |
|---|---|---|---|
| Zonaprop | terrenos | 3.999 | 134 |
| Zonaprop | casas | 2.152 | 72 |
| Zonaprop | galpones | 555 | 19 |
| Zonaprop | edificios | 761 | 26 |
| Mercado Libre | terrenos | 2.000 (tope del portal) | 42 |
| Mercado Libre | casas | 1.806 | 33 |
| Mercado Libre | galpones | 884 | 17 |

En total son 251 páginas de Zonaprop contra ~60 que tolera una corrida. **Gonzalo eligió la descarga incremental (Fase C):** la primera descarga se reparte en ~6 corridas y después cada corrida baja las novedades y sigue refrescando el resto.

**Pendiente:** Mercado Libre corta en 2.000 resultados, así que a terrenos le faltan avisos. Hay que partir esa búsqueda por precio, con un formato de URL todavía sin probar.

## Decidido por Gonzalo (14/11/2026)

- La plusvalía entra en la incidencia.
- La referencia es la incidencia de la Ley 6062 del distrito: oportunidad hasta 0,8 y casi hasta 1,0.
- Mínimo de 1.000 m² construibles (de piso) para que un aviso pueda ser oportunidad; gran predio desde 1.500 m².

## Para validar con Gonzalo

1. Si los m² construibles son brutos (como hoy) o vendibles.
2. Comparar 3 o 4 hits con un anteproyecto o con lo que muestra Ciudad 3D, para ajustar la eficiencia de planta.
