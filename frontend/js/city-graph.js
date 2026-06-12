/* ============================================================
   Oober — City Graph Visualization (D3.js)
   THE STAR COMPONENT — Dual force-directed city graphs
   with animated rider/driver dots and glowing match lines
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  // ── Constants ──────────────────────────────────────────────────
  var NODE_RADIUS = 20;
  var RIDER_SIZE = 5;
  var DRIVER_SIZE = 4;
  var MATCH_LINE_WIDTH = 2;
  var ZONE_COLORS = {
    idle: 'rgba(30, 41, 59, 0.8)',
    active: 'rgba(59, 130, 246, 0.15)',
    stroke_idle: 'rgba(148, 163, 184, 0.2)',
    stroke_active: 'rgba(59, 130, 246, 0.4)'
  };

  // ── State ──────────────────────────────────────────────────────
  var graphs = {
    joint: null,
    baseline: null
  };

  var cityData = null;
  var nodePositions = [];


  /**
   * Initialize both city graph SVGs.
   * Runs D3 force simulation to compute stable node positions,
   * then renders zones and edges into both SVGs.
   *
   * @param {Object} cityGraph - { nodes: [0..N], edges: [{source, target, cost}] }
   */
  function init(cityGraph) {
    cityData = cityGraph;

    // Compute layout once using D3 force simulation
    var simNodes = cityGraph.nodes.map(function (id) {
      return { id: id, x: 0, y: 0 };
    });

    var simLinks = cityGraph.edges.map(function (e) {
      return { source: e.source, target: e.target, cost: e.cost };
    });

    // Run force simulation to completion (no animation)
    var simulation = d3.forceSimulation(simNodes)
      .force('link', d3.forceLink(simLinks).id(function (d) { return d.id; }).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(0, 0))
      .force('collision', d3.forceCollide(NODE_RADIUS + 10))
      .stop();

    // Tick to completion
    for (var i = 0; i < 300; i++) simulation.tick();

    // Store positions
    nodePositions = simNodes.map(function (n) {
      return { id: n.id, x: n.x, y: n.y };
    });

    // Initialize both SVGs
    setupSVG('svg-joint', 'joint');
    setupSVG('svg-baseline', 'baseline');
  }


  /**
   * Set up a single SVG with zones and edges.
   */
  function setupSVG(svgId, key) {
    var svgEl = document.getElementById(svgId);
    if (!svgEl) return;

    var wrap = svgEl.parentElement;
    var width = wrap.clientWidth || 500;
    var height = wrap.clientHeight || 300;

    var svg = d3.select('#' + svgId)
      .attr('viewBox', null)
      .attr('width', width)
      .attr('height', height);

    svg.selectAll('*').remove();

    // Compute bounds and scale
    var xExtent = d3.extent(nodePositions, function (d) { return d.x; });
    var yExtent = d3.extent(nodePositions, function (d) { return d.y; });
    var dataWidth = (xExtent[1] - xExtent[0]) || 1;
    var dataHeight = (yExtent[1] - yExtent[0]) || 1;
    var padding = 50;
    var scaleX = (width - 2 * padding) / dataWidth;
    var scaleY = (height - 2 * padding) / dataHeight;
    var scale = Math.min(scaleX, scaleY);

    var centerX = width / 2;
    var centerY = height / 2;
    var dataCenterX = (xExtent[0] + xExtent[1]) / 2;
    var dataCenterY = (yExtent[0] + yExtent[1]) / 2;

    function tx(x) { return centerX + (x - dataCenterX) * scale; }
    function ty(y) { return centerY + (y - dataCenterY) * scale; }

    // Define gradient for match lines
    var defs = svg.append('defs');

    var gradient = defs.append('linearGradient')
      .attr('id', 'match-gradient-' + key)
      .attr('gradientUnits', 'userSpaceOnUse');

    gradient.append('stop')
      .attr('offset', '0%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.3);

    gradient.append('stop')
      .attr('offset', '50%')
      .attr('stop-color', '#3b82f6')
      .attr('stop-opacity', 0.9);

    gradient.append('stop')
      .attr('offset', '100%')
      .attr('stop-color', '#10b981')
      .attr('stop-opacity', 0.5);

    // Glow filter
    var glow = defs.append('filter')
      .attr('id', 'glow-' + key)
      .attr('x', '-50%').attr('y', '-50%')
      .attr('width', '200%').attr('height', '200%');

    glow.append('feGaussianBlur')
      .attr('stdDeviation', '3')
      .attr('result', 'glow');

    var feMerge = glow.append('feMerge');
    feMerge.append('feMergeNode').attr('in', 'glow');
    feMerge.append('feMergeNode').attr('in', 'SourceGraphic');

    // Layers
    var edgeLayer = svg.append('g').attr('class', 'edge-layer');
    var matchLayer = svg.append('g').attr('class', 'match-layer');
    var agentLayer = svg.append('g').attr('class', 'agent-layer');
    var nodeLayer = svg.append('g').attr('class', 'node-layer');

    // Draw edges
    if (cityData.edges) {
      edgeLayer.selectAll('.graph-edge')
        .data(cityData.edges)
        .join('path')
        .attr('class', 'graph-edge')
        .attr('d', function (d) {
          var sp = nodePositions.find(function (n) { return n.id === d.source; });
          var tp = nodePositions.find(function (n) { return n.id === d.target; });
          if (!sp || !tp) return '';
          var sx = tx(sp.x), sy = ty(sp.y);
          var ex = tx(tp.x), ey = ty(tp.y);
          var mx = (sx + ex) / 2 + (sy - ey) * 0.15;
          var my = (sy + ey) / 2 + (ex - sx) * 0.15;
          return 'M ' + sx + ' ' + sy + ' Q ' + mx + ' ' + my + ' ' + ex + ' ' + ey;
        })
        .attr('data-source', function (d) { return d.source; })
        .attr('data-target', function (d) { return d.target; });
    }

    // Draw zone nodes
    var zoneGroups = nodeLayer.selectAll('.zone-node')
      .data(nodePositions)
      .join('g')
      .attr('class', 'zone-node')
      .attr('transform', function (d) {
        return 'translate(' + tx(d.x) + ',' + ty(d.y) + ')';
      })
      .attr('data-zone', function (d) { return d.id; });

    zoneGroups.append('circle')
      .attr('r', NODE_RADIUS)
      .attr('fill', ZONE_COLORS.idle)
      .attr('stroke', ZONE_COLORS.stroke_idle)
      .attr('stroke-width', 1.5);

    zoneGroups.append('text')
      .text(function (d) { return d.id; })
      .attr('fill', '#64748b')
      .attr('font-family', "'JetBrains Mono', monospace")
      .attr('font-size', '10px')
      .attr('text-anchor', 'middle')
      .attr('dominant-baseline', 'central');

    // Store reference
    graphs[key] = {
      svg: svg,
      edgeLayer: edgeLayer,
      matchLayer: matchLayer,
      agentLayer: agentLayer,
      nodeLayer: nodeLayer,
      tx: tx,
      ty: ty,
      width: width,
      height: height
    };
  }


  /**
   * Get pixel position for a zone node.
   */
  function getZonePos(graphKey, zoneId) {
    var g = graphs[graphKey];
    if (!g) return { x: 0, y: 0 };
    var node = nodePositions.find(function (n) { return n.id === zoneId; });
    if (!node) return { x: 0, y: 0 };
    return { x: g.tx(node.x), y: g.ty(node.y) };
  }


  /**
   * Scatter agent position slightly around zone center.
   */
  function jitter(pos, index, total) {
    var angle = (index / Math.max(total, 1)) * Math.PI * 2;
    var radius = 8 + (index % 3) * 4;
    return {
      x: pos.x + Math.cos(angle) * radius,
      y: pos.y + Math.sin(angle) * radius
    };
  }


  /**
   * Update a single graph for a given time window.
   *
   * @param {string} graphKey - 'joint' or 'baseline'
   * @param {Object} windowData - the window object with riders, drivers, assignments
   * @param {string} systemKey - 'joint_opt' or 'seq_baseline'
   * @param {Object} animTimings - { spawn, match, hold } durations in ms
   * @returns {Object} anime.js timeline for this graph
   */
  function updateGraph(graphKey, windowData, systemKey, animTimings) {
    var g = graphs[graphKey];
    if (!g) return null;

    var riders = windowData.riders;
    var drivers = windowData.drivers;
    var systemData = windowData[systemKey];
    var assignments = systemData.assignments;
    var spawn = animTimings.spawn;
    var match = animTimings.match;

    // Clear previous agents and matches
    g.agentLayer.selectAll('*').remove();
    g.matchLayer.selectAll('*').remove();

    // Reset zone node visuals
    g.nodeLayer.selectAll('.zone-node circle')
      .attr('fill', ZONE_COLORS.idle)
      .attr('stroke', ZONE_COLORS.stroke_idle);

    // Find active zones
    var activeZones = {};
    riders.forEach(function (r) { activeZones[r.origin_zone] = true; });
    drivers.forEach(function (d) { activeZones[d.current_zone] = true; });

    // Highlight active zones
    g.nodeLayer.selectAll('.zone-node').each(function () {
      var zone = +d3.select(this).attr('data-zone');
      if (activeZones[zone]) {
        d3.select(this).select('circle')
          .attr('fill', ZONE_COLORS.active)
          .attr('stroke', ZONE_COLORS.stroke_active);
      }
    });

    // Highlight active edges
    var assignedPairs = {};
    assignments.forEach(function (a) {
      var rider = riders.find(function (r) { return r.id === a[0]; });
      var driver = drivers.find(function (d) { return d.id === a[1]; });
      if (rider && driver) {
        assignedPairs[driver.current_zone + '-' + rider.origin_zone] = true;
      }
    });

    g.edgeLayer.selectAll('.graph-edge').each(function () {
      var el = d3.select(this);
      var src = el.attr('data-source');
      var tgt = el.attr('data-target');
      var key = src + '-' + tgt;
      if (assignedPairs[key]) {
        el.classed('active', true);
      } else {
        el.classed('active', false);
      }
    });

    // Build matched rider/driver ID sets
    var matchedRiders = {};
    var matchedDrivers = {};
    assignments.forEach(function (a) {
      matchedRiders[a[0]] = true;
      matchedDrivers[a[1]] = true;
    });

    // Draw rider dots (small diamonds)
    var riderDots = [];
    riders.forEach(function (r, idx) {
      var zonePos = getZonePos(graphKey, r.origin_zone);
      var pos = jitter(zonePos, idx, riders.length);
      var color = matchedRiders[r.id] ? '#f59e0b' : '#ef4444';

      var diamond = g.agentLayer.append('rect')
        .attr('x', pos.x - RIDER_SIZE)
        .attr('y', pos.y - RIDER_SIZE)
        .attr('width', RIDER_SIZE * 2)
        .attr('height', RIDER_SIZE * 2)
        .attr('transform', 'rotate(45, ' + pos.x + ', ' + pos.y + ')')
        .attr('fill', color)
        .attr('opacity', 0)
        .attr('class', 'rider-dot')
        .attr('data-rider-id', r.id);

      riderDots.push({ el: diamond.node(), pos: pos, rider: r });
    });

    // Draw driver dots (circles)
    var driverDots = [];
    drivers.forEach(function (d, idx) {
      var zonePos = getZonePos(graphKey, d.current_zone);
      var pos = jitter(zonePos, idx + riders.length, drivers.length);
      var color = matchedDrivers[d.id] ? '#10b981' : '#475569';

      var circle = g.agentLayer.append('circle')
        .attr('cx', pos.x)
        .attr('cy', pos.y)
        .attr('r', DRIVER_SIZE)
        .attr('fill', color)
        .attr('opacity', 0)
        .attr('class', 'driver-dot')
        .attr('data-driver-id', d.id);

      driverDots.push({ el: circle.node(), pos: pos, driver: d });
    });

    // Draw unmatched feasible edges (bipartite relations where rider WTP >= driver MAF and they are not matched together)
    var unmatchedFeasibleLines = [];
    var matchedPairMap = {};
    assignments.forEach(function (a) {
      matchedPairMap[a[0] + '-' + a[1]] = true;
    });

    riders.forEach(function (r) {
      drivers.forEach(function (d) {
        if (r.wtp >= d.maf && !matchedPairMap[r.id + '-' + d.id]) {
          var riderDot = riderDots.find(function (rd) { return rd.rider.id === r.id; });
          var driverDot = driverDots.find(function (dd) { return dd.driver.id === d.id; });
          if (riderDot && driverDot) {
            var line = g.matchLayer.append('line')
              .attr('x1', driverDot.pos.x)
              .attr('y1', driverDot.pos.y)
              .attr('x2', riderDot.pos.x)
              .attr('y2', riderDot.pos.y)
              .attr('class', 'feasible-edge')
              .attr('opacity', 0);
            unmatchedFeasibleLines.push(line.node());
          }
        }
      });
    });

    // Build anime.js timeline
    var tl = anime.timeline({
      easing: 'cubicBezier(0.4, 0, 0.2, 1)',
      autoplay: false
    });

    // Phase 1: Spawn riders
    if (riderDots.length > 0) {
      tl.add({
        targets: riderDots.map(function (d) { return d.el; }),
        opacity: [0, 1],
        scale: [0.3, 1],
        duration: spawn,
        delay: anime.stagger(Math.min(30, spawn / riderDots.length))
      });
    }

    // Phase 1b: Spawn drivers (overlapping slightly with riders)
    if (driverDots.length > 0) {
      tl.add({
        targets: driverDots.map(function (d) { return d.el; }),
        opacity: [0, 0.9],
        scale: [0.3, 1],
        duration: spawn,
        delay: anime.stagger(Math.min(25, spawn / driverDots.length))
      }, '-=' + Math.round(spawn * 0.6));
    }

    // Phase 1.5: Spawn unmatched feasible lines
    if (unmatchedFeasibleLines.length > 0) {
      tl.add({
        targets: unmatchedFeasibleLines,
        opacity: [0, 0.25],
        duration: spawn,
      }, '-=' + Math.round(spawn * 0.4));
    }

    // Phase 2: Draw match lines
    assignments.forEach(function (assignment, i) {
      var riderId = assignment[0];
      var driverId = assignment[1];

      var riderDot = riderDots.find(function (rd) { return rd.rider.id === riderId; });
      var driverDot = driverDots.find(function (dd) { return dd.driver.id === driverId; });

      if (!riderDot || !driverDot) return;

      var line = g.matchLayer.append('line')
        .attr('x1', driverDot.pos.x)
        .attr('y1', driverDot.pos.y)
        .attr('x2', driverDot.pos.x) // Start at driver position
        .attr('y2', driverDot.pos.y)
        .attr('stroke', '#3b82f6')
        .attr('stroke-width', MATCH_LINE_WIDTH)
        .attr('stroke-linecap', 'round')
        .attr('opacity', 0)
        .attr('filter', 'url(#glow-' + graphKey + ')')
        .attr('class', 'match-line');

      var offset = Math.round(spawn * 1.4 + i * Math.min(25, match / (assignments.length || 1)));

      tl.add({
        targets: line.node(),
        opacity: [0, 0.85],
        x2: riderDot.pos.x,
        y2: riderDot.pos.y,
        duration: Math.round(match * 0.7),
        easing: 'cubicBezier(0.4, 0, 0.2, 1)'
      }, offset);
    });

    // Phase 3: Fade unmatched agents and feasible lines
    var unmatchedRiders = riderDots.filter(function (rd) {
      return !matchedRiders[rd.rider.id];
    });
    var unmatchedDrivers = driverDots.filter(function (dd) {
      return !matchedDrivers[dd.driver.id];
    });

    var unmatchedEls = unmatchedRiders.map(function (d) { return d.el; })
      .concat(unmatchedDrivers.map(function (d) { return d.el; }));

    if (unmatchedEls.length > 0) {
      tl.add({
        targets: unmatchedEls,
        opacity: 0.15,
        duration: Math.round(match * 0.4),
        easing: 'cubicBezier(0.4, 0, 0.2, 1)'
      }, '-=' + Math.round(match * 0.2));
    }

    if (unmatchedFeasibleLines.length > 0) {
      tl.add({
        targets: unmatchedFeasibleLines,
        opacity: 0.04,
        duration: Math.round(match * 0.4),
        easing: 'cubicBezier(0.4, 0, 0.2, 1)'
      }, '-=' + Math.round(match * 0.4));
    }

    return tl;
  }


  /**
   * Clear all agents and match lines from both graphs.
   */
  function clearAgents() {
    ['joint', 'baseline'].forEach(function (key) {
      var g = graphs[key];
      if (!g) return;
      g.agentLayer.selectAll('*').remove();
      g.matchLayer.selectAll('*').remove();
      g.nodeLayer.selectAll('.zone-node circle')
        .attr('fill', ZONE_COLORS.idle)
        .attr('stroke', ZONE_COLORS.stroke_idle);
      g.edgeLayer.selectAll('.graph-edge').classed('active', false);
    });
  }


  /**
   * Resize handler — re-render both SVGs.
   */
  function resize() {
    if (!cityData) return;
    setupSVG('svg-joint', 'joint');
    setupSVG('svg-baseline', 'baseline');
  }


  // Export
  window.OoberApp.cityGraph = {
    init: init,
    updateGraph: updateGraph,
    clearAgents: clearAgents,
    resize: resize
  };

})();
