"""Assembles the deployment package a human takes to a real Windows
machine with Plant 3D installed: the generated CustomScript, a golden
case dataset, the validation manifest, an example config, and a README
explaining the manual steps.

Nothing here touches the real Plant 3D install (there isn't one). This
only writes plain files into an output directory.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List

from core.geometry.segmented_elbow import SegmentedElbowGeometry
from core.library.elbow_registration import ComponentRegistration
from core.models.elbow import ElbowParameters
from core.serialization.json_export import elbow_to_dict
from plant3d.deployment.manifest import build_initial_manifest, write_manifest
from plant3d.generators.custom_script_generator import generate_custom_script

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
EXAMPLE_CONFIG_PATH = REPO_ROOT / "plant3d_config.example.yaml"


def _readme_text(script_name: str, params: ElbowParameters) -> str:
    golden_label = f"DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados"
    return f"""# {script_name} — paquete de despliegue Plant 3D (Proof of Concept, V0.3)

Estado del paquete: **PLANT3D_PACKAGE_READY_FOR_VALIDATION** — todavia
NO ha sido probado contra una instalacion real de AutoCAD Plant 3D (este
paquete se genero en un entorno Linux sin Plant 3D; ver
docs/PLANT3D_ENVIRONMENT.md). El archivo `{script_name}.py` es un
SCAFFOLD: su cabecera de metadata (`@activate`/`@group`/`@param`) esta
basada en documentacion publica real de Autodesk, pero la seccion de
geometria/puertos es un marcador explicito (`NOT_VERIFIED_AGAINST_REAL_PLANT3D_API`)
que un desarrollador con acceso al SDK real debe completar. Ver
docs/PLANT3D_CUSTOMSCRIPT.md para el detalle completo.

Caso de referencia (Golden Case): **{golden_label}**.

## 1. Donde copiar el .PY

Copia `{script_name}.py` (y, si corresponde, sus iconos
`{script_name}_32.png` / `_64.png` / `_200.png`) a:

```
<Shared Content Folder>\\CPak Common\\CustomScripts\\
```

Esa ruta la puedes obtener corriendo `plant3d/environment/detector.py`
en la maquina con Plant 3D instalado, o copiando
`plant3d_config.example.yaml` a `plant3d_config.yaml` y completandolo a
mano (ver docs/PLANT3D_ENVIRONMENT.md).

## 2. Como ejecutar PLANTREGISTERCUSTOMSCRIPTS

1. Abre AutoCAD Plant 3D con el toolset Plant 3D activo.
2. En la linea de comandos escribe: `PLANTREGISTERCUSTOMSCRIPTS` y presiona Enter.
3. El comando compila los `.py` de `CPak Common\\CustomScripts\\` y los
   agrega a la libreria de formas parametricas.

## 3. Que resultado esperar

Dado que `{script_name}.py` es un scaffold (ver arriba), **se espera que
la compilacion falle o que el script no aparezca funcional** hasta que
la seccion de geometria/puertos se complete con la API real de Plant 3D.
Este paquete existe para dejar listo todo lo que SI se puede preparar sin
esa API (metadata, datos parametricos, puertos mapeados) — no para
afirmar que ya funciona.

## 4. Como verificar que la forma aparece

Una vez completada la seccion de geometria: abre Shape Browser / Catalog
Builder en Plant 3D y busca el nombre del script (`{script_name}`) bajo
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

- `{script_name}.py` — CustomScript scaffold.
- `golden_case.json` — parametros y puertos completos del caso DN110/PN10/90 (ver docs/GEOMETRY_VALIDATION_REFERENCE.md).
- `plant3d_config.example.yaml` — plantilla de configuracion de entorno.
- `validation_manifest.json` — estado de avance (GENERATED -> REGISTERED -> CATALOG_AVAILABLE -> SPEC_AVAILABLE -> MODEL_VALIDATED), basado solo en evidencia real.

## Siguientes pasos manuales (fuera de este paquete)

Ver, en orden: `docs/PLANT3D_REGISTRATION_TEST.md`,
`docs/PLANT3D_CATALOG_WORKFLOW.md`, `docs/PLANT3D_SPEC_TEST.md`,
`docs/PLANT3D_MODEL_ACCEPTANCE.md`.
"""


@dataclass(frozen=True)
class DeploymentPackage:
    output_dir: Path
    files: List[Path]
    warnings: List[str]


def build_deployment_package(
    params: ElbowParameters,
    geometry: SegmentedElbowGeometry,
    registration: ComponentRegistration,
    output_dir: Path,
    script_name: str = "HDPE_SEGMENTED_ELBOW",
) -> DeploymentPackage:
    output_dir.mkdir(parents=True, exist_ok=True)
    files: List[Path] = []

    script_result = generate_custom_script(params, geometry, registration, script_name=script_name)
    script_path = output_dir / f"{script_name}.py"
    script_path.write_text(script_result.source_code, encoding="utf-8")
    files.append(script_path)

    golden_case_payload = elbow_to_dict(params, geometry=geometry, registration=registration)
    golden_case_path = output_dir / "golden_case.json"
    golden_case_path.write_text(json.dumps(golden_case_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    files.append(golden_case_path)

    manifest = build_initial_manifest(
        component_family=registration.family.key,
        golden_case_label=f"DN{params.dn_mm:g} {params.pn} {params.angle_deg:g} grados",
    )
    manifest_path = write_manifest(manifest, output_dir / "validation_manifest.json")
    files.append(manifest_path)

    readme_path = output_dir / "README_PLANT3D.md"
    readme_path.write_text(_readme_text(script_name, params), encoding="utf-8")
    files.append(readme_path)

    if EXAMPLE_CONFIG_PATH.is_file():
        config_dest = output_dir / "plant3d_config.example.yaml"
        shutil.copyfile(EXAMPLE_CONFIG_PATH, config_dest)
        files.append(config_dest)

    return DeploymentPackage(output_dir=output_dir, files=files, warnings=script_result.warnings)
