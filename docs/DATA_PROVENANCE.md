# Data Provenance (V0.2.2)

`core/library/provenance.py` define el modelo de trazabilidad documental
que cualquier conjunto de datos registrado en la librería puede declarar.

## Modelo

```python
DataProvenance(
    document,               # p.ej. "Catalogo HDPE 2(1).pdf"
    document_revision=None,
    page=None,
    section=None,            # p.ej. "6.1"
    table=None,               # p.ej. "6.1.1"
    standard_reference=None,  # p.ej. "DIN 16963 Part 1"
    source_type=SourceType.MANUFACTURER_CATALOG,
    notes=None,
)
```

`SourceType` distingue: `MANUFACTURER_CATALOG`, `STANDARD_DOCUMENT`,
`PROJECT_DRAWING`, `INTERNAL_CALCULATION`, `USER_PROVIDED`.

## Procedencia del codo HDPE segmentado (Modo Normalizado)

```text
document:           Catalogo HDPE 2(1).pdf
section:             6.1
table:                6.1.1
standard_reference:  DIN 16963 Part 1
source_type:         MANUFACTURER_CATALOG
```

Definida como constante `HDPE_CATALOG_ELBOW_PROVENANCE` en
`core/library/elbow_registration.py`, y adjuntada automáticamente por
`register_hdpe_segmented_elbow()` a cualquier codo en Modo Normalizado.
En Modo Personalizado, `provenance` es `None` — no hay a qué documento
atribuir una geometría inventada por el usuario.

No es visible en la UI todo el tiempo (queda en el JSON exportado y,
opcionalmente, en secciones de trazabilidad), tal como se pidió.

## Relación con `docs/DATA_NOTES.md`

`docs/DATA_NOTES.md` (V0.1) ya documentaba cómo se interpretó el Excel
derivado del catálogo. Esta capa de provenance no reemplaza esa
documentación — la referencia (`notes` de
`HDPE_CATALOG_ELBOW_PROVENANCE` apunta explícitamente a
`docs/DATA_NOTES.md`) y le da una forma estructurada, consultable desde
código y serializable a JSON.

## Estado epistémico de la relación Z = Le + R·tan(ángulo/2)

Esta fórmula (`core/geometry/elbow_geometry.py::calculate_z_mm`) fue
descubierta comparando la hoja `BUSCADOR` contra `BD_Codos` del Excel, y
se verificó que se cumple exactamente en las 84 combinaciones DN×ángulo
disponibles (ver `docs/DATA_NOTES.md` y
`tests/test_geometry.py::test_calculate_z_matches_catalog_value`).

Se etiqueta explícitamente como:

```text
GEOMETRIC_RELATION_VERIFIED_AGAINST_SOURCE_DATA
```

(constante en `core/geometry/elbow_geometry.py`, incluida en el JSON como
`geometric_relation_status` cuando hay geometría 3D disponible) — **no**
como una fórmula citada directamente de DIN 16963. La distinción importa:
"verificada contra los datos fuente" es una afirmación que este proyecto
puede sostener con evidencia propia (los tests); "cita textual de la
norma" requeriría haber leído el documento DIN 16963 mismo, lo cual no ha
ocurrido.

## Documentos de referencia registrados, no digitalizados

`data_sources/registry.py` registra tres fuentes documentales:

| Fuente | Tipo | Estado |
|---|---|---|
| `hdpe_catalog` (Catalogo HDPE 2(1).pdf) | MANUFACTURER_CATALOG | `PARTIALLY_DIGITIZED` — solo la seccion 6.1 esta en uso |
| `codelco_support_standard` (Soportes Cañerías Codelco 1.pdf) | SUPPORT_STANDARD | `REGISTERED_NOT_DIGITIZED` |
| `hipogeno_support_standard` (2111-1CD-6-057_R1 3.pdf) | SUPPORT_STANDARD | `REGISTERED_NOT_DIGITIZED` |

Registrar estos documentos dejó la arquitectura preparada para que,
cuando se digitalicen sus tablas de soportes, tengan un lugar natural
donde vivir (`core/library/support_family.py`) y una forma de declarar de
dónde salió cada dato (`DataProvenance`) — sin haber transcrito una sola
tabla de soportes todavía.
