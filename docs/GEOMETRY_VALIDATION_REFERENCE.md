# Validación geométrica de referencia (V0.2.1)

**Propósito de este documento:** separar, sin ambigüedad, qué parte del
modelo de codo segmentado es **dato del Excel**, qué parte es **ecuación**
(consecuencia matemática necesaria de otros datos) y qué parte es
**hipótesis de modelado** (una interpretación razonable, pero todavía no
confirmada contra un codo fabricado o modelado a mano).

Esta separación existe porque, como se señaló al iniciar V0.2.1: que el
volumen, Z o el cierre geométrico coincidan **no confirma** que el método
de construcción sea el correcto — sólo confirma que el modelo es
matemáticamente consistente consigo mismo. La confirmación real requiere
comparar contra una referencia externa (física o CAD diseñada a mano),
que es exactamente lo que la sección **"Validación de ingeniería"** de la
UI y `core/validation/reference_comparison.py` existen para hacer.

## Tabla resumen

| Concepto | Tipo | Fuente / fórmula |
|---|---|---|
| DN, DN equiv., PN, espesor, SDR | **DATO** | `BD_Codos`, `BD_PN` (Excel) |
| R (radio) | **DATO** | `BD_Codos`, columna `R mm`. Nunca recalculado. |
| Le (tramo recto) | **DATO** | `BD_Codos`, columna `Le min mm`. |
| Z (tabulado, Modo A) | **DATO** | `BD_Codos`, columnas `Z <angulo>° mm`. |
| Configuración (texto: "15°-30°-30°-15°") | **DATO** | Hoja `Codo <angulo>`, fila "Configuración". |
| ID = OD − 2·espesor | **ECUACIÓN** | Siempre calculado, nunca buscado en el Excel. |
| Z = Le + R·tan(ángulo/2) (Modo B, o verificación) | **ECUACIÓN** | Verificada contra las 84 combinaciones DN×ángulo de `BD_Codos` (ver `docs/DATA_NOTES.md`). Tratada como relación geométrica verificada contra este Excel — no como cita textual de DIN 16963. |
| Plano de inglete = bisectriz de las dos direcciones adyacentes | **ECUACIÓN** | Consecuencia matemática obligatoria si se acepta el supuesto de los puntos de unión (ver abajo): es la única familia de planos que hace coincidir las secciones elípticas de dos cilindros iguales que se encuentran en ese punto. |
| Cada número de "Configuración" = arco (grados) que ese gajo ocupa sobre el círculo de radio R | **HIPÓTESIS DE MODELADO** | Ver sección siguiente. |
| El codo es plano (sin componente fuera del plano de la curva) | **HIPÓTESIS DE MODELADO** | Consistente con los datos disponibles (DIN 16963 no define codos espaciales), pero no verificada contra fabricación real. |
| Longitud exterior/interior aproximada de cada gajo | **DERIVADO** (de la hipótesis anterior + geometría de planos) | Ver "Cómo se obtienen las longitudes". |

## Qué representa R

R es el radio de curvatura del codo tal como lo entrega el catálogo
(`BD_Codos`, columna `R mm`). Es un **dato**, no algo que la aplicación
calcule: aunque el catálogo cita la regla de diseño `r = 1.5 × DN`, los
valores tabulados ya vienen redondeados de fábrica (p. ej. DN125 → R=188,
no 187.5), así que `data/repository.py` siempre lee R de la tabla.

En el modelo geométrico, R es el radio de la **circunferencia teórica**
sobre la que se apoya toda la hipótesis de segmentación — visible en la
vista de ingeniería como "Circunferencia teórica R".

## Qué representa Z

Z es la distancia, medida desde el **vértice teórico** (la intersección
imaginaria de los dos ejes rectos, si el codo no existiera) hasta la cara
de cada extremo (P1 o P2). En Modo A se lee directamente de `BD_Codos`
(columnas `Z <ángulo>°`). En Modo B, si el usuario no la ingresa
manualmente, se calcula con la ecuación `Z = Le + R·tan(ángulo/2)`.

Es simétrica en este modelo: la misma Z aplica a ambos lados (consistente
con que el catálogo sólo publica una Z por combinación DN×ángulo, no una
Z por lado).

## Cómo se calculan los gajos (la hipótesis central)

El texto "Configuración" de la hoja `Codo <ángulo>` (ej. `15° - 30° -
30° - 15°` para 90°) da un desglose que **suma exactamente el ángulo
total**. `core/geometry/segmented_elbow.py` interpreta esto literalmente:
cada número es el arco, en grados, que ese gajo ocupa sobre la misma
circunferencia de radio R usada para el cálculo de Z. Los puntos de unión
son entonces:

```
offsets = cumsum([0, 15, 30, 30, 15]) = [0, 15, 45, 75, 90]
punto[k] = centro_arco + R · (cos(-90° + offsets[k]), sin(-90° + offsets[k]))
```

Esta construcción hace que el primer y el último punto coincidan
**exactamente** con los puntos de tangencia T1/T2 ya usados para Z —
propiedad verificada en `tests/test_segmented_elbow.py`, no asumida.

