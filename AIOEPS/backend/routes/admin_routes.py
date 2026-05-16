"""
admin_routes.py - Admin API Routes
AIOEPS - AI Based Online Examination Proctoring System
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import get_db_connection
from utils.helpers import hash_password
import json
from datetime import datetime

admin_bp = Blueprint('admin', __name__)

def get_current_user():
    return json.loads(get_jwt_identity())

def require_admin():
    user = get_current_user()
    if user.get('role') != 'admin':
        return None, jsonify({'success': False, 'message': 'Admin access required'}), 403
    return user, None, None

# ─── Dashboard Overview ───────────────────────────────────────────────────────
@admin_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    """Admin dashboard stats."""
    conn = get_db_connection()
    try:
        total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        total_exams = conn.execute("SELECT COUNT(*) FROM exams").fetchone()[0]
        total_warnings = conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
        high_warnings = conn.execute("SELECT COUNT(*) FROM warnings WHERE severity='High'").fetchone()[0]
        ongoing_exams = conn.execute("SELECT COUNT(*) FROM exams WHERE status='ongoing'").fetchone()[0]
        completed_exams = conn.execute("SELECT COUNT(*) FROM exams WHERE status='completed'").fetchone()[0]

        safe_count = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM exam_sessions WHERE total_warnings=0"
        ).fetchone()[0]

        suspicious = conn.execute(
            "SELECT COUNT(DISTINCT student_id) FROM exam_sessions WHERE total_warnings>=3"
        ).fetchone()[0]

        # Warning type distribution
        warning_types = conn.execute("""
            SELECT warning_type, COUNT(*) as count
            FROM warnings GROUP BY warning_type ORDER BY count DESC
        """).fetchall()

        # Live student status
        live_students = conn.execute("""
            SELECT u.name, u.student_id, es.total_warnings, es.status,
                   COALESCE(sl.bpm, 80) as rppg
            FROM exam_sessions es
            JOIN users u ON es.student_id = u.id
            LEFT JOIN stress_logs sl ON sl.student_id = u.id
            WHERE es.status = 'active'
            ORDER BY es.started_at DESC LIMIT 10
        """).fetchall()

        return jsonify({
            'success': True,
            'stats': {
                'total_students': total_students,
                'total_exams': total_exams,
                'total_warnings': total_warnings,
                'high_severity_warnings': high_warnings,
                'ongoing_exams': ongoing_exams,
                'completed_exams': completed_exams,
                'safe_students': safe_count,
                'suspicious_students': suspicious
            },
            'warning_types': [dict(w) for w in warning_types],
            'live_students': [dict(s) for s in live_students]
        }), 200
    finally:
        conn.close()

# ─── Students CRUD ────────────────────────────────────────────────────────────
@admin_bp.route('/students', methods=['GET'])
@jwt_required()
def get_students():
    """Get all students with stats."""
    conn = get_db_connection()
    try:
        students = conn.execute("""
            SELECT u.*, 
                   COUNT(DISTINCT es.id) as exam_count,
                   AVG(es.percentage) as avg_score,
                   COUNT(DISTINCT w.id) as warning_count
            FROM users u
            LEFT JOIN exam_sessions es ON u.id = es.student_id
            LEFT JOIN warnings w ON u.id = w.student_id
            WHERE u.role='student'
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """).fetchall()
        return jsonify({'success': True, 'students': [dict(s) for s in students]}), 200
    finally:
        conn.close()

@admin_bp.route('/students', methods=['POST'])
@jwt_required()
def add_student():
    """Add a new student."""
    data = request.get_json()
    from utils.helpers import generate_student_id
    conn = get_db_connection()
    try:
        student_id = generate_student_id()
        pwd_hash = hash_password(data.get('password', 'student123'))
        conn.execute(
            "INSERT INTO users (student_id,name,email,password_hash,role) VALUES (?,?,?,?,?)",
            (student_id, data['name'], data['email'], pwd_hash, 'student')
        )
        conn.commit()
        return jsonify({'success': True, 'student_id': student_id, 'message': 'Student added'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/students/<int:student_id>', methods=['DELETE'])
@jwt_required()
def delete_student(student_id):
    """Delete a student account."""
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET is_active=0 WHERE id=?", (student_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Student deactivated'}), 200
    finally:
        conn.close()

# ─── Exams CRUD ───────────────────────────────────────────────────────────────
@admin_bp.route('/exams', methods=['GET'])
@jwt_required()
def get_exams():
    """Get all exams."""
    conn = get_db_connection()
    try:
        exams = conn.execute("""
            SELECT e.*, COUNT(q.id) as question_count
            FROM exams e
            LEFT JOIN questions q ON e.id = q.exam_id
            GROUP BY e.id ORDER BY e.created_at DESC
        """).fetchall()
        return jsonify({'success': True, 'exams': [dict(e) for e in exams]}), 200
    finally:
        conn.close()

@admin_bp.route('/exams', methods=['POST'])
@jwt_required()
def create_exam():
    """Create a new exam."""
    user = get_current_user()
    data = request.get_json()
    conn = get_db_connection()
    try:
        import random, string
        exam_id = 'EXM' + ''.join(random.choices(string.digits, k=4))
        conn.execute("""
            INSERT INTO exams (exam_id,title,subject,exam_type,duration_minutes,total_marks,pass_marks,instructions,status,created_by)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (
            exam_id, data['title'], data['subject'], data.get('exam_type','MCQ'),
            data['duration_minutes'], data['total_marks'], data['pass_marks'],
            data.get('instructions',''), data.get('status','upcoming'), user['id']
        ))
        conn.commit()
        return jsonify({'success': True, 'exam_id': exam_id, 'message': 'Exam created'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

@admin_bp.route('/exams/<exam_id>/status', methods=['PUT'])
@jwt_required()
def update_exam_status(exam_id):
    """Update exam status."""
    data = request.get_json()
    conn = get_db_connection()
    try:
        conn.execute("UPDATE exams SET status=? WHERE exam_id=?", (data['status'], exam_id))
        conn.commit()
        return jsonify({'success': True, 'message': 'Status updated'}), 200
    finally:
        conn.close()

# ─── Add Questions ────────────────────────────────────────────────────────────
@admin_bp.route('/exams/<exam_id>/questions', methods=['POST'])
@jwt_required()
def add_question(exam_id):
    """Add a question to an exam."""
    conn = get_db_connection()
    data = request.get_json()
    try:
        exam = conn.execute("SELECT id FROM exams WHERE exam_id=?", (exam_id,)).fetchone()
        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found'}), 404
        conn.execute("""
            INSERT INTO questions (exam_id,question_text,question_type,option_a,option_b,option_c,option_d,correct_answer,marks,language,sample_input,expected_output)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            exam['id'], data['question_text'], data.get('question_type','MCQ'),
            data.get('option_a'), data.get('option_b'), data.get('option_c'), data.get('option_d'),
            data.get('correct_answer'), data.get('marks',1),
            data.get('language'), data.get('sample_input'), data.get('expected_output')
        ))
        conn.commit()
        return jsonify({'success': True, 'message': 'Question added'}), 201
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ─── All Warnings ─────────────────────────────────────────────────────────────
@admin_bp.route('/warnings', methods=['GET'])
@jwt_required()
def get_warnings():
    """Get all proctoring warnings."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT w.*, u.name as student_name, u.student_id as sid, e.title as exam_title
            FROM warnings w
            JOIN users u ON w.student_id = u.id
            JOIN exams e ON w.exam_id = e.id
            ORDER BY w.timestamp DESC LIMIT 100
        """).fetchall()
        return jsonify({'success': True, 'warnings': [dict(r) for r in rows]}), 200
    finally:
        conn.close()

# ─── All Results ──────────────────────────────────────────────────────────────
@admin_bp.route('/results', methods=['GET'])
@jwt_required()
def get_results():
    """Get all exam results."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT es.*, u.name, u.student_id as sid, e.title, e.subject
            FROM exam_sessions es
            JOIN users u ON es.student_id = u.id
            JOIN exams e ON es.exam_id = e.id
            WHERE es.status IN ('submitted','terminated')
            ORDER BY es.submitted_at DESC
        """).fetchall()
        return jsonify({'success': True, 'results': [dict(r) for r in rows]}), 200
    finally:
        conn.close()

# ─── AI Analysis ─────────────────────────────────────────────────────────────
@admin_bp.route('/ai-analysis', methods=['GET'])
@jwt_required()
def ai_analysis():
    """AI Analysis overview for admin."""
    conn = get_db_connection()
    try:
        face_match = conn.execute("SELECT COUNT(*) FROM warnings WHERE warning_type='Face Mismatch'").fetchone()[0]
        looking_away = conn.execute("SELECT COUNT(*) FROM warnings WHERE warning_type='Looking Away'").fetchone()[0]
        multiple_faces = conn.execute("SELECT COUNT(*) FROM warnings WHERE warning_type='Multiple Faces'").fetchone()[0]
        mobile = conn.execute("SELECT COUNT(*) FROM warnings WHERE warning_type='Mobile Detected'").fetchone()[0]

        total_sessions = conn.execute("SELECT COUNT(*) FROM exam_sessions").fetchone()[0]
        total_warnings = conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
        accuracy = round(100 - (total_warnings / max(total_sessions, 1) * 5), 2)

        stress_data = conn.execute("""
            SELECT stress_level, COUNT(*) as cnt
            FROM stress_logs GROUP BY stress_level
        """).fetchall()

        return jsonify({
            'success': True,
            'face_mismatches': face_match,
            'looking_away': looking_away,
            'multiple_faces': multiple_faces,
            'mobile_detected': mobile,
            'ai_accuracy': min(accuracy, 99.9),
            'stress_distribution': [dict(s) for s in stress_data]
        }), 200
    finally:
        conn.close()

# ─── Settings ─────────────────────────────────────────────────────────────────
@admin_bp.route('/settings', methods=['GET', 'POST'])
@jwt_required()
def settings():
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'settings': {
                'system_name': 'AIOEPS',
                'timezone': 'UTC+05:30 Asia/Kolkata',
                'email_notifications': True,
                'sms_notifications': True,
                'push_notifications': False,
                'ai_sensitivity': 'Medium'
            }
        }), 200
    data = request.get_json()
    return jsonify({'success': True, 'message': 'Settings saved', 'settings': data}), 200

# ─── Delete Exam ──────────────────────────────────────────────────────────────
@admin_bp.route('/exams/<exam_id>', methods=['DELETE'])
@jwt_required()
def delete_exam(exam_id):
    """Delete an exam."""
    conn = get_db_connection()
    try:
        conn.execute("DELETE FROM questions WHERE exam_id=(SELECT id FROM exams WHERE exam_id=?)", (exam_id,))
        conn.execute("DELETE FROM exams WHERE exam_id=?", (exam_id,))
        conn.commit()
        return jsonify({'success': True, 'message': 'Exam deleted'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ─── Get Questions for Exam ───────────────────────────────────────────────────
@admin_bp.route('/exams/<exam_id>/questions', methods=['GET'])
@jwt_required()
def get_questions(exam_id):
    """Get questions for an exam."""
    conn = get_db_connection()
    try:
        exam = conn.execute("SELECT id FROM exams WHERE exam_id=?", (exam_id,)).fetchone()
        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found'}), 404
        questions = conn.execute("SELECT * FROM questions WHERE exam_id=?", (exam['id'],)).fetchall()
        return jsonify({'success': True, 'questions': [dict(q) for q in questions]}), 200
    finally:
        conn.close()

# ─── Get Stored Answers ───────────────────────────────────────────────────────
@admin_bp.route('/stored-answers', methods=['GET'])
@jwt_required()
def get_stored_answers():
    """Get all student answers (MCQ selections + coding submissions) for admin view."""
    conn = get_db_connection()
    try:
        rows = conn.execute("""
            SELECT
                a.id,
                a.session_id,
                a.question_id,
                a.student_answer,
                a.is_correct,
                a.marks_obtained,
                a.answered_at,
                u.name AS student_name,
                u.student_id AS student_sid,
                e.title AS exam_title,
                q.question_text,
                q.question_type,
                q.marks AS total_marks,
                q.correct_answer,
                q.option_a, q.option_b, q.option_c, q.option_d
            FROM answers a
            JOIN exam_sessions es ON a.session_id = es.id
            JOIN users u ON es.student_id = u.id
            JOIN exams e ON es.exam_id = e.id
            JOIN questions q ON a.question_id = q.id
            ORDER BY a.session_id DESC, a.id ASC
        """).fetchall()
        return jsonify({'success': True, 'answers': [dict(r) for r in rows]}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()
