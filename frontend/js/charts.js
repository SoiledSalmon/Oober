/* ============================================================
   Oober — Charts Module
   Canvas-based line charts for per-window metric comparison
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  // ── Chart Configs ──────────────────────────────────────────────
  var CHART_DEFS = [
    { id: 'chart-wait', key: 'wait_time', label: 'Wait Time' },
    { id: 'chart-variance', key: 'earnings_variance', label: 'Earnings Variance' },
    { id: 'chart-price', key: 'price_deviation', label: 'Price Deviation' },
    { id: 'chart-match', key: 'matching_rate', label: 'Matching Rate' }
  ];

  // ── Theme Colors ───────────────────────────────────────────────
  var COLORS = {
    joint: '#3b82f6',
    jointFill: 'rgba(59, 130, 246, 0.08)',
    baseline: '#ef4444',
    baselineFill: 'rgba(239, 68, 68, 0.05)',
    grid: 'rgba(148, 163, 184, 0.06)',
    axis: 'rgba(148, 163, 184, 0.15)',
    text: '#64748b',
    currentDot: '#3b82f6',
    currentGlow: 'rgba(59, 130, 246, 0.4)',
    bg: 'transparent'
  };

  // ── State ──────────────────────────────────────────────────────
  var traceData = null;
  var currentWindowIndex = -1;
  var charts = {};


  /**
   * Initialize charts with trace data.
   */
  function init(data) {
    traceData = data;
    currentWindowIndex = -1;

    CHART_DEFS.forEach(function (def) {
      var canvas = document.getElementById(def.id);
      if (!canvas) return;

      var ctx = canvas.getContext('2d');
      var dpr = window.devicePixelRatio || 1;
      var wrap = canvas.parentElement;
      var w = wrap.clientWidth;
      var h = wrap.clientHeight;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      ctx.scale(dpr, dpr);
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';

      charts[def.key] = {
        canvas: canvas,
        ctx: ctx,
        width: w,
        height: h,
        def: def
      };

      drawChart(def.key, -1);
    });
  }


  /**
   * Draw a chart up to the given window index.
   */
  function drawChart(key, upToWindow) {
    var chart = charts[key];
    if (!chart || !traceData) return;

    var ctx = chart.ctx;
    var w = chart.width;
    var h = chart.height;
    var windows = traceData.windows;
    var total = windows.length;

    // Margins
    var margin = { top: 10, right: 16, bottom: 28, left: 52 };
    var plotW = w - margin.left - margin.right;
    var plotH = h - margin.top - margin.bottom;

    // Clear
    ctx.clearRect(0, 0, w, h);

    // Collect all values for scale
    var allVals = [];
    windows.forEach(function (win) {
      allVals.push(win.joint_opt[key]);
      allVals.push(win.seq_baseline[key]);
    });

    var minVal = Math.min.apply(null, allVals);
    var maxVal = Math.max.apply(null, allVals);
    var range = maxVal - minVal || 1;
    minVal -= range * 0.1;
    maxVal += range * 0.1;
    range = maxVal - minVal;

    // Scale functions
    function sx(i) { return margin.left + (i / Math.max(total - 1, 1)) * plotW; }
    function sy(v) { return margin.top + plotH - ((v - minVal) / range) * plotH; }

    // Draw gridlines
    ctx.strokeStyle = COLORS.grid;
    ctx.lineWidth = 1;
    var numGridLines = 4;
    for (var g = 0; g <= numGridLines; g++) {
      var gy = margin.top + (g / numGridLines) * plotH;
      ctx.beginPath();
      ctx.moveTo(margin.left, gy);
      ctx.lineTo(w - margin.right, gy);
      ctx.stroke();
    }

    // Draw axes
    ctx.strokeStyle = COLORS.axis;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(margin.left, margin.top);
    ctx.lineTo(margin.left, margin.top + plotH);
    ctx.lineTo(w - margin.right, margin.top + plotH);
    ctx.stroke();

    // Y-axis labels
    ctx.fillStyle = COLORS.text;
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (var l = 0; l <= numGridLines; l++) {
      var val = minVal + (1 - l / numGridLines) * range;
      var ly = margin.top + (l / numGridLines) * plotH;
      var label;
      if (key === 'price_deviation' || key === 'matching_rate') {
        label = val.toFixed(2);
      } else {
        label = val.toFixed(0);
      }
      ctx.fillText(label, margin.left - 6, ly);
    }

    // X-axis labels
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    var xLabelStep = Math.max(1, Math.floor(total / 6));
    for (var xi = 0; xi < total; xi += xLabelStep) {
      ctx.fillText(xi.toString(), sx(xi), margin.top + plotH + 6);
    }
    // Always show last
    if ((total - 1) % xLabelStep !== 0) {
      ctx.fillText((total - 1).toString(), sx(total - 1), margin.top + plotH + 6);
    }

    // Determine how many points to draw
    var drawCount = upToWindow >= 0 ? upToWindow + 1 : 0;
    if (drawCount === 0) return;

    // --- Draw baseline line (dashed) ---
    drawLine(ctx, windows, 'seq_baseline', key, drawCount, sx, sy, COLORS.baseline, true, COLORS.baselineFill, margin, plotH);

    // --- Draw joint line (solid) ---
    drawLine(ctx, windows, 'joint_opt', key, drawCount, sx, sy, COLORS.joint, false, COLORS.jointFill, margin, plotH);

    // Current point glow (JointOpt)
    if (upToWindow >= 0 && upToWindow < total) {
      var cx = sx(upToWindow);
      var cy = sy(windows[upToWindow].joint_opt[key]);

      // Glow
      ctx.beginPath();
      ctx.arc(cx, cy, 8, 0, Math.PI * 2);
      ctx.fillStyle = COLORS.currentGlow;
      ctx.fill();

      // Dot
      ctx.beginPath();
      ctx.arc(cx, cy, 4, 0, Math.PI * 2);
      ctx.fillStyle = COLORS.currentDot;
      ctx.fill();
      ctx.strokeStyle = '#0a0e17';
      ctx.lineWidth = 2;
      ctx.stroke();
    }
  }


  /**
   * Draw a single data line with optional fill and dashing.
   */
  function drawLine(ctx, windows, systemKey, metricKey, count, sx, sy, color, dashed, fillColor, margin, plotH) {
    if (count < 1) return;

    ctx.save();

    // Line
    ctx.strokeStyle = color;
    ctx.lineWidth = 2;
    ctx.lineJoin = 'round';
    ctx.lineCap = 'round';

    if (dashed) {
      ctx.setLineDash([6, 4]);
    } else {
      ctx.setLineDash([]);
    }

    ctx.beginPath();
    for (var i = 0; i < count; i++) {
      var x = sx(i);
      var y = sy(windows[i][systemKey][metricKey]);
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
    }
    ctx.stroke();

    // Fill under line
    if (!dashed && fillColor) {
      ctx.setLineDash([]);
      ctx.globalAlpha = 0.5;
      ctx.lineTo(sx(count - 1), margin.top + plotH);
      ctx.lineTo(sx(0), margin.top + plotH);
      ctx.closePath();
      ctx.fillStyle = fillColor;
      ctx.fill();
      ctx.globalAlpha = 1;
    }

    // Data points
    ctx.setLineDash([]);
    for (var j = 0; j < count; j++) {
      var px = sx(j);
      var py = sy(windows[j][systemKey][metricKey]);
      ctx.beginPath();
      ctx.arc(px, py, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = color;
      ctx.fill();
    }

    ctx.restore();
  }


  /**
   * Update charts to reflect a new current window.
   */
  function addDataPoint(windowIndex) {
    currentWindowIndex = windowIndex;

    Object.keys(charts).forEach(function (key) {
      drawChart(key, windowIndex);
    });
  }


  /**
   * Redraw all charts at current state (for resize).
   */
  function resize() {
    if (!traceData) return;

    CHART_DEFS.forEach(function (def) {
      var canvas = document.getElementById(def.id);
      if (!canvas) return;

      var dpr = window.devicePixelRatio || 1;
      var wrap = canvas.parentElement;
      var w = wrap.clientWidth;
      var h = wrap.clientHeight;

      canvas.width = w * dpr;
      canvas.height = h * dpr;
      var ctx = canvas.getContext('2d');
      ctx.scale(dpr, dpr);
      canvas.style.width = w + 'px';
      canvas.style.height = h + 'px';

      if (charts[def.key]) {
        charts[def.key].ctx = ctx;
        charts[def.key].width = w;
        charts[def.key].height = h;
      }
    });

    Object.keys(charts).forEach(function (key) {
      drawChart(key, currentWindowIndex);
    });
  }


  // Export
  window.OoberApp.charts = {
    init: init,
    addDataPoint: addDataPoint,
    resize: resize
  };

})();
