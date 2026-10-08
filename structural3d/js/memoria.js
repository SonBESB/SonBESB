/**
 * Generador de memoria de calculo imprimible (3D). Ver structural/js/memoria.js
 * (modulo 2D) para la explicacion de por que es una vista HTML + window.print()
 * en vez de un PDF generado por backend — mismo enfoque, codigo aparte.
 */
(function (root) {
  'use strict';

  var FEM3D = root.FEM3D;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }

  function sectionDescription(el) {
    if (el.catalogRef) {
      return 'Catálogo ' + el.catalogRef.label + ' — ' + el.catalogRef.id + ' (eje fuerte → Iy)';
    }
    if (el.section.type === 'rect') return 'Rectangular ' + el.section.params.b + '×' + el.section.params.h + ' mm';
    if (el.section.type === 'circle') return 'Circular Ø' + el.section.params.d + ' mm';
    var p = el.section.params;
    return 'Manual (A=' + p.A.toFixed(0) + ' mm², Iy=' + p.Iy.toExponential(2) + ', Iz=' + p.Iz.toExponential(2) + ' mm⁴)';
  }

  function restraintLabel(node) { return FEM3DRender.restraintLabel(node); }
  var RESTRAINT_NAMES = { free: 'Libre', partial: 'Parcial', pinned: 'Pin (3D)', fixed: 'Empotrado' };

  function generate(ctx) {
    var model = ctx.model, lr = ctx.lastResult, meta = ctx.meta, allowable = ctx.allowableStress;
    var Units = FEM3D.Units;
    var diagrams = [];

    var html = '';
    html += '<h1>Memoria de Cálculo — Análisis de Pórtico 3D</h1>';
    html += '<table class="meta-table">' +
      '<tr><td><b>Proyecto:</b></td><td id="mem_display_proyecto">' + escapeHtml(meta.proyecto || '(sin especificar)') + '</td></tr>' +
      '<tr><td><b>Autor:</b></td><td id="mem_display_autor">' + escapeHtml(meta.autor || '(sin especificar)') + '</td></tr>' +
      '<tr><td><b>Fecha:</b></td><td>' + escapeHtml(meta.fecha) + '</td></tr>' +
      '</table>' +
      '<p class="note" id="mem_display_notas"' + (meta.notas ? '' : ' hidden') + '>' + escapeHtml(meta.notas || '') + '</p>';

    html += '<h2>1. Descripción del modelo</h2>';
    html += '<p>Pórtico espacial (3D) analizado por el método matricial de rigidez directa ' +
      '(elemento de Euler-Bernoulli biaxial + torsión de Saint-Venant, 6 grados de libertad por nodo). ' +
      model.nodes.length + ' nodos, ' + model.elements.length + ' barras, ' + model.nodalLoads.length + ' carga(s) puntual(es).</p>';

    html += '<h3 style="font-size:13px">1.1 Nodos</h3>';
    html += '<table><tr><th>Nodo</th><th>X (m)</th><th>Y (m)</th><th>Z (m)</th><th>Apoyo</th></tr>';
    model.nodes.forEach(function (n) {
      html += '<tr><td>#' + n.id + '</td><td>' + (n.x / 1000).toFixed(3) + '</td><td>' + (n.y / 1000).toFixed(3) +
        '</td><td>' + (n.z / 1000).toFixed(3) + '</td><td>' + RESTRAINT_NAMES[restraintLabel(n)] + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">1.2 Barras</h3>';
    html += '<table><tr><th>Barra</th><th>Nodo I→J</th><th>L (m)</th><th>E (MPa)</th><th>G (MPa)</th><th>Sección</th><th>UDLy/UDLz (kN/m)</th></tr>';
    model.elements.forEach(function (el) {
      html += '<tr><td>#' + el.id + '</td><td>#' + el.nodeI.id + '→#' + el.nodeJ.id + '</td><td>' +
        (el.length() / 1000).toFixed(3) + '</td><td>' + el.E + '</td><td>' + el.G + '</td><td>' +
        sectionDescription(el) + '</td><td>' + el.udlY.toFixed(2) + ' / ' + el.udlZ.toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    if (model.nodalLoads.length) {
      html += '<h3 style="font-size:13px">1.3 Cargas puntuales</h3>';
      html += '<table><tr><th>Nodo</th><th>Fx</th><th>Fy</th><th>Fz</th><th>Mx</th><th>My</th><th>Mz</th></tr>';
      model.nodalLoads.forEach(function (l) {
        html += '<tr><td>#' + l.nodeId + '</td><td>' + Units.forceToUi(l.fx).toFixed(2) + '</td><td>' +
          Units.forceToUi(l.fy).toFixed(2) + '</td><td>' + Units.forceToUi(l.fz).toFixed(2) + '</td><td>' +
          Units.momentToUi(l.mx).toFixed(2) + '</td><td>' + Units.momentToUi(l.my).toFixed(2) + '</td><td>' +
          Units.momentToUi(l.mz).toFixed(2) + '</td></tr>';
      });
      html += '</table>';
    }

    html += '<h2>2. Metodología</h2>' +
      '<p>Se resuelve el sistema K·D=F (matrices locales 12×12) por el método de rigidez directa. ' +
      'Flexión biaxial de Euler-Bernoulli (Iy gobierna la flexión vertical típica — My/Vz; Iz la horizontal ' +
      '— Mz/Vy) y torsión de Saint-Venant (GJ). La tensión combinada es σ(y,z)=N/A−Mz·y/Iz−My·z/Iy, con corte ' +
      'de Jourawski por eje y von Mises σ_vm=√(σ²+3·(τxy²+τxz²)). Para secciones rectangulares, el corte de ' +
      'torsión NO se incluye en el campo de von Mises (aproximación de Saint-Venant, no cerrada) y se reporta ' +
      'aparte. Ver <code>README.md</code> del proyecto para el detalle completo y límites de alcance.</p>';

    if (!lr) {
      html += '<h2>3. Resultados</h2><p class="note">No hay resultados calculados.</p>';
      return { html: html, diagrams: diagrams };
    }

    html += '<h2>3. Resultados</h2>';
    html += '<h3 style="font-size:13px">3.1 Reacciones</h3>';
    html += '<table><tr><th>Nodo</th><th>Fx</th><th>Fy</th><th>Fz</th><th>Mx</th><th>My</th><th>Mz</th></tr>';
    model.nodes.forEach(function (node) {
      var r = node.restraint;
      if (!(r.ux || r.uy || r.uz || r.rx || r.ry || r.rz)) return;
      var rx = lr.result.reactions.get(node.id);
      html += '<tr><td>#' + node.id + '</td><td>' + Units.forceToUi(rx.fx).toFixed(2) + '</td><td>' +
        Units.forceToUi(rx.fy).toFixed(2) + '</td><td>' + Units.forceToUi(rx.fz).toFixed(2) + '</td><td>' +
        Units.momentToUi(rx.mx).toFixed(2) + '</td><td>' + Units.momentToUi(rx.my).toFixed(2) + '</td><td>' +
        Units.momentToUi(rx.mz).toFixed(2) + '</td></tr>';
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">3.2 Máximos por barra y diagramas</h3>';
    html += '<table><tr><th>Barra</th><th>|N|</th><th>|Vy|</th><th>|Vz|</th><th>|T|</th><th>|My|</th><th>|Mz|</th></tr>';
    var FORCE_KEYS = { N: true, Vy: true, Vz: true };
    var COLORS = { N: '#c43fa8', Vy: '#2f6fed', Vz: '#1e9bd7', T: '#c47a1e', My: '#2f8f4f', Mz: '#4fb06c' };
    model.elements.forEach(function (el) {
      var ef = lr.result.elementForces.get(el.id);
      var m = { N: 0, Vy: 0, Vz: 0, T: 0, My: 0, Mz: 0 };
      var series = { N: [], Vy: [], Vz: [], T: [], My: [], Mz: [] };
      var nx = 24;
      for (var i = 0; i <= nx; i++) {
        var f = FEM3D.solver.internalForcesAt(ef, (ef.L * i) / nx);
        Object.keys(m).forEach(function (k) {
          m[k] = Math.max(m[k], Math.abs(f[k]));
          series[k].push(FORCE_KEYS[k] ? Units.forceToUi(f[k]) : Units.momentToUi(f[k]));
        });
      }
      html += '<tr><td>#' + el.id + '</td><td>' + Units.forceToUi(m.N).toFixed(2) + '</td><td>' +
        Units.forceToUi(m.Vy).toFixed(2) + '</td><td>' + Units.forceToUi(m.Vz).toFixed(2) + '</td><td>' +
        Units.momentToUi(m.T).toFixed(2) + '</td><td>' + Units.momentToUi(m.My).toFixed(2) + '</td><td>' +
        Units.momentToUi(m.Mz).toFixed(2) + '</td></tr>';
      html += '</table>';
      Object.keys(series).forEach(function (k) {
        var id = 'mem_diag' + k + '_' + el.id;
        html += '<div class="diagram-block"><h4>Barra #' + el.id + ' — ' + k + '(x)</h4><canvas id="' + id + '"></canvas></div>';
        diagrams.push({ canvasId: id, points: series[k], color: COLORS[k], unit: FORCE_KEYS[k] ? 'kN' : 'kN·m' });
      });
      html += '<table>';
    });
    html += '</table>';

    html += '<h3 style="font-size:13px">3.3 Tensión de von Mises</h3>';
    html += '<p>Máximo global: <b>' + lr.globalMax.vonMises.toFixed(2) + ' MPa</b>';
    if (lr.vmLocation) {
      html += ' — barra #' + lr.vmLocation.elementId + ', x=' + (lr.vmLocation.x / 1000).toFixed(3) +
        ' m, y=' + lr.vmLocation.y.toFixed(1) + ' mm, z=' + lr.vmLocation.z.toFixed(1) + ' mm.';
    }
    html += '</p><p class="note">El corte por torsión en secciones rectangulares no está incluido en este máximo ' +
      '(ver metodología) — se reporta aparte por barra:</p>';
    model.elements.forEach(function (el) {
      var tmax = lr.torsionMaxByElement.get(el.id);
      if (tmax > 0) html += '<p class="note">Barra #' + el.id + ': τ_torsión máx (aprox. Roark) = ' + tmax.toFixed(2) + ' MPa</p>';
    });

    if (allowable > 0) {
      var fs = allowable / lr.globalMax.vonMises;
      html += '<h3 style="font-size:13px">3.4 Verificación</h3>' +
        '<p>Tensión admisible/fluencia especificada: ' + allowable.toFixed(1) + ' MPa.<br>' +
        'Factor de seguridad FS = σ_adm / σ_vm,máx = ' + fs.toFixed(2) + ' — <b>' +
        (fs >= 1 ? 'CUMPLE' : 'NO CUMPLE') + '</b>.</p>' +
        '<p class="note">Comparación directa σ_adm/σ_vm, no un chequeo de norma (AISC, NCh, Eurocódigo, etc.), ' +
        'y no incluye el corte de torsión en perfiles rectangulares (ver 3.3).</p>';
    }

    html += '<p class="note" style="margin-top:30px">Generado automáticamente el ' + new Date().toLocaleString('es-CL') +
      ' — herramienta de análisis de pórticos 3D (método matricial de rigidez espacial). Esta memoria resume el ' +
      'modelo y los resultados tal como fueron calculados; no reemplaza la revisión de un ingeniero estructural responsable.</p>';

    return { html: html, diagrams: diagrams };
  }

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.Memoria = { generate: generate };
})(typeof window !== 'undefined' ? window : global);
