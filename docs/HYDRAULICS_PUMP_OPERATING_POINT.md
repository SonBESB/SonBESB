# Bombeo — Punto de Operacion (`core/hydraulics/`)

Modulo de hidraulica de sistemas de bombeo: interseccion entre la curva
de una bomba y la curva de un sistema de tuberias, con verificacion
NPSH, leyes de afinidad (VDF, recorte de rodete, bombas gemelas) y
potencia. Independiente del motor geometrico de codos (`core/geometry/`).

## Origen y motivacion

El punto de partida fue una app web de referencia, **PiezoCalc**
(pump.geo-alba.com), que resuelve el mismo problema (tramos en serie +
accesorios + curva de bomba -> caudal de equilibrio) con una interfaz
en vivo. Se analizo su base de calculo y se encontraron limitaciones
reales:

1. **Sin viscosidad como input** — solo pide densidad; el Reynolds (y
   por tanto la friccion) asume implicitamente agua a una temperatura
   fija, sin advertirlo.
2. **Curva de bomba por interpolacion lineal de 3 puntos** — cerca de
   los extremos (cierre, caudal de fuga) puede desviar la carga varios
   metros respecto a una curva real, tipicamente concava.
3. **Eficiencia de bomba constante en todos los escenarios VDF** — la
   eficiencia real cae fuera del punto de mejor eficiencia (BEP), que
   ademas se desplaza al escalar la velocidad.
4. **Coeficientes K sin dependencia del diametro** (heredado tambien
   de la fuente usada aqui, ver mas abajo).
5. **Sin verificacion NPSH** — ausencia total de calculo de cavitacion.
6. **Solo modela la linea de impulsion** — la succion no aparece.
7. La columna "Presion" de su tabla por tramo literalmente dice "no
   evaluado" — seleccionan una clase PN pero nunca comparan la presion
   de trabajo calculada contra ella.

Para portar una version mas rigurosa se uso como segunda fuente una
planilla de calculo en SMath Studio (`Bombas.sm`, autor: Bryam Perez,
compartida por el usuario junto con el pedido), que sí resuelve varios
de estos puntos correctamente:

- Factor de friccion por **Colebrook-White** (implicito, resuelto via
  Newton-Raphson), no Swamee-Jain.
- Curva de bomba y de sistema por **regresion de minimos cuadrados**
  (`polyfit`, grados constante/lineal/cuadratica/cubica), no
  interpolacion lineal.
- **NPSH disponible vs requerido**, con presion atmosferica corregida
  por altitud (formula barometrica ISA) y presion de vapor por
  temperatura, y un margen de seguridad de 1 m sobre el NPSH del
  fabricante.
- Leyes de afinidad completas: variador de frecuencia, recorte de
  rodete, bombas gemelas en paralelo y en serie.

Pero la planilla SMath tambien tiene un bug real, que se corrigio al
portar el codigo:

- **`potencia(Q, H, eta)` hardcodea 1000 kgf/m3** (agua) en vez de
  recibir la densidad como parametro. Si se reutiliza esa funcion con
  un fluido de otra densidad, el resultado queda mal sin ningun aviso.
  Aqui (`power.py`) la densidad es siempre un argumento explicito.

Y una discrepancia real entre ambas fuentes que se documenta en vez de
ocultar: la tabla de coeficientes K de PiezoCalc y la de la planilla
SMath difieren para "valvula de compuerta" (ver `minor_losses.py`,
`FITTING_K_DISCREPANCIES`) — ninguna de las dos cita una norma
especifica (tipo Crane TP-410) para su tabla, asi que ningun K de
`FITTING_K_TABLE` debe tomarse como definitivo sin contrastarlo contra
el catalogo real del accesorio.

## Estructura

