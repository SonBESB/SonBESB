# Pórticos 3D — esfuerzos, deformaciones, von Mises, N/Vy/Vz/T/My/Mz

Herramienta web standalone (HTML/JS, sin backend) para analizar pórticos
espaciales (3D) definidos por coordenadas de nodos y barras. Es el
equivalente 3D de `structural/` (2D), pero es **código completamente
aparte** — no comparte archivos ni namespace JS (`FEM3D` en vez de `FEM`).

## Cómo se dibuja en 3D: boceto en 4 paneles (planta/frontal/lateral/3D)

En 2D, hacer click en un lienzo define un punto sin ambigüedad. En 3D, un
click en una pantalla 2D no puede definir la profundidad por sí solo — por
eso herramientas profesionales de análisis estructural (SAP2000, ETABS,
STAAD.Pro) no dibujan pórticos 3D en una sola vista en perspectiva: usan
varias vistas ortogonales sincronizadas (planta + elevaciones) más un
visor 3D para confirmar. Esta herramienta sigue el mismo patrón, pero
dejando el trazado — como un diagrama de cuerpo libre — en manos del
usuario, en vez de forzar una tabla de coordenadas:

- **Planta (X-Y)**, **Frontal (X-Z)** y **Lateral (Y-Z)**: tres lienzos
  2D, cada uno la proyección del mismo modelo sobre un par de ejes. Un
  click en cualquiera de ellos define las DOS coordenadas que esa vista
  puede fijar directamente; la tercera (la que esa vista no puede "ver")
  se toma del valor **activo** correspondiente en la barra de
  herramientas (X/Y/Z activa, en m) — edítalo antes de hacer click para
  controlar la profundidad, o selecciona un nodo ya creado para que su
  posición se vuelva el valor activo (así es fácil alinear nodos nuevos
  con uno existente).
- **3D**: el visor Three.js de siempre (rotar/zoom/pan), ahora como un
  cuarto panel de solo confirmación visual — no se dibuja ahí directamente,
  por la misma razón de ambigüedad de profundidad.
- Los **nodos y barras son el mismo modelo en los 4 paneles**: crear,
  seleccionar o borrar en cualquiera de los tres lienzos 2D afecta a los
  otros tres al instante (incluida la vista 3D). Una barra puede incluso
  "cruzarse" entre vistas: con el modo **+ Barra**, puedes click-ar el
  primer nodo en Planta y el segundo en Frontal — el nodo pendiente queda
  resaltado en los tres lienzos 2D mientras eliges el segundo.
- Las **tablas de Nodos/Barras/Cargas** (pestañas del panel derecho) siguen
  existiendo como respaldo para edición masiva o numérica precisa, y la
  pestaña **Propiedades** muestra siempre el nodo o barra seleccionado
  (por click en cualquier panel o en una fila de tabla) con sus campos
  editables.

## Cómo correr

```bash
cd structural3d
python3 -m http.server 8000
# abrir http://localhost:8000/index.html
```

Three.js y OrbitControls están **vendorizados** en `js/vendor/` (no se
cargan desde un CDN) — el módulo funciona completamente offline, sin
depender de que `cdn.jsdelivr.net` o similar esté disponible.

## Cómo usar

1. **Perfil activo** (arriba del panel derecho): elige material (E, G —
   atajos Acero/Hormigón/Aluminio) y sección (rectangular, circular
   sólida, o **catálogo de perfiles** — ver abajo) *antes* de dibujar.
   Cada barra nueva se crea con este perfil; las ya creadas no cambian al
   editarlo.
2. **+ Nodo** (modo activo por defecto): click en cualquiera de los tres
   paneles 2D (Planta/Frontal/Lateral) para agregar un nodo, con snap a
   grilla de 0.5 m (desactivable). El eje que ese panel no puede fijar
   toma el valor de la coordenada **activa** correspondiente (campos
   X/Y/Z activa en la barra de herramientas, en m).
3. **+ Barra**: click en un nodo (en cualquier panel) y luego en otro —
   pueden estar en paneles distintos — para conectarlos con el perfil
   activo.
4. **Seleccionar**: click en un nodo o barra (en cualquier panel, o una
   fila de tabla) para editarlo en la pestaña **Propiedades**: apoyo
   (Libre / Pin 3D / Fijo) y carga puntual del nodo, o material/sección/
   UDL/ángulo β de la barra.
5. **Borrar**: click en un nodo o barra para eliminarlo (borrar un nodo
   también borra las barras y cargas conectadas a él).
6. **Calcular**: resuelve el modelo. Pestaña **Resultados**: reacciones,
   máximos por barra, **diagramas N/Vy/Vz/T/My/Mz(x) por barra**, von Mises
   máximo global con ubicación, y el corte de torsión máximo aproximado
   por barra (ver limitaciones).
