# plant3d_validation/ — evidencia real, no afirmaciones

Esta carpeta guarda la evidencia de cada etapa del pipeline real de
validación en Plant 3D. `plant3d/deployment/manifest.py` lee estos
archivos para decidir `current_stage` — **nunca al revés**: nadie edita
`validation_manifest.json` a mano para "avanzar" el estado.

Los cuatro archivos de evidencia (`registration_result.txt`,
`catalog_result.md`, `spec_result.md`, `model_result.md`) se entregan
**vacíos** (0 bytes) en este repositorio a propósito: mientras estén
vacíos, `update_manifest_with_evidence()` los trata como "sin evidencia
todavía" y el estado no avanza más allá de `GENERATED`. Un archivo
cuenta como evidencia real solo cuando tiene contenido — la prueba
manual real, no una plantilla.

## Qué escribir en cada uno

| Archivo | Cuándo se llena | Qué debe contener |
|---|---|---|
| `registration_result.txt` | Después de `docs/PLANT3D_REGISTRATION_TEST.md` | Salida real de `PLANTREGISTERCUSTOMSCRIPTS` (éxito o el error de compilación completo) |
| `catalog_result.md` | Después de `docs/PLANT3D_CATALOG_WORKFLOW.md` | Confirmación de que la forma aparece en Catalog Builder, con el catálogo de prueba usado |
| `spec_result.md` | Después de `docs/PLANT3D_SPEC_TEST.md` | Confirmación de "Add to Spec" exitoso |
| `model_result.md` | Después de `docs/PLANT3D_MODEL_ACCEPTANCE.md` | Checklist de aceptación en modelo (P1/P2 conectan, orientación, diámetro, geometría) |
| `screenshots/` | En cualquier etapa | Capturas de pantalla como evidencia visual complementaria |

## Estados posibles (nunca declarar uno sin evidencia)

```text
GENERATED           <- este repo lo produce solo, sin Plant 3D instalado
REGISTERED          <- requiere registration_result.txt con contenido real
CATALOG_AVAILABLE   <- requiere catalog_result.md con contenido real
SPEC_AVAILABLE       <- requiere spec_result.md con contenido real
MODEL_VALIDATED      <- requiere model_result.md con contenido real
```

`package_status` solo pasa de `PLANT3D_PACKAGE_READY_FOR_VALIDATION` a
`PLANT3D_VALIDATED` cuando `current_stage == MODEL_VALIDATED` — es decir,
cuando los cuatro archivos tienen evidencia real. Ver
`docs/PLANT3D_MODEL_ACCEPTANCE.md` para el criterio de éxito completo de V0.3.
