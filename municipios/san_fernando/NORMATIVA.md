# San Fernando — normativa y decisiones a validar

**Fuente:** UrbaSIG de la Provincia (`urbasig:_zonificacion`, partido 096), capa actualizada en **03-2026**. La base es el Código de Edificación y Zonificación (Ord. 3603), con modificaciones por las Ord. 13017/21, 13536/23 y 13667/24. Lo baja `python tools/municipio_pba.py san_fernando`.

**Tipo B** (capa vectorial con indicadores), y de las tres es la más actualizada.

**26/11/2026:** el texto completo del Código, comparado con lo que usa el motor, está en `GUIA_NORMATIVA.md`. Gonzalo aprobó las 8 propuestas y quedaron aplicadas (sección 9.1), así que lo de abajo sobre R3/R4 y casas agrupadas quedó superado.

## Cómo se arma cada zona (decidido el 14/11/2026, sin Gonzalo)

- **FOT y densidad:** los de UrbaSIG (en San Fernando casi no hay valores potenciales).
- **Multifamiliar según la densidad:**
  - **Sí, con 300 hab/ha o más:** R1, R2, C1, C2, C2A, C2B, C4Ue, DDP, DRC y RR.
  - **Sí (Gonzalo, 14/11/2026, revisado en el código):** C3 y C3A.
  - **No (Gonzalo, 14/11/2026, revisado en el código):** R3, R3A, R3B y R4. Siguen dando lotes con frente propio.
  - **No:** I2, I2A, DI, BPN y RRE.
  - **DUE 1a / 1b** (urbanización especial de vivienda social, parcelas de 80 a 130 m²): Condicional.
- **Sin producto:** I1, IE U4, los UE, equipamiento comunitario, cesiones, zonas de recuperación inundables, canal, islas y R4Ue (frentistas de Libertador: UrbaSIG no trae indicadores).
- **Lotes con frente propio:** parcela y frente mínimos de cada zona.
- **Casas agrupadas:** no se calculan, porque UrbaSIG no da m² por vivienda en San Fernando.
- **Observaciones de UrbaSIG que cambian el FOT** (por ejemplo, C3A llega a 1,8 sobre Av. Avellaneda, y C4Ue tiene FOT 2 para multifamiliar): aparecen como el flag `ver_observacion_zona`, con el texto en `notas`.

## Umbrales (decididos por Gonzalo el 14/11/2026)

Incidencia < 350 USD/m² para oportunidad y entre 350 y 450 para casi. El resto es como en San Isidro: 1.300 m², ratio de loteo 0,6 y gran predio desde 3.000 m².

## Para validar con Gonzalo

1. ~~Si R3, R3A, R3B, R4, C3 y C3A admiten multifamiliar~~ → **decidido por Gonzalo el 14/11/2026:** C3 y C3A sí; R3, R3A, R3B y R4 no.
2. Pasar 10 a 15 avisos reales a mano antes de sacar la marca "EN PRUEBA".
