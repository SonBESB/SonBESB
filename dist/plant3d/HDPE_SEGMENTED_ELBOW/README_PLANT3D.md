# HDPE_SEGMENTED_ELBOW — paquete de despliegue Plant 3D (Proof of Concept, V0.3)

Estado del paquete: **PLANT3D_PACKAGE_READY_FOR_VALIDATION** — todavia
NO ha sido probado contra una instalacion real de AutoCAD Plant 3D (este
paquete se genero en un entorno Linux sin Plant 3D; ver
docs/PLANT3D_ENVIRONMENT.md). El archivo `HDPE_SEGMENTED_ELBOW.py` es un
SCAFFOLD: su cabecera de metadata (`@activate`/`@group`/`@param`) esta
basada en documentacion publica real de Autodesk, pero la seccion de
geometria/puertos es un marcador explicito (`NOT_VERIFIED_AGAINST_REAL_PLANT3D_API`)
que un desarrollador con acceso al SDK real debe completar. Ver
docs/PLANT3D_CUSTOMSCRIPT.md para el detalle completo.

Caso de referencia (Golden Case): **DN110 PN10 90 grados**.

## 1. Donde copiar el .PY

Copia `HDPE_SEGMENTED_ELBOW.py` (y, si corresponde, sus iconos
`HDPE_SEGMENTED_ELBOW_32.png` / `_64.png` / `_200.png`) a:

```
<Shared Content Folder>\CPak Common\CustomScripts\
```

Esa ruta la puedes obtener corriendo `plant3d/environment/detector.py`
en la maquina con Plant 3D instalado, o copiando
`plant3d_config.example.yaml` a `plant3d_config.yaml` y completandolo a
mano (ver docs/PLANT3D_ENVIRONMENT.md).

## 2. Como ejecutar PLANTREGISTERCUSTOMSCRIPTS

1. Abre AutoCAD Plant 3D con el toolset Plant 3D activo.
2. En la linea de comandos escribe: `PLANTREGISTERCUSTOMSCRIPTS` y presiona Enter.
3. El comando compila los `.py` de `CPak Common\CustomScripts\` y los
   agrega a la libreria de formas parametricas.

## 3. Que resultado esperar

Dado que `HDPE_SEGMENTED_ELBOW.py` es un scaffold (ver arriba), **se espera que
la compilacion falle o que el script no aparezca funcional** hasta que
la seccion de geometria/puertos se complete con la API real de Plant 3D.
Este paquete existe para dejar listo todo lo que SI se puede preparar sin
esa API (metadata, datos parametricos, puertos mapeados) — no para
afirmar que ya funciona.

## 4. Como verificar que la forma aparece

Una vez completada la seccion de geometria: abre Shape Browser / Catalog
Builder en Plant 3D y busca el nombre del script (`HDPE_SEGMENTED_ELBOW`) bajo
el grupo `Fitting`. Registra el resultado en
`docs/PLANT3D_REGISTRATION_TEST.md` y copia la evidencia a
`plant3d_validation/registration_result.txt`.

## 5. Como detectar errores de compilacion

Plant 3D reporta errores de compilacion de CustomScripts en la linea de
comandos al ejecutar `PLANTREGISTERCUSTOMSCRIPTS`. Copia el texto
completo del error (si lo hay) a `plant3d_validation/registration_result.txt`
— nunca se debe marcar el estado `REGISTERED` sin ese archivo de
evidencia (ver `plant3d/deployment/manifest.py`).

## Contenido de este paquete

- `HDPE_SEGMENTED_ELBOW.py` — CustomScript scaffold.
- `golden_case.json` — parametros y puertos completos del caso DN110/PN10/90 (ver docs/GEOMETRY_VALIDATION_REFERENCE.md).
- `plant3d_config.example.yaml` — plantilla de configuracion de entorno.
- `validation_manifest.json` — estado de avance (GENERATED -> REGISTERED -> CATALOG_AVAILABLE -> SPEC_AVAILABLE -> MODEL_VALIDATED), basado solo en evidencia real.

## Siguientes pasos manuales (fuera de este paquete)

Ver, en orden: `docs/PLANT3D_REGISTRATION_TEST.md`,
`docs/PLANT3D_CATALOG_WORKFLOW.md`, `docs/PLANT3D_SPEC_TEST.md`,
`docs/PLANT3D_MODEL_ACCEPTANCE.md`.
