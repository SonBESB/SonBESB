/**
 * Dibujo en canvas: transformacion de vista (mm modelo <-> px pantalla),
 * geometria del modelo (nodos, barras, apoyos, cargas) y overlays de
 * resultados (diagramas N/V/M, deformada, mapa de von Mises).
 *
 * Nada de fisica/calculo vive aqui: solo lectura del modelo y de los
 * resultados ya calculados por solver.js / stress.js.
 */
(function (root) {
  'use strict';

  var MARGIN_PX = 60;
  var MIN_SCALE = 0.01;
  var MAX_SCALE = 2.0;

  function makeView(scale, originX, originY) {
    scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));
    return {
      scale: scale,
      originX: originX,
      originY: originY,
      toPx: function (xMm, yMm) {
        return { x: originX + xMm * scale, y: originY - yMm * scale };
      },
      toModel: function (px, py) {
        return { x: (px - originX) / scale, y: (originY - py) / scale };
      }
    };
  }

  /**
   * Vista que encuadra todos los nodos (o una vista por defecto si no hay
   * ninguno). Llamar explicitamente (al iniciar, al cambiar tamano de
   * ventana, o cuando el usuario pide "ajustar vista") — NO en cada render,
   * para que la vista no "salte" mientras se dibuja.
   */
  function computeView(canvasWidthPx, canvasHeightPx, nodes) {
    var minX, maxX, minY, maxY;
    if (!nodes || nodes.length === 0) {
      minX = -3000; maxX = 3000; minY = -2000; maxY = 2000; // mm, default ~6x4 m
    } else {
      minX = maxX = nodes[0].x;
      minY = maxY = nodes[0].y;
      nodes.forEach(function (n) {
        minX = Math.min(minX, n.x); maxX = Math.max(maxX, n.x);
        minY = Math.min(minY, n.y); maxY = Math.max(maxY, n.y);
      });
      // Padding minimo generoso (2 m): evita que el primer nodo deje una
      // vista hiper-zoomeada donde cualquier clic cercano cae en la misma
      // celda de la grilla de snap.
      var padX = Math.max(2000, (maxX - minX) * 0.15);
      var padY = Math.max(2000, (maxY - minY) * 0.15);
      minX -= padX; maxX += padX; minY -= padY; maxY += padY;
    }
    var boundW = Math.max(1, maxX - minX);
    var boundH = Math.max(1, maxY - minY);
    var scale = Math.min(
      (canvasWidthPx - 2 * MARGIN_PX) / boundW,
      (canvasHeightPx - 2 * MARGIN_PX) / boundH
    );
    scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));

    var cx = (minX + maxX) / 2;
    var cy = (minY + maxY) / 2;
    var originX = canvasWidthPx / 2 - cx * scale;
    var originY = canvasHeightPx / 2 + cy * scale;

    return makeView(scale, originX, originY);
  }

  /** Zoom centrado en (pxFocus, pyFocus), conservando ese punto fijo en pantalla. */
  function zoomView(view, pxFocus, pyFocus, factor) {
    var modelPoint = view.toModel(pxFocus, pyFocus);
    var newScale = view.scale * factor;
    var newOriginX = pxFocus - modelPoint.x * newScale;
    var newOriginY = pyFocus + modelPoint.y * newScale;
    return makeView(newScale, newOriginX, newOriginY);
  }

  function drawGrid(ctx, view, canvasW, canvasH, gridMm) {
    ctx.save();
    ctx.strokeStyle = '#1b2128';
    ctx.lineWidth = 1;
    var topLeft = view.toModel(0, 0);
    var botRight = view.toModel(canvasW, canvasH);
    var xStart = Math.floor(topLeft.x / gridMm) * gridMm;
    var xEnd = Math.ceil(botRight.x / gridMm) * gridMm;
    var yStart = Math.floor(botRight.y / gridMm) * gridMm;
    var yEnd = Math.ceil(topLeft.y / gridMm) * gridMm;
    for (var x = xStart; x <= xEnd; x += gridMm) {
      var p1 = view.toPx(x, yStart), p2 = view.toPx(x, yEnd);
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
    }
    for (var y = yStart; y <= yEnd; y += gridMm) {
      var q1 = view.toPx(xStart, y), q2 = view.toPx(xEnd, y);
      ctx.beginPath(); ctx.moveTo(q1.x, q1.y); ctx.lineTo(q2.x, q2.y); ctx.stroke();
    }
    ctx.restore();
  }

  function drawArrow(ctx, fromX, fromY, toX, toY, color) {
    ctx.save();
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(fromX, fromY); ctx.lineTo(toX, toY); ctx.stroke();
    var angle = Math.atan2(toY - fromY, toX - fromX);
    var headLen = 8;
    ctx.beginPath();
    ctx.moveTo(toX, toY);
    ctx.lineTo(toX - headLen * Math.cos(angle - Math.PI / 6), toY - headLen * Math.sin(angle - Math.PI / 6));
    ctx.lineTo(toX - headLen * Math.cos(angle + Math.PI / 6), toY - headLen * Math.sin(angle + Math.PI / 6));
    ctx.closePath(); ctx.fill();
    ctx.restore();
  }

  function restraintLabel(node) {
    var r = node.restraint;
    if (r.ux && r.uy && r.rz) return 'fixed';
    if (r.ux && r.uy && !r.rz) return 'pinned';
    if (!r.ux && r.uy && !r.rz) return 'roller';
    return 'free';
  }

  function drawSupportSymbol(ctx, px, type) {
    ctx.save();
    ctx.strokeStyle = '#d7ba52';
    ctx.fillStyle = '#d7ba52';
    ctx.lineWidth = 2;
    var x = px.x, y = px.y;
    if (type === 'free') { ctx.restore(); return; }
    if (type === 'pinned' || type === 'roller') {
      ctx.beginPath();
      ctx.moveTo(x, y + 8);
      ctx.lineTo(x - 9, y + 24);
      ctx.lineTo(x + 9, y + 24);
      ctx.closePath();
      ctx.stroke();
      if (type === 'roller') {
        ctx.beginPath(); ctx.arc(x - 5, y + 29, 3, 0, 2 * Math.PI); ctx.stroke();
        ctx.beginPath(); ctx.arc(x + 5, y + 29, 3, 0, 2 * Math.PI); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(x - 12, y + 33); ctx.lineTo(x + 12, y + 33); ctx.stroke();
      } else {
        ctx.beginPath(); ctx.moveTo(x - 12, y + 24); ctx.lineTo(x + 12, y + 24); ctx.stroke();
        for (var i = -10; i <= 10; i += 5) {
          ctx.beginPath(); ctx.moveTo(x + i, y + 24); ctx.lineTo(x + i - 4, y + 30); ctx.stroke();
        }
      }
    } else if (type === 'fixed') {
      ctx.beginPath(); ctx.moveTo(x - 14, y); ctx.lineTo(x + 14, y); ctx.stroke();
      for (var j = -12; j <= 12; j += 5) {
        ctx.beginPath(); ctx.moveTo(x + j, y); ctx.lineTo(x + j - 4, y + 8); ctx.stroke();
      }
    }
    ctx.restore();
  }

  function drawModel(ctx, view, canvasW, canvasH, model, ui) {
    ctx.clearRect(0, 0, canvasW, canvasH);
    drawGrid(ctx, view, canvasW, canvasH, ui.gridSize || 500);

    model.elements.forEach(function (el) {
      var pI = view.toPx(el.nodeI.x, el.nodeI.y);
      var pJ = view.toPx(el.nodeJ.x, el.nodeJ.y);
      var isSel = ui.selection && ui.selection.type === 'element' && ui.selection.id === el.id;
      ctx.save();
      ctx.strokeStyle = isSel ? '#4f8cff' : '#c8ccd2';
      ctx.lineWidth = isSel ? 5 : 3;
      ctx.beginPath(); ctx.moveTo(pI.x, pI.y); ctx.lineTo(pJ.x, pJ.y); ctx.stroke();
      ctx.restore();

      if (el.udl) {
        var midX = (pI.x + pJ.x) / 2, midY = (pI.y + pJ.y) / 2;
        ctx.save();
        ctx.fillStyle = '#9fd3ff'; ctx.font = '12px sans-serif';
        ctx.fillText('w = ' + (el.udl).toFixed(2) + ' N/mm (= kN/m)', midX + 6, midY - 10);
        ctx.restore();
      }
    });

    model.nodes.forEach(function (node) {
      var p = view.toPx(node.x, node.y);
      var isSel = ui.selection && ui.selection.type === 'node' && ui.selection.id === node.id;
      var isPending = ui.pendingElementNode === node.id;
      drawSupportSymbol(ctx, p, restraintLabel(node));
      ctx.save();
      ctx.beginPath();
      ctx.arc(p.x, p.y, isSel ? 8 : 6, 0, 2 * Math.PI);
      ctx.fillStyle = isPending ? '#ffd24f' : (isSel ? '#4f8cff' : '#e6e8eb');
      ctx.fill();
      ctx.strokeStyle = '#0b0d10'; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.restore();
    });

    model.nodalLoads.forEach(function (load) {
      var node = model.nodes.find(function (n) { return n.id === load.nodeId; });
      if (!node) return;
      var p = view.toPx(node.x, node.y);
      if (load.fx || load.fy) {
        var len = 36;
        var mag = Math.sqrt(load.fx * load.fx + load.fy * load.fy) || 1;
        var ux = load.fx / mag, uy = -load.fy / mag; // -y porque pantalla tiene y invertido
        drawArrow(ctx, p.x - ux * len, p.y - uy * len, p.x, p.y, '#ff8a4f');
        ctx.save();
        ctx.fillStyle = '#ff8a4f'; ctx.font = '11px sans-serif';
        var fxKn = root.FEM.Units.forceToUi(load.fx);
        var fyKn = root.FEM.Units.forceToUi(load.fy);
        ctx.fillText('(' + fxKn.toFixed(1) + ', ' + fyKn.toFixed(1) + ') kN', p.x + 8, p.y - 14);
        ctx.restore();
      }
      if (load.m) {
        ctx.save();
        ctx.strokeStyle = '#ff8a4f'; ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(p.x, p.y, 16, 0.3, Math.PI * 1.4); ctx.stroke();
        ctx.fillStyle = '#ff8a4f'; ctx.font = '11px sans-serif';
        ctx.fillText((root.FEM.Units.momentToUi(load.m)).toFixed(2) + ' kN·m', p.x + 18, p.y + 4);
        ctx.restore();
      }
    });
  }

  function colorForT(t) {
    t = Math.max(0, Math.min(1, t));
    var hue = 240 * (1 - t);
    return 'hsl(' + hue + ', 85%, 50%)';
  }

  /**
   * Dibuja los overlays de resultados (diagramas, deformada, banda von Mises)
   * para un elemento, trabajando en un marco local (origen en nodoI, eje x
   * a lo largo del elemento) via transformacion de canvas.
   */
  function drawElementResults(ctx, view, el, ef, stressGrid, globalMax, opts) {
    var pI = view.toPx(el.nodeI.x, el.nodeI.y);
    var pJ = view.toPx(el.nodeJ.x, el.nodeJ.y);
    var screenAngle = Math.atan2(pJ.y - pI.y, pJ.x - pI.x);
    var Lpx = Math.sqrt(Math.pow(pJ.x - pI.x, 2) + Math.pow(pJ.y - pI.y, 2));
    var solver = root.FEM.solver;
    var nx = 24;

    ctx.save();
    ctx.translate(pI.x, pI.y);
    ctx.rotate(screenAngle);

    // --- banda von Mises ---
    if (opts.showVM && stressGrid && globalMax.vonMises > 0) {
      var bandHalf = 12;
      var cols = stressGrid.grid;
      var ny = cols[0].points.length;
      var colW = Lpx / (cols.length - 1);
      for (var ix = 0; ix < cols.length - 1; ix++) {
        var x0 = ix * colW;
        for (var iy = 0; iy < ny - 1; iy++) {
          var v0 = cols[ix].points[iy].vonMises;
          var v1 = cols[ix + 1].points[iy].vonMises;
          var vAvg = (v0 + v1) / 2;
          var y0 = bandHalf - (2 * bandHalf * iy) / (ny - 1);
          var y1 = bandHalf - (2 * bandHalf * (iy + 1)) / (ny - 1);
          ctx.fillStyle = colorForT(vAvg / globalMax.vonMises);
          ctx.fillRect(x0, Math.min(y0, y1), colW + 0.5, Math.abs(y1 - y0));
        }
      }
    }

    // --- diagramas N/V/M (offset perpendicular, relleno translucido) ---
    function drawDiagram(key, maxAbs, color, flip) {
      if (!maxAbs) return;
      var scaleOff = 40 / maxAbs;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      for (var i = 0; i <= nx; i++) {
        var x = (Lpx * i) / nx;
        var xMm = (el.length() * i) / nx;
        var f = solver.internalForcesAt(ef, xMm);
        var val = f[key] * (flip ? -1 : 1);
        ctx.lineTo(x, -val * scaleOff);
      }
      ctx.lineTo(Lpx, 0);
      ctx.closePath();
      ctx.fillStyle = color + '33';
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    if (opts.showM) drawDiagram('M', globalMax.M, '#4fd27a', false);
    if (opts.showV) drawDiagram('V', globalMax.V, '#4fb8ff', true);
    if (opts.showN) drawDiagram('N', globalMax.N, '#ff4fd2', true);

    // --- deformada ---
    if (opts.showDefl && globalMax.defl > 0) {
      var deflScale = 30 / globalMax.defl;
      ctx.beginPath();
      for (var k = 0; k <= nx; k++) {
        var xk = (el.length() * k) / nx;
        var v = solver.deflectionAt(ef, xk);
        var px2 = (Lpx * k) / nx;
        var py2 = -v * deflScale;
        if (k === 0) ctx.moveTo(px2, py2); else ctx.lineTo(px2, py2);
      }
      ctx.setLineDash([5, 4]);
      ctx.strokeStyle = '#ffd24f';
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.setLineDash([]);
    }

    ctx.restore();
  }

  root.FEM = root.FEM || {};
  root.FEM.render = {
    makeView: makeView,
    computeView: computeView,
    zoomView: zoomView,
    drawModel: drawModel,
    drawElementResults: drawElementResults,
    restraintLabel: restraintLabel,
    colorForT: colorForT
  };
})(typeof window !== 'undefined' ? window : global);
