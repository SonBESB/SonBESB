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
- **La UI (`ui/pump_operating_view.py`) soporta hasta 2 tramos en
  serie**, igual que PiezoCalc — no modela redes con derivaciones.

## Validacion cruzada realizada

Con los mismos inputs del caso de ejemplo de PiezoCalc (tramo de 1250 m,
DI=250 mm HDPE, rugosidad 0.007 mm, altura estatica 18.5 m, curva de
bomba (0,38)/(100,34)/(220,24) L/s-m, eta bomba 75%, eta motor 92%),
este modulo entrega Q=103.63 L/s / H=33.78 m (PiezoCalc: Q=103.50 L/s /
H=33.71 m) — la diferencia de ~0.1-0.2% es la esperada entre
Colebrook-White (aqui) y Swamee-Jain (PiezoCalc), y confirma que la
implementacion es consistente con la referencia en el rango donde
ambas correlaciones deberian coincidir.
