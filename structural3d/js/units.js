/**
 * Convencion de unidades (misma que el modulo 2D structural/js/units.js).
 *
 * Interno (todo el solver trabaja en esto, SIN excepcion):
 *   longitud -> mm
 *   fuerza   -> N
 *   momento / torque -> N*mm
 *   tension / E / G -> MPa (= N/mm^2)
 *   A -> mm^2, I -> mm^4, J -> mm^4
 *
 * UI (lo que el usuario ve y tipea):
 *   coordenadas de nodos      -> m
 *   dimensiones de seccion    -> mm
 *   E, G                      -> MPa
 *   cargas puntuales          -> kN
 *   momentos / torques        -> kN*m
 *   carga distribuida         -> kN/m
 *   resultados: reacciones    -> kN / kN*m
 *   resultados: desplazamientos -> mm
 *   resultados: tensiones     -> MPa
 */
(function (root) {
  'use strict';

  var Units = {
    M_TO_MM: 1000,
    MM_TO_M: 1 / 1000,
    KN_TO_N: 1000,
    N_TO_KN: 1 / 1000,
    KNM_TO_NMM: 1e6,
    NMM_TO_KNM: 1 / 1e6,
    KN_PER_M_TO_N_PER_MM: 1,
    N_PER_MM_TO_KN_PER_M: 1,

    nodeCoordToInternal: function (xM, yM, zM) {
      return { x: xM * Units.M_TO_MM, y: yM * Units.M_TO_MM, z: zM * Units.M_TO_MM };
    },
    nodeCoordToUi: function (xMm, yMm, zMm) {
      return { x: xMm * Units.MM_TO_M, y: yMm * Units.MM_TO_M, z: zMm * Units.MM_TO_M };
    },

    pointLoadToInternal: function (fxKn, fyKn, fzKn, mxKnm, myKnm, mzKnm) {
      return {
        fx: fxKn * Units.KN_TO_N, fy: fyKn * Units.KN_TO_N, fz: fzKn * Units.KN_TO_N,
        mx: mxKnm * Units.KNM_TO_NMM, my: myKnm * Units.KNM_TO_NMM, mz: mzKnm * Units.KNM_TO_NMM
      };
    },

    distributedLoadToInternal: function (wKnPerM) {
      return wKnPerM * Units.KN_PER_M_TO_N_PER_MM;
    },

    forceToUi: function (fN) { return fN * Units.N_TO_KN; },
    momentToUi: function (mNmm) { return mNmm * Units.NMM_TO_KNM; }
  };

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.Units = Units;
})(typeof window !== 'undefined' ? window : global);
