"""
keystroke_service.py - Keystroke Dynamics Analysis
AIOEPS - AI Based Online Examination Proctoring System

Features:
  - 40-second baseline recording (dwell + flight times → WPM signature)
  - Continuous live monitoring vs baseline
  - Typing speed mismatch detection
  - Bot/paste detection
"""

import json
import math
import numpy as np
from datetime import datetime

# In-memory session store: session_id -> keystroke state
_sessions: dict = {}


# ─── WPM helper ──────────────────────────────────────────────────────────────

def _wpm_from_flight(flight_times: list) -> float:
    """
    Estimate WPM from flight-time list.
    Average chars per second = 1000 / avg_flight_ms
    Words ≈ chars / 5
    """
    if not flight_times:
        return 0.0
    avg_flight = float(np.mean(flight_times))
    if avg_flight <= 0:
        return 0.0
    chars_per_sec = 1000.0 / avg_flight
    return round(chars_per_sec * 60 / 5, 1)


# ─── Session lifecycle ────────────────────────────────────────────────────────

def init_session(session_id: str) -> dict:
    """Create a fresh keystroke tracking session."""
    _sessions[session_id] = {
        'phase': 'baseline',          # 'baseline' | 'monitoring'
        'started_at': datetime.utcnow().isoformat(),
        'baseline_dwell': [],
        'baseline_flight': [],
        'baseline_wpm': None,
        'baseline_avg_dwell': None,
        'baseline_std_dwell': None,
        'live_wpm': None,
        'mismatch_count': 0,
        'last_warning': None,
        'history': [],                 # [{ts, wpm, flagged}]
    }
    return {'session_id': session_id, 'phase': 'baseline'}


def get_session(session_id: str) -> dict:
    return _sessions.get(session_id, {})


# ─── Core analysis ───────────────────────────────────────────────────────────

def analyze_keystroke(key_data: dict, session_id: str = None) -> dict:
    """
    Main entry point.
    key_data = { dwell_times: [...], flight_times: [...], elapsed_seconds: float }

    Returns a result dict with:
      phase, anomaly_score, flagged, reason,
      baseline_wpm (if captured), live_wpm, mismatch_warning
    """
    dwell_times  = key_data.get('dwell_times', [])
    flight_times = key_data.get('flight_times', [])
    elapsed_sec  = float(key_data.get('elapsed_seconds', 9999))

    if not dwell_times or not flight_times:
        return {'anomaly_score': 0, 'flagged': False,
                'reason': 'Insufficient data', 'phase': 'baseline'}

    dwell  = np.array(dwell_times, dtype=float)
    flight = np.array(flight_times, dtype=float)

    avg_dwell  = float(np.mean(dwell))
    std_dwell  = float(np.std(dwell))
    avg_flight = float(np.mean(flight))
    live_wpm   = _wpm_from_flight(flight_times)

    # ── Bot / paste heuristics (always active) ────────────────────────
    anomaly_score = 0.0
    bot_reasons   = []

    if avg_dwell < 50:
        anomaly_score += 0.4
        bot_reasons.append('dwell<50ms')
    if std_dwell < 10:
        anomaly_score += 0.3
        bot_reasons.append('uniform_rhythm')
    if avg_flight < 30:
        anomaly_score += 0.3
        bot_reasons.append('instant_transitions')

    anomaly_score = min(anomaly_score, 1.0)
    bot_flagged   = anomaly_score > 0.6

    result = {
        'phase':         'baseline',
        'anomaly_score': round(anomaly_score, 3),
        'flagged':       bot_flagged,
        'avg_dwell_ms':  round(avg_dwell, 1),
        'avg_flight_ms': round(avg_flight, 1),
        'live_wpm':      live_wpm,
        'baseline_wpm':  None,
        'mismatch_warning': None,
        'mismatch_count':   0,
        'reason': ('Bot-like typing pattern detected'
                   if bot_flagged else 'Normal typing pattern'),
    }

    # ── Session-aware 40-second baseline + mismatch logic ─────────────
    if session_id:
        sess = _sessions.get(session_id)
        if not sess:
            sess = init_session(session_id)
            _sessions[session_id] = sess

        sess['baseline_dwell'].extend(dwell_times)
        sess['baseline_flight'].extend(flight_times)

        if sess['phase'] == 'baseline':
            if elapsed_sec >= 40 and len(sess['baseline_flight']) >= 10:
                # Lock baseline
                sess['phase']            = 'monitoring'
                sess['baseline_wpm']     = _wpm_from_flight(sess['baseline_flight'])
                sess['baseline_avg_dwell'] = float(np.mean(sess['baseline_dwell']))
                sess['baseline_std_dwell'] = float(np.std(sess['baseline_dwell']))
                result['phase']          = 'monitoring'
                result['baseline_wpm']   = sess['baseline_wpm']
            else:
                result['phase']        = 'baseline'
                result['baseline_wpm'] = None

        if sess['phase'] == 'monitoring':
            result['phase']        = 'monitoring'
            result['baseline_wpm'] = sess['baseline_wpm']

            # ── Mismatch detection ──────────────────────────────────
            bwpm = sess['baseline_wpm'] or 0
            if bwpm > 0 and live_wpm > 0:
                ratio = live_wpm / bwpm
                # Flag if speed jumps more than 2× baseline OR drops below 0.3×
                if ratio > 2.0 or ratio < 0.3:
                    sess['mismatch_count'] += 1
                    warning_msg = (
                        "Warning: Typing speed mismatch detected! "
                        f"Pattern changed significantly after 40s baseline "
                        f"(Baseline: {bwpm} WPM → Current: {live_wpm} WPM)"
                    )
                    sess['last_warning']        = warning_msg
                    result['mismatch_warning']  = warning_msg
                    result['flagged']           = True
                    result['reason']            = warning_msg

            result['mismatch_count'] = sess['mismatch_count']

        # History
        sess['history'].append({
            'ts':      datetime.utcnow().isoformat(),
            'wpm':     live_wpm,
            'flagged': result['flagged'],
        })
        # Keep last 100
        if len(sess['history']) > 100:
            sess['history'] = sess['history'][-100:]

    return result


# ─── Plagiarism bypass for MCQ ────────────────────────────────────────────────

def is_coding_question(question_type: str) -> bool:
    """Only run plagiarism on coding questions."""
    return (question_type or '').upper() in ('CODING', 'CODE')


# ─── Session summary (for admin API) ─────────────────────────────────────────

def get_session_summary(session_id: str) -> dict:
    sess = _sessions.get(session_id, {})
    if not sess:
        return {'error': 'Session not found'}
    return {
        'session_id':     session_id,
        'phase':          sess.get('phase', 'baseline'),
        'baseline_wpm':   sess.get('baseline_wpm'),
        'mismatch_count': sess.get('mismatch_count', 0),
        'last_warning':   sess.get('last_warning'),
        'history':        sess.get('history', [])[-20:],
    }


def get_all_sessions_summary() -> list:
    return [
        {
            'session_id':     sid,
            'phase':          s.get('phase'),
            'baseline_wpm':   s.get('baseline_wpm'),
            'mismatch_count': s.get('mismatch_count', 0),
            'last_warning':   s.get('last_warning'),
        }
        for sid, s in _sessions.items()
    ]
