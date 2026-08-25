# Plant 3D CustomScript — investigación y generador (V0.3)

**Estado: Proof of Concept.** `plant3d/generators/custom_script_generator.py`
produce un archivo `.py` con el formato de un CustomScript de AutoCAD
Plant 3D, pero **nunca fue probado contra una instalación real** — este
proyecto se desarrolla en un entorno Linux sin Plant 3D instalado (ver
`docs/PLANT3D_ENVIRONMENT.md`). Este documento existe para que cualquiera
que lea el `.py` generado sepa exactamente qué parte viene de una fuente
real y qué parte es un marcador explícito pendiente de esa instalación.

## Regla fundamental: NO INVENTAR API DE PLANT 3D

Ningún decorador, función, módulo o clase de este generador fue escrito
"de memoria" o copiando un ejemplo genérico de internet sin verificar que
viniera de una fuente real de Autodesk. Donde la investigación no encontró
una fuente citable, el generador emite un marcador (`TODO`,
`NOT_VERIFIED_AGAINST_REAL_PLANT3D_API`) en vez de una llamada inventada.

## Qué se investigó y qué se encontró

Este proyecto no tiene acceso a Plant 3D ni a su SDK (confirmado: sistema
operativo Linux x86_64, `AutoCAD Plant 3D` es exclusivamente Windows).
`WebFetch` está bloqueado por el proxy de salida de este entorno para
todos los dominios probados (incluido `example.com`), así que la única
evidencia disponible fue el contenido citado en los fragmentos devueltos
por `WebSearch`. Lo que se pudo confirmar por esa vía:

| Elemento | Confirmado por | Uso en el generador |
|---|---|---|
| Comando `PLANTREGISTERCUSTOMSCRIPTS` | Ayuda pública de Autodesk (help.autodesk.com) | Documentado en README del paquete y en `docs/PLANT3D_REGISTRATION_TEST.md` |
| Carpeta `CPak Common\CustomScripts\` bajo el Shared Content Folder por versión | Ayuda pública de Autodesk | `plant3d/environment/detector.py` |
| Convención de íconos `{script}_32.png` / `_64.png` / `_200.png` | blog.autodesk.io (serie "Custom Python Scripts for AutoCAD Plant 3D") | Mencionada en el README del paquete, no generada (no hay ícono real que copiar) |
| Decoradores `@activate`, `@group`, `@param` | blog.autodesk.io (partes 2 y 3) y handout PD1746 de Autodesk University | Emitidos textualmente en el header del `.py` generado |
| Argumentos `Group`, `TooltipShort`, `TooltipLong`, `LengthUnit`, `Ports`, `FirstPortEndtypes` | Mismas fuentes | Usados solo los confirmados (`FirstPortEndtypes` se documenta pero no se usa porque el código de extremo HDPE no está confirmado, ver abajo) |
| Constante de tipo `LENGTH` para `@param` | Mismas fuentes | Usada en `@param(OD=LENGTH, ...)` etc. |
| Imports `from aqa.math import *`, `from varmain.primitiv import *`, `from varmain.custom import *` | Mismas fuentes | Emitidos textualmente |
| Cuerpo real de la función de entry point (qué API llama para construir geometría / puertos) | **No confirmado** | Ver "Qué NO se generó" abajo |
| Código de `EndType` de Plant 3D para termofusión HDPE | **No confirmado** — Plant 3D gestiona extremos vía el comando separado `PLANTENDCODES`, sin instancia real para consultarlo | `plant3d/generators/port_mapping.py` deja `plant_end_type = "REQUIRES_PLANT_CONFIGURATION"` |

Las URLs exactas usadas como cita quedan en
`plant3d.generators.custom_script_generator.SOURCE_CITATIONS` y se repiten
textualmente dentro del `.py` generado, para que la procedencia viaje con
el archivo.

## Pipeline (sin geometría duplicada)

```text
Excel / fuente de datos
        |
        v
ElbowParameters               (core/models/elbow.py)
        |
        v
SegmentedElbowGeometry         (core/geometry/segmented_elbow.py — motor 3D real)
        |
        v
map_ports()                    (plant3d/generators/port_mapping.py — lee geometry.ports)
        |
        v
generate_custom_script()       (plant3d/generators/custom_script_generator.py)
        |
        v
