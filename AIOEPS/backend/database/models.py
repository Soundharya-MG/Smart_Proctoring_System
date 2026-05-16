"""
models.py - SQLAlchemy ORM Models
AIOEPS - AI Based Online Examination Proctoring System
"""

from datetime import datetime
from database.db import db

class User(db.Model):
    """Student and Admin users."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(10), default='student')
    face_encoded = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'face_encoded': self.face_encoded,
            'created_at': str(self.created_at),
            'is_active': self.is_active
        }

class Exam(db.Model):
    """Exam definitions."""
    __tablename__ = 'exams'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.String(20), unique=True, nullable=False)
    title = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    exam_type = db.Column(db.String(20), default='MCQ')
    duration_minutes = db.Column(db.Integer, nullable=False)
    total_marks = db.Column(db.Integer, nullable=False)
    pass_marks = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='upcoming')
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    instructions = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'title': self.title,
            'subject': self.subject,
            'exam_type': self.exam_type,
            'duration_minutes': self.duration_minutes,
            'total_marks': self.total_marks,
            'pass_marks': self.pass_marks,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
            'status': self.status
        }

class Question(db.Model):
    """Exam questions (MCQ + Coding)."""
    __tablename__ = 'questions'
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    question_text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(10), default='MCQ')
    option_a = db.Column(db.Text)
    option_b = db.Column(db.Text)
    option_c = db.Column(db.Text)
    option_d = db.Column(db.Text)
    correct_answer = db.Column(db.String(5))
    marks = db.Column(db.Integer, default=1)
    language = db.Column(db.String(20))
    sample_input = db.Column(db.Text)
    expected_output = db.Column(db.Text)
    order_num = db.Column(db.Integer)

    def to_dict(self):
        return {
            'id': self.id,
            'exam_id': self.exam_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'option_a': self.option_a,
            'option_b': self.option_b,
            'option_c': self.option_c,
            'option_d': self.option_d,
            'marks': self.marks,
            'language': self.language,
            'sample_input': self.sample_input,
            'expected_output': self.expected_output
        }

class ExamSession(db.Model):
    """Active exam sessions."""
    __tablename__ = 'exam_sessions'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'), nullable=False)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    submitted_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    score = db.Column(db.Float, default=0)
    percentage = db.Column(db.Float, default=0)
    result = db.Column(db.String(10))
    total_warnings = db.Column(db.Integer, default=0)
    face_verified = db.Column(db.Boolean, default=False)
    ip_address = db.Column(db.String(50))

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'started_at': str(self.started_at),
            'submitted_at': str(self.submitted_at) if self.submitted_at else None,
            'status': self.status,
            'score': self.score,
            'percentage': self.percentage,
            'result': self.result,
            'total_warnings': self.total_warnings,
            'face_verified': self.face_verified
        }

class Warning(db.Model):
    """Proctoring alerts/warnings."""
    __tablename__ = 'warnings'
    id = db.Column(db.Integer, primary_key=True)
    warning_id = db.Column(db.String(20), unique=True)
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'))
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    exam_id = db.Column(db.Integer, db.ForeignKey('exams.id'))
    warning_type = db.Column(db.String(50), nullable=False)
    severity = db.Column(db.String(10), default='Medium')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    snapshot_path = db.Column(db.String(300))
    action_taken = db.Column(db.String(100))
    resolved = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            'id': self.id,
            'warning_id': self.warning_id,
            'student_id': self.student_id,
            'exam_id': self.exam_id,
            'warning_type': self.warning_type,
            'severity': self.severity,
            'timestamp': str(self.timestamp),
            'snapshot_path': self.snapshot_path,
            'action_taken': self.action_taken,
            'resolved': self.resolved
        }

class StressLog(db.Model):
    """rPPG/BPM stress logs."""
    __tablename__ = 'stress_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'))
    bpm = db.Column(db.Float)
    stress_level = db.Column(db.String(10))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class KeystrokeLog(db.Model):
    """Keystroke dynamics logs."""
    __tablename__ = 'keystroke_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_id = db.Column(db.Integer, db.ForeignKey('exam_sessions.id'))
    key_data = db.Column(db.Text)
    anomaly_score = db.Column(db.Float, default=0)
    flagged = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class ActivityLog(db.Model):
    """General activity log."""
    __tablename__ = 'activity_logs'
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer)
    session_id = db.Column(db.Integer)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
