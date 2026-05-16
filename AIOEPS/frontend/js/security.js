/**
 * security.js — Exam Security: Tab Switch, Copy-Paste, Screenshot Prevention
 * AIOEPS - AI Based Online Examination Proctoring System
 */

const ExamSecurity = (() => {
  let _sessionId   = null;
  let _enabled     = false;
  let _tabSwitches = 0;
  let _onViolation = null;  // callback(type, count)

  /** Call this once when exam starts. */
  function enable(sessionId, onViolation) {
    _sessionId   = sessionId;
    _onViolation = onViolation || (() => {});
    _enabled     = true;
    _attachListeners();
    _enterFullscreen();
    console.log('🔒 Exam security enabled');
  }

  function disable() {
    _enabled = false;
    _removeListeners();
    console.log('🔓 Exam security disabled');
  }

  // ── Fullscreen (optional - don't crash if browser blocks) ────
  function _enterFullscreen() {
    try {
      const el = document.documentElement;
      const req = el.requestFullscreen || el.webkitRequestFullscreen || el.mozRequestFullScreen;
      if (req) req.call(el).catch(() => {}); // silently ignore permission denied
    } catch (e) { /* browser blocked fullscreen - ignore */ }
  }

  // ── Visibility (tab switch) ────────────────────────────────────────────────
  function _onVisibilityChange() {
    if (!_enabled) return;
    if (document.hidden) {
      _tabSwitches++;
      _report('Tab Switch', _tabSwitches);
      _warn(`⚠️ Tab switch detected (${_tabSwitches}). Return immediately!`);
    }
  }

  // ── Context menu (right-click) ─────────────────────────────────────────────
  function _onContextMenu(e) {
    if (!_enabled) return;
    e.preventDefault();
    _warn('Right-click is disabled during exam');
  }

  // ── Copy / Cut / Paste ─────────────────────────────────────────────────────
  function _onCopy(e) { if (!_enabled) return; e.preventDefault(); _report('Copy Attempt'); }
  function _onCut(e)  { if (!_enabled) return; e.preventDefault(); _report('Cut Attempt'); }
  function _onPaste(e){ if (!_enabled) return; e.preventDefault(); _report('Paste Attempt'); }

  // ── Keyboard shortcuts ─────────────────────────────────────────────────────
  function _onKeyDown(e) {
    if (!_enabled) return;
    const ctrl = e.ctrlKey || e.metaKey;

    // Block: Ctrl+C/V/X/A/U/S/P, F12, PrintScreen
    if (ctrl && ['c','v','x','a','u','s','p'].includes(e.key.toLowerCase())) {
      e.preventDefault();
      if (e.key.toLowerCase() !== 'a') _report('Keyboard Shortcut: Ctrl+' + e.key.toUpperCase());
      return;
    }
    if (['F12','F5'].includes(e.key)) { e.preventDefault(); return; }
    if (e.key === 'PrintScreen')      { e.preventDefault(); _report('Screenshot Attempt'); }

    // Alt+Tab / Alt+F4
    if (e.altKey && (e.key === 'Tab' || e.key === 'F4')) {
      e.preventDefault(); _report('Alt+Tab Attempt');
    }
  }

  // ── Fullscreen exit ────────────────────────────────────────────────────────
  function _onFullscreenChange() {
    if (!_enabled) return;
    if (!document.fullscreenElement) {
      _report('Fullscreen Exit', null, 'Low');
      // Try re-entering after delay, but don't warn aggressively
      setTimeout(() => { try { _enterFullscreen(); } catch(e){} }, 3000);
    }
  }

  // ── Dev tools (size heuristic) ─────────────────────────────────────────────
  let _devToolsTimer = null;
  function _startDevToolsDetection() {
    _devToolsTimer = setInterval(() => {
      if (!_enabled) return;
      const threshold = 160;
      if (window.outerWidth - window.innerWidth > threshold ||
          window.outerHeight - window.innerHeight > threshold) {
        _report('DevTools Opened', null, 'Low');
      }
    }, 3000);
  }

  // ── Report violation ──────────────────────────────────────────────────────
  function _report(type, count = null, severity = 'Medium') {
    if (_onViolation) _onViolation(type, count ?? _tabSwitches, severity);
    if (_sessionId && typeof API !== 'undefined') {
      API.logAlert(_sessionId, type, severity).catch(() => {});
    }
    console.warn(`[SECURITY] ${type}`);
  }

  function _warn(msg) {
    if (typeof showToast === 'function') showToast(msg, 'warning', 5000);
    else alert(msg);
  }

  // ── Attach / Remove Listeners ─────────────────────────────────────────────
  function _attachListeners() {
    document.addEventListener('visibilitychange',  _onVisibilityChange);
    document.addEventListener('contextmenu',       _onContextMenu);
    document.addEventListener('copy',              _onCopy);
    document.addEventListener('cut',               _onCut);
    document.addEventListener('paste',             _onPaste);
    document.addEventListener('keydown',           _onKeyDown);
    document.addEventListener('fullscreenchange',  _onFullscreenChange);
    _startDevToolsDetection();
  }

  function _removeListeners() {
    document.removeEventListener('visibilitychange', _onVisibilityChange);
    document.removeEventListener('contextmenu',      _onContextMenu);
    document.removeEventListener('copy',             _onCopy);
    document.removeEventListener('cut',              _onCut);
    document.removeEventListener('paste',            _onPaste);
    document.removeEventListener('keydown',          _onKeyDown);
    document.removeEventListener('fullscreenchange', _onFullscreenChange);
    if (_devToolsTimer) clearInterval(_devToolsTimer);
  }

  return { enable, disable, getTabSwitches: () => _tabSwitches };
})();
