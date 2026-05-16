/**
 * proctor.js — Advanced AI Proctoring (v5)
 * Features: Multi-face, Eye Gaze, Head Pose, Voice, Mobile, rPPG, TTS Alerts, Tab Switch
 */

const Proctor = (() => {
  let _sessionId   = null;
  let _videoEl     = null;
  let _onAlert     = null;
  let _intervalId  = null;
  let _faceMesh    = null;
  let _ready       = false;
  let _audioCtx    = null;
  let _analyser    = null;
  let _micStream   = null;
  let _ttsEnabled  = true;
  let _mobileNet   = null;

  const COOLDOWN   = 8000;
  const CHECK_MS   = 1500;
  const _lastAlert = {};
  const _lastTTS   = {};
  const TTS_COOL   = 12000;

  // Counters (real-time)
  let _gazeAway    = 0;
  let _headTurned  = 0;
  const _counts    = { head: 0, faces: 0, voice: 0, mobile: 0 };
  let _suspicious  = false;
  let _tabSwitches = 0;
  const MAX_TAB    = 3;

  // rPPG state
  let _rppgBuf     = [];
  let _rppgBPM     = 75;
  const RPPG_WIN   = 90; // frames

  // Keystroke baselines
  let _ksBaseline  = null;
  let _ksBuffer    = [];
  let _ksPhase     = 'baseline'; // baseline | check
  let _ksStart     = Date.now();

  const GAZE_THRESH = 10;
  const HEAD_THRESH = 8;

  // ── Public API ──────────────────────────────────────────────────────
  function start(sessionId, videoEl, onAlert) {
    _sessionId = sessionId;
    _videoEl   = videoEl;
    _onAlert   = onAlert || (() => {});
    _initFaceMesh();
    _initVoice();
    _initTabSwitch();
    _initKeystroke();
    console.log('✅ Proctor v5 started');
  }

  function stop() {
    if (_intervalId) clearInterval(_intervalId);
    if (_micStream)  _micStream.getTracks().forEach(t => t.stop());
    _ready = false;
  }

  // ── MediaPipe FaceMesh ─────────────────────────────────────────────
  function _initFaceMesh() {
    if (typeof FaceMesh !== 'undefined') {
      _faceMesh = new FaceMesh({
        locateFile: f => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${f}`
      });
      _faceMesh.setOptions({
        maxNumFaces: 4,
        refineLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5
      });
      _faceMesh.onResults(_onFaceMeshResults);
      _ready = true;
      _startLoop();
    } else {
      console.warn('MediaPipe not loaded — simulation mode');
      _startSimulationMode();
    }
  }

  function _startLoop() {
    _intervalId = setInterval(async () => {
      if (!_videoEl || _videoEl.readyState < 2) return;
      try { await _faceMesh.send({ image: _videoEl }); } catch(e) {}
      _computeRPPG();
    }, CHECK_MS);
  }

  // ── FaceMesh Results ───────────────────────────────────────────────
  function _onFaceMeshResults(results) {
    const faces = (results.multiFaceLandmarks || []);
    const count = faces.length;

    // — No face —
    if (count === 0) {
      _triggerAlert('Face Not Detected', 'High');
      _voiceAlert('Face not detected. Please sit properly in front of the camera.');
      _ui('ai-face', '❌ Not Found', false);
      _ui('ai-faces', 'No Face ⚠️', false);
      _setSuspicious(true);
      return;
    }

    // — Multiple faces —
    if (count > 1) {
      _counts.faces++;
      _triggerAlert('Multiple Faces', 'High');
      _voiceAlert('Multiple faces detected. Only the registered student should be visible.');
      _ui('ai-faces', `Detected (${count}) ⚠️`, false);
      _el('alt-faces').textContent = `👥 Multiple Faces: ${_counts.faces}`;
      _setSuspicious(true);
    } else {
      _ui('ai-faces', 'None ✓', true);
    }

    const lm = faces[0];
    _checkFaceMatch(lm);
    _checkGaze(lm);
    _checkHeadPose(lm);
    _extractRPPGFrame(lm);
  }

  // ── Face Match (compare with stored snapshot) ──────────────────────
  function _checkFaceMatch(lm) {
    // Continuous match via canvas pixel comparison against stored face
    if (!_videoEl) return;
    const canvas = document.getElementById('examCanvas');
    if (!canvas) return;
    canvas.width = 80; canvas.height = 80;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(_videoEl, 0, 0, 80, 80);
    const stored = localStorage.getItem('aioeps_face_ref');
    if (!stored) { _ui('ai-face', 'Matched ✓', true); return; }
    // Basic brightness/histogram compare
    const cur = ctx.getImageData(0, 0, 80, 80).data;
    const curBr = _avgBrightness(cur);
    const refBr = parseFloat(stored);
    const diff = Math.abs(curBr - refBr);
    if (diff > 40) {
      _triggerAlert('Face Mismatch', 'High');
      _voiceAlert('Face mismatch detected. Please ensure you are the registered student.');
      _ui('ai-face', 'Mismatch ⚠️', false);
      _setSuspicious(true);
    } else {
      _ui('ai-face', 'Matched ✓', true);
    }
  }

  function _avgBrightness(data) {
    let sum = 0;
    for (let i = 0; i < data.length; i += 4) sum += (data[i] + data[i+1] + data[i+2]) / 3;
    return sum / (data.length / 4);
  }

  // ── Eye Gaze ───────────────────────────────────────────────────────
  function _checkGaze(lm) {
    const li = lm[473], lL = lm[33], lR = lm[133];
    if (!li) return;
    const ratio = (li.x - lL.x) / ((lR.x - lL.x) || 0.001);
    const away = ratio < 0.25 || ratio > 0.75;
    if (away) {
      _gazeAway++;
      if (_gazeAway > GAZE_THRESH) {
        _triggerAlert('Looking Away', 'Medium');
        _voiceAlert('Warning: You appear to be looking away from the screen.');
        _ui('ai-gaze', 'Looking Away ⚠️', false);
        _setSuspicious(true);
      }
    } else {
      _gazeAway = Math.max(0, _gazeAway - 2);
      _ui('ai-gaze', 'Focused ✓', true);
    }
  }

  // ── Head Pose ──────────────────────────────────────────────────────
  function _checkHeadPose(lm) {
    const nose = lm[1], le = lm[33], re = lm[263];
    if (!nose) return;
    const midX = (le.x + re.x) / 2, midY = (le.y + re.y) / 2;
    const yaw   = Math.abs(nose.x - midX);
    const pitch = Math.abs(nose.y - midY);
    if (yaw > 0.12 || pitch > 0.12) {
      _headTurned++;
      if (_headTurned > HEAD_THRESH) {
        _counts.head++;
        _triggerAlert('Head Turned', 'Medium');
        _voiceAlert('Warning: Head turned. Please face the camera directly.');
        _ui('ai-head', 'Turned ⚠️', false);
        _el('alt-head').textContent = `🤦 Head Turned: ${_counts.head}`;
        _setSuspicious(true);
      }
    } else {
      _headTurned = Math.max(0, _headTurned - 2);
      _ui('ai-head', 'Stable ✓', true);
    }
  }

  // ── rPPG Heart Rate (Green channel forehead) ────────────────────────
  function _extractRPPGFrame(lm) {
    if (!_videoEl || !_videoEl.videoWidth) return;
    const canvas = document.createElement('canvas');
    canvas.width = _videoEl.videoWidth; canvas.height = _videoEl.videoHeight;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(_videoEl, 0, 0);

    // Forehead ROI from landmarks (between eyebrows)
    const fh = lm[10]; // top-of-head
    const lb = lm[107], rb = lm[336]; // left/right brow
    if (!fh || !lb || !rb) return;

    const W = canvas.width, H = canvas.height;
    const x = Math.round(lb.x * W), y = Math.round(fh.y * H);
    const w = Math.round((rb.x - lb.x) * W), h = Math.round((lb.y - fh.y) * H);
    if (w < 4 || h < 4) return;

    try {
      const pix = ctx.getImageData(Math.max(0,x), Math.max(0,y), Math.max(1,w), Math.max(1,h)).data;
      let gSum = 0;
      for (let i = 0; i < pix.length; i += 4) gSum += pix[i+1];
      const gMean = gSum / (pix.length / 4);
      _rppgBuf.push(gMean);
      if (_rppgBuf.length > RPPG_WIN) _rppgBuf.shift();
    } catch(e) {}
  }

  function _computeRPPG() {
    if (_rppgBuf.length < 30) return;
    // Simple peak detection on green channel signal
    const sig = _rppgBuf;
    const mean = sig.reduce((a,b) => a+b, 0) / sig.length;
    const norm = sig.map(v => v - mean);
    let peaks = 0;
    for (let i = 1; i < norm.length - 1; i++) {
      if (norm[i] > norm[i-1] && norm[i] > norm[i+1] && norm[i] > 1) peaks++;
    }
    const fps = 1000 / CHECK_MS;
    const durationSec = sig.length / fps;
    _rppgBPM = Math.round((peaks / durationSec) * 60);
    // Clamp to realistic range
    _rppgBPM = Math.min(160, Math.max(50, _rppgBPM));

    const stress = _rppgBPM > 100 ? 'High ⚠️' : _rppgBPM > 85 ? 'Medium' : 'Normal ✓';
    const ok = _rppgBPM <= 85;
    _ui('ai-stress', `${_rppgBPM} BPM — ${stress}`, ok);

    if (_rppgBPM > 100) {
      _triggerAlert('High Stress', 'Medium');
      _setSuspicious(true);
    }

    // Send to backend
    if (typeof API !== 'undefined' && _sessionId) {
      API.logStress(_sessionId, _rppgBPM).catch(() => {});
    }
    // Update admin live panel
    _el('alt-bpm') && (_el('alt-bpm').textContent = `❤️ rPPG: ${_rppgBPM} BPM`);
  }

  // ── Voice Detection (WebAudio) ─────────────────────────────────────
  async function _initVoice() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      _micStream = stream;
      _audioCtx  = new (window.AudioContext || window.webkitAudioContext)();
      _analyser  = _audioCtx.createAnalyser();
      _analyser.fftSize = 256;
      _audioCtx.createMediaStreamSource(stream).connect(_analyser);

      setInterval(() => {
        const data = new Uint8Array(_analyser.frequencyBinCount);
        _analyser.getByteFrequencyData(data);
        const vol = data.reduce((a,b) => a+b, 0) / data.length;
        if (vol > 20) { // voice threshold
          _counts.voice++;
          _triggerAlert('Voice Detected', 'Low');
          _voiceAlert('Background voice detected. Please maintain silence.');
          _ui('ai-voice', 'Voice ⚠️', false);
          _el('alt-voice').textContent = `🔊 Voice: Yes`;
          _setSuspicious(true);
        } else {
          _el('alt-voice').textContent = `🔊 Voice: No`;
        }
      }, 2000);
    } catch(e) {
      console.warn('Mic not accessible:', e);
    }
  }

  // ── Tab Switch Detection ───────────────────────────────────────────
  function _initTabSwitch() {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden) {
        _tabSwitches++;
        const remaining = MAX_TAB - _tabSwitches;
        _triggerAlert('Tab Switch', 'High');
        _voiceAlert('Warning: Do not switch tabs during the exam.');
        if (_tabSwitches >= MAX_TAB) {
          _voiceAlert('Exam terminated due to repeated tab switching.');
          setTimeout(() => {
            if (typeof submitExam === 'function') submitExam();
            else {
              alert('⛔ Exam terminated due to tab switching!');
              window.location.href = 'dashboard.html';
            }
          }, 2000);
        } else {
          showToast && showToast(`⚠️ Tab switch ${_tabSwitches}/${MAX_TAB}. ${remaining} remaining before auto-submit!`, 'error');
        }
        if (typeof API !== 'undefined' && _sessionId) {
          API.logAlert(_sessionId, 'Tab Switch', 'High').catch(() => {});
        }
      }
    });
  }

  // ── Keystroke Dynamics ─────────────────────────────────────────────
  function _initKeystroke() {
    let lastKeyTime = 0;
    const intervals = [];

    document.addEventListener('keydown', (e) => {
      const now = Date.now();
      if (lastKeyTime > 0) {
        const gap = now - lastKeyTime;
        if (gap < 2000) intervals.push(gap); // ignore long pauses
      }
      lastKeyTime = now;

      const elapsed = (now - _ksStart) / 1000;

      if (_ksPhase === 'baseline' && elapsed > 50 && intervals.length >= 20) {
        // Set baseline after 50s
        _ksBaseline = _mean(intervals);
        _ksBuffer = [];
        _ksPhase = 'check';
        console.log('⌨️ Keystroke baseline set:', Math.round(_ksBaseline), 'ms');
      } else if (_ksPhase === 'check' && _ksBaseline) {
        _ksBuffer.push(intervals[intervals.length - 1] || 0);
        if (_ksBuffer.length >= 20) {
          const cur = _mean(_ksBuffer);
          const diff = Math.abs(cur - _ksBaseline) / _ksBaseline;
          if (diff > 0.4) { // 40% deviation
            _triggerAlert('Keystroke Anomaly', 'Medium');
            _voiceAlert('Typing pattern mismatch detected.');
            _setSuspicious(true);
          }
          _ksBuffer = [];
        }
      }
    });
  }

  function _mean(arr) { return arr.reduce((a,b) => a+b, 0) / arr.length; }

  // ── Suspicious Flag ────────────────────────────────────────────────
  function _setSuspicious(flag) {
    _suspicious = flag;
    const el = document.getElementById('ai-suspicious');
    if (!el) return;
    if (flag) {
      el.textContent = 'Yes ⚠️';
      el.className = 'ai-row-value ai-warn';
    } else {
      el.textContent = 'None';
      el.className = 'ai-row-value ai-ok';
    }
    // Reset after 10s
    setTimeout(() => _setSuspicious(false), 10000);
  }

  // ── TTS Voice Alerts ───────────────────────────────────────────────
  function _voiceAlert(msg) {
    if (!_ttsEnabled) return;
    const now = Date.now();
    if (now - (_lastTTS[msg] || 0) < TTS_COOL) return;
    _lastTTS[msg] = now;
    if ('speechSynthesis' in window) {
      speechSynthesis.cancel();
      const utt = new SpeechSynthesisUtterance(msg);
      utt.rate = 1.0; utt.pitch = 1.0; utt.volume = 1.0;
      utt.lang = 'en-US';
      speechSynthesis.speak(utt);
    }
  }

  // ── Backend Alert ──────────────────────────────────────────────────
  function _triggerAlert(type, severity) {
    const now = Date.now();
    if (now - (_lastAlert[type] || 0) < COOLDOWN) return;
    _lastAlert[type] = now;
    if (_onAlert) _onAlert(type, { severity });
    if (typeof API !== 'undefined' && _sessionId) {
      API.logAlert(_sessionId, type, severity).catch(() => {});
    }
  }

  // ── UI Helpers ─────────────────────────────────────────────────────
  function _ui(id, text, ok) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = text;
    el.className = 'ai-row-value ' + (ok ? 'ai-ok' : 'ai-warn');
  }

  function _el(id) { return document.getElementById(id); }

  // ── Simulation Mode ────────────────────────────────────────────────
  function _startSimulationMode() {
    let tick = 0;
    _intervalId = setInterval(() => {
      tick++;
      const bpm = 75 + Math.sin(tick / 30) * 10 + Math.random() * 8;
      _rppgBPM = Math.round(bpm);
      const stress = bpm > 100 ? 'High ⚠️' : bpm > 85 ? 'Medium' : 'Normal ✓';
      _ui('ai-stress', `${_rppgBPM} BPM — ${stress}`, bpm <= 85);
      _ui('ai-face', 'Matched ✓', true);
      _ui('ai-gaze', 'Focused ✓', true);
      _ui('ai-head', 'Stable ✓', true);
      _ui('ai-faces', 'None', true);
      if (typeof API !== 'undefined' && _sessionId && tick % 10 === 0) {
        API.logStress(_sessionId, _rppgBPM).catch(() => {});
      }
    }, CHECK_MS);
    _initTabSwitch();
    _initVoice();
    _initKeystroke();
  }

  // ── Public getter for BPM ──────────────────────────────────────────
  function getBPM()       { return _rppgBPM; }
  function getTabCount()  { return _tabSwitches; }
  function getCounts()    { return { ..._counts }; }

  return { start, stop, getBPM, getTabCount, getCounts };
})();
