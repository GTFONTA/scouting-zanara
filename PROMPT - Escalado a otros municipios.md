# PROMPT — Escalado del scouting de tierra a otros municipios (ZANARA)

Escrito el 13/11/2026 desde claude.ai, para continuar en Claude Code. Actualizado el mismo día después de aplicar los arreglos de salud y bloqueos (ver sección 2).
Antes de tocar nada, leé en este orden: `CLAUDE.md`, `RESUMEN_NIVEL.md` y este archivo.
Primer mensaje sugerido en Claude Code: "Leé CLAUDE.md, RESUMEN_NIVEL.md y PROMPT - Escalado a otros municipios.md. Empezá por la Fase A, punto 1, con la corrida más reciente."
Regla de siempre: **trabajar por fases y no avanzar de fase sin el OK de Gonzalo**. Donde este archivo diga "decisión de Gonzalo", preguntá antes de construir.

---

## 1. Objetivo

Que el sistema que hoy corre para San Isidro cubra varios municipios (CABA y partidos del GBA norte: Tigre, San Fernando, Pilar, Vicente López u otros que Gonzalo indique), con estas condiciones:

- Gonzalo sigue sin intervenir en régimen: lee un mail por semana y por municipio.
- Los portales no nos bloquean, o si bloquean, el sistema se recupera solo sin perder la semana.
- Cada municipio tiene su propia normativa, metodología y salidas (carpeta, mail y Sheet), pero lo común (portales, bloqueos, catastro, mail) es uno solo.
- Costo cero o casi cero, como hasta ahora (sin Apify, sin servicios pagos de scraping).

## 2. Punto de partida real (13/11/2026)

Lo que hay que saber antes de escalar, sacado de `runs/`:

| Corrida | Zonaprop | Mercado Libre | Hits |
|---|---|---|---|
| 19/10 | **FALLA**: la búsqueda de *terrenos* dio 403 (bloqueo). 1.144 avisos | ok | 40 |
| 26/10 | ok, 1.515 avisos | **FALLA** falsa (ver abajo) | 38 |
| 02/11 | **FALLA** falsa: "edificios: 51 de 54" | ok | 37 |
| 09/11 | **FALLA** falsa: "edificios: 50 de 54". Corrió a las 18:51, no a las 10:30 | **FALLA** falsa | 38 |

Diagnóstico: 3 de esas 4 fallas eran falsas alarmas y una era un bloqueo real.

### Ya resuelto el 13/11/2026 (desde claude.ai, detallado al final de `CLAUDE.md`)

Respaldo de los originales en `runs/_respaldo_pre_arreglos_2026-11-13/`.
- **Mercado Libre, avisos patrocinados**: la tarjeta trae una URL de clics de publicidad (`click1.../brand_ads/...`) y el código le agregaba otro `https://`. Ahora `_ml_url` usa la URL canónica `https://articulo.mercadolibre.com.ar/MLA-<n>` y nunca abre la de publicidad.
- **Zonaprop "50 de 54"**: el portal repetía 4 destacados entre páginas; llegaron las 54 filas. La cobertura ahora se compara con las filas recibidas y los repetidos quedan como aviso menor.
- **Salud en dos niveles**: `errores` (falla, línea roja del mail) y `avisos_menores` (solo en `resumen.txt` y `salud.json`): fichas sueltas de ML que no abren (hasta `errores_fichas_max`), repetidos del portal, búsqueda bloqueada que se recuperó.
- **Bloqueos**: un solo reintento ante 403/429 (`reintentos_bloqueo`); si sigue, la búsqueda pasa al final de la corrida y se reintenta una vez tras `espera_recupero_s` (25 min). El 19/10 el 403 fue en la **primera página del lunes** (no por volumen) y se destrabó ~40 min después.
- **PC suspendida**: `main.py` llama a `SetThreadExecutionState` mientras dura la corrida.
- **Ruta de Python**: `correr_semanal.ps1` usa `py -3` si la ruta fija ya no existe.