HDPE_SEGMENTED_ELBOW.py
```

`custom_script_generator.py` no contiene trigonometría, tolerancias ni
lógica de segmentos propia: todo número que aparece en el `.py` generado
(`GOLDEN_CASE_PARAMETERS`, `GOLDEN_CASE_PORTS`) se lee directamente de los
objetos `ElbowParameters` / `SegmentedElbowGeometry` ya construidos y
validados por el motor geométrico existente (V0.2 / V0.2.1). Si esos
valores cambian, el generador los refleja automáticamente — nunca los
recalcula con una fórmula propia.

## Qué SÍ se generó

- Header de metadata: docstring, imports, `@activate`/`@group`/`@param`
  con los argumentos confirmados arriba, citando las fuentes inline.
- `GOLDEN_CASE_PARAMETERS`: diccionario plano con OD/THK/ID/R/Le/Z/ángulo
  y la descomposición de segmentos (cuando existe) — datos, no llamadas
  de API.
- `GOLDEN_CASE_PORTS`: la salida de `map_ports()` (ver
  "Mapeo de puertos P1/P2" abajo) como lista de diccionarios.
- Una función `UNCONFIRMED_PLANT3D_ENTRY_POINT()` como destino sintáctico
  de los decoradores (Python exige que un decorador preceda a una
  `def`/`class`) — su nombre y cuerpo están explícitamente marcados como
  no verificados, con un `raise NotImplementedError(...)`.

## Qué NO se generó (y por qué)

- Ninguna llamada real para construir el sólido (`varmain.primitiv` /
  `varmain.custom` reales) — no se confirmó su firma exacta.
- Ninguna llamada real para posicionar los puertos 1..2 (un hilo del foro
  de Autodesk menciona una función `setPoint`, pero no se confirmó su
  firma ni módulo — no se inventa).
- Ningún código de `EndType` para termofusión — ver tabla arriba.
- Ningún tipo de parámetro Plant 3D para el ángulo del codo (`ANGLE_DEG`)
  — solo `LENGTH` quedó evidenciado como tipo real de `@param`; el
  ángulo queda como comentario `# TODO` explícito, sin inventar un tipo.

## Bug encontrado y corregido durante el desarrollo

La primera versión del generador colocaba los decoradores
`@activate`/`@group`/`@param` directamente sobre una asignación de
diccionario (`GOLDEN_CASE_PARAMETERS = {...}`), lo cual es un
`SyntaxError` en Python (los decoradores solo pueden preceder a una
`def`/`class`). Se detectó ejecutando `ast.parse()` sobre la salida antes
de entregarla, y se corrigió agregando la función
`UNCONFIRMED_PLANT3D_ENTRY_POINT()` como destino explícito. La suite de
tests (`tests/test_plant3d_generators.py`) incluye una prueba de
regresión (`ast.parse()` sobre la salida) para que este error no pueda
reintroducirse en silencio.

## Mapeo de puertos P1/P2

Ver `plant3d/generators/port_mapping.py`: `map_ports()` recorre
`geometry.ports` (ya calculado por `core/geometry/segmented_elbow.py`) y
reempaqueta cada `Port` en un `PlantPortMapping` con posición, dirección,
diámetro nominal, diámetro exterior y tipo de extremo — sin recomputar
ninguna coordenada. `plant_port_index` sigue la convención `Ports=N` de
Plant 3D (1-based).

## Determinismo

`generate_custom_script()` con las mismas entradas produce siempre el
mismo texto byte a byte: no hay timestamps embebidos ni orden
no-determinista. Cubierto por
`tests/test_plant3d_generators.py::test_generated_script_is_deterministic`.

## Qué falta para pasar de PROOF OF CONCEPT a algo ejecutable en Plant 3D

1. Acceso real a una instalación de AutoCAD Plant 3D (o a su SDK) para
   inspeccionar `varmain.primitiv` / `varmain.custom` reales.
2. Confirmar la firma real para posicionar puertos.
3. Confirmar (vía `PLANTENDCODES` en una instalación real) un código de
   extremo para termofusión HDPE, o una configuración manual documentada.
4. Ejecutar `PLANTREGISTERCUSTOMSCRIPTS` sobre el `.py` completado y
   registrar el resultado real en `plant3d_validation/registration_result.txt`
   (ver `docs/PLANT3D_REGISTRATION_TEST.md`).

Hasta que eso ocurra, el estado máximo declarado por este proyecto es
`PLANT3D_PACKAGE_READY_FOR_VALIDATION` — nunca `PLANT3D_VALIDATED`.

## V0.3.1 — primera evidencia real (AutoCAD Plant 3D 2025)

