/* ============================================================
   Oober — Config View Module
   Manages dashboard configuration controls, validation, and run request
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  function init() {
    var paramWindows = document.getElementById('param-windows');
    var valWindows = document.getElementById('val-windows');
    var paramDelta = document.getElementById('param-delta');
    var valDelta = document.getElementById('val-delta');
    var paramFairness = document.getElementById('param-fairness');
    var valFairness = document.getElementById('val-fairness');
    var paramZones = document.getElementById('param-zones');
    var valZones = document.getElementById('val-zones');
    var paramSeed = document.getElementById('param-seed');
    var runBtn = document.getElementById('run-btn');
    var configError = document.getElementById('config-error');

    function updateSliderFill(slider) {
      if (!slider) return;
      var min = parseFloat(slider.min) || 0;
      var max = parseFloat(slider.max) || 100;
      var val = parseFloat(slider.value) || 0;
      var pct = ((val - min) / (max - min)) * 100;
      slider.style.setProperty('--fill-percent', pct + '%');
    }

    function syncSlider(slider, display) {
      if (!slider) return;
      
      // Initial state
      if (display) {
        display.textContent = slider.value;
      }
      updateSliderFill(slider);

      slider.oninput = function () {
        if (display) {
          display.textContent = slider.value;
        }
        updateSliderFill(slider);
      };
    }

    syncSlider(paramWindows, valWindows);
    syncSlider(paramDelta, valDelta);
    syncSlider(paramFairness, valFairness);
    syncSlider(paramZones, valZones);

    function showError(msg) {
      if (configError) {
        configError.textContent = msg;
        configError.classList.add('visible');
      }
    }

    function clearError() {
      if (configError) {
        configError.textContent = '';
        configError.classList.remove('visible');
      }
    }

    if (runBtn) {
      runBtn.onclick = function () {
        clearError();

        var num_windows = parseInt(paramWindows.value, 10);
        var delta = parseFloat(paramDelta.value);
        var fairness_tolerance = parseFloat(paramFairness.value);
        var num_zones = parseInt(paramZones.value, 10);
        
        // Seed default fallback to 42 if empty or invalid
        var seedVal = paramSeed.value.trim();
        var seed = seedVal === '' ? 42 : parseInt(seedVal, 10);

        // Validation
        if (isNaN(num_windows) || num_windows < 5 || num_windows > 20) {
          showError('Time Windows must be an integer between 5 and 20.');
          return;
        }
        if (isNaN(delta) || delta < 0.05 || delta > 0.30) {
          showError('Price Stability δ must be a number between 0.05 and 0.30.');
          return;
        }
        if (isNaN(fairness_tolerance) || fairness_tolerance < 0.10 || fairness_tolerance > 0.50) {
          showError('Fairness Tolerance must be a number between 0.10 and 0.50.');
          return;
        }
        if (isNaN(num_zones) || num_zones < 5 || num_zones > 15) {
          showError('City Zones must be an integer between 5 and 15.');
          return;
        }
        if (isNaN(seed) || seed < 0) {
          showError('Random Seed must be a non-negative integer.');
          return;
        }

        var params = {
          num_windows: num_windows,
          delta: delta,
          fairness_tolerance: fairness_tolerance,
          num_zones: num_zones,
          seed: seed
        };

        // UI Loading State
        runBtn.classList.add('loading');
        runBtn.disabled = true;

        window.OoberApp.simulation.run(params, function (err) {
          // Reset UI State
          runBtn.classList.remove('loading');
          runBtn.disabled = false;

          if (err) {
            showError(err.message || 'An error occurred while running the simulation.');
          }
        });
      };
    }
  }

  // Export
  window.OoberApp.config = {
    init: init
  };

})();
