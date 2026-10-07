/**
 * Estado de la aplicacion e interaccion de UI. Traduce eventos de mouse
 * sobre el canvas a cambios en el modelo (model.js), dispara el solver
 * (solver.js + stress.js) y pinta resultados (render.js).
 */
(function () {
  'use strict';

  var FEM = window.FEM;
  var Units = FEM.Units;

  var canvas = document.getElementById('canvas');
  var ctx = canvas.getContext('2d');
  var hintEl = document.getElementById('hint');
  var propsPanel = document.getElementById('propsPanel');
  var resultsPanel = document.getElementById('resultsPanel');

  var MATERIAL_PRESETS = {
    acero: { label: 'Acero (E=200000 MPa)', E: 200000 },
    hormigon: { label: 'Hormigón (E=25000 MPa)', E: 25000 },
    aluminio: { label: 'Aluminio (E=70000 MPa)', E: 70000 }
  };

  var state = {
    model: new FEM.Model(),
    mode: 'addNode',
    selection: null,
    pendingElementNode: null,
    gridSize: 500,
    snapEnabled: true,
    lastResult: null,
    view: null
  };

  var HINTS = {
    addNode: 'Click en el lienzo para agregar un nodo (con snap a grilla de 0.5 m).',
    addElement: 'Click en un nodo existente y luego en otro para crear una barra entre ambos.',
    select: 'Click en un nodo o barra para ver y editar sus propiedades.',
    delete: 'Click en un nodo o barra para eliminarlo. Borrar un nodo borra tambien sus barras y cargas.'
  };

  function resizeCanvas() {
    var rect = canvas.getBoundingClientRect();
    canvas.width = Math.max(200, Math.round(rect.width));
    canvas.height = Math.max(200, Math.round(rect.height));
  }

  function currentDisplayOptions() {
    return {
      showM: document.getElementById('showM').checked,
      showV: document.getElementById('showV').checked,
      showN: document.getElementById('showN').checked,
      showDefl: document.getElementById('showDefl').checked,
      showVM: document.getElementById('showVM').checked
    };
  }

  function fitView() {
    state.view = FEM.render.computeView(canvas.width, canvas.height, state.model.nodes);
  }

  function render() {
    if (!state.view) fitView();
    var view = state.view;
    FEM.render.drawModel(ctx, view, canvas.width, canvas.height, state.model, state);

    if (state.lastResult) {
      var opts = currentDisplayOptions();
      state.model.elements.forEach(function (el) {
        var ef = state.lastResult.result.elementForces.get(el.id);
        var grid = state.lastResult.stressGrids.get(el.id);
        FEM.render.drawElementResults(ctx, view, el, ef, grid, state.lastResult.globalMax, opts);
      });
    }
  }

  function invalidateResults() {
    state.lastResult = null;
    renderResultsPlaceholder();
    var btn = document.getElementById('memoriaBtn');
    if (btn) btn.disabled = true;
  }

  function renderResultsPlaceholder() {
    resultsPanel.innerHTML = '<h2>Resultados</h2><p class="muted">Presiona "Calcular" para resolver el modelo.</p>';
  }

  // ---------------------------------------------------------------
  // Geometria / snapping / hit-testing
  // ---------------------------------------------------------------

  function snapMm(v) {
    if (!state.snapEnabled) return v;
    return Math.round(v / state.gridSize) * state.gridSize;
  }

  function nodeAtPixel(px, py, tolPx) {
    tolPx = tolPx || 14;
    var best = null, bestD = tolPx;
    state.model.nodes.forEach(function (n) {
      var p = state.view.toPx(n.x, n.y);
      var d = Math.hypot(p.x - px, p.y - py);
      if (d < bestD) { bestD = d; best = n; }
    });
    return best;
  }

  function elementAtPixel(px, py, tolPx) {
    tolPx = tolPx || 8;
    var best = null, bestD = tolPx;
    state.model.elements.forEach(function (el) {
      var a = state.view.toPx(el.nodeI.x, el.nodeI.y);
      var b = state.view.toPx(el.nodeJ.x, el.nodeJ.y);
      var d = distToSegment(px, py, a.x, a.y, b.x, b.y);
      if (d < bestD) { bestD = d; best = el; }
    });
    return best;
  }

  function distToSegment(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay;
    var len2 = dx * dx + dy * dy;
    var t = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    var cx = ax + t * dx, cy = ay + t * dy;
    return Math.hypot(px - cx, py - cy);
  }

  // ---------------------------------------------------------------
  // Modo / toolbar
  // ---------------------------------------------------------------

  function setMode(mode) {
    state.mode = mode;
    state.pendingElementNode = null;
    document.querySelectorAll('.tool-btn').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    hintEl.textContent = HINTS[mode] || '';
    render();
  }

  document.getElementById('toolbar').addEventListener('click', function (evt) {
    var btn = evt.target.closest('.tool-btn');
    if (btn && btn.dataset.mode) setMode(btn.dataset.mode);
  });

  document.getElementById('snapToggle').addEventListener('change', function (evt) {
    state.snapEnabled = evt.target.checked;
  });

  ['showM', 'showV', 'showN', 'showDefl', 'showVM'].forEach(function (id) {
    document.getElementById(id).addEventListener('change', render);
  });

  document.getElementById('clearBtn').addEventListener('click', function () {
    if (!confirm('¿Borrar todo el modelo (nodos, barras, cargas)?')) return;
    state.model = new FEM.Model();
    state.selection = null;
    invalidateResults();
    updatePropsPanel();
    fitView();
    render();
  });

  document.getElementById('calcBtn').addEventListener('click', calc);

  document.getElementById('fitBtn').addEventListener('click', function () {
    fitView();
    render();
  });

  canvas.addEventListener('wheel', function (evt) {
    evt.preventDefault();
    var rect = canvas.getBoundingClientRect();
    var px = evt.clientX - rect.left;
    var py = evt.clientY - rect.top;
    var factor = evt.deltaY < 0 ? 1.1 : 1 / 1.1;
    if (!state.view) fitView();
    state.view = FEM.render.zoomView(state.view, px, py, factor);
    render();
  }, { passive: false });

  // ---------------------------------------------------------------
  // Interaccion con el canvas
  // ---------------------------------------------------------------

  canvas.addEventListener('click', function (evt) {
    var rect = canvas.getBoundingClientRect();
    var px = evt.clientX - rect.left;
    var py = evt.clientY - rect.top;

    if (state.mode === 'addNode') {
      var wasEmpty = state.model.nodes.length === 0;
      var m = state.view.toModel(px, py);
      state.model.addNode(snapMm(m.x), snapMm(m.y));
      invalidateResults();
      if (wasEmpty) fitView();
      render();
      return;
    }

    if (state.mode === 'addElement') {
      var node = nodeAtPixel(px, py);
      if (!node) return;
      if (state.pendingElementNode == null) {
        state.pendingElementNode = node.id;
      } else if (state.pendingElementNode === node.id) {
        state.pendingElementNode = null;
      } else {
        var nodeI = state.model.nodes.find(function (n) { return n.id === state.pendingElementNode; });
        var section = new FEM.Section('rect', { b: 200, h: 400 });
        var el = state.model.addElement(nodeI, node, MATERIAL_PRESETS.acero.E, section);
        state.pendingElementNode = null;
        state.selection = { type: 'element', id: el.id };
        invalidateResults();
        updatePropsPanel();
      }
      render();
      return;
    }

    if (state.mode === 'select') {
      var n2 = nodeAtPixel(px, py);
      if (n2) {
        state.selection = { type: 'node', id: n2.id };
      } else {
        var e2 = elementAtPixel(px, py);
        state.selection = e2 ? { type: 'element', id: e2.id } : null;
      }
      updatePropsPanel();
      render();
      return;
    }

    if (state.mode === 'delete') {
      var n3 = nodeAtPixel(px, py);
      if (n3) {
        state.model.removeNode(n3.id);
      } else {
        var e3 = elementAtPixel(px, py);
        if (e3) state.model.removeElement(e3.id);
      }
      state.selection = null;
      invalidateResults();
      updatePropsPanel();
      render();
      return;
    }
  });

  // ---------------------------------------------------------------
  // Panel de propiedades
  // ---------------------------------------------------------------

  function restraintFromLabel(label) {
    return FEM.RESTRAINT[
      label === 'fixed' ? 'FIXED' : label === 'pinned' ? 'PINNED' : label === 'roller' ? 'ROLLER_X' : 'FREE'
    ];
  }

  // ---------------------------------------------------------------
  // Catalogo de perfiles (ver js/catalog.js)
  // ---------------------------------------------------------------

  function renderCatalogFields(el) {
    if (!FEM.Catalog.loaded) {
      var msg = FEM.Catalog.error
        ? 'No se pudo cargar el catálogo (' + FEM.Catalog.error + '). Si abriste el archivo directamente ' +
          '(file://), corre un servidor local (ver README) — los navegadores bloquean fetch() de JSON local sin servidor.'
        : 'Cargando catálogo…';
      return '<p class="muted">' + msg + '</p>';
    }
    var families = FEM.Catalog.families();
    var currentFamily = (el.catalogRef && el.catalogRef.family) || (families[0] && families[0].family);
    var familyOptions = families.map(function (f) {
      return '<option value="' + f.family + '"' + (f.family === currentFamily ? ' selected' : '') + '>' + f.label + ' (' + f.family + ')</option>';
    }).join('');
    return '<label>Familia<select id="f_catfamily">' + familyOptions + '</select></label>' +
      '<label>Perfil<select id="f_catprofile"></select></label>' +
      '<label>Eje a usar' +
      '<select id="f_cataxis">' +
      '<option value="strong"' + (!el.catalogRef || el.catalogRef.axis !== 'weak' ? ' selected' : '') + '>Fuerte (x-x) — uso típico en vigas/columnas</option>' +
      '<option value="weak"' + (el.catalogRef && el.catalogRef.axis === 'weak' ? ' selected' : '') + '>Débil (y-y)</option>' +
      '</select></label>' +
      '<div id="catalogSummary" class="catalog-summary"></div>';
  }

  function wireCatalogFields(el) {
    if (!FEM.Catalog.loaded) return;
    var familySelect = document.getElementById('f_catfamily');
    var profileSelect = document.getElementById('f_catprofile');
    var axisSelect = document.getElementById('f_cataxis');
    var summary = document.getElementById('catalogSummary');

    function populateProfiles() {
      var profiles = FEM.Catalog.byFamily(familySelect.value);
      var currentId = el.catalogRef && el.catalogRef.id;
      profileSelect.innerHTML = profiles.map(function (p) {
        return '<option value="' + p.id + '"' + (p.id === currentId ? ' selected' : '') + '>' +
          p.id + ' (' + p.weight_kg_m + ' kg/m)</option>';
      }).join('');
      updateSummary();
    }
    function updateSummary() {
      var profile = FEM.Catalog.findById(profileSelect.value);
      if (!profile) { summary.textContent = ''; return; }
      var sp = FEM.Catalog.toSectionParams(profile, axisSelect.value);
      summary.textContent = 'A=' + sp.A.toFixed(0) + ' mm², I=' + sp.I.toExponential(3) +
        ' mm⁴, c=' + sp.c.toFixed(1) + ' mm — fuente: ICHA (archivo subido por el usuario, ver data/catalog_icha.json)';
    }
    familySelect.addEventListener('change', populateProfiles);
    profileSelect.addEventListener('change', updateSummary);
    axisSelect.addEventListener('change', updateSummary);
    populateProfiles();
  }

  function updatePropsPanel() {
    if (!state.selection) {
      propsPanel.innerHTML = '<h2>Propiedades</h2><p class="muted">Selecciona un nodo o una barra para editarlo.</p>';
      return;
    }

    if (state.selection.type === 'node') {
      var node = state.model.nodes.find(function (n) { return n.id === state.selection.id; });
      if (!node) { state.selection = null; return updatePropsPanel(); }
      var existingLoad = state.model.nodalLoads.find(function (l) { return l.nodeId === node.id; });
      var fxKn = existingLoad ? Units.forceToUi(existingLoad.fx) : 0;
      var fyKn = existingLoad ? Units.forceToUi(existingLoad.fy) : 0;
      var mKnm = existingLoad ? Units.momentToUi(existingLoad.m) : 0;
      var currentLabel = FEM.render.restraintLabel(node);

      propsPanel.innerHTML =
        '<h2>Nodo #' + node.id + '</h2>' +
        '<label>Coordenadas (m)<br>x = ' + (node.x / 1000).toFixed(3) + ', y = ' + (node.y / 1000).toFixed(3) + '</label>' +
        '<label>Apoyo' +
        '<select id="f_restraint">' +
        '<option value="free"' + (currentLabel === 'free' ? ' selected' : '') + '>Libre</option>' +
        '<option value="pinned"' + (currentLabel === 'pinned' ? ' selected' : '') + '>Articulado (pin)</option>' +
        '<option value="roller"' + (currentLabel === 'roller' ? ' selected' : '') + '>Rodillo</option>' +
        '<option value="fixed"' + (currentLabel === 'fixed' ? ' selected' : '') + '>Empotrado</option>' +
        '</select></label>' +
        '<label>Carga puntual' +
        '<div class="field-row">' +
        '<div><input type="number" id="f_fx" value="' + fxKn + '" placeholder="Fx (kN)"></div>' +
        '<div><input type="number" id="f_fy" value="' + fyKn + '" placeholder="Fy (kN)"></div>' +
        '</div>' +
        '<input type="number" id="f_m" value="' + mKnm + '" placeholder="Momento (kN·m)" style="margin-top:6px"></label>' +
        '<button class="apply-btn" id="applyNode">Aplicar</button>' +
        '<button class="remove-btn" id="removeNode">Eliminar nodo</button>';

      document.getElementById('applyNode').addEventListener('click', function () {
        node.restraint = restraintFromLabel(document.getElementById('f_restraint').value);
        var fx = parseFloat(document.getElementById('f_fx').value) || 0;
        var fy = parseFloat(document.getElementById('f_fy').value) || 0;
        var m = parseFloat(document.getElementById('f_m').value) || 0;
        state.model.nodalLoads = state.model.nodalLoads.filter(function (l) { return l.nodeId !== node.id; });
        if (fx || fy || m) {
          var internal = Units.pointLoadToInternal(fx, fy, m);
          state.model.addNodalLoad(node.id, internal.fx, internal.fy, internal.m);
        }
        invalidateResults();
        render();
      });
      document.getElementById('removeNode').addEventListener('click', function () {
        state.model.removeNode(node.id);
        state.selection = null;
        invalidateResults();
        updatePropsPanel();
        render();
      });
      return;
    }

    if (state.selection.type === 'element') {
      var el = state.model.elements.find(function (e) { return e.id === state.selection.id; });
      if (!el) { state.selection = null; return updatePropsPanel(); }
      var secType = el.section.type;
      var p = el.section.params;
      var udlKnm = el.udl; // kN/m == N/mm numericamente, ver units.js

      var materialOptions = Object.keys(MATERIAL_PRESETS).map(function (key) {
        var preset = MATERIAL_PRESETS[key];
        var selected = preset.E === el.E ? ' selected' : '';
        return '<option value="' + key + '"' + selected + '>' + preset.label + '</option>';
      }).join('');
      var customSelected = !Object.keys(MATERIAL_PRESETS).some(function (k) { return MATERIAL_PRESETS[k].E === el.E; });

      propsPanel.innerHTML =
        '<h2>Barra #' + el.id + ' (L = ' + (el.length() / 1000).toFixed(3) + ' m)</h2>' +
        '<label>Material' +
        '<select id="f_material">' + materialOptions + '<option value="custom"' + (customSelected ? ' selected' : '') + '>Personalizado</option></select></label>' +
        '<label>E (MPa)<input type="number" id="f_E" value="' + el.E + '"></label>' +
        '<label>Tipo de sección' +
        '<select id="f_sectype">' +
        '<option value="rect"' + (secType === 'rect' ? ' selected' : '') + '>Rectangular</option>' +
        '<option value="circle"' + (secType === 'circle' ? ' selected' : '') + '>Circular sólida</option>' +
        '<option value="manual"' + (secType === 'manual' ? ' selected' : '') + '>Manual (A, I, c)</option>' +
        '<option value="catalog"' + (secType === 'manual' && el.catalogRef ? ' selected' : '') + '>Catálogo de perfiles</option>' +
        '</select></label>' +
        '<div id="sectionFields"></div>' +
        '<label>Carga distribuida uniforme w (kN/m)<br>' +
        '<input type="number" id="f_udl" value="' + udlKnm + '">' +
        '<span class="muted">positivo = sentido -y local (hacia "abajo" tal como se dibujó la barra)</span></label>' +
        '<button class="apply-btn" id="applyElement">Aplicar</button>' +
        '<button class="remove-btn" id="removeElement">Eliminar barra</button>';

      function renderSectionFields(type) {
        var html = '';
        if (type === 'rect') {
          html = '<div class="field-row">' +
            '<div><label>b (mm)<input type="number" id="f_b" value="' + (p.b || 200) + '"></label></div>' +
            '<div><label>h (mm)<input type="number" id="f_h" value="' + (p.h || 400) + '"></label></div>' +
            '</div>';
        } else if (type === 'circle') {
          html = '<label>d (mm)<input type="number" id="f_d" value="' + (p.d || 300) + '"></label>';
        } else if (type === 'manual') {
          html = '<div class="field-row">' +
            '<div><label>A (mm²)<input type="number" id="f_A" value="' + (p.A || 10000) + '"></label></div>' +
            '<div><label>I (mm⁴)<input type="number" id="f_I" value="' + (p.I || 1e8) + '"></label></div>' +
            '</div><label>c, distancia a fibra extrema (mm)<input type="number" id="f_c" value="' + (p.c || 100) + '"></label>' +
            '<p class="muted">Sección manual: no hay geometría real para calcular corte (τ); el mapa von Mises usará solo flexión+axial.</p>';
        } else if (type === 'catalog') {
          html = renderCatalogFields(el);
        }
        document.getElementById('sectionFields').innerHTML = html;
        if (type === 'catalog') wireCatalogFields(el);
      }
      renderSectionFields(secType === 'manual' && el.catalogRef ? 'catalog' : secType);
      document.getElementById('f_sectype').addEventListener('change', function (evt) {
        renderSectionFields(evt.target.value);
      });
      document.getElementById('f_material').addEventListener('change', function (evt) {
        var val = evt.target.value;
        if (MATERIAL_PRESETS[val]) document.getElementById('f_E').value = MATERIAL_PRESETS[val].E;
      });

      document.getElementById('applyElement').addEventListener('click', function () {
        el.E = parseFloat(document.getElementById('f_E').value) || el.E;
        var type = document.getElementById('f_sectype').value;
        if (type === 'rect') {
          el.section = new FEM.Section('rect', {
            b: parseFloat(document.getElementById('f_b').value) || 1,
            h: parseFloat(document.getElementById('f_h').value) || 1
          });
          el.catalogRef = null;
        } else if (type === 'circle') {
          el.section = new FEM.Section('circle', { d: parseFloat(document.getElementById('f_d').value) || 1 });
          el.catalogRef = null;
        } else if (type === 'catalog') {
          var profileId = document.getElementById('f_catprofile').value;
          var axis = document.getElementById('f_cataxis').value;
          var profile = FEM.Catalog.findById(profileId);
          if (profile) {
            var sp = FEM.Catalog.toSectionParams(profile, axis);
            el.section = new FEM.Section('manual', sp);
            el.catalogRef = { id: profile.id, family: profile.family, axis: axis, label: profile.familyLabel };
          }
        } else {
          el.section = new FEM.Section('manual', {
            A: parseFloat(document.getElementById('f_A').value) || 1,
            I: parseFloat(document.getElementById('f_I').value) || 1,
            c: parseFloat(document.getElementById('f_c').value) || 1
          });
          el.catalogRef = null;
        }
        el.udl = Units.distributedLoadToInternal(parseFloat(document.getElementById('f_udl').value) || 0);
        invalidateResults();
        render();
      });
      document.getElementById('removeElement').addEventListener('click', function () {
        state.model.removeElement(el.id);
        state.selection = null;
        invalidateResults();
        updatePropsPanel();
        render();
      });
      return;
    }
  }

  // ---------------------------------------------------------------
  // Calculo y resultados
  // ---------------------------------------------------------------

  function calc() {
    var result;
    try {
      result = FEM.solver.solve(state.model);
    } catch (e) {
      state.lastResult = null;
      resultsPanel.innerHTML = '<h2>Resultados</h2><p class="error-box">Error: ' + e.message + '</p>';
      render();
      return;
    }

    var stressGrids = new Map();
    var globalMax = { N: 0, V: 0, M: 0, defl: 0, vonMises: 0 };
    var vmLocation = null;

    state.model.elements.forEach(function (el) {
      var ef = result.elementForces.get(el.id);
      var grid = FEM.stress.elementStressGrid(FEM.solver, ef, el.section, 24, 11);
      stressGrids.set(el.id, grid);
      if (grid.max && grid.max.vonMises > globalMax.vonMises) {
        globalMax.vonMises = grid.max.vonMises;
        vmLocation = { elementId: el.id, x: grid.max.x, y: grid.max.y };
      }
      var nx = 24;
      for (var i = 0; i <= nx; i++) {
        var x = (ef.L * i) / nx;
        var f = FEM.solver.internalForcesAt(ef, x);
        globalMax.N = Math.max(globalMax.N, Math.abs(f.N));
        globalMax.V = Math.max(globalMax.V, Math.abs(f.V));
        globalMax.M = Math.max(globalMax.M, Math.abs(f.M));
        globalMax.defl = Math.max(globalMax.defl, Math.abs(FEM.solver.deflectionAt(ef, x)));
      }
    });

    state.lastResult = { result: result, stressGrids: stressGrids, globalMax: globalMax, vmLocation: vmLocation };
    document.getElementById('memoriaBtn').disabled = false;
    renderResultsPanel();
    render();
  }

  function renderResultsPanel() {
    var lr = state.lastResult;
    var html = '<h2>Resultados</h2>';

    html += '<h3 style="font-size:12px;color:#8b949e;margin:10px 0 4px">Reacciones</h3>';
    html += '<table class="results-table"><tr><th>Nodo</th><th>Fx (kN)</th><th>Fy (kN)</th><th>M (kN·m)</th></tr>';
    state.model.nodes.forEach(function (node) {
      var r = node.restraint;
      if (!(r.ux || r.uy || r.rz)) return;
      var rx = lr.result.reactions.get(node.id);
      html += '<tr><td>#' + node.id + '</td><td>' + Units.forceToUi(rx.fx).toFixed(2) +
        '</td><td>' + Units.forceToUi(rx.fy).toFixed(2) + '</td><td>' + Units.momentToUi(rx.m).toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:12px;color:#8b949e;margin:10px 0 4px">Máximos por barra</h3>';
    html += '<table class="results-table"><tr><th>Barra</th><th>|N| (kN)</th><th>|V| (kN)</th><th>|M| (kN·m)</th><th>δ máx (mm)</th></tr>';
    state.model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var maxN = 0, maxV = 0, maxM = 0, maxD = 0;
      var nx = 24;
      for (var i = 0; i <= nx; i++) {
        var x = (ef.L * i) / nx;
        var f = FEM.solver.internalForcesAt(ef, x);
        maxN = Math.max(maxN, Math.abs(f.N));
        maxV = Math.max(maxV, Math.abs(f.V));
        maxM = Math.max(maxM, Math.abs(f.M));
        maxD = Math.max(maxD, Math.abs(FEM.solver.deflectionAt(ef, x)));
      }
      html += '<tr><td>#' + el.id + '</td><td>' + Units.forceToUi(maxN).toFixed(2) + '</td><td>' +
        Units.forceToUi(maxV).toFixed(2) + '</td><td>' + Units.momentToUi(maxM).toFixed(2) + '</td><td>' + maxD.toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:12px;color:#8b949e;margin:10px 0 4px">Diagramas por barra</h3>';
    state.model.elements.forEach(function (el) {
      html += '<div class="diagram-block"><h4>Barra #' + el.id + ' — Momento M(x)</h4>' +
        '<canvas id="diagM_' + el.id + '"></canvas></div>' +
        '<div class="diagram-block"><h4>Barra #' + el.id + ' — Corte V(x)</h4>' +
        '<canvas id="diagV_' + el.id + '"></canvas></div>';
    });

    html += '<h3 style="font-size:12px;color:#8b949e;margin:10px 0 4px">Von Mises máximo global</h3>';
    html += '<p>' + lr.globalMax.vonMises.toFixed(2) + ' MPa';
    if (lr.vmLocation) {
      html += ' — barra #' + lr.vmLocation.elementId + ', x = ' + (lr.vmLocation.x / 1000).toFixed(3) +
        ' m, y = ' + lr.vmLocation.y.toFixed(1) + ' mm (desde eje neutro)';
    }
    html += '</p>';

    var allowable = parseFloat(document.getElementById('allowableStress').value);
    if (allowable > 0) {
      var fs = allowable / lr.globalMax.vonMises;
      html += '<p>Tensión admisible: ' + allowable.toFixed(1) + ' MPa — FS = ' + fs.toFixed(2) +
        ' <span class="' + (fs >= 1 ? 'pass">PASA' : 'fail">NO PASA') + '</span></p>';
    }

    resultsPanel.innerHTML = html;

    state.model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var pointsM = [], pointsV = [];
      var nx = 40;
      for (var i = 0; i <= nx; i++) {
        var x = (ef.L * i) / nx;
        var f = FEM.solver.internalForcesAt(ef, x);
        pointsM.push(Units.momentToUi(f.M));
        pointsV.push(Units.forceToUi(f.V));
      }
      drawMiniDiagram(document.getElementById('diagM_' + el.id), pointsM, '#4fd27a', 'kN·m');
      drawMiniDiagram(document.getElementById('diagV_' + el.id), pointsV, '#4fb8ff', 'kN');
    });
  }

  /**
   * Mini-diagrama de area (M(x) o V(x)) en un <canvas>: linea de base en 0,
   * relleno hasta la curva, con el valor maximo absoluto etiquetado.
   */
  function drawMiniDiagram(canvas, values, color, unit, theme) {
    if (!canvas) return;
    theme = theme || { grid: '#3a414c', text: '#c8ccd2' };
    // Resolucion interna fija (independiente del layout/CSS, que puede dar
    // 0 si el panel esta oculto en el momento de dibujar): el canvas se
    // escala visualmente via CSS (width:100%) pero se dibuja siempre a
    // esta resolucion.
    var w = 360, h = 70;
    canvas.width = w; canvas.height = h;
    var c = canvas.getContext('2d');
    c.clearRect(0, 0, w, h);

    var maxAbs = 0;
    values.forEach(function (v) { maxAbs = Math.max(maxAbs, Math.abs(v)); });
    var padL = 4, padR = 4, padT = 10, padB = 4;
    var plotW = w - padL - padR, plotH = h - padT - padB;
    var zeroY = padT + plotH / 2;
    var scale = maxAbs > 1e-9 ? (plotH / 2 - 2) / maxAbs : 0;

    c.strokeStyle = theme.grid; c.lineWidth = 1;
    c.beginPath(); c.moveTo(padL, zeroY); c.lineTo(w - padR, zeroY); c.stroke();

    c.beginPath();
    c.moveTo(padL, zeroY);
    values.forEach(function (v, i) {
      var x = padL + (plotW * i) / (values.length - 1);
      var y = zeroY - v * scale;
      c.lineTo(x, y);
    });
    c.lineTo(w - padR, zeroY);
    c.closePath();
    c.fillStyle = color + '33';
    c.fill();
    c.strokeStyle = color; c.lineWidth = 1.5;
    c.beginPath();
    values.forEach(function (v, i) {
      var x = padL + (plotW * i) / (values.length - 1);
      var y = zeroY - v * scale;
      if (i === 0) c.moveTo(x, y); else c.lineTo(x, y);
    });
    c.stroke();

    c.fillStyle = theme.text; c.font = '10px sans-serif'; c.textAlign = 'right';
    c.fillText('máx |' + maxAbs.toFixed(2) + '| ' + unit, w - padR, padT - 1);
  }

  document.getElementById('allowableStress').addEventListener('input', function () {
    if (state.lastResult) renderResultsPanel();
  });

  // ---------------------------------------------------------------
  // Memoria de calculo
  // ---------------------------------------------------------------

  var memoriaMeta = { proyecto: '', autor: '', notas: '' };
  var memoriaOverlay = document.getElementById('memoriaOverlay');
  var memoriaBtn = document.getElementById('memoriaBtn');

  function renderMemoria() {
    var allowable = parseFloat(document.getElementById('allowableStress').value) || 0;
    var fecha = new Date().toLocaleDateString('es-CL', { year: 'numeric', month: 'long', day: 'numeric' });
    var result = FEM.Memoria.generate({
      model: state.model, lastResult: state.lastResult,
      meta: { proyecto: memoriaMeta.proyecto, autor: memoriaMeta.autor, fecha: fecha, notas: memoriaMeta.notas },
      allowableStress: allowable
    });

    var formHtml = '<div class="no-print" style="background:#f0f0f0;border:1px solid #ccc;border-radius:6px;padding:10px;margin-bottom:16px">' +
      '<div class="memoria-field"><label>Proyecto: <input type="text" id="mem_proyecto" value="' +
      (memoriaMeta.proyecto || '').replace(/"/g, '&quot;') + '" style="width:300px"></label></div>' +
      '<div class="memoria-field"><label>Autor: <input type="text" id="mem_autor" value="' +
      (memoriaMeta.autor || '').replace(/"/g, '&quot;') + '" style="width:300px"></label></div>' +
      '<div class="memoria-field"><label>Notas: <input type="text" id="mem_notas" value="' +
      (memoriaMeta.notas || '').replace(/"/g, '&quot;') + '" style="width:500px"></label></div>' +
      '</div>';

    document.getElementById('memoriaContent').innerHTML = formHtml + result.html;

    result.diagrams.forEach(function (d) {
      drawMiniDiagram(document.getElementById(d.canvasId), d.points, d.color, d.unit, { grid: '#ccc', text: '#444' });
    });

    ['mem_proyecto', 'mem_autor', 'mem_notas'].forEach(function (id) {
      var key = id.replace('mem_', '');
      document.getElementById(id).addEventListener('input', function (evt) {
        memoriaMeta[key] = evt.target.value;
        var display = document.getElementById('mem_display_' + key);
        if (display) {
          display.textContent = evt.target.value || (key === 'notas' ? '' : '(sin especificar)');
          if (key === 'notas') display.hidden = !evt.target.value;
        }
      });
    });
  }

  memoriaBtn.addEventListener('click', function () {
    renderMemoria();
    memoriaOverlay.hidden = false;
  });
  document.getElementById('memoriaCloseBtn').addEventListener('click', function () {
    memoriaOverlay.hidden = true;
  });
  document.getElementById('memoriaPrintBtn').addEventListener('click', function () {
    window.print();
  });

  // ---------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------

  window.addEventListener('resize', function () { resizeCanvas(); fitView(); render(); });
  resizeCanvas();
  fitView();
  setMode('addNode');
  renderResultsPlaceholder();
  render();

  FEM.Catalog.load().then(function () {
    if (state.selection && state.selection.type === 'element') updatePropsPanel();
  }).catch(function () {
    if (state.selection && state.selection.type === 'element') updatePropsPanel();
  });
})();