### Sin verificar todavía

- Que `articulo.mercadolibre.com.ar/MLA-<n>` redirija bien a avisos de inmuebles. Si no, esas fichas aparecen como aviso menor en `resumen.txt`.
- `SetThreadExecutionState` no se pudo probar fuera de Windows.
- La primera corrida con los arreglos es la del **lunes 16/11/2026**: revisar su `resumen.txt` y `salud.json` antes de cualquier otra cosa.

### Lo que sigue pendiente

1. **El bloqueo real de Zonaprop pasa con un solo partido.** El reintento al final de la corrida es un parche: multiplicar por 5 municipios con la estrategia actual (todo en una corrida el lunes) es garantía de bloqueo. El remedio es la sección 5.
2. **No hay git ni tests.** Un refactor multi-municipio sin eso es jugar sin red.

## 3. Lo que se mantiene (no cambiar sin que Gonzalo lo pida)

Todo lo de "Reglas de negocio" y "Convenciones" de `CLAUDE.md` vale para San Isidro tal cual. Además:

- Priorizar no perder oportunidades sobre evitar falsos positivos (cada hit se verifica a mano).
- Se valora por lo construible según código, no por lo edificado.
- Exclusión de PH, departamentos, oficinas, locales, cocheras y unidades funcionales.
- Sin Apify ni servicios pagos de scraping. Ejecución desde PCs con IP residencial (las de datacenter las bloquea Cloudflare).
- Salud del scraper: un portal con 0 avisos, una página que no se puede interpretar o un bloqueo se reportan como falla, nunca como "semana sin novedades".
- Nombres de archivos para Gonzalo (mails, planillas, documentos): sin guiones bajos, con espacios y " - " para separar nombre de descripción. Excepción: archivos que procesa el código, donde manda lo que no rompa el proceso.

## 4. Arquitectura objetivo: núcleo común + un "plugin" por municipio

Decidido con Gonzalo el 13/11/2026:
- **Cada municipio tiene su propia metodología** (su "motor": CABA calcula por parcela con Ciudad 3D; San Isidro por zona vectorizada + C.O.U.; cada partido de PBA con su código), **sus propios datos y sus propias salidas** (carpeta, mail y Sheet separados).
- **Lo que no depende del municipio se escribe una sola vez**: descarga de portales y control de bloqueos (tiene que ser uno solo porque es el que reparte el tráfico total por portal e IP), normalización, deduplicación, catastro de ARBA, cotización del dólar, envío de mail y escritura de Sheet.
- Motivo: un arreglo del núcleo (como los del 13/11) se hace una vez y vale para todos; y cinco sistemas independientes le pegarían a los portales al mismo tiempo desde la misma IP.

Carpetas en Google Drive, una por municipio, con todo lo que es de ese municipio (lo que Gonzalo mira y comparte):

```
Drive / Scouting ZANARA /
  San Isidro /
    Normativa /        Excel del C.O.U., plano PDF, fuentes
    Zonificación /     zonas.geojson, calles, barrios, mapa de control
    Resultados /       una carpeta por semana: resultado.csv, resumen.txt, salud.json, copia del mail
  CABA /
    Normativa /  Zonificación /  Resultados /
  Tigre / ...
  Sistema /            estado de la cola y bloqueos exportados por cada máquina (ver 5.6), logs
```

Los nombres de carpetas y archivos que mira Gonzalo van con espacios y sin guiones bajos; los que procesa solo el código pueden quedar como estén.

Código (repo con git, ver Fase A), que lee y escribe en esas carpetas de Drive:

