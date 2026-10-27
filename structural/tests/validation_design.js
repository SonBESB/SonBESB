/**
 * Suite de validacion del modulo de diseno en acero (js/design.js, AISC 360
 * LRFD). A diferencia de tests/validation.js (que valida contra formulas
 * cerradas de resistencia de materiales), aqui NO hay un "resultado exacto
 * de libro" para comparar porque no se pudo verificar un ejemplo numerico
 * oficial de AISC (ver README y cabecera de design.js) -- en su lugar se
 * verifica:
 *   (a) que la implementacion reproduce calculos hechos a mano con las
 *       MISMAS formulas (detecta errores de transcripcion en el codigo), y
 *   (b) invariantes matematicos de las propias formulas (p.ej. continuidad
 *       del limite elastico/inelastico en E3, casos limite triviales) que
 *       cualquier transcripcion correcta debe cumplir.
 *
 * Correr con: node structural/tests/validation_design.js
 */
'use strict';

var path = require('path');
var base = path.join(__dirname, '..', 'js');
require(path.join(base, 'units.js'));
require(path.join(base, 'linalg.js'));
require(path.join(base, 'model.js'));
require(path.join(base, 'frameElement.js'));
require(path.join(base, 'solver.js'));
require(path.join(base, 'stress.js'));
require(path.join(base, 'catalog.js'));
require(path.join(base, 'design.js'));

var FEM = global.FEM;
var Design = FEM.Design;
var failures = 0;

function check(got, expected, tol, label) {
  var rel = Math.abs(got - expected) / Math.max(1, Math.abs(expected));
  var ok = rel < tol;
  if (!ok) failures++;
  console.log((ok ? 'OK  ' : 'FAIL') + ' ' + label +
    ': got=' + got.toFixed(6) + ' expected=' + expected.toFixed(6) +
    ' rel_err=' + rel.toExponential(3));
}
function checkTrue(cond, label) {
  if (!cond) failures++;
  console.log((cond ? 'OK  ' : 'FAIL') + ' ' + label);
}

var E = 200000; // MPa
var Fy = 250; // MPa

// ---------------------------------------------------------------
// Caso D1: traccion (D2a) -- calculo a mano: Pn = Fy*A
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 100, h: 100 }) });
  var cap = Design.tensionCapacity(geom, Fy);
  check(cap.Pn, Fy * 10000, 1e-9, 'D1 traccion: Pn = Fy*A (100x100mm, Fy=250)');
  check(cap.phiPn, 0.9 * Fy * 10000, 1e-9, 'D1 traccion: phiPn = 0.9*Fy*A');
})();

// ---------------------------------------------------------------
// Caso E1: compresion (E3), rama inelastica -- calculo a mano completo
// Seccion cuadrada 100x100mm: A=10000 mm2, I=100^4/12=8333333.33 mm4,
// r=sqrt(I/A)=28.8675 mm. L=2000mm, K=1 -> KL/r=69.282.
// Fe = pi^2*E/(KL/r)^2 = 9.8696*200000/4800.0 = 411.233 MPa
// limite = 4.71*sqrt(E/Fy) = 4.71*28.284 = 133.22 -> KL/r=69.28 esta en zona inelastica
// Fcr = 0.658^(Fy/Fe)*Fy = 0.658^(0.60794)*250
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 100, h: 100 }) });
  var L = 2000;
  var cap = Design.compressionCapacity(geom, Fy, E, L);

  var r = Math.sqrt((100 * Math.pow(100, 3) / 12) / 10000);
  check(r, 28.8675, 1e-3, 'E1: radio de giro r de seccion cuadrada 100x100');

  var KLr = L / r;
  check(cap.KLr, KLr, 1e-9, 'E1: KL/r reproducido');

  var Fe = (Math.PI * Math.PI * E) / (KLr * KLr);
  check(cap.Fe, Fe, 1e-6, 'E1: Fe = pi^2*E/(KL/r)^2');

  var limiteInelastico = 4.71 * Math.sqrt(E / Fy);
  checkTrue(KLr < limiteInelastico, 'E1: KL/r cae en zona inelastica (precondicion del caso)');

  var FcrEsperado = Math.pow(0.658, Fy / Fe) * Fy;
  check(cap.Fcr, FcrEsperado, 1e-6, 'E1: Fcr = 0.658^(Fy/Fe)*Fy (calculo independiente a mano)');
  check(cap.Fcr, 193.8, 0.01, 'E1: Fcr numerico esperado ~193.8 MPa (calculo a mano, ver cabecera)');

  check(cap.Pn, FcrEsperado * 10000, 1e-6, 'E1: Pn = Fcr*A');
  check(cap.phiPn, 0.9 * FcrEsperado * 10000, 1e-6, 'E1: phiPn = 0.9*Pn');
})();

