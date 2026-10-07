/**
 * Convencion de unidades.
 *
 * Interno (todo el solver trabaja en esto, SIN excepcion):
 *   longitud -> mm
 *   fuerza   -> N
 *   momento  -> N*mm
 *   tension / E -> MPa (= N/mm^2)
 *   A -> mm^2, I -> mm^4
 *
 * UI (lo que el usuario ve y tipea):
 *   coordenadas de nodos      -> m
 *   dimensiones de seccion    -> mm
 *   E                         -> MPa
 *   cargas puntuales          -> kN
 *   momentos puntuales        -> kN*m
 *   carga distribuida         -> kN/m
 *   resultados: reacciones    -> kN / kN*m
 *   resultados: desplazamientos -> mm
 *   resultados: tensiones     -> MPa
 *
 * Nota: kN/m == N/mm numericamente (1 kN/m = 1000 N / 1000 mm = 1 N/mm),
 * por lo que la carga distribuida no necesita factor de conversion.
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

    // kN/m -> N/mm es factor 1 (ver nota arriba), se deja explicito para
    // que el codigo que lo use sea legible y no "numeros magicos".
    KN_PER_M_TO_N_PER_MM: 1,
    N_PER_MM_TO_KN_PER_M: 1,

    nodeCoordToInternal: function (xMeters, yMeters) {
      return { x: xMeters * Units.M_TO_MM, y: yMeters * Units.M_TO_MM };
    },
    nodeCoordToUi: function (xMm, yMm) {
      return { x: xMm * Units.MM_TO_M, y: yMm * Units.MM_TO_M };
    },

    pointLoadToInternal: function (fxKn, fyKn, mKnm) {
      return {
        fx: fxKn * Units.KN_TO_N,
        fy: fyKn * Units.KN_TO_N,
        m: mKnm * Units.KNM_TO_NMM
      };
    },

    distributedLoadToInternal: function (wKnPerM) {
      return wKnPerM * Units.KN_PER_M_TO_N_PER_MM;
    },

    forceToUi: function (fN) {
      return fN * Units.N_TO_KN;
    },
    momentToUi: function (mNmm) {
      return mNmm * Units.NMM_TO_KNM;
    }
  };

  root.FEM = root.FEM || {};
  root.FEM.Units = Units;
})(typeof window !== 'undefined' ? window : global);
