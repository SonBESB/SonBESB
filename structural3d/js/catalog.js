/**
 * Catalogo de perfiles comerciales (3D). Mismos datos que el modulo 2D
 * (data/catalog_icha.json, ver ese archivo y js/catalog.js del modulo 2D
 * para el origen y la validacion de los datos) pero mapeados a las DOS
 * direcciones de flexion del modelo 3D (Iy, Iz) en vez de una sola.
 *
 * Mapeo de ejes (CRITICO — ver tambien model.js/frameElement.js de este
 * mismo modulo, donde Iy gobierna la flexion vertical tipica "My" y Iz la
 * flexion horizontal "Mz"):
 *   catalogo "eje x-x" (FUERTE, resiste la flexion vertical tipica de una
 *     viga parada bajo carga de gravedad) -> Iy del modelo 3D, cz del
 *     modelo 3D (fibra extrema en direccion z local).
 *   catalogo "eje y-y" (DEBIL) -> Iz del modelo 3D, cy del modelo 3D.
 * Esta es la MISMA logica que ya se verifico en tests/validation.js para
 * el elemento de portico 3D (Caso2: carga en Z usa Iy; theta_y=-dw/dx).
 * Si se invierte este mapeo, el perfil queda "acostado" (eje fuerte
 * resistiendo la direccion equivocada) sin que el solver tire error —
 * es un error silencioso, por eso se documenta tan explicito aqui.
 *
 * El perfil se aplica como seccion 'manual' con A, Iy, Iz, cy, cz, y J
 * (constante de torsion aproximada, Saint-Venant secciones abiertas de
 * pared delgada, calculada al generar el catalogo — ver
 * structural/data/catalog_icha.json / el script de conversion; no es un
 * valor de catalogo, es una aproximacion geometrica).
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
     * del modulo 3D: {A, Iy, Iz, cy, cz, J}. El eje fuerte del catalogo
     * siempre se orienta como Iy/cz (resiste flexion vertical tipica); no
     * hay opcion de "acostar" el perfil desde aqui — para eso usar el
     * angulo beta del elemento.
     */
    toSectionParams: function (profile) {
      return {
        A: profile.A_mm2,
        Iy: profile.Istrong_mm4,
        cz: profile.cStrong_mm,
        Iz: profile.Iweak_mm4,
        cy: profile.cWeak_mm,
        J: profile.J_mm4_approx || Math.min(profile.Istrong_mm4, profile.Iweak_mm4) * 0.1
      };
    }
  };

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.Catalog = Catalog;
})(typeof window !== 'undefined' ? window : global);
