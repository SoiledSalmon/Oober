/* ============================================================
   Oober — API Module
   Handles communication with the backend /api/simulate endpoint
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  var API_BASE = '';  // Same origin — adjust if serving from different host
  var TIMEOUT_MS = 120000; // 2 minute timeout for ILP solver

  /**
   * Run simulation with given parameters.
   * POST /api/simulate
   *
   * @param {Object} params
   * @param {number} params.num_windows
   * @param {number} params.delta
   * @param {number} params.fairness_tolerance
   * @param {number} params.num_zones
   * @param {number} params.seed
   * @returns {Promise<Object>} Parsed JSON response with trace data
   */
  async function runSimulation(params) {
    var controller = new AbortController();
    var timeoutId = setTimeout(function () {
      controller.abort();
    }, TIMEOUT_MS);

    try {
      var response = await fetch(API_BASE + '/api/simulate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({
          num_windows: params.num_windows,
          delta: params.delta,
          fairness_tolerance: params.fairness_tolerance,
          num_zones: params.num_zones,
          seed: params.seed
        }),
        signal: controller.signal
      });

      clearTimeout(timeoutId);

      if (!response.ok) {
        var errorBody = '';
        try {
          errorBody = await response.text();
        } catch (_) {}
        throw new Error(
          'Server error (' + response.status + '): ' +
          (errorBody || response.statusText)
        );
      }

      var data = await response.json();

      // Normalize backend keys: graph -> city_graph
      if (data && data.graph && !data.city_graph) {
        data.city_graph = data.graph;
      }

      // Normalize flat per-window metrics and assignments into nested structures
      if (data && data.windows && Array.isArray(data.windows)) {
        data.windows.forEach(function (win) {
          win.joint_opt = {
            assignments: win.joint_opt_assignments,
            wait_time: win.joint_opt_wait_time,
            earnings_variance: win.joint_opt_earnings_variance,
            price_deviation: win.joint_opt_price_deviation,
            matching_rate: win.joint_opt_matching_rate,
            solve_time: win.joint_opt_solve_time
          };
          win.seq_baseline = {
            assignments: win.seq_baseline_assignments,
            wait_time: win.seq_baseline_wait_time,
            earnings_variance: win.seq_baseline_earnings_variance,
            price_deviation: win.seq_baseline_price_deviation,
            matching_rate: win.seq_baseline_matching_rate,
            solve_time: win.seq_baseline_solve_time
          };
        });
      }

      // Validate essential structure
      if (!data.windows || !Array.isArray(data.windows)) {
        throw new Error('Invalid response: missing windows array');
      }
      if (!data.city_graph || !data.city_graph.nodes) {
        throw new Error('Invalid response: missing city_graph');
      }

      return data;

    } catch (err) {
      clearTimeout(timeoutId);

      if (err.name === 'AbortError') {
        throw new Error('Request timed out after ' + (TIMEOUT_MS / 1000) + ' seconds');
      }

      throw err;
    }
  }
  // Export
  window.OoberApp.api = {
    runSimulation: runSimulation
  };

})();
