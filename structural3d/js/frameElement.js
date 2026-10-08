/**
 * Elemento de portico espacial (3D), teoria de viga de Euler-Bernoulli +
 * torsion de Saint-Venant. 6 GDL por nodo: [u,v,w (traslaciones locales),
 * rx,ry,rz (rotaciones locales)]. 12 GDL por elemento, orden:
 * [u1,v1,w1,rx1,ry1,rz1, u2,v2,w2,rx2,ry2,rz2].
 *
 * Convencion de ejes locales:
 *   - x local: de nodo I a nodo J.
 *   - y local, z local: perpendiculares, definidos por un vector de
 *     referencia "arriba" (global Z, o global X si la barra es vertical),
 *     mas un angulo opcional "beta" (grados) de rotacion alrededor de x
 *     local (ver localAxes()).
 *   - Flexion sobre z local -> desplazamiento en y local (igual forma que
 *     el elemento 2D de structural/js/frameElement.js, usando Iz).
 *   - Flexion sobre y local -> desplazamiento en z local, usando Iy (bloque
 *     con signos distintos por la regla de la mano derecha — ver mas abajo).
 *   - Carga distribuida element.udlY / udlZ: positiva = sentido local +y / +z.
 *
 * Todo esto se fija aqui de forma interna y se verifica en
 * tests/validation.js contra formulas cerradas de libro (voladizo con
 * flexion en eje fuerte, eje debil, y torsion pura).
 */
