# Pórticos 2D — esfuerzos, deformaciones, von Mises, N/V/M

Herramienta web standalone (HTML/JS, sin backend) para analizar pórticos y
vigas planos dibujados libremente por el usuario: coloca nodos y barras,
asigna apoyos, materiales, secciones y cargas, y obtiene reacciones,
diagramas de axial/corte/momento, deformada y un mapa de tensión de von
Mises a lo largo de cada barra.

Este módulo es **independiente** del generador de codos HDPE del resto de
`SonBESB` (`components/`, `core/`, `plant3d/`): no comparte código ni
dominio de ingeniería con esos módulos (ver `core/models/engineering.py`,
que es un placeholder para edición de segmentos del codo, no para esto).

## Cómo correr

No requiere instalación ni build. Es un sitio estático:

```bash
cd structural
python3 -m http.server 8000
# abrir http://localhost:8000/index.html
```

(Abrir `index.html` directamente con `file://` también funciona en la
mayoría de los navegadores, ya que no usa ES modules ni fetch a otros
archivos; un servidor estático es solo la forma más portable de probarlo.)

## Cómo usar

1. **Perfil activo** (panel derecho, arriba): elige material (E, con
   presets de acero/hormigón/aluminio o un valor personalizado) y sección
   (rectangular, circular sólida, o **catálogo de perfiles** — ver abajo)
   *antes* de dibujar. Cada barra nueva se crea con este perfil; las ya
   creadas no cambian si luego lo editas.
2. **+ Nodo**: click en el lienzo para colocar nodos (con snap a grilla de
   0.5 m, desactivable).
3. **+ Barra**: click en un nodo existente y luego en otro para conectar
   una barra entre ambos con el perfil activo.
4. **Seleccionar**: click en un nodo o barra para editar sus propiedades
   en el panel derecho:
   - Nodo: tipo de apoyo (Libre / Articulado / Rodillo / Empotrado) y
     carga puntual (Fx, Fy en kN; momento en kN·m).
   - Barra: material (E, con presets de acero/hormigón/aluminio o un valor
     personalizado), sección (rectangular, circular sólida, o manual
     A/I/c) y carga distribuida uniforme (kN/m).
5. **Borrar**: click en un nodo o barra para eliminarlo (borrar un nodo
   borra también las barras y cargas conectadas a él).
6. **Calcular**: resuelve el modelo y muestra reacciones, máximos por
   barra, y la tensión de von Mises máxima global con su ubicación.
7. Panel "Mostrar": activa/desactiva los diagramas de M(x), V(x), N(x), la
   deformada (escala automática) y el mapa de von Mises sobre cada barra.
8. "Verificación (opcional)": ingresa una tensión admisible/fluencia (MPa)
   para obtener un factor de seguridad PASA/NO PASA contra el von Mises
   máximo.

Rueda del mouse = zoom centrado en el cursor. "Ajustar vista" reencuadra
la vista a los nodos actuales (la vista no se reajusta sola en cada clic,
para que no "salte" mientras se dibuja).

## Catálogo de perfiles

En el tipo de sección de una barra, además de Rectangular/Circular/Manual
hay una opción **Catálogo de perfiles**: elige una familia (IN, HN, IP,
PH, T, CA, C) y un perfil, y se autocompletan A, I y c (fibra extrema)
reales — con la opción de usar el eje fuerte (x-x, por defecto) o el
débil (y-y) del perfil, según cómo lo vayas a orientar.

**Origen de los datos** (`data/catalog_icha.json`, 429 perfiles): extraídos
y verificados desde un archivo ICHA real que subió el usuario del proyecto
(`Serie IN/HN/IP/PH/T/CA/C (Diseño)`), **no inventados**. Cada fila pasó
dos chequeos de consistencia física antes de incluirse: fibra extrema
c=I/W contra la geometría publicada, y Área×densidad del acero (7850 kg/m³)
contra el peso por metro catalogado. De 442 filas originales, **12 se
excluyeron** por errores de transcripción reales detectados en el archivo
fuente (ver `data/catalog_icha_excluidos.json` para la lista, con el motivo
de cada exclusión, por si quieres revisarlas contra tu copia impresa).

