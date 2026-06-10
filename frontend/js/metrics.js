/* ============================================================
   Oober — Metrics Module
   Glass metric cards with count-up animation
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  // ── Metric Definitions ─────────────────────────────────────────
  var METRICS = [
    {
      joint: 'm-wait-joint',
      base: 'm-wait-base',
      key: 'wait_time',
      lowerBetter: true,
      format: function (v) { return v.toFixed(1); }
    },
    {
      joint: 'm-var-joint',
      base: 'm-var-base',
      key: 'earnings_variance',
      lowerBetter: true,
      format: function (v) { return v.toFixed(1); }
    },
    {
      joint: 'm-price-joint',
      base: 'm-price-base',
      key: 'price_deviation',
      lowerBetter: true,
      format: function (v) { return v.toFixed(3); }
    },
    {
      joint: 'm-match-joint',
      base: 'm-match-base',
      key: 'matching_rate',
      lowerBetter: false,
      format: function (v) { return (v * 100).toFixed(1) + '%'; }
    }
  ];

  var traceData = null;
  var currentValues = {};


  /**
   * Initialize metrics with trace data.
   */
  function init(data) {
    traceData = data;
    resetDisplay();
  }


  /**
   * Reset all metric displays to placeholder.
   */
  function resetDisplay() {
    METRICS.forEach(function (m) {
      setElement(m.joint, '—');
      setElement(m.base, '—');
      clearWinnerClass(m.joint);
      clearWinnerClass(m.base);
    });
    currentValues = {};
  }


  /**
   * Update metrics for a given window index.
   * Animates values with count-up effect.
   */
  function updateMetrics(windowIndex) {
    if (!traceData || !traceData.windows[windowIndex]) return;

    var win = traceData.windows[windowIndex];

    METRICS.forEach(function (m) {
      var jointVal = win.joint_opt[m.key];
      var baseVal = win.seq_baseline[m.key];

      // Determine winner
      var jointWins;
      if (m.lowerBetter) {
        jointWins = jointVal <= baseVal;
      } else {
        jointWins = jointVal >= baseVal;
      }

      // Animate joint value
      animateValue(m.joint, currentValues[m.joint] || 0, jointVal, m.format, 400);
      animateValue(m.base, currentValues[m.base] || 0, baseVal, m.format, 400);

      // Store current
      currentValues[m.joint] = jointVal;
      currentValues[m.base] = baseVal;

      // Apply winner/loser classes
      setTimeout(function () {
        clearWinnerClass(m.joint);
        clearWinnerClass(m.base);

        var jEl = document.getElementById(m.joint);
        var bEl = document.getElementById(m.base);

        if (jEl) jEl.classList.add(jointWins ? 'winner' : 'loser');
        if (bEl) bEl.classList.add(jointWins ? 'loser' : 'winner');
      }, 420);
    });
  }


  /**
   * Animate a numeric value change using anime.js.
   */
  function animateValue(elementId, fromVal, toVal, formatFn, duration) {
    var el = document.getElementById(elementId);
    if (!el) return;

    var obj = { val: fromVal };

    anime({
      targets: obj,
      val: toVal,
      duration: duration,
      easing: 'cubicBezier(0.4, 0, 0.2, 1)',
      round: false,
      update: function () {
        el.textContent = formatFn(obj.val);
      }
    });
  }


  /**
   * Set element text content.
   */
  function setElement(id, text) {
    var el = document.getElementById(id);
    if (el) el.textContent = text;
  }


  /**
   * Clear winner/loser classes.
   */
  function clearWinnerClass(id) {
    var el = document.getElementById(id);
    if (el) {
      el.classList.remove('winner', 'loser');
    }
  }


  // Export
  window.OoberApp.metrics = {
    init: init,
    updateMetrics: updateMetrics,
    resetDisplay: resetDisplay
  };

})();