(function (root) {
  'use strict';

  var FEM3D = root.FEM3D;
  var zeros = FEM3D.linalg.zeros;

  /** Matriz de rigidez local 12x12 (Euler-Bernoulli + torsion). */
  function localStiffness(E, G, A, Iy, Iz, J, L) {
    var k = zeros(12, 12);
    var EAL = (E * A) / L;
    var GJL = (G * J) / L;

    // Axial: u1=0, u2=6
    k[0][0] = EAL; k[0][6] = -EAL;
    k[6][0] = -EAL; k[6][6] = EAL;

    // Torsion: rx1=3, rx2=9
    k[3][3] = GJL; k[3][9] = -GJL;
    k[9][3] = -GJL; k[9][9] = GJL;

    // Flexion sobre z (v,rz): v1=1, rz1=5, v2=7, rz2=11 — usa Iz.
    var cz = (E * Iz) / (L * L * L);
    k[1][1] = 12 * cz; k[1][5] = 6 * L * cz; k[1][7] = -12 * cz; k[1][11] = 6 * L * cz;
    k[5][1] = 6 * L * cz; k[5][5] = 4 * L * L * cz; k[5][7] = -6 * L * cz; k[5][11] = 2 * L * L * cz;
    k[7][1] = -12 * cz; k[7][5] = -6 * L * cz; k[7][7] = 12 * cz; k[7][11] = -6 * L * cz;
    k[11][1] = 6 * L * cz; k[11][5] = 2 * L * L * cz; k[11][7] = -6 * L * cz; k[11][11] = 4 * L * L * cz;

    // Flexion sobre y (w,ry): w1=2, ry1=4, w2=8, ry2=10 — usa Iy.
    // Signos en los terminos de acoplamiento corte-momento invertidos
    // respecto al bloque z, por la regla de la mano derecha (ver
    // tests/validation.js, caso de flexion en eje debil).
    var cy = (E * Iy) / (L * L * L);
    k[2][2] = 12 * cy; k[2][4] = -6 * L * cy; k[2][8] = -12 * cy; k[2][10] = -6 * L * cy;
    k[4][2] = -6 * L * cy; k[4][4] = 4 * L * L * cy; k[4][8] = 6 * L * cy; k[4][10] = 2 * L * L * cy;
    k[8][2] = -12 * cy; k[8][4] = 6 * L * cy; k[8][8] = 12 * cy; k[8][10] = 6 * L * cy;
    k[10][2] = -6 * L * cy; k[10][4] = 2 * L * L * cy; k[10][8] = 6 * L * cy; k[10][10] = 4 * L * L * cy;

    return k;
  }

  /**
   * Ejes locales (vectores unitarios, cada uno un array [x,y,z] en
   * coordenadas globales) para un elemento de nodeI a nodeJ, con rotacion
   * opcional beta (grados) alrededor del eje local x.
   */
  function localAxes(nodeI, nodeJ, betaDeg) {
    var dx = nodeJ.x - nodeI.x, dy = nodeJ.y - nodeI.y, dz = nodeJ.z - nodeI.z;
    var L = Math.sqrt(dx * dx + dy * dy + dz * dz);
    var ex = [dx / L, dy / L, dz / L];

    var globalZ = [0, 0, 1];
    var globalX = [1, 0, 0];
    var dotZ = Math.abs(ex[0] * globalZ[0] + ex[1] * globalZ[1] + ex[2] * globalZ[2]);
    var ref = dotZ > 0.999 ? globalX : globalZ; // barra ~vertical -> usar X como referencia

    function cross(a, b) {
      return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]];
    }
    function normalize(v) {
      var n = Math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2]);
      return [v[0] / n, v[1] / n, v[2] / n];
    }

    var ey = normalize(cross(ref, ex));
    var ez = cross(ex, ey);

    if (betaDeg) {
      var b = (betaDeg * Math.PI) / 180;
      var cb = Math.cos(b), sb = Math.sin(b);
      var ey2 = [cb * ey[0] + sb * ez[0], cb * ey[1] + sb * ez[1], cb * ey[2] + sb * ez[2]];
      var ez2 = [-sb * ey[0] + cb * ez[0], -sb * ey[1] + cb * ez[1], -sb * ey[2] + cb * ez[2]];
      ey = ey2; ez = ez2;
    }

    return { ex: ex, ey: ey, ez: ez, L: L };
  }

  /** Matriz de transformacion 12x12 local<->global (bloques 3x3 repetidos). */
  function transformMatrix(axes) {
    var lambda = [axes.ex, axes.ey, axes.ez]; // filas: local = lambda * global
    var T = zeros(12, 12);
    for (var block = 0; block < 4; block++) {
      var off = block * 3;
      for (var r = 0; r < 3; r++) {
        for (var c = 0; c < 3; c++) {
          T[off + r][off + c] = lambda[r][c];
        }
      }
    }
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

  function globalStiffness(kLocal, T) {
    var Tt = transpose(T);
    return matMul(matMul(Tt, kLocal), T);
  }

  /**
   * Vector de carga nodal equivalente local (12) para UDL uniforme en
   * local y (qy) y local z (qz) simultaneamente. qy, qz positivos =
   * sentido local -y / -z (misma convencion que el parametro `w` del
   * modulo 2D). Misma derivacion (trabajo virtual con funciones de forma
   * de Hermite) que el modulo 2D para el bloque y/rz; el bloque z/ry usa
   * el patron de signos invertido del bloque de rigidez de flexion en y
   * — verificado en tests/validation.js contra viga simplemente apoyada
   * con UDL en cada direccion.
   */
  function udlEquivalentLoadLocal(qy, qz, L) {
    var f = new Array(12).fill(0);
    // bloque y/rz (v1=1,rz1=5,v2=7,rz2=11)
    f[1] = -qy * L / 2; f[5] = -qy * L * L / 12; f[7] = -qy * L / 2; f[11] = qy * L * L / 12;
    // bloque z/ry (w1=2,ry1=4,w2=8,ry2=10) — signos de momento invertidos
    f[2] = -qz * L / 2; f[4] = qz * L * L / 12; f[8] = -qz * L / 2; f[10] = -qz * L * L / 12;
    return f;
  }

  root.FEM3D.frameElement = {
    localStiffness: localStiffness,
    localAxes: localAxes,
    transformMatrix: transformMatrix,
    globalStiffness: globalStiffness,
    matMul: matMul,
    transpose: transpose,
    matVec: matVec,
    udlEquivalentLoadLocal: udlEquivalentLoadLocal
  };
})(typeof window !== 'undefined' ? window : global);
