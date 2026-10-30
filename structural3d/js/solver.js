/**
 * Ensamblaje, condiciones de borde, solucion y recuperacion de fuerzas
 * internas para un modelo de portico espacial 3D. Unidades internas
 * (mm, N, N*mm, MPa). Ver units.js para la conversion a/desde la UI.
 */
(function (root) {
  'use strict';

  var FEM3D = root.FEM3D;
  var fe = FEM3D.frameElement;
  var linalg = FEM3D.linalg;

  function elementDofMap(model, element) {
    var i = model.dofIndex(element.nodeI.id);
    var j = model.dofIndex(element.nodeJ.id);
    var m = [];
    for (var k = 0; k < 6; k++) m.push(i + k);
    for (k = 0; k < 6; k++) m.push(j + k);
    return m;
  }

  function solve(model) {
    if (model.nodes.length === 0) throw new Error('El modelo no tiene nodos.');
    var n = model.dofCount();
    var K = linalg.zeros(n, n);
    var F = new Array(n).fill(0);
    var elemData = [];

    model.elements.forEach(function (el) {
      var axes = fe.localAxes(el.nodeI, el.nodeJ, el.beta);
      var L = axes.L;
      if (L <= 0) throw new Error('Elemento ' + el.id + ' tiene longitud cero.');
      var props = el.section.properties();
      var kLocal = fe.localStiffness(el.E, el.G, props.A, props.Iy, props.Iz, props.J, L);
      var T = fe.transformMatrix(axes);
      var kGlobal = fe.globalStiffness(kLocal, T);
      var dofMap = elementDofMap(model, el);

      for (var a = 0; a < 12; a++) {
        for (var b = 0; b < 12; b++) K[dofMap[a]][dofMap[b]] += kGlobal[a][b];
      }

      if (el.udlY || el.udlZ) {
        var fEqLocal = fe.udlEquivalentLoadLocal(el.udlY, el.udlZ, L);
        var fEqGlobal = fe.matVec(fe.transpose(T), fEqLocal);
        for (var c = 0; c < 12; c++) F[dofMap[c]] += fEqGlobal[c];
      }

      elemData.push({ element: el, L: L, axes: axes, T: T, kLocal: kLocal, dofMap: dofMap });
    });

    model.nodalLoads.forEach(function (load) {
      var idx = model.dofIndex(load.nodeId);
      F[idx] += load.fx; F[idx + 1] += load.fy; F[idx + 2] += load.fz;
      F[idx + 3] += load.mx; F[idx + 4] += load.my; F[idx + 5] += load.mz;
    });

    var restrained = new Array(n).fill(false);
    model.nodes.forEach(function (node, i) {
      var base = i * 6;
      var r = node.restraint;
      restrained[base] = !!r.ux; restrained[base + 1] = !!r.uy; restrained[base + 2] = !!r.uz;
      restrained[base + 3] = !!r.rx; restrained[base + 4] = !!r.ry; restrained[base + 5] = !!r.rz;
    });

    var freeIdx = [];
    for (var idx = 0; idx < n; idx++) if (!restrained[idx]) freeIdx.push(idx);
    if (freeIdx.length === 0) throw new Error('Todos los grados de libertad estan restringidos; no hay nada que resolver.');

    var Kff = linalg.zeros(freeIdx.length, freeIdx.length);
    var Ff = new Array(freeIdx.length).fill(0);
    for (var r1 = 0; r1 < freeIdx.length; r1++) {
      Ff[r1] = F[freeIdx[r1]];
      for (var c1 = 0; c1 < freeIdx.length; c1++) Kff[r1][c1] = K[freeIdx[r1]][freeIdx[c1]];
    }

    var Df;
    try {
      Df = linalg.solve(Kff, Ff);
    } catch (e) {
      throw new Error(
        'Estructura inestable o con mecanismo (grados de libertad sin ' +
        'restriccion suficiente). Revisa los apoyos. Detalle: ' + e.message
      );
    }

    var D = new Array(n).fill(0);
    freeIdx.forEach(function (gi, r) { D[gi] = Df[r]; });

    var KD = new Array(n).fill(0);
    for (var rr = 0; rr < n; rr++) {
      var sum = 0;
      for (var cc = 0; cc < n; cc++) sum += K[rr][cc] * D[cc];
      KD[rr] = sum;
    }
    var R = KD.map(function (v, i) { return v - F[i]; });

    var displacements = new Map();
    var reactions = new Map();
    model.nodes.forEach(function (node, i) {
      var base = i * 6;
      displacements.set(node.id, {
        ux: D[base], uy: D[base + 1], uz: D[base + 2],
        rx: D[base + 3], ry: D[base + 4], rz: D[base + 5]
      });
      reactions.set(node.id, {
        fx: R[base], fy: R[base + 1], fz: R[base + 2],
        mx: R[base + 3], my: R[base + 4], mz: R[base + 5]
      });
    });

    var elementForces = new Map();
    elemData.forEach(function (ed) {
      var el = ed.element;
      var dGlobal = ed.dofMap.map(function (gi) { return D[gi]; });
      var dLocal = fe.matVec(ed.T, dGlobal);
      var fLocal = fe.matVec(ed.kLocal, dLocal);
      if (el.udlY || el.udlZ) {
        var fEq = fe.udlEquivalentLoadLocal(el.udlY, el.udlZ, ed.L);
        fLocal = fLocal.map(function (v, i2) { return v - fEq[i2]; });
      }
      elementForces.set(el.id, {
        N1: fLocal[0], Vy1: fLocal[1], Vz1: fLocal[2], T1: fLocal[3], My1: fLocal[4], Mz1: fLocal[5],
        N2: fLocal[6], Vy2: fLocal[7], Vz2: fLocal[8], T2: fLocal[9], My2: fLocal[10], Mz2: fLocal[11],
        u1: dLocal[0], v1: dLocal[1], w1: dLocal[2], rx1: dLocal[3], ry1: dLocal[4], rz1: dLocal[5],
        u2: dLocal[6], v2: dLocal[7], w2: dLocal[8], rx2: dLocal[9], ry2: dLocal[10], rz2: dLocal[11],
        L: ed.L, axes: ed.axes, udlY: el.udlY, udlZ: el.udlZ, E: el.E, G: el.G,
        Iy: el.section.properties().Iy, Iz: el.section.properties().Iz
      });
    });

    return { displacements: displacements, reactions: reactions, elementForces: elementForces };
  }

  /**
   * Evalua N(x), Vy(x), Vz(x), T(x), My(x), Mz(x) en coordenada local
   * x in [0,L], a partir del resultado de solve() para ese elemento.
   * Convencion verificada en tests/validation.js.
   */
  function internalForcesAt(ef, x) {
    var qy = ef.udlY || 0, qz = ef.udlZ || 0;
    var N = ef.N1;
    var T = ef.T1;
    var Vy = ef.Vy1 - qy * x;
    var Vz = ef.Vz1 - qz * x;
    var Mz = ef.Mz1 + ef.Vy1 * x - (qy * x * x) / 2;
    var My = ef.My1 - ef.Vz1 * x + (qz * x * x) / 2;
    return { N: N, Vy: Vy, Vz: Vz, T: T, My: My, Mz: Mz };
  }

  /** Deflexion local v(x) (en y) y w(x) (en z), por integracion analitica. */
  function deflectionAt(ef, x) {
    var qy = ef.udlY || 0, qz = ef.udlZ || 0;
    var EIz = ef.E * ef.Iz;
    var EIy = ef.E * ef.Iy;
    var v = ef.v1 + ef.rz1 * x +
      (1 / EIz) * (ef.Mz1 * x * x / 2 + ef.Vy1 * x * x * x / 6 - (qy * Math.pow(x, 4)) / 24);
    // w(x): con el sistema de ejes locales right-handed usado aqui,
    // theta_y = -dw/dx (al reves que theta_z = +dv/dx), por lo que
    // EIy*w'' = -My(x) y la condicion inicial de pendiente es
    // w'(0) = -ry1, no +ry1. Verificado en tests/validation.js (viga
    // simplemente apoyada con UDL en z).
    var w = ef.w1 - ef.ry1 * x +
      (1 / EIy) * (-ef.My1 * x * x / 2 + ef.Vz1 * x * x * x / 6 - (qz * Math.pow(x, 4)) / 24);
    return { v: v, w: w };
  }

  /**
   * Giro de torsion phi(x) (rad). Sin torque distribuido, el giro es
   * lineal entre los extremos (interpolacion de rx1/rx2, que ya incluyen
   * el efecto de T1 = GJ*(rx2-rx1)/L).
   */
  function twistAt(ef, x) {
    return ef.rx1 + (ef.rx2 - ef.rx1) * (x / ef.L);
  }

  root.FEM3D.solver = {
    solve: solve,
    internalForcesAt: internalForcesAt,
    deflectionAt: deflectionAt,
    twistAt: twistAt,
    elementDofMap: elementDofMap
  };
})(typeof window !== 'undefined' ? window : global);
