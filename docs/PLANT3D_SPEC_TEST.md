# Spec Editor — prueba manual "Add to Spec" (V0.3)

**Estado: solo el flujo soportado oficialmente por Autodesk. Ningún
archivo `.pspx`/`.pspc` es leído ni editado por código de este
repositorio, y ninguna automatización de la UI de Spec Editor existe ni
está planeada en este proyecto.**

## Prerrequisito

Haber completado `docs/PLANT3D_CATALOG_WORKFLOW.md`: la forma
`HDPE_SEGMENTED_ELBOW` debe existir y aparecer correctamente en un
catálogo real de Plant 3D antes de poder agregarla a una especificación.

## Procedimiento manual

- [ ] **1. Abrir Spec Editor** en la instalación de Plant 3D, sobre el
      catálogo generado en el paso anterior.
- [ ] **2. Seleccionar (o crear) una especificación de prueba** — no una
      especificación de producción real.
- [ ] **3. Add to Spec**: agregar `HDPE_SEGMENTED_ELBOW` a esa
      especificación, para DN110/PN10 (Golden Case).
- [ ] **4. Verificar** que Spec Editor acepta el componente sin errores
      (dimensiones, material, clase de presión coherentes con lo cargado
      en Catalog Builder).
- [ ] **5. Registrar el resultado** en
      `plant3d_validation/spec_result.md`: qué especificación de prueba
      se usó, si "Add to Spec" fue exitoso, y cualquier mensaje de error
      o advertencia mostrado por Spec Editor. Mientras ese archivo esté
      vacío, `plant3d/deployment/manifest.py` no avanza a
      `SPEC_AVAILABLE`.

## Qué NO hacer

- No editar `.pspx`/`.pspc` directamente ni con ninguna librería fuera de
  Spec Editor.
- No automatizar los clics de Spec Editor — este proyecto no tiene (ni
  planea tener en V0.3) ningún driver de UI de AutoCAD.
- No marcar `SPEC_AVAILABLE` sin haber completado
  `plant3d_validation/spec_result.md` con contenido real.

## Siguiente paso

Con `spec_result.md` completo, continuar con
`docs/PLANT3D_MODEL_ACCEPTANCE.md` — la prueba final: insertar el
componente en un modelo real y verificar que conecta correctamente.
