# Materials Architecture (V0.2.2)

`core/library/materials.py` registra materiales independientemente de
cualquier componente. Registrar un material no significa tener sus
propiedades mecánicas — cada propiedad numérica es `Optional` y queda en
`None` salvo que exista un valor realmente cargado y con fuente.

## Modelo

```python
MaterialDefinition(
    family,                # HDPE | CARBON_STEEL | STAINLESS_STEEL | CUSTOM
    specification=None,    # p.ej. "ASTM A106"
    grade=None,            # p.ej. "PE100", "Gr.B", "TP304L"
    density_kg_m3=None,
    yield_strength_mpa=None,
    temperature_limits_c=None,
    notes=None,
)
```

## Registro actual

| Clave | Familia | Especificacion / Grado | Propiedades cargadas |
|---|---|---|---|
| `PE80` | HDPE | PE80 | Ninguna |
| `PE100` | HDPE | PE100 | Ninguna — es el material del Golden Case actual, pero sin datos mecánicos |
| `CARBON_STEEL` | CARBON_STEEL | — | Ninguna |
| `STAINLESS_STEEL` | STAINLESS_STEEL | — | Ninguna |
| `ASTM_A36` | CARBON_STEEL | ASTM A36 | Ninguna |
| `ASTM_A106_GR_B` | CARBON_STEEL | ASTM A106 / Gr.B | Ninguna |
| `ASTM_A312_TP304L` | STAINLESS_STEEL | ASTM A312 / TP304L | Ninguna |
| `ASTM_A312_TP316L` | STAINLESS_STEEL | ASTM A312 / TP316L | Ninguna |
| `CUSTOM` | CUSTOM | — | Ninguna (Modo Personalizado) |

Ningún material tiene `density_kg_m3`, `yield_strength_mpa` ni
`temperature_limits_c` cargados todavía. Esto es intencional: el
propósito de esta etapa es reservar las claves y la forma del dato, no
adivinar valores de catálogo que no hemos verificado.

## Por qué PE100 no tiene propiedades aunque sea el material "en uso"

El motor geométrico del codo (V0.1-V0.2.1) nunca necesitó propiedades
mecánicas — solo dimensiones (OD, espesor, radio, etc.), que vienen del
catálogo HDPE, no de una ficha de propiedades de material. Cuando el
proyecto necesite cálculos que sí dependan de propiedades (p.ej.
espesores mínimos por presión, soportes con cargas), esos valores se
cargarán con su propia trazabilidad (`core/library/provenance.py`) antes
de completarse aquí — nunca antes.

## Extensión futura

Añadir un material nuevo es agregar una entrada a `MATERIALS_REGISTRY`
con la especificación/grado correctos y las propiedades que realmente se
tengan — el resto de la arquitectura (compatibilidad, JSON, UI) ya sabe
leer un material con campos `None`.