| Modulo | Responsabilidad |
|---|---|
| `fluids.py` | Densidad/viscosidad del agua por tabla (Cengel & Cimbala) interpolada por temperatura, o fluido personalizado marcado explicitamente como no verificado. |
| `friction.py` | Reynolds, Colebrook-White (Newton-Raphson) con rama laminar exacta (`Re<2300`) y aviso explicito en zona transicional (`2300<=Re<=4000`), perdida Darcy-Weisbach. |
| `minor_losses.py` | Tabla de K por tipo de accesorio (fuente citada, discrepancias documentadas) y perdida singular. |
| `curve_fit.py` | Ajuste polinomico por minimos cuadrados con R^2 siempre reportado. |
| `system_curve.py` | Tramos de tuberia en serie, evaluacion punto a punto (velocidad, Re, f, hf, hs) y barrido de curva de sistema. |
| `operating_point.py` | Interseccion bomba/sistema por biseccion pura Python (sin scipy); devuelve `found=False` con razon explicita si no hay cambio de signo, en vez de inventar un caudal. |
| `affinity.py` | Leyes de afinidad Q∝phi, H∝phi^2, P∝phi^3; eficiencia trasladada por punto (no aplanada); bombas gemelas en paralelo/serie. |
| `npsh.py` | Presion atmosferica (ISA) y de vapor (Tetens) como columna de fluido, NPSH disponible, chequeo PASS/FAIL con margen de seguridad. |
| `power.py` | Potencia hidraulica/al eje/electrica con densidad real siempre explicita. |
| `pressure_rating.py` | Presion de diseno en condicion de shutoff (Q=0, sin friccion) por tramo vs su clase PN, PASS/FAIL. |
| `velocity_check.py` | Velocidad vs rango recomendado (guia de practica, no norma), PASS/BAJA/ALTA por tramo. |
| `surge.py` | Golpe de ariete: celeridad de onda (Korteweg), tiempo critico 2L/a, Joukowsky para cierre rapido y aproximacion lineal para cierre lento. |

## Ampliaciones agregadas tras el analisis inicial (segunda ronda)

Tras entregar la primera version, se le pidio a este modulo un analisis
de que mas se podia agregar "de manera ingenieril". Se identificaron 11
puntos, priorizados por costo/valor; el usuario eligio 4 para esta
ronda (los otros quedan en el backlog, ver seccion de limitaciones):

1. **Presion de diseno vs PN en condicion de shutoff** (`pressure_rating.py`)
   — cierra el hueco de PiezoCalc donde la columna "Presion" decia
   literalmente "no evaluado". Se evalua a Q=0 (sin friccion, toda la
   carga de la bomba aparece como presion estatica) por ser la
   condicion mas exigente en regimen permanente.
2. **Velocidad min/max** (`velocity_check.py`) — PASS/BAJA/ALTA contra
   un rango editable (0.6-3.0 m/s por defecto), declarado como guia de
   practica, no como limite normativo.
3. **Golpe de ariete** (`surge.py`) — el pendiente mas serio identificado
   en el analisis: un diseno que pasa el chequeo de presion en regimen
   permanente puede superar la clase PN varias veces durante un cierre
   de valvula. Modelo simplificado (celeridad de tuberia de pared
   delgada + Joukowsky/cierre lento), declarado como tal — no
   reemplaza un analisis transiente completo (metodo de las
   caracteristicas).
4. **Exportar caso a JSON** — mismo patron que `elbow_to_dict` del
   modulo de codos: inputs + resultados descargables, sin mecanismo de
   reimportacion (igual que el modulo de codos).

Sobre el fluido: se evaluo agregar reologia no-newtoniana (pulpas/lodos
mineros, dado el dominio `geo-alba.com`), pero el usuario indico que el
fluido de trabajo por defecto sigue siendo agua — la seccion de fluido
personalizado (`custom_fluid`) ya permite ingresar densidad/viscosidad
manualmente para una estimacion aproximada de una pulpa, pero eso trata
al fluido como newtoniano equivalente: es una aproximacion de primer
orden, no un modelo de reologia Bingham/power-law. Si el fluido de
trabajo real no es agua, ese aviso debe tomarse en serio antes de usar
los resultados para diseno.

## Limitaciones conocidas (no resueltas, declaradas)

- **K de accesorios sin dependencia del diametro** — en la practica
  (metodo Crane, `K = f_T * L/D`) K varia con el diametro nominal. Para
  un accesorio critico de una linea real, usar el K de catalogo
  especifico del fabricante, no esta tabla generica.
- **Viscosidad del agua fija por tabla, no corregida para otros
  fluidos** — para un fluido distinto del agua, el usuario debe
  ingresar densidad y viscosidad manualmente (`custom_fluid`); no se
  extrapola ninguna correlacion.
- **Presion de vapor (Tetens) valida solo para agua entre 0-100 C** —
  no se aplica a otros fluidos.
- **Interseccion via biseccion asume una unica raiz en el rango** — si
  la curva de sistema no es monotona (topologia mas compleja que
  tramos en serie con un solo punto de union) puede no encontrar todas
  las intersecciones. Suficiente para el modelo de tramos en serie que
  implementa `system_curve.py`, no para redes ramificadas.
- **La UI (`ui/pump_operating_view.py`) soporta N tramos en serie**
  (sin limite artificial) — pero sigue siendo un modelo de tramos EN
  SERIE, no modela redes con derivaciones (tees que reparten caudal).
- **El perfil de elevacion para el chequeo de presion se reparte
  proporcional a la longitud acumulada**, no a cotas de terreno reales
  — mismo supuesto que declara PiezoCalc ("perfil ilustrativo").