7. En el visor 3D (cuarto panel): arrastrar rota la cámara, rueda hace
   zoom. "Ajustar vista" reencuadra los tres paneles 2D y el visor 3D a
   los nodos actuales. La forma deformada se dibuja coloreada por von
   Mises (azul=bajo, rojo=alto), con escala automática.
8. **Memoria de cálculo**: tras calcular, abre una vista imprimible con
   el modelo, metodología y resultados completos — ver sección propia
   abajo.

Las pestañas **Nodos/Barras/Cargas** siguen disponibles como tablas de
respaldo (útiles para edición numérica precisa o en lote).

El modelo carga con un ejemplo pequeño (pórtico en L, empotrado, con carga
en el extremo) para que los paneles no arranquen vacíos — bórralo con
"Limpiar todo" para empezar de cero.

## Catálogo de perfiles

Mismos datos y misma procedencia que el módulo 2D (`data/catalog_icha.json`,
429 perfiles reales extraídos y verificados desde un archivo ICHA que subió
el usuario del proyecto — ver el README de `structural/` para el detalle
de la validación y las 12 filas excluidas por inconsistencia).

**Mapeo de ejes (importante):** el eje fuerte del catálogo (x-x) siempre
se asigna a **Iy** del modelo 3D (resiste la flexión vertical típica bajo
carga de gravedad), y el eje débil (y-y) a **Iz**. No hay opción de
invertir esto desde el selector — si necesitas "acostar" el perfil, usa
el ángulo β del elemento. Ver el comentario de cabecera de `js/catalog.js`
para la justificación completa de este mapeo (está directamente ligado a
la convención de ejes locales verificada en `tests/validation.js`).

La constante de torsión J se calcula con la misma aproximación de
Saint-Venant que el módulo 2D (no es un valor de catálogo). **CINTAC no
está incluido** (ver README de `structural/` — ese archivo solo trae
dimensiones, no propiedades de sección calculadas).

## Convención de unidades

Igual que el módulo 2D: UI en m / MPa / mm / kN / kN·m / kN/m; interno en
mm / N / N·mm / MPa. Ver `js/units.js`.

## Teoría y alcance

- **Elemento**: pórtico espacial, **6 GDL por nodo** (ux,uy,uz,rx,ry,rz),
  Euler-Bernoulli para flexión (ambos ejes, Iy e Iz) + **torsión de
  Saint-Venant** (GJ/L).
- **Método**: rigidez directa, matrices locales **12×12**. Ver
  `js/frameElement.js` (rigidez local, ejes locales automáticos, carga
  equivalente UDL) y `js/solver.js` (ensamblaje, condiciones de borde,
  recuperación de N/Vy/Vz/T/My/Mz, deflexión v(x)/w(x)).
- **Ejes locales**: x de nodo I a nodo J; y,z automáticos usando un vector
  de referencia "arriba" (global Z, o global X si la barra es vertical) —
  igual convención que SAP2000 por defecto. Rotación manual opcional vía
  el ángulo β por barra.
- **Convención de signos verificada** (no asumida de memoria — ver
  `tests/validation.js`): θz = +dv/dx (como en el módulo 2D), pero
  **θy = −dw/dx** (signo invertido, consecuencia inevitable de un sistema
  de ejes locales right-handed). Esto se refleja en la matriz de rigidez,
  la recuperación de My(x) y la integración de la deflexión w(x) — los
  tres fueron verificados independientemente contra fórmulas cerradas.
- **Secciones**: rectangular sólida y circular sólida (igual que el
  módulo 2D). La constante de torsión J y el coeficiente de tensión de
  corte por torsión para rectángulos usan la **tabla de Roark /
  Saint-Venant** (interpolación lineal por relación de aspecto
  lado-largo/lado-corto) — es una aproximación de ingeniería estándar,
  no una solución cerrada exacta.
- **Cargas**: puntuales/momentos en nodos; carga distribuida uniforme por
  barra en local y/z. No soporta carga puntual a mitad de barra ni carga
  trapezoidal.
- **Von Mises**: σ_vm = √(σ² + 3·(τxy² + τxz²)) — fórmula general exacta
  para un estado σxx + τxy + τxz con σyy=σzz=τyz=0 (hipótesis de viga
  delgada). τxy se aproxima como función solo de y (uniforme en z) y τxz
  solo de z (uniforme en y) — Jourawski estándar, exacto en los ejes de
  simetría.
- **Torsión en el mapa de von Mises**: exacta para sección **circular**
  sólida (flujo de corte circular cerrado, τxy=−Tz/J, τxz=Ty/J). Para
  sección **rectangular**, el campo de Saint-Venant real no es cerrado —
  el corte de torsión NO se incluye en el mapa visual ni en el von Mises
  máximo automático para rectángulos; se reporta aparte como un escalar
  (τ_torsión máx, tabla de Roark) en el panel de resultados, con una nota
  explícita. Si necesitas el caso combinado exacto en una sección
  rectangular, hay que sumarlo a mano en el punto crítico.

