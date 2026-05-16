"""
proctor_service.py - Cheating Detection Service
AIOEPS - AI Based Online Examination Proctoring System
"""

from database.db import get_db_connection
from datetime import datetime
import random
import string

# Severity mapping per warning type
SEVERITY_MAP = {
    'Face Mismatch': 'Critical',
    'Multiple Faces': 'High',
    'Mobile Detected': 'High',
    'Suspicious Activity': 'High',
    'Looking Away': 'Medium',
    'Head Turned': 'Medium',
    'Eye Off Screen': 'Medium',
    'Voice Detected': 'Low',
}

def process_alert(session_id: int, warning_type: str, severity: str = None, snapshot_b64: str = None) -> dict:
    """Process and store a proctoring alert."""
    conn = get_db_connection()
    try:
        session = conn.execute(
            "SELECT * FROM exam_sessions WHERE id=?", (session_id,)
        ).fetchone()
        if not session:
            return {'success': False, 'message': 'Session not found'}

        # Auto-determine severity
        if not severity:
            severity = SEVERITY_MAP.get(warning_type, 'Medium')

        warning_id = 'WRN' + ''.join(random.choices(string.digits, k=6))

        # Save snapshot if provided
        snapshot_path = None
        if snapshot_b64:
            import base64, os
            snap_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'snapshots')
            os.makedirs(snap_dir, exist_ok=True)
            filename = f"{warning_id}.jpg"
            try:
                img_data = base64.b64decode(snapshot_b64.split(',')[-1])
                with open(os.path.join(snap_dir, filename), 'wb') as f:
                    f.write(img_data)
                snapshot_path = filename
            except:
                pass

        conn.execute("""
            INSERT INTO warnings (warning_id, session_id, student_id, exam_id, warning_type, severity, snapshot_path, action_taken)
            VALUES (?,?,?,?,?,?,?,?)
        """, (
            warning_id, session_id, session['student_id'], session['exam_id'],
            warning_type, severity, snapshot_path,
            'Warning issued' if severity != 'Critical' else 'Exam flagged for review'
        ))

        # Update warning count in session
        conn.execute(
            "UPDATE exam_sessions SET total_warnings = total_warnings + 1 WHERE id=?",
            (session_id,)
        )

        # Auto-terminate if critical (Face Mismatch) or >5 warnings
        new_count = session['total_warnings'] + 1
        terminated = False
        if severity == 'Critical' or new_count >= 5:
            conn.execute(
                "UPDATE exam_sessions SET status='terminated', submitted_at=? WHERE id=?",
                (datetime.utcnow(), session_id)
            )
            terminated = True

        conn.commit()

        return {
            'success': True,
            'warning_id': warning_id,
            'severity': severity,
            'terminated': terminated,
            'warning_count': new_count,
            'message': 'Exam terminated due to violations' if terminated else 'Warning logged'
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}
    finally:
        conn.close()

def get_session_alerts(session_id: int) -> dict:
    """Get all alerts for a session."""
    conn = get_db_connection()
    try:
        alerts = conn.execute(
            "SELECT * FROM warnings WHERE session_id=? ORDER BY timestamp DESC",
            (session_id,)
        ).fetchall()
        return {'success': True, 'alerts': [dict(a) for a in alerts], 'count': len(alerts)}
    finally:
        conn.close()
