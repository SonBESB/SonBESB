/**
 * Elemento de portico plano (2D), teoria de viga de Euler-Bernoulli.
 * 3 GDL por nodo: [u (axial local), v (transversal local), theta (giro)].
 * 6 GDL por elemento, orden: [u1, v1, t1, u2, v2, t2].
 *
 * Convencion de signos local:
 *   - eje x local: de nodo I a nodo J.
 *   - eje y local: 90 grados antihorario desde x local (mano derecha, z hacia afuera).
 *   - momento positivo: antihorario.
 *   - carga distribuida uniforme element.udl: positiva = sentido -y local
 *     (ver model.js).
 *
 * Estas convenciones se fijan arbitrariamente aqui; lo que importa es que
 * sean internamente consistentes, y eso se verifica en tests/validation.js
 * contra formulas cerradas de libro (viga simplemente apoyada, voladizo).
 */
(function (root) {
  'use strict';

  var FEM = root.FEM;
  var zeros = FEM.linalg.zeros;

  /** Matriz de rigidez local 6x6 (Euler-Bernoulli). */
  function localStiffness(E, A, I, L) {
    var k = zeros(6, 6);
    var EAL = (E * A) / L;
    var c1 = (E * I) / (L * L * L);

    k[0][0] = EAL; k[0][3] = -EAL;
    k[3][0] = -EAL; k[3][3] = EAL;

    k[1][1] = 12 * c1; k[1][2] = 6 * L * c1; k[1][4] = -12 * c1; k[1][5] = 6 * L * c1;
    k[2][1] = 6 * L * c1; k[2][2] = 4 * L * L * c1; k[2][4] = -6 * L * c1; k[2][5] = 2 * L * L * c1;
    k[4][1] = -12 * c1; k[4][2] = -6 * L * c1; k[4][4] = 12 * c1; k[4][5] = -6 * L * c1;
    k[5][1] = 6 * L * c1; k[5][2] = 2 * L * L * c1; k[5][4] = -6 * L * c1; k[5][5] = 4 * L * L * c1;

    return k;
  }

  /** Matriz de transformacion 6x6 local<->global para angulo dado (rad). */
  function transformMatrix(angleRad) {
    var c = Math.cos(angleRad);
    var s = Math.sin(angleRad);
    var T = zeros(6, 6);
    T[0][0] = c; T[0][1] = s;
    T[1][0] = -s; T[1][1] = c;
    T[2][2] = 1;
    T[3][3] = c; T[3][4] = s;
    T[4][3] = -s; T[4][4] = c;
    T[5][5] = 1;
    return T;
  }

  function matMul(A, B) {
    var n = A.length, m = B[0].length, p = B.length;
    var C = zeros(n, m);
    for (var i = 0; i < n; i++) {
      for (var j = 0; j < m; j++) {
        var sum = 0;
        for (var k = 0; k < p; k++) sum += A[i][k] * B[k][j];
        C[i][j] = sum;
      }
    }
    return C;
  }

  function transpose(A) {
    var n = A.length, m = A[0].length;
    var T = zeros(m, n);
    for (var i = 0; i < n; i++) for (var j = 0; j < m; j++) T[j][i] = A[i][j];
    return T;
  }

  function matVec(A, v) {
    var n = A.length, m = A[0].length;
    var r = new Array(n).fill(0);
    for (var i = 0; i < n; i++) {
      var sum = 0;
      for (var j = 0; j < m; j++) sum += A[i][j] * v[j];
      r[i] = sum;
    }
    return r;
  }

  /** k_global = T^T * k_local * T */
  function globalStiffness(kLocal, T) {
    var Tt = transpose(T);
    return matMul(matMul(Tt, kLocal), T);
  }

  /**
   * Vector de carga nodal equivalente (local) para UDL transversal uniforme.
   * w: magnitud positiva = sentido -y local (ver convencion arriba).
   * Resultado en coordenadas locales, orden [Fx1, Fy1, M1, Fx2, Fy2, M2],
   * listo para sumarse directamente al vector de cargas globales (luego de
   * rotar con T^T) antes de resolver K*D = F.
   */
  function udlEquivalentLoadLocal(w, L) {
    // w positivo = -y local => carga equivalente consistente (trabajo
    // virtual con las mismas funciones de forma de Hermite usadas en
    // localStiffness), con q = -w en +y local:
    //   Fy = qL/2, M = qL^2/12 (nodo 1); Fy = qL/2, M = -qL^2/12 (nodo 2).
    // Este MISMO vector se usa (a) sumado al vector de cargas global en el
    // ensamblaje y (b) restado al recuperar fuerzas de extremo del elemento
    // (f_extremo = k_local*d_local - F_eq_local). Verificado en
    // tests/validation.js contra viga simplemente apoyada con UDL.
    return [0, -w * L / 2, -w * L * L / 12, 0, -w * L / 2, w * L * L / 12];
  }

  root.FEM.frameElement = {
    localStiffness: localStiffness,
    transformMatrix: transformMatrix,
    globalStiffness: globalStiffness,
    matMul: matMul,
    transpose: transpose,
    matVec: matVec,
    udlEquivalentLoadLocal: udlEquivalentLoadLocal
  };
})(typeof window !== 'undefined' ? window : global);
