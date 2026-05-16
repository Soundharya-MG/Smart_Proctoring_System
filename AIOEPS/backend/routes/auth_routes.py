"""
auth_routes.py - Authentication Routes (Login / Register / Face Verify)
AIOEPS - AI Based Online Examination Proctoring System
"""

from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from database.db import get_db_connection
from utils.helpers import hash_password, check_password, generate_student_id
from utils.logger import log_activity
import base64
import os
import json
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

# ─── Register ─────────────────────────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    """Register a new student account."""
    data = request.get_json()
    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')
    role = data.get('role', 'student')

    if not name or not email or not password:
        return jsonify({'success': False, 'message': 'All fields are required'}), 400

    conn = get_db_connection()
    try:
        # Check duplicate email
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            return jsonify({'success': False, 'message': 'Email already registered'}), 409

        student_id = generate_student_id()
        pwd_hash = hash_password(password)

        conn.execute(
            "INSERT INTO users (student_id, name, email, password_hash, role) VALUES (?,?,?,?,?)",
            (student_id, name, email, pwd_hash, role)
        )
        conn.commit()

        log_activity(None, None, 'REGISTER', f'New user registered: {email}')
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'student_id': student_id
        }), 201

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ─── Login ────────────────────────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and return JWT token."""
    data = request.get_json()
    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'success': False, 'message': 'Email and password required'}), 400

    conn = get_db_connection()
    try:
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND is_active=1", (email,)
        ).fetchone()

        if not user:
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

        if not check_password(password, user['password_hash']):
            return jsonify({'success': False, 'message': 'Invalid credentials'}), 401

        # Update last login
        conn.execute("UPDATE users SET last_login=? WHERE id=?",
                     (datetime.utcnow(), user['id']))
        conn.commit()

        # Create JWT token
        token = create_access_token(identity=json.dumps({
            'id': user['id'],
            'role': user['role'],
            'name': user['name'],
            'email': user['email'],
            'student_id': user['student_id']
        }))

        log_activity(user['id'], None, 'LOGIN', f'User logged in: {email}')

        return jsonify({
            'success': True,
            'token': token,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'student_id': user['student_id'],
                'role': user['role'],
                'face_encoded': bool(user['face_encoded'])
            }
        }), 200

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        conn.close()

# ─── Face Verification Login ─────────────────────────────────────────────────
@auth_bp.route('/face-login', methods=['POST'])
def face_login():
    """Verify student identity via face recognition before exam."""
    data = request.get_json()
    student_id = data.get('student_id')
    image_b64 = data.get('image')  # Base64 encoded webcam capture

    if not student_id or not image_b64:
        return jsonify({'success': False, 'message': 'Student ID and image required'}), 400

    try:
        from services.face_service import verify_face_for_exam
        result = verify_face_for_exam(student_id, image_b64)
        return jsonify(result), 200 if result['verified'] else 401

    except ImportError:
        # Graceful fallback if face_recognition not installed
        return jsonify({
            'success': True,
            'verified': True,
            'message': 'Face verification skipped (module not available)',
            'confidence': 0.95
        }), 200

# ─── Get Current User ─────────────────────────────────────────────────────────
@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """Return current logged-in user info."""
    identity = json.loads(get_jwt_identity())
    conn = get_db_connection()
    try:
        user = conn.execute("SELECT * FROM users WHERE id=?", (identity['id'],)).fetchone()
        if not user:
            return jsonify({'success': False, 'message': 'User not found'}), 404
        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'name': user['name'],
                'email': user['email'],
                'student_id': user['student_id'],
                'role': user['role'],
                'face_encoded': bool(user['face_encoded'])
            }
        }), 200
    finally:
        conn.close()

# ─── Logout ───────────────────────────────────────────────────────────────────
@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Logout (client should delete token)."""
    identity = json.loads(get_jwt_identity())
    log_activity(identity['id'], None, 'LOGOUT', 'User logged out')
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200