```
scouting-zanara/                      # repo nuevo (ver Fase A, punto 2)
  CLAUDE.md
  config.yaml                         # global: portales, presupuestos, máquinas, mail, Sheet
  municipios/
    san_isidro/
      municipio.yaml                  # motor que usa, rutas a sus carpetas de Drive, límites, URLs de búsqueda por portal,
                                      # umbrales propios, alias de zonas/barrios
      motor.py                        # implementa MotorNormativo (hoy: lógica de evaluate.py + flags.py de San Isidro);
                                      # lee zonas, normativa, calles y barrios desde Drive/.../San Isidro/
    caba/
      municipio.yaml
      motor.py                        # edificabilidad por parcela desde Ciudad 3D (ver 6.1): otra metodología, mismo contrato
    tigre/ ...
  src/
    fetch/                            # un módulo por portal + scheduler (ver 5)
    normalize.py, dedupe.py, catastro_arba.py, comparables.py, store.py, notify.py, main.py
    motor_base.py                     # interfaz común
  estado/                             # cola y estado local de cada máquina (fuera de Drive, ver 5.6)
  tests/                              # golden tests con crudos reales (copias chicas, versionadas)
```
Los crudos bajados de los portales son comunes (una búsqueda puede traer varios municipios) y van a `Drive/.../Sistema/`; los resultados ya evaluados van a la carpeta de cada municipio.

Interfaz mínima del motor normativo (cada municipio la implementa con su propia metodología; el núcleo solo conoce este contrato):

```python
class MotorNormativo:
    slug: str
    def contiene(self, lat, lon) -> bool                 # ¿el pin está en este municipio? (con margen)
    def ubicar(self, aviso) -> Ubicacion                 # pin/calle/barrio -> zona(s) o parcela, con flag_confianza
    def evaluar(self, aviso, ubicacion, comparables) -> Evaluacion
        # devuelve: m2_construibles, unidades por producto/vía, incidencia, clasificación
        # (oportunidad / casi / gran predio / descartado + motivo), flags con artículo, checklist manual,
        # y TODOS los valores intermedios para la Sheet
```

Reglas del refactor:
- El ruteo aviso → municipio se hace por el pin (y por la localidad del aviso si no hay pin), no por qué búsqueda lo trajo: una búsqueda de "GBA Norte" puede traer avisos de varios partidos.
- Umbrales por municipio en `municipio.yaml` (incidencia, m² construibles mínimos, ratio de loteo, superficie mínima de prefiltro). Los de San Isidro son los vigentes; los de los demás son **decisión de Gonzalo** (ver 8).
- **Salidas separadas por municipio** (decidido): un mail por municipio (asunto "Scouting <Municipio> — …"), una Google Sheet por municipio y los resultados de cada semana en `Drive/.../<Municipio>/Resultados/`. La salud de los portales es común: cada mail trae la línea de salud que afecta a ese municipio.
- `municipio.yaml` dice qué motor usa cada municipio y dónde están sus carpetas de Drive. Agregar un municipio = crear su carpeta en Drive, su `municipio.yaml` y su motor (o reutilizar uno existente si de verdad aplica la misma metodología), sin tocar el núcleo.

## 5. Estrategia anti-bloqueo

### 5.1 Diagnóstico (por qué "varias cuentas" no sirve)

- Las páginas de resultados de Zonaprop y Mercado Libre **no piden login**. El bloqueo es por IP y por patrón de tráfico/huella del cliente, no por cuenta. Tener 3 cuentas no cambia nada de lo que ve el portal.
- Crear cuentas para repartir tráfico va contra los términos de uso de los portales y pone en riesgo la cuenta real de Mercado Libre de Gonzalo/ZANARA. **No se hace.**
- Lo que sí mueve la aguja: **menos páginas por semana** (incremental), **tráfico repartido en el tiempo** (presupuesto diario) y **más de una IP residencial real** (dos conexiones distintas).

### 5.2 Descarga incremental (el cambio de más impacto)

Hoy cada lunes se recorren todas las páginas de todas las búsquedas (~55 de Zonaprop + ~90–120 de ML por un solo partido), aunque el 90% de los avisos sean los mismos de la semana anterior.

