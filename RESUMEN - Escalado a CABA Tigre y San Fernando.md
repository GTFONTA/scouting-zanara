# Resumen — Escalado a CABA, Tigre y San Fernando

Trabajo del 13 y 14/11/2026, a pedido de Gonzalo: "armar un scouting para CABA, otro para San Fernando y otro para Tigre; si tenés dudas elegí lo que te parezca adecuado".

## Estado

| | San Isidro | CABA | Tigre | San Fernando |
|---|---|---|---|---|
| Normativa | C.O.U. 2022 (Excel de Gonzalo) | Ciudad 3D por parcela (API oficial) | UrbaSIG 09-2022 | UrbaSIG 03-2026 |
| Motor | zonas | caba (nuevo) | zonas | zonas |
| Probado con | corridas reales | 6 parcelas reales de la API | avisos sintéticos en cada zona | avisos sintéticos en cada zona |
| Búsquedas en portales | en producción | **sin probar** | **sin probar** | **sin probar** |
| Tarea programada | lunes 10:30 (`main`) | no | no | no |
| Modo | producción | EN PRUEBA | EN PRUEBA | EN PRUEBA |

**Dónde está cada cosa**
- **Código de los tres municipios nuevos:** rama `dev`, en `C:\Users\ZN - GF\Proyectos\scouting-zanara-dev` y en GitHub.
- **Rama `main`**, la que corre el lunes: tiene solo git y los tests, sin cambios de lógica.

## Qué se hizo

1. **Git y GitHub privado** (Fase A, punto 2). El código pasó de Drive a `C:\Users\ZN - GF\Proyectos\scouting-zanara`, y la tarea programada ya corre desde ahí.
2. **Golden tests** (Fase A, punto 3). Las corridas del 09/11 y del 02/11 se reprocesan sin red y tienen que dar el mismo `resultado.csv`, el mismo resumen y el mismo mail. A eso se suman tests del scraper (403→403, repetidos de Zonaprop, búsqueda recuperada al final, ficha patrocinada de Mercado Libre) y tests de los municipios. Pasan los 23 tests.
3. **Multi-municipio.** En vez del refactor completo de la sección 4 del prompt, cada municipio es un overlay de configuración más un motor:
   - todo lo común (portales, normalización, deduplicación, catastro de ARBA, dólar, mail) se sigue escribiendo una sola vez;
   - San Isidro no cambió: los golden tests dan idéntico.
4. **Tigre y San Fernando:** zonificación vectorial de UrbaSIG (Provincia), con FOS, FOT, densidad, parcela y frente mínimos y observaciones. Son de **tipo B**, así que no hizo falta vectorizar planos. Las localidades y calles salen de OpenStreetMap. Cada uno tiene un mapa de control (`Mapa de control - Zonas.html`).
5. **CABA:** motor propio con la API de Ciudad 3D.
   - Por parcela: FOT, altura, distrito, catalogación, afectaciones y plusvalía.
   - La plusvalía entra en la incidencia.
   - Umbral relativo a la incidencia oficial de la Ley 6062 de cada distrito.

## Decisiones que tomé (a validar)

**Generales**
- **No traer a `main` el código nuevo antes de la corrida del lunes 16/11.** Primero hay que verificar los arreglos del 13/11 con esa corrida (Fase A, punto 1).
- **Cero consultas a Zonaprop y Mercado Libre para los municipios nuevos antes del 16/11**, para no arriesgar la corrida de San Isidro. Por eso las URLs de búsqueda están armadas por patrón y sin probar.
- **Salidas separadas por municipio:** carpeta `runs/<slug>/` y mail con su propio asunto, como se había decidido el 13/11.
- **Sin Sheet propia mientras estén en prueba:** el mail va solo a Gonzalo, marcado "[EN PRUEBA]". Crear las Sheets queda para cuando se activen.
- **Umbrales de Tigre y San Fernando:** 350 / 450 USD/m² (**decidido por Gonzalo el 14/11/2026**); el resto como en San Isidro (1.300 m², ratio de loteo 0,6).
- **Mismos productos que en San Isidro** (multifamiliar, lotes, agrupadas, loteo con calle), pero con los indicadores de cada código. Las reglas de cada zona están en `municipios/<slug>/normativa_zonas.csv` y la explicación en `NORMATIVA.md`.

