/**
 * keystroke.js — Keystroke Dynamics Logger with 40s Baseline
 * AIOEPS - AI Based Online Examination Proctoring System
 */

const Keylogger = (() => {
  let _sessionId    = null;
  let _keyDownTime  = {};
  let _dwellTimes   = [];
  let _flightTimes  = [];
  let _lastKeyUp    = null;
  let _sendTimer    = null;
  let _startTime    = null;

  function start(sessionId) {
    _sessionId = sessionId;
    _startTime = performance.now();

    // Initialize session baseline on server
    if (typeof API !== 'undefined') {
      API.post('/proctor/keystroke/init', { session_id: sessionId }).catch(() => {});
    }

    document.addEventListener('keydown', _onKeyDown);
    document.addEventListener('keyup',   _onKeyUp);
    // Send batch every 15 seconds (more frequent for 40s baseline window)
    _sendTimer = setInterval(_sendBatch, 15000);
  }

  function stop() {
    document.removeEventListener('keydown', _onKeyDown);
    document.removeEventListener('keyup',   _onKeyUp);
    clearInterval(_sendTimer);
    _sendBatch();
  }

  function _onKeyDown(e) {
    const now = performance.now();
    _keyDownTime[e.code] = now;
    if (_lastKeyUp !== null) {
      _flightTimes.push(Math.round(now - _lastKeyUp));
    }
  }

  function _onKeyUp(e) {
    const now = performance.now();
    _lastKeyUp = now;
    if (_keyDownTime[e.code]) {
      _dwellTimes.push(Math.round(now - _keyDownTime[e.code]));
      delete _keyDownTime[e.code];
    }
  }

  function _sendBatch() {
    if (!_sessionId || _dwellTimes.length < 5) return;
    const elapsed = _startTime ? (performance.now() - _startTime) / 1000 : 0;
    const batch = {
      dwell_times:     [..._dwellTimes],
      flight_times:    [..._flightTimes],
      elapsed_seconds: Math.round(elapsed),
    };
    if (typeof API !== 'undefined') {
      API.post('/proctor/keystroke', {
        session_id: _sessionId,
        key_data:   batch,
      }).then(res => {
        // Show mismatch warning on the exam page if detected
        const analysis = res && res.analysis;
        if (analysis && analysis.mismatch_warning) {
          _showMismatchWarning(analysis.mismatch_warning);
        }
      }).catch(() => {});
    }
    _dwellTimes  = [];
    _flightTimes = [];
  }

  function _showMismatchWarning(message) {
    // Show an on-screen warning if the exam page has a warning container
    const container = document.getElementById('keystroke-warning') ||
                      document.getElementById('proctor-warnings');
    if (container) {
      const el = document.createElement('div');
      el.style.cssText = 'background:rgba(239,68,68,0.12);border:1px solid #ef4444;border-radius:6px;' +
                         'padding:0.6rem 1rem;margin-top:0.5rem;font-size:0.83rem;color:#ef4444';
      el.textContent = '⚠️ ' + message;
      container.appendChild(el);
      setTimeout(() => el.remove(), 10000);
    }
    console.warn('[AIOEPS Keystroke]', message);
  }

  return { start, stop };
})();
