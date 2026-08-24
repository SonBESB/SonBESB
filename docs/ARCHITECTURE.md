# Arquitectura — V0.1

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
GEOMETRIA           core/geometry/  (puntos 2D: vertice, arco, P1/P2, cuerpo del codo)
  |
  v
INTERFAZ            ui/  (Streamlit + Plotly; solo llama a components/, nunca a data/ o a core/geometry directamente para construir el modelo)
  |
  v
EXPORTADORES        core/serialization/  (JSON intermedio)
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
