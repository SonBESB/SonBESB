# Plant 3D Environment Detection (V0.3)

`plant3d/environment/detector.py` resuelve, de forma honesta, si hay una
instalación de AutoCAD Plant 3D disponible y dónde están sus carpetas
relevantes. **Nunca asume presencia** — en cualquier plataforma que no
sea Windows (que incluye todo el desarrollo de este proyecto hasta ahora)
la respuesta es siempre `detected=False`.

## Por qué el entorno de desarrollo no tiene Plant 3D

`uname -a` en este entorno reporta Linux x86_64. AutoCAD Plant 3D es
exclusivamente Windows — no existe una versión Linux ni una forma de
instalarlo aquí. Por eso todo lo generado por `plant3d/` en este proyecto
es, como máximo, `PLANT3D_PACKAGE_READY_FOR_VALIDATION`: listo para que
un humano lo pruebe en una máquina Windows real con Plant 3D instalado,
nunca `PLANT3D_VALIDATED` por sí solo.

## Regla: ninguna ruta hardcodeada como si fuera LA ruta

`C:\AutoCAD Plant 3D 2026 Content` (o cualquier año específico) nunca se
trata como la ruta real — es solo **uno entre varios candidatos**
generados a partir de un rango de versiones, exactamente igual que
cualquier otro año en `_CANDIDATE_VERSIONS`. La detección real solo puede
confirmar un candidato comprobando si el directorio existe (en Windows) o
leyendo una configuración manual explícita.

## Dos formas de resolver el entorno

### 1. Archivo de configuración manual (`plant3d_config.yaml`)

La forma recomendada en una máquina real. Copiar
`plant3d_config.example.yaml` (en la raíz del repo) a
`plant3d_config.yaml` y completar los campos bajo `plant3d:`:

```yaml
plant3d:
  version: "2024"
  shared_content: "C:\\AutoCAD Plant 3D 2024 Content"
  # opcionales — si se omiten, se derivan de shared_content:
  # custom_scripts: "C:\\AutoCAD Plant 3D 2024 Content\\CPak Common\\CustomScripts"
  # catalogs: "C:\\AutoCAD Plant 3D 2024 Content\\Catalogs"
  # specs: "C:\\AutoCAD Plant 3D 2024 Content\\Specs"
  # sdk: "C:\\AutoCAD Plant 3D 2024 Content\\SDK"
```

`plant3d_config.yaml` está en `.gitignore` (es específico de cada máquina);
solo `plant3d_config.example.yaml` se versiona. Si el archivo existe y
tiene `shared_content`, `detect_plant3d_environment()` lo usa siempre
primero — nunca compite con el sondeo automático.

### 2. Sondeo automático por sistema de archivos (solo Windows)

Si no hay configuración manual, y el sistema operativo es Windows, el
detector prueba una lista de candidatos generados por:

```python
_CANDIDATE_VERSIONS = ["2022", "2023", "2024", "2025", "2026", "2027"]
_CANDIDATE_DRIVE_ROOTS = [r"C:\\", r"D:\\"]
```

es decir `C:\AutoCAD Plant 3D 2022 Content` ... `D:\AutoCAD Plant 3D 2027
Content` (12 candidatos), comprobando `Path(candidate).is_dir()` uno por
uno y quedándose con el primero que exista. En cualquier plataforma
distinta de Windows este bloque nunca se ejecuta — la función retorna
`detected=False, source="NOT_DETECTED"` con la lista completa de
candidatos en `candidates_checked` (para que quede trazable qué se
intentó, aunque nada haya sido encontrado).

## Versiones documentadas vs. versión detectada

```python
KNOWN_DOCUMENTED_VERSIONS = ["2019", "2022", "2023", "2024", "2025"]
```

Esta lista viene de las versiones para las que la investigación de V0.3
encontró una página de ayuda pública de Autodesk sobre
`PLANTREGISTERCUSTOMSCRIPTS`. `PlantEnvironmentInfo.version_documented`
indica si la versión detectada/configurada está en esa lista — **no**
significa que una versión fuera de la lista sea inválida, solo que esta
investigación no encontró una fuente citable para ella. Una versión no
documentada (ej. `"2018"` o `"2028"`) se reporta con
`version_documented=False`, nunca se trata en silencio como soportada.

## Derivación de subrutas — bug corregido

`_derive_subpaths()` construye `custom_scripts_path` / `catalog_path` /
`specs_path` / `sdk_path` a partir de `shared_content_path` usando
**concatenación de strings pura**, nunca `pathlib.Path`. La primera
versión usaba `pathlib.Path`, lo cual en un host Linux/macOS (como este
entorno de desarrollo) mezclaba separadores `/` de POSIX con los `\` de
Windows, produciendo rutas inválidas como
`C:\AutoCAD Plant 3D 2026 Content/Catalogs`. Como estas rutas son
siempre de Windows (Plant 3D no corre en otro sistema) independientemente
de en qué SO se ejecute este código, la corrección usa solo `str` y
`\\` explícito. Cubierto por
`tests/test_plant3d_environment.py::test_derived_subpaths_use_only_windows_separators`.

## `PlantEnvironmentInfo` — campos

```python
@dataclass(frozen=True)
class PlantEnvironmentInfo:
    detected: bool
    source: str  # "CONFIG_FILE" | "AUTO_DETECTED_CANDIDATE" | "NOT_DETECTED"
    version: Optional[str]
    version_documented: Optional[bool]
    shared_content_path: Optional[str]
    custom_scripts_path: Optional[str]
    catalog_path: Optional[str]
    specs_path: Optional[str]
    sdk_path: Optional[str]
    platform_name: str
    candidates_checked: List[str]
```

Usado por la sección "Plant 3D" de la UI de Streamlit
(`ui/app_streamlit.py::render_plant3d_section`) para mostrar
`DETECTED`/`NOT DETECTED` y por
`plant3d/deployment/package_builder.py` indirectamente (a través del
README generado, que le indica al usuario cómo obtener estas rutas en su
propia máquina).
