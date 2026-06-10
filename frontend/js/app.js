/* ============================================================
   Oober — Main Entry Point
   Initializes config on DOMContentLoaded and coordinates window resize
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  // Initialize modules when DOM is fully loaded
  document.addEventListener('DOMContentLoaded', function () {
    if (window.OoberApp.config && typeof window.OoberApp.config.init === 'function') {
      window.OoberApp.config.init();
    }
  });

  // Debounced window resize handler for D3 graph and charts
  var resizeTimeout = null;
  window.addEventListener('resize', function () {
    if (resizeTimeout) {
      clearTimeout(resizeTimeout);
    }
    resizeTimeout = setTimeout(function () {
      if (window.OoberApp.cityGraph && typeof window.OoberApp.cityGraph.resize === 'function') {
        window.OoberApp.cityGraph.resize();
      }
      if (window.OoberApp.charts && typeof window.OoberApp.charts.resize === 'function') {
        window.OoberApp.charts.resize();
      }
    }, 150);
  });

})();
