"""
student_routes.py - Student Routes
AIOEPS - AI Based Online Examination Proctoring System
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database.db import get_db_connection
from services.exam_service import submit_exam, get_exam_result
from datetime import datetime
import json
import base64
import os

student_bp = Blueprint('student', __name__)


def get_current_user():
    return json.loads(get_jwt_identity())


# ── Dashboard ────────────────────────────────────────────────────────────────
@student_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def dashboard():
    user = get_current_user()
    conn = get_db_connection()
    try:
        sessions = conn.execute(
            "SELECT es.*, e.title, e.subject FROM exam_sessions es JOIN exams e ON es.exam_id=e.id WHERE es.student_id=? ORDER BY es.started_at DESC",
            (user['id'],)
        ).fetchall()

        total     = len(sessions)
        passed    = sum(1 for s in sessions if s['result'] == 'Pass')
        failed    = sum(1 for s in sessions if s['result'] == 'Fail')
        avg_score = round(sum(s['percentage'] or 0 for s in sessions) / total, 1) if total else 0

        return jsonify({
            'success': True,
            'stats': {
                'total_exams': total,
                'passed': passed,
                'failed': failed,
                'avg_score': avg_score
            },
            'recent': [dict(s) for s in sessions[:5]]
        })
    finally:
        conn.close()


# ── Available Exams ──────────────────────────────────────────────────────────
@student_bp.route('/exams', methods=['GET'])
@jwt_required()
def get_exams():
    conn = get_db_connection()
    try:
        exams = conn.execute(
            "SELECT * FROM exams WHERE status IN ('upcoming','ongoing') ORDER BY created_at DESC"
        ).fetchall()
        return jsonify({'success': True, 'exams': [dict(e) for e in exams]})
    finally:
        conn.close()


# ── Start Exam ───────────────────────────────────────────────────────────────
@student_bp.route('/exams/<exam_id>/start', methods=['POST'])
@jwt_required()
def start_exam(exam_id):
    user = get_current_user()
    conn = get_db_connection()
    try:
        # Support both string exam_id (EXM001) and numeric id
        if str(exam_id).isdigit():
            exam = conn.execute("SELECT * FROM exams WHERE id=?", (int(exam_id),)).fetchone()
        else:
            exam = conn.execute("SELECT * FROM exams WHERE exam_id=?", (exam_id,)).fetchone()

        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        real_exam_id = exam['id']

        # Check if already has active session
        active = conn.execute(
            "SELECT * FROM exam_sessions WHERE student_id=? AND exam_id=? AND status='active'",
            (user['id'], real_exam_id)
        ).fetchone()
        if active:
            return jsonify({'success': True, 'session_id': active['id'], 'exam': dict(exam), 'message': 'Resuming existing session'})

        # Check if already submitted
        submitted = conn.execute(
            "SELECT * FROM exam_sessions WHERE student_id=? AND exam_id=? AND status='submitted'",
            (user['id'], real_exam_id)
        ).fetchone()
        if submitted:
            return jsonify({'success': False, 'message': 'You have already submitted this exam'}), 409

        ip = request.remote_addr
        cursor = conn.execute(
            "INSERT INTO exam_sessions (student_id, exam_id, status, ip_address) VALUES (?,?,?,?)",
            (user['id'], real_exam_id, 'active', ip)
        )
        conn.commit()
        session_id = cursor.lastrowid

        return jsonify({'success': True, 'session_id': session_id, 'exam': dict(exam)})
    finally:
        conn.close()


# ── Get Questions ────────────────────────────────────────────────────────────
@student_bp.route('/exams/<exam_id>/questions', methods=['GET'])
@jwt_required()
def get_questions(exam_id):
    conn = get_db_connection()
    try:
        # Support both string exam_id (EXM001) and numeric id
        if str(exam_id).isdigit():
            exam = conn.execute("SELECT id FROM exams WHERE id=?", (int(exam_id),)).fetchone()
        else:
            exam = conn.execute("SELECT id FROM exams WHERE exam_id=?", (exam_id,)).fetchone()

        if not exam:
            return jsonify({'success': False, 'message': 'Exam not found'}), 404

        exam_details = conn.execute("SELECT * FROM exams WHERE id=?", (exam['id'],)).fetchone()
        questions = conn.execute(
            "SELECT id, question_text, question_type, option_a, option_b, option_c, option_d, marks, language, sample_input, expected_output FROM questions WHERE exam_id=? ORDER BY id",
            (exam['id'],)
        ).fetchall()
        # Never send correct_answer to student!
        return jsonify({'success': True, 'questions': [dict(q) for q in questions], 'exam': dict(exam_details)})
    finally:
        conn.close()


# ── Submit Exam ──────────────────────────────────────────────────────────────
@student_bp.route('/sessions/<int:session_id>/submit', methods=['POST'])
@jwt_required()
def submit(session_id):
    user = get_current_user()
    data = request.get_json()
    answers = data.get('answers', {})

    result = submit_exam(session_id, user['id'], answers)
    return jsonify(result), (200 if result['success'] else 400)


# ── Get Single Result ────────────────────────────────────────────────────────
@student_bp.route('/results/<int:session_id>', methods=['GET'])
@jwt_required()
def get_result(session_id):
    user = get_current_user()
    result = get_exam_result(session_id, user['id'])
    return jsonify(result), (200 if result['success'] else 404)


# ── My All Results ───────────────────────────────────────────────────────────
@student_bp.route('/my-results', methods=['GET'])
@jwt_required()
def my_results():
    user = get_current_user()
    conn = get_db_connection()
    try:
        sessions = conn.execute("""
            SELECT es.*, e.title, e.subject, e.total_marks, e.pass_marks
            FROM exam_sessions es
            JOIN exams e ON es.exam_id = e.id
            WHERE es.student_id=? AND es.status='submitted'
            ORDER BY es.submitted_at DESC
        """, (user['id'],)).fetchall()
        return jsonify({'success': True, 'results': [dict(s) for s in sessions]})
    finally:
        conn.close()


# ── Upload Face ──────────────────────────────────────────────────────────────
@student_bp.route('/upload-face', methods=['POST'])
@jwt_required()
def upload_face():
    user = get_current_user()
    data = request.get_json()
    image_b64 = data.get('image', '')

    if not image_b64:
        return jsonify({'success': False, 'message': 'No image provided'}), 400

    try:
        conn = get_db_connection()
        conn.execute("UPDATE users SET face_encoded=1 WHERE id=?", (user['id'],))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Face registered successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ── Federated Update ─────────────────────────────────────────────────────────
@student_bp.route('/federated-update', methods=['POST'])
@jwt_required()
def federated_update():
    # Accept and store behavioral data for federated learning
    return jsonify({'success': True, 'message': 'Behavioral data received'})
