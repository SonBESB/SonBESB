# Catalog Builder — flujo manual (V0.3)

**Estado: solo el flujo soportado oficialmente por Autodesk. Ningún
archivo `.pcat` es leído, escrito ni editado por código de este
repositorio — ni ahora ni en ninguna etapa futura planeada.** Plant 3D
Catalog Builder es la única herramienta que este proyecto asume para
crear o modificar un catálogo.

## Por qué no se edita `.pcat` directamente

`.pcat` es un formato binario/opaco propio de Autodesk. Editarlo a mano
(por SQL directo, por edición binaria, o por cualquier librería que no
sea la propia Catalog Builder) no está soportado por Autodesk y podría
corromper el catálogo. Este proyecto explícitamente prohíbe ese camino —
ver la regla "NO INVENTAR API DE PLANT 3D" en
`docs/PLANT3D_CUSTOMSCRIPT.md`.

## Qué SÍ existe hoy en este repositorio

- `plant3d/catalog/catalog_builder_payload.py`: construye un diccionario
  plano (DN, PN, OD, THK, ID, SDR, R, Le, Z, ángulo, configuración de
  segmentos) a partir de `ElbowParameters` / `SegmentedElbowGeometry` ya
  validados. No es un archivo de Autodesk ni asume ningún formato de
  columnas — son solo nuestros propios números.
- `plant3d/catalog/catalog_builder_excel_exporter.py`:
  `CatalogBuilderExcelExporter.export_to_excel()` está preparado para
  transformar ese payload al formato Excel exacto que Catalog Builder
  exporta con **Export to Excel**, pero **siempre levanta
  `ReferenceTemplateRequiredError`** hasta que exista un archivo real
  exportado bajo `plant3d/templates/reference/`. El formato de columnas
  de ese Excel nunca se adivina — solo se implementa después de
  inspeccionar un archivo real.

## Procedimiento manual para obtener el catálogo

- [ ] **1. Abrir Catalog Builder** en la instalación de Plant 3D.
- [ ] **2. Create Catalog Template -> Elbow -> Custom Parametric Shape.**
- [ ] **3. Nombrar la forma** `HDPE_SEGMENTED_ELBOW` (mismo nombre que el
      CustomScript registrado — ver `docs/PLANT3D_REGISTRATION_TEST.md`).
- [ ] **4. Exportar la plantilla** con **Export to Excel**.
- [ ] **5. Copiar ese archivo Excel** a
      `plant3d/templates/reference/` en este repositorio (con su nombre
      original, cualquier `.xls`/`.xlsx`).
- [ ] **6. Avisar al desarrollador** (o completar directamente) la
      implementación de `CatalogBuilderExcelExporter.export_to_excel()`
      contra ese archivo real — recién ahí deja de levantar
      `ReferenceTemplateRequiredError`.
- [ ] **7. Verificar en Catalog Builder** que la forma
      `HDPE_SEGMENTED_ELBOW` aparece bajo el grupo `Fitting` y que sus
      parámetros (OD/THK/R/Le/Z) coinciden con el Golden Case
      DN110/PN10/90° (ver `docs/GEOMETRY_VALIDATION_REFERENCE.md`).
- [ ] **8. Registrar el resultado** en
      `plant3d_validation/catalog_result.md`: qué catálogo de prueba se
      usó, si la forma aparece, y cualquier discrepancia dimensional
      encontrada. Mientras ese archivo esté vacío,
      `plant3d/deployment/manifest.py` no avanza a `CATALOG_AVAILABLE`.

## Qué NO hacer

- No escribir un `.pcat` desde Python.
- No adivinar el layout de columnas del Excel de Catalog Builder sin
  tener el archivo real — `catalog_builder_excel_exporter.py` está
  diseñado exactamente para impedir esto (`REFERENCE_TEMPLATE_REQUIRED`).
- No editar `validation_manifest.json` a mano.

## Siguiente paso

Con `catalog_result.md` completo, continuar con
`docs/PLANT3D_SPEC_TEST.md`.
