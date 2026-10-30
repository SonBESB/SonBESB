/**
 * Estructuras de datos del modelo estructural.
 * Todas las cantidades aqui ya estan en unidades internas (mm, N, N*mm, MPa).
 */
(function (root) {
  'use strict';

  var RESTRAINT = {
    FREE: { ux: false, uy: false, rz: false },
    PINNED: { ux: true, uy: true, rz: false },
    FIXED: { ux: true, uy: true, rz: true },
    ROLLER_X: { ux: false, uy: true, rz: false }, // deja mover horizontal, restringe vertical
    ROLLER_Y: { ux: true, uy: false, rz: false }  // restringe horizontal, deja mover vertical
  };

  function Node(id, xMm, yMm) {
    this.id = id;
    this.x = xMm;
    this.y = yMm;
    this.restraint = { ux: false, uy: false, rz: false };
  }

  /**
   * Seccion transversal. type: 'rect' | 'circle' | 'manual'.
   * rect: { b, h } (mm). circle: { d } (mm, solida). manual: { A, I, c }.
   */
  function Section(type, params) {
    this.type = type;
    this.params = params;
  }

  Section.prototype.properties = function () {
    var p = this.params;
    if (this.type === 'rect') {
      var b = p.b, h = p.h;
      return { A: b * h, I: (b * Math.pow(h, 3)) / 12, c: h / 2, shape: 'rect', b: b, h: h };
    }
    if (this.type === 'circle') {
      var R = p.d / 2;
      return { A: Math.PI * R * R, I: (Math.PI * Math.pow(R, 4)) / 4, c: R, shape: 'circle', R: R };
    }
    if (this.type === 'manual') {
      return { A: p.A, I: p.I, c: p.c, shape: 'manual' };
    }
    throw new Error('Tipo de seccion desconocido: ' + this.type);
  };

  /**
   * Elemento de portico 2D (barra entre dos nodos).
   * E en MPa. section: instancia de Section.
   */
  function Element(id, nodeI, nodeJ, E, section) {
    this.id = id;
    this.nodeI = nodeI;
    this.nodeJ = nodeJ;
    this.E = E;
    this.section = section;
    // Carga distribuida transversal uniforme, magnitud en N/mm.
    // Convencion: positivo = actua en sentido local -y (hacia "abajo" del
    // elemento tal como se dibuja, analogo a peso propio). Ver frameElement.js.
    this.udl = 0;
  }

  Element.prototype.length = function () {
    var dx = this.nodeJ.x - this.nodeI.x;
    var dy = this.nodeJ.y - this.nodeI.y;
    return Math.sqrt(dx * dx + dy * dy);
  };

  Element.prototype.angle = function () {
    var dx = this.nodeJ.x - this.nodeI.x;
    var dy = this.nodeJ.y - this.nodeI.y;
    return Math.atan2(dy, dx);
  };

  /** Carga puntual nodal: fx, fy en N; m en N*mm. */
  function NodalLoad(nodeId, fx, fy, m) {
    this.nodeId = nodeId;
    this.fx = fx || 0;
    this.fy = fy || 0;
    this.m = m || 0;
  }

  function Model() {
    this.nodes = [];
    this.elements = [];
    this.nodalLoads = [];
    this._nodeSeq = 1;
    this._elemSeq = 1;
  }

  Model.prototype.addNode = function (xMm, yMm) {
    var n = new Node(this._nodeSeq++, xMm, yMm);
    this.nodes.push(n);
    return n;
  };

  Model.prototype.addElement = function (nodeI, nodeJ, E, section) {
    var e = new Element(this._elemSeq++, nodeI, nodeJ, E, section);
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

  Model.prototype.addNodalLoad = function (nodeId, fx, fy, m) {
    var l = new NodalLoad(nodeId, fx, fy, m);
    this.nodalLoads.push(l);
    return l;
  };

  Model.prototype.dofCount = function () {
    return this.nodes.length * 3;
  };

  /** indice global del DOF ux/uy/rz del nodo (orden de nodes[]) */
  Model.prototype.dofIndex = function (nodeId) {
    var idx = this.nodes.findIndex(function (n) { return n.id === nodeId; });
    if (idx < 0) throw new Error('Nodo no encontrado: ' + nodeId);
    return idx * 3; // ux en idx*3, uy en idx*3+1, rz en idx*3+2
  };

  root.FEM = root.FEM || {};
  root.FEM.RESTRAINT = RESTRAINT;
  root.FEM.Node = Node;
  root.FEM.Section = Section;
  root.FEM.Element = Element;
  root.FEM.NodalLoad = NodalLoad;
  root.FEM.Model = Model;
})(typeof window !== 'undefined' ? window : global);
