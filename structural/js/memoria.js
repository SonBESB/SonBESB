/**
 * Generador de memoria de calculo imprimible (vista HTML, no PDF generado
 * por backend — el usuario usa Ctrl/Cmd+P o el boton "Imprimir / Guardar
 * PDF", que llama a window.print() con una hoja de estilos @media print
 * que oculta todo excepto esta vista; ver css/style.css).
 *
 * No agrega ningun calculo nuevo: solo formatea lo que el modelo y
 * solve()/stress.js ya calcularon, en un documento legible/imprimible.
 */
(function (root) {
  'use strict';

  var FEM = root.FEM;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function sectionDescription(el) {
    if (el.catalogRef) {
      return 'Catálogo ' + el.catalogRef.label + ' — ' + el.catalogRef.id +
        ' (eje ' + (el.catalogRef.axis === 'weak' ? 'débil y-y' : 'fuerte x-x') + ')';
    }
    if (el.section.type === 'rect') return 'Rectangular ' + el.section.params.b + '×' + el.section.params.h + ' mm';
    if (el.section.type === 'circle') return 'Circular Ø' + el.section.params.d + ' mm';
    return 'Manual (A=' + el.section.params.A.toFixed(0) + ' mm², I=' + el.section.params.I.toExponential(2) + ' mm⁴)';
  }

  function restraintLabel(node) { return FEM.render.restraintLabel(node); }
  var RESTRAINT_NAMES = { free: 'Libre', pinned: 'Articulado', roller: 'Rodillo', fixed: 'Empotrado' };

  /**
   * meta: {proyecto, autor, fecha, notas} — campos editables que el
   * llamador controla (ver app.js, inputs #mem_proyecto etc.).
   * Devuelve {html, diagrams: [{canvasId, points, color, unit}, ...]} —
   * los diagramas se dibujan aparte (el caller necesita insertar el html
   * en el DOM antes de poder tomar getContext('2d') de los canvas).
   */
  function generate(ctx) {
    var model = ctx.model, lr = ctx.lastResult, meta = ctx.meta, allowable = ctx.allowableStress;
    var Units = FEM.Units;
    var diagrams = [];

    var html = '';
    html += '<h1>Memoria de Cálculo — Análisis de Pórtico 2D</h1>';
    html += '<table class="meta-table">' +
      '<tr><td><b>Proyecto:</b></td><td id="mem_display_proyecto">' + escapeHtml(meta.proyecto || '(sin especificar)') + '</td></tr>' +
      '<tr><td><b>Autor:</b></td><td id="mem_display_autor">' + escapeHtml(meta.autor || '(sin especificar)') + '</td></tr>' +
      '<tr><td><b>Fecha:</b></td><td>' + escapeHtml(meta.fecha) + '</td></tr>' +
      '</table>' +
      '<p class="note" id="mem_display_notas"' + (meta.notas ? '' : ' hidden') + '>' + escapeHtml(meta.notas || '') + '</p>';

    html += '<h2>1. Descripción del modelo</h2>';
    html += '<p>Pórtico/viga plano analizado por el método matricial de rigidez directa ' +
      '(elemento de Euler-Bernoulli, 3 grados de libertad por nodo). ' + model.nodes.length +
      ' nodos, ' + model.elements.length + ' barras, ' + model.nodalLoads.length + ' carga(s) puntual(es).</p>';

    html += '<h3 style="font-size:13px">1.1 Nodos</h3>';
    html += '<table><tr><th>Nodo</th><th>X (m)</th><th>Y (m)</th><th>Apoyo</th></tr>';
    model.nodes.forEach(function (n) {
      html += '<tr><td>#' + n.id + '</td><td>' + (n.x / 1000).toFixed(3) + '</td><td>' + (n.y / 1000).toFixed(3) +
        '</td><td>' + RESTRAINT_NAMES[restraintLabel(n)] + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">1.2 Barras</h3>';
    html += '<table><tr><th>Barra</th><th>Nodo I→J</th><th>L (m)</th><th>E (MPa)</th><th>Sección</th><th>UDL (kN/m)</th></tr>';
    model.elements.forEach(function (el) {
      html += '<tr><td>#' + el.id + '</td><td>#' + el.nodeI.id + '→#' + el.nodeJ.id + '</td><td>' +
        (el.length() / 1000).toFixed(3) + '</td><td>' + el.E + '</td><td>' + sectionDescription(el) +
        '</td><td>' + el.udl.toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    if (model.nodalLoads.length) {
      html += '<h3 style="font-size:13px">1.3 Cargas puntuales</h3>';
      html += '<table><tr><th>Nodo</th><th>Fx (kN)</th><th>Fy (kN)</th><th>M (kN·m)</th></tr>';
      model.nodalLoads.forEach(function (l) {
        html += '<tr><td>#' + l.nodeId + '</td><td>' + Units.forceToUi(l.fx).toFixed(2) + '</td><td>' +
          Units.forceToUi(l.fy).toFixed(2) + '</td><td>' + Units.momentToUi(l.m).toFixed(2) + '</td></tr>';
      });
      html += '</table>';
    }

    html += '<h2>2. Metodología</h2>' +
      '<p>Se resuelve el sistema K·D=F por el método de rigidez directa, con matriz de rigidez local ' +
      'de Euler-Bernoulli (sin deformación por corte) transformada a coordenadas globales. Las fuerzas internas ' +
      'N(x), V(x), M(x) se recuperan por equilibrio del tramo, y la tensión combinada se calcula como ' +
      'σ(y)=N/A−M·y/I (flexión+axial) y τ(y) por la fórmula de Jourawski (corte), combinadas en ' +
      'von Mises σ_vm=√(σ²+3τ²). Ver <code>README.md</code> del proyecto para el detalle completo, supuestos y ' +
      'límites de alcance (elástico lineal, sin pandeo, secciones rectangular/circular sólida o de catálogo).</p>';

    if (!lr) {
      html += '<h2>3. Resultados</h2><p class="note">No hay resultados calculados.</p>';
      return { html: html, diagrams: diagrams };
    }

    html += '<h2>3. Resultados</h2>';
    html += '<h3 style="font-size:13px">3.1 Reacciones</h3>';
    html += '<table><tr><th>Nodo</th><th>Fx (kN)</th><th>Fy (kN)</th><th>M (kN·m)</th></tr>';
    model.nodes.forEach(function (node) {
      var r = node.restraint;
      if (!(r.ux || r.uy || r.rz)) return;
      var rx = lr.result.reactions.get(node.id);
      html += '<tr><td>#' + node.id + '</td><td>' + Units.forceToUi(rx.fx).toFixed(2) + '</td><td>' +
        Units.forceToUi(rx.fy).toFixed(2) + '</td><td>' + Units.momentToUi(rx.m).toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">3.2 Máximos por barra y diagramas</h3>';
    html += '<table><tr><th>Barra</th><th>|N| (kN)</th><th>|V| (kN)</th><th>|M| (kN·m)</th><th>δ máx (mm)</th></tr>';
    model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var maxN = 0, maxV = 0, maxM = 0, maxD = 0;
      var nx = 24;
      var pointsM = [], pointsV = [];
      for (var i = 0; i <= nx; i++) {
        var x = (ef.L * i) / nx;
        var f = FEM.solver.internalForcesAt(ef, x);
        maxN = Math.max(maxN, Math.abs(f.N));
        maxV = Math.max(maxV, Math.abs(f.V));
        maxM = Math.max(maxM, Math.abs(f.M));
        maxD = Math.max(maxD, Math.abs(FEM.solver.deflectionAt(ef, x)));
        pointsM.push(Units.momentToUi(f.M));
        pointsV.push(Units.forceToUi(f.V));
      }
      html += '<tr><td>#' + el.id + '</td><td>' + Units.forceToUi(maxN).toFixed(2) + '</td><td>' +
        Units.forceToUi(maxV).toFixed(2) + '</td><td>' + Units.momentToUi(maxM).toFixed(2) + '</td><td>' +
        maxD.toFixed(2) + '</td></tr>';
      var idM = 'mem_diagM_' + el.id, idV = 'mem_diagV_' + el.id;
      html += '</table><div class="diagram-block"><h4>Barra #' + el.id + ' — M(x)</h4><canvas id="' + idM +
        '"></canvas></div><div class="diagram-block"><h4>Barra #' + el.id + ' — V(x)</h4><canvas id="' + idV +
        '"></canvas></div><table>';
      diagrams.push({ canvasId: idM, points: pointsM, color: '#2f6f3f', unit: 'kN·m' });
      diagrams.push({ canvasId: idV, points: pointsV, color: '#2f6fed', unit: 'kN' });
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">3.3 Tensión de von Mises</h3>';
    html += '<p>Máximo global: <b>' + lr.globalMax.vonMises.toFixed(2) + ' MPa</b>';
    if (lr.vmLocation) {
      html += ' — barra #' + lr.vmLocation.elementId + ', x=' + (lr.vmLocation.x / 1000).toFixed(3) +
        ' m, y=' + lr.vmLocation.y.toFixed(1) + ' mm (desde eje neutro).';
    }
    html += '</p>';

    if (allowable > 0) {
      var fs = allowable / lr.globalMax.vonMises;
      html += '<h3 style="font-size:13px">3.4 Verificación</h3>' +
        '<p>Tensión admisible/fluencia especificada: ' + allowable.toFixed(1) + ' MPa.<br>' +
        'Factor de seguridad FS = σ_adm / σ_vm,máx = ' + fs.toFixed(2) + ' — ' +
        '<b>' + (fs >= 1 ? 'CUMPLE' : 'NO CUMPLE') + '</b>.</p>' +
        '<p class="note">Esta verificación es una comparación directa σ_adm/σ_vm, no un chequeo de norma ' +
        '(AISC, NCh, Eurocódigo, etc.).</p>';
    }

    html += '<p class="note" style="margin-top:30px">Generado automáticamente el ' + new Date().toLocaleString('es-CL') +
      ' — herramienta de análisis de pórticos 2D (método matricial de rigidez). Esta memoria resume el ' +
      'modelo y los resultados tal como fueron calculados; no reemplaza la revisión de un ingeniero ' +
      'estructural responsable.</p>';

    return { html: html, diagrams: diagrams };
  }

  root.FEM = root.FEM || {};
  root.FEM.Memoria = { generate: generate };
})(typeof window !== 'undefined' ? window : global);