- **Pasada incremental (diaria o casi):** cada búsqueda ordenada por "más recientes"; se avanza página por página y se corta cuando una página entera ya es conocida (más una página de margen). Volumen esperado: 1–3 páginas por búsqueda y por día.
- **Barrido completo (rotativo):** cada búsqueda se recorre entera una vez cada 2–4 semanas (configurable), repartido en varios días. Sirve para detectar bajas de precio, avisos dados de baja y lo que la pasada incremental se pierda.
- Validar en la Fase C que Zonaprop y ML ordenan de verdad por fecha de publicación (y no reordenan por destacados); si un portal no lo permite, ese portal se queda con barrido completo espaciado.
- Las bajas de precio se detectan en el barrido; aceptar que se vean con hasta 2–4 semanas de demora (decisión de Gonzalo si no le sirve).

### 5.3 Presupuesto por portal, por IP y por día

- Cola persistente de tareas (SQLite local de cada máquina): `portal, municipio, url, tipo (incremental|barrido|ficha), prioridad, estado, intentos, proximo_intento`.
- Un worker que lanza el Programador de tareas **cada hora de lunes a viernes de 10 a 18** (la ventana en que la PC está prendida). Cada ejecución toma tareas hasta agotar el presupuesto de esa hora y sale. Si la PC se apagó, la cola sigue al día siguiente donde quedó: **lento pero ininterrumpido**.
- Presupuesto inicial conservador (calibrar con datos): Zonaprop ≤ 15 páginas por sesión y ≤ 40 por día por IP; ML ≤ 60 páginas/fichas por día por IP; pausas con azar como hoy. Estos números son una suposición de partida: ajustarlos con el historial de bloqueos.
- Ajuste automático: tras un bloqueo, bajar el presupuesto de ese portal en esa IP un 30%; tras una semana limpia, subirlo un 5% hasta el tope configurado.
- Prioridad: primero las pasadas incrementales de todos los municipios (lo nuevo es lo que importa), después fichas de ML nuevas, al final el barrido rotativo.

### 5.4 Ante un bloqueo: cortar, no insistir

- Un 403/429 o un desafío anti-bot = **circuit breaker**: ese portal queda en pausa para esa IP hasta el día siguiente (o N horas configurables). Nada de esperar 10 minutos y reintentar 3 veces: eso es justamente lo que hace que el portal endurezca el bloqueo.
- Hoy (desde el 13/11) existe una versión mínima dentro de la corrida semanal: `BlockedError` en `fetch.py`, un reintento y la búsqueda pasa al final de la corrida. En la Fase C se reemplaza por la pausa del portal en la cola.
- Se registra cada bloqueo (fecha, hora, portal, IP, página, cuántas páginas se habían pedido ese día) en `estado/bloqueos.csv`. Con 4–6 semanas de eso se sabe cuál es el límite real.
- **No se sortean desafíos anti-bot**: nada de proxies residenciales rotativos, resolvedores de captcha ni navegadores "stealth" para pasar el desafío. Si un portal endurece y Gonzalo quiere escalar, es una decisión explícita suya con sus riesgos (legales y de baneo), no algo que el código haga solo.

### 5.5 Salud: tres categorías, no una

Desde el 13/11 ya hay dos niveles (`errores` y `avisos_menores`, ver sección 2). Al escalar hay que separar más:
- **Bloqueo** (403/desafío): rojo.
- **Error de código/parseo** (página que no se entiende, URL mal armada): rojo, con el aviso de que hay que arreglar código.
- **Aviso menor** (repetidos del portal, ficha suelta, búsqueda recuperada): solo en `resumen.txt`, como hoy.
Y una línea por municipio: "cobertura de la semana: X avisos vistos / Y esperados según el portal".

### 5.6 Dos computadoras