La constante de torsión J para estos perfiles (soldados/plegados, secciones
abiertas) **no viene en el catálogo ICHA** — se calcula aquí con la
aproximación estándar de Saint-Venant para secciones de pared delgada
(J≈Σbᵢtᵢ³/3), no es un valor de catálogo.

**CINTAC no está incluido.** El archivo CINTAC que se subió es una
biblioteca de *dimensiones* para Autodesk Inventor (perfiles conformados
en frío: costaneras, tubos, cajones, etc.) — no trae A, I ni W calculados,
solo geometría. Incorporarlo requeriría calcular las propiedades de
sección desde cero para ~13 familias de perfiles distintas (fórmulas de
pared delgada por familia), que no se hizo en esta pasada.

Si abres `index.html` directamente con `file://`, el catálogo no cargará
(los navegadores bloquean `fetch()` de JSON local sin servidor) — corre
un servidor local como se indica arriba.

## Memoria de cálculo

Tras "Calcular", el botón "Memoria de cálculo" abre una vista imprimible
con: datos de proyecto (editables: nombre, autor, notas), descripción del
modelo (nodos, barras con su sección/material, cargas), un resumen breve
de la metodología, resultados (reacciones, máximos por barra con sus
diagramas M(x)/V(x), von Mises máximo con ubicación) y la verificación
contra la tensión admisible si se especificó una.

Usa Ctrl/Cmd+P o el botón "Imprimir / Guardar PDF" para exportar. **Si
estás viendo la app como un Artifact de Claude, ese botón no va a
funcionar** — `window.print()` está deshabilitado en ese entorno por
diseño. Para imprimir/exportar PDF, corre la app desde el repo (ver
"Cómo correr" arriba) en un navegador normal.

## Convención de unidades

| Cantidad | UI (lo que ves/tipeas) | Interno (solver) |
|---|---|---|
| Coordenadas de nodos | m | mm |
| Dimensiones de sección | mm | mm |
| Módulo elástico E | MPa | MPa |
| Carga puntual | kN, kN·m | N, N·mm |
| Carga distribuida | kN/m | N/mm (numéricamente igual, ver `js/units.js`) |
| Tensiones (σ, τ, von Mises) | MPa | MPa |
| Desplazamientos | mm | mm |

Ver `js/units.js` para la conversión exacta.

## Teoría y alcance

- **Elemento**: pórtico plano 2D, 3 GDL por nodo (ux, uy, rz), teoría de
  viga de **Euler-Bernoulli** (sin deformación por corte tipo Timoshenko).
- **Método**: rigidez directa (stiffness method) — ver `js/frameElement.js`
  (matriz de rigidez local 6×6 y transformación global) y `js/solver.js`
  (ensamblaje, condiciones de borde, recuperación de fuerzas internas).
- **Cargas soportadas**: puntuales y momentos en nodos; carga distribuida
  uniforme transversal por barra. **No** soporta carga puntual a mitad de
  barra, carga distribuida no uniforme (trapezoidal), ni carga axial
  distribuida.
- **Material**: lineal elástico, isótropo. Un solo material por barra.
- **Análisis**: estático, lineal (pequeñas deformaciones, sin efectos
  P-Δ ni pandeo), un solo caso de carga (todas las cargas activas a la
  vez — no hay combinaciones ni envolventes).
- **Tensiones**: σ(x,y) = N(x)/A − M(x)·y/I (fibra extrema vía b/h o
  diámetro); τ(x,y) vía fórmula de Jourawski τ = V·Q(y)/(I·b(y)), exacta
  para sección **rectangular sólida** y **circular sólida**. Sección
  "manual" (A, I, c directos) no tiene geometría real para calcular τ, por
  lo que el mapa de von Mises en ese caso usa solo axial+flexión (no se
  inventa una distribución de corte sin conocer la forma real).
- **Von Mises**: estado plano simplificado, σ_vm = √(σ² + 3τ²) (sin
  tensión transversal σ_y, válido para la hipótesis de viga delgada).
- **Deformada**: v(x) se obtiene integrando analíticamente EI·v''(x)=M(x)
  con las condiciones iniciales exactas v(0), v'(0) de la solución nodal
  (no es una interpolación aproximada).

### Qué NO cubre (fuera de alcance deliberado)

