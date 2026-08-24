# Arquitectura

## Pipeline

```
DATOS               data/raw/*.xlsx  (nunca se edita)
  |                  data/loader.py    (unico modulo que conoce el layout del Excel)
  v
MODELO PARAMETRICO  core/models/  (ElbowParameters, Port, SegmentConfiguration — sin dependencias de UI ni Excel)
  |
  v
VALIDACIONES        core/validation/  (Modo B: reglas geometricas basicas)
                    core/standards/   (alcance normativo DIN 16963)
  |
  v
GEOMETRIA           core/geometry/elbow_geometry.py     (V0.1: arco suave 2D, vista dimensional)
                    core/geometry/segmented_elbow.py    (V0.2: gajos + planos a inglete, 3D real)
                    core/geometry/geometry_validation.py (autochequeo, GEOMETRY_VALIDATION_ERROR)
  |
  v
INTERFAZ            ui/  (Streamlit + Plotly 2D y 3D; solo llama a components/ y a core/geometry, nunca a data/ directamente)
  |
  v
EXPORTADORES        core/serialization/  (JSON intermedio, incluye "segments" cuando hay geometria 3D)
                    core/geometry/tube_mesh.py  (malla numpy para el preview 3D, sin cadquery)
                    cad/backends/  (CadQuery opcional, STEP/STL — experimental, desacoplado de core/)
                    plant3d/  (placeholders, sin API ficticia — etapa futura)
```

`components/elbows/hdpe_segmented_elbow.py` es el unico punto de entrada
que la UI usa para construir un `ElbowParameters`: envuelve al repositorio
(Modo A) y a la validacion (Modo B) para que la UI nunca arme el modelo a
mano.

## Por que Streamlit + Plotly

- **Streamlit**: formularios (selects, number inputs) con muy poco codigo
  de "wiring", y reactivo por defecto (recalcula al cambiar cualquier
  input) — encaja con el requisito de que el preview cambie dinamicamente
  sin que el usuario dispare nada manualmente.
- **Plotly**: la misma libreria sirve para la vista 2D de V0.1
  (`go.Scatter`) y para una futura vista 3D (`go.Scatter3d` / `go.Mesh3d`)
  sin cambiar de stack de visualizacion ni reescribir `ui/plotly_view.py`
  desde cero.

Alternativas consideradas: Tkinter+Matplotlib (mas codigo de empaquetado
de ventana nativa, sin ruta clara a 3D interactivo) y Dash (mas pesado
para una V0.1 de un solo formulario).

## Geometria del codo (core/geometry/elbow_geometry.py)

El codo segmentado se modela como un tramo recto (Le) + un arco circular
(radio R) + otro tramo recto (Le), con el vertice teorico (interseccion de
los dos ejes) en el origen local. La longitud tangente desde el vertice
hasta el arco es `t = R·tan(angulo/2)`, y de ahi sale la identidad
`Z = Le + t` que tambien aparece en el catalogo (ver
`docs/DATA_NOTES.md`). Como el eje 1 se fija siempre en la direccion
180°, el centro del arco tiene una forma cerrada simple
(`C = (-t, R)`) en vez de requerir una solucion trigonometrica general.

Los "segmentos" (uniones de termofusion entre tramos rectos del codo
segmentado) se marcan sobre el arco en las posiciones angulares
acumuladas de `segment_angles_deg`, cuando la fuente los desglosa (ver
nota de ambigüedad para 30° en `docs/DATA_NOTES.md`).

## Geometria 3D real (V0.2 — core/geometry/segmented_elbow.py)

`elbow_geometry.py` sigue intacto: sigue siendo la vista 2D de
validacion dimensional. `segmented_elbow.py` es un modulo nuevo,
independiente, que construye el codo como realmente es fabricado —
tramos rectos cilindricos huecos, cortados a inglete, no un barrido
suave. Detalle matematico completo (sistema de coordenadas, formulas,
generacion de gajos, tolerancias) en
`docs/SEGMENTED_ELBOW_GEOMETRY.md`.

Consumidores, todos independientes entre si:

- `core/geometry/tube_mesh.py`: malla triangulada (numpy puro, sin
  cadquery) para el preview 3D interactivo en Streamlit/Plotly. Esto es
  deliberado: la vista 3D nunca debe depender de una instalacion de
  CadQuery.
- `cad/backends/cadquery_backend.py`: solido B-rep real (OpenCASCADE) solo
  para exportacion STEP/STL experimental. Vive fuera de `core/` para que
  `core/geometry` se pueda importar y testear sin la dependencia pesada.