- **El golpe de ariete usa un modulo elastico de tuberia generico por
  material** (no de catalogo especifico del fabricante) y asume el
  modulo de compresibilidad del agua para el fluido — si el fluido real
  no es agua, ese valor no aplica y el resultado de sobrepresion queda
  mal sin que la UI lo bloquee (solo lo advierte).
- **No implementado (backlog, ver seccion de ampliaciones):** redes
  ramificadas, diametro economico, reologia no-newtoniana/transporte de
  solidos, bombas no identicas en paralelo, derateo de presion HDPE por
  temperatura, fuerzas de empuje en codos bajo presion, catalogo de
  materiales de fabricante (PEXGOL/HDPE/PVC/acero/hierro fundido) — este
  ultimo con diseno propuesto pendiente de que el usuario aporte los
  PDF de catalogo.

## Validacion cruzada realizada

Con los mismos inputs del caso de ejemplo de PiezoCalc (tramo de 1250 m,
DI=250 mm HDPE, rugosidad 0.007 mm, altura estatica 18.5 m, curva de
bomba (0,38)/(100,34)/(220,24) L/s-m, eta bomba 75%, eta motor 92%),
este modulo entrega Q=103.63 L/s / H=33.78 m (PiezoCalc: Q=103.50 L/s /
H=33.71 m) — la diferencia de ~0.1-0.2% es la esperada entre
Colebrook-White (aqui) y Swamee-Jain (PiezoCalc), y confirma que la
implementacion es consistente con la referencia en el rango donde
ambas correlaciones deberian coincidir.


## Catalogo PEXGOL (borrador 2023)

Selector por clase y referencia, presion admisible por temperatura para agua,
espesor para golpe de ariete y procedencia exportada. Ver
[PEXGOL_CATALOG.md](PEXGOL_CATALOG.md) para alcance y 26 discrepancias.
Datos pendientes de revision humana; resultados preliminares.

## Presion de borde (tie-in / destino presurizado)

Limitacion real reportada por el usuario: el "Desnivel entre destino y
origen" solo captura la diferencia de cota, no una diferencia de presion
de borde cuando el sistema conecta a una red existente con presion
conocida (tie-in) y debe entregar a una presion minima en el destino
(ej. una sala de proceso). Antes, la unica forma de modelar eso era
mezclarlo a mano dentro del campo de desnivel, sin dejar rastro de que
parte era geometria y que parte era presion.

`core/hydraulics/system_curve.pressure_boundary_head_m(available_bar,
required_bar, density_kg_m3)` convierte `(presion_requerida -
presion_disponible)` a una carga equivalente en metros (ecuacion de
energia entre el origen y el destino: positivo exige mas carga a la
bomba, negativo indica que la presion ya disponible en el origen cubre
parte o toda la presion requerida en el destino). La UI lo suma al
desnivel geometrico para obtener el "desnivel efectivo" que alimenta la
curva de sistema — ambos valores (geometrico y el ajuste) quedan
visibles por separado en pantalla y en el JSON exportado
(`desnivel_geometrico_m`, `presion_disponible_origen_bar`,
`presion_requerida_destino_bar`, `altura_estatica_m`). Por defecto ambas
presiones son 0 bar (ambos extremos abiertos a la atmosfera), que es un
no-op: no cambia el comportamiento de un caso que no las usa.

No se mezcla con la fricción ni con el modo "% de la fricción" para
accesorios (ver seccion anterior): son tres ajustes de carga
independientes y con una fuente fisica distinta cada uno (perdida por
friccion, perdida/estimacion por accesorios, diferencia de presion de
borde).

**Bug encontrado y corregido tras revision externa (OT-120):** el "desnivel
efectivo" de arriba es valido SOLO para resolver el punto de equilibrio
bomba-sistema — nunca debe reutilizarse como si fuera la elevacion real en
un calculo que dibuja un perfil de presion fisico. Las primeras versiones
de `illustrative_profile` (perfil de energia) y `build_shutoff_pressure_profile`
(presion vs PN en shutoff) recibian ese valor ya mezclado con la presion de
borde en el parametro pensado para la elevacion geometrica, lo que producia
una cota ficticia y, en el perfil ilustrativo, presiones negativas espurias
que no reflejaban la instalacion real. Corregido: ambas funciones ahora
reciben la elevacion geometrica real por separado y un nuevo parametro
`inlet_pressure_head_m` con la carga de la presion real ya disponible en la
succion (0.0 por defecto, sin cambio de comportamiento cuando no se usa
presion de borde). Ver `pressure_to_head_m` en `system_curve.py` para la
conversion bar -> m reutilizada en ambos lugares.

