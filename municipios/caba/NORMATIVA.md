# CABA — metodología y decisiones a validar

**Tipo A** (edificabilidad por parcela). El motor propio está en `src/motor_caba.py` y no usa capa de zonas. Consulta la API pública que usa Ciudad 3D (`epok.buenosaires.gob.ar`), probada el 14/11/2026 con 6 parcelas reales:

| Dato | Endpoint |
|---|---|
| Parcela en el pin → SMP, superficie, frente | `/catastro/parcela/?lng=&lat=` |
| FOT (medianera, semi libre, perímetro libre), altura del plano límite, distrito, incidencia de la Ley 6062 (UVA/m²), catalogación, afectaciones, APH | `/cur3d/seccion_edificabilidad/?smp=` |
| Plusvalía (derecho de desarrollo urbano) para un área dada, en UVA | `/cur3d/calcular_plusvalia/?smp=&area_edificar=` |
| Geocodificación de avisos sin pin | USIG `normalizar_y_geocodificar_direcciones` |
| Valor de la UVA | API del BCRA (variable 31) |

Todo queda en caché en `data/cache_caba.json`: una consulta por parcela, nunca más.

## Cálculo (decidido el 14/11/2026, sin Gonzalo)

1. **m² construibles:** de dos escenarios, se queda con el de menor incidencia. Así no se pierden oportunidades.
   - **FOT:** superficie × el FOT más alto de la parcela. La plusvalía es 0, porque la API solo la cobra por encima del FOT.
   - **Envolvente:** se usa la superficie edificable de Ciudad 3D cuando la da (hoy viene en 0). Si no, se estima como pisos × planta, donde pisos = altura del plano límite ÷ 3 m y planta = superficie en planta × 0,65 (descuenta patios y pulmón). Este escenario paga la plusvalía de los m² que superan el FOT entre medianeras.
2. **Plusvalía:** la que devuelve la API. En algunos casos la API da 0 aunque se supere el FOT; ahí se aplica la fórmula de la Ley 6062 sin reducciones: (m² − superficie × FOT) × incidencia UVA × alícuota. El aviso lleva el flag `plusvalia_estimada`.
3. **Incidencia total:** (precio + plusvalía en USD) ÷ m² construibles. La UVA sale del BCRA y el dólar es el MEP.
4. **Umbral por distrito, sin una tabla por barrio:** la incidencia de referencia es la de la Ley 6062 para el distrito de la parcela, que es la valuación oficial del m² de suelo. Va de unos 300 USD/m² en el sur a más de 800 en Palermo.
   - **Oportunidad:** más de 1.000 m² construibles e incidencia total ≤ 0,8 × la de referencia.
   - **Casi:** incidencia total ≤ 1,0 × la de referencia.
   - **Gran predio:** desde 1.500 m², a cualquier precio.
5. **Productos:** solo multifamiliar. En CABA no aplican loteo ni casas agrupadas.

## Trampas

- **Catalogado integral o estructural:** se descarta, porque no se puede demoler.
- **Catalogado cautelar:** como mucho sale como casi.
- **Se marcan con flag:** APH o distrito especial, ensanche o apertura de calle, riesgo hídrico, manzana atípica y lindero a APH.
- **FOT de perímetro libre o semi libre:** el flag aclara que exige ese tipo de edificio y muestra el FOT entre medianeras.
- **Pin sobre la calle:** se buscan parcelas a 12 m alrededor del pin.
- **Parcela del pin que no coincide con el aviso** (superficie con más de ±15% de diferencia): se usa igual el FOT de esa parcela y el aviso lleva una alerta.

## Búsquedas

Terrenos desde 200 m², casas y galpones desde 300 m², edificios sin filtro. **Pendiente:** medir el volumen después del 16/11. CABA tiene muchas más páginas que San Isidro y, sin la descarga incremental (Fase C), puede no entrar en el presupuesto semanal de Zonaprop.

## Decidido por Gonzalo (14/11/2026)

- La plusvalía entra en la incidencia.
- La referencia es la incidencia de la Ley 6062 del distrito: oportunidad hasta 0,8 y casi hasta 1,0.
- Mínimo de 1.000 m² construibles (de piso) para que un aviso pueda ser oportunidad; gran predio desde 1.500 m².

## Para validar con Gonzalo

1. La envolvente estimada (3 m por piso, 65% de la planta): comparar 3 o 4 casos con lo que muestra Ciudad 3D.
