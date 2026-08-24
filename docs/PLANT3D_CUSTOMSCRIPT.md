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
