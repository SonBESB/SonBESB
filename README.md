# Piping Component Generator — V0.1

Generador de componentes parametricos de piping para preparar, en etapas
futuras, su exportacion a AutoCAD Plant 3D. Esta version (V0.1) es una
aplicacion independiente de Plant 3D que cubre un unico componente:
**codo HDPE segmentado PE100 (DIN 16963)**.

## Que hace V0.1

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
- Vista previa geometrica 2D (Plotly) que se actualiza con cada cambio de
  parametros: eje, curva, segmentos, P1 y P2.
- Exportacion a un JSON intermedio (`piping-component-generator/0.1`) con
  los puertos P1/P2 (posicion, direccion, diametros, EndType).

## Instalacion

```bash
pip install -r requirements.txt
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

## Estructura del proyecto

```
piping-component-generator/
    app.py o main.py         # entry point (lanza la UI de Streamlit)
    components/elbows/       # facade de dominio: MODE A/B -> ElbowParameters
    core/
        models/               # ElbowParameters, Port, EndType, SegmentConfiguration
        geometry/             # geometria 2D del codo (vertice, arco, P1/P2)
        validation/           # reglas geometricas del Modo B
        standards/            # alcance normativo DIN 16963
        serialization/        # exportacion a JSON intermedio
    data/
        raw/                  # Excel original, sin modificar
        processed/            # (reservado para snapshots futuros)
        loader.py             # unico modulo que conoce el layout del Excel
        repository.py         # API de consulta (Modo A)
    plant3d/
        exporters/            # interfaz abstracta, sin API ficticia de Plant 3D
        custom_scripts/       # placeholder para la etapa de integracion futura
    ui/                       # Streamlit + Plotly
    tests/
    docs/                     # ARCHITECTURE.md, DATA_NOTES.md
```

Ver `docs/ARCHITECTURE.md` para el detalle del pipeline
(`DATOS → MODELO → VALIDACIONES → GEOMETRIA → INTERFAZ → EXPORTADORES`) y
`docs/DATA_NOTES.md` para como se interpreta el Excel fuente y que datos
son ambiguos o estan incompletos en el catalogo original.

## Fuente de datos

`data/raw/Codos_HDPE_Parametricos_DIN16963.xlsx` no se modifica nunca.
Ningun valor del catalogo esta hardcodeado en el codigo: todo se lee en
tiempo de ejecucion via `data/loader.py`. Para actualizar o ampliar el
catalogo, reemplaza ese archivo (manteniendo los nombres de hoja y
encabezados esperados) o ajusta el loader si cambia el layout.

## Proximos pasos (fuera de alcance de V0.1)

- Modo C (Ingenieria) con edicion avanzada por segmento/puerto.
- Generacion real de CustomScripts Python para AutoCAD Plant 3D
  (`plant3d/`), validada contra documentacion real de Plant 3D — no
  implementada todavia.
- Otros tipos de componente (tees, reductores, flanges, valvulas,
  soportes, bombas).