**Tigre**
- FOT = el mayor entre el actual y el potencial; los premios del Art. 47 de la Ley 8912 van solo como flag.
- Multifamiliar:
  - **Sí:** C, TC, Tr, R5 a R8, RM y UR.
  - **Sí, con cloaca (Gonzalo, 14/11):** C1 a C4.
  - **Sí solo en terrenos de más de 1.000 m² (Gonzalo, 14/11):** R4.
  - **No:** R1u, R2, R3, RP, I, E y A.
- **Sin producto:** barrios cerrados, club de campo, parques y UE.
- **Delta:** excluido.
- **Búsquedas:** terrenos y casas desde 600 m², para no pagar páginas con lotes de barrios cerrados.

**San Fernando**
- Multifamiliar según la densidad:
  - **Sí, con 300 hab/ha o más:** R1, R2, C1, C2, etc.
  - **Condicional, entre 150 y 299:** DUE.
  - **No, con menos de 150.**
  - **Revisado por Gonzalo en el código (14/11):** C3 y C3A sí; R3, R3A, R3B y R4 no.
- Casas agrupadas: no se calculan, porque UrbaSIG no da m² por vivienda.

**CABA**
- m² construibles: el mejor de dos escenarios.
  - **FOT:** sin plusvalía.
  - **Envolvente:** altura del plano límite ÷ 3 m × 65% de la planta, pagando la plusvalía de los m² que superan el FOT entre medianeras.
- **Plusvalía:** la de la API. Cuando la API da 0 por encima del FOT, se aplica la fórmula de la Ley 6062 sin reducciones, con flag.
- **Umbral:** oportunidad si la incidencia con plusvalía ≤ 0,8 × la incidencia oficial de la Ley 6062 del distrito; casi hasta 1,0; además, más de 1.000 m² construibles. Gran predio desde 1.500 m².
- **Catalogado integral o estructural:** se descarta. **Cautelar:** como mucho sale como casi.
- **Búsquedas:** terrenos desde 200 m², casas y galpones desde 300 m², edificios sin filtro.

## Dudas abiertas (para Gonzalo)

1. ~~**CABA:** plusvalía y referencia del umbral~~ → **decidido por Gonzalo el 14/11/2026:** la plusvalía entra en la incidencia y la referencia es la Ley 6062 por distrito (0,8 / 1,0).
2. **CABA:** la envolvente estimada (3 m por piso y 65% de la planta) hay que compararla con Ciudad 3D en 3 o 4 casos reales.
3. ~~**Tigre y San Fernando:** umbrales y zonas dudosas~~ → **decidido por Gonzalo el 14/11/2026:** umbrales 350 / 450; Tigre C1 a C4 sí con cloaca y R4 sí desde 1.000 m²; San Fernando C3 y C3A sí, R3, R3A, R3B y R4 no.
4. **Volumen:** CABA y Tigre pueden superar lo que Zonaprop tolera por corrida (unas 60 páginas). Si es así, hay que subir los filtros de superficie o hacer primero la Fase C (descarga incremental con presupuesto diario).
5. **Validación manual:** 10 a 15 avisos reales por municipio, pasados a mano, antes de sacarlos del modo prueba (checklist de la sección 6 del prompt).

## Lo que no pude hacer (y por qué)

- **Probar las búsquedas en los portales:** a propósito, para no arriesgar la corrida del lunes.
- **Programar los controles del lunes y martes:** el sistema no me dejó crear tareas programadas.
- **Ver los mapas de control en el navegador integrado:** se generaron, pero no los revisé visualmente.

## Próximos pasos, en orden

1. **Lunes 16/11, después de la corrida de las 10:30:** revisar `runs/2026-11-16_*/resumen.txt` y `salud.json`. Es la Fase A, punto 1.
2. **Si salió bien, traer el código multi-municipio a `main`:**
   ```bash
   cd "C:/Users/ZN - GF/Proyectos/scouting-zanara" && git merge --ff-only dev && git push
   ```
   Después correr `python -m pytest` en esa carpeta.
3. **Medir el volumen de cada municipio,** un municipio por día y nunca antes de una corrida semanal:
   ```bash
   python tools/medir_busquedas.py caba
   ```
4. **Primera corrida de prueba de cada municipio,** a mano: `correr_semanal.ps1 -Municipio caba`. Llega un mail "[EN PRUEBA]" solo a Gonzalo.
5. **Si el volumen entra, una tarea programada por municipio en otro día que San Isidro.** Propuesta: CABA el miércoles, Tigre el jueves y San Fernando el viernes, a las 10:30, con la misma configuración que "Scouting San Isidro" y el argumento `-Municipio <slug>`.
