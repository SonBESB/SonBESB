# Piping Component Generator — V0.3

Generador de componentes parametricos de piping para preparar, en etapas
futuras, su exportacion a AutoCAD Plant 3D. Esta aplicacion es
independiente de Plant 3D. El unico componente con motor geometrico real
es el **codo HDPE segmentado PE100 (DIN 16963 Parte 1)**, ahora registrado
dentro de una arquitectura general de biblioteca (familias de
componentes, normas, materiales, compatibilidad) preparada para crecer
sin reescribir lo que ya funciona.

**Golden Case principal (V0.2.2+): DN110 / PN10 / 90°** — ver
`docs/COMPONENT_LIBRARY.md`. DN315/PN10/90° (principal hasta V0.2.1) se
mantiene como caso de regresion/escalabilidad.

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
- Exportacion a un JSON intermedio (`piping-component-generator/0.3`) con
  los puertos P1/P2, el desglose de segmentos, y (V0.2.2) la metadata de
  biblioteca: familia/categoria/tipo, norma, material, estado de
  cumplimiento y procedencia documental.
- **Arquitectura de biblioteca** (V0.2.2, `core/library/`,
  `core/compatibility/`, `data_sources/`, `plant3d/publishers/`): registra
  el codo actual como `FITTING/ELBOW/HDPE_SEGMENTED_ELBOW` dentro de una
  taxonomia general (fitting/valve/support/equipment), un registro de
  normas (`DIN`, `ISO`, `ASME`, `EN`, `MSS`, `PROJECT_STANDARD`, `CUSTOM`)
  y materiales (HDPE PE80/PE100, acero al carbono, acero inoxidable,
  grados ASTM) donde registrar un nombre nunca implica tener sus tablas
  cargadas, un motor de compatibilidad que distingue `SUPPORTED` de
  `NOT_AVAILABLE_IN_LIBRARY` (esto ultimo NO significa invalido en
  ingenieria), y contratos abstractos de publicacion a Plant 3D que
  siempre devuelven `PLANT3D_BACKEND_NOT_IMPLEMENTED`. Nada de esto
  modifica el motor geometrico existente. Detalle en
  `docs/COMPONENT_LIBRARY.md`, `docs/STANDARDS_ARCHITECTURE.md`,
  `docs/MATERIALS_ARCHITECTURE.md`, `docs/DATA_PROVENANCE.md` y
  `docs/PLANT3D_PUBLISHING_ARCHITECTURE.md`.
- **Plant 3D CustomScript — Proof of Concept (V0.3, `plant3d/`)**: primera
  integracion real (no un contrato abstracto) con AutoCAD Plant 3D, con la
  regla NO INVENTAR API DE PLANT 3D aplicada estrictamente: cada
  decorador/import del `.py` generado viene de documentacion publica
  citada de Autodesk (ver `docs/PLANT3D_CUSTOMSCRIPT.md`); lo que no pudo
  confirmarse (geometria/puertos reales, codigo de EndType para
  termofusion HDPE) queda como marcador explicito
  `NOT_VERIFIED_AGAINST_REAL_PLANT3D_API` / `REQUIRES_PLANT_CONFIGURATION`,
  nunca inventado. Incluye deteccion de entorno Plant 3D (honesta:
  `NOT DETECTED` en este sandbox Linux, ver `docs/PLANT3D_ENVIRONMENT.md`),
  mapeo P1/P2 (`plant3d/generators/port_mapping.py`), un paquete de
  despliegue completo en `dist/plant3d/HDPE_SEGMENTED_ELBOW/` (script +
  README + golden_case.json + validation_manifest.json), una carpeta de
  evidencia `plant3d_validation/` cuyo estado solo avanza con archivos
  reales no vacios, y una seccion "Plant 3D" en la UI con el boton
  "Generar paquete Plant 3D" (deliberadamente sin ningun boton de
  publicacion automatica). El estado maximo declarado es
  **`PLANT3D_PACKAGE_READY_FOR_VALIDATION`** — nunca `PLANT3D_VALIDATED`
  sin una prueba real en una maquina Windows con Plant 3D instalado (ver
  `docs/PLANT3D_MODEL_ACCEPTANCE.md`).
