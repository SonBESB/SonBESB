# Catalogo PEXGOL 2023 - integracion preliminar

Estado: **DRAFT_UNVERIFIED**. Ninguna fila se considera aprobada por una
extraccion automatica o revision visual del asistente. La revision humana
pendiente se mantiene en la interfaz y en cada fila exportada.

Fuente: Engineering Guide Spanish 16-05-2023.pdf, entregado por el usuario.
SHA-256: `225dae2124298b5f9a5e8ec4cce5ab65c2bd0f85772568da6e01d1b56f59c11a`.
El PDF original permanece en los archivos del proyecto del usuario; la tabla
transcrita esta en `data_sources/pexgol_catalog/dimensions.json`.

## Alcance

- 170 referencias, ocho clases (6, 8, 10, 12, 15, 19, 24, 30), pp. 10-13.
- Se conserva DE (diametro exterior), no se lo renombra como DN sin evidencia.
- DI y espesor publicados alimentan el modelo; no se recalcula ni corrige DI.
- `*` significa cantidad minima; `**`, bajo pedido especial.
- Rugosidad absoluta: 0,0005-0,0007 mm, p. 23. Se propone 0,0007 mm editable.
  No se aplica el factor de temperatura de las tablas Hazen-Williams a
  Darcy/Colebrook, que ya utiliza las propiedades del fluido.
- Presion admisible: tabla 9.1, p. 9, agua, C=1,25. Se conserva el valor de la
  tabla (Clase 10 a 20 C: 9,9 bar), no el encabezado redondeado de p. 11.
  Entre temperaturas se usa el escalon superior, una decision conservadora
  de implementacion, no una regla atribuida al fabricante. Fuera de 10-110 C
  o con fluido personalizado no se emite PASS/FAIL de presion para el caso.
  Los tramos manuales conservan la referencia PN sin derateo.
- Golpe de ariete toma el espesor de la referencia seleccionada. E requiere
  aceptacion como supuesto del usuario: 465 MPa por defecto proviene solo
  del ejemplo de tuberia enterrada a 20 C de p. 46. No se extrapola una tabla
  E(T) ni se aplica automaticamente el multiplicador transitorio de 2,5.
- La exportacion JSON incluye codigo, dimensiones originales, observaciones,
  estado de revision, pagina, revision, hash del documento, temperatura de
  tabla y presion usada. El E utilizado se incluye si se activa su calculo.

## Discrepancias conservadas

Son diferencias aritmeticas o con el codigo; no se afirma que todas sean
erratas. Algunas pueden responder a redondeos. Requieren resolucion humana
antes de aprobar el catalogo. Hay 26 referencias marcadas.

| Clase | Codigo | Pagina | Observacion |
|---|---|---|---|
| 10 | PA-754.7BLK | 11 | DI publicado 65.8 mm; DE - 2e = 65.6 mm; diferencia 0.2 mm. Sin correccion automatica. |
| 12 | PA-50036.7BLK | 11 | DI publicado 426.4 mm; DE - 2e = 426.6 mm; diferencia -0.2 mm. Sin correccion automatica. |
| 12 | PA-63046.6BLK* | 11 | DI publicado 537.4 mm; DE - 2e = 536.8 mm; diferencia 0.6 mm. Sin correccion automatica. |
| 15 | PA-162BLK | 12 | DI publicado 13 mm; DE - 2e = 12 mm; diferencia 1 mm. Sin correccion automatica. |
| 15 | PA-202BLK | 12 | DI publicado 16.2 mm; DE - 2e = 16 mm; diferencia 0.2 mm. Sin correccion automatica. |
| 15 | PA-56050.9BLK** | 12 | DI publicado 458.4 mm; DE - 2e = 458.2 mm; diferencia 0.2 mm. Sin correccion automatica. |
| 15 | PA-63057.3BLK | 12 | DI publicado 515.6 mm; DE - 2e = 515.4 mm; diferencia 0.2 mm. Sin correccion automatica. |
| 19 | PA-12514.1BLK | 12 | DI publicado 97 mm; DE - 2e = 96.8 mm; diferencia 0.2 mm. Sin correccion automatica. |
| 19 | PA-22525.0BLK | 12 | DI publicado 175 mm; DE - 2e = 174.6 mm; diferencia 0.4 mm. Sin correccion automatica. Espesor en codigo 25 mm; columna 25.2 mm. |
| 19 | PA-63070.0BLK* | 12 | DI publicado 489.4 mm; DE - 2e = 490 mm; diferencia -0.6 mm. Sin correccion automatica. |
| 24 | PA-506.9BLK | 13 | DI publicado 38.2 mm; DE - 2e = 36.2 mm; diferencia 2 mm. Sin correccion automatica. |
| 24 | PA-20027.4BLK | 13 | DI publicado 145.2 mm; DE - 2e = 145.4 mm; diferencia -0.2 mm. Sin correccion automatica. Espesor en codigo 27.4 mm; columna 27.3 mm. |
| 24 | PA-22530.7BLK | 13 | Espesor en codigo 30.7 mm; columna 30.8 mm. |
| 24 | PA-56076.7BLK** | 13 | DI publicado 406.5 mm; DE - 2e = 406.6 mm; diferencia -0.1 mm. Sin correccion automatica. |
| 24 | PA-63086.3BLK* | 13 | DI publicado 457 mm; DE - 2e = 457.4 mm; diferencia -0.4 mm. Sin correccion automatica. |
| 24 | PA-71097.3BLK** | 13 | DI publicado 515 mm; DE - 2e = 515.4 mm; diferencia -0.4 mm. Sin correccion automatica. |
| 30 | PA-11018.3BLK | 13 | DI publicado 73 mm; DE - 2e = 73.4 mm; diferencia -0.4 mm. Sin correccion automatica. |
| 30 | PA-14023.3BLK | 13 | DI publicado 93 mm; DE - 2e = 93.4 mm; diferencia -0.4 mm. Sin correccion automatica. |
| 30 | PA-18029.9BLK | 13 | DI publicado 120 mm; DE - 2e = 120.2 mm; diferencia -0.2 mm. Sin correccion automatica. |
| 30 | PA-20033.2BLK | 13 | DI publicado 133.5 mm; DE - 2e = 133.6 mm; diferencia -0.1 mm. Sin correccion automatica. |
| 30 | PA-22537.4BLK | 13 | DI publicado 150 mm; DE - 2e = 150.2 mm; diferencia -0.2 mm. Sin correccion automatica. |
| 30 | PA-31552.3BLK* | 13 | DI publicado 210 mm; DE - 2e = 210.4 mm; diferencia -0.4 mm. Sin correccion automatica. |
| 30 | PA-40066.7BLK* | 13 | DI publicado 266.5 mm; DE - 2e = 266.6 mm; diferencia -0.1 mm. Sin correccion automatica. |
| 30 | PA-50083.4BLK* | 13 | Espesor en codigo 83.4 mm; columna 83.5 mm. |
| 30 | PA-56093.4BLK** | 13 | Espesor en codigo 93.4 mm; columna 93.5 mm. |
| 30 | PA-710118.3BLK** | 13 | DI publicado 473 mm; DE - 2e = 473.4 mm; diferencia -0.4 mm. Sin correccion automatica. |

## Validacion de implementacion

Suite existente y pruebas de catalogo: 300 pasan, 1 omitida (CadQuery).
Prueba de interfaz/JSON adicional: pasa; verifica tramos mixtos, presion a
40 C, procedencia, E usado en golpe de ariete y retorno a entrada manual.
Estas pruebas verifican el software, no aprueban los datos del fabricante.
