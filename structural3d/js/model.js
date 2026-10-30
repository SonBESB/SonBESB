/**
 * Estructuras de datos del modelo de portico 3D. Todas las cantidades aqui
 * ya estan en unidades internas (mm, N, N*mm, MPa).
 */
(function (root) {
  'use strict';

  var RESTRAINT = {
    FREE: { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false },
    PINNED: { ux: true, uy: true, uz: true, rx: false, ry: false, rz: false },
    FIXED: { ux: true, uy: true, uz: true, rx: true, ry: true, rz: true }
  };

  function Node(id, xMm, yMm, zMm) {
    this.id = id;
    this.x = xMm; this.y = yMm; this.z = zMm;
    this.restraint = { ux: false, uy: false, uz: false, rx: false, ry: false, rz: false };
  }

  // Tabla de Roark/Saint-Venant para torsion de rectangulo (a = lado largo,
  // b = lado corto, a/b en la tabla). K = beta*a*b^3 (rigidez torsional),
  // tau_max = T/(alpha*a*b^2) (tension de corte maxima, en el punto medio
  // del lado largo). Interpolacion lineal entre filas; fuera de rango se
  // usa el valor limite (cuadrado) o 1/3 (a/b -> infinito).
  var RECT_TORSION_TABLE = [
    { ratio: 1.0, beta: 0.1406, alpha: 0.208 },
    { ratio: 1.5, beta: 0.196, alpha: 0.231 },
    { ratio: 2.0, beta: 0.229, alpha: 0.246 },
    { ratio: 3.0, beta: 0.263, alpha: 0.267 },
    { ratio: 4.0, beta: 0.281, alpha: 0.282 },
    { ratio: 5.0, beta: 0.291, alpha: 0.291 },
    { ratio: 6.0, beta: 0.299, alpha: 0.299 },
    { ratio: 8.0, beta: 0.307, alpha: 0.307 },
    { ratio: 10.0, beta: 0.313, alpha: 0.313 },
    { ratio: 1e9, beta: 1 / 3, alpha: 1 / 3 }
  ];

  function interpRectTorsion(ratio) {
    var t = RECT_TORSION_TABLE;
    if (ratio <= t[0].ratio) return t[0];
    for (var i = 0; i < t.length - 1; i++) {
      if (ratio >= t[i].ratio && ratio <= t[i + 1].ratio) {
        var f = (ratio - t[i].ratio) / (t[i + 1].ratio - t[i].ratio);
        return {
          beta: t[i].beta + f * (t[i + 1].beta - t[i].beta),
          alpha: t[i].alpha + f * (t[i + 1].alpha - t[i].alpha)
        };
      }
    }
    return t[t.length - 1];
  }

  /**
   * Seccion transversal 3D. type: 'rect' | 'circle' | 'manual'.
   * rect: { b, h } — b = dimension en direccion local y, h = dimension en
   *   direccion local z (mm). circle: { d } (mm, solida).
   *   manual: { A, Iy, Iz, J, cy, cz }.
   */
  function Section(type, params) {
    this.type = type;
    this.params = params;
  }

  Section.prototype.properties = function () {
    var p = this.params;
    if (this.type === 'rect') {
      var b = p.b, h = p.h; // b: ancho (eje y local), h: alto (eje z local)
      var A = b * h;
      var Iy = (b * Math.pow(h, 3)) / 12; // resiste flexion con curvatura en plano x-z
      var Iz = (h * Math.pow(b, 3)) / 12; // resiste flexion con curvatura en plano x-y
      var longSide = Math.max(b, h), shortSide = Math.min(b, h);
      var coef = interpRectTorsion(longSide / shortSide);
      var J = coef.beta * longSide * Math.pow(shortSide, 3);
      var alphaTorsion = coef.alpha;
      return {
        shape: 'rect', A: A, Iy: Iy, Iz: Iz, J: J, cy: b / 2, cz: h / 2,
        b: b, h: h, torsionAlpha: alphaTorsion, torsionLong: longSide, torsionShort: shortSide
      };
    }
    if (this.type === 'circle') {
      var R = p.d / 2;
      var A2 = Math.PI * R * R;
      var I = (Math.PI * Math.pow(R, 4)) / 4;
      var J2 = (Math.PI * Math.pow(R, 4)) / 2;
      return { shape: 'circle', A: A2, Iy: I, Iz: I, J: J2, cy: R, cz: R, R: R };
    }
    if (this.type === 'manual') {
      return {
        shape: 'manual', A: p.A, Iy: p.Iy, Iz: p.Iz, J: p.J,
        cy: p.cy, cz: p.cz
      };
    }
    throw new Error('Tipo de seccion desconocido: ' + this.type);
  };

  /**
   * Elemento de portico 3D. E, G en MPa. section: instancia de Section.
   * beta: angulo (grados) de rotacion del eje local y/z alrededor del eje
   *   local x, respecto a la orientacion automatica por defecto (ver
   *   frameElement.js). udlY, udlZ: carga distribuida uniforme (N/mm);
   *   positiva = sentido local -y / -z respectivamente (igual convencion
   *   que el modulo 2D: un valor positivo "empuja hacia abajo" si la barra
   *   esta orientada con el local y/z apuntando "arriba"). Ver
   *   frameElement.js (udlEquivalentLoadLocal) y tests/validation.js.
   */
  function Element(id, nodeI, nodeJ, E, G, section) {
    this.id = id;
    this.nodeI = nodeI;
    this.nodeJ = nodeJ;
    this.E = E;
    this.G = G;
    this.section = section;
    this.beta = 0;
    this.udlY = 0;
    this.udlZ = 0;
  }

  Element.prototype.length = function () {
    var dx = this.nodeJ.x - this.nodeI.x;
    var dy = this.nodeJ.y - this.nodeI.y;
    var dz = this.nodeJ.z - this.nodeI.z;
    return Math.sqrt(dx * dx + dy * dy + dz * dz);
  };

  function NodalLoad(nodeId, fx, fy, fz, mx, my, mz) {
    this.nodeId = nodeId;
    this.fx = fx || 0; this.fy = fy || 0; this.fz = fz || 0;
    this.mx = mx || 0; this.my = my || 0; this.mz = mz || 0;
  }

  function Model() {
    this.nodes = [];
    this.elements = [];
    this.nodalLoads = [];
    this._nodeSeq = 1;
    this._elemSeq = 1;
  }

  Model.prototype.addNode = function (xMm, yMm, zMm) {
    var n = new Node(this._nodeSeq++, xMm, yMm, zMm);
    this.nodes.push(n);
    return n;
  };

  Model.prototype.addElement = function (nodeI, nodeJ, E, G, section) {
    var e = new Element(this._elemSeq++, nodeI, nodeJ, E, G, section);
    this.elements.push(e);
    return e;
  };

  Model.prototype.removeNode = function (nodeId) {
    this.elements = this.elements.filter(function (e) {
      return e.nodeI.id !== nodeId && e.nodeJ.id !== nodeId;
    });
    this.nodalLoads = this.nodalLoads.filter(function (l) { return l.nodeId !== nodeId; });
    this.nodes = this.nodes.filter(function (n) { return n.id !== nodeId; });
  };

  Model.prototype.removeElement = function (elemId) {
    this.elements = this.elements.filter(function (e) { return e.id !== elemId; });
  };

  Model.prototype.addNodalLoad = function (nodeId, fx, fy, fz, mx, my, mz) {
    var l = new NodalLoad(nodeId, fx, fy, fz, mx, my, mz);
    this.nodalLoads.push(l);
    return l;
  };

  Model.prototype.dofCount = function () { return this.nodes.length * 6; };

  Model.prototype.dofIndex = function (nodeId) {
    var idx = this.nodes.findIndex(function (n) { return n.id === nodeId; });
    if (idx < 0) throw new Error('Nodo no encontrado: ' + nodeId);
    return idx * 6; // ux,uy,uz,rx,ry,rz en idx*6 .. idx*6+5
  };

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.RESTRAINT = RESTRAINT;
  root.FEM3D.Node = Node;
  root.FEM3D.Section = Section;
  root.FEM3D.Element = Element;
  root.FEM3D.NodalLoad = NodalLoad;
  root.FEM3D.Model = Model;
  root.FEM3D.interpRectTorsion = interpRectTorsion;
})(typeof window !== 'undefined' ? window : global);