El punto 4 de arriba dejó de ser teórico: el `.py` de V0.3 (commit
`1feb598`) se probó en una instalación real de **AutoCAD Plant 3D 2025**
(Windows, Shared Content en
`C:\AutoCAD Plant 3D 2025 Content\CPak Common\CustomScripts\`). Evidencia
completa en `plant3d_validation/registration_result.txt`. Resumen:

| Paso | Resultado real |
|---|---|
| `PLANTREGISTERCUSTOMSCRIPTS` | Sin errores en línea de comandos — `REGISTER = PASS` |
| `(arxload "PnP3dACPAdapter")` | `"PnP3dACPAdapter"` — `ACP_ADAPTER = PASS` |
| `(testacpscript "HDPE_SEGMENTED_ELBOW")` | `nil`, sin geometría — `TESTACPSCRIPT = NIL` |

**Causa identificada** (real, no hipótesis): el script se llama
`HDPE_SEGMENTED_ELBOW.py` pero el V0.3 scaffold definía
`def UNCONFIRMED_PLANT3D_ENTRY_POINT():` como entry point. El lookup de
formas de Plant 3D exige que el nombre de la rutina coincida con el
nombre del script — `ENTRY_POINT_MATCH = FAIL`. Esto confirma, con
evidencia real y no solo con la nota de troubleshooting de la
comunidad citada abajo, exactamente el riesgo que ya advertía la sección
"Bug encontrado y corregido durante el desarrollo": el placeholder
sintácticamente válido no era funcionalmente válido.

**Estado global tras V0.3.1: `PLANT3D_VALIDATION_IN_PROGRESS`** — ni
`PLANT3D_PACKAGE_READY_FOR_VALIDATION` a secas (ya hay evidencia real
parcial) ni `PLANT3D_VALIDATED` (todavía no hay geometría real
confirmada). `plant3d/deployment/manifest.py` refleja esto con
`current_stage = REGISTERED` (el registro/compilación sí tiene evidencia
real) y `package_status` todavía en
`PLANT3D_PACKAGE_READY_FOR_VALIDATION`.

### Fuentes adicionales confirmadas en V0.3.1

Corroboran, con múltiples ejemplos reales independientes, la existencia
y el patrón de uso de `CYLINDER`, `.rotateY(...)`, `.uniteWith(...)`,
`s.setPoint(...)`, la convención `def SCRIPT_NAME(s, ..., **kw):`, y el
comportamiento de `TESTACPSCRIPT`/`PnP3dACPAdapter` (ver
`plant3d/generators/validation_script_generator.py::SOURCE_CITATIONS`):

- https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-2/
- https://blog.autodesk.io/custom-python-scripts-for-autocad-plant-3d-part-3/
- https://static.au-uw2-prd.autodesk.com/PD1746_handout_1746_pd1746_20-_20scripting_20components_20for_20autocad_20plant_203d.pdf
- https://mgfx.co.za/blog/uncategorized/plant-3d-adding-custom-components-part-2-breaking-down-the-code/
- https://enginine.com/2025/11/11/custom-python-scripts-for-autocad-plant-3d-case-study-of-tubing-fittings-part-1/
- https://pipingcontent.com/blog/plant3d-python-testacpscript-debugging-loop
- https://forums.autodesk.com/t5/autocad-plant-3d-forum/testacpscript-unknown-command/td-p/11901666

Como en V0.3, `WebFetch` sigue bloqueado en este sandbox — estas fuentes
se verificaron por fragmentos de `WebSearch`, no por el contenido
completo de la página. Un dato concreto (`def TESTSCRIPT2(s, D=80.0,
L=150.0, OF=-1, **kw):` con `s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0,
0.0), 0.0)` / `s.setPoint((L, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)`) sí
apareció citado literalmente en un snippet — ese es el patrón exacto que
usa `validation_script_generator.py` para el entry point y los puertos.
`CYLINDER`/`.rotateY(...)`/`.uniteWith(...)` están confirmados como
existentes y usados en ese patrón (construir → transformar → unir booleano)
en múltiples scripts reales independientes, pero **ningún snippet
disponible citó literalmente el orden de argumentos del constructor de
`CYLINDER`** — por eso `validation_script_generator.py` lo marca
explícitamente como reconstrucción best-effort, no como cita verificada,
y evita `.rotateY(...)`/`.uniteWith(...)` hasta tener evidencia real de
su semántica de posicionamiento.

### V0.3.1A — script mínimo de validación (no es el codo)

`plant3d/generators/validation_script_generator.py` reemplaza el entry
point roto por uno mínimo y correctamente nombrado:

```python
def HDPE_SEGMENTED_ELBOW(s, OD=110.0, THK=6.6, R=165.0, LE=150.0, Z=315.0, **kw):
    tramo = CYLINDER(s, R=OD / 2.0, H=LE, O=0.0).rotateY(90.0)
    s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)
    s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
