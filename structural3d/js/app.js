/**
 * Estado de la aplicacion e interaccion de UI: tablas de nodos/barras/
 * cargas, visor 3D (render3d.js), calculo (solver.js + stress.js) y
 * panel de resultados.
 */
(function () {
  'use strict';

  var FEM3D = window.FEM3D;
  var Units = FEM3D.Units;

  var MATERIAL_PRESETS = {
    acero: { label: 'Acero', E: 200000, G: 77000 },
    hormigon: { label: 'Hormigón', E: 25000, G: 10400 },
    aluminio: { label: 'Aluminio', E: 70000, G: 26000 }
  };

  var state = {
    model: new FEM3D.Model(),
    selectedElementId: null,
    lastResult: null,
    ctx: null
  };

  var viewportEl = document.getElementById('viewport');
  state.ctx = FEM3DRender.init(viewportEl);
  window.addEventListener('resize', function () { state.ctx.resize(); });

  // ---------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () {
      document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.remove('active'); });
      document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.remove('active'); });
      btn.classList.add('active');
      document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
    });
  });

  function invalidateResults() {
    state.lastResult = null;
    document.getElementById('resultsContent').innerHTML = '<p class="muted">Presiona "Calcular" para resolver el modelo.</p>';
  }

  function render3D() {
    var selection = state.selectedElementId != null ? { type: 'element', id: state.selectedElementId } : null;
    FEM3DRender.drawModel(state.ctx, state.model, selection);
    if (state.lastResult) {
      FEM3DRender.drawResults(state.ctx, state.model, state.lastResult.result, state.lastResult.stressGrids,
        state.lastResult.globalMax.vonMises, currentDisplayOptions());
    } else {
      state.ctx.resultGroup.children.length = 0;
    }
  }

  function currentDisplayOptions() {
    return {
      showDefl: document.getElementById('showDefl').checked,
      showVM: document.getElementById('showVM').checked
    };
  }
  ['showDefl', 'showVM'].forEach(function (id) {
    document.getElementById(id).addEventListener('change', render3D);
  });

  function nodeOptionsHtml(selectedId) {
    return state.model.nodes.map(function (n) {
      return '<option value="' + n.id + '"' + (n.id === selectedId ? ' selected' : '') + '>#' + n.id + '</option>';
    }).join('');
  }

  function restraintFromLabel(label) {
    return FEM3D.RESTRAINT[label === 'fixed' ? 'FIXED' : label === 'pinned' ? 'PINNED' : 'FREE'];
  }

  // ---------------------------------------------------------------
  // Tabla de nodos
  // ---------------------------------------------------------------
  function renderNodesTable() {
    var tbody = document.querySelector('#nodesTable tbody');
    tbody.innerHTML = state.model.nodes.map(function (n) {
      var label = FEM3DRender.restraintLabel(n);
      var ui = Units.nodeCoordToUi(n.x, n.y, n.z);
      return '<tr data-node-id="' + n.id + '">' +
        '<td>' + n.id + '</td>' +
        '<td><input type="number" step="any" data-field="x" value="' + ui.x.toFixed(3) + '"></td>' +
        '<td><input type="number" step="any" data-field="y" value="' + ui.y.toFixed(3) + '"></td>' +
        '<td><input type="number" step="any" data-field="z" value="' + ui.z.toFixed(3) + '"></td>' +
        '<td><select data-field="restraint">' +
        '<option value="free"' + (label === 'free' ? ' selected' : '') + '>Libre</option>' +
        '<option value="pinned"' + (label === 'pinned' ? ' selected' : '') + '>Pin (3D)</option>' +
        '<option value="fixed"' + (label === 'fixed' ? ' selected' : '') + '>Fijo</option>' +
        '</select></td>' +
        '<td><button class="del-btn" data-action="del">✕</button></td>' +
        '</tr>';
    }).join('');
  }

  document.querySelector('#nodesTable tbody').addEventListener('input', function (evt) {
    var tr = evt.target.closest('tr');
    if (!tr) return;
    var node = state.model.nodes.find(function (n) { return n.id === Number(tr.dataset.nodeId); });
    if (!node) return;
    var field = evt.target.dataset.field;
    var val = parseFloat(evt.target.value) || 0;
    var internal = Units.nodeCoordToInternal(
      field === 'x' ? val : Units.nodeCoordToUi(node.x, node.y, node.z).x,
      field === 'y' ? val : Units.nodeCoordToUi(node.x, node.y, node.z).y,
      field === 'z' ? val : Units.nodeCoordToUi(node.x, node.y, node.z).z
    );
    node.x = internal.x; node.y = internal.y; node.z = internal.z;
    invalidateResults();
    render3D();
  });
  document.querySelector('#nodesTable tbody').addEventListener('change', function (evt) {
    if (evt.target.dataset.field !== 'restraint') return;
    var tr = evt.target.closest('tr');
    var node = state.model.nodes.find(function (n) { return n.id === Number(tr.dataset.nodeId); });
    if (!node) return;
    node.restraint = restraintFromLabel(evt.target.value);
    invalidateResults();
    render3D();
  });
  document.querySelector('#nodesTable tbody').addEventListener('click', function (evt) {
    if (evt.target.dataset.action !== 'del') return;
    var tr = evt.target.closest('tr');
    state.model.removeNode(Number(tr.dataset.nodeId));
    invalidateResults();
    renderAll();
  });
  document.getElementById('addNodeBtn').addEventListener('click', function () {
    state.model.addNode(0, 0, 0);
    invalidateResults();
    renderAll();
  });

  // ---------------------------------------------------------------
  // Tabla de barras + panel de edicion
  // ---------------------------------------------------------------
  function sectionSummary(section) {
    var p = section.params;
    if (section.type === 'rect') return 'Rect ' + p.b + '×' + p.h + ' mm';
    if (section.type === 'circle') return 'Ø' + p.d + ' mm';
    return 'Manual';
  }

  function renderElementsTable() {
    var tbody = document.querySelector('#elementsTable tbody');
    tbody.innerHTML = state.model.elements.map(function (el) {
      var isSel = state.selectedElementId === el.id;
      return '<tr data-el-id="' + el.id + '" style="' + (isSel ? 'outline:2px solid var(--accent)' : '') + '">' +
        '<td>' + el.id + '</td><td>#' + el.nodeI.id + '</td><td>#' + el.nodeJ.id + '</td>' +
        '<td>' + el.E + '</td><td>' + sectionSummary(el.section) + '</td>' +
        '<td><button class="del-btn" data-action="del">✕</button></td></tr>';
    }).join('');
  }

  document.querySelector('#elementsTable tbody').addEventListener('click', function (evt) {
    var tr = evt.target.closest('tr');
    if (!tr) return;
    var id = Number(tr.dataset.elId);
    if (evt.target.dataset.action === 'del') {
      state.model.removeElement(id);
      if (state.selectedElementId === id) state.selectedElementId = null;
      invalidateResults();
      renderAll();
      return;
    }
    state.selectedElementId = id;
    renderElementsTable();
    renderElementEdit();
    render3D();
  });

  document.getElementById('addElementBtn').addEventListener('click', function () {
    if (state.model.nodes.length < 2) { alert('Necesitas al menos 2 nodos.'); return; }
    var n1 = state.model.nodes[0], n2 = state.model.nodes[1];
    var section = new FEM3D.Section('rect', { b: 200, h: 400 });
    var el = state.model.addElement(n1, n2, MATERIAL_PRESETS.acero.E, MATERIAL_PRESETS.acero.G, section);
    state.selectedElementId = el.id;
    invalidateResults();
    renderAll();
  });

  function renderElementEdit() {
    var container = document.getElementById('elementEdit');
    var el = state.model.elements.find(function (e) { return e.id === state.selectedElementId; });
    if (!el) { container.innerHTML = '<p class="muted">Selecciona una barra en la tabla para editarla.</p>'; return; }

    var p = el.section.params;
    var matButtons = Object.keys(MATERIAL_PRESETS).map(function (k) {
      return '<button type="button" class="tool-btn" data-preset="' + k + '" style="font-size:10px;padding:4px 6px">' +
        MATERIAL_PRESETS[k].label + '</button>';
    }).join(' ');

    container.innerHTML =
      '<h3 style="font-size:12px;color:var(--muted);margin:4px 0">Editar barra #' + el.id + '</h3>' +
      '<label>Nodo I / Nodo J<div style="display:flex;gap:6px">' +
      '<select id="ee_nodeI" style="flex:1">' + nodeOptionsHtml(el.nodeI.id) + '</select>' +
      '<select id="ee_nodeJ" style="flex:1">' + nodeOptionsHtml(el.nodeJ.id) + '</select></div></label>' +
      '<label>Material rápido: ' + matButtons + '</label>' +
      '<div style="display:flex;gap:6px">' +
      '<label style="flex:1">E (MPa)<input type="number" id="ee_E" value="' + el.E + '"></label>' +
      '<label style="flex:1">G (MPa)<input type="number" id="ee_G" value="' + el.G + '"></label>' +
      '</div>' +
      '<label>Sección<select id="ee_sectype">' +
      '<option value="rect"' + (el.section.type === 'rect' ? ' selected' : '') + '>Rectangular</option>' +
      '<option value="circle"' + (el.section.type === 'circle' ? ' selected' : '') + '>Circular sólida</option>' +
      '</select></label>' +
      '<div id="ee_sectionFields"></div>' +
      '<div style="display:flex;gap:6px">' +
      '<label style="flex:1">UDLy (kN/m)<input type="number" id="ee_udlY" value="' + el.udlY + '"></label>' +
      '<label style="flex:1">UDLz (kN/m)<input type="number" id="ee_udlZ" value="' + el.udlZ + '"></label>' +
      '<label style="flex:1">β (°)<input type="number" id="ee_beta" value="' + el.beta + '"></label>' +
      '</div>' +
      '<button class="apply-btn" id="ee_apply">Aplicar</button>';

    function renderSectionFields(type) {
      var html;
      if (type === 'rect') {
        html = '<div style="display:flex;gap:6px">' +
          '<label style="flex:1">b -y- (mm)<input type="number" id="ee_b" value="' + (p.b || 200) + '"></label>' +
          '<label style="flex:1">h -z- (mm)<input type="number" id="ee_h" value="' + (p.h || 400) + '"></label>' +
          '</div>';
      } else {
        html = '<label>d (mm)<input type="number" id="ee_d" value="' + (p.d || 300) + '"></label>';
      }
      document.getElementById('ee_sectionFields').innerHTML = html;
    }
    renderSectionFields(el.section.type);
    document.getElementById('ee_sectype').addEventListener('change', function (evt) { renderSectionFields(evt.target.value); });
    container.querySelectorAll('[data-preset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var preset = MATERIAL_PRESETS[btn.dataset.preset];
        document.getElementById('ee_E').value = preset.E;
        document.getElementById('ee_G').value = preset.G;
      });
    });

    document.getElementById('ee_apply').addEventListener('click', function () {
      var nodeI = state.model.nodes.find(function (n) { return n.id === Number(document.getElementById('ee_nodeI').value); });
      var nodeJ = state.model.nodes.find(function (n) { return n.id === Number(document.getElementById('ee_nodeJ').value); });
      if (nodeI) el.nodeI = nodeI;
      if (nodeJ) el.nodeJ = nodeJ;
      el.E = parseFloat(document.getElementById('ee_E').value) || el.E;
      el.G = parseFloat(document.getElementById('ee_G').value) || el.G;
      var type = document.getElementById('ee_sectype').value;
      if (type === 'rect') {
        el.section = new FEM3D.Section('rect', {
          b: parseFloat(document.getElementById('ee_b').value) || 1,
          h: parseFloat(document.getElementById('ee_h').value) || 1
        });
      } else {
        el.section = new FEM3D.Section('circle', { d: parseFloat(document.getElementById('ee_d').value) || 1 });
      }
      el.udlY = Units.distributedLoadToInternal(parseFloat(document.getElementById('ee_udlY').value) || 0);
      el.udlZ = Units.distributedLoadToInternal(parseFloat(document.getElementById('ee_udlZ').value) || 0);
      el.beta = parseFloat(document.getElementById('ee_beta').value) || 0;
      invalidateResults();
      renderAll();
    });
  }

  // ---------------------------------------------------------------
  // Tabla de cargas
  // ---------------------------------------------------------------
  function renderLoadsTable() {
    var tbody = document.querySelector('#loadsTable tbody');
    tbody.innerHTML = state.model.nodalLoads.map(function (l, idx) {
      var fx = Units.forceToUi(l.fx), fy = Units.forceToUi(l.fy), fz = Units.forceToUi(l.fz);
      var mx = Units.momentToUi(l.mx), my = Units.momentToUi(l.my), mz = Units.momentToUi(l.mz);
      return '<tr data-load-idx="' + idx + '">' +
        '<td><select data-field="node">' + nodeOptionsHtml(l.nodeId) + '</select></td>' +
        '<td><input type="number" step="any" data-field="fx" value="' + fx + '"></td>' +
        '<td><input type="number" step="any" data-field="fy" value="' + fy + '"></td>' +
        '<td><input type="number" step="any" data-field="fz" value="' + fz + '"></td>' +
        '<td><input type="number" step="any" data-field="mx" value="' + mx + '"></td>' +
        '<td><input type="number" step="any" data-field="my" value="' + my + '"></td>' +
        '<td><input type="number" step="any" data-field="mz" value="' + mz + '"></td>' +
        '<td><button class="del-btn" data-action="del">✕</button></td></tr>';
    }).join('');
  }

  function loadFromRow(tr) {
    var idx = Number(tr.dataset.loadIdx);
    return state.model.nodalLoads[idx];
  }

  document.querySelector('#loadsTable tbody').addEventListener('input', function (evt) {
    var tr = evt.target.closest('tr');
    if (!tr) return;
    var load = loadFromRow(tr);
    if (!load) return;
    var field = evt.target.dataset.field;
    var val = parseFloat(evt.target.value) || 0;
    if (field === 'fx') load.fx = val * Units.KN_TO_N;
    else if (field === 'fy') load.fy = val * Units.KN_TO_N;
    else if (field === 'fz') load.fz = val * Units.KN_TO_N;
    else if (field === 'mx') load.mx = val * Units.KNM_TO_NMM;
    else if (field === 'my') load.my = val * Units.KNM_TO_NMM;
    else if (field === 'mz') load.mz = val * Units.KNM_TO_NMM;
    invalidateResults();
    render3D();
  });
  document.querySelector('#loadsTable tbody').addEventListener('change', function (evt) {
    if (evt.target.dataset.field !== 'node') return;
    var tr = evt.target.closest('tr');
    var load = loadFromRow(tr);
    if (load) load.nodeId = Number(evt.target.value);
    invalidateResults();
    render3D();
  });
  document.querySelector('#loadsTable tbody').addEventListener('click', function (evt) {
    if (evt.target.dataset.action !== 'del') return;
    var tr = evt.target.closest('tr');
    state.model.nodalLoads.splice(Number(tr.dataset.loadIdx), 1);
    invalidateResults();
    renderAll();
  });
  document.getElementById('addLoadBtn').addEventListener('click', function () {
    if (state.model.nodes.length === 0) { alert('Agrega al menos un nodo primero.'); return; }
    state.model.addNodalLoad(state.model.nodes[0].id, 0, 0, 0, 0, 0, 0);
    invalidateResults();
    renderAll();
  });

  // ---------------------------------------------------------------
  // Calculo y resultados
  // ---------------------------------------------------------------
  function calc() {
    var result;
    try {
      result = FEM3D.solver.solve(state.model);
    } catch (e) {
      state.lastResult = null;
      document.getElementById('resultsContent').innerHTML = '<p class="error-box">Error: ' + e.message + '</p>';
      render3D();
      return;
    }

    var stressGrids = new Map();
    var globalMax = { vonMises: 0 };
    var vmLocation = null;
    var torsionMaxByElement = new Map();

    state.model.elements.forEach(function (el) {
      var ef = result.elementForces.get(el.id);
      var grid = FEM3D.stress.elementStressGrid(FEM3D.solver, ef, el.section, 15, 7, 7);
      stressGrids.set(el.id, grid);
      torsionMaxByElement.set(el.id, grid.torsionMax);
      if (grid.max && grid.max.vonMises > globalMax.vonMises) {
        globalMax.vonMises = grid.max.vonMises;
        vmLocation = { elementId: el.id, x: grid.max.x, y: grid.max.y, z: grid.max.z };
      }
    });

    state.lastResult = { result: result, stressGrids: stressGrids, globalMax: globalMax, vmLocation: vmLocation, torsionMaxByElement: torsionMaxByElement };
    renderResultsPanel();
    render3D();
  }
  document.getElementById('calcBtn').addEventListener('click', calc);

  function renderResultsPanel() {
    var lr = state.lastResult;
    var html = '';
    html += '<h3 style="font-size:12px;color:var(--muted)">Reacciones</h3>';
    html += '<table class="results-table"><tr><th>Nodo</th><th>Fx</th><th>Fy</th><th>Fz</th><th>Mx</th><th>My</th><th>Mz</th></tr>';
    state.model.nodes.forEach(function (node) {
      var r = node.restraint;
      if (!(r.ux || r.uy || r.uz || r.rx || r.ry || r.rz)) return;
      var rx = lr.result.reactions.get(node.id);
      html += '<tr><td>#' + node.id + '</td><td>' + Units.forceToUi(rx.fx).toFixed(1) + '</td><td>' +
        Units.forceToUi(rx.fy).toFixed(1) + '</td><td>' + Units.forceToUi(rx.fz).toFixed(1) + '</td><td>' +
        Units.momentToUi(rx.mx).toFixed(2) + '</td><td>' + Units.momentToUi(rx.my).toFixed(2) + '</td><td>' +
        Units.momentToUi(rx.mz).toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:12px;color:var(--muted)">Máximos por barra</h3>';
    html += '<table class="results-table"><tr><th>Barra</th><th>|N|</th><th>|Vy|</th><th>|Vz|</th><th>|T|</th><th>|My|</th><th>|Mz|</th></tr>';
    state.model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var m = { N: 0, Vy: 0, Vz: 0, T: 0, My: 0, Mz: 0 };
      for (var i = 0; i <= 20; i++) {
        var f = FEM3D.solver.internalForcesAt(ef, (ef.L * i) / 20);
        Object.keys(m).forEach(function (k) { m[k] = Math.max(m[k], Math.abs(f[k])); });
      }
      html += '<tr><td>#' + el.id + '</td><td>' + Units.forceToUi(m.N).toFixed(2) + '</td><td>' +
        Units.forceToUi(m.Vy).toFixed(2) + '</td><td>' + Units.forceToUi(m.Vz).toFixed(2) + '</td><td>' +
        Units.momentToUi(m.T).toFixed(2) + '</td><td>' + Units.momentToUi(m.My).toFixed(2) + '</td><td>' +
        Units.momentToUi(m.Mz).toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:12px;color:var(--muted)">Von Mises máximo global</h3>';
    html += '<p>' + lr.globalMax.vonMises.toFixed(2) + ' MPa';
    if (lr.vmLocation) {
      html += ' — barra #' + lr.vmLocation.elementId + ', x=' + (lr.vmLocation.x / 1000).toFixed(3) +
        ' m, y=' + lr.vmLocation.y.toFixed(1) + ' mm, z=' + lr.vmLocation.z.toFixed(1) + ' mm';
    }
    html += '</p>';
    html += '<p class="muted">Nota: el corte por torsión en secciones rectangulares NO está incluido en este máximo ' +
      '(campo de Saint-Venant no cerrado) — se reporta aparte abajo y debe sumarse manualmente en el punto crítico si corresponde.</p>';

    var anyRectTorsion = false;
    state.model.elements.forEach(function (el) {
      var tmax = lr.torsionMaxByElement.get(el.id);
      if (tmax > 0) {
        anyRectTorsion = true;
        html += '<p class="muted">Barra #' + el.id + ': τ_torsión máx (aprox. Roark) = ' + tmax.toFixed(2) + ' MPa</p>';
      }
    });
    void anyRectTorsion;

    var allowable = parseFloat(document.getElementById('allowableStress').value);
    if (allowable > 0) {
      var fs = allowable / lr.globalMax.vonMises;
      html += '<p>Tensión admisible: ' + allowable.toFixed(1) + ' MPa — FS = ' + fs.toFixed(2) +
        ' <span class="' + (fs >= 1 ? 'pass">PASA' : 'fail">NO PASA') + '</span></p>';
    }

    document.getElementById('resultsContent').innerHTML = html;
  }
  document.getElementById('allowableStress').addEventListener('input', function () {
    if (state.lastResult) renderResultsPanel();
  });

  document.getElementById('fitBtn').addEventListener('click', function () {
    FEM3DRender.fitView(state.ctx, state.model.nodes);
  });

  document.getElementById('clearBtn').addEventListener('click', function () {
    if (!confirm('¿Borrar todo el modelo?')) return;
    state.model = new FEM3D.Model();
    state.selectedElementId = null;
    invalidateResults();
    renderAll();
    FEM3DRender.fitView(state.ctx, []);
  });

  function renderAll() {
    renderNodesTable();
    renderElementsTable();
    renderElementEdit();
    renderLoadsTable();
    render3D();
  }

  // ---------------------------------------------------------------
  // Modelo inicial de ejemplo (para que el visor no arranque vacio)
  // ---------------------------------------------------------------
  (function seedExample() {
    var n1 = state.model.addNode(0, 0, 0);
    var n2 = state.model.addNode(4000, 0, 0);
    var n3 = state.model.addNode(4000, 0, 3000);
    n1.restraint = FEM3D.RESTRAINT.FIXED;
    var section = new FEM3D.Section('rect', { b: 200, h: 400 });
    state.model.addElement(n1, n2, MATERIAL_PRESETS.acero.E, MATERIAL_PRESETS.acero.G, section);
    state.model.addElement(n2, n3, MATERIAL_PRESETS.acero.E, MATERIAL_PRESETS.acero.G, section);
    state.model.addNodalLoad(n3.id, 0, -5000, 0, 0, 0, 0);
  })();

  renderAll();
  FEM3DRender.fitView(state.ctx, state.model.nodes);
})();
