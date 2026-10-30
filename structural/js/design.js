/**
 * Chequeo de diseño en acero por AISC 360 (LRFD) — tracción, compresión con
 * pandeo flexural, flexión elástica, corte, e interacción flexo-compresión.
 *
 * IMPORTANTE sobre alcance y fuentes (ver README, sección "Diseño AISC 360"):
 * - Las ecuaciones (D2, E3, G2, H1) se verificaron cruzando varias fuentes
 *   técnicas independientes (no el texto oficial comprado de AISC/ANSI), y
 *   usando invariantes de las propias fórmulas (ver tests/validation_design.js).
 *   No es NCh427 verificado contra el documento oficial del INN — es AISC 360,
 *   que es la base que NCh427 referencia según fuentes consultadas.
 * - Flexión: solo se verifica contra fluencia (Mn = Fy·Sx). NO se calcula el
 *   momento plástico Mp = Fy·Zx (el catálogo no trae Zx) ni pandeo
 *   lateral-torsional AISC F2/F3 (no se tiene la constante de alabeo Cw).
 *   Es conservador respecto a Mp, pero el LTB no verificado es una limitación
 *   real si el tramo sin arriostrar es largo — revisar aparte.
 * - Compresión: solo pandeo flexural (E3). Para perfiles no doblemente
 *   simétricos (C, CA, T) NO se verifica pandeo flexo-torsional (E4), que
 *   puede gobernar en esos casos — el número mostrado puede ser optimista.
 * - Se asume K=1 y longitud sin arriostrar = largo de la barra, igual en
 *   ambos ejes (no hay forma de modelar arriostramientos intermedios).
 * - Solo disponible para secciones con geometría real: rectangular sólida,
 *   circular sólida, o catálogo de perfiles. Sección "manual" (A/I/c
 *   directos) no tiene geometría real — mismo criterio que el cálculo de
 *   corte en stress.js.
 */
