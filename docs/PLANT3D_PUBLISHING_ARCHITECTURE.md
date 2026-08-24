# Plant 3D Publishing Architecture (V0.2.2)

**Estado: contratos abstractos únicamente. Ninguna integración real con
AutoCAD Plant 3D existe todavía.** Este documento describe la forma que
esa integración tendrá, no su implementación.

## Qué existe hoy

`plant3d/publishers/`:

```text
base.py           PublishResult, PublishResultStatus.NOT_IMPLEMENTED,
                   ComponentPublisher (ABC), not_implemented_result()
catalog_part.py    CatalogPartPublisher(ComponentPublisher)
support.py         SupportPublisher(ComponentPublisher)
equipment.py        EquipmentPublisher(ComponentPublisher)
```

Cada `publish()` concreto devuelve, siempre:

```python
PublishResult(status=PublishResultStatus.NOT_IMPLEMENTED,
              message="Publicacion a AutoCAD Plant 3D para '<tipo>' no "
                      "esta implementada todavia (etapa V0.3+)...")
```

Ningún archivo `.pcat`, `.pspx` o `.pspc` es leído, escrito ni inventado.
Ninguna clase, decorador o función de la API de Autodesk/Plant 3D
aparece en este código — ni real ni ficticia.

`plant3d/exporters/base_exporter.py` (de V0.1) sigue existiendo,
igualmente sin implementar; `publishers/` es el contrato más amplio que
cubre catálogo, soportes y equipos, no solo la exportación de geometría.

## Pipeline futuro — componentes de catálogo

```text
HDPE_SEGMENTED_ELBOW (ComponentRegistration + geometria)
        |
        v
CatalogPartPublisher.publish()
        |
        v
Plant 3D CustomScript (.py)
        |
        v
PLANTREGISTERCUSTOMSCRIPTS
        |
        v
Catalog
        |
        v
Spec
        |
        v
AutoCAD Plant 3D
```

## Pipeline futuro — soportes

```text
SupportFamilyDefinition (core/library/support_family.py, hoy vacio)
        |
        v
SupportPublisher.publish()
        |
        v
Plant 3D Support Catalog
        |
        v
PipeSupportsSpec
        |
        v
AutoCAD Plant 3D
```

## Qué se necesita antes de implementar cualquiera de los dos pipelines

1. Documentación real de Plant 3D CustomScripts (formato, decoradores,
   registro) — nada se inventará sin ella.
2. Geometría de al menos una familia de soporte real (hoy
   `SUPPORT_FAMILIES` está vacío — ver `docs/DATA_PROVENANCE.md`).
3. Validación explícita del usuario de que el Golden Case actual
   (DN110/PN10/90°) está listo para pasar a esta etapa — ver
   `docs/GEOMETRY_VALIDATION_REFERENCE.md`, sección de estado del modelo.

Hasta entonces, cualquier llamado a `publish()` en este proyecto devuelve
`PLANT3D_BACKEND_NOT_IMPLEMENTED` y no produce ningún efecto secundario.
