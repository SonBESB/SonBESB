/**
 * Boceto 2D por proyeccion: tres paneles sincronizados (Planta X-Y,
 * Frontal X-Z, Lateral Y-Z) sobre el MISMO modelo 3D, igual idea que un
 * CAD clasico (planta + elevaciones + vista 3D). Cada panel es, en
 * esencia, el mismo patron de vista/grilla/hit-testing que
 * structural/js/render.js (modulo 2D) pero generico sobre que par de
 * coordenadas (u,v) se dibuja — la profundidad (w) la fija el usuario con
 * un valor "activo" por eje (ver app.js), porque un clic en una pantalla
 * 2D no puede definir la tercera dimension por si solo.
 *
 * No depende de structural/ (codigo aparte, como el resto de este modulo).
 */
(function (root) {
  'use strict';

  var MARGIN_PX = 40;
  var MIN_SCALE = 0.005;
  var MAX_SCALE = 5.0;

  /** u/v/w: 'x'|'y'|'z' — que coordenada del nodo 3D (en mm) va a cada eje de pantalla. */
  var PROJECTIONS = {
    xy: { u: 'x', v: 'y', w: 'z', label: 'Planta (X-Y)', wLabel: 'Z' },
    xz: { u: 'x', v: 'z', w: 'y', label: 'Frontal (X-Z)', wLabel: 'Y' },
    yz: { u: 'y', v: 'z', w: 'x', label: 'Lateral (Y-Z)', wLabel: 'X' }
  };

  function projUV(node, proj) {
    return { u: node[proj.u], v: node[proj.v] };
  }

  /** Construye las coordenadas (x,y,z en mm) de un nodo nuevo a partir de un clic (u,v) + el valor activo del eje oculto w. */
  function uvToCoords(proj, u, v, wActive) {
    var c = { x: 0, y: 0, z: 0 };
    c[proj.u] = u; c[proj.v] = v; c[proj.w] = wActive;
    return c;
  }

  function makeView(scale, originX, originY) {
    scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));
    return {
      scale: scale, originX: originX, originY: originY,
      toPx: function (u, v) { return { x: originX + u * scale, y: originY - v * scale }; },
      toModel: function (px, py) { return { u: (px - originX) / scale, v: (originY - py) / scale }; }
    };
  }

  function computeView(canvasW, canvasH, uvPoints) {
    var minU, maxU, minV, maxV;
    if (!uvPoints || uvPoints.length === 0) {
      minU = -3000; maxU = 3000; minV = -2000; maxV = 2000;
    } else {
      minU = maxU = uvPoints[0].u; minV = maxV = uvPoints[0].v;
      uvPoints.forEach(function (p) {
        minU = Math.min(minU, p.u); maxU = Math.max(maxU, p.u);
        minV = Math.min(minV, p.v); maxV = Math.max(maxV, p.v);
      });
      var padU = Math.max(2000, (maxU - minU) * 0.15);
      var padV = Math.max(2000, (maxV - minV) * 0.15);
      minU -= padU; maxU += padU; minV -= padV; maxV += padV;
    }
    var boundW = Math.max(1, maxU - minU), boundH = Math.max(1, maxV - minV);
    var scale = Math.min((canvasW - 2 * MARGIN_PX) / boundW, (canvasH - 2 * MARGIN_PX) / boundH);
    scale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, scale));
    var cu = (minU + maxU) / 2, cv = (minV + maxV) / 2;
    return makeView(scale, canvasW / 2 - cu * scale, canvasH / 2 + cv * scale);
  }

  function zoomView(view, pxFocus, pyFocus, factor) {
    var m = view.toModel(pxFocus, pyFocus);
    var newScale = view.scale * factor;
    return makeView(newScale, pxFocus - m.u * newScale, pyFocus + m.v * newScale);
  }

  function drawGrid(ctx, view, canvasW, canvasH, gridMm) {
    ctx.save();
    ctx.strokeStyle = 'rgba(128,128,128,0.15)';
    ctx.lineWidth = 1;
    var tl = view.toModel(0, 0), br = view.toModel(canvasW, canvasH);
    var uStart = Math.floor(tl.u / gridMm) * gridMm, uEnd = Math.ceil(br.u / gridMm) * gridMm;
    var vStart = Math.floor(br.v / gridMm) * gridMm, vEnd = Math.ceil(tl.v / gridMm) * gridMm;
    for (var u = uStart; u <= uEnd; u += gridMm) {
      var p1 = view.toPx(u, vStart), p2 = view.toPx(u, vEnd);
      ctx.beginPath(); ctx.moveTo(p1.x, p1.y); ctx.lineTo(p2.x, p2.y); ctx.stroke();
    }
    for (var v = vStart; v <= vEnd; v += gridMm) {
      var q1 = view.toPx(uStart, v), q2 = view.toPx(uEnd, v);
      ctx.beginPath(); ctx.moveTo(q1.x, q1.y); ctx.lineTo(q2.x, q2.y); ctx.stroke();
    }
    // ejes u=0 / v=0 un poco mas marcados
    ctx.strokeStyle = 'rgba(128,128,128,0.35)';
    var o1 = view.toPx(uStart, 0), o2 = view.toPx(uEnd, 0);
    ctx.beginPath(); ctx.moveTo(o1.x, o1.y); ctx.lineTo(o2.x, o2.y); ctx.stroke();
    var o3 = view.toPx(0, vStart), o4 = view.toPx(0, vEnd);
    ctx.beginPath(); ctx.moveTo(o3.x, o3.y); ctx.lineTo(o4.x, o4.y); ctx.stroke();
    ctx.restore();
  }

  function restraintLabel(node) {
    var r = node.restraint;
    if (r.ux && r.uy && r.uz && r.rx && r.ry && r.rz) return 'fixed';
    if (r.ux && r.uy && r.uz && !r.rx && !r.ry && !r.rz) return 'pinned';
    if (r.ux || r.uy || r.uz || r.rx || r.ry || r.rz) return 'partial';
    return 'free';
  }

  function drawSketchView(ctx, view, canvasW, canvasH, model, projKey, ui) {
    var proj = PROJECTIONS[projKey];
    ctx.clearRect(0, 0, canvasW, canvasH);
    drawGrid(ctx, view, canvasW, canvasH, ui.gridSize || 500);

    model.elements.forEach(function (el) {
      var pI = view.toPx(el.nodeI[proj.u], el.nodeI[proj.v]);
      var pJ = view.toPx(el.nodeJ[proj.u], el.nodeJ[proj.v]);
      var isSel = ui.selection && ui.selection.type === 'element' && ui.selection.id === el.id;
      ctx.save();
      ctx.strokeStyle = isSel ? '#4f8cff' : '#8891a0';
      ctx.lineWidth = isSel ? 4 : 2.5;
      ctx.beginPath(); ctx.moveTo(pI.x, pI.y); ctx.lineTo(pJ.x, pJ.y); ctx.stroke();
      ctx.restore();
    });

    model.nodes.forEach(function (node) {
      var p = view.toPx(node[proj.u], node[proj.v]);
      var isSel = ui.selection && ui.selection.type === 'node' && ui.selection.id === node.id;
      var isPending = ui.pendingElementNode === node.id;
      var label = restraintLabel(node);
      if (label !== 'free') {
        ctx.save();
        ctx.strokeStyle = '#d7ba52'; ctx.lineWidth = 2;
        if (label === 'fixed') {
          ctx.beginPath(); ctx.moveTo(p.x - 10, p.y + 10); ctx.lineTo(p.x + 10, p.y + 10); ctx.stroke();
          for (var i = -8; i <= 8; i += 4) { ctx.beginPath(); ctx.moveTo(p.x + i, p.y + 10); ctx.lineTo(p.x + i - 3, p.y + 16); ctx.stroke(); }
        } else {
          ctx.beginPath(); ctx.moveTo(p.x, p.y + 6); ctx.lineTo(p.x - 8, p.y + 18); ctx.lineTo(p.x + 8, p.y + 18); ctx.closePath(); ctx.stroke();
        }
        ctx.restore();
      }
      ctx.save();
      ctx.beginPath(); ctx.arc(p.x, p.y, isSel ? 7 : 5, 0, 2 * Math.PI);
      ctx.fillStyle = isPending ? '#ffd24f' : (isSel ? '#4f8cff' : '#e6e8eb');
      ctx.fill(); ctx.strokeStyle = '#06080a'; ctx.lineWidth = 1.2; ctx.stroke();
      ctx.restore();
    });

    model.nodalLoads.forEach(function (load) {
      var node = model.nodes.find(function (n) { return n.id === load.nodeId; });
      if (!node) return;
      var fu = load[{ x: 'fx', y: 'fy', z: 'fz' }[proj.u]];
      var fv = load[{ x: 'fx', y: 'fy', z: 'fz' }[proj.v]];
      if (!fu && !fv) return;
      var p = view.toPx(node[proj.u], node[proj.v]);
      var mag = Math.sqrt(fu * fu + fv * fv) || 1;
      var ux = fu / mag, uyS = -fv / mag;
      var len = 28;
      ctx.save();
      ctx.strokeStyle = '#ff8a4f'; ctx.fillStyle = '#ff8a4f'; ctx.lineWidth = 2;
      var fromX = p.x - ux * len, fromY = p.y - uyS * len;
      ctx.beginPath(); ctx.moveTo(fromX, fromY); ctx.lineTo(p.x, p.y); ctx.stroke();
      var ang = Math.atan2(p.y - fromY, p.x - fromX);
      ctx.beginPath(); ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - 7 * Math.cos(ang - Math.PI / 6), p.y - 7 * Math.sin(ang - Math.PI / 6));
      ctx.lineTo(p.x - 7 * Math.cos(ang + Math.PI / 6), p.y - 7 * Math.sin(ang + Math.PI / 6));
      ctx.closePath(); ctx.fill();
      ctx.restore();
    });
  }

  function nodeAtPixel(view, model, projKey, px, py, tolPx) {
    var proj = PROJECTIONS[projKey];
    tolPx = tolPx || 14;
    var best = null, bestD = tolPx;
    model.nodes.forEach(function (n) {
      var p = view.toPx(n[proj.u], n[proj.v]);
      var d = Math.hypot(p.x - px, p.y - py);
      if (d < bestD) { bestD = d; best = n; }
    });
    return best;
  }

  function distToSegment(px, py, ax, ay, bx, by) {
    var dx = bx - ax, dy = by - ay;
    var len2 = dx * dx + dy * dy;
    var t = len2 === 0 ? 0 : ((px - ax) * dx + (py - ay) * dy) / len2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (ax + t * dx), py - (ay + t * dy));
  }

  function elementAtPixel(view, model, projKey, px, py, tolPx) {
    var proj = PROJECTIONS[projKey];
    tolPx = tolPx || 8;
    var best = null, bestD = tolPx;
    model.elements.forEach(function (el) {
      var a = view.toPx(el.nodeI[proj.u], el.nodeI[proj.v]);
      var b = view.toPx(el.nodeJ[proj.u], el.nodeJ[proj.v]);
      var d = distToSegment(px, py, a.x, a.y, b.x, b.y);
      if (d < bestD) { bestD = d; best = el; }
    });
    return best;
  }

  root.FEM3D = root.FEM3D || {};
  root.FEM3D.Sketch = {
    PROJECTIONS: PROJECTIONS,
    projUV: projUV,
    uvToCoords: uvToCoords,
    makeView: makeView,
    computeView: computeView,
    zoomView: zoomView,
    drawSketchView: drawSketchView,
    nodeAtPixel: nodeAtPixel,
    elementAtPixel: elementAtPixel,
    restraintLabel: restraintLabel
  };
})(typeof window !== 'undefined' ? window : global);