### Qué NO cubre (fuera de alcance deliberado)

- Pandeo / inestabilidad (Euler, pandeo lateral-torsional, efectos P-Δ).
- Cargas dinámicas, sísmicas, térmicas.
- Secciones no prismáticas, compuestas, perfiles I/H/tubo (solo
  rectangular sólida y circular sólida).
- Alabeo (warping) de torsión en secciones abiertas — solo Saint-Venant.
- Verificación normativa (AISC, Eurocódigo, NCh) — el factor de seguridad
  opcional es σ_adm/σ_vm directo, no un check de norma.
- Dibujo directamente en el visor 3D en perspectiva (ver la sección de
  arriba sobre por qué se usan proyecciones ortogonales sincronizadas en
  vez de un único lienzo 3D).

## Validación

```bash
node structural3d/tests/validation.js
```

22 verificaciones contra fórmulas cerradas: voladizo con flexión en eje
fuerte (Iz) y eje débil (Iy), torsión pura (ángulo=TL/GJ), viga simplemente
apoyada con UDL en cada dirección (momento, reacciones, deflexión),
orientación de ejes locales, e identidades de tensión (σ=Mc/I, τ_max=1.5V/A
rectangular, τ_max=4V/3A circular, von Mises en corte/torsión puros,
constante de torsión rectangular contra la tabla de Roark).

Este proceso de validación **detectó y corrigió** durante el desarrollo:
un modelo de prueba inicialmente inestable (torsión sin restringir en
ningún nodo — mecanismo real, no bug), y dos errores de signo reales en
la integración de w(x) (eje débil) — ver el comentario de cabecera de
`tests/validation.js` para el detalle. La lección aplicada: en 3D, copiar
por analogía directa la fórmula del eje "gemelo" (z→y) casi nunca es
seguro por la asimetría del sistema right-handed; cada bloque se verificó
por separado contra un caso físico independiente antes de confiar en él.

## Memoria de cálculo

Igual enfoque que el módulo 2D: vista HTML imprimible (no PDF de backend),
con datos de proyecto editables, descripción del modelo, metodología,
resultados (reacciones, máximos y diagramas N/Vy/Vz/T/My/Mz por barra,
von Mises, nota de torsión en rectangulares) y verificación si se
especificó tensión admisible. Usa Ctrl/Cmd+P o el botón "Imprimir /
Guardar PDF" — **ese botón no funciona si estás viendo esto como Artifact**
(`window.print()` deshabilitado ahí); corre desde el repo para imprimir.

## Estructura de archivos

```
structural3d/
  index.html
  css/style.css
  data/
    catalog_icha.json, catalog_icha_excluidos.json  (compartido con structural/, ver ese README)
  js/
    units.js            conversion UI <-> interno (igual patron que 2D)
    model.js             Node, Element, Section (3D), Model, tabla Roark
    linalg.js             eliminacion gaussiana (duplicado del 2D, codigo aparte)
    frameElement.js        rigidez local 12x12, ejes locales 3D, carga equivalente UDL
    solver.js               ensamblaje, condiciones de borde, N/Vy/Vz/T/My/Mz, deflexion
    stress.js                sigma biaxial, corte Jourawski por eje, torsion, von Mises
    render3d.js               escena Three.js, geometria, forma deformada coloreada
    sketch2d.js                 boceto por proyeccion (planta/frontal/lateral): vista, grilla, hit-testing
    catalog.js                 carga/consulta del catalogo de perfiles (mapeo de ejes 3D)
    memoria.js                 genera el HTML de la memoria de calculo imprimible
    app.js                     estado de UI, interaccion de boceto cross-view, tablas, resultados, diagramas
    vendor/three.min.js, vendor/OrbitControls.js   (vendorizados, sin CDN)
  tests/
    validation.js            suite de validacion (node structural3d/tests/validation.js)
```

## Limitaciones conocidas de la UI

- No hay deshacer/rehacer ni guardado de modelos.
- Al crear el primer nodo del modelo, los tres paneles 2D se reencuadran
  automáticamente centrados en él (igual criterio que "Ajustar vista"); a
  partir del segundo nodo, la vista no se reajusta sola en cada click,
  para que no "salte" mientras se dibuja — usa "Ajustar vista" cuando lo
  necesites.
- Las vistas 2D (planta/frontal/lateral) y la vista 3D tienen zoom/pan
  independientes entre sí (cada panel recuerda su propio encuadre).
- Los marcadores de apoyo (cubo=fijo, cono=pin) se dibujan siempre
  apuntando en -Z local al nodo, sin relación con la orientación real del
  apoyo — es solo un indicador visual, no afecta el cálculo.
- La forma deformada se colorea con el von Mises **máximo de la sección
  en cada x** (colapsando y,z a un solo valor por corte transversal) —
  para la distribución exacta dentro de la sección, usar los resultados
  numéricos, no el color.