(function (root) {
  'use strict';

  var FEM = root.FEM;

  var PHI = { tension: 0.90, compression: 0.90, flexure: 0.90, shear: 0.90 };

  /** Geometría real de la sección: A, Sx (módulo elástico del eje modelado),
   * rx/ry (radios de giro de AMBOS ejes, para pandeo), y datos de alma
   * (h, tw, kv) para el corte. null si no hay geometría real disponible. */
  function sectionGeometry(el) {
    var sec = el.section;
    if (sec.type === 'rect') {
      var b = sec.params.b, h = sec.params.h; // h = direccion de flexion modelada
      var A = b * h;
      var Istrong = (b * Math.pow(h, 3)) / 12;
      var Iweak = (h * Math.pow(b, 3)) / 12;
      return {
        available: true, shape: 'rect', A: A, Sx: Istrong / (h / 2),
        rx: Math.sqrt(Istrong / A), ry: Math.sqrt(Iweak / A),
        h: null, tw: null, kv: null, Aw: A
      };
    }
    if (sec.type === 'circle') {
      var R = sec.params.d / 2;
      var A2 = Math.PI * R * R;
      var I2 = (Math.PI * Math.pow(R, 4)) / 4;
      return {
        available: true, shape: 'circle', A: A2, Sx: I2 / R,
        rx: Math.sqrt(I2 / A2), ry: Math.sqrt(I2 / A2),
        h: null, tw: null, kv: null, Aw: A2
      };
    }
    if (sec.type === 'manual' && el.catalogRef && FEM.Catalog.loaded) {
      var profile = FEM.Catalog.findById(el.catalogRef.id);
      if (profile) {
        var A3 = profile.A_mm2;
        var Smodeled = el.catalogRef.axis === 'weak' ? profile.Wweak_mm3 : profile.Wstrong_mm3;
        var hWeb = profile.H_mm - 2 * profile.e_mm; // alma libre, aproximada
        return {
          available: true, shape: 'catalog', family: el.catalogRef.family, A: A3, Sx: Smodeled,
          rx: Math.sqrt(profile.Istrong_mm4 / A3), ry: Math.sqrt(profile.Iweak_mm4 / A3),
          h: hWeb, tw: profile.t_mm, kv: 5, Aw: hWeb * profile.t_mm,
          nonDoublySymmetric: ['C', 'CA', 'T'].indexOf(el.catalogRef.family) !== -1
        };
      }
    }
    return { available: false, reason: 'Sin geometría real para diseño (sección manual sin perfil de catálogo).' };
  }

  /** Coeficiente de corte del alma Cv (AISC 360 G2, forma general con kv explícito). */
  function shearCv(h, tw, kv, Fy, E) {
    if (kv == null) return 1; // seccion solida: sin alma delgada, sin pandeo de corte
    var ratio = h / tw;
    var lim1 = 1.10 * Math.sqrt((kv * E) / Fy);
    var lim2 = 1.37 * Math.sqrt((kv * E) / Fy);
    if (ratio <= lim1) return 1;
    if (ratio <= lim2) return lim1 / ratio;
    return (1.51 * kv * E) / (ratio * ratio * Fy);
  }

  /** D2(a): fluencia en tracción. Pn = Fy*Ag. */
  function tensionCapacity(geom, Fy) {
    var Pn = Fy * geom.A;
    return { Pn: Pn, phi: PHI.tension, phiPn: PHI.tension * Pn };
  }

  /** E3: pandeo flexural. K=1, L = largo de la barra (ver limitaciones arriba). */
  function compressionCapacity(geom, Fy, E, L) {
    var rGov = Math.min(geom.rx, geom.ry);
    var KLr = L / rGov;
    var Fe = (Math.PI * Math.PI * E) / (KLr * KLr);
    var Fcr = KLr <= 4.71 * Math.sqrt(E / Fy)
      ? Math.pow(0.658, Fy / Fe) * Fy
      : 0.877 * Fe;
    var Pn = Fcr * geom.A;
    return { Pn: Pn, phi: PHI.compression, phiPn: PHI.compression * Pn, Fcr: Fcr, Fe: Fe, KLr: KLr };
  }

  /** Flexión: solo fluencia elástica Mn = Fy*Sx (ver limitaciones: no hay Mp ni LTB). */
  function flexureCapacity(geom, Fy) {
    var Mn = Fy * geom.Sx;
    return { Mn: Mn, phi: PHI.flexure, phiMn: PHI.flexure * Mn };
  }

  /** G2: corte. Vn = 0.6*Fy*Aw*Cv. */
  function shearCapacity(geom, Fy, E) {
    var Cv = shearCv(geom.h, geom.tw, geom.kv, Fy, E);
    var Vn = 0.6 * Fy * geom.Aw * Cv;
    return { Vn: Vn, phi: PHI.shear, phiVn: PHI.shear * Vn, Cv: Cv };
  }

  /**
   * H1: interacción flexo-compresión (H1-1a/b, compresión) o tracción+flexión
   * (forma simplificada análoga, ver cabecera del archivo sobre su certeza).
   * N: axial (N>0 tracción, N<0 compresión, convención de stress.js). M: momento.
   */
  function interactionRatio(N, M, tensionCap, compCap, flexCap) {
    var isCompression = N < 0;
    var axialCap = isCompression ? compCap : tensionCap;
    var Pr = Math.abs(N);
    var Pc = axialCap.phiPn;
    var Mr = Math.abs(M);
    var Mc = flexCap.phiMn;
    var axialRatio = Pc > 0 ? Pr / Pc : (Pr > 0 ? Infinity : 0);
    var flexRatio = Mc > 0 ? Mr / Mc : (Mr > 0 ? Infinity : 0);
    var dcr;
    if (isCompression) {
      dcr = axialRatio >= 0.2
        ? axialRatio + (8 / 9) * flexRatio
        : axialRatio / 2 + flexRatio;
    } else {
      dcr = axialRatio + flexRatio;
    }
    return { axialRatio: axialRatio, flexRatio: flexRatio, dcr: dcr, isCompression: isCompression };
  }

  /**
   * Chequeo completo de una barra: evalúa tracción/compresión, flexión,
   * corte e interacción en varios puntos a lo largo de la barra y devuelve
   * el peor caso (DCR máximo) y el punto donde ocurre.
   */
  function checkMember(el, ef, solverModule, Fy, E, numPoints) {
    var geom = sectionGeometry(el);
    if (!geom.available) return { available: false, reason: geom.reason };

    var tensionCap = tensionCapacity(geom, Fy);
    var compCap = compressionCapacity(geom, Fy, E, el.length());
    var flexCap = flexureCapacity(geom, Fy);
    var shearCap = shearCapacity(geom, Fy, E);

    var nx = numPoints || 21;
    var worst = null;
    for (var i = 0; i <= nx; i++) {
      var x = (ef.L * i) / nx;
      var f = solverModule.internalForcesAt(ef, x);
      var shearRatio = shearCap.phiVn > 0 ? Math.abs(f.V) / shearCap.phiVn : Infinity;
      var inter = interactionRatio(f.N, f.M, tensionCap, compCap, flexCap);
      var govRatio = Math.max(shearRatio, inter.dcr);
      if (!worst || govRatio > worst.dcr) {
        worst = {
          x: x, dcr: govRatio, shearRatio: shearRatio, interaction: inter,
          N: f.N, M: f.M, V: f.V,
          governing: shearRatio > inter.dcr ? 'corte' : (inter.isCompression ? 'compresión+flexión' : 'tracción+flexión')
        };
      }
    }

    return {
      available: true, geom: geom, Fy: Fy, E: E,
      tension: tensionCap, compression: compCap, flexure: flexCap, shear: shearCap,
      worst: worst, nonDoublySymmetric: !!geom.nonDoublySymmetric
    };
  }

  root.FEM = root.FEM || {};
  root.FEM.Design = {
    PHI: PHI,
    sectionGeometry: sectionGeometry,
    shearCv: shearCv,
    tensionCapacity: tensionCapacity,
    compressionCapacity: compressionCapacity,
    flexureCapacity: flexureCapacity,
    shearCapacity: shearCapacity,
    interactionRatio: interactionRatio,
    checkMember: checkMember
  };
})(typeof window !== 'undefined' ? window : global);