// ---------------------------------------------------------------
// Caso E2: compresion, rama elastica (columna muy esbelta)
// L muy grande -> KL/r muy alto -> debe usar Fcr = 0.877*Fe
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 100, h: 100 }) });
  var L = 20000; // columna muy larga -> esbelta
  var cap = Design.compressionCapacity(geom, Fy, E, L);
  var limiteInelastico = 4.71 * Math.sqrt(E / Fy);
  checkTrue(cap.KLr > limiteInelastico, 'E2: KL/r cae en zona elastica (precondicion del caso)');
  check(cap.Fcr, 0.877 * cap.Fe, 1e-9, 'E2: Fcr = 0.877*Fe en zona elastica');
})();

// ---------------------------------------------------------------
// Caso E3: caso limite KL/r -> 0 (columna muy corta/robusta): Fcr -> Fy
// Invariante de la formula E3, no depende de ningun ejemplo externo.
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 100, h: 100 }) });
  var cap = Design.compressionCapacity(geom, Fy, E, 1); // L=1mm, practicamente un stub
  check(cap.Fcr, Fy, 1e-3, 'E3: columna muy corta (KL/r->0): Fcr tiende a Fy');
})();

// ---------------------------------------------------------------
// Caso F1: flexion elastica -- Mn = Fy*Sx, Sx=I/c
// Rect 50x100mm (igual que tests/validation.js): Sx = (50*100^3/12)/(50) = 83333.3 mm3
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 50, h: 100 }) });
  var Sx = (50 * Math.pow(100, 3) / 12) / 50;
  check(geom.Sx, Sx, 1e-6, 'F1: Sx de rect 50x100mm');
  var cap = Design.flexureCapacity(geom, Fy);
  check(cap.Mn, Fy * Sx, 1e-9, 'F1: Mn = Fy*Sx');
})();

// ---------------------------------------------------------------
// Caso G1: corte, zona 1 (Cv=1, h/tw bajo) -- seccion solida (kv=null) siempre Cv=1
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 50, h: 100 }) });
  var cap = Design.shearCapacity(geom, Fy, E);
  check(cap.Cv, 1, 1e-12, 'G1: seccion solida -> Cv=1 siempre (sin pandeo de alma)');
  check(cap.Vn, 0.6 * Fy * (50 * 100), 1e-9, 'G1: Vn = 0.6*Fy*Aw para seccion solida (Aw=A)');
})();

// ---------------------------------------------------------------
// Caso G2: corte, perfil con alma delgada (kv=5) -- las 3 zonas de Cv
// Verifica que la zona 1 (Cv=1) se aplique exactamente en su limite,
// y que la zona 2 de la formula reproduzca el calculo a mano.
// ---------------------------------------------------------------
(function () {
  var kv = 5;
  var lim1 = 1.10 * Math.sqrt((kv * E) / Fy);
  var lim2 = 1.37 * Math.sqrt((kv * E) / Fy);

  check(Design.shearCv(lim1 - 1, 1, kv, Fy, E), 1, 1e-9, 'G2: justo bajo el limite 1 -> Cv=1');
  check(Design.shearCv(lim1, 1, kv, Fy, E), 1, 1e-9, 'G2: exactamente en el limite 1 -> Cv=1');

  var ratioZona2 = (lim1 + lim2) / 2;
  var CvEsperadoZona2 = lim1 / ratioZona2;
  check(Design.shearCv(ratioZona2, 1, kv, Fy, E), CvEsperadoZona2, 1e-9, 'G2: zona 2 (transicion), Cv=1.10*sqrt(kvE/Fy)/(h/tw)');

  var ratioZona3 = lim2 * 2;
  var CvEsperadoZona3 = (1.51 * kv * E) / (ratioZona3 * ratioZona3 * Fy);
  check(Design.shearCv(ratioZona3, 1, kv, Fy, E), CvEsperadoZona3, 1e-9, 'G2: zona 3 (alma muy esbelta), Cv=1.51*kv*E/((h/tw)^2*Fy)');
})();