Este mismo mecanismo (`inlet_pressure_head_m=0`, sin bomba) es el que
calcula la "presion residual estimada en el destino" que se muestra en el
modo sin bomba: toma la presion real de entrada, resta las perdidas y la
elevacion real, y entrega la presion que efectivamente llegaria al destino
sin ningun aporte de bomba — independiente de cualquier presion "requerida"
que se haya ingresado como supuesto de diseño.

## Importar una tabla de requisitos (CSV)

Modulo `core/hydraulics/requirements_import.py`, expuesto en la UI como
"📥 Importar tabla de requisitos (CSV)" al inicio de la calculadora. Pensado
para el flujo de trabajo real: el usuario ya trae una tabla de requisitos de
ingenieria (como la de OT-120 — parametro/valor) y quiere que la calculadora
arranque con esos datos en vez de reescribirlos campo por campo.

Formato esperado: CSV de dos columnas, `parametro,valor`. Tolera acentos,
mayusculas, unidades inline ("12,50 m", "2,5 bar", "82 L/min = 1,3667 L/s")
y separador decimal "," o ".". La lista completa de nombres de parametro
reconocidos esta en `_KEY_ALIASES` del modulo.

**Mismo limite deliberado que la libreria de casos guardados, y por la misma
razon** (ver seccion de arriba): solo se rellenan campos INDEPENDIENTES —
fluido, temperatura, desnivel geometrico, presiones de borde, un tramo con
geometria MANUAL (longitud, diametro interior, rugosidad, clase PN, % de
accesorios) y el caudal de diseno (que activa el modo sin bomba). Nunca se
rellenan: accesorios detallados por pieza, selecciones de catalogo
HDPE/PEXGOL, la curva Q-H de la bomba, ni escenarios VDF — esas claves de
estado son interdependientes entre si y reconstruirlas mal desde un CSV
generico es peor que dejarlas en blanco. Mas de un tramo tampoco se soporta
todavia (solo Tramo 1); con varios tramos reales, se completan a mano los
siguientes.

Cada parametro no reconocido o fuera de este alcance se lista explicitamente
en la UI ("N parametro(s) no importado(s)") en vez de fallar en silencio. Un
archivo ya aplicado no se vuelve a aplicar solo en cada rerun (se guarda su
hash en `session_state`): el usuario puede editar los campos despues de
importar sin que la importacion los pise de vuelta.

## Libreria de calculos guardados (Supabase)

Modulo `core/hydraulics/pumping_library.py`. Persiste casos (el mismo
JSON que ya genera "Descargar caso") en una tabla `pumping_cases` de un
proyecto Supabase dedicado a BESB Piping — separado del proyecto
Supabase de otra app del mismo usuario (finanzas personales), que ya
tenia su propio esquema con autenticacion real.

**Decision de diseno explicita (no es una limitacion encontrada despues,
se eligio asi con el usuario):** la app no tiene login. La "privacidad"
de la libreria es por posesion de un link (`?owner=<uuid>` en la URL),
igual que compartir un documento "cualquiera con el enlace" — no es una
cuenta protegida. Row Level Security esta activo en la tabla, pero su
politica permite cualquier operacion a la key anonima (`using (true)`,
`with check (true)`): RLS no puede verificar de quien es un owner_key
sin autenticacion real, asi que no hay una regla de base de datos que
impida a alguien con la key anonima leer todos los casos si conociera
o adivinara un owner_key ajeno. La proteccion real es que el UUID es
impredecible (122 bits de entropia), no una regla de acceso. Esto se
declara en la UI, no se presenta como seguridad real.

**Limitacion deliberada:** la libreria guarda y permite volver a
descargar el JSON de un caso, pero NO reconstruye automaticamente los
widgets del formulario (tramos, catalogo/SDR por tramo, accesorios,
escenarios VDF, golpe de ariete por material) a partir de un caso
guardado. El formulario tiene demasiadas claves de estado dependientes
entre si (ej. `pump_hdpe_de_{tramo}_{sdr}`, `pump_fit_{tramo}_{pieza}`)
para reconstruirlas con seguridad sin arriesgar una restauracion
silenciosamente incorrecta — mejor no reconstruir el formulario que
reconstruirlo mal. Retomar un caso antiguo significa descargar su JSON
y volver a ingresar esos valores a mano.

**Configuracion:** `SUPABASE_URL` / `SUPABASE_ANON_KEY` en
`st.secrets` (ver README). Sin esas credenciales, la seccion de
libreria se deshabilita con un aviso — el resto de la calculadora
sigue funcionando igual.
