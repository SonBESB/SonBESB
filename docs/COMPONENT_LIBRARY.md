# Component Library (V0.2.2)

Este documento describe la capa de registro/definición agregada en
V0.2.2 (`core/library/`) — **no** un rediseño del motor geométrico. El
codo HDPE segmentado sigue siendo exactamente el mismo código de
V0.1/V0.2/V0.2.1 (`core/models/elbow.py`, `core/geometry/`,
`components/elbows/hdpe_segmented_elbow.py`); esta capa solo lo *envuelve*
con metadata para que pueda convivir en un catálogo más amplio.

## Taxonomía general

```
COMPONENT
  |- FITTING
  |    |- ELBOW      <- unica familia implementada: HDPE_SEGMENTED_ELBOW
  |    |- TEE        (registrada, sin motor geometrico)
  |    |- REDUCER    (registrada, sin motor geometrico)
  |    `- FLANGE     (registrada, sin motor geometrico)
  |- VALVE           (registrada, sin motor geometrico)
  |- SUPPORT         (registrada, ver core/library/support_family.py)
  `- EQUIPMENT       (registrada, sin motor geometrico)
```

`core/library/component_family.py` define `ComponentCategory`,
`ComponentType` y el registro `COMPONENT_FAMILIES`. Cada entrada tiene un
flag `implemented: bool` — hoy solo `HDPE_SEGMENTED_ELBOW` es `True`. Las
demás existen como nombres reservados en la arquitectura, no como
funcionalidad real.

## El codo actual, registrado

```text
Category: FITTING
Type:     ELBOW
Family:   HDPE_SEGMENTED_ELBOW
Material: PE100
Standard: DIN16963_PART1
```

## Cómo se envuelve el codo (sin reescribir su geometría)

`core/library/elbow_registration.py` expone una única función:

```python
def register_hdpe_segmented_elbow(
    params: ElbowParameters,               # ya construido, sin tocar
    geometry: SegmentedElbowGeometry | None,  # ya construido, sin tocar
) -> ComponentRegistration
```

Esta función **solo lee** los dos objetos que recibe. No llama a
`data/repository.py`, no reconstruye geometría, no valida dimensiones —
esas responsabilidades siguen exactamente donde estaban. Devuelve:

```python
ComponentRegistration(
    family,                        # ComponentFamilyDefinition
    material,                      # MaterialDefinition
    standard,                      # StandardDefinition
    compliance_status,             # SOURCE_DATA | OUT_OF_STANDARD_SCOPE | NOT_CERTIFIED
    segment_decomposition_status,  # SEGMENT_DECOMPOSITION_DEFINED | _NOT_DEFINED
    provenance,                    # DataProvenance | None
)
```

`ui/app_streamlit.py` llama a esta función una vez por render y usa el
resultado tanto para la cabecera visual como para el JSON — nunca
construye esta metadata "a mano" en dos lugares distintos.

## Origen de cada parámetro (ParameterOrigin)

`core/library/parameter_origin.py` define un enum de cinco valores
(`USER_INPUT`, `DATABASE_VALUE`, `RULE_DERIVED`, `GEOMETRY_DERIVED`,
`SOURCE_DOCUMENT`). Para el codo actual (documentación, no forzado en
código todavía):

| Parametro | Origen |
|---|---|
| DN / PN / angulo (Modo A) | USER_INPUT (seleccion) |
| OD, espesor, ID, R, Le, Z (Modo A) | DATABASE_VALUE |
| Z (Modo B, sin definir manual) | RULE_DERIVED |
| Coordenadas de gajos y planos de corte | GEOMETRY_DERIVED |
| Texto "Configuracion" | SOURCE_DOCUMENT |

Esto será mucho más relevante para soportes (ver
`core/library/support_family.py`), donde un mismo soporte mezcla varias
de estas fuentes en el mismo objeto.

## Motor de compatibilidad

`core/compatibility/engine.py::check_compatibility(family, standard,
material)` responde `SUPPORTED`, `NOT_AVAILABLE_IN_LIBRARY` o
`UNKNOWN_KEY`. Solo una combinación está en `SUPPORTED_COMBINATIONS` hoy:
`(HDPE_SEGMENTED_ELBOW, DIN_16963_1, PE100)`. Ver
`docs/STANDARDS_ARCHITECTURE.md` para la distinción importante entre
"no disponible en esta libreria" y "inválido en ingeniería".

## Qué NO hace esta etapa

- No implementa geometría de tees, reductores, flanges, válvulas,
  soportes ni equipos — solo los nombra.
- No carga propiedades mecánicas de ningún material nuevo.
- No integra AutoCAD Plant 3D (ver `docs/PLANT3D_PUBLISHING_ARCHITECTURE.md`).
