/**
 * Ensamblaje, condiciones de borde, solucion y recuperacion de
 * fuerzas internas para un modelo de portico plano 2D.
 *
 * Todo en unidades internas (mm, N, N*mm, MPa). Ver units.js para la
 * conversion a/desde las unidades que ve el usuario en la UI.
 */
(function (root) {
  'use strict';

  var FEM = root.FEM;
  var fe = FEM.frameElement;
  var linalg = FEM.linalg;

  function elementDofMap(model, element) {
    var i = model.dofIndex(element.nodeI.id);
    var j = model.dofIndex(element.nodeJ.id);
    return [i, i + 1, i + 2, j, j + 1, j + 2];
  }

  /**
   * Resuelve el modelo. Lanza Error si la estructura es inestable
   * (matriz singular: faltan apoyos / mecanismo) o si no hay nodos.
   *
   * @returns {{
   *   displacements: Map<nodeId, {ux,uy,rz}>,
   *   reactions: Map<nodeId, {fx,fy,m}>,
   *   elementForces: Map<elementId, {N1,V1,M1,N2,V2,M2,L,angle}>
   * }}
   */
  function solve(model) {
    if (model.nodes.length === 0) {
      throw new Error('El modelo no tiene nodos.');
    }
    var n = model.dofCount();
    var K = linalg.zeros(n, n);
    var F = new Array(n).fill(0);

    var elemData = []; // cache por elemento: {L, angle, T, kLocal, dofMap}

    model.elements.forEach(function (el) {
      var L = el.length();
      if (L <= 0) throw new Error('Elemento ' + el.id + ' tiene longitud cero.');
      var angle = el.angle();
      var props = el.section.properties();
      var kLocal = fe.localStiffness(el.E, props.A, props.I, L);
      var T = fe.transformMatrix(angle);
      var kGlobal = fe.globalStiffness(kLocal, T);
      var dofMap = elementDofMap(model, el);

      for (var a = 0; a < 6; a++) {
        for (var b = 0; b < 6; b++) {
          K[dofMap[a]][dofMap[b]] += kGlobal[a][b];
        }
      }

      if (el.udl) {
        var fEqLocal = fe.udlEquivalentLoadLocal(el.udl, L);
        var fEqGlobal = fe.matVec(fe.transpose(T), fEqLocal);
        for (var c = 0; c < 6; c++) {
          F[dofMap[c]] += fEqGlobal[c];
        }
      }

      elemData.push({ element: el, L: L, angle: angle, T: T, kLocal: kLocal, dofMap: dofMap });
    });

    model.nodalLoads.forEach(function (load) {
      var idx = model.dofIndex(load.nodeId);
      F[idx] += load.fx;
      F[idx + 1] += load.fy;
      F[idx + 2] += load.m;
    });

    // Particion en GDL libres / restringidos (apoyos). No se soportan
    // desplazamientos prescritos no nulos en esta version.
    var restrained = new Array(n).fill(false);
    model.nodes.forEach(function (node, i) {
      var base = i * 3;
      restrained[base] = !!node.restraint.ux;
      restrained[base + 1] = !!node.restraint.uy;
      restrained[base + 2] = !!node.restraint.rz;
    });

    var freeIdx = [];
    for (var idx = 0; idx < n; idx++) if (!restrained[idx]) freeIdx.push(idx);

    if (freeIdx.length === 0) {
      throw new Error('Todos los grados de libertad estan restringidos; no hay nada que resolver.');
    }

    var Kff = linalg.zeros(freeIdx.length, freeIdx.length);
    var Ff = new Array(freeIdx.length).fill(0);
    for (var r = 0; r < freeIdx.length; r++) {
      Ff[r] = F[freeIdx[r]];
      for (var cI = 0; cI < freeIdx.length; cI++) {
        Kff[r][cI] = K[freeIdx[r]][freeIdx[cI]];
      }
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

    // Reacciones: R = K*D - F_aplicado, evaluado en todos los GDL
    // (debe ser ~0 en los GDL libres; es la reaccion real en los restringidos).
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
      var base = i * 3;
      displacements.set(node.id, { ux: D[base], uy: D[base + 1], rz: D[base + 2] });
      reactions.set(node.id, { fx: R[base], fy: R[base + 1], m: R[base + 2] });
    });

    var elementForces = new Map();
    elemData.forEach(function (ed) {
      var el = ed.element;
      var dGlobal = ed.dofMap.map(function (gi) { return D[gi]; });
      var dLocal = fe.matVec(ed.T, dGlobal);
      var fLocal = fe.matVec(ed.kLocal, dLocal);
      if (el.udl) {
        var fEqRecover = fe.udlEquivalentLoadLocal(el.udl, ed.L);
        fLocal = fLocal.map(function (v, i2) { return v - fEqRecover[i2]; });
      }
      elementForces.set(el.id, {
        N1: fLocal[0], V1: fLocal[1], M1: fLocal[2],
        N2: fLocal[3], V2: fLocal[4], M2: fLocal[5],
        u1: dLocal[0], v1: dLocal[1], t1: dLocal[2],
        u2: dLocal[3], v2: dLocal[4], t2: dLocal[5],
        L: ed.L, angle: ed.angle, udl: el.udl, E: el.E,
        I: el.section.properties().I
      });
    });

    return { displacements: displacements, reactions: reactions, elementForces: elementForces };
  }

  /**
   * Evalua N(x), V(x), M(x) en coordenada local x in [0, L] de un elemento,
   * a partir del resultado de solve() para ese elemento.
   */
  function internalForcesAt(ef, x) {
    var w = ef.udl || 0;
    // Convencion: N, V, M expuestos en el corte del tramo izquierdo [0,x],
    // apuntando en el sentido positivo de los ejes locales (+x, +y, CCW).
    // Equilibrio del tramo izquierdo: N1 - N(x) = 0; V1 - w*x - V(x) = 0;
    // M1 + V1*x - w*x^2/2 - M(x) = 0. N positivo = traccion.
    var N = ef.N1;
    var V = ef.V1 - w * x;
    var M = ef.M1 + ef.V1 * x - (w * x * x) / 2;
    return { N: N, V: V, M: M };
  }

  /**
   * Deflexion transversal local v(x), x in [0,L], por integracion analitica
   * de EI*v''(x) = M(x) con condiciones iniciales v(0)=v1, v'(0)=theta1
   * (ambas conocidas exactamente de la solucion nodal). Teoria de
   * Euler-Bernoulli (sin deformacion por corte).
   */
  function deflectionAt(ef, x) {
    var w = ef.udl || 0;
    var EI = ef.E * ef.I;
    var v = ef.v1 + ef.t1 * x +
      (1 / EI) * (ef.M1 * x * x / 2 + ef.V1 * x * x * x / 6 - (w * Math.pow(x, 4)) / 24);
    return v;
  }

  root.FEM.solver = {
    solve: solve,
    internalForcesAt: internalForcesAt,
    deflectionAt: deflectionAt,
    elementDofMap: elementDofMap
  };
})(typeof window !== 'undefined' ? window : global);
