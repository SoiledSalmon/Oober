/* ============================================================
   Oober — Playback Controller
   Manages window stepping, play/pause, speed, timeline
   ============================================================ */

(function () {
  'use strict';

  window.OoberApp = window.OoberApp || {};

  // ── State ──────────────────────────────────────────────────────
  var state = {
    currentWindow: -1,
    totalWindows: 0,
    isPlaying: false,
    speed: 1,
    animating: false
  };

  // Animation phase durations at 1x speed (ms)
  var BASE_TIMINGS = {
    spawn: 300,
    match: 500,
    hold: 400,
    transition: 200
  };

  // Active timelines
  var activeTimelines = [];
  var playTimeout = null;

  // Callbacks
  var listeners = {
    onWindowChange: [],
    onPlayStateChange: [],
    onComplete: []
  };


  /**
   * Register a callback.
   */
  function on(event, fn) {
    if (listeners[event]) {
      listeners[event].push(fn);
    }
  }

  function emit(event, data) {
    if (listeners[event]) {
      listeners[event].forEach(function (fn) { fn(data); });
    }
  }


  /**
   * Get scaled timings based on current speed.
   */
  function getTimings() {
    var s = state.speed;
    return {
      spawn: Math.round(BASE_TIMINGS.spawn / s),
      match: Math.round(BASE_TIMINGS.match / s),
      hold: Math.round(BASE_TIMINGS.hold / s),
      transition: Math.round(BASE_TIMINGS.transition / s),
      total: Math.round(
        (BASE_TIMINGS.spawn + BASE_TIMINGS.match + BASE_TIMINGS.hold + BASE_TIMINGS.transition) / s
      )
    };
  }


  /**
   * Initialize playback with total window count.
   */
  function init(totalWindows) {
    state.totalWindows = totalWindows;
    state.currentWindow = -1;
    state.isPlaying = false;
    state.animating = false;

    renderTimeline();
    updateUI();
    bindControls();
  }


  /**
   * Render timeline markers.
   */
  function renderTimeline() {
    var container = document.getElementById('timeline-markers');
    if (!container) return;
    container.innerHTML = '';

    for (var i = 0; i < state.totalWindows; i++) {
      var marker = document.createElement('div');
      marker.className = 'timeline-marker';
      marker.setAttribute('data-window', i);
      marker.title = 'Window ' + i;
      container.appendChild(marker);
    }
  }


  /**
   * Update all UI elements to reflect current state.
   */
  function updateUI() {
    // Window counter
    var currentEl = document.getElementById('window-current');
    var totalEl = document.getElementById('window-total');
    if (currentEl) currentEl.textContent = Math.max(0, state.currentWindow);
    if (totalEl) totalEl.textContent = state.totalWindows - 1;

    // Timeline fill
    var fill = document.getElementById('timeline-fill');
    if (fill) {
      var pct = state.totalWindows > 1
        ? ((state.currentWindow + 1) / state.totalWindows) * 100
        : 0;
      fill.style.width = pct + '%';
    }

    // Timeline markers
    var markers = document.querySelectorAll('.timeline-marker');
    markers.forEach(function (m) {
      var w = parseInt(m.getAttribute('data-window'));
      m.classList.remove('visited', 'current');
      if (w < state.currentWindow) m.classList.add('visited');
      if (w === state.currentWindow) m.classList.add('current');
    });

    // Play button icon
    var playBtn = document.getElementById('btn-play');
    if (playBtn) {
      playBtn.textContent = state.isPlaying ? '⏸' : '▶';
      playBtn.title = state.isPlaying ? 'Pause' : 'Play';
    }

    // Step buttons
    var stepBack = document.getElementById('btn-step-back');
    var stepFwd = document.getElementById('btn-step-fwd');
    if (stepBack) stepBack.disabled = state.currentWindow <= 0 || state.animating;
    if (stepFwd) stepFwd.disabled = state.currentWindow >= state.totalWindows - 1 || state.animating;
  }


  /**
   * Bind control button handlers.
   */
  function bindControls() {
    var playBtn = document.getElementById('btn-play');
    var stepBack = document.getElementById('btn-step-back');
    var stepFwd = document.getElementById('btn-step-fwd');
    var timelineBar = document.getElementById('timeline-bar');

    if (playBtn) {
      playBtn.onclick = function () {
        if (state.isPlaying) {
          pause();
        } else {
          play();
        }
      };
    }

    if (stepBack) {
      stepBack.onclick = function () {
        if (!state.animating) stepBackward();
      };
    }

    if (stepFwd) {
      stepFwd.onclick = function () {
        if (!state.animating) stepForward();
      };
    }

    // Timeline click
    if (timelineBar) {
      timelineBar.onclick = function (e) {
        if (state.animating) return;
        var rect = timelineBar.getBoundingClientRect();
        var pct = (e.clientX - rect.left) / rect.width;
        var targetWindow = Math.round(pct * (state.totalWindows - 1));
        targetWindow = Math.max(0, Math.min(targetWindow, state.totalWindows - 1));
        jumpToWindow(targetWindow);
      };
    }

    // Speed buttons
    var speedBtns = document.querySelectorAll('.speed-btn');
    speedBtns.forEach(function (btn) {
      btn.onclick = function () {
        setSpeed(parseFloat(btn.getAttribute('data-speed')));
        speedBtns.forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
      };
    });
  }


  /**
   * Play through all windows automatically.
   */
  function play() {
    state.isPlaying = true;
    emit('onPlayStateChange', { playing: true });
    updateUI();

    if (state.currentWindow >= state.totalWindows - 1) {
      // Restart from beginning
      state.currentWindow = -1;
    }

    advanceToNext();
  }


  /**
   * Advance to next window and schedule subsequent.
   */
  function advanceToNext() {
    if (!state.isPlaying) return;
    if (state.currentWindow >= state.totalWindows - 1) {
      pause();
      emit('onComplete', {});
      return;
    }

    stepForward(function () {
      if (state.isPlaying) {
        var timings = getTimings();
        playTimeout = setTimeout(function () {
          advanceToNext();
        }, timings.hold);
      }
    });
  }


  /**
   * Pause playback.
   */
  function pause() {
    state.isPlaying = false;
    clearTimeout(playTimeout);
    playTimeout = null;
    emit('onPlayStateChange', { playing: false });
    updateUI();
  }


  /**
   * Step forward one window.
   */
  function stepForward(callback) {
    if (state.currentWindow >= state.totalWindows - 1) return;
    if (state.animating) return;

    state.currentWindow++;
    state.animating = true;
    updateUI();

    emit('onWindowChange', {
      windowIndex: state.currentWindow,
      timings: getTimings(),
      callback: function () {
        state.animating = false;
        updateUI();
        if (callback) callback();
      }
    });
  }


  /**
   * Step backward one window (instant, no animation).
   */
  function stepBackward() {
    if (state.currentWindow <= 0) return;

    // Stop all active animations
    stopAnimations();

    state.currentWindow--;
    updateUI();

    emit('onWindowChange', {
      windowIndex: state.currentWindow,
      timings: getTimings(),
      callback: function () {
        state.animating = false;
        updateUI();
      }
    });
  }


  /**
   * Jump to a specific window.
   */
  function jumpToWindow(index) {
    if (index < 0 || index >= state.totalWindows) return;

    stopAnimations();
    var wasPlaying = state.isPlaying;
    if (wasPlaying) pause();

    state.currentWindow = index;
    state.animating = true;
    updateUI();

    emit('onWindowChange', {
      windowIndex: state.currentWindow,
      timings: getTimings(),
      callback: function () {
        state.animating = false;
        updateUI();
      }
    });
  }


  /**
   * Set playback speed.
   */
  function setSpeed(newSpeed) {
    state.speed = newSpeed;
  }


  /**
   * Register an anime.js timeline to be tracked.
   */
  function trackTimeline(tl) {
    activeTimelines.push(tl);
  }


  /**
   * Stop all tracked animations.
   */
  function stopAnimations() {
    activeTimelines.forEach(function (tl) {
      if (tl && tl.pause) tl.pause();
    });
    activeTimelines = [];
    clearTimeout(playTimeout);
  }


  /**
   * Get current state.
   */
  function getState() {
    return {
      currentWindow: state.currentWindow,
      totalWindows: state.totalWindows,
      isPlaying: state.isPlaying,
      speed: state.speed
    };
  }


  // Export
  window.OoberApp.playback = {
    init: init,
    on: on,
    play: play,
    pause: pause,
    stepForward: stepForward,
    stepBackward: stepBackward,
    jumpToWindow: jumpToWindow,
    setSpeed: setSpeed,
    trackTimeline: trackTimeline,
    stopAnimations: stopAnimations,
    getState: getState,
    getTimings: getTimings
  };

})();