- 3D (pórticos espaciales, torsión, flexión biaxial).
- Pandeo / inestabilidad (Euler, efectos P-Δ).
- Cargas dinámicas, sísmicas, térmicas.
- Secciones no prismáticas, compuestas, o con huecos (perfiles I/H/tubo
  rectangular no están implementados — solo rectangular sólida y circular
  sólida; se puede aproximar cualquier otra con la sección "manual" dando
  A/I/c, pero sin cálculo real de corte).
- Continuo 2D/3D con malla libre (FEM general): esto es intencional, ver
  la discusión de alcance al inicio del proyecto — un analizador de
  pórticos/vigas vía método matricial es un problema bien acotado; un FEM
  de geometría arbitraria con mallado es un proyecto distinto y mucho
  mayor.
- Verificación normativa (AISC, Eurocódigo, NCh, etc.) — el factor de
  seguridad opcional es una comparación directa σ_adm/σ_vm, no un check
  de norma.

## Validación

El núcleo de cálculo (álgebra lineal, elemento de pórtico, solver,
tensiones) está verificado contra fórmulas cerradas de resistencia de
materiales — no solo probado manualmente, sino con una suite automatizada:

```bash
node structural/tests/validation.js
```

Casos verificados (tolerancia relativa < 1e-6, salvo identidades exactas):

- Viga simplemente apoyada con carga puntual al centro: momento máximo
  (PL/4), deflexión al centro (PL³/48EI), reacciones (P/2 cada una).
- Viga en voladizo con carga puntual en el extremo: momento en el
  empotramiento (PL), deflexión en el extremo (PL³/3EI), reacción (P).
- Viga simplemente apoyada con carga distribuida uniforme: momento máximo
  (wL²/8), deflexión al centro (5wL⁴/384EI), reacciones (wL/2 cada una).
- Identidades de tensión: σ = Mc/I en fibra extrema, τ_max = 1.5V/A
  (rectangular) y 4V/(3A) (circular sólida), von Mises = √3·τ en corte
  puro.

Si modificas `js/frameElement.js`, `js/solver.js` o `js/stress.js`, correr
esta suite antes de confiar en los resultados — un error de signo ahí es
silencioso (el modelo "resuelve" igual, pero da un diagrama o una tensión
con el signo equivocado). De hecho, durante el desarrollo esta misma suite
detectó y permitió corregir dos errores de signo reales: uno en la fuerza
axial N(x) recuperada en la post-proceso, y otro en el vector de carga
equivalente de la carga distribuida uniforme (ambos ya corregidos y
cubiertos por los casos de arriba).

## Estructura de archivos

```
structural/
  index.html              UI (toolbar, canvas, panel de propiedades/resultados)
  css/style.css
  js/
    units.js               conversion de unidades UI <-> interno
    model.js                Node, Element, Section, Model (estructuras de datos)
    linalg.js               eliminacion gaussiana (resolver A*x=b)
    frameElement.js          matriz de rigidez local/global, carga equivalente UDL
    solver.js                ensamblaje, condiciones de borde, fuerzas internas, deflexion
    stress.js                tension normal/corte/von Mises (Jourawski)
    render.js                vista (pan/zoom), dibujo de modelo y overlays de resultados
    catalog.js                carga/consulta del catalogo de perfiles (data/catalog_icha.json)
    memoria.js                genera el HTML de la memoria de calculo imprimible
    app.js                   estado de UI, interaccion, panel de propiedades/resultados
  data/
    catalog_icha.json         429 perfiles reales verificados (ver seccion "Catalogo de perfiles")
    catalog_icha_excluidos.json  filas descartadas por inconsistencia, con el motivo
  tests/
    validation.js            suite de validacion (node structural/tests/validation.js)
```

## Limitaciones conocidas de la UI (no del cálculo)

- Los símbolos de apoyo (triángulo, rodillo, empotramiento rayado) se
  dibujan siempre en orientación "vertical hacia abajo", independiente de
  la orientación real de la barra conectada — es una simplificación
  visual, no afecta el cálculo (que usa solo los flags ux/uy/rz).
- La banda de von Mises se dibuja a una altura de píxeles fija
  (esquemática), no a escala real de la sección — para leer el valor
  exacto, usar la tabla de resultados, no el color.
- No hay deshacer/rehacer ni guardado de modelos (ninguna persistencia:
  recargar la página borra el modelo).
