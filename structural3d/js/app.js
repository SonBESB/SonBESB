/**
 * Estado de la aplicacion e interaccion de UI: boceto sincronizado en 3
 * paneles 2D (Planta/Frontal/Lateral, sketch2d.js) + vista 3D (render3d.js)
 * como confirmacion visual, tablas de respaldo (nodos/barras/cargas),
 * calculo (solver.js + stress.js) y panel de resultados.
 */
(function () {
  'use strict';

  var FEM3D = window.FEM3D;
  var Units = FEM3D.Units;
  var Sketch = FEM3D.Sketch;

  var MATERIAL_PRESETS = {
    acero: { label: 'Acero', E: 200000, G: 77000 },
    hormigon: { label: 'Hormigón', E: 25000, G: 10400 },
    aluminio: { label: 'Aluminio', E: 70000, G: 26000 }
  };

  var state = {
    model: new FEM3D.Model(),
    mode: 'addNode',
    selection: null, // {type:'node'|'element', id}
    pendingElementNode: null,
    gridSize: 500, // mm
    snapEnabled: true,
    activeCoords: { x: 0, y: 0, z: 0 }, // mm — eje oculto al crear nodos
    activeProfile: {
      E: MATERIAL_PRESETS.acero.E, G: MATERIAL_PRESETS.acero.G,
      sectionType: 'rect',
      rectParams: { b: 200, h: 400 },
      circleParams: { d: 300 },
      catalogRef: null
    },
    lastResult: null,
    ctx: null,
    sketch: {}
  };

  var viewportEl = document.getElementById('viewport');
  state.ctx = FEM3DRender.init(viewportEl);

  // ---------------------------------------------------------------
  // Paneles de boceto 2D (Planta/Frontal/Lateral)
  // ---------------------------------------------------------------

  ['xy', 'xz', 'yz'].forEach(function (key) {
    var canvasId = { xy: 'canvasXY', xz: 'canvasXZ', yz: 'canvasYZ' }[key];
    var canvas = document.getElementById(canvasId);
    state.sketch[key] = { canvas: canvas, ctx: canvas.getContext('2d'), view: null };
  });

  function resizeSketchCanvas(sv) {
    var rect = sv.canvas.getBoundingClientRect();
    sv.canvas.width = Math.max(100, Math.round(rect.width));
    sv.canvas.height = Math.max(100, Math.round(rect.height));
  }

  function fitSketchView(key) {
    var sv = state.sketch[key];
    var proj = Sketch.PROJECTIONS[key];
    var pts = state.model.nodes.map(function (n) { return Sketch.projUV(n, proj); });
    sv.view = Sketch.computeView(sv.canvas.width, sv.canvas.height, pts);
  }
  function fitAllSketchViews() { ['xy', 'xz', 'yz'].forEach(fitSketchView); }

  function renderSketchView(key) {
    var sv = state.sketch[key];
    if (!sv.view) fitSketchView(key);
    Sketch.drawSketchView(sv.ctx, sv.view, sv.canvas.width, sv.canvas.height, state.model, key, {
      gridSize: state.gridSize, selection: state.selection, pendingElementNode: state.pendingElementNode
    });
  }
  function renderAllSketchViews() { ['xy', 'xz', 'yz'].forEach(renderSketchView); }

  function snapMm(v) {
    if (!state.snapEnabled) return v;
    return Math.round(v / state.gridSize) * state.gridSize;
  }

  function syncActiveCoordInputs() {
    var ui = Units.nodeCoordToUi(state.activeCoords.x, state.activeCoords.y, state.activeCoords.z);
    document.getElementById('activeX').value = ui.x.toFixed(3);
    document.getElementById('activeY').value = ui.y.toFixed(3);
    document.getElementById('activeZ').value = ui.z.toFixed(3);
  }
  ['activeX', 'activeY', 'activeZ'].forEach(function (id, idx) {
    var axis = ['x', 'y', 'z'][idx];
    document.getElementById(id).addEventListener('input', function (evt) {
      state.activeCoords[axis] = (parseFloat(evt.target.value) || 0) * Units.M_TO_MM;
    });
  });

  function handleSketchClick(key, evt) {
    var sv = state.sketch[key];
    var proj = Sketch.PROJECTIONS[key];
    var rect = sv.canvas.getBoundingClientRect();
    var px = evt.clientX - rect.left, py = evt.clientY - rect.top;
    if (!sv.view) fitSketchView(key);

    if (state.mode === 'addNode') {
      var wasEmpty = state.model.nodes.length === 0;
      var m = sv.view.toModel(px, py);
      var u = snapMm(m.u), v = snapMm(m.v);
      var coords = Sketch.uvToCoords(proj, u, v, state.activeCoords[proj.w]);
      var node = state.model.addNode(coords.x, coords.y, coords.z);
      state.activeCoords = { x: node.x, y: node.y, z: node.z };
      syncActiveCoordInputs();
      invalidateResults();
      if (wasEmpty) fitAllSketchViews();
      renderTablesAndSketches();
      return;
    }

    if (state.mode === 'addElement') {
      var hitNode = Sketch.nodeAtPixel(sv.view, state.model, key, px, py);
      if (!hitNode) return;
      if (state.pendingElementNode == null) {
        state.pendingElementNode = hitNode.id;
      } else if (state.pendingElementNode === hitNode.id) {
        state.pendingElementNode = null;
      } else {
        var nodeI = state.model.nodes.find(function (n) { return n.id === state.pendingElementNode; });
        var active = buildActiveSection();
        var el = state.model.addElement(nodeI, hitNode, active.E, active.G, active.section);
        el.catalogRef = active.catalogRef;
        state.pendingElementNode = null;
        state.selection = { type: 'element', id: el.id };
        invalidateResults();
        switchTab('props');
      }
      renderTablesAndSketches();
      return;
    }

    if (state.mode === 'select' || state.mode === 'addLoad') {
      var n2 = Sketch.nodeAtPixel(sv.view, state.model, key, px, py);
      if (n2) {
        state.selection = { type: 'node', id: n2.id };
        state.activeCoords = { x: n2.x, y: n2.y, z: n2.z };
        syncActiveCoordInputs();
      } else {
        var e2 = Sketch.elementAtPixel(sv.view, state.model, key, px, py);
        state.selection = e2 ? { type: 'element', id: e2.id } : null;
      }
      switchTab('props');
      renderTablesAndSketches();
      return;
    }

    if (state.mode === 'delete') {
      var n3 = Sketch.nodeAtPixel(sv.view, state.model, key, px, py);
      if (n3) {
        state.model.removeNode(n3.id);
        if (state.selection && state.selection.type === 'node' && state.selection.id === n3.id) state.selection = null;
      } else {
        var e3 = Sketch.elementAtPixel(sv.view, state.model, key, px, py);
        if (e3) {
          state.model.removeElement(e3.id);
          if (state.selection && state.selection.type === 'element' && state.selection.id === e3.id) state.selection = null;
        }
      }
      invalidateResults();
      renderTablesAndSketches();
      return;
    }
  }

  function handleSketchWheel(key, evt) {
    evt.preventDefault();
    var sv = state.sketch[key];
    if (!sv.view) fitSketchView(key);
    var rect = sv.canvas.getBoundingClientRect();
    var px = evt.clientX - rect.left, py = evt.clientY - rect.top;
    var factor = evt.deltaY < 0 ? 1.1 : 1 / 1.1;
    sv.view = Sketch.zoomView(sv.view, px, py, factor);
    renderSketchView(key);
  }

  ['xy', 'xz', 'yz'].forEach(function (key) {
    var sv = state.sketch[key];
    sv.canvas.addEventListener('click', function (evt) { handleSketchClick(key, evt); });
    sv.canvas.addEventListener('wheel', function (evt) { handleSketchWheel(key, evt); }, { passive: false });
  });

  // ---------------------------------------------------------------
  // Modo (+Nodo/+Barra/Seleccionar/Borrar)
  // ---------------------------------------------------------------

  var HINTS = {
    addNode: 'Click en cualquier panel para agregar un nodo. El eje que ese panel no puede fijar usa el valor "activo" del toolbar.',
    addElement: 'Click en un nodo (en cualquier panel) y luego en otro para crear una barra.',
    addLoad: 'Click en un NODO (en cualquier panel) = apoyo y carga puntual. Click en una BARRA = carga distribuida. Edítalo en "Propiedades".',
    select: 'Click en un nodo o barra (en cualquier panel) para editarlo en "Propiedades".',
    delete: 'Click en un nodo o barra para eliminarlo.'
  };

  function setMode(mode) {
    state.mode = mode;
    state.pendingElementNode = null;
    document.querySelectorAll('.tool-btn[data-mode]').forEach(function (btn) {
      btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    document.getElementById('hint').textContent = HINTS[mode] || '';
    renderAllSketchViews();
  }
  document.querySelectorAll('.tool-btn[data-mode]').forEach(function (btn) {
    btn.addEventListener('click', function () { setMode(btn.dataset.mode); });
  });
  document.getElementById('snapToggle').addEventListener('change', function (evt) {
    state.snapEnabled = evt.target.checked;
  });

  // ---------------------------------------------------------------
  // Perfil activo (material+seccion por defecto al dibujar barras)
  // ---------------------------------------------------------------

  function buildActiveSection() {
    var ap = state.activeProfile;
    if (ap.sectionType === 'circle') {
      return { E: ap.E, G: ap.G, section: new FEM3D.Section('circle', { d: ap.circleParams.d }), catalogRef: null };
    }
    if (ap.sectionType === 'catalog' && ap.catalogRef && FEM3D.Catalog.loaded) {
      var profile = FEM3D.Catalog.findById(ap.catalogRef.id);
      if (profile) {
        return {
          E: ap.E, G: ap.G, section: new FEM3D.Section('manual', FEM3D.Catalog.toSectionParams(profile)),
          catalogRef: { id: profile.id, family: profile.family, label: profile.familyLabel }
        };
      }
    }
    return { E: ap.E, G: ap.G, section: new FEM3D.Section('rect', { b: ap.rectParams.b, h: ap.rectParams.h }), catalogRef: null };
  }

  function renderActiveProfilePanel() {
    var ap = state.activeProfile;
    var container = document.getElementById('activeProfileFields');
    var matButtons = Object.keys(MATERIAL_PRESETS).map(function (k) {
      return '<button type="button" class="tool-btn" data-preset="' + k + '" style="font-size:10px;padding:4px 6px">' + MATERIAL_PRESETS[k].label + '</button>';
    }).join(' ');

    container.innerHTML =
      '<label>Material rápido: ' + matButtons + '</label>' +
      '<div class="field-row"><div><label>E (MPa)<input type="number" id="ap_E" value="' + ap.E + '"></label></div>' +
      '<div><label>G (MPa)<input type="number" id="ap_G" value="' + ap.G + '"></label></div></div>' +
      '<label>Tipo de sección<select id="ap_sectype">' +
      '<option value="rect"' + (ap.sectionType === 'rect' ? ' selected' : '') + '>Rectangular</option>' +
      '<option value="circle"' + (ap.sectionType === 'circle' ? ' selected' : '') + '>Circular sólida</option>' +
      '<option value="catalog"' + (ap.sectionType === 'catalog' ? ' selected' : '') + '>Catálogo de perfiles</option>' +
      '</select></label><div id="ap_sectionFields"></div>' +
      '<p class="muted">Se aplica a cada barra nueva. Las ya creadas no cambian.</p>';

    container.querySelectorAll('[data-preset]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var preset = MATERIAL_PRESETS[btn.dataset.preset];
        ap.E = preset.E; ap.G = preset.G;
        document.getElementById('ap_E').value = ap.E;
        document.getElementById('ap_G').value = ap.G;
      });
    });
    document.getElementById('ap_E').addEventListener('input', function (evt) { ap.E = parseFloat(evt.target.value) || ap.E; });
    document.getElementById('ap_G').addEventListener('input', function (evt) { ap.G = parseFloat(evt.target.value) || ap.G; });
    document.getElementById('ap_sectype').addEventListener('change', function (evt) {
      ap.sectionType = evt.target.value;
      renderActiveProfileSectionFields();
    });
    renderActiveProfileSectionFields();
  }

  function renderActiveProfileSectionFields() {
    var ap = state.activeProfile;
    var container = document.getElementById('ap_sectionFields');
    if (ap.sectionType === 'rect') {
      container.innerHTML = '<div class="field-row">' +
        '<div><label>b -y- (mm)<input type="number" id="ap_b" value="' + ap.rectParams.b + '"></label></div>' +
        '<div><label>h -z- (mm)<input type="number" id="ap_h" value="' + ap.rectParams.h + '"></label></div></div>';
      document.getElementById('ap_b').addEventListener('input', function (evt) { ap.rectParams.b = parseFloat(evt.target.value) || ap.rectParams.b; });
      document.getElementById('ap_h').addEventListener('input', function (evt) { ap.rectParams.h = parseFloat(evt.target.value) || ap.rectParams.h; });
    } else if (ap.sectionType === 'circle') {
      container.innerHTML = '<label>d (mm)<input type="number" id="ap_d" value="' + ap.circleParams.d + '"></label>';
      document.getElementById('ap_d').addEventListener('input', function (evt) { ap.circleParams.d = parseFloat(evt.target.value) || ap.circleParams.d; });
    } else if (ap.sectionType === 'catalog') {
      if (!FEM3D.Catalog.loaded) { container.innerHTML = '<p class="muted">Cargando catálogo…</p>'; return; }
      var families = FEM3D.Catalog.families();
      var currentFamily = (ap.catalogRef && ap.catalogRef.family) || (families[0] && families[0].family);
      container.innerHTML = '<label>Familia<select id="ap_catfamily">' + families.map(function (f) {
        return '<option value="' + f.family + '"' + (f.family === currentFamily ? ' selected' : '') + '>' + f.label + ' (' + f.family + ')</option>';
      }).join('') + '</select></label><label>Perfil<select id="ap_catprofile"></select></label>' +
        '<div id="ap_catalogSummary" class="catalog-summary"></div>';
      var familySelect = document.getElementById('ap_catfamily');
      var profileSelect = document.getElementById('ap_catprofile');
      var summary = document.getElementById('ap_catalogSummary');
      function update() {
        var profile = FEM3D.Catalog.findById(profileSelect.value);
        if (!profile) return;
        ap.catalogRef = { id: profile.id, family: profile.family };
        var sp = FEM3D.Catalog.toSectionParams(profile);
        summary.textContent = 'A=' + sp.A.toFixed(0) + ' mm², Iy=' + sp.Iy.toExponential(3) + ', Iz=' + sp.Iz.toExponential(3) + ' mm⁴';
      }
      function populateProfiles() {
        var profiles = FEM3D.Catalog.byFamily(familySelect.value);
        var currentId = ap.catalogRef && ap.catalogRef.id;
        profileSelect.innerHTML = profiles.map(function (p) {
          return '<option value="' + p.id + '"' + (p.id === currentId ? ' selected' : '') + '>' + p.id + '</option>';
        }).join('');
        update();
      }
      familySelect.addEventListener('change', populateProfiles);
      profileSelect.addEventListener('change', update);
      populateProfiles();
    }
  }

  // ---------------------------------------------------------------
  // Resultados / render orquestado
  // ---------------------------------------------------------------

  function invalidateResults() {
    state.lastResult = null;
    document.getElementById('resultsContent').innerHTML = '<p class="muted">Presiona "Calcular" para resolver el modelo.</p>';
    var btn = document.getElementById('memoriaBtn');
    if (btn) btn.disabled = true;
  }

  function render3D() {
    FEM3DRender.drawModel(state.ctx, state.model, state.selection);
    if (state.lastResult) {
      FEM3DRender.drawResults(state.ctx, state.model, state.lastResult.result, state.lastResult.stressGrids,
        state.lastResult.globalMax.vonMises, currentDisplayOptions());
    } else {
      state.ctx.resultGroup.children.length = 0;
    }
  }
  function currentDisplayOptions() {
    return { showDefl: document.getElementById('showDefl') ? document.getElementById('showDefl').checked : true, showVM: true };
  }

  function renderTablesAndSketches() {
    renderNodesTable();
    renderElementsTable();
    renderLoadsTable();
    renderPropsTab();
    renderAllSketchViews();
    render3D();
  }

  function nodeOptionsHtml(selectedId) {
    return state.model.nodes.map(function (n) {
      return '<option value="' + n.id + '"' + (n.id === selectedId ? ' selected' : '') + '>#' + n.id + '</option>';
    }).join('');
  }
  function restraintFromLabel(label) {
    return FEM3D.RESTRAINT[label === 'fixed' ? 'FIXED' : label === 'pinned' ? 'PINNED' : 'FREE'];
  }

  // ---------------------------------------------------------------
  // Tabs
  // ---------------------------------------------------------------
  function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(function (b) { b.classList.toggle('active', b.dataset.tab === tabName); });
    document.querySelectorAll('.tab-panel').forEach(function (p) { p.classList.toggle('active', p.id === 'tab-' + tabName); });
  }
  document.querySelectorAll('.tab-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { switchTab(btn.dataset.tab); });
  });

  // ---------------------------------------------------------------
  // Pestaña Propiedades: nodo o barra seleccionados
  // ---------------------------------------------------------------

  function renderPropsTab() {
    var container = document.getElementById('propsContent');
    if (!state.selection) {
      container.innerHTML = '<p class="muted">Selecciona un nodo o barra en cualquier panel para editarlo (o usa "+ Carga").</p>' +
        '<p class="muted">Apoyos y carga puntual van en los <b>nodos</b>. La carga distribuida va en las <b>barras</b>.</p>';
      return;
    }
    if (state.selection.type === 'node') {
      var node = state.model.nodes.find(function (n) { return n.id === state.selection.id; });
      if (!node) { state.selection = null; return renderPropsTab(); }
      renderNodePropsInto(container, node);
    } else {
      var el = state.model.elements.find(function (e) { return e.id === state.selection.id; });
      if (!el) { state.selection = null; return renderPropsTab(); }
      renderElementEditInto(container, el);
    }
  }

  function renderNodePropsInto(container, node) {
    var label = FEM3DRender.restraintLabel(node);
    var ui = Units.nodeCoordToUi(node.x, node.y, node.z);
    var load = state.model.nodalLoads.find(function (l) { return l.nodeId === node.id; });
    var fx = load ? Units.forceToUi(load.fx) : 0, fy = load ? Units.forceToUi(load.fy) : 0, fz = load ? Units.forceToUi(load.fz) : 0;
    var mx = load ? Units.momentToUi(load.mx) : 0, my = load ? Units.momentToUi(load.my) : 0, mz = load ? Units.momentToUi(load.mz) : 0;

    container.innerHTML =
      '<h3 style="font-size:12px;color:var(--muted);margin:4px 0">Nodo #' + node.id + '</h3>' +
      '<div class="field-row">' +
      '<div><label>X (m)<input type="number" step="any" id="np_x" value="' + ui.x.toFixed(3) + '"></label></div>' +
      '<div><label>Y (m)<input type="number" step="any" id="np_y" value="' + ui.y.toFixed(3) + '"></label></div>' +
      '<div><label>Z (m)<input type="number" step="any" id="np_z" value="' + ui.z.toFixed(3) + '"></label></div></div>' +
      '<label>Apoyo<select id="np_restraint">' +
      '<option value="free"' + (label === 'free' ? ' selected' : '') + '>Libre</option>' +
      '<option value="pinned"' + (label === 'pinned' ? ' selected' : '') + '>Pin (3D)</option>' +
      '<option value="fixed"' + (label === 'fixed' ? ' selected' : '') + '>Fijo</option>' +
      '</select></label>' +
      '<h4 style="font-size:11px;color:var(--muted);margin:10px 0 4px">Carga puntual</h4>' +
      '<div class="field-row">' +
      '<div><label>Fx (kN)<input type="number" step="any" id="np_fx" value="' + fx + '"></label></div>' +
      '<div><label>Fy (kN)<input type="number" step="any" id="np_fy" value="' + fy + '"></label></div>' +
      '<div><label>Fz (kN)<input type="number" step="any" id="np_fz" value="' + fz + '"></label></div></div>' +
      '<div class="field-row">' +
      '<div><label>Mx (kN·m)<input type="number" step="any" id="np_mx" value="' + mx + '"></label></div>' +
      '<div><label>My (kN·m)<input type="number" step="any" id="np_my" value="' + my + '"></label></div>' +
      '<div><label>Mz (kN·m)<input type="number" step="any" id="np_mz" value="' + mz + '"></label></div></div>' +
      '<button class="apply-btn" id="np_apply">Aplicar</button>' +
      '<button class="remove-btn" id="np_delete">Eliminar nodo</button>';

    document.getElementById('np_apply').addEventListener('click', function () {
      var internal = Units.nodeCoordToInternal(
        parseFloat(document.getElementById('np_x').value) || 0,
        parseFloat(document.getElementById('np_y').value) || 0,
        parseFloat(document.getElementById('np_z').value) || 0
      );
      node.x = internal.x; node.y = internal.y; node.z = internal.z;
      node.restraint = restraintFromLabel(document.getElementById('np_restraint').value);

      var fxv = parseFloat(document.getElementById('np_fx').value) || 0;
      var fyv = parseFloat(document.getElementById('np_fy').value) || 0;
      var fzv = parseFloat(document.getElementById('np_fz').value) || 0;
      var mxv = parseFloat(document.getElementById('np_mx').value) || 0;
      var myv = parseFloat(document.getElementById('np_my').value) || 0;
      var mzv = parseFloat(document.getElementById('np_mz').value) || 0;
      state.model.nodalLoads = state.model.nodalLoads.filter(function (l) { return l.nodeId !== node.id; });
      if (fxv || fyv || fzv || mxv || myv || mzv) {
        var il = Units.pointLoadToInternal(fxv, fyv, fzv, mxv, myv, mzv);
        state.model.addNodalLoad(node.id, il.fx, il.fy, il.fz, il.mx, il.my, il.mz);
      }
      invalidateResults();
      renderTablesAndSketches();
    });
    document.getElementById('np_delete').addEventListener('click', function () {
      state.model.removeNode(node.id);
      state.selection = null;
      invalidateResults();
      renderTablesAndSketches();
    });
  }

  function sectionSummary(section) {
    var p = section.params;
    if (section.type === 'rect') return 'Rect ' + p.b + '×' + p.h + ' mm';
    if (section.type === 'circle') return 'Ø' + p.d + ' mm';
    return 'Manual';
  }

  function renderCatalogFields3D(el) {
    if (!FEM3D.Catalog.loaded) {
      var msg = FEM3D.Catalog.error
        ? 'No se pudo cargar el catálogo (' + FEM3D.Catalog.error + '). Si abriste el archivo con file://, corre un servidor local (ver README).'
        : 'Cargando catálogo…';
      return '<p class="muted">' + msg + '</p>';
    }
    var families = FEM3D.Catalog.families();
    var currentFamily = (el.catalogRef && el.catalogRef.family) || (families[0] && families[0].family);
    var familyOptions = families.map(function (f) {
      return '<option value="' + f.family + '"' + (f.family === currentFamily ? ' selected' : '') + '>' + f.label + ' (' + f.family + ')</option>';
    }).join('');
    return '<label>Familia<select id="ee_catfamily">' + familyOptions + '</select></label>' +
      '<label>Perfil<select id="ee_catprofile"></select></label>' +
      '<div id="ee_catalogSummary" class="catalog-summary"></div>' +
      '<p class="muted">El eje fuerte del catálogo (x-x) siempre se orienta como Iy (resiste flexión vertical). Para "acostar" el perfil, usa el ángulo β.</p>';
  }

  function wireCatalogFields3D(el) {
    if (!FEM3D.Catalog.loaded) return;
    var familySelect = document.getElementById('ee_catfamily');
    var profileSelect = document.getElementById('ee_catprofile');
    var summary = document.getElementById('ee_catalogSummary');
    function populateProfiles() {
      var profiles = FEM3D.Catalog.byFamily(familySelect.value);
      var currentId = el.catalogRef && el.catalogRef.id;
      profileSelect.innerHTML = profiles.map(function (p) {
        return '<option value="' + p.id + '"' + (p.id === currentId ? ' selected' : '') + '>' + p.id + ' (' + p.weight_kg_m + ' kg/m)</option>';
      }).join('');
      updateSummary();
    }
    function updateSummary() {
      var profile = FEM3D.Catalog.findById(profileSelect.value);
      if (!profile) { summary.textContent = ''; return; }
      var sp = FEM3D.Catalog.toSectionParams(profile);
      summary.textContent = 'A=' + sp.A.toFixed(0) + ' mm², Iy=' + sp.Iy.toExponential(3) +
        ' mm⁴, Iz=' + sp.Iz.toExponential(3) + ' mm⁴, J≈' + sp.J.toExponential(3) + ' mm⁴';
    }
    familySelect.addEventListener('change', populateProfiles);
    profileSelect.addEventListener('change', updateSummary);
    populateProfiles();
  }

  function renderElementEditInto(container, el) {
    var p = el.section.params;
    var matButtons = Object.keys(MATERIAL_PRESETS).map(function (k) {
      return '<button type="button" class="tool-btn" data-preset="' + k + '" style="font-size:10px;padding:4px 6px">' + MATERIAL_PRESETS[k].label + '</button>';
    }).join(' ');

    container.innerHTML =
      '<h3 style="font-size:12px;color:var(--muted);margin:4px 0">Barra #' + el.id + '</h3>' +
      '<label>Nodo I / Nodo J<div style="display:flex;gap:6px">' +
      '<select id="ee_nodeI" style="flex:1">' + nodeOptionsHtml(el.nodeI.id) + '</select>' +
      '<select id="ee_nodeJ" style="flex:1">' + nodeOptionsHtml(el.nodeJ.id) + '</select></div></label>' +
      '<div class="field-row">' +
      '<div><label>UDLy (kN/m)<input type="number" id="ee_udlY" value="' + el.udlY + '"></label></div>' +
      '<div><label>UDLz (kN/m)<input type="number" id="ee_udlZ" value="' + el.udlZ + '"></label></div></div>' +
      '<hr style="border-color:var(--border);margin:12px 0">' +
      '<label>Material rápido: ' + matButtons + '</label>' +
      '<div class="field-row">' +
      '<div><label>E (MPa)<input type="number" id="ee_E" value="' + el.E + '"></label></div>' +
      '<div><label>G (MPa)<input type="number" id="ee_G" value="' + el.G + '"></label></div></div>' +
      '<label>Sección<select id="ee_sectype">' +
      '<option value="rect"' + (el.section.type === 'rect' ? ' selected' : '') + '>Rectangular</option>' +
      '<option value="circle"' + (el.section.type === 'circle' ? ' selected' : '') + '>Circular sólida</option>' +
      '<option value="catalog"' + (el.section.type === 'manual' && el.catalogRef ? ' selected' : '') + '>Catálogo de perfiles</option>' +
      '</select></label>' +
      '<div id="ee_sectionFields"></div>' +
      '<label>β, ángulo de giro de la sección (°)<input type="number" id="ee_beta" value="' + el.beta + '"></label>' +
      '<button class="apply-btn" id="ee_apply">Aplicar</button>' +
      '<button class="remove-btn" id="ee_delete">Eliminar barra</button>';

    function renderSectionFields(type) {
      var html;
      if (type === 'rect') {
        html = '<div class="field-row">' +
          '<div><label>b -y- (mm)<input type="number" id="ee_b" value="' + (p.b || 200) + '"></label></div>' +
          '<div><label>h -z- (mm)<input type="number" id="ee_h" value="' + (p.h || 400) + '"></label></div></div>';
      } else if (type === 'circle') {
        html = '<label>d (mm)<input type="number" id="ee_d" value="' + (p.d || 300) + '"></label>';
      } else {
        html = renderCatalogFields3D(el);
      }
      document.getElementById('ee_sectionFields').innerHTML = html;
      if (type === 'catalog') wireCatalogFields3D(el);
    }
    renderSectionFields(el.section.type === 'manual' && el.catalogRef ? 'catalog' : el.section.type);
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
        el.catalogRef = null;
      } else if (type === 'circle') {
        el.section = new FEM3D.Section('circle', { d: parseFloat(document.getElementById('ee_d').value) || 1 });
        el.catalogRef = null;
      } else if (type === 'catalog') {
        var profileId = document.getElementById('ee_catprofile').value;
        var profile = FEM3D.Catalog.findById(profileId);
        if (profile) {
          el.section = new FEM3D.Section('manual', FEM3D.Catalog.toSectionParams(profile));
          el.catalogRef = { id: profile.id, family: profile.family, label: profile.familyLabel };
        }
      }
      el.udlY = Units.distributedLoadToInternal(parseFloat(document.getElementById('ee_udlY').value) || 0);
      el.udlZ = Units.distributedLoadToInternal(parseFloat(document.getElementById('ee_udlZ').value) || 0);
      el.beta = parseFloat(document.getElementById('ee_beta').value) || 0;
      invalidateResults();
      renderTablesAndSketches();
    });
    document.getElementById('ee_delete').addEventListener('click', function () {
      state.model.removeElement(el.id);
      state.selection = null;
      invalidateResults();
      renderTablesAndSketches();
    });
  }

  // ---------------------------------------------------------------
  // Tabla de nodos (respaldo / edicion masiva)
  // ---------------------------------------------------------------
  function renderNodesTable() {
    var tbody = document.querySelector('#nodesTable tbody');
    tbody.innerHTML = state.model.nodes.map(function (n) {
      var label = FEM3DRender.restraintLabel(n);
      var ui = Units.nodeCoordToUi(n.x, n.y, n.z);
      var isSel = state.selection && state.selection.type === 'node' && state.selection.id === n.id;
      return '<tr data-node-id="' + n.id + '"' + (isSel ? ' style="outline:2px solid var(--accent)"' : '') + '>' +
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
    renderAllSketchViews();
    render3D();
  });
  document.querySelector('#nodesTable tbody').addEventListener('change', function (evt) {
    if (evt.target.dataset.field !== 'restraint') return;
    var tr = evt.target.closest('tr');
    var node = state.model.nodes.find(function (n) { return n.id === Number(tr.dataset.nodeId); });
    if (!node) return;
    node.restraint = restraintFromLabel(evt.target.value);
    invalidateResults();
    renderAllSketchViews();
    render3D();
  });
  document.querySelector('#nodesTable tbody').addEventListener('click', function (evt) {
    var tr = evt.target.closest('tr');
    if (!tr) return;
    var id = Number(tr.dataset.nodeId);
    if (evt.target.dataset.action === 'del') {
      state.model.removeNode(id);
      if (state.selection && state.selection.type === 'node' && state.selection.id === id) state.selection = null;
      invalidateResults();
      renderTablesAndSketches();
      return;
    }
    if (evt.target.tagName === 'INPUT' || evt.target.tagName === 'SELECT') return;
    state.selection = { type: 'node', id: id };
    switchTab('props');
    renderTablesAndSketches();
  });
  document.getElementById('addNodeBtn').addEventListener('click', function () {
    var wasEmpty = state.model.nodes.length === 0;
    state.model.addNode(0, 0, 0);
    invalidateResults();
    if (wasEmpty) fitAllSketchViews();
    renderTablesAndSketches();
  });

  // ---------------------------------------------------------------
  // Tabla de barras
  // ---------------------------------------------------------------
  function renderElementsTable() {
    var tbody = document.querySelector('#elementsTable tbody');
    tbody.innerHTML = state.model.elements.map(function (el) {
      var isSel = state.selection && state.selection.type === 'element' && state.selection.id === el.id;
      return '<tr data-el-id="' + el.id + '"' + (isSel ? ' style="outline:2px solid var(--accent)"' : '') + '>' +
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
      if (state.selection && state.selection.type === 'element' && state.selection.id === id) state.selection = null;
      invalidateResults();
      renderTablesAndSketches();
      return;
    }
    state.selection = { type: 'element', id: id };
    switchTab('props');
    renderTablesAndSketches();
  });
  document.getElementById('addElementBtn').addEventListener('click', function () {
    if (state.model.nodes.length < 2) { alert('Necesitas al menos 2 nodos.'); return; }
    var n1 = state.model.nodes[0], n2 = state.model.nodes[1];
    var active = buildActiveSection();
    var el = state.model.addElement(n1, n2, active.E, active.G, active.section);
    el.catalogRef = active.catalogRef;
    state.selection = { type: 'element', id: el.id };
    invalidateResults();
    switchTab('props');
    renderTablesAndSketches();
  });

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
  function loadFromRow(tr) { return state.model.nodalLoads[Number(tr.dataset.loadIdx)]; }

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
    renderAllSketchViews();
    render3D();
  });
  document.querySelector('#loadsTable tbody').addEventListener('change', function (evt) {
    if (evt.target.dataset.field !== 'node') return;
    var tr = evt.target.closest('tr');
    var load = loadFromRow(tr);
    if (load) load.nodeId = Number(evt.target.value);
    invalidateResults();
    renderAllSketchViews();
    render3D();
  });
  document.querySelector('#loadsTable tbody').addEventListener('click', function (evt) {
    if (evt.target.dataset.action !== 'del') return;
    var tr = evt.target.closest('tr');
    state.model.nodalLoads.splice(Number(tr.dataset.loadIdx), 1);
    invalidateResults();
    renderTablesAndSketches();
  });
  document.getElementById('addLoadBtn').addEventListener('click', function () {
    if (state.model.nodes.length === 0) { alert('Agrega al menos un nodo primero.'); return; }
    state.model.addNodalLoad(state.model.nodes[0].id, 0, 0, 0, 0, 0, 0);
    invalidateResults();
    renderTablesAndSketches();
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
    document.getElementById('memoriaBtn').disabled = false;
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

    html += '<h3 style="font-size:12px;color:var(--muted)">Diagramas por barra</h3>';
    state.model.elements.forEach(function (el) {
      ['N', 'Vy', 'Vz', 'T', 'My', 'Mz'].forEach(function (k) {
        html += '<div class="diagram-block"><h4>Barra #' + el.id + ' — ' + k + '(x)</h4>' +
          '<canvas id="diag' + k + '_' + el.id + '"></canvas></div>';
      });
    });

    html += '<h3 style="font-size:12px;color:var(--muted)">Von Mises máximo global</h3>';
    html += '<p>' + lr.globalMax.vonMises.toFixed(2) + ' MPa';
    if (lr.vmLocation) {
      html += ' — barra #' + lr.vmLocation.elementId + ', x=' + (lr.vmLocation.x / 1000).toFixed(3) +
        ' m, y=' + lr.vmLocation.y.toFixed(1) + ' mm, z=' + lr.vmLocation.z.toFixed(1) + ' mm';
    }
    html += '</p>';
    html += '<p class="muted">Nota: el corte por torsión en secciones rectangulares NO está incluido en este máximo ' +
      '(campo de Saint-Venant no cerrado) — se reporta aparte abajo y debe sumarse manualmente en el punto crítico si corresponde.</p>';

    state.model.elements.forEach(function (el) {
      var tmax = lr.torsionMaxByElement.get(el.id);
      if (tmax > 0) html += '<p class="muted">Barra #' + el.id + ': τ_torsión máx (aprox. Roark) = ' + tmax.toFixed(2) + ' MPa</p>';
    });

    var allowable = parseFloat(document.getElementById('allowableStress').value);
    if (allowable > 0) {
      var fs = allowable / lr.globalMax.vonMises;
      html += '<p>Tensión admisible: ' + allowable.toFixed(1) + ' MPa — FS = ' + fs.toFixed(2) +
        ' <span class="' + (fs >= 1 ? 'pass">PASA' : 'fail">NO PASA') + '</span></p>';
    }

    document.getElementById('resultsContent').innerHTML = html;

    var FORCE_KEYS = { N: true, Vy: true, Vz: true };
    var COLORS = { N: '#ff4fd2', Vy: '#4fb8ff', Vz: '#7fd4ff', T: '#ffb84f', My: '#4fd27a', Mz: '#7fe39a' };
    state.model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var nx = 40;
      var series = { N: [], Vy: [], Vz: [], T: [], My: [], Mz: [] };
      for (var i = 0; i <= nx; i++) {
        var f = FEM3D.solver.internalForcesAt(ef, (ef.L * i) / nx);
        Object.keys(series).forEach(function (k) {
          series[k].push(FORCE_KEYS[k] ? Units.forceToUi(f[k]) : Units.momentToUi(f[k]));
        });
      }
      Object.keys(series).forEach(function (k) {
        var canvas = document.getElementById('diag' + k + '_' + el.id);
        drawMiniDiagram(canvas, series[k], COLORS[k], FORCE_KEYS[k] ? 'kN' : 'kN·m');
      });
    });
  }

  function drawMiniDiagram(canvas, values, color, unit, theme) {
    if (!canvas) return;
    theme = theme || { grid: '#3a414c', text: '#c8ccd2' };
    var w = 360, h = 60;
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
    c.beginPath(); c.moveTo(padL, zeroY);
    values.forEach(function (v, i) { c.lineTo(padL + (plotW * i) / (values.length - 1), zeroY - v * scale); });
    c.lineTo(w - padR, zeroY); c.closePath();
    c.fillStyle = color + '33'; c.fill();
    c.strokeStyle = color; c.lineWidth = 1.5;
    c.beginPath();
    values.forEach(function (v, i) {
      var x = padL + (plotW * i) / (values.length - 1), y = zeroY - v * scale;
      if (i === 0) c.moveTo(x, y); else c.lineTo(x, y);
    });
    c.stroke();
    c.fillStyle = theme.text; c.font = '10px sans-serif'; c.textAlign = 'right';
    c.fillText('máx |' + maxAbs.toFixed(2) + '| ' + unit, w - padR, padT - 1);
  }

  document.getElementById('allowableStress').addEventListener('input', function () {
    if (state.lastResult) renderResultsPanel();
  });

  document.getElementById('fitBtn').addEventListener('click', function () {
    FEM3DRender.fitView(state.ctx, state.model.nodes);
    fitAllSketchViews();
    renderAllSketchViews();
  });

  // ---------------------------------------------------------------
  // Memoria de calculo
  // ---------------------------------------------------------------
  var memoriaMeta = { proyecto: '', autor: '', notas: '' };
  var memoriaOverlay = document.getElementById('memoriaOverlay');

  function renderMemoria() {
    var allowable = parseFloat(document.getElementById('allowableStress').value) || 0;
    var fecha = new Date().toLocaleDateString('es-CL', { year: 'numeric', month: 'long', day: 'numeric' });
    var result = FEM3D.Memoria.generate({
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
      (memoriaMeta.notas || '').replace(/"/g, '&quot;') + '" style="width:500px"></label></div></div>';

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
  document.getElementById('memoriaBtn').addEventListener('click', function () {
    renderMemoria();
    memoriaOverlay.hidden = false;
  });
  document.getElementById('memoriaCloseBtn').addEventListener('click', function () { memoriaOverlay.hidden = true; });
  document.getElementById('memoriaPrintBtn').addEventListener('click', function () { window.print(); });

  document.getElementById('clearBtn').addEventListener('click', function () {
    if (!confirm('¿Borrar todo el modelo?')) return;
    state.model = new FEM3D.Model();
    state.selection = null;
    state.pendingElementNode = null;
    invalidateResults();
    renderTablesAndSketches();
    FEM3DRender.fitView(state.ctx, []);
    fitAllSketchViews();
    renderAllSketchViews();
  });

  // ---------------------------------------------------------------
  // Modelo inicial de ejemplo
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

  function resizeAll() {
    ['xy', 'xz', 'yz'].forEach(function (key) { resizeSketchCanvas(state.sketch[key]); });
    state.ctx.resize();
  }
  window.addEventListener('resize', function () { resizeAll(); fitAllSketchViews(); renderAllSketchViews(); });

  resizeAll();
  fitAllSketchViews();
  setMode('addNode');
  renderActiveProfilePanel();
  renderTablesAndSketches();
  FEM3DRender.fitView(state.ctx, state.model.nodes);

  FEM3D.Catalog.load().then(function () {
    if (state.activeProfile.sectionType === 'catalog') renderActiveProfileSectionFields();
    renderPropsTab();
  }).catch(function () {
    renderPropsTab();
  });
})();
