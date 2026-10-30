/**
 * Catalogo de perfiles comerciales. Carga datos reales desde
 * data/catalog_icha.json (extraidos y verificados desde el archivo ICHA
 * que subio el usuario — ver data/catalog_icha_excluidos.json para las
 * filas descartadas por inconsistencia detectada en el archivo fuente).
 *
 * Mapeo de ejes (IMPORTANTE, fuente de errores si se confunde):
 *   El catalogo da propiedades para el "eje x-x" (eje FUERTE, resiste la
 *   flexion vertical tipica de una viga/columna parada) y el "eje y-y"
 *   (eje DEBIL). Este modulo 2D solo tiene UN eje de flexion (I, c), asi
 *   que el usuario elige cual de los dos usar segun como oriente la barra
 *   en su modelo — por defecto se ofrece el eje fuerte (uso mas comun).
 *
 * c (fibra extrema) se calcula como I/W directamente del catalogo
 * (exacto, no se asume H/2 — importante para perfiles asimetricos como
 * T y C/CA).
 */
(function (root) {
  'use strict';

  var Catalog = {
    profiles: [],
    loaded: false,
    error: null,

    load: function (url) {
      url = url || 'data/catalog_icha.json';
      return fetch(url)
        .then(function (resp) {
          if (!resp.ok) throw new Error('HTTP ' + resp.status);
          return resp.json();
        })
        .then(function (data) {
          Catalog.profiles = data;
          Catalog.loaded = true;
          return data;
        })
        .catch(function (err) {
          Catalog.error = err.message;
          Catalog.loaded = false;
          throw err;
        });
    },

    families: function () {
      var seen = {};
      var out = [];
      Catalog.profiles.forEach(function (p) {
        if (!seen[p.family]) { seen[p.family] = true; out.push({ family: p.family, label: p.familyLabel }); }
      });
      return out;
    },

    byFamily: function (family) {
      return Catalog.profiles.filter(function (p) { return p.family === family; });
    },

    findById: function (id) {
      return Catalog.profiles.find(function (p) { return p.id === id; });
    },

    /**
     * Convierte un perfil de catalogo a parametros de seccion 'manual'
     * del modulo 2D: {A, I, c}. axis: 'strong' (x-x, por defecto) o 'weak' (y-y).
     */
    toSectionParams: function (profile, axis) {
      if (axis === 'weak') {
        return { A: profile.A_mm2, I: profile.Iweak_mm4, c: profile.cWeak_mm };
      }
      return { A: profile.A_mm2, I: profile.Istrong_mm4, c: profile.cStrong_mm };
    }
  };

  root.FEM = root.FEM || {};
  root.FEM.Catalog = Catalog;
})(typeof window !== 'undefined' ? window : global);