// ---------------------------------------------------------------
// Caso H1: interaccion flexo-compresion -- casos limite triviales
// ---------------------------------------------------------------
(function () {
  var geom = Design.sectionGeometry({ section: new FEM.Section('rect', { b: 100, h: 100 }) });
  var tensionCap = Design.tensionCapacity(geom, Fy);
  var compCap = Design.compressionCapacity(geom, Fy, E, 2000);
  var flexCap = Design.flexureCapacity(geom, Fy);

  // Solo flexion (N=0): axialRatio=0 < 0.2 -> rama H1-1b -> dcr = 0/2 + flexRatio = flexRatio
  var M = flexCap.phiMn * 0.5;
  var inter1 = Design.interactionRatio(0, M, tensionCap, compCap, flexCap);
  check(inter1.dcr, 0.5, 1e-9, 'H1: solo flexion (N=0) -> dcr = flexRatio exacto');

  // Solo compresion (M=0), con axialRatio >= 0.2: dcr = axialRatio + (8/9)*0 = axialRatio
  var Pcomp = -compCap.phiPn * 0.6; // compresion (N<0), ratio 0.6 >= 0.2
  var inter2 = Design.interactionRatio(Pcomp, 0, tensionCap, compCap, flexCap);
  check(inter2.dcr, 0.6, 1e-9, 'H1: solo compresion (M=0, ratio>=0.2) -> dcr = axialRatio exacto');

  // Solo traccion (M=0): dcr = axialRatio + 0 = axialRatio (forma simplificada, ver cabecera)
  var Ptrac = tensionCap.phiPn * 0.4;
  var inter3 = Design.interactionRatio(Ptrac, 0, tensionCap, compCap, flexCap);
  check(inter3.dcr, 0.4, 1e-9, 'H1: solo traccion (M=0) -> dcr = axialRatio exacto');
})();

// ---------------------------------------------------------------
// Caso M1: integracion checkMember() contra un caso ya validado en
// tests/validation.js (Caso1: viga simplemente apoyada, P al centro).
// Mmax = P*L/4 conocido -> se verifica que el DCR de flexion en checkMember
// coincide con Mmax/phiMn calculado a mano, y que lo encuentra en x=L/2.
// ---------------------------------------------------------------
(function () {
  var L = 4000, P = 10000; // mm, N
  var section = new FEM.Section('rect', { b: 50, h: 100 });
  var model = new FEM.Model();
  // El solver no soporta carga puntual a mitad de barra -- se divide en dos
  // elementos con un nodo central y se aplica la carga ahi, igual que se
  // haria en la UI real.
  var a = model.addNode(0, 0);
  var mid = model.addNode(L / 2, 0);
  var b2 = model.addNode(L, 0);
  a.restraint = FEM.RESTRAINT.PINNED;
  b2.restraint = FEM.RESTRAINT.ROLLER_X; // restringe vertical, deja mover horizontal (rodillo clasico)
  var el1 = model.addElement(a, mid, E, section);
  var el2 = model.addElement(mid, b2, E, section);
  model.addNodalLoad(mid.id, 0, -P, 0);

  var result = FEM.solver.solve(model);
  var ef1 = result.elementForces.get(el1.id);

  var geom = Design.sectionGeometry({ section: section });
  var flexCap = Design.flexureCapacity(geom, Fy);
  var Mmax = (P * L) / 4;
  var checkResult = Design.checkMember({ section: section, catalogRef: null, length: function () { return L / 2; } }, ef1, FEM.solver, Fy, E, 40);

  check(Math.abs(checkResult.worst.M), Mmax, 1e-2, 'M1: checkMember encuentra Mmax=PL/4 en el tramo con momento maximo');
  check(checkResult.worst.interaction.flexRatio, Mmax / flexCap.phiMn, 1e-2, 'M1: DCR de flexion coincide con Mmax/phiMn calculado a mano');
})();

console.log('');
if (failures > 0) {
  console.log(failures + ' verificacion(es) fallaron.');
  process.exit(1);
} else {
  console.log('Todas las verificaciones pasaron.');
}