- **Solo suman si salen a internet por IPs públicas distintas.** Dos PCs en la misma oficina comparten la IP del router: para el portal son la misma, y duplicar tráfico desde ahí acelera el bloqueo. Verificar con `https://api.ipify.org` desde cada máquina antes de configurar nada. Opciones reales: una en la oficina y otra en la casa, o una segunda conexión (otro proveedor o módem 4G).
- Reparto estático en `config.yaml`, no dinámico (más simple y sin peleas por la cola):
  ```yaml
  maquinas:
    oficina:   {ip_esperada: x.x.x.x, portales: {zonaprop: [san_isidro, caba], mercadolibre: [tigre, pilar]}}
    casa:      {ip_esperada: y.y.y.y, portales: {zonaprop: [tigre, pilar], mercadolibre: [san_isidro, caba]}}
  principal: oficina          # la que consolida, evalúa, escribe las Sheets y manda los mails
  ```
  El worker se identifica por nombre de máquina; si la IP actual no es la esperada (p. ej. la notebook de la casa llevada a la oficina), no descarga y lo reporta.
- Cada máquina guarda su SQLite **en disco local** (nunca una SQLite compartida por Google Drive: Drive la corrompe) y exporta lo bajado como JSON a `Drive/.../Sistema/<maquina>/`. La principal lee las dos carpetas, deduplica, evalúa y manda el mail semanal (lunes, como hoy). Si la otra máquina no exportó nada en la semana, eso va en la línea roja.
- Si más adelante esto queda chico, migrar el estado compartido a una base (Supabase/Postgres gratis) — no antes.

### 5.7 Fuentes legítimas a probar (1–2 consultas cada una, no más)

- **API oficial de Mercado Libre con app registrada** (developers.mercadolibre.com.ar, OAuth): hoy se lee HTML porque la API pública pide login; con una app propia el login es el token de la app y los límites son explícitos. Probar si la búsqueda de inmuebles por categoría y ubicación responde con token. Si sí, reemplaza el scraping de ML y elimina su riesgo de bloqueo. No es seguro que funcione para búsquedas de terceros: probarlo.
- **Argenprop**: sigue deshabilitado (AWS WAF). No reintentar.
- Acceso comercial a datos (Navent/Zonaprop u otros): solo listar la opción para Gonzalo, no contactar a nadie.

## 6. Alta de un municipio: tres tipos de fuente de zonificación

Antes de construir un municipio, clasificarlo:

| Tipo | Qué hay | Ejemplo | Esfuerzo |
|---|---|---|---|
| **A — Edificabilidad por parcela digital** | Un servicio que, dada la parcela, devuelve m² edificables/altura | CABA (Ciudad 3D) | Bajo en zonificación; el trabajo está en el motor y en las reglas de negocio |
| **B — Capa vectorial de zonas** | GIS municipal con capa de zonas exportable (GeoJSON/WFS/ArcGIS REST) | San Isidro *tenía* una (no responde) | Medio: casar zonas con normativa |
| **C — Solo plano PDF + ordenanza** | Plano escaneado o PDF | San Isidro en la práctica; probablemente Tigre, San Fernando, Pilar | Alto: Fase 0 de vectorización como en San Isidro |

**El cuello de botella no es el scraper, es la normativa**: en San Isidro lo más valioso fue el Excel del C.O.U. que armó Gonzalo (productos, densidades, parcela mínima, incentivos y trampas, Calculadora). Cada municipio de tipo B/C necesita su equivalente, y eso lo valida Gonzalo. Planificar un municipio por vez.

Checklist de alta (Fase 0 por municipio, igual que la de San Isidro):
1. Buscar la fuente de zonificación vigente y clasificar el tipo (A/B/C). Documentar ordenanza, fecha y modificaciones.
2. Obtener/vectorizar las zonas a EPSG:4326 y hacer el mapa de control.
3. Armar con Gonzalo la tabla `normativa.csv` (o su Excel fuente) y las reglas de producto que aplican en ese municipio.
4. Límite del partido, barrios/localidades con alias, calles de OSM.
5. URLs de búsqueda por portal (o confirmar que las búsquedas regionales lo cubren) y volumen estimado de avisos/páginas.
6. Validación manual: 10–15 avisos reales pasados a mano por Gonzalo antes de activar el municipio.
7. Activación en modo "solo reporte" una o dos semanas (su mail sale marcado como en prueba).

### 6.1 CABA (tipo A)

