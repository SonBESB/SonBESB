/**
 * Tensiones normales, de corte (Jourawski por eje) y de torsion, combinadas
 * en von Mises para un elemento de portico 3D. Secciones soportadas:
 * rectangular solida y circular solida (igual que el modulo 2D).
 *
 * Convencion (derivada y verificada en tests/validation.js):
 *   sigma(y,z) = N/A - Mz(x)*y/Iz - My(x)*z/Iy
 *   tau_xy(y,z) = Vy(x)*Qy(y)/(Iz*anchoY(y)) + tau_torsion_xy(y,z)
 *   tau_xz(y,z) = Vz(x)*Qz(z)/(Iy*anchoZ(z)) + tau_torsion_xz(y,z)
 *   von Mises = sqrt(sigma^2 + 3*(tau_xy^2 + tau_xz^2))
 *     (formula general de von Mises para un estado sigma_xx + tau_xy + tau_xz
 *     con sigma_yy=sigma_zz=tau_yz=0 — exacta, no aproximada, dada esa
 *     hipotesis de viga delgada).
 *
 * Aproximacion deliberada: tau_xy se trata como funcion solo de y (uniforme
 * en z) y tau_xz solo de z (uniforme en y) — estandar en teoria de vigas,
 * exacta en los ejes de simetria, aproximada fuera de ellos.
 *
 * Torsion: exacta para seccion circular solida (tau_xy=-T*z/J, tau_xz=T*y/J,
 * flujo de corte circular estandar). Para seccion rectangular NO se agrega
 * al campo (y,z) — el campo de Saint-Venant real no es cerrado — se reporta
 * aparte como un maximo escalar (tabla de Roark, ver model.js) y se combina
 * de forma conservadora (sumado al corte transversal maximo) solo en el
 * resumen numerico, nunca en el mapa visual. Ver README.
 */
(function (root) {
  'use strict';

  function widthAndQ_y(section, y) {
    var p = section.properties();
    if (p.shape === 'rect') {
      var yc = Math.max(-p.cy, Math.min(p.cy, y));
      return { width: p.h, Q: (p.h / 2) * (p.cy * p.cy - yc * yc) };
    }
    if (p.shape === 'circle') {
      var R = p.R;
      var yc2 = Math.max(-R, Math.min(R, y));
      var rem = Math.max(0, R * R - yc2 * yc2);
      return { width: 2 * Math.sqrt(rem), Q: (2 / 3) * Math.pow(rem, 1.5) };
    }
    return null; // manual: sin geometria real para corte
  }

  function widthAndQ_z(section, z) {
    var p = section.properties();
    if (p.shape === 'rect') {
      var zc = Math.max(-p.cz, Math.min(p.cz, z));
      return { width: p.b, Q: (p.b / 2) * (p.cz * p.cz - zc * zc) };
    }
    if (p.shape === 'circle') {
      var R = p.R;
      var zc2 = Math.max(-R, Math.min(R, z));
      var rem = Math.max(0, R * R - zc2 * zc2);
      return { width: 2 * Math.sqrt(rem), Q: (2 / 3) * Math.pow(rem, 1.5) };
    }
    return null;
  }

  /** Corte de torsion exacto en (y,z) para seccion circular; null si no aplica. */
  function torsionShearField(section, T, y, z) {
    var p = section.properties();
    if (p.shape !== 'circle' || !T) return { txy: 0, txz: 0 };
    var J = p.J;
    return { txy: (-T * z) / J, txz: (T * y) / J };
  }

  /** Corte de torsion maximo escalar (en el borde), para reportar aparte. */
  function torsionShearMax(section, T) {
    var p = section.properties();
    if (!T) return 0;
    if (p.shape === 'circle') return (Math.abs(T) * p.R) / p.J;
    if (p.shape === 'rect') return Math.abs(T) / (p.torsionAlpha * p.torsionLong * p.torsionShort * p.torsionShort);
    return 0; // manual: sin geometria real
  }

  function stressAt(section, N, My, Mz, Vy, Vz, T, y, z) {
    var p = section.properties();
    var sigma = N / p.A - (Mz * y) / p.Iz - (My * z) / p.Iy;

    var txy = 0, txz = 0;
    if (p.shape !== 'manual') {
      var wqY = widthAndQ_y(section, y);
      var wqZ = widthAndQ_z(section, z);
      if (Vy) txy += (Vy * wqY.Q) / (p.Iz * wqY.width);
      if (Vz) txz += (Vz * wqZ.Q) / (p.Iy * wqZ.width);
      var tors = torsionShearField(section, T, y, z);
      txy += tors.txy; txz += tors.txz;
    }

    var vonMises = Math.sqrt(sigma * sigma + 3 * (txy * txy + txz * txz));
    return { sigma: sigma, txy: txy, txz: txz, vonMises: vonMises };
  }

  /**
   * Grilla (x a lo largo del elemento) x (y,z a traves de la seccion) de
   * von Mises, usando N(x)/Vy(x)/Vz(x)/My(x)/Mz(x)/T(x) exactos del solver.
   * Para seccion rectangular, el corte de torsion NO esta en esta grilla
   * (ver cabecera del archivo); se agrega por separado en torsionMax.
   */
  function elementStressGrid(solverModule, ef, section, numX, numY, numZ) {
    var nx = numX || 15, ny = numY || 7, nz = numZ || 7;
    var p = section.properties();
    var grid = [];
    var maxVm = -Infinity, maxAt = null;

    for (var ix = 0; ix < nx; ix++) {
      var x = (ef.L * ix) / (nx - 1);
      var f = solverModule.internalForcesAt(ef, x);
      var points = [];
      for (var iy = 0; iy < ny; iy++) {
        var y = -p.cy + (2 * p.cy * iy) / (ny - 1);
        for (var iz = 0; iz < nz; iz++) {
          var z = -p.cz + (2 * p.cz * iz) / (nz - 1);
          var s = stressAt(section, f.N, f.My, f.Mz, f.Vy, f.Vz, f.T, y, z);
          points.push({ y: y, z: z, sigma: s.sigma, vonMises: s.vonMises });
          if (s.vonMises > maxVm) { maxVm = s.vonMises; maxAt = { x: x, y: y, z: z, vonMises: s.vonMises }; }
        }
      }
      grid.push({ x: x, N: f.N, Vy: f.Vy, Vz: f.Vz, T: f.T, My: f.My, Mz: f.Mz, points: points });
    }

    // Maximo conservador de torsion (seccion rectangular): se suma al corte
    // transversal maximo en el centroide de cada corte x, solo para el
    // resumen (no para el color del mapa).
    var torsionMaxGlobal = 0;
    if (p.shape === 'rect') {
      grid.forEach(function (col) {
        var tMax = torsionShearMax(section, col.T);
        torsionMaxGlobal = Math.max(torsionMaxGlobal, tMax);
      });
    }

    return { grid: grid, max: maxAt, torsionMax: torsionMaxGlobal, shape: p.shape };
  }

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.stress = {
    widthAndQ_y: widthAndQ_y,
    widthAndQ_z: widthAndQ_z,
    torsionShearField: torsionShearField,
    torsionShearMax: torsionShearMax,
    stressAt: stressAt,
    elementStressGrid: elementStressGrid
  };
})(typeof window !== 'undefined' ? window : global);
