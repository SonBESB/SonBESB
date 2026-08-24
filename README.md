# Piping Component Generator — V0.2.1

Generador de componentes parametricos de piping para preparar, en etapas
futuras, su exportacion a AutoCAD Plant 3D. Esta aplicacion es
independiente de Plant 3D y cubre por ahora un unico componente:
**codo HDPE segmentado PE100 (DIN 16963)**.

## Que hace

- **Modo A — Normalizado**: elige DN, PN y angulo (30°/45°/60°/90°); la
  app busca los parametros reales en el catalogo (`data/raw/*.xlsx`) y
  muestra si la combinacion esta `DISPONIBLE`, `NO DISPONIBLE` o con
  informacion `INCOMPLETA`. Nunca inventa un valor faltante.
- **Modo B — Personalizado**: se ingresan las dimensiones a mano (OD,
  espesor, angulo, radio, Le, Z opcional). Se marca explicitamente como
  `COMPONENTE PERSONALIZADO` (nunca declarado conforme a DIN 16963) y se
  valida geometricamente (OD>0, OD>2×espesor, angulo entre 0°-180°, etc.).
- **Modo C — Ingenieria**: reservado para una version futura; solo hay un
  placeholder de arquitectura (`core/models/engineering.py`), sin logica.
- Vista previa 2D (Plotly, sin cambios desde V0.1) para validacion
  dimensional rapida.
- **Vista previa 3D interactiva** (V0.2): motor geometrico real de codo
  *segmentado* (gajos + tramos rectos, cortados a inglete) — no un barrido
  suave. Rotar/zoom, mostrar/ocultar centerline, puertos, planos de union
  y numeros de gajo. Cuando la fuente no desglosa los segmentos (30° en
  el Excel entregado), se muestra un vacio real en vez de inventar gajos.
- **`GEOMETRY_VALIDATION_ERROR`**: cada geometria se autochequea contra
  formulas independientes (ley de cosenos, radio tabulado, suma de
  segmentos) antes de mostrarse o exportarse; una discrepancia nunca se
  ajusta en silencio.
- Exportacion CAD experimental a **STEP/STL** (CadQuery/OpenCASCADE), solo
  para validar la geometria — no es el mecanismo de integracion con
  Plant 3D.
- **Validacion de ingenieria** (V0.2.1): la geometria de gajos es una
  HIPOTESIS DE MODELADO, no un hecho confirmado. Esta seccion agrega una
  vista de ingenieria (circunferencia teorica R, puntos de union, planos
  de corte, cotas), una tabla de fabricacion detallada por gajo, las
  dimensiones generales del solido, y un comparador **MODELO PARAMETRICO
  vs MODELO DE REFERENCIA** (medidas reales que el usuario ingresa, con
  tolerancias editables ±1/±2/±5 mm, PASS/FAIL y diferencia %) que nunca
  ajusta la geometria automaticamente. Detalle completo en
  `docs/GEOMETRY_VALIDATION_REFERENCE.md`.
- Exportacion a un JSON intermedio (`piping-component-generator/0.2`) con
  los puertos P1/P2 y, cuando hay geometria 3D disponible, el desglose de
  segmentos (`segments`) y los tramos rectos (`leg1_stub`/`leg2_stub`).

## Instalacion

```bash
pip install -r requirements.txt
# opcional, para exportar STEP/STL (dependencia pesada, ~165MB):
pip install -r requirements-cad.txt
```

## Ejecutar la aplicacion

```bash
python main.py
# equivalente a: streamlit run ui/app_streamlit.py
```

## Ejecutar los tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

Los tests del backend CadQuery (`tests/test_cadquery_backend.py`) se
saltan automaticamente si `cadquery` no esta instalado.

## Estructura del proyecto

```
piping-component-generator/
    app.py o main.py         # entry point (lanza la UI de Streamlit)
    components/elbows/       # facade de dominio: MODE A/B -> ElbowParameters
    core/
        models/               # ElbowParameters, Port, EndType, SegmentConfiguration
        geometry/
            elbow_geometry.py     # V0.1: arco suave 2D (vista dimensional)
            segmented_elbow.py    # V0.2: motor 3D real (gajos + planos a inglete)
            geometry_validation.py # GEOMETRY_VALIDATION_ERROR (autochequeo)
            tube_mesh.py           # malla triangulada numpy (preview 3D, sin cadquery)
            engineering_report.py  # V0.2.1: tabla de fabricacion + dimensiones generales
        validation/
            elbow_validation.py    # reglas geometricas del Modo B
            reference_comparison.py # V0.2.1: MODELO PARAMETRICO vs MODELO DE REFERENCIA
        standards/            # alcance normativo DIN 16963
        serialization/        # exportacion a JSON intermedio
    data/
        raw/                  # Excel original, sin modificar
        processed/            # (reservado para snapshots futuros)
        loader.py             # unico modulo que conoce el layout del Excel
        repository.py         # API de consulta (Modo A)
    cad/
        backends/              # CadQuery (opcional) para STEP/STL — desacoplado de core/
    plant3d/
        exporters/            # interfaz abstracta, sin API ficticia de Plant 3D
        custom_scripts/       # placeholder para la etapa de integracion futura
    ui/                       # Streamlit + Plotly (2D, 3D y vista de ingenieria)
    tests/
    docs/                     # ARCHITECTURE.md, DATA_NOTES.md, SEGMENTED_ELBOW_GEOMETRY.md,
                              # GEOMETRY_VALIDATION_REFERENCE.md
```

Ver `docs/ARCHITECTURE.md` para el detalle del pipeline
(`DATOS → MODELO → VALIDACIONES → GEOMETRIA → INTERFAZ → EXPORTADORES`),
`docs/DATA_NOTES.md` para como se interpreta el Excel fuente,
`docs/SEGMENTED_ELBOW_GEOMETRY.md` para el detalle matematico del motor 3D
(sistema de coordenadas, formulas, tolerancias), y
`docs/GEOMETRY_VALIDATION_REFERENCE.md` para que es dato/ecuacion/hipotesis
de modelado y como usar el comparador contra una referencia fisica/CAD.

## Fuente de datos

`data/raw/Codos_HDPE_Parametricos_DIN16963.xlsx` no se modifica nunca.
Ningun valor del catalogo esta hardcodeado en el codigo: todo se lee en
tiempo de ejecucion via `data/loader.py`. Para actualizar o ampliar el
catalogo, reemplaza ese archivo (manteniendo los nombres de hoja y
encabezados esperados) o ajusta el loader si cambia el layout.

## Proximos pasos

- Modo C (Ingenieria) con edicion avanzada por segmento/puerto.
- Generacion real de CustomScripts Python para AutoCAD Plant 3D
  (`plant3d/`), validada contra documentacion real de Plant 3D — no
  implementada todavia.
- Otros tipos de componente (tees, reductores, flanges, valvulas,
  soportes, bombas).
