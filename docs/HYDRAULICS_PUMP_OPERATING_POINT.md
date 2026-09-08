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
