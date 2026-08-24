# Notas sobre la fuente de datos (Codos_HDPE_Parametricos_DIN16963.xlsx)

Este documento resume como `data/loader.py` interpreta el Excel y que
ambigüedades o datos incompletos se detectaron. Ningun valor listado aqui
como "incompleto" o "ambiguo" se resuelve inventando un numero: la
aplicacion siempre lo expone como `NO DISPONIBLE` o con una nota explicita.

## Hojas y su rol

| Hoja | Rol | Se usa como fuente de datos? |
|---|---|---|
| `BD_Codos` | DN, DN equiv. (pulgadas), R, Le min, Z por angulo (30/45/60/90) | Si — fuente unica para estos campos |
| `BD_PN` | Espesor por DN x PN, y tabla independiente SDR por PN | Si — fuente unica para espesor y SDR |
| `Codo 30/45/60/90` | Repiten R/Le/Z/espesor (ya cubiertos por las tablas anteriores) y aportan el texto de "Configuracion" de segmentos por angulo | Si, solo para "Configuracion" |
| `BUSCADOR` | Formulario de ejemplo con una sola combinacion activa | No — solo se uso para *verificar* las formulas (ver mas abajo), no se lee en tiempo de ejecucion |

## Relaciones verificadas (no supuestas)

- **OD = DN.** En tuberia HDPE el diametro nominal es igual al diametro
  exterior. Verificado contra `BUSCADOR` ("Diametro exterior d" = 110 para
  DN 110).
- **ID = OD − 2 × espesor.** Siempre calculado, nunca buscado en una celda.
  Verificado: 110 − 2×6.6 = 96.8, igual al valor de `BUSCADOR`.
- **Z = Le + R·tan(angulo/2).** Descubierta comparando `BUSCADOR` contra
  `BD_Codos` y confirmada en las 4×21 combinaciones DN×angulo de
  `BD_Codos` (ver `tests/test_geometry.py`). Se usa para calcular Z en
  Modo B cuando el usuario no lo define manualmente; en Modo A, Z se lee
  siempre de la tabla (nunca se recalcula, para no introducir diferencias
  de redondeo frente al catalogo).
- **R no se recalcula.** `r = 1.5 × DN` es la regla de diseño citada por el
  catalogo, pero los valores tabulados en `BD_Codos` ya vienen redondeados
  (ej. DN125 → R=188, no 187.5). Por eso el repositorio siempre lee R de
  la tabla en Modo A.
- **SDR por PN es independiente del DN.** Es, por definicion, la relacion
  de la serie de tuberia (Standard Dimension Ratio), constante para una
  misma clase de presion. La hoja `BD_PN` solo la lista una vez (no por
  cada fila de DN); el repositorio la trata como una tabla PN→SDR
  aplicable a cualquier DN disponible.

## Datos ambiguos o incompletos

1. **Configuracion de segmentos a 30° no esta desglosada.** Las hojas
   `Codo 45/60/90` dan un desglose explicito por segmento (ej. 90° →
   "15° - 30° - 30° - 15°", que suma exactamente el angulo total). La hoja
   `Codo 30` solo tiene el texto "Giro total 30° según esquema de
   catálogo", sin numeros. `data/loader.py` detecta esto (
   `_parse_segment_configuration` devuelve `None` si el texto no son solo
   tokens `NN°` separados por guiones) y el repositorio expone
   `segment_angles_deg = None` con `is_itemized = False`: la UI muestra el
   texto original y una nota, nunca un desglose supuesto.

2. **La configuracion de segmentos es por angulo, no por DN.** El
   workbook solo da un texto de configuracion por hoja de angulo (uno para
   30°, uno para 45°, etc.), no uno distinto por cada DN. Se modela como
   una propiedad del angulo (no del componente completo) — es un supuesto
   de modelado razonable dado como esta organizada la fuente, pero no es
   un hecho verificado para cada DN individualmente.

3. **Combinaciones DN×PN marcadas `N/D`.** Para DN grandes y PN altos
   (ej. DN560/PN20, DN900/PN12,5) `BD_PN` marca la celda `N/D`. El
   repositorio lo traduce a `DataAvailability.NOT_AVAILABLE` y no
   construye un componente.

4. **DN 1200–1600 fuera del alcance formal de DIN 16963.** La hoja
   `BUSCADOR` incluye la nota: "DN 1200 a 1600 figuran como valores no
   cubiertos por DIN 16963." Estos DN tienen fila completa en
   `BD_Codos`/`BD_PN` (son datos de fabricante), pero
   `core/standards/din16963.py` los marca con `din16963_compliant=False`
   y una nota explicita en vez de reportarlos como normados.

5. **Etiqueta de PN con coma decimal.** La columna se llama literalmente
   `PN12,5` (coma, no punto). Se preserva tal cual como clave/etiqueta
   para no inventar una normalizacion que no está en la fuente; la UI la
   muestra igual que en el Excel.
