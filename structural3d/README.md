# Pórticos 3D — esfuerzos, deformaciones, von Mises, N/Vy/Vz/T/My/Mz

Herramienta web standalone (HTML/JS, sin backend) para analizar pórticos
espaciales (3D) definidos por coordenadas de nodos y barras. Es el
equivalente 3D de `structural/` (2D), pero es **código completamente
aparte** — no comparte archivos ni namespace JS (`FEM3D` en vez de `FEM`).

## Por qué tablas de coordenadas y no "dibujar con el mouse"

En 2D, hacer click en un lienzo define un punto sin ambigüedad. En 3D,
un click en una pantalla 2D no define profundidad — por eso herramientas
profesionales de análisis estructural (SAP2000, ETABS, STAAD.Pro) no
dibujan pórticos 3D a mano alzada: se definen nodos por coordenadas (X,Y,Z)
en una tabla, se conectan con barras, y se usa un visor 3D (rotar/zoom/pan)
para confirmar visualmente la geometría. Esta herramienta sigue el mismo
patrón: tabla de nodos, tabla de barras, tabla de cargas, visor 3D
(Three.js) de solo lectura para verificar.

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

1. Pestaña **Nodos**: agrega nodos con sus coordenadas (m) y tipo de
   apoyo (Libre / Pin 3D / Fijo). Un "Pin 3D" restringe las 3 traslaciones
   y deja las 3 rotaciones libres.
2. Pestaña **Barras**: agrega barras conectando dos nodos existentes.
   Selecciona una barra en la tabla para editar en el panel de abajo:
   material (E, G — con atajos Acero/Hormigón/Aluminio), sección
   (rectangular o circular sólida), carga distribuida uniforme (UDLy,
   UDLz, kN/m) y el ángulo β de rotación de la sección alrededor de su
   propio eje.
3. Pestaña **Cargas**: cargas puntuales por nodo (Fx,Fy,Fz en kN;
   Mx,My,Mz en kN·m).
4. **Calcular**: resuelve el modelo. Pestaña **Resultados**: reacciones,
   máximos por barra, von Mises máximo global con ubicación, y el corte
   de torsión máximo aproximado por barra (ver limitaciones).
5. En el visor 3D: arrastrar rota la cámara, rueda hace zoom, shift+arrastrar
   desplaza (pan). "Ajustar vista" reencuadra a los nodos actuales.
   La forma deformada se dibuja coloreada por von Mises (azul=bajo,
   rojo=alto), con escala automática (o manual, campo "Escala deformada").

El modelo carga con un ejemplo pequeño (pórtico en L, empotrado, con carga
en el extremo) para que el visor no arranque vacío — bórralo con
"Limpiar todo" para empezar de cero.

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
- Dibujo libre en 3D (ver la sección de arriba sobre por qué se usa
  tabla de coordenadas).

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

## Estructura de archivos

```
structural3d/
  index.html
  css/style.css
  js/
    units.js            conversion UI <-> interno (igual patron que 2D)
    model.js             Node, Element, Section (3D), Model, tabla Roark
    linalg.js             eliminacion gaussiana (duplicado del 2D, codigo aparte)
    frameElement.js        rigidez local 12x12, ejes locales 3D, carga equivalente UDL
    solver.js               ensamblaje, condiciones de borde, N/Vy/Vz/T/My/Mz, deflexion
    stress.js                sigma biaxial, corte Jourawski por eje, torsion, von Mises
    render3d.js               escena Three.js, geometria, forma deformada coloreada
    app.js                     tablas de nodos/barras/cargas, estado, resultados
    vendor/three.min.js, vendor/OrbitControls.js   (vendorizados, sin CDN)
  tests/
    validation.js            suite de validacion (node structural3d/tests/validation.js)
```

## Limitaciones conocidas de la UI

- No hay deshacer/rehacer ni guardado de modelos.
- Los marcadores de apoyo (cubo=fijo, cono=pin) se dibujan siempre
  apuntando en -Z local al nodo, sin relación con la orientación real del
  apoyo — es solo un indicador visual, no afecta el cálculo.
- La forma deformada se colorea con el von Mises **máximo de la sección
  en cada x** (colapsando y,z a un solo valor por corte transversal) —
  para la distribución exacta dentro de la sección, usar los resultados
  numéricos, no el color.