- **Ciudad 3D** (`ciudad3d.buenosaires.gob.ar`) muestra por parcela la superficie edificable, la altura máxima y el plano límite del Código Urbanístico, la unidad de edificabilidad, la plusvalía y el FOT. El GCBA aprobó en 2025 publicar componentes de Ciudad 3D como código abierto (Res. 152/2025 SITD).
- Tarea: identificar el servicio que consume Ciudad 3D (por SMP — sección/manzana/parcela — o por coordenadas), probarlo con 3 parcelas conocidas, y cachear por SMP (una consulta por parcela, nunca más). Para pasar de dirección/pin a SMP, usar los servicios de USIG / datos abiertos de la Ciudad. Tráfico bajo y espaciado también acá.
- Diferencias de negocio que **decide Gonzalo** antes de construir:
  - En CABA el Código Urbanístico regula por alturas/unidades de edificabilidad, no por FOT de zona: los m² construibles salen de la parcela, no de "superficie × FOT".
  - **Plusvalía** (derecho de desarrollo urbano): ¿la incidencia se calcula como (precio + plusvalía estimada) ÷ m² edificables? Sin esto, la incidencia en CABA sale artificialmente baja.
  - Productos: básicamente multifamiliar; loteo y agrupadas no aplican.
  - Umbral de incidencia propio (los 400 USD/m² de San Isidro probablemente no den ningún hit en CABA, o den todos en el sur). Probablemente convenga umbral por barrio o por comuna.
  - Volumen: CABA tiene muchos más avisos que San Isidro. Sin la descarga incremental (5.2) no entra en el presupuesto. Filtrar por superficie mínima en la URL (p. ej. terrenos y casas de más de 250–300 m²: a definir con Gonzalo).

### 6.2 Partidos de la Provincia de Buenos Aires (tipo B o C)

- El catastro de ARBA (WFS `idera:Parcela` y `idera:Lado_Catastral`) sirve para todos los partidos: `catastro.py` se reutiliza tal cual (frente real, superficie, partida).
- Códigos: los partidos del GBA norte tienen códigos de zonificación bajo la Ley 8912, con años y modificaciones distintas (por ejemplo, Tigre con el Código de Zonificación de 1996 y sus modificaciones; San Fernando con el texto ordenado convalidado en 1996 y modificaciones posteriores). Verificar en cada caso cuál es la versión vigente antes de vectorizar.
- **Pilar**: dominan los grandes predios, barrios cerrados y urbanizaciones especiales; la vía "multifamiliar por incidencia" pesa poco y la de loteo/barrio pesa mucho. Las reglas de producto se arman con Gonzalo desde cero, no copiando las de San Isidro.
- **Tigre**: excluir el Delta (régimen propio) salvo que Gonzalo diga lo contrario.

## 7. Fases (cada una termina con el OK de Gonzalo)

**Fase A — Red de seguridad antes de tocar más código (sin agregar municipios)**

Los arreglos de salud y bloqueos ya están aplicados (sección 2). Esta fase es solo git, tests y verificar esos arreglos en producción. No se cambia lógica.
1. **Verificar los arreglos** con las corridas del 16/11 y el 23/11 (`resumen.txt`, `salud.json`, log):
   - sin falsas fallas en la línea roja;
   - las fichas de avisos patrocinados de ML abren por `articulo.mercadolibre.com.ar` (si no, buscar otra URL canónica en la tarjeta, sin abrir nunca la de publicidad);
   - si hubo un 403, el log muestra el reintento al final de la corrida y su resultado;
   - la corrida no se cortó por suspensión de la PC.
