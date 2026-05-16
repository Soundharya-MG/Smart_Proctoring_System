"""
proctor_routes.py — v5 Proctoring Routes (with Federated + Plagiarism)
AIOEPS
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import get_db_connection
from services.proctor_service import process_alert, get_session_alerts
from services.plagiarism_service import compute_plagiarism, get_reference_answers, get_references_for_question, is_coding_question
from services.federated_service import local_update, aggregate_weights, get_global_model
from services.keystroke_service import analyze_keystroke, init_session, get_session_summary, get_all_sessions_summary
import json, base64, os
from datetime import datetime

proctor_bp = Blueprint('proctor', __name__)

def _identity():
    return json.loads(get_jwt_identity())

# ─── Log Alert ───────────────────────────────────────────────────────────────
@proctor_bp.route('/alert', methods=['POST'])
@jwt_required()
def log_alert():
    data = request.get_json()
    session_id   = data.get('session_id')
    warning_type = data.get('warning_type')
    severity     = data.get('severity', 'Medium')
    snapshot_b64 = data.get('snapshot')
    if not session_id or not warning_type:
        return jsonify({'success': False, 'message': 'session_id and warning_type required'}), 400
    result = process_alert(session_id, warning_type, severity, snapshot_b64)
    return jsonify(result), 200

# ─── Session Alerts ──────────────────────────────────────────────────────────
@proctor_bp.route('/session/<int:session_id>/alerts', methods=['GET'])
@jwt_required()
def session_alerts(session_id):
    return jsonify(get_session_alerts(session_id)), 200

# ─── Keystroke Log ───────────────────────────────────────────────────────────
@proctor_bp.route('/keystroke', methods=['POST'])
@jwt_required()
def log_keystroke():
    identity = _identity()
    data     = request.get_json()
    key_data = data.get('key_data', data)          # support flat or nested
    session_id_str = str(data.get('session_id', identity['id']))

    # Run full 40s-baseline + mismatch analysis
    result = analyze_keystroke(key_data, session_id=session_id_str)

    anomaly    = result.get('anomaly_score', 0)
    mismatch   = result.get('mismatch_warning')
    flagged    = result.get('flagged', False)

    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO keystroke_logs (student_id,session_id,key_data,anomaly_score,flagged) VALUES (?,?,?,?,?)",
            (identity['id'], data.get('session_id'),
             json.dumps(key_data), anomaly, 1 if flagged else 0)
        )
        conn.commit()

        # Raise alerts as needed
        if mismatch:
            process_alert(data.get('session_id'), 'Keystroke Speed Mismatch', 'High')
        elif anomaly > 0.6:
            process_alert(data.get('session_id'), 'Keystroke Anomaly (Bot Pattern)', 'High')
        elif anomaly > 0.4:
            process_alert(data.get('session_id'), 'Keystroke Anomaly', 'Medium')

        return jsonify({'success': True, 'analysis': result}), 200
    finally:
        conn.close()


@proctor_bp.route('/keystroke/init', methods=['POST'])
@jwt_required()
def init_keystroke_session():
    """Initialize a new keystroke tracking session."""
    data       = request.get_json()
    session_id = str(data.get('session_id', get_jwt_identity()))
    result     = init_session(session_id)
    return jsonify({'success': True, **result}), 200


@proctor_bp.route('/keystroke/summary', methods=['GET'])
@jwt_required()
def keystroke_summary():
    """Get keystroke summary for a session (admin)."""
    session_id = request.args.get('session_id')
    if session_id:
        return jsonify({'success': True, 'summary': get_session_summary(session_id)}), 200
    return jsonify({'success': True, 'sessions': get_all_sessions_summary()}), 200

# ─── Stress / rPPG Log ───────────────────────────────────────────────────────
@proctor_bp.route('/stress', methods=['POST'])
@jwt_required()
def log_stress():
    identity = _identity()
    data = request.get_json()
    bpm = data.get('bpm', 80)
    stress = 'High' if bpm > 100 else ('Medium' if bpm > 85 else 'Normal')
    conn = get_db_connection()
    try:
        conn.execute(
            "INSERT INTO stress_logs (student_id,session_id,bpm,stress_level) VALUES (?,?,?,?)",
            (identity['id'], data.get('session_id'), bpm, stress)
        )
        conn.commit()
        if bpm > 100:
            process_alert(data.get('session_id'), 'High Stress rPPG', 'Medium')
        return jsonify({'success': True, 'stress_level': stress, 'bpm': bpm}), 200
    finally:
        conn.close()

# ─── Live Monitoring ──────────────────────────────────────────────────────────
@proctor_bp.route('/live', methods=['GET'])
@jwt_required()
def live_monitoring():
    conn = get_db_connection()
    try:
        sessions = conn.execute("""
            SELECT es.id, es.total_warnings, es.face_verified,
                   u.name, u.student_id,
                   e.title as exam_title,
                   COALESCE((SELECT bpm FROM stress_logs WHERE session_id=es.id ORDER BY timestamp DESC LIMIT 1), 78) as bpm,
                   COALESCE((SELECT stress_level FROM stress_logs WHERE session_id=es.id ORDER BY timestamp DESC LIMIT 1), 'Normal') as stress_level,
                   COALESCE((SELECT COUNT(*) FROM warnings WHERE session_id=es.id AND warning_type='Multiple Faces'), 0) as multi_face_count,
                   COALESCE((SELECT COUNT(*) FROM warnings WHERE session_id=es.id AND warning_type='Head Turned'), 0) as head_turn_count,
                   COALESCE((SELECT COUNT(*) FROM warnings WHERE session_id=es.id AND warning_type='Voice Detected'), 0) as voice_count,
                   COALESCE((SELECT COUNT(*) FROM warnings WHERE session_id=es.id AND warning_type='Mobile Detected'), 0) as mobile_count
            FROM exam_sessions es
            JOIN users u ON es.student_id = u.id
            JOIN exams e ON es.exam_id = e.id
            WHERE es.status = 'active'
            ORDER BY es.started_at DESC
        """).fetchall()
        return jsonify({
            'success': True,
            'active_sessions': len(sessions),
            'sessions': [dict(s) for s in sessions]
        }), 200
    finally:
        conn.close()

# ─── Terminate ────────────────────────────────────────────────────────────────
@proctor_bp.route('/terminate/<int:session_id>', methods=['POST'])
@jwt_required()
def terminate_exam(session_id):
    identity = _identity()
    if identity.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    conn = get_db_connection()
    try:
        conn.execute("UPDATE exam_sessions SET status='terminated', submitted_at=? WHERE id=?",
                     (datetime.utcnow(), session_id))
        conn.commit()
        return jsonify({'success': True}), 200
    finally:
        conn.close()

# ─── Snapshot ─────────────────────────────────────────────────────────────────
@proctor_bp.route('/snapshot', methods=['POST'])
@jwt_required()
def save_snapshot():
    data = request.get_json()
    session_id = data.get('session_id')
    image_b64  = data.get('image')
    if not image_b64:
        return jsonify({'success': False, 'message': 'No image'}), 400
    try:
        img_data = base64.b64decode(image_b64.split(',')[-1])
        snap_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'snapshots')
        os.makedirs(snap_dir, exist_ok=True)
        filename = f"snap_{session_id}_{int(datetime.utcnow().timestamp())}.jpg"
        with open(os.path.join(snap_dir, filename), 'wb') as f:
            f.write(img_data)
        return jsonify({'success': True, 'path': filename}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# ─── Plagiarism Check ─────────────────────────────────────────────────────────
@proctor_bp.route('/plagiarism', methods=['POST'])
@jwt_required()
def check_plagiarism():
    data          = request.get_json()
    question_type = data.get('question_type', 'MCQ')

    # Strictly bypass for non-coding questions
    if not is_coding_question(question_type):
        return jsonify({
            'success': True,
            'plagiarism': {
                'score': 0,
                'level': 'N/A',
                'details': 'Plagiarism check is only applicable to Coding questions.'
            },
            'bypassed': True
        }), 200

    answer        = data.get('answer', '')
    subject       = data.get('subject', '')
    question_text = data.get('question_text', '')
    # Use question-aware references if question_text provided
    if question_text:
        refs = data.get('references', []) or get_references_for_question(question_text)
    else:
        refs = data.get('references', []) or get_reference_answers(subject)
    result  = compute_plagiarism(answer, refs)
    return jsonify({'success': True, 'plagiarism': result, 'bypassed': False}), 200

# ─── Federated Learning: Local Update ─────────────────────────────────────────
@proctor_bp.route('/federated/local-update', methods=['POST'])
@jwt_required()
def federated_local():
    identity = _identity()
    data = request.get_json()
    result = local_update(identity['id'], data.get('behavior_data', {}))
    return jsonify(result), 200

# ─── Federated Learning: Aggregate (admin) ────────────────────────────────────
@proctor_bp.route('/federated/aggregate', methods=['POST'])
@jwt_required()
def federated_aggregate():
    identity = _identity()
    if identity.get('role') != 'admin':
        return jsonify({'success': False, 'message': 'Admin only'}), 403
    result = aggregate_weights()
    return jsonify(result), 200

# ─── Federated Learning: Global Model ─────────────────────────────────────────
@proctor_bp.route('/federated/model', methods=['GET'])
@jwt_required()
def federated_model():
    return jsonify(get_global_model()), 200

# ─── Real-time Stats for Admin ────────────────────────────────────────────────
@proctor_bp.route('/realtime-stats', methods=['GET'])
@jwt_required()
def realtime_stats():
    conn = get_db_connection()
    try:
        active = conn.execute("SELECT COUNT(*) FROM exam_sessions WHERE status='active'").fetchone()[0]
        warns_today = conn.execute(
            "SELECT COUNT(*) FROM warnings WHERE date(timestamp)=date('now')"
        ).fetchone()[0]
        suspicious = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM exam_sessions WHERE total_warnings>=3 AND status='active'"
        ).fetchone()[0]
        avg_bpm = conn.execute(
            "SELECT AVG(bpm) FROM stress_logs WHERE date(timestamp)=date('now')"
        ).fetchone()[0] or 75

        # Warning breakdown
        breakdown = conn.execute("""
            SELECT warning_type, COUNT(*) as cnt FROM warnings
            WHERE date(timestamp)=date('now')
            GROUP BY warning_type ORDER BY cnt DESC
        """).fetchall()

        return jsonify({
            'success': True,
            'active_sessions': active,
            'warnings_today': warns_today,
            'suspicious_count': suspicious,
            'avg_bpm': round(avg_bpm, 1),
            'breakdown': [dict(b) for b in breakdown]
        }), 200
    finally:
        conn.close()
