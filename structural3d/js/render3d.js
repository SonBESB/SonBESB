/**
 * Escena Three.js: geometria del modelo (nodos, barras, apoyos, cargas) y
 * overlays de resultados (forma deformada coloreada por von Mises).
 * Trabaja en METROS en la escena (convierte desde mm internos solo aqui).
 */
(function (root) {
  'use strict';

  var MM_TO_M = 1 / 1000;

  function init(container) {
    var scene = new THREE.Scene();
    scene.background = new THREE.Color(0x06080a);

    var camera = new THREE.PerspectiveCamera(50, container.clientWidth / container.clientHeight, 0.01, 1000);
    camera.up.set(0, 0, 1);
    camera.position.set(8, -12, 8);

    var renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(container.clientWidth, container.clientHeight);
    container.appendChild(renderer.domElement);

    var controls = new THREE.OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;

    var grid = new THREE.GridHelper(20, 20, 0x2a313c, 0x1a1f26);
    grid.rotation.x = Math.PI / 2; // plano XY en vez de XZ (Three default)
    scene.add(grid);

    var axes = new THREE.AxesHelper(1.2);
    scene.add(axes);

    scene.add(new THREE.AmbientLight(0xffffff, 0.6));
    var dir = new THREE.DirectionalLight(0xffffff, 0.6);
    dir.position.set(5, -8, 10);
    scene.add(dir);

    var modelGroup = new THREE.Group();
    var resultGroup = new THREE.Group();
    scene.add(modelGroup);
    scene.add(resultGroup);

    function resize() {
      camera.aspect = container.clientWidth / container.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(container.clientWidth, container.clientHeight);
    }

    function animate() {
      requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    }
    animate();

    return {
      scene: scene, camera: camera, renderer: renderer, controls: controls,
      modelGroup: modelGroup, resultGroup: resultGroup, resize: resize
    };
  }

  function fitView(ctx, nodes) {
    if (!nodes || nodes.length === 0) {
      ctx.camera.position.set(8, -12, 8);
      ctx.controls.target.set(0, 0, 0);
      ctx.controls.update();
      return;
    }
    var minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity, minZ = Infinity, maxZ = -Infinity;
    nodes.forEach(function (n) {
      var x = n.x * MM_TO_M, y = n.y * MM_TO_M, z = n.z * MM_TO_M;
      minX = Math.min(minX, x); maxX = Math.max(maxX, x);
      minY = Math.min(minY, y); maxY = Math.max(maxY, y);
      minZ = Math.min(minZ, z); maxZ = Math.max(maxZ, z);
    });
    var cx = (minX + maxX) / 2, cy = (minY + maxY) / 2, cz = (minZ + maxZ) / 2;
    var size = Math.max(2, maxX - minX, maxY - minY, maxZ - minZ);
    ctx.controls.target.set(cx, cy, cz);
    ctx.camera.position.set(cx + size * 1.2, cy - size * 1.6, cz + size * 1.0);
    ctx.controls.update();
  }

  function clearGroup(group) {
    while (group.children.length) {
      var obj = group.children.pop();
      if (obj.geometry) obj.geometry.dispose();
      if (obj.material) obj.material.dispose();
    }
  }

  function restraintLabel(node) {
    var r = node.restraint;
    if (r.ux && r.uy && r.uz && r.rx && r.ry && r.rz) return 'fixed';
    if (r.ux && r.uy && r.uz && !r.rx && !r.ry && !r.rz) return 'pinned';
    if (r.ux || r.uy || r.uz || r.rx || r.ry || r.rz) return 'partial';
    return 'free';
  }

  function cylinderBetween(p1, p2, radius, material) {
    var dir = new THREE.Vector3().subVectors(p2, p1);
    var len = dir.length();
    var geom = new THREE.CylinderGeometry(radius, radius, len, 8);
    geom.translate(0, len / 2, 0);
    var mesh = new THREE.Mesh(geom, material);
    mesh.position.copy(p1);
    var axis = new THREE.Vector3(0, 1, 0);
    var quat = new THREE.Quaternion().setFromUnitVectors(axis, dir.clone().normalize());
    mesh.quaternion.copy(quat);
    return mesh;
  }

  function drawModel(ctx, model, selection) {
    clearGroup(ctx.modelGroup);
    var g = ctx.modelGroup;

    var nodeMat = new THREE.MeshStandardMaterial({ color: 0xe6e8eb });
    var selMat = new THREE.MeshStandardMaterial({ color: 0x4f8cff });
    var elemMat = new THREE.MeshStandardMaterial({ color: 0x8891a0 });
    var selElemMat = new THREE.MeshStandardMaterial({ color: 0x4f8cff });
    var supportMat = new THREE.MeshStandardMaterial({ color: 0xd7ba52 });

    model.elements.forEach(function (el) {
      var p1 = new THREE.Vector3(el.nodeI.x * MM_TO_M, el.nodeI.y * MM_TO_M, el.nodeI.z * MM_TO_M);
      var p2 = new THREE.Vector3(el.nodeJ.x * MM_TO_M, el.nodeJ.y * MM_TO_M, el.nodeJ.z * MM_TO_M);
      var isSel = selection && selection.type === 'element' && selection.id === el.id;
      g.add(cylinderBetween(p1, p2, isSel ? 0.035 : 0.02, isSel ? selElemMat : elemMat));
    });

    model.nodes.forEach(function (node) {
      var p = new THREE.Vector3(node.x * MM_TO_M, node.y * MM_TO_M, node.z * MM_TO_M);
      var isSel = selection && selection.type === 'node' && selection.id === node.id;
      var sphere = new THREE.Mesh(new THREE.SphereGeometry(isSel ? 0.07 : 0.05, 12, 12), isSel ? selMat : nodeMat);
      sphere.position.copy(p);
      g.add(sphere);

      var label = restraintLabel(node);
      if (label !== 'free') {
        var markerGeom = label === 'fixed'
          ? new THREE.BoxGeometry(0.16, 0.16, 0.16)
          : new THREE.ConeGeometry(0.1, 0.16, 8);
        var marker = new THREE.Mesh(markerGeom, supportMat);
        marker.position.set(p.x, p.y, p.z - 0.12);
        if (label !== 'fixed') marker.rotation.x = Math.PI;
        g.add(marker);
      }
    });

    model.nodalLoads.forEach(function (load) {
      var node = model.nodes.find(function (n) { return n.id === load.nodeId; });
      if (!node) return;
      var p = new THREE.Vector3(node.x * MM_TO_M, node.y * MM_TO_M, node.z * MM_TO_M);
      var fvec = new THREE.Vector3(load.fx, load.fy, load.fz);
      var mag = fvec.length();
      if (mag > 0) {
        var dir = fvec.clone().normalize();
        var len = 0.8;
        var arrow = new THREE.ArrowHelper(dir, p.clone().sub(dir.clone().multiplyScalar(len)), len, 0xff8a4f, 0.15, 0.08);
        g.add(arrow);
      }
    });
  }

  function colorForT(t) {
    t = Math.max(0, Math.min(1, t));
    var c = new THREE.Color();
    c.setHSL((1 - t) * (240 / 360), 0.85, 0.5);
    return c;
  }

  /**
   * Dibuja la forma deformada (escalada) coloreada por von Mises, usando
   * los resultados de solve()/stress.js. deflScale: factor de escala
   * (si 0 o undefined, se calcula automaticamente para que el
   * desplazamiento maximo sea ~8% del tamano del modelo).
   */
  function drawResults(ctx, model, result, stressGrids, globalMaxVM, options, deflScaleOverride) {
    clearGroup(ctx.resultGroup);
    if (!options.showDefl && !options.showVM) return;
    var g = ctx.resultGroup;
    var solver = root.FEM3D.solver;

    var maxDeflMm = 0;
    model.elements.forEach(function (el) {
      var ef = result.elementForces.get(el.id);
      for (var i = 0; i <= 10; i++) {
        var x = (ef.L * i) / 10;
        var d = solver.deflectionAt(ef, x);
        maxDeflMm = Math.max(maxDeflMm, Math.abs(d.v), Math.abs(d.w));
      }
    });

    var modelSize = 0;
    model.nodes.forEach(function (n) {
      modelSize = Math.max(modelSize, Math.abs(n.x), Math.abs(n.y), Math.abs(n.z));
    });
    modelSize = Math.max(modelSize * MM_TO_M, 1);

    var scale = deflScaleOverride;
    if (!scale) {
      scale = maxDeflMm > 0 ? (modelSize * 0.08 * 1000) / maxDeflMm : 1;
    }

    model.elements.forEach(function (el) {
      var ef = result.elementForces.get(el.id);
      var grid = stressGrids.get(el.id);
      var axes = ef.axes;
      var ex = new THREE.Vector3(axes.ex[0], axes.ex[1], axes.ex[2]);
      var ey = new THREE.Vector3(axes.ey[0], axes.ey[1], axes.ey[2]);
      var ez = new THREE.Vector3(axes.ez[0], axes.ez[1], axes.ez[2]);
      var origin = new THREE.Vector3(el.nodeI.x, el.nodeI.y, el.nodeI.z);

      var nx = grid.grid.length;
      var positions = [];
      var colors = [];
      for (var i = 0; i < nx; i++) {
        var col = grid.grid[i];
        var x = col.x;
        var pos = origin.clone().add(ex.clone().multiplyScalar(x));
        if (options.showDefl) {
          var d = solver.deflectionAt(ef, x);
          pos.add(ey.clone().multiplyScalar(d.v * scale));
          pos.add(ez.clone().multiplyScalar(d.w * scale));
        }
        positions.push(pos.x * MM_TO_M, pos.y * MM_TO_M, pos.z * MM_TO_M);

        var maxVmHere = 0;
        col.points.forEach(function (pt) { maxVmHere = Math.max(maxVmHere, pt.vonMises); });
        var t = options.showVM && globalMaxVM > 0 ? maxVmHere / globalMaxVM : 0.4;
        var c = colorForT(t);
        colors.push(c.r, c.g, c.b);
      }

      var geom = new THREE.BufferGeometry();
      geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      geom.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      var mat = new THREE.LineBasicMaterial({ vertexColors: true, linewidth: 3 });
      g.add(new THREE.Line(geom, mat));
    });

    return scale;
  }

  root.FEM3DRender = {
    init: init,
    fitView: fitView,
    drawModel: drawModel,
    drawResults: drawResults,
    colorForT: colorForT,
    restraintLabel: restraintLabel
  };
})(typeof window !== 'undefined' ? window : global);