**Por qué esto sigue siendo una hipótesis, no un hecho confirmado:** es
la lectura más literal posible de un dato que cierra exacto, pero el
Excel no dice explícitamente "estos son arcos sobre un círculo de radio
R". Podría, en teoría, ser otra convención de fabricación (p. ej. un
método de "ángulo de corte" distinto) que produjera un desglose textual
idéntico pero gajos de longitud distinta. La única forma de descartar
esa posibilidad es comparar contra un codo real — de ahí V0.2.1.

## Cómo se obtienen las longitudes

- **Longitud de eje** (`axis_length_mm`): distancia recta entre los dos
  puntos de unión de ese gajo (`ElbowSegment.length_mm`).
- **Longitud exterior/interior aproximada**: la longitud real que un
  fabricante marcaría a cada lado del tubo antes de cortarlo a inglete.
  Se calcula extendiendo la línea generatriz del cilindro (a radio OD/2,
  en la dirección extrados — la que se aleja del centro de la
  circunferencia teórica, o intrados — la que se acerca) hasta
  intersectarla con los dos planos de corte reales del gajo. Es
  **derivada** (no un dato ni una hipótesis nueva): una vez aceptados los
  puntos de unión y los planos de inglete, esta longitud es la única
  consistente con ellos. Como verificación interna: el promedio de la
  longitud exterior e interior siempre da exactamente la longitud de eje
  (ver `tests/test_engineering_report.py`).

## Cómo se determinan los planos de inglete

Cada unión (incluidos los extremos abiertos P1/P2) usa un plano cuya
normal es la **bisectriz** de las direcciones de las dos piezas que se
encuentran ahí. Esto no es una hipótesis sobre los datos: es la solución
geométrica necesaria para que las dos secciones (generalmente elípticas)
encajen sin superposición ni hueco, dado que ambas piezas tienen el mismo
diámetro. En P1/P2 sólo hay una pieza, así que la "bisectriz" de una
dirección consigo misma da un corte perpendicular (extremo abierto
normal, no a inglete).

## La herramienta de verificación dimensional (V0.2.1)

En la UI, sección **"Validación de ingeniería"**:

1. **Vista de ingeniería**: el codo 3D con overlays adicionales —
   circunferencia teórica R, puntos de unión, planos de corte, cotas
   principales (Z, R, Le) y numeración de gajos. Permite *ver* la
   hipótesis, no sólo confiar en que el cierre numérico es correcto.
2. **Tabla de fabricación**: por gajo — ángulo, ángulo acumulado,
   longitud de eje, longitud exterior/interior aproximada, coordenadas
   de inicio/fin, dirección, ángulo de los planos de corte inicial y
   final.
3. **Tabla de uniones**: posición de cada unión y distancia a la
   siguiente.
4. **Dimensiones generales**: ancho/alto/largo del sólido (envolvente de
   la malla real, no una caja aproximada), distancia P1-P2, distancia de
   cada puerto al vértice teórico, R utilizado, Z resultante.
5. **Comparación MODELO PARAMÉTRICO vs MODELO DE REFERENCIA**
   (`core/validation/reference_comparison.py`): el usuario ingresa las
   medidas reales de un codo ya diseñado a mano o fabricado. Por cada
   campo con un valor de referencia ingresado (los campos en blanco/0 se
   omiten, nunca se asumen), se calcula diferencia absoluta \[mm],
   diferencia porcentual \[%] y **PASS/FAIL** contra una tolerancia
   editable (presets ±1/±2/±5 mm, o un valor personalizado). **La
   geometría nunca se ajusta automáticamente** para hacer coincidir los
   valores. Cada fila reprobada muestra qué hipótesis de modelado (de la
   tabla resumen de arriba) es la primera sospechosa de causar esa
   desviación.

### Caso de referencia principal: DN315 / PN10 / 90°

Valores que el modelo paramétrico produce hoy para esta combinación
(reproducibles en `tests/test_engineering_report.py`):

| Dimensión | Valor |
|---|---|
| OD / e / ID | 315 / 18.7 / 277.6 mm |
| R / Le / Z | 473 / 300 / 773 mm |
| Configuración | 15° - 30° - 30° - 15° |
| Ancho total / Largo total | 930.5 / 930.5 mm |
| Alto total | 315 mm (= OD, exacto para un codo plano) |
| Distancia P1-P2 | 1093.187 mm |
| Distancia P1/P2 - vértice | 773 mm |
| Gajo 1 y 4 — long. eje / ext. / int. | 123.478 / 165.13 / 81.83 mm |
| Gajo 2 y 3 — long. eje / ext. / int. | 244.843 / 318.37 / 171.31 mm |

Estos números están listos para compararse en cuanto se disponga de las
medidas del modelo de referencia diseñado manualmente.

## Estado del modelo

La UI muestra, siempre, el banner:

> MODELO MATEMÁTICO — PENDIENTE DE VALIDACIÓN CONTRA REFERENCIA
> FÍSICA/CAD

Este texto **no cambia automáticamente**, ni siquiera si una comparación
ingresada da 100% PASS: una comparación exitosa contra *algunos* campos
no es lo mismo que una validación completa y deliberada contra el modelo
de referencia. El cambio a "MODELO GEOMÉTRICO VALIDADO" es una decisión
que se tomará explícitamente en el código cuando esa validación completa
se haya hecho, no algo que la herramienta se auto-otorgue.
