/* ============================================================
   Oober — Log Panel Module
   Collapsible assignment details with expandable window rows
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  var traceData = null;
  var logContent = null;
  var isExpanded = false;


  /**
   * Initialize log panel with trace data.
   */
  function init(data) {
    traceData = data;
    logContent = document.getElementById('log-content');

    if (logContent) {
      logContent.innerHTML = '';
    }

    bindToggle();
  }


  /**
   * Bind the log toggle button.
   */
  function bindToggle() {
    var toggle = document.getElementById('log-toggle');
    if (!toggle) return;

    toggle.onclick = function () {
      isExpanded = !isExpanded;
      toggle.classList.toggle('expanded', isExpanded);
      toggle.setAttribute('aria-expanded', isExpanded);

      var content = document.getElementById('log-content');
      if (content) {
        content.classList.toggle('expanded', isExpanded);
      }
    };
  }


  /**
   * Add or update a window log entry.
   */
  function addWindowLog(windowIndex) {
    if (!traceData || !logContent) return;
    var win = traceData.windows[windowIndex];
    if (!win) return;

    // Check if row already exists
    var existingRow = logContent.querySelector('[data-window="' + windowIndex + '"]');
    if (existingRow) {
      // Update highlight for current window
      highlightCurrentRow(windowIndex);
      return;
    }

    var row = document.createElement('div');
    row.className = 'log-window-row';
    row.setAttribute('data-window', windowIndex);

    var jointAssignments = win.joint_opt.assignments;
    var baseAssignments = win.seq_baseline.assignments;

    // Header
    var header = document.createElement('div');
    header.className = 'log-window-header';
    header.innerHTML =
      '<span class="window-label">Window ' + windowIndex + '</span>' +
      '<span class="window-summary">JointOpt: ' + jointAssignments.length +
      ' matches · Baseline: ' + baseAssignments.length + ' matches</span>';

    header.onclick = function () {
      var detail = row.querySelector('.log-window-detail');
      if (detail) {
        detail.classList.toggle('expanded');
      }
    };

    // Detail
    var detail = document.createElement('div');
    detail.className = 'log-window-detail';

    // Build table
    var table = buildAssignmentTable(win, jointAssignments, baseAssignments);
    detail.appendChild(table);

    row.appendChild(header);
    row.appendChild(detail);

    // Insert row in sorted order based on data-window attribute
    var inserted = false;
    for (var i = 0; i < logContent.children.length; i++) {
      var child = logContent.children[i];
      if (parseInt(child.getAttribute('data-window'), 10) > windowIndex) {
        logContent.insertBefore(row, child);
        inserted = true;
        break;
      }
    }
    if (!inserted) {
      logContent.appendChild(row);
    }

    highlightCurrentRow(windowIndex);

    // Auto-scroll to bottom
    logContent.scrollTop = logContent.scrollHeight;
  }


  /**
   * Build the assignment comparison table.
   */
  function buildAssignmentTable(win, jointAssigns, baseAssigns) {
    var riders = win.riders;
    var drivers = win.drivers;

    var riderMap = {};
    riders.forEach(function (r) { riderMap[r.id] = r; });
    var driverMap = {};
    drivers.forEach(function (d) { driverMap[d.id] = d; });

    var table = document.createElement('table');
    table.className = 'assignment-table';

    // Header
    var thead = document.createElement('thead');
    thead.innerHTML =
      '<tr>' +
      '<th>System</th>' +
      '<th>Rider</th>' +
      '<th>Driver</th>' +
      '<th>Price</th>' +
      '<th>Route</th>' +
      '</tr>';
    table.appendChild(thead);

    var tbody = document.createElement('tbody');

    // JointOpt assignments
    jointAssigns.forEach(function (a) {
      var rider = riderMap[a[0]];
      var driver = driverMap[a[1]];
      var tr = document.createElement('tr');
      tr.className = 'joint-row';
      tr.innerHTML =
        '<td><span class="system-tag joint">Joint</span></td>' +
        '<td>R' + a[0] + '</td>' +
        '<td>D' + a[1] + '</td>' +
        '<td>$' + a[2].toFixed(2) + '</td>' +
        '<td>' + (rider ? rider.origin_zone : '?') + ' → ' + (rider ? rider.dest_zone : '?') + '</td>';
      tbody.appendChild(tr);
    });

    // Separator
    if (jointAssigns.length > 0 && baseAssigns.length > 0) {
      var sepRow = document.createElement('tr');
      sepRow.innerHTML = '<td colspan="5" style="padding:4px;border-bottom:1px solid rgba(148,163,184,0.1)"></td>';
      tbody.appendChild(sepRow);
    }

    // Baseline assignments
    baseAssigns.forEach(function (a) {
      var rider = riderMap[a[0]];
      var tr = document.createElement('tr');
      tr.className = 'baseline-row';
      tr.innerHTML =
        '<td><span class="system-tag baseline">Base</span></td>' +
        '<td>R' + a[0] + '</td>' +
        '<td>D' + a[1] + '</td>' +
        '<td>$' + a[2].toFixed(2) + '</td>' +
        '<td>' + (rider ? rider.origin_zone : '?') + ' → ' + (rider ? rider.dest_zone : '?') + '</td>';
      tbody.appendChild(tr);
    });

    if (jointAssigns.length === 0 && baseAssigns.length === 0) {
      var emptyRow = document.createElement('tr');
      emptyRow.innerHTML = '<td colspan="5" style="text-align:center;color:#64748b;padding:12px;">No assignments</td>';
      tbody.appendChild(emptyRow);
    }

    table.appendChild(tbody);
    return table;
  }


  /**
   * Highlight the current window row.
   */
  function highlightCurrentRow(windowIndex) {
    if (!logContent) return;

    // Remove previous highlights
    var allHeaders = logContent.querySelectorAll('.log-window-header');
    allHeaders.forEach(function (h) {
      h.style.background = '';
    });

    // Highlight current
    var currentRow = logContent.querySelector('[data-window="' + windowIndex + '"] .log-window-header');
    if (currentRow) {
      currentRow.style.background = 'rgba(59, 130, 246, 0.06)';
    }
  }


  // Export
  window.OoberApp.log = {
    init: init,
    addWindowLog: addWindowLog
  };

})();