```

Explícitamente marcado `VALIDATION_GEOMETRY_ONLY` — un solo tramo recto,
NO el codo segmentado DIN 16963. Su único propósito es confirmar, en
Plant 3D 2025 real, que `SCRIPT EXECUTION`, `GEOMETRY API`
(`CYLINDER(...).rotateY(...)`) y `PORT API` (`s.setPoint(...)`) funcionan
de extremo a extremo antes de intentar la geometría segmentada real
(V0.3.1B). `.uniteWith(...)` no se usa todavía — solo hay un primitivo,
nada que unir hasta V0.3.1B.

**Corrección del constructor de `CYLINDER` (segunda iteración de
V0.3.1A):** la primera versión usaba `CYLINDER(OD, LE)`, marcado
explícitamente como reconstrucción best-effort sin cita literal. El
usuario propuso la corrección `CYLINDER(s, R=D/2.0, H=L, O=0.0)` +
`.rotateY(90.0)`, atribuyéndola a documentación de Autodesk. En vez de
aceptarla solo de confianza, se repitió la misma investigación
WebSearch-only ya usada en todo V0.3/V0.3.1 (`WebFetch` sigue bloqueado
en este sandbox) y se encontró una corroboración **independiente**: un
resultado que cita el artículo oficial de la base de conocimiento de
Autodesk *"Plant 3D Custom Python scripting for catalog parts
Reference"* junto con el handout *"Annex B: Creating Custom Component
Scripts in Plant 3D"*, describiendo un `TESTSCRIPT` real que construye
`CYLINDER(s, R=D/2, H=L, O=0.0).rotateY(90)` — la misma forma de llamada,
desde una fuente distinta a la del usuario. Con esa segunda fuente, la
firma pasó de "reconstrucción best-effort" a "corroborada de forma
independiente" (aunque todavía solo vía snippets de `WebSearch`, no el
documento completo — la confirmación definitiva sigue siendo la prueba
real en Plant 3D).

También se detectó una inconsistencia menor en la corrección propuesta
por el usuario: su primera llamada `s.setPoint(...)` traía solo 2
argumentos (sin el `0.0` final), mientras la segunda sí lo traía. Como
no hay evidencia de una variante de 2 argumentos y el único ejemplo real
citado literalmente (`TESTSCRIPT2`) usa 3 argumentos en ambas llamadas,
el generador mantiene 3 argumentos en las dos — la discrepancia se
señaló en vez de copiarse tal cual (probable error de transcripción del
usuario, no una corrección deliberada).

Generador cubierto por `tests/test_plant3d_validation_script.py`
(validez `ast.parse()`, determinismo, nombre de entry point, firma de
`CYLINDER`, patrón de puertos, ausencia de `.pcat`/`.pspx`/`.pspc`).

### V0.3.1B1 — validacion sin puertos (plan por etapas, sin saltar ninguna)

Antes de que V0.3.1A (con la firma corregida de `CYLINDER`) llegara a
probarse en el entorno real, el usuario definio un plan explicito por
etapas para separar aun mas las variables en juego:

```text
V0.3.1B1  -- CYLINDER(...).rotateY(90), Ports=1, SIN s.setPoint(...)
V0.3.1B2  -- (futura) Ports=2, agrega P1/P2, valida s.setPoint(...)
V0.3.1B3  -- (futura) geometria real del codo DN110/PN10/90 (4 gajos)
```

`generate_validation_script_b1()` en
`plant3d/generators/validation_script_generator.py` produce esta
version minima: mismo `CYLINDER(s, R=OD/2.0, H=LE, O=0.0).rotateY(90)`
ya usado en V0.3.1A, pero sin ningun `s.setPoint(...)`, `Ports=1` en vez
de `2`, `Group="Support"` en vez de `"Fitting"`, y solo `OD`/`LE` como
parametros con efecto (`OF`/`K` se reciben pero no se usan). Su unico
proposito es aislar si la familia/nombre propios de este proyecto
(`HDPE_SEGMENTED_ELBOW` como archivo y como rutina) ejecutan bajo el
lookup de componentes de Plant 3D, antes de reintroducir puertos.

Dos elementos nuevos de API, verificados de forma independiente por
WebSearch antes de usarse (no aceptados solo porque el usuario los
propuso, mismo estandar que el resto de V0.3/V0.3.1):

- `Ask4Dist=True` en un `@param(...=LENGTH, ...)`: confirmado por un
  hilo dedicado de Autodesk Community ("Plant 3D Python Scripts: Help
  Understanding Ask4Dist").
- `def NOMBRE(s, D=80.0, L=150.0, OF=-1, K=1, **kw):`: confirmado por
  una cita literal con esa forma exacta de firma.

Prueba real siguiente:
`(testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "LE" "150")` — se
espera un cilindro OD=110mm x L=150mm. Solo si esto produce el objeto
esperado se avanza a V0.3.1B2 (reintroducir `Ports=2` + `s.setPoint`);
solo despues de B2 se avanza a V0.3.1B3 (geometria real del codo, 4
gajos 15°-30°-30°-15°). Sin saltar etapas.

Generador cubierto por las pruebas `test_b1_*` en
`tests/test_plant3d_validation_script.py`.

### V0.3.1B1 — VALIDADO EN AUTOCAD PLANT 3D 2025 REAL

```text
(testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "LE" "150")
-> <Entity name: ...>  (cilindro visible OD=110mm x L=150mm)