- `core/geometry/geometry_validation.py`: recalcula varias magnitudes por
  formulas independientes (ley de cosenos para P1-P2, radio tabulado
  contra cada punto de union, suma de angulos de los gajos) y levanta
  `GeometryValidationError` si no coinciden dentro de tolerancia — nunca
  ajusta en silencio.

### Por que CadQuery (y por que no es una dependencia dura)

Se evaluo instalando CadQuery directamente en este entorno: se resuelve
solo via pip (~53s, trae OpenCASCADE/OCP, ~165MB), y construir un tubo
hueco mitrado (dos circulos + extrude + corte booleano con una caja
rotada) toma <15ms. STEP requiere un kernel B-rep real — no hay
alternativa Python liviana seria para ese formato — asi que es la opcion
correcta para exportacion CAD. Pero es una dependencia pesada y opcional
(`requirements-cad.txt`, no `requirements.txt`): si no esta instalada,
`CADQUERY_AVAILABLE=False` y el boton de exportar se deshabilita con un
mensaje claro; el resto de la app (incluida la vista 3D) sigue
funcionando igual.

## Validacion de ingenieria (V0.2.1 — core/geometry/engineering_report.py, core/validation/reference_comparison.py)

`segmented_elbow.py` construye la geometria bajo una hipotesis de
modelado explicita (los puntos de union de los gajos estan inscritos en
el circulo de radio R — ver `docs/GEOMETRY_VALIDATION_REFERENCE.md`).
Que esa geometria cierre matematicamente (Z, radio, angulo) no prueba
que la hipotesis sea correcta, solo que es autoconsistente. V0.2.1 agrega
la capa que permite *comprobarla* contra una referencia externa:

- `core/geometry/engineering_report.py`: lee (nunca modifica) la
  `SegmentedElbowGeometry` ya construida y produce una tabla de
  fabricacion por gajo (longitudes de eje/exterior/interior, coordenadas,
  angulos de los planos de corte) y las dimensiones generales del solido
  — usando formulas independientes de las que construyeron la geometria,
  para que sirvan de chequeo real y no una relectura circular.
- `core/validation/reference_comparison.py`: compara esas dimensiones
  contra medidas de referencia que el usuario ingresa (un codo diseñado
  a mano o fabricado), campo por campo, con tolerancia editable y
  PASS/FAIL. Nunca ajusta la geometria para que coincida. Cada campo
  reprobado se asocia a la hipotesis de modelado especifica de la que
  depende (`FIELD_HYPOTHESIS_NOTES`), para que una desviacion apunte a
  que revisar, no solo a que "algo no coincide".
- `ui/engineering_view.py`: agrega a la vista 3D la circunferencia
  teorica R, los puntos de union y las cotas principales — para que la
  hipotesis se pueda *ver*, no solo confiar en que el numero cierra.

El banner de la UI ("MODELO MATEMATICO — PENDIENTE DE VALIDACION...") es
deliberadamente estatico: una comparacion satisfactoria contra algunos
campos de referencia no cambia automaticamente el estado a "validado" —
eso queda para una decision explicita una vez comparado contra el modelo
de referencia completo.

## Separacion de modos

- **Modo A (Normalizado)**: `data/repository.py` — nunca inventa datos.
  Retorna `AVAILABLE`, `NOT_AVAILABLE` o `INCOMPLETE` mas una lista de
  notas/campos faltantes.
- **Modo B (Personalizado)**: `components/elbows/hdpe_segmented_elbow.py`
  → `build_custom()`. Nunca marca `din16963_compliant=True`. Corre
  `core/validation/elbow_validation.py` (OD>0, espesor>0, OD>2×espesor,
  ID>0, R>0, 0°<angulo<180°, longitudes positivas).
- **Modo C (Ingenieria)**: `core/models/engineering.py` es un placeholder
  documentado (dataclass vacio con TODO); no hay logica ni UI activa en
  V0.1. La pestaña "Modo C" en la UI solo muestra un mensaje informativo.

## Plant 3D (etapa futura)

`plant3d/exporters/base_exporter.py` define solo la interfaz abstracta
(`ComponentExporter.export()`), documentando el pipeline futuro
(`ElbowParameters → CustomScript → PLANTREGISTERCUSTOMSCRIPTS → Catalog →
Spec`) sin implementar ninguna llamada real a Plant 3D. No se debe agregar
ninguna clase/decorador/API de Plant 3D inventada; esa integracion se
construira y validara contra documentacion real en una etapa posterior.