- **Bombeo — Punto de Operacion** (`core/hydraulics/`, pestaña propia en
  la UI): modulo independiente del codo HDPE, para el caudal de
  equilibrio entre una curva de bomba y una curva de sistema (tramos en
  serie + accesorios). Factor de friccion por Colebrook-White real
  (viscosidad explicita, no agua fija), ajuste de curva por regresion
  (no interpolacion lineal de 3 puntos), leyes de afinidad con
  eficiencia trasladada por punto, y verificacion NPSH disponible vs
  requerido con margen de seguridad. Metodologia, fuentes y
  limitaciones conocidas en `docs/HYDRAULICS_PUMP_OPERATING_POINT.md`.

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
        library/               # V0.2.2: capa de registro/definicion (NO geometria)
            provenance.py          # DataProvenance, SourceType
            standards.py           # StandardDefinition + registro (DIN/ISO/ASME/EN/MSS/...)
            materials.py           # MaterialDefinition + registro (HDPE, aceros, ASTM...)
            component_family.py    # ComponentCategory/Type + registro de familias
            parameter_origin.py    # USER_INPUT | DATABASE_VALUE | RULE_DERIVED | ...
            elbow_registration.py  # envuelve el codo actual en la libreria general
            support_family.py      # SupportFamilyDefinition (placeholder, sin geometria)
        standards/            # alcance normativo DIN 16963 (V0.1, especifico del codo)
        serialization/        # exportacion a JSON intermedio
    core/compatibility/       # V0.2.2: SUPPORTED vs NOT_AVAILABLE_IN_LIBRARY
    data/
        raw/                  # Excel original, sin modificar
        processed/            # (reservado para snapshots futuros)
        loader.py             # unico modulo que conoce el layout del Excel
        repository.py         # API de consulta (Modo A)
    data_sources/             # V0.2.2: metadata de fuentes documentales, sin digitalizar
        hdpe_catalog/
        codelco_support_standard/
        hipogeno_support_standard/
    cad/
        backends/              # CadQuery (opcional) para STEP/STL — desacoplado de core/
    plant3d/
        exporters/            # interfaz abstracta, sin API ficticia de Plant 3D (V0.1)
        custom_scripts/       # placeholder para la etapa de integracion futura
        publishers/            # V0.2.2: CatalogPartPublisher/SupportPublisher/EquipmentPublisher,
                              # siempre PLANT3D_BACKEND_NOT_IMPLEMENTED
        environment/           # V0.3: deteccion/config del entorno Plant 3D (nunca hardcodea 1 ruta)
        generators/            # V0.3: custom_script_generator.py + port_mapping.py (P1/P2)
        deployment/            # V0.3: manifest.py (estado evidenciado) + package_builder.py
        catalog/               # V0.3: payload propio + exportador Excel REFERENCE_TEMPLATE_REQUIRED
        templates/reference/   # V0.3: espera un Excel real exportado por Catalog Builder (vacio hoy)
    plant3d_validation/        # V0.3: evidencia real por etapa (vacia/plantilla hasta prueba manual)
    dist/plant3d/               # V0.3: paquete de despliegue generado para el Golden Case
        HDPE_SEGMENTED_ELBOW/
    core/hydraulics/           # Bombeo: friccion, curva de sistema/bomba, punto de operacion,
                              # afinidad (VDF/gemelas), NPSH, potencia — independiente del codo
    ui/                       # Streamlit + Plotly (2D, 3D, vista de ingenieria, cabecera de libreria,
                              # seccion Plant 3D, pestaña Bombeo)
    tests/
    docs/                     # ver lista completa mas abajo
```

Ver `docs/ARCHITECTURE.md` para el detalle del pipeline
(`DATOS → MODELO → VALIDACIONES → GEOMETRIA → INTERFAZ → EXPORTADORES`),
`docs/DATA_NOTES.md` para como se interpreta el Excel fuente,
`docs/SEGMENTED_ELBOW_GEOMETRY.md` para el detalle matematico del motor 3D
(sistema de coordenadas, formulas, tolerancias),
`docs/GEOMETRY_VALIDATION_REFERENCE.md` para que es dato/ecuacion/hipotesis
de modelado y como usar el comparador contra una referencia fisica/CAD, y
(V0.2.2) `docs/COMPONENT_LIBRARY.md`, `docs/STANDARDS_ARCHITECTURE.md`,
`docs/MATERIALS_ARCHITECTURE.md`, `docs/DATA_PROVENANCE.md` y
`docs/PLANT3D_PUBLISHING_ARCHITECTURE.md` para la arquitectura general de
biblioteca. Para el Proof of Concept de Plant 3D (V0.3): `docs/PLANT3D_CUSTOMSCRIPT.md`
(que esta sourced vs. que es un marcador), `docs/PLANT3D_ENVIRONMENT.md`
(deteccion de entorno), y los cuatro checklists manuales
`docs/PLANT3D_REGISTRATION_TEST.md`, `docs/PLANT3D_CATALOG_WORKFLOW.md`,
`docs/PLANT3D_SPEC_TEST.md` y `docs/PLANT3D_MODEL_ACCEPTANCE.md`.

## Fuente de datos

`data/raw/Codos_HDPE_Parametricos_DIN16963.xlsx` no se modifica nunca.
Ningun valor del catalogo esta hardcodeado en el codigo: todo se lee en
tiempo de ejecucion via `data/loader.py`. Para actualizar o ampliar el
catalogo, reemplaza ese archivo (manteniendo los nombres de hoja y
encabezados esperados) o ajusta el loader si cambia el layout.

## Proximos pasos

- Modo C (Ingenieria) con edicion avanzada por segmento/puerto.
- Probar el paquete `dist/plant3d/HDPE_SEGMENTED_ELBOW/` en una maquina
  Windows real con AutoCAD Plant 3D instalado (ver
  `docs/PLANT3D_REGISTRATION_TEST.md` y los checklists siguientes) —
  hasta entonces el estado sigue en `PLANT3D_PACKAGE_READY_FOR_VALIDATION`.
- Completar la seccion de geometria/puertos del CustomScript con la API
  real de Plant 3D una vez confirmada contra una instalacion real (ver
  `docs/PLANT3D_CUSTOMSCRIPT.md`).
- Otros tipos de componente (tees, reductores, flanges, valvulas,
  soportes, bombas).
