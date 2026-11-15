# Plan — Fase 5: valor de venta por zona y margen

Pedido de Gonzalo (14/11/2026): las mejores oportunidades no son las de menor incidencia, sino las que dejan más diferencia entre el costo por m² y el precio de venta. Hay que mapear el valor de venta de cada zona y cruzarlo con los avisos.

**Estado:** plan para revisar. No se toca código hasta que Gonzalo lo apruebe, y no se empieza antes de revisar la corrida del lunes 16/11 y de pasar `dev` a `main`.

## 1. Qué cambia para Gonzalo

Cada hit del mail suma tres datos:
- **Valor de venta de la zona** (USD/m²), con cuántos comparables se calculó y de dónde salen.
- **Margen por m²** y **margen total estimado** del proyecto.
- **Margen sobre costo** (%), que es el número para ordenar los hits.

Además, un **mapa de valores de venta** por municipio, que se va completando semana a semana.

Mientras dure la fase, **la regla vigente no cambia**: los umbrales de incidencia siguen decidiendo qué es oportunidad. El margen entra primero como dato y como orden. Recién con el backtest a la vista (paso 6) Gonzalo decide si pasa a ser la regla.

## 2. Fórmulas

Costos dados por Gonzalo el 14/11/2026. Van a `config.yaml`, nunca en el código.

**Multifamiliar**
- Costo de obra: 1.300 USD/m² directo + 500 USD/m² de honorarios, comisiones e impuestos = **1.800 USD por m² vendible** (Gonzalo, 14/11/2026). El valor de venta también es por m² vendible, así que el margen por m² se calcula directo.
- Margen por m² = valor de venta de la zona − 1.800 − incidencia.
- Margen total = margen por m² × m² vendibles. Se toman como vendibles los m² construibles por FOT (superficie × FOT), que es lo que el código computa.
- Margen sobre costo = margen por m² ÷ (1.800 + incidencia).

**Loteo de barrio cerrado**
- Costo de desarrollo: 25 USD + 5 USD = **30 USD por m² de tierra bruta**.
- Ingreso por m² bruto = valor del lote de la zona (USD/m²) × parte vendible (hoy 75%: se pierde 25% en calles).
- Margen por m² bruto = ingreso − 30 − precio de la tierra por m².
- Margen sobre costo = margen ÷ (30 + precio de la tierra por m²).

**Casas (housing):** falta el costo de obra. Ver dudas.

## 3. De dónde sale el valor de venta

Un **registro propio de comparables**, armado con los mismos portales:

| Producto | Qué se baja como comparable | Dato |
|---|---|---|
| Multifamiliar | Departamentos a estrenar o en pozo (lo que ZANARA vendería) | USD/m² |
| Housing | Casas nuevas o de pocos años, en lotes chicos | USD/m² |
| Barrio cerrado | Lotes dentro de barrios cerrados, con el nombre del barrio | USD/m² de lote |
| Loteo abierto | Lotes de 150–600 m² (ya existe desde la Fase 4) | USD/m² de lote |

**El registro**
- Un archivo por municipio en disco local (`data/registro_comparables_<slug>.csv`), fuera de Drive.
- Una fila por aviso: fecha de primera y última vez visto, portal, tipo, ubicación, m², precio, USD/m², antigüedad.
- Es acumulativo: cada semana suma avisos nuevos y actualiza los que siguen publicados. Así el mapa se hace más denso sin bajar todo de una vez.

**Valor de la zona para un aviso**
- Mediana de los comparables a 500 m, de los últimos 12 meses.
- Con menos de 5 comparables: la mediana de la localidad. Con menos de 5 ahí también: la del partido. Es la misma escalera que ya usan los lotes chicos.
- Cada hit dice qué escalón usó, para saber cuánto confiar.

**Control externo:** una vez por municipio, comparar las medianas por localidad con un informe público (Zonaprop Index, Reporte Inmobiliario, estadísticas de la Ciudad). Si difieren mucho, se revisa el filtro de comparables.

## 4. Tráfico a los portales

Es la restricción principal: los departamentos son miles de avisos y Zonaprop tolera unas 60 páginas por corrida.

- **Mercado Libre primero**, sin abrir fichas cuando la página de resultados ya trae m² y precio.
- **Solo a estrenar o en pozo**, que reduce mucho el volumen.
- **Por tramos:** cada semana se baja una parte (por ejemplo, un rango de precio o una localidad), con un tope de páginas por corrida en `config.yaml`. El registro se completa en 4 a 6 semanas.
- **Nunca antes de la corrida semanal del municipio**, siempre después, y sin paralelismo.
- **Zonaprop para comparables:** solo si Mercado Libre no alcanza, y recién después de resolver el volumen de los municipios nuevos.
- Si un portal bloquea la búsqueda de comparables, es un aviso menor: los hits salen con el valor del registro que ya había.

## 5. Pasos

1. **Piloto en San Isidro (multifamiliar).** Bajar departamentos a estrenar de Mercado Libre, armar el registro y calcular el valor por localidad. Entregable: tabla de USD/m² por localidad con cantidad de comparables, comparada con un informe público.
2. **Margen como dato.** Sumar valor de venta, margen por m², margen total y margen sobre costo a `resultado.csv`, a la Sheet y al mail. La regla no cambia.
3. **Backtest.** Recalcular los hits de las corridas ya guardadas y mostrar el orden actual (por incidencia) al lado del nuevo (por margen). Entregable: una tabla con los casos que suben y los que bajan.
4. **Mapa.** Un mapa de calor por municipio (`Mapa - Valor de venta.html`) con los comparables y las oportunidades encima.
5. **Loteo y barrio cerrado.** Lo mismo con lotes en barrios cerrados, sobre todo en Tigre.
6. **Decisión de Gonzalo.** Con el backtest: si el margen reemplaza a los umbrales de incidencia, si se combinan (por ejemplo, incidencia máxima y margen mínimo) o si queda solo como orden.
7. **Extender** a casas y a CABA, Tigre y San Fernando.

Cada paso se valida con Gonzalo antes de pasar al siguiente. Los golden tests de San Isidro tienen que seguir dando igual hasta el paso 6.

## 6. Limitaciones que hay que tener presentes

- **Son precios de publicación, no de cierre.** Para comparar zonas sirven igual. Para el margen absoluto se puede aplicar un descuento de negociación, configurable.
- **Zonas con pocos avisos a estrenar** van a caer en la mediana de la localidad, que es gruesa.
- **m² vendibles:** se asume que son los m² por FOT. Si en la práctica se vende más o menos que eso, se agrega un factor en `config.yaml`.

## 7. Dudas para Gonzalo

1. ~~**Multifamiliar:** los 1.800 USD/m², ¿por m² vendible o construido?~~ → **por m² vendible** (Gonzalo, 14/11/2026).
2. **Casas (housing):** falta el costo de obra por m² y los honorarios.
3. **Descuento de negociación** sobre el precio publicado: ¿aplicamos alguno (por ejemplo, 5–10%) o comparamos contra publicación?
4. **Margen mínimo** que te interesa (sobre costo, en %), para cuando el margen pase a ser regla.
5. **Loteo abierto** (lotes con frente a calle pública, sin infraestructura interna): ¿tiene un costo de desarrollo propio o es despreciable?
6. **Costo financiero y plazo:** ¿los dejamos fuera? Lo propongo así para empezar, porque es un filtro de primera mirada.
