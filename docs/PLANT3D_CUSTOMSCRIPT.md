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

### Siguiente paso

Probar V0.3.1A en el mismo entorno (Plant 3D 2025) y registrar el
resultado real en una nueva entrada de
`plant3d_validation/registration_result.txt`. Solo si
`(testacpscript "HDPE_SEGMENTED_ELBOW")` produce un objeto visible se
avanza a V0.3.1B (geometría real del codo DN110/PN10/90°, con los cuatro
gajos 15°-30°-30°-15° y el mapeo P1/P2 real vía
`plant3d/generators/port_mapping.py`).
