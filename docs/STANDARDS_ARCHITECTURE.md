# Standards Architecture (V0.2.2)

`core/library/standards.py` registra normas de ingeniería como
**nombres conocidos**, no como tablas cargadas. Registrar una norma nunca
significa inventar su contenido.

## Modelo

```python
StandardDefinition(
    organization,          # DIN | ISO | ASME | EN | MSS | PROJECT_STANDARD | CUSTOM
    code,                  # p.ej. "16963", "B16.9"
    part,                  # p.ej. "1"
    edition,
    title,
    component_categories,  # que categorias de COMPONENT cubre (informativo)
    source_reference,
    data_status,
)
```

## Estados de datos

| Estado | Significa |
|---|---|
| `VERIFIED_DATA` | Datos comprobados contra el texto oficial de la norma. **Ninguna entrada tiene este estado hoy.** |
| `SOURCE_DATA` | Hay datos utilizables, provenientes de una fuente secundaria confiable (catálogo de fabricante), no verificados contra el texto oficial. |
| `REFERENCE_ONLY` | La norma es citada por otra fuente pero no aporta datos propios usados en la app. |
| `DATA_NOT_LOADED` | La norma existe en el registro; cero datos cargados. |
| `PROJECT_STANDARD` | Norma o especificación propia de un proyecto, no de un organismo. |
| `CUSTOM` | Sin norma declarada (Modo Personalizado). |

## Registro actual

| Clave | Organización + código | Estado |
|---|---|---|
| `DIN_16963_1` | DIN 16963 Parte 1 | `SOURCE_DATA` — el único con datos reales, provenientes del catálogo HDPE (ver `docs/DATA_PROVENANCE.md`) |
| `ASME_B16_9` | ASME B16.9 | `DATA_NOT_LOADED` |
| `ISO_4427` | ISO 4427 | `REFERENCE_ONLY` — citada en el Excel origen como norma de tubería, no de fitting |
| `MSS_SP_58` | MSS SP-58 | `DATA_NOT_LOADED` |
| `PROJECT_STANDARD` | — | `PROJECT_STANDARD` |
| `CUSTOM` | — | `CUSTOM` |

**`DIN_16963_1` está en `SOURCE_DATA`, no en `VERIFIED_DATA`**, porque los
valores usados (R, Le, Z, espesores) provienen del catálogo del
fabricante, no de una lectura directa del texto de la norma DIN 16963.
Ver `docs/GEOMETRY_VALIDATION_REFERENCE.md` para el detalle de qué es
dato, qué es ecuación y qué es hipótesis de modelado dentro de esos
datos.

## Por qué registrar ASME B16.9 sin datos es útil

Permite que `core/compatibility/engine.py` responda algo específico y
correcto — `NOT_AVAILABLE_IN_LIBRARY` — en vez de fallar con un error de
clave desconocida (`UNKNOWN_KEY`) cuando alguien pregunte por una
combinación real que simplemente no hemos cargado todavía. Es la
diferencia entre "no sabemos qué es eso" y "sabemos qué es, no tenemos
datos".

## No confundir "no disponible" con "inválido"

`core/compatibility/engine.py` distingue explícitamente:

- `NOT_AVAILABLE_IN_LIBRARY`: esta librería no tiene datos/geometría para
  esa combinación. No dice nada sobre si la combinación es válida en la
  realidad.
- `engineering_invalid` (campo del resultado, siempre `False` hoy): se
  reserva para combinaciones que la propia ingeniería rechazaría (p.ej.
  un material incompatible con un rango de presión). Ninguna combinación
  está marcada así todavía — no se ha cargado el conocimiento de
  ingeniería necesario para afirmar eso de manera responsable.