V0.3.1B1                    = PASS
HDPE_ENTRY_POINT            = PASS
PARAMETER_PASSING           = PASS
CYLINDER_API                = PASS
ROTATEY_API                 = PASS
GEOMETRY_CREATION           = PASS
TESTACPSCRIPT_ENTITY_RETURN = PASS
```

Evidencia completa en `plant3d_validation/registration_result.txt`.
Esta es la primera confirmacion real de que la cadena completa (entry
point propio + `CYLINDER(...).rotateY(...)` + `PLANTREGISTERCUSTOMSCRIPTS`
+ `PnP3dACPAdapter` + `TESTACPSCRIPT`) funciona de punta a punta en Plant
3D 2025 — para esta geometria minima, todavia sin puertos. El estado
global sigue en `PLANT3D_VALIDATION_IN_PROGRESS` (esto confirma
geometria base, no confirma puertos ni el codo real).

### V0.3.1B2 — agrega Ports=2 + s.setPoint(...), sin tocar la geometria de B1

`generate_validation_script_b2()` cambia EXACTAMENTE dos cosas sobre la
version de B1 ya validada en real:

```python
Ports=1  ->  Ports=2

# + dos llamadas nuevas, con la misma forma ya confirmada desde V0.3.1A
# (posicion, direccion, 0.0):
s.setPoint((0.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 0.0)   # P1
s.setPoint((LE, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)     # P2
```

El `CYLINDER(s, R=OD/2.0, H=LE, O=0.0).rotateY(90)` de B1 no se toca —
B2 no introduce ninguna API nueva sin confirmar: `Ports=N` y la forma de
`s.setPoint(...)` ya estaban confirmadas desde V0.3.1A, y `CYLINDER`/
`rotateY` ya tienen confirmacion de hardware real desde B1. Sigue sin
`THK`/`R`/`Z`/`PN`/`SDR`/`EndType`/`ButtFusion`/geometria segmentada —
eso empieza recien en V0.3.1B3. Generador cubierto por las pruebas
`test_b2_*` en `tests/test_plant3d_validation_script.py`.

### V0.3.1B2 — VALIDADO EN AUTOCAD PLANT 3D 2025 REAL

```text
(testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "LE" "150")
-> <Entity name: ...>, sin errores

V0.3.1B2                    = PASS
PORT_COUNT_2                 = PASS
SETPOINT_P1                  = PASS
SETPOINT_P2                  = PASS
GEOMETRY_CREATION            = PASS
TESTACPSCRIPT_ENTITY_RETURN  = PASS
```

Evidencia completa en `plant3d_validation/registration_result.txt`. El
usuario señalo explicitamente: esto valida la EJECUCION de `setPoint`,
todavia NO valida conexion fisica con Pipe, EndType, Catalog ni Spec —
eso viene despues de que la geometria real del codo (V0.3.1B3) tambien
pase.

### V0.3.1B3A — geometria real del codo (exterior, sin corte a inglete)

`plant3d/generators/segmented_elbow_script_generator.py` (nuevo modulo,
distinto de `validation_script_generator.py` porque este SI consume
`ElbowParameters`/`SegmentedElbowGeometry` reales) construye por primera
vez el codo DN110/PN10/90 completo: 4 gajos (15°-30°-30°-15°) + 2 tramos
Le, calculados UNA SOLA VEZ por `core/geometry/segmented_elbow.py` (ya
probado, sin duplicar la trigonometria) y horneados como constantes
literales en el `.py` generado — el script en si no reimporta
`core.geometry...` (no estaria disponible dentro de Plant 3D) ni
recalcula nada.

**Simplificacion revelada explicitamente** (autorizada por el usuario:
*"si resulta necesario, dividir B3A/B3B, no esconder esa
simplificacion"*): los 6 tramos son `CYLINDER` rectos SIN corte a
inglete — las 3 uniones internas entre gajos son solapes de cilindros de
tapa redonda, no cortes planos a bisectriz. Un hilo real de Autodesk
Community titulado *"Creation of miter bend without straight parts"*
describe un script funcional para esto (usando `ARC3DS`/`PYRAMID` +
`rotateX`/`rotateZ` + `translate` + `subtractFrom`), pero `WebFetch`
sigue bloqueado en este sandbox — solo se pudo leer un resumen generado
por el motor de busqueda, nunca el codigo literal ni la matematica de
los planos de corte. Inventar esa matematica a partir de un resumen
violaria la regla NO INVENTAR API DE PLANT 3D, asi que el corte a
inglete real queda diferido hasta que ese hilo (o una fuente equivalente)
se pueda leer completo. Tampoco incluye el taladro interior (THK/ID) —
eso es V0.3.1B3B, deliberadamente separado para poder aislar un fallo a
la union de 6 piezas (este archivo) o a la sustraccion hueca (B3B) por
separado.

**Composicion rotate/translate**: el unico ejemplo real literal de
`.translate(...)` encontrado lo encadena inmediatamente despues de
`CYLINDER(...)`, sin rotacion en esa misma cadena — no hay evidencia de
si Plant 3D compone rotar-luego-trasladar igual que trasladar-luego-rotar
(en general no son lo mismo, salvo que la rotacion pivote sobre la
posicion actual del objeto). Para no adivinar, cada pieza se construye
como `CYLINDER(...).rotateY(theta).translate(inicio)`: rotar primero,
mientras la pieza todavia esta en el origen local (ahi "pivotar sobre el
objeto" y "pivotar sobre el origen global" son lo mismo), y trasladar
una sola vez a su posicion final (ahi "mover a un punto absoluto" y
"mover por un desplazamiento" tambien coinciden, porque la posicion
previa a trasladar YA es el origen). Ver el docstring del modulo para el
detalle completo.

**Mapeo de coordenadas**: `core/geometry/segmented_elbow.py` construye
el codo en su propio plano XY (Z siempre 0). La unica rotacion con
confirmacion de hardware (`rotateY(90)`, confirmada por B1/B2) alcanza
el plano XZ de Plant 3D, no el XY. En vez de adivinar como componen
`rotateY`+`rotateZ` juntos, este generador intercambia las componentes Y
y Z de cada punto/direccion (nuestro `(x, y, 0)` -> Plant 3D
`(x, 0, y)`), reproduciendo el codo completo usando solo el eje de
rotacion ya confirmado. Es una decision de este generador, no una
llamada a la API de Plant 3D — no necesita cita.

Verificado matematicamente (sin depender de Plant 3D real) que la
cadena de 6 piezas es geometricamente continua: el punto final de cada
pieza (inicio + longitud·direccion tras `rotateY`) coincide exactamente
con el punto de `translate` de la siguiente — cubierto por
`tests/test_plant3d_segmented_elbow_script.py::test_piece_chain_is_geometrically_continuous`.

**Elementos usados por primera vez, sin confirmacion de hardware
todavia**: `translate(...)`, angulos de `rotateY` distintos de 90°
(82.5°/60°/30°/7.5°/0°), y union de 6 piezas via `uniteWith()` +
`.erase()` (el patron `.erase()` esta confirmado para
`subtractFrom()`/`intersectWith()`; para `uniteWith()` es una inferencia
por analogia, sin cita literal propia — sinalado explicitamente en los
`warnings` del generador).

Generador cubierto por `tests/test_plant3d_segmented_elbow_script.py`.

### V0.3.1B3A — VALIDADO EN AUTOCAD PLANT 3D 2025 REAL

```text
(testacpscript "HDPE_SEGMENTED_ELBOW")
-> geometria generada correctamente: tramo horizontal, cuatro gajos,
   tramo vertical, transicion total ~90°, y los solapes esperados entre
   cilindros (sin cortes a inglete todavia -- NO es un fallo)

V0.3.1B3A               = PASS
MULTIPLE_CYLINDER       = PASS
ROTATEY_ARBITRARY       = PASS
TRANSLATE               = PASS
UNITEWITH               = PASS
ERASE                   = PASS
SEGMENT_CHAIN           = PASS
PLANT3D_NATIVE_GEOMETRY = PASS
```

Evidencia completa en `plant3d_validation/registration_result.txt`.
Primera confirmacion real de `translate(...)`, angulos `rotateY`
distintos de 90°, y union de 6 piezas via `uniteWith()`+`.erase()` — los
tres elementos que B3A introducia sin confirmacion de hardware. Los
solapes visibles en las 3 juntas internas son el resultado esperado de
la simplificacion ya revelada (sin corte a inglete todavia), confirmado
por el usuario explicitamente como no-fallo.

### V0.3.1B3B-1 — prueba minima de `subtractFrom()` (tubo hueco simple)

Con B3A confirmado, el siguiente paso NO modifica la cadena de 6 piezas
directamente: `generate_validation_script_b3b1()` (en
`plant3d/generators/validation_script_generator.py`, junto a B1/B2 —
sigue sin consumir `ElbowParameters`/geometria real, es de nuevo un
fixture de validacion) aisla `subtractFrom()` en el caso mas simple
posible: un solo tubo recto (misma forma que B1/B2), OD110/ID96.8/e6.6,
marcado `VALIDATION_HOLLOW_GEOMETRY_ONLY`.

```python
id_mm = OD - 2 * THK  # misma ecuacion que core/models/elbow.py

tubo_exterior = CYLINDER(s, R=OD / 2.0, H=LE, O=0.0).rotateY(90)
tubo_interior = CYLINDER(s, R=id_mm / 2.0, H=LE + 10, O=-5).rotateY(90)

tubo_exterior.subtractFrom(tubo_interior)
tubo_interior.erase()
```

A diferencia de `uniteWith()` en B3A (inferido por analogia),
`subtractFrom()` y su `.erase()` requerido SI tienen cita literal
directa: *"BOX1.subtractFrom(BOX2) to subtract BOX2 from BOX1 ... the
second object must be removed from memory with .erase"* (ver
SOURCE_CITATIONS). El cilindro interior se construye 5mm mas largo por
cada extremo — una decision de modelado propia de este generador
(tecnica CAD estandar para evitar caras coincidentes en la resta), no
una convencion de la API de Plant 3D. Los puertos se mantienen
identicos al patron ya confirmado en B1/B2 (`Ports=2` + los mismos dos
`s.setPoint(...)`) precisamente porque no introducen ninguna variable
nueva. Generador cubierto por las pruebas `test_b3b1_*` en
`tests/test_plant3d_validation_script.py`.

### V0.3.1B3B-1 — VALIDADO EN AUTOCAD PLANT 3D 2025 REAL

```text
(testacpscript "HDPE_SEGMENTED_ELBOW" "OD" "110" "THK" "6.6" "LE" "150")
-> tubo hueco generado correctamente, hueco interior visible

V0.3.1B3B-1             = PASS
SUBTRACTFROM            = PASS
ERASE_AFTER_SUBTRACTION = PASS
HOLLOW_GEOMETRY         = PASS
```

Evidencia completa en `plant3d_validation/registration_result.txt`. El
usuario señalo explicitamente: la evidencia visual confirma el hueco,
pero NO se declara validacion dimensional exacta de ID=96.8mm hasta
medirlo con `DIST`/`MEASURE` en Plant 3D (ver
`docs/PLANT3D_MODEL_ACCEPTANCE.md`).

### V0.3.1B3B-2 — la cadena de B3A, ahora hueca

`generate_segmented_elbow_script()` gano un parametro `hollow: bool =
False` (retrocompatible — con `hollow=False` produce, byte a byte salvo
comentarios/citas, el mismo `.py` que ya paso B3A en real). Con
`hollow=True`, cada una de las 6 piezas se construye como:

```python
ext_i = CYLINDER(s, R=radio_ext_mm, H=..., O=0.0).rotateY(...).translate(...)
int_i = CYLINDER(s, R=radio_int_mm, H=...+10, O=-5).rotateY(...).translate(...)
ext_i.subtractFrom(int_i)
int_i.erase()
```

usando el MISMO angulo/posicion ya validado por B3A para ambos
cilindros (exterior e interior deben ser coaxiales), y el mismo margen
de sobre-extension de 5mm por extremo ya confirmado en real por B3B-1.
Solo despues de huecar las 6 piezas se ejecuta la cadena de union
(`uniteWith()`+`.erase()`), exactamente igual que en B3A — la
matematica de posiciones/angulos y la cadena de union no se tocan, solo
cambia como se construye cada pieza individual. `THK` pasa de "recibido
pero no usado" (B3A) a afectar realmente el taladro (`radio_int_mm = (OD
- 2*THK) / 2.0`). Generador cubierto por las pruebas `test_hollow_*` en
`tests/test_plant3d_segmented_elbow_script.py`, incluyendo una guarda de
retrocompatibilidad que confirma que `hollow=False` sigue produciendo el
contenido ejecutable ya validado de B3A.

### V0.3.1B3B-2 — VALIDADO EN AUTOCAD PLANT 3D 2025 REAL

```text
(testacpscript "HDPE_SEGMENTED_ELBOW")
-> seccion longitudinal real: conducto interior continuo desde el
   tramo horizontal hasta el vertical, sin pared transversal que
   bloquee el flujo

V0.3.1B3B-2             = PASS
B3B-2_SCRIPT_EXECUTION  = PASS
B3B-2_HOLLOW_GEOMETRY   = PASS
B3B-2_CONTINUOUS_BORE   = PASS
HOLLOW_90_DEG_CHAIN     = PASS
```

Evidencia completa en `plant3d_validation/registration_result.txt`. NO
se implemento B3B-3 (no hizo falta). El usuario señalo explicitamente
que la seccion tambien muestra escalones/intersecciones locales en las
uniones (esperado — los solapes de B3A/B3B, sin corte a inglete
todavia), por lo que aun NO se declaran `CONSTANT_ID_AT_JOINTS`,
`CONSTANT_THICKNESS_AT_JOINTS` ni `FABRICATION_GEOMETRY_VALIDATED` —
esos quedan pendientes de los cortes reales (B3C).

### V0.3.1B3C-1 — investigación y primera junta real a inglete (fixture aislado)

Antes de escribir nada, se investigo la estrategia de corte real (regla
explicita del usuario: *"no inventar firmas ni semantica"*). Hallazgos:

- **`BOX(s, L, W, H)`** — firma literal confirmada por una respuesta
  real de Autodesk Community, que ademas señala explicitamente que
  `BOX` **no** acepta un parametro `O` (a diferencia de `CYLINDER`).
- Un hilo real, *"Creation of miter bend without straight parts"*,
  describe un script funcional completo para mitered bends usando
  `ARC3DS(s, D, D2, R, A, S)` (un primitivo que construye TODA una
  curva multi-segmento de una sola vez) y `PYRAMID(s, L, W, H, HT)`
  como cuerpo cortador. **Investigado pero NO adoptado**: solo un
  resumen del buscador fue alcanzable (`WebFetch` sigue bloqueado), sin
  la matematica literal de los planos de corte, y no se pudo confirmar
  si `ARC3DS` soporta segmentacion **asimetrica** (15°-30°-30°-15°,
  la del Golden Case) o solo angulos uniformes por segmento — adoptarlo
  a ciegas podria producir silenciosamente el codo equivocado. Se
  mantiene el enfoque propio ya validado (`CYLINDER` por pieza,
  B3A/B3B) y se usa `BOX` (no `PYRAMID`/`ARC3DS`) solo como cuerpo
  cortador.

`plant3d/generators/miter_joint_script_generator.py` (nuevo modulo,
independiente de `segmented_elbow_script_generator.py` — no lo modifica
ni lo importa) construye un fixture aislado: **solo Gajo 2 (30°) + Gajo
3 (30°)**, la junta representativa del Golden Case, cada uno ya hueco
(mismo patron `subtractFrom()`+`.erase()` confirmado en real por
B3B-1/B3B-2), cortados contra su **plano bisectriz real compartido**
(`cut_plane_end` de Gajo 2 == `cut_plane_start` de Gajo 3, verificado
programaticamente antes de generar el script — no son dos planos
derivados independientemente que podrian no coincidir).

```python
cutter_a = BOX(s, L=2000, W=2000, H=500).rotateY(theta_cut).translate(...)
ext_a.subtractFrom(cutter_a)   # quita de Gajo 2 el lado hacia Gajo 3
cutter_a.erase()

cutter_b = BOX(s, L=2000, W=2000, H=500).rotateY(theta_cut + 180).translate(...)
ext_b.subtractFrom(cutter_b)   # quita de Gajo 3 el lado hacia Gajo 2
cutter_b.erase()
```

**Única suposición no confirmada, señalada explícitamente**: la
convención de origen local de `BOX` (esquina vs. centrado) no tiene
ninguna fuente que la confirme. Se asumió "esquina en el origen"
(consistente con `CYLINDER`, el único primitivo que este proyecto ha
confirmado realmente en hardware) y se compensó desplazando la
traslación en `(-L/2, -W/2)` rotado por el mismo ángulo del cuerpo
cortador — cálculo hecho en Python al generar el script, no una llamada
nueva de Plant 3D. `L=W=2000mm` es deliberadamente enorme frente al
OD de 110mm para que un eventual error en esa suposición tenga bajo
impacto. Si el corte queda mal ubicado en la prueba real, esa es la
primera hipótesis a revisar — el resultado, en cualquier caso, es
evidencia nueva sobre la convención real de `BOX`.

Generador cubierto por `tests/test_plant3d_miter_joint_script.py`,
incluyendo una verificación independiente de la matemática de
compensación de la caja cortadora y una comprobación de que ambos gajos
comparten el mismo plano bisectriz antes de generar el script.

### Siguiente paso

Probar V0.3.1B3C-1 en el mismo entorno (Plant 3D 2025):
`(testacpscript "HDPE_SEGMENTED_ELBOW")`, esperando dos gajos huecos
unidos por una sola cara de corte plana compartida — sin solape, sin
separación, taladro interior continuo a través de la junta. Registrar
el resultado real en una nueva entrada de
`plant3d_validation/registration_result.txt`. Si falla o el corte queda
mal ubicado, revisar primero la suposición de convención de `BOX`. Solo
si B3C-1 pasa se avanza a V0.3.1B3C-2 (aplicar el mismo principio a las
otras dos juntas del codo completo) — sin saltar etapas.
