/**
 * Algebra lineal minima: resolver A*x = b por eliminacion gaussiana con
 * pivoteo parcial. Suficiente para los tamanos de matriz de este modulo
 * (porticos de decenas de nodos, no miles).
 */
(function (root) {
  'use strict';

  /**
   * @param {number[][]} Ain matriz n x n
   * @param {number[]} bin vector n
   * @returns {number[]} solucion x
   */
  function solve(Ain, bin) {
    var n = bin.length;
    // copia profunda para no mutar las entradas del caller
    var A = Ain.map(function (row) { return row.slice(); });
    var b = bin.slice();

    for (var col = 0; col < n; col++) {
      // pivoteo parcial
      var maxRow = col;
      var maxVal = Math.abs(A[col][col]);
      for (var r = col + 1; r < n; r++) {
        if (Math.abs(A[r][col]) > maxVal) {
          maxVal = Math.abs(A[r][col]);
          maxRow = r;
        }
      }
      if (maxVal < 1e-12) {
        throw new Error(
          'Matriz singular (columna ' + col + '): revisa apoyos ' +
          '(estructura inestable / grados de libertad sin restringir).'
        );
      }
      if (maxRow !== col) {
        var tmpRow = A[col]; A[col] = A[maxRow]; A[maxRow] = tmpRow;
        var tmpB = b[col]; b[col] = b[maxRow]; b[maxRow] = tmpB;
      }

      for (var i = col + 1; i < n; i++) {
        var factor = A[i][col] / A[col][col];
        if (factor === 0) continue;
        for (var j = col; j < n; j++) {
          A[i][j] -= factor * A[col][j];
        }
        b[i] -= factor * b[col];
      }
    }

    var x = new Array(n).fill(0);
    for (var k = n - 1; k >= 0; k--) {
      var sum = b[k];
      for (var m = k + 1; m < n; m++) {
        sum -= A[k][m] * x[m];
      }
      x[k] = sum / A[k][k];
    }
    return x;
  }

  function zeros(rows, cols) {
    var m = new Array(rows);
    for (var i = 0; i < rows; i++) m[i] = new Array(cols).fill(0);
    return m;
  }

  root.FEM = root.FEM || {};
  root.FEM.linalg = { solve: solve, zeros: zeros };
})(typeof window !== 'undefined' ? window : global);