2. **Git**: recomendado, repo en disco local fuera de Google Drive (p. ej. `C:\Users\ZN - GF\Proyectos\scouting-zanara`), porque Drive sincroniza a medias los archivos internos de `.git` y puede romper el repo; los datos y salidas sí van a Drive (sección 4). Si Gonzalo prefiere dejar el código en Drive: aceptable solo si se edita desde una única PC y hay copia en un remoto privado de GitHub. `.gitignore` para secretos, cachés grandes y resultados. Primer commit = el estado actual con los arreglos. Al pasar a la carpeta nueva, la tarea programada corre desde ahí y la carpeta vieja de Drive queda como archivo (no editar dos copias).
3. **Golden tests** (pytest): con `--reusar` sobre `runs/2026-11-09_1851` y otra corrida, fijar como resultado esperado los hits, la vía, las unidades y la incidencia de cada aviso. Más tests chicos de `fetch.py` con HTML/JSON guardados (tarjeta patrocinada de ML, página de Zonaprop con repetidos, secuencia 403→403 que tiene que dar `BlockedError`). Todo cambio posterior tiene que pasarlos.
- Criterio de aceptación: dos lunes seguidos sin falsas fallas, el repo con su primer commit y los tests pasando.

**Fase B — Refactor multi-municipio con un solo municipio**
- Núcleo + `municipios/san_isidro/` según la sección 4. Nada de comportamiento nuevo.
- Crear `Drive / Scouting ZANARA / San Isidro /` con Normativa, Zonificación y Resultados, y mover ahí lo que corresponde de `data/`, `docs/` y `runs/` (copiar primero, borrar el original solo con el OK de Gonzalo).
- Criterio: reprocesar los crudos de la Fase A da exactamente los mismos hits, valores intermedios y mail.

**Fase C — Motor de descarga nuevo (cola, presupuesto, incremental, circuit breaker)**
- Solo San Isidro. Reemplaza a la descarga del lunes (no correr las dos en paralelo: duplicaría el tráfico).
- Criterio: 2–3 semanas con cobertura semanal equivalente a la actual (~1.480 avisos distintos) con menos páginas pedidas, y bloqueos registrados.

**Fase D — Segunda máquina** (si Gonzalo tiene una con otra IP)
- Verificar IPs distintas, reparto estático, exportación a Drive y consolidación en la principal.

**Fase E — CABA** (tipo A; empezar por acá porque no necesita vectorizar)
- Primero responder con Gonzalo las preguntas de 6.1. Después checklist de 6, con una o dos semanas en modo "solo reporte".

**Fase F — Primer partido de PBA** (el que elija Gonzalo) con su Fase 0 completa.

**Fase G — Resto de los partidos, uno por vez.**

Fase 3 de San Isidro (calibración con lo que Gonzalo marca en la Sheet) sigue pendiente y es independiente: se puede intercalar cuando haya datos.

## 8. Decisiones pendientes de Gonzalo (preguntar en su fase, no antes)

1. Lista y orden de municipios (propuesta: CABA → Tigre → San Fernando → Pilar).
2. Umbrales por municipio (incidencia, m² mínimos, ratio de loteo) y, en CABA, si se usan por barrio/comuna.
3. CABA: ¿la plusvalía entra en la incidencia?
4. ~~Un mail o varios~~ → **decidido el 13/11: un mail por municipio.**
5. ~~Sheet~~ → **decidido el 13/11: una Google Sheet por municipio.**
6. Remoto privado en GitHub para el repo (sí/no).
7. Segunda máquina: cuál, dónde, con qué conexión.
8. Demora aceptable para detectar bajas de precio (2–4 semanas con barrido rotativo).
9. Si algún portal endurece el bloqueo: ¿se acepta perder ese portal o se evalúa una fuente paga/comercial?

## 9. Lo que no hay que hacer

- Crear cuentas en los portales para repartir tráfico.
- Sortear desafíos anti-bot (proxies rotativos, captchas, navegadores stealth).
- Correr la descarga vieja y la nueva en paralelo.
- Agregar un municipio sin su normativa validada por Gonzalo.
- Copiar las reglas de producto de San Isidro a otro municipio "porque se parecen".
- Una SQLite compartida entre dos máquinas por Google Drive.
- Romper San Isidro: cada fase tiene que reproducir sus resultados (golden tests) antes de reemplazar lo que corre los lunes.
