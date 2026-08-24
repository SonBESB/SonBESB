# Aceptación en modelo — checklist final (V0.3)

Este es el último de los cuatro pasos manuales del pipeline de validación
real (ver `plant3d_validation/README.md`). Se ejecuta sobre un modelo de
tuberías real en AutoCAD Plant 3D, después de
`docs/PLANT3D_SPEC_TEST.md`.

## Checklist de aceptación

- [ ] **Inserción**: el componente `HDPE_SEGMENTED_ELBOW` (DN110/PN10/90°,
      Golden Case) se inserta en el modelo sin error.
- [ ] **P1/P2 conectan**: ambos puertos se conectan correctamente a
      tramos de tubería DN110 adyacentes — sin "gap" ni superposición
      visible, y sin que Plant 3D marque un error de inconsistencia de
      línea (line inconsistency).
- [ ] **Orientación**: el ángulo entre P1 y P2 en el modelo corresponde a
      90°, coincidiendo con `params.angle_deg` del Golden Case.
- [ ] **Diámetro**: Plant 3D reporta DN110 para ambos extremos — coincide
      con `params.dn_mm` / `params.od_mm` (110 mm).
- [ ] **Geometría general**: las dimensiones visibles en el modelo
      (distancia P1-P2, altura, ancho) son razonablemente consistentes
      con `docs/GEOMETRY_VALIDATION_REFERENCE.md` / la tabla de
      "Dimensiones generales del sólido" de la UI (Modo C —
      Validación de ingeniería).
- [ ] **Reporte / BOM**: el componente aparece correctamente en un
      reporte o lista de materiales generado por Plant 3D para ese
      modelo (nombre, DN, material).

## Registrar el resultado

Completar `plant3d_validation/model_result.md` con:

- Qué cada ítem del checklist arriba dio como resultado (pasa / falla /
  no aplica), con capturas de pantalla en
  `plant3d_validation/screenshots/` cuando sea posible.
- Cualquier discrepancia dimensional u orientación incorrecta encontrada
  — sin omitir fallas, aunque sean menores.

Solo cuando `model_result.md` tiene contenido real (no vacío),
`plant3d/deployment/manifest.py` marca `current_stage = MODEL_VALIDATED`
y, únicamente en ese caso, `package_status` pasa de
`PLANT3D_PACKAGE_READY_FOR_VALIDATION` a `PLANT3D_VALIDATED`.

## Criterio de éxito de V0.3 (resumen)

```text
GENERATED           <- producido por este repo, sin Plant 3D instalado (ya alcanzado)
REGISTERED          <- requiere docs/PLANT3D_REGISTRATION_TEST.md + evidencia real
CATALOG_AVAILABLE   <- requiere docs/PLANT3D_CATALOG_WORKFLOW.md + evidencia real
SPEC_AVAILABLE       <- requiere docs/PLANT3D_SPEC_TEST.md + evidencia real
MODEL_VALIDATED      <- requiere este documento + evidencia real
```

`PLANT3D_VALIDATED` **nunca** se declara solo porque el código de este
repositorio corrió sin error — se declara únicamente cuando los cuatro
archivos de evidencia en `plant3d_validation/` contienen resultados
reales de una máquina Windows con AutoCAD Plant 3D instalado. Hasta
entonces, el estado correcto y honesto de este proyecto es
`PLANT3D_PACKAGE_READY_FOR_VALIDATION`.
