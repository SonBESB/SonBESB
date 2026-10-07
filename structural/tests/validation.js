/**
 * Suite de validacion del solver de porticos 2D contra formulas cerradas
 * de libro (Hibbeler / Timoshenko) y contra identidades de resistencia de
 * materiales. No es un test exhaustivo de UI, solo del nucleo de calculo
 * (js/linalg.js, js/frameElement.js, js/solver.js, js/stress.js).
 *
 * Correr con: node structural/tests/validation.js
 * Sale con codigo 1 si alguna verificacion falla.
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

var FEM = global.FEM;
var failures = 0;

function check(got, expected, tol, label) {
  var rel = Math.abs(got - expected) / Math.max(1, Math.abs(expected));
  var ok = rel < tol;
  if (!ok) failures++;
  console.log((ok ? 'OK  ' : 'FAIL') + ' ' + label +
    ': got=' + got.toFixed(6) + ' expected=' + expected.toFixed(6) +
    ' rel_err=' + rel.toExponential(3));
}

function makeRectModel() {
  var E = 200000; // MPa (acero)
  var section = new FEM.Section('rect', { b: 50, h: 100 }); // mm
  return { E: E, section: section, I: section.properties().I, A: section.properties().A };
}

// ---------------------------------------------------------------
// Caso 1: viga simplemente apoyada, carga puntual P en el centro.
// M_max = P*L/4 (en el centro). Deflexion en el centro = P*L^3/(48*E*I).
// ---------------------------------------------------------------
(function caso1() {
  var mat = makeRectModel();
  var model = new FEM.Model();
  var L = 4000, P = 10000; // mm, N

  var n1 = model.addNode(0, 0);
  var n2 = model.addNode(L / 2, 0);
  var n3 = model.addNode(L, 0);
  n1.restraint = { ux: true, uy: true, rz: false };
  n3.restraint = { ux: false, uy: true, rz: false };

  model.addElement(n1, n2, mat.E, mat.section);
  var elB = model.addElement(n2, n3, mat.E, mat.section);
  model.addNodalLoad(n2.id, 0, -P, 0);

  var result = FEM.solver.solve(model);

  check(-result.displacements.get(n2.id).uy, (P * Math.pow(L, 3)) / (48 * mat.E * mat.I), 1e-6,
    'Caso1 (SS + P centro): deflexion en el centro');

  var efA = result.elementForces.get(model.elements[0].id);
  var mMid = FEM.solver.internalForcesAt(efA, efA.L).M;
  check(Math.abs(mMid), (P * L) / 4, 1e-6, 'Caso1: momento maximo en el centro');

  check(result.reactions.get(n1.id).fy, P / 2, 1e-6, 'Caso1: reaccion apoyo izquierdo');
  check(result.reactions.get(n3.id).fy, P / 2, 1e-6, 'Caso1: reaccion apoyo derecho');

  void elB;
})();

// ---------------------------------------------------------------
// Caso 2: voladizo (empotrado-libre) con carga puntual P en el extremo.
// M_max = P*L (en el empotramiento). Deflexion en el extremo = P*L^3/(3*E*I).
// ---------------------------------------------------------------
(function caso2() {
  var mat = makeRectModel();
  var model = new FEM.Model();
  var L = 3000, P = 5000;

  var n1 = model.addNode(0, 0);
  var n2 = model.addNode(L, 0);
  n1.restraint = { ux: true, uy: true, rz: true };

  model.addElement(n1, n2, mat.E, mat.section);
  model.addNodalLoad(n2.id, 0, -P, 0);

  var result = FEM.solver.solve(model);

  check(-result.displacements.get(n2.id).uy, (P * Math.pow(L, 3)) / (3 * mat.E * mat.I), 1e-6,
    'Caso2 (voladizo + P extremo): deflexion en el extremo libre');

  var ef = result.elementForces.get(model.elements[0].id);
  check(Math.abs(FEM.solver.internalForcesAt(ef, 0).M), P * L, 1e-6,
    'Caso2: momento maximo en el empotramiento');
  check(result.reactions.get(n1.id).fy, P, 1e-6, 'Caso2: reaccion vertical en el empotramiento');
})();

// ---------------------------------------------------------------
// Caso 3: viga simplemente apoyada con carga distribuida uniforme w.
// M_max = w*L^2/8 (centro). Deflexion en el centro = 5*w*L^4/(384*E*I).
// ---------------------------------------------------------------
(function caso3() {
  var mat = makeRectModel();
  var model = new FEM.Model();
  var L = 4000, w = 5; // mm, N/mm (= 5 kN/m)

  var n1 = model.addNode(0, 0);
  var n2 = model.addNode(L, 0);
  n1.restraint = { ux: true, uy: true, rz: false };
  n2.restraint = { ux: false, uy: true, rz: false };

  var el = model.addElement(n1, n2, mat.E, mat.section);
  el.udl = w;

  var result = FEM.solver.solve(model);
  var ef = result.elementForces.get(el.id);

  check(Math.abs(FEM.solver.internalForcesAt(ef, L / 2).M), (w * L * L) / 8, 1e-6,
    'Caso3 (SS + UDL): momento maximo en el centro');
  check(result.reactions.get(n1.id).fy, (w * L) / 2, 1e-6, 'Caso3: reaccion apoyo izquierdo');
  check(result.reactions.get(n2.id).fy, (w * L) / 2, 1e-6, 'Caso3: reaccion apoyo derecho');
  check(-FEM.solver.deflectionAt(ef, L / 2), (5 * w * Math.pow(L, 4)) / (384 * mat.E * mat.I), 1e-6,
    'Caso3: deflexion en el centro (integracion analitica de M/EI)');
  check(Math.abs(FEM.solver.deflectionAt(ef, L)), 0, 1e-6,
    'Caso3: consistencia v(L) con el extremo restringido (~0)');
})();

// ---------------------------------------------------------------
// Caso 4: identidades de tension (independientes del solver de porticos).
// sigma = M*c/I en fibra extrema; tau_max = 1.5*V/A (rect) y 4*V/(3*A) (circulo).
// ---------------------------------------------------------------
(function caso4() {
  var section = new FEM.Section('rect', { b: 50, h: 100 });
  var props = section.properties();
  var M = 10000000, V = 5000;

  var top = FEM.stress.stressAt(section, 0, M, V, props.c);
  var bot = FEM.stress.stressAt(section, 0, M, V, -props.c);
  check(-top.sigma, (M * props.c) / props.I, 1e-9, 'Caso4: compresion en fibra superior = M*c/I');
  check(bot.sigma, (M * props.c) / props.I, 1e-9, 'Caso4: traccion en fibra inferior = M*c/I');

  var neutral = FEM.stress.stressAt(section, 0, 0, V, 0);
  check(neutral.tau, 1.5 * V / props.A, 1e-9, 'Caso4: tau maximo rectangular = 1.5*V/A');
  check(neutral.vonMises, Math.sqrt(3) * neutral.tau, 1e-9,
    'Caso4: von Mises en corte puro = sqrt(3)*tau');

  var sectionC = new FEM.Section('circle', { d: 100 });
  var propsC = sectionC.properties();
  var neutralC = FEM.stress.stressAt(sectionC, 0, 0, V, 0);
  check(neutralC.tau, (4 * V) / (3 * propsC.A), 1e-9, 'Caso4: tau maximo circular = 4V/(3A)');
})();

console.log('');
if (failures > 0) {
  console.log(failures + ' verificacion(es) fallaron.');
  process.exit(1);
} else {
  console.log('Todas las verificaciones pasaron.');
}
