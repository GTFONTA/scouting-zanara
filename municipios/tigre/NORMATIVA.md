# Tigre — normativa y decisiones a validar

**Fuente:** UrbaSIG de la Provincia (`urbasig:_zonificacion`, partido 057), capa con fecha 09-2022. La base es el Código de Zonificación (Ord. 1894/96 y 1996/97), con modificaciones por las Ord. 1297/92, 3564/17 y 3776/21. Lo baja `python tools/municipio_pba.py tigre`, que genera `zonas.geojson`, `normativa_zonas.csv`, `localidades.geojson` y `calles.geojson`.

**Tipo B** (capa vectorial con indicadores): no hizo falta vectorizar un plano.

## Cómo se arma cada zona (decidido el 14/11/2026, sin Gonzalo)

- **FOT:** el mayor entre el actual y el potencial de UrbaSIG. Los premios del Art. 47 de la Ley 8912 (por ejemplo, C1 llega a FOT 3,6) **no** se usan en el cálculo: aparecen como el flag `premio_ley_8912`, con el valor en `notas`.
- **Densidad:** la mayor entre la actual y la potencial (hab/ha), con 4 personas por unidad, igual que en San Isidro.
- **Multifamiliar:**
  - **Sí:** zonas centrales (C1 a C7, TC, Tr), R5 a R8, RM1, RM2 y las UR de Nordelta.
  - **Condicional:** R4. La observación de la zona dice "en terrenos mayores a 1.000 m² se admite multifamiliar"; un hit ahí sale como casi.
  - **No:** R1u, R2, R3, RP, I, E y A (son zonas de "una vivienda cada X m² de lote").
- **Sin producto:** barrios cerrados (R1a, R1b, R3b), club de campo (CC), parques (PR, PU, PT, PA), usos específicos (UE) y precinto industrial (P). También cualquier zona con FOT 0 en UrbaSIG.
- **Lotes con frente propio:** parcela mínima (sm) y frente mínimo (lm) de cada zona.
- **Casas agrupadas:** solo donde UrbaSIG da "una vivienda cada X m² de lote" (um2), con 5 m de frente propio por casa (el mismo mínimo que en San Isidro).
- **Delta:** excluido. Solo cuenta el área continental zonificada; las islas no tienen zonas en la capa.

## Umbrales

Por ahora son los mismos de San Isidro: incidencia < 400 USD/m² para oportunidad y entre 400 y 500 para casi, más de 1.300 m² construibles, ratio de loteo 0,6 y gran predio desde 3.000 m².

**Decisión de Gonzalo:** Tigre tiene valores de venta más bajos que San Isidro, así que probablemente le corresponda un umbral de incidencia menor.

## Búsquedas

- Terrenos y casas desde 600 m², porque Tigre tiene miles de lotes en barrios cerrados que no sirven como producto. Galpones desde 400 m², edificios sin filtro.
- **Pendiente:** medir cuántas páginas da cada búsqueda. Se hace con una consulta por búsqueda, después de la corrida de San Isidro del 16/11.

## Para validar con Gonzalo

1. La clasificación de multifamiliar de cada zona, sobre todo C1 a C4: UrbaSIG les asigna densidad 150 hab/ha, y con agua y cloaca llegarían a 2.000 hab/ha.
2. Si conviene usar los premios del Art. 47 en vez de dejarlos solo como flag.
3. Los umbrales propios de Tigre.
4. Pasar 10 a 15 avisos reales a mano antes de sacar la marca "EN PRUEBA".
