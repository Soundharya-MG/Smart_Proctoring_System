"""
exam_service.py - Exam Logic Service
AIOEPS v8
- Result = score only (AI warnings do NOT affect pass/fail)
- Auto plagiarism check on submission (cross-student + reference)
- All sqlite3.Row objects converted to dict to prevent .get() errors
"""

from database.db import get_db_connection
from datetime import datetime
from services.plagiarism_service import (
    compute_plagiarism_full, get_references_for_question, is_coding_question
)

def start_exam_session(student_id: int, exam_id: str, ip_address: str = None) -> dict:
    """Create a new exam session."""
    conn = get_db_connection()
    try:
        exam = conn.execute("SELECT * FROM exams WHERE exam_id=?", (exam_id,)).fetchone()
        if not exam:
            return {'success': False, 'message': 'Exam not found'}
        exam = dict(exam)

        existing = conn.execute(
            "SELECT id FROM exam_sessions WHERE student_id=? AND exam_id=? AND status='active'",
            (student_id, exam['id'])
        ).fetchone()

        if existing:
            return {'success': True, 'session_id': existing['id'], 'message': 'Session resumed', 'resumed': True}

        conn.execute(
            "INSERT INTO exam_sessions (student_id, exam_id, ip_address, face_verified) VALUES (?,?,?,?)",
            (student_id, exam['id'], ip_address, 1)
        )
        conn.commit()

        session = conn.execute(
            "SELECT id FROM exam_sessions WHERE student_id=? AND exam_id=? AND status='active' ORDER BY started_at DESC",
            (student_id, exam['id'])
        ).fetchone()

        return {'success': True, 'session_id': session['id'], 'exam': exam, 'message': 'Session started'}
    except Exception as e:
        return {'success': False, 'message': str(e)}
    finally:
        conn.close()

def submit_exam(session_id: int, student_id: int, answers: dict) -> dict:
    """
    Score and submit exam.
    - Result is based ONLY on correct answers vs pass_marks
    - AI warnings do NOT affect result
    - Auto plagiarism runs for all coding answers
    """
    conn = get_db_connection()
    try:
        session_row = conn.execute(
            "SELECT * FROM exam_sessions WHERE id=? AND student_id=?", (session_id, student_id)
        ).fetchone()
        if not session_row:
            return {'success': False, 'message': 'Session not found'}
        session = dict(session_row)

        exam_row = conn.execute("SELECT * FROM exams WHERE id=?", (session['exam_id'],)).fetchone()
        if not exam_row:
            return {'success': False, 'message': 'Exam not found'}
        exam = dict(exam_row)

        question_rows = conn.execute(
            "SELECT * FROM questions WHERE exam_id=?", (exam['id'],)
        ).fetchall()
        questions = [dict(q) for q in question_rows]

        total_marks    = 0
        obtained_marks = 0
        plagiarism_results = {}

        for q in questions:
            total_marks += q['marks']
            student_ans  = answers.get(str(q['id']), '') or ''
            is_correct   = False

            if q['question_type'] == 'MCQ':
                is_correct = (student_ans.strip().upper() == (q.get('correct_answer') or '').strip().upper())
            elif q['question_type'] == 'Coding' and student_ans and student_ans.strip():
                is_correct = True

            marks = q['marks'] if is_correct else 0
            obtained_marks += marks

            # ── AUTO PLAGIARISM CHECK for coding questions ──────────────────
            if is_coding_question(q['question_type']) and student_ans and student_ans.strip():
                try:
                    plag_result = compute_plagiarism_full(
                        answer=student_ans,
                        question_id=q['id'],
                        student_id=student_id,
                        question_text=q.get('question_text') or '',
                        session_id=session_id
                    )
                    # Ensure plag_result is a plain dict
                    if not isinstance(plag_result, dict):
                        plag_result = {'score': 0, 'level': 'Normal'}
                    plagiarism_results[str(q['id'])] = plag_result

                    try:
                        conn.execute("""
                            INSERT OR REPLACE INTO plagiarism_results
                                (session_id, question_id, student_id, score, level, matched_with, details, checked_at)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (
                            session_id, q['id'], student_id,
                            float(plag_result.get('score', 0)),
                            str(plag_result.get('level', 'Normal')),
                            str(plag_result.get('matched_with', '')),
                            str(plag_result.get('details', '')),
                            datetime.utcnow()
                        ))
                    except Exception:
                        pass
                except Exception:
                    pass  # Plagiarism check failed gracefully

            # Save answer
            conn.execute("""
                INSERT OR REPLACE INTO answers
                    (session_id, question_id, student_answer, is_correct, marks_obtained, answered_at)
                VALUES (?,?,?,?,?,?)
            """, (session_id, q['id'], student_ans, int(is_correct), marks, datetime.utcnow()))

        percentage = round((obtained_marks / total_marks * 100), 2) if total_marks > 0 else 0

        # ── RESULT BASED ON SCORE ONLY — warnings do NOT affect pass/fail ──
        result = 'Pass' if obtained_marks >= exam['pass_marks'] else 'Fail'

        conn.execute("""
            UPDATE exam_sessions
            SET status='submitted', submitted_at=?, score=?, percentage=?, result=?
            WHERE id=?
        """, (datetime.utcnow(), obtained_marks, percentage, result, session_id))
        conn.commit()

        warnings_row = conn.execute(
            "SELECT total_warnings FROM exam_sessions WHERE id=?", (session_id,)
        ).fetchone()
        warnings_count = int(warnings_row['total_warnings']) if warnings_row else 0

        return {
            'success': True,
            'submitted': True,
            'message': 'Your exam has been submitted successfully.',
            'admin': {
                'score': obtained_marks,
                'total': total_marks,
                'percentage': percentage,
                'result': result,
                'pass_marks': exam['pass_marks'],
                'warnings': warnings_count,
                'plagiarism_results': plagiarism_results,
            }
        }
    except Exception as e:
        return {'success': False, 'message': str(e)}
    finally:
        conn.close()

def get_exam_result(session_id: int, student_id: int) -> dict:
    """Get detailed exam result."""
    conn = get_db_connection()
    try:
        session_row = conn.execute(
            """SELECT es.*, e.title, e.subject, e.total_marks, e.pass_marks
               FROM exam_sessions es
               JOIN exams e ON es.exam_id=e.id
               WHERE es.id=? AND es.student_id=?""",
            (session_id, student_id)
        ).fetchone()
        if not session_row:
            return {'success': False, 'message': 'Result not found'}
        session = dict(session_row)

        warning_rows = conn.execute(
            "SELECT * FROM warnings WHERE session_id=? ORDER BY timestamp", (session_id,)
        ).fetchall()
        warnings = [dict(w) for w in warning_rows]

        try:
            plag_rows = conn.execute(
                "SELECT * FROM plagiarism_results WHERE session_id=?", (session_id,)
            ).fetchall()
            plag_data = [dict(p) for p in plag_rows]
        except Exception:
            plag_data = []

        return {
            'success': True,
            'result': session,
            'warnings': warnings,
            'warning_count': len(warnings),
            'plagiarism': plag_data
        }
    finally:
        conn.close()
