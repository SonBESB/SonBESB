/**
 * Tensiones normales, de corte y von Mises sobre la seccion transversal,
 * a partir de N(x), M(x), V(x) (teoria de viga, Euler-Bernoulli + formula
 * de Jourawski para corte). Secciones soportadas: rectangular solida y
 * circular solida (ver model.js Section).
 *
 * Convencion (derivada y verificada contra el caso de viga simplemente
 * apoyada con carga puntual, ver tests/validation.js):
 *   y medido desde el eje neutro en direccion +y local ("arriba").
 *   sigma(y) = N/A - M*y/I   (M positivo = tramo en flexion positiva segun
 *                             solver.js; da compresion arriba, traccion abajo,
 *                             consistente con "sagging" bajo carga hacia abajo)
 *   tau(y)   = V*Q(y) / (I*b(y))  (formula de Jourawski; el signo de tau no
 *                                  afecta von Mises, que usa tau^2)
 *   von Mises (estado plano, sigma_y=sigma_z=0, tau_xz=0):
 *     sigma_vm = sqrt(sigma^2 + 3*tau^2)
 */
(function (root) {
  'use strict';

  /**
   * Ancho b(y) y momento estatico Q(y) (area por encima de y, respecto al
   * eje neutro) de la seccion, para la formula de corte de Jourawski.
   */
  function widthAndQ(section, y) {
    var props = section.properties();
    if (props.shape === 'rect') {
      var b = props.b, c = props.c;
      var yc = Math.max(-c, Math.min(c, y));
      return { b: b, Q: (b / 2) * (c * c - yc * yc) };
    }
    if (props.shape === 'circle') {
      var R = props.R;
      var yc2 = Math.max(-R, Math.min(R, y));
      var width = 2 * Math.sqrt(Math.max(0, R * R - yc2 * yc2));
      var Q = (2 / 3) * Math.pow(Math.max(0, R * R - yc2 * yc2), 1.5);
      return { b: width, Q: Q };
    }
    throw new Error(
      'Calculo de tension de corte no soportado para seccion manual ' +
      '(falta geometria real de la seccion, no se inventa un perfil).'
    );
  }

  /** Tension normal, de corte y von Mises en un punto (x fijo, altura y). */
  function stressAt(section, N, M, V, y) {
    var props = section.properties();
    var sigmaAxial = N / props.A;
    var sigmaBending = -(M * y) / props.I;
    var sigma = sigmaAxial + sigmaBending;

    var tau = 0;
    if (V !== 0 && props.shape !== 'manual') {
      var wq = widthAndQ(section, y);
      tau = (V * wq.Q) / (props.I * wq.b);
    }

    var vonMises = Math.sqrt(sigma * sigma + 3 * tau * tau);
    return { sigmaAxial: sigmaAxial, sigmaBending: sigmaBending, sigma: sigma, tau: tau, vonMises: vonMises };
  }

  /** Tensiones en numPointsY alturas (desde -c hasta +c) para un (N,M,V) dado. */
  function stressField(section, N, M, V, numPointsY) {
    var props = section.properties();
    var c = props.c;
    var pts = [];
    var n = numPointsY || 11;
    for (var i = 0; i < n; i++) {
      var y = -c + (2 * c * i) / (n - 1);
      pts.push(Object.assign({ y: y }, stressAt(section, N, M, V, y)));
    }
    return pts;
  }

  /**
   * Grilla completa (x a lo largo del elemento, y a traves de la seccion)
   * de von Mises y tensiones, usando las funciones N(x)/V(x)/M(x) exactas
   * del solver (solver.internalForcesAt). Util para visualizacion y para
   * encontrar el maximo von Mises del elemento.
   */
  function elementStressGrid(solverModule, ef, section, numX, numY) {
    var nx = numX || 21;
    var ny = numY || 11;
    var grid = [];
    var maxVm = -Infinity;
    var maxAt = null;
    for (var ix = 0; ix < nx; ix++) {
      var x = (ef.L * ix) / (nx - 1);
      var forces = solverModule.internalForcesAt(ef, x);
      var column = stressField(section, forces.N, forces.M, forces.V, ny);
      column.forEach(function (pt) {
        if (pt.vonMises > maxVm) {
          maxVm = pt.vonMises;
          maxAt = { x: x, y: pt.y, vonMises: pt.vonMises, sigma: pt.sigma, tau: pt.tau };
        }
      });
      grid.push({ x: x, N: forces.N, V: forces.V, M: forces.M, points: column });
    }
    return { grid: grid, max: maxAt };
  }

  root.FEM = root.FEM || {};
  root.FEM.stress = {
    widthAndQ: widthAndQ,
    stressAt: stressAt,
    stressField: stressField,
    elementStressGrid: elementStressGrid
  };
})(typeof window !== 'undefined' ? window : global);
