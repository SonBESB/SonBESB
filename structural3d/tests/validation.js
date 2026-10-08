/**
 * Suite de validacion del solver de porticos 3D contra formulas cerradas
 * de resistencia de materiales. Nucleo de calculo: js/linalg.js,
 * js/frameElement.js, js/solver.js, js/stress.js.
 *
 * Correr con: node structural3d/tests/validation.js
 * Sale con codigo 1 si alguna verificacion falla.
 *
 * Durante el desarrollo esta suite detecto y permitio corregir:
 *  - Un bug de restricciones (torsion sin restringir en ningun nodo del
 *    modelo de prueba => mecanismo real, no bug del solver).
 *  - Dos errores de signo reales en la integracion de la deflexion w(x)
 *    (eje debil / flexion en y): primero un signo global de mas, luego
 *    la condicion inicial de pendiente w'(0) que debia ser -ry1 y no
 *    +ry1 (por la convencion de ejes locales right-handed usada aqui,
 *    theta_y = -dw/dx, al reves que theta_z = +dv/dx).
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

var FEM3D = global.FEM3D;
var failures = 0;

function check(got, expected, tol, label) {
  var rel = Math.abs(got - expected) / Math.max(1, Math.abs(expected));
  var ok = rel < tol;
  if (!ok) failures++;
  console.log((ok ? 'OK  ' : 'FAIL') + ' ' + label +
    ': got=' + got.toFixed(6) + ' expected=' + expected.toFixed(6) +
    ' rel_err=' + rel.toExponential(3));
}

var E = 200000, G = 77000; // MPa (acero aprox, G=E/(2*(1+nu)), nu~0.3)
var section = new FEM3D.Section('rect', { b: 50, h: 100 }); // b=y, h=z
var props = section.properties();

// ---------------------------------------------------------------
// Caso 1: voladizo horizontal (eje X), carga puntual P en -Y en el extremo
// (flexion sobre z, usa Iz). M_max=PL, deflexion=PL^3/3EIz.
// ---------------------------------------------------------------
(function caso1() {
  var model = new FEM3D.Model();
  var L = 3000, P = 5000;
  var n1 = model.addNode(0, 0, 0), n2 = model.addNode(L, 0, 0);
  n1.restraint = { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true };
  var el = model.addElement(n1, n2, E, G, section);
  model.addNodalLoad(n2.id, 0, -P, 0, 0, 0, 0);

  var result = FEM3D.solver.solve(model);
  var ef = result.elementForces.get(el.id);

  check(-result.displacements.get(n2.id).uy, (P * Math.pow(L, 3)) / (3 * E * props.Iz), 1e-6,
    'Caso1 (voladizo, P en Y, eje fuerte): deflexion en el extremo');
  check(Math.abs(FEM3D.solver.internalForcesAt(ef, 0).Mz), P * L, 1e-6,
    'Caso1: |Mz| en el empotramiento');
  check(result.reactions.get(n1.id).fy, P, 1e-6, 'Caso1: reaccion Fy');
})();

// ---------------------------------------------------------------
// Caso 2: voladizo horizontal, carga puntual P en -Z en el extremo
// (flexion sobre y, usa Iy — eje con signos invertidos en la matriz).
// ---------------------------------------------------------------
(function caso2() {
  var model = new FEM3D.Model();
  var L = 3000, P = 5000;
  var n1 = model.addNode(0, 0, 0), n2 = model.addNode(L, 0, 0);
  n1.restraint = { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true };
  var el = model.addElement(n1, n2, E, G, section);
  model.addNodalLoad(n2.id, 0, 0, -P, 0, 0, 0);

  var result = FEM3D.solver.solve(model);
  var ef = result.elementForces.get(el.id);

  check(-result.displacements.get(n2.id).uz, (P * Math.pow(L, 3)) / (3 * E * props.Iy), 1e-6,
    'Caso2 (voladizo, P en Z, eje debil): deflexion en el extremo');
  check(Math.abs(FEM3D.solver.internalForcesAt(ef, 0).My), P * L, 1e-6,
    'Caso2: |My| en el empotramiento');
  check(result.reactions.get(n1.id).fz, P, 1e-6, 'Caso2: reaccion Fz');
})();

// ---------------------------------------------------------------
// Caso 3: voladizo con torque puro T en el extremo. Giro=TL/GJ.
// ---------------------------------------------------------------
(function caso3() {
  var model = new FEM3D.Model();
  var L = 2000, Tq = 2000000; // N*mm
  var n1 = model.addNode(0, 0, 0), n2 = model.addNode(L, 0, 0);
  n1.restraint = { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true };
  var circSection = new FEM3D.Section('circle', { d: 100 });
  var cProps = circSection.properties();
  var el = model.addElement(n1, n2, E, G, circSection);
  model.addNodalLoad(n2.id, 0, 0, 0, Tq, 0, 0);

  var result = FEM3D.solver.solve(model);
  check(result.displacements.get(n2.id).rx, (Tq * L) / (G * cProps.J), 1e-6,
    'Caso3 (torsion pura): giro en el extremo libre');
  check(Math.abs(result.reactions.get(n1.id).mx), Tq, 1e-6, 'Caso3: reaccion Mx');
})();

// ---------------------------------------------------------------
// Caso 4 y 5: viga simplemente apoyada (eje X) con UDL en -Y / -Z.
// rx restringido en nodo1 para evitar el mecanismo de giro libre sobre el
// eje de la barra (sin eso, el modelo es inestable: nada restringe la
// rotacion de cuerpo rigido alrededor de x si no hay torque aplicado).
// M_max=wL^2/8, deflexion centro=5wL^4/384EI.
// ---------------------------------------------------------------
(function caso4() {
  var model = new FEM3D.Model();
  var L = 4000, w = 5;
  var n1 = model.addNode(0, 0, 0), n2 = model.addNode(L, 0, 0);
  n1.restraint = { ux: true, uy: true, uz: true, rx: true, ry: false, rz: false };
  n2.restraint = { ux: false, uy: true, uz: true, rx: false, ry: false, rz: false };
  var el = model.addElement(n1, n2, E, G, section);
  el.udlY = w;

  var result = FEM3D.solver.solve(model);
  var ef = result.elementForces.get(el.id);

  check(Math.abs(FEM3D.solver.internalForcesAt(ef, L / 2).Mz), (w * L * L) / 8, 1e-6,
    'Caso4 (SS+UDL en Y): |Mz| maximo en el centro');
  check(result.reactions.get(n1.id).fy, (w * L) / 2, 1e-6, 'Caso4: reaccion apoyo 1');
  check(result.reactions.get(n2.id).fy, (w * L) / 2, 1e-6, 'Caso4: reaccion apoyo 2');
  check(-FEM3D.solver.deflectionAt(ef, L / 2).v, (5 * w * Math.pow(L, 4)) / (384 * E * props.Iz), 1e-6,
    'Caso4: deflexion en Y en el centro');
})();

(function caso5() {
  var model = new FEM3D.Model();
  var L = 4000, w = 5;
  var n1 = model.addNode(0, 0, 0), n2 = model.addNode(L, 0, 0);
  n1.restraint = { ux: true, uy: true, uz: true, rx: true, ry: false, rz: false };
  n2.restraint = { ux: false, uy: true, uz: true, rx: false, ry: false, rz: false };
  var el = model.addElement(n1, n2, E, G, section);
  el.udlZ = w;

  var result = FEM3D.solver.solve(model);
  var ef = result.elementForces.get(el.id);

  check(Math.abs(FEM3D.solver.internalForcesAt(ef, L / 2).My), (w * L * L) / 8, 1e-6,
    'Caso5 (SS+UDL en Z): |My| maximo en el centro');
  check(result.reactions.get(n1.id).fz, (w * L) / 2, 1e-6, 'Caso5: reaccion apoyo 1 (Fz)');
  check(result.reactions.get(n2.id).fz, (w * L) / 2, 1e-6, 'Caso5: reaccion apoyo 2 (Fz)');
  check(-FEM3D.solver.deflectionAt(ef, L / 2).w, (5 * w * Math.pow(L, 4)) / (384 * E * props.Iy), 1e-6,
    'Caso5: deflexion en Z en el centro');
})();

// ---------------------------------------------------------------
// Caso 6: orientacion de ejes locales para barra horizontal a lo largo de
// X (referencia por defecto = global Z): local y debe coincidir con
// global Y, local z con global Z.
// ---------------------------------------------------------------
(function caso6() {
  var n1 = { x: 0, y: 0, z: 0 };
  var n2 = { x: 1000, y: 0, z: 0 };
  var axes = FEM3D.frameElement.localAxes(n1, n2, 0);
  check(axes.ey[1], 1, 1e-9, 'Caso6: eje local y == global Y (barra horizontal en X)');
  check(axes.ez[2], 1, 1e-9, 'Caso6: eje local z == global Z (barra horizontal en X)');
})();

// ---------------------------------------------------------------
// Caso 7: identidades de tension (independientes del solver de porticos).
// ---------------------------------------------------------------
(function caso7() {
  var Mz = 10000000, My = 8000000, Vy = 5000, Vz = 4000;
  var sTop = FEM3D.stress.stressAt(section, 0, 0, Mz, 0, 0, 0, props.cy, 0);
  check(-sTop.sigma, (Mz * props.cy) / props.Iz, 1e-9, 'Caso7: sigma por Mz en fibra extrema (y)');
  var sTopY = FEM3D.stress.stressAt(section, 0, My, 0, 0, 0, 0, 0, props.cz);
  check(-sTopY.sigma, (My * props.cz) / props.Iy, 1e-9, 'Caso7: sigma por My en fibra extrema (z)');

  var sNeutralY = FEM3D.stress.stressAt(section, 0, 0, 0, Vy, 0, 0, 0, 0);
  check(sNeutralY.txy, 1.5 * Vy / props.A, 1e-9, 'Caso7: tau_xy maximo rectangular = 1.5*Vy/A');
  var sNeutralZ = FEM3D.stress.stressAt(section, 0, 0, 0, 0, Vz, 0, 0, 0);
  check(sNeutralZ.txz, 1.5 * Vz / props.A, 1e-9, 'Caso7: tau_xz maximo rectangular = 1.5*Vz/A');

  var circ = new FEM3D.Section('circle', { d: 100 });
  var pc = circ.properties();
  var sC = FEM3D.stress.stressAt(circ, 0, 0, 0, Vy, 0, 0, 0, 0);
  check(sC.txy, (4 * Vy) / (3 * pc.A), 1e-9, 'Caso7: tau_xy maximo circular = 4Vy/3A');

  var T = 3000000;
  var sT = FEM3D.stress.stressAt(circ, 0, 0, 0, 0, 0, T, pc.R, 0);
  check(Math.abs(sT.txz), (T * pc.R) / pc.J, 1e-9, 'Caso7: tau de torsion circular en el borde');
  check(sT.vonMises, Math.sqrt(3) * Math.abs(sT.txz), 1e-9, 'Caso7: von Mises en torsion pura = sqrt(3)*tau');

  var sq = new FEM3D.Section('rect', { b: 100, h: 100 });
  var tmax = FEM3D.stress.torsionShearMax(sq, T);
  check(tmax, T / (0.208 * 100 * 100 * 100), 0.01, 'Caso7: torsion max rectangular cuadrado (tabla Roark alpha=0.208)');
})();

console.log('');
if (failures > 0) {
  console.log(failures + ' verificacion(es) fallaron.');
  process.exit(1);
} else {
  console.log('Todas las verificaciones pasaron.');
}
