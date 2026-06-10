/* ============================================================
   Oober — Simulation Coordinator Module
   Manages simulation state, transitions, playback handlers, and CSV export
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  var currentTraceData = null;
  var animTimeout = null;

  var configView = document.getElementById('config-view');
  var simulationView = document.getElementById('simulation-view');

  function showSimulationView() {
    if (configView) configView.style.display = 'none';
    if (simulationView) simulationView.classList.add('active');
  }

  function showConfigView() {
    if (configView) configView.style.display = 'flex';
    if (simulationView) simulationView.classList.remove('active');
  }

  function resetSummary() {
    var banner = document.getElementById('summary-banner');
    var aggSection = document.getElementById('aggregate-section');
    if (banner) banner.style.display = 'none';
    if (aggSection) aggSection.style.display = 'none';
  }

  function formatImprovement(val) {
    if (val === undefined || val === null || isNaN(val)) return '—';
    var sign = val >= 0 ? '+' : '';
    return sign + val.toFixed(1) + '%';
  }

  function updateAggCard(valueElId, val, jointElId, jointVal, baseElId, baseVal, isRate, isPrice) {
    var valueEl = document.getElementById(valueElId);
    var jointEl = document.getElementById(jointElId);
    var baseEl = document.getElementById(baseElId);

    if (valueEl) {
      valueEl.textContent = formatImprovement(val);
      if (val >= 0) {
        valueEl.classList.add('positive');
        valueEl.classList.remove('negative');
      } else {
        valueEl.classList.add('negative');
        valueEl.classList.remove('positive');
      }
    }

    if (jointEl && jointVal !== undefined && jointVal !== null) {
      if (isRate) {
        jointEl.textContent = (jointVal * 100).toFixed(1) + '%';
      } else if (isPrice) {
        jointEl.textContent = jointVal.toFixed(3);
      } else {
        jointEl.textContent = jointVal.toFixed(1);
      }
    }

    if (baseEl && baseVal !== undefined && baseVal !== null) {
      if (isRate) {
        baseEl.textContent = (baseVal * 100).toFixed(1) + '%';
      } else if (isPrice) {
        baseEl.textContent = baseVal.toFixed(3);
      } else {
        baseEl.textContent = baseVal.toFixed(1);
      }
    }
  }

  function convertWindowsToCSV(windows) {
    var headers = [
      'Window ID',
      'Rider Count',
      'Driver Count',
      'JointOpt Matches',
      'Baseline Matches',
      'JointOpt Wait Time',
      'Baseline Wait Time',
      'JointOpt Earnings Var',
      'Baseline Earnings Var',
      'JointOpt Price Dev',
      'Baseline Price Dev',
      'JointOpt Match Rate',
      'Baseline Match Rate',
      'JointOpt Solve Time',
      'Baseline Solve Time'
    ];

    var rows = [headers.join(',')];

    windows.forEach(function (w) {
      var rCount = w.riders ? w.riders.length : 0;
      var dCount = w.drivers ? w.drivers.length : 0;
      var jMatches = w.joint_opt.assignments ? w.joint_opt.assignments.length : 0;
      var bMatches = w.seq_baseline.assignments ? w.seq_baseline.assignments.length : 0;

      var row = [
        w.window_id,
        rCount,
        dCount,
        jMatches,
        bMatches,
        w.joint_opt.wait_time,
        w.seq_baseline.wait_time,
        w.joint_opt.earnings_variance,
        w.seq_baseline.earnings_variance,
        w.joint_opt.price_deviation,
        w.seq_baseline.price_deviation,
        w.joint_opt.matching_rate,
        w.seq_baseline.matching_rate,
        w.joint_opt.solve_time,
        w.seq_baseline.solve_time
      ];
      rows.push(row.map(function(val) {
        return val === undefined || val === null ? '' : val;
      }).join(','));
    });

    return rows.join('\n');
  }

  function downloadCSV(csvContent, filename) {
    var blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', filename);
    link.style.visibility = 'hidden';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Bind Back Button
  var backBtn = document.getElementById('back-btn');
  if (backBtn) {
    backBtn.onclick = function () {
      if (animTimeout) {
        clearTimeout(animTimeout);
        animTimeout = null;
      }
      window.OoberApp.playback.pause();
      window.OoberApp.playback.stopAnimations();
      
      if (window.OoberApp.cityGraph && typeof window.OoberApp.cityGraph.clearAgents === 'function') {
        window.OoberApp.cityGraph.clearAgents();
      }
      
      showConfigView();
    };
  }

  // Bind CSV Download Button
  var downloadBtn = document.getElementById('download-csv-btn');
  if (downloadBtn) {
    downloadBtn.onclick = function () {
      if (!currentTraceData) return;
      var csv = convertWindowsToCSV(currentTraceData.windows);
      downloadCSV(csv, 'oober_simulation_results.csv');
    };
  }

  // Bind Playback Events
  window.OoberApp.playback.on('onWindowChange', function (eventData) {
    window.OoberApp.playback.stopAnimations();
    var windowIndex = eventData.windowIndex;
    var timings = eventData.timings;
    var playbackCallback = eventData.callback;

    if (animTimeout) {
      clearTimeout(animTimeout);
      animTimeout = null;
    }

    // 1. Update Charts
    if (window.OoberApp.charts && typeof window.OoberApp.charts.addDataPoint === 'function') {
      window.OoberApp.charts.addDataPoint(windowIndex);
    }

    // 2. Update Metrics Cards
    if (window.OoberApp.metrics && typeof window.OoberApp.metrics.updateMetrics === 'function') {
      window.OoberApp.metrics.updateMetrics(windowIndex);
    }

    // 3. Update Assignment Logs
    if (window.OoberApp.log && typeof window.OoberApp.log.addWindowLog === 'function') {
      window.OoberApp.log.addWindowLog(windowIndex);
    }

    // 4. Update City Graphs
    if (window.OoberApp.cityGraph && typeof window.OoberApp.cityGraph.updateGraph === 'function' && currentTraceData) {
      var win = currentTraceData.windows[windowIndex];
      var jointTimeline = window.OoberApp.cityGraph.updateGraph('joint', win, 'joint_opt', timings);
      var baselineTimeline = window.OoberApp.cityGraph.updateGraph('baseline', win, 'seq_baseline', timings);

      if (jointTimeline) {
        window.OoberApp.playback.trackTimeline(jointTimeline);
        jointTimeline.play();
      }
      if (baselineTimeline) {
        window.OoberApp.playback.trackTimeline(baselineTimeline);
        baselineTimeline.play();
      }
    }

    // 5. Track completion
    animTimeout = setTimeout(function () {
      if (playbackCallback) {
        playbackCallback();
      }
    }, timings.spawn + timings.match);
  });

  window.OoberApp.playback.on('onComplete', function () {
    if (!currentTraceData || !currentTraceData.summary) return;

    var summary = currentTraceData.summary;

    // Display banner
    var banner = document.getElementById('summary-banner');
    if (banner) {
      banner.style.display = 'flex';
    }

    var summarySubtitle = document.getElementById('summary-subtitle');
    if (summarySubtitle) {
      var waitPct = summary.wait_time_improvement_pct;
      var varPct = summary.earnings_variance_improvement_pct;
      summarySubtitle.textContent = 'JointOpt achieved a ' + waitPct.toFixed(1) + '% wait time reduction and a ' + varPct.toFixed(1) + '% improvement in driver earnings fairness across ' + currentTraceData.windows.length + ' windows.';
    }

    // Display aggregates section
    var aggSection = document.getElementById('aggregate-section');
    if (aggSection) {
      aggSection.style.display = 'grid';
    }

    // Update aggregate cards
    updateAggCard('agg-wait', summary.wait_time_improvement_pct, 'agg-wait-joint', summary.joint_opt_avg_wait, 'agg-wait-base', summary.seq_baseline_avg_wait);
    updateAggCard('agg-variance', summary.earnings_variance_improvement_pct, 'agg-var-joint', summary.joint_opt_avg_earnings_variance, 'agg-var-base', summary.seq_baseline_avg_earnings_variance);
    updateAggCard('agg-price', summary.price_deviation_improvement_pct, 'agg-price-joint', summary.joint_opt_avg_price_deviation, 'agg-price-base', summary.seq_baseline_avg_price_deviation, false, true);
    updateAggCard('agg-match', summary.matching_rate_improvement_pct, 'agg-match-joint', summary.joint_opt_avg_matching_rate, 'agg-match-base', summary.seq_baseline_avg_matching_rate, true);
  });

  /**
   * Run simulation wrapper. Called by config module when run clicked.
   */
  function run(params, callback) {
    resetSummary();

    window.OoberApp.api.runSimulation(params)
      .then(function (data) {
        currentTraceData = data;
        
        showSimulationView();

        // Initialize display submodules
        if (window.OoberApp.cityGraph && typeof window.OoberApp.cityGraph.init === 'function') {
          window.OoberApp.cityGraph.init(data.city_graph);
        }
        if (window.OoberApp.charts && typeof window.OoberApp.charts.init === 'function') {
          window.OoberApp.charts.init(data);
        }
        if (window.OoberApp.metrics && typeof window.OoberApp.metrics.init === 'function') {
          window.OoberApp.metrics.init(data);
        }
        if (window.OoberApp.log && typeof window.OoberApp.log.init === 'function') {
          window.OoberApp.log.init(data);
        }

        // Initialize playback controls
        if (window.OoberApp.playback && typeof window.OoberApp.playback.init === 'function') {
          window.OoberApp.playback.init(data.windows.length);
          window.OoberApp.playback.play(); // Auto-start play
        }

        if (callback) callback(null, data);
      })
      .catch(function (err) {
        if (callback) callback(err);
      });
  }

  // Export
  window.OoberApp.simulation = {
    run: run
  };

})();
