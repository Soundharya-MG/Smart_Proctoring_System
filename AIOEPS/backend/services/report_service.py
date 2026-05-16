"""
report_service.py - PDF Report Generation Service
AIOEPS - AI Based Online Examination Proctoring System
"""

import os
from datetime import datetime
from database.db import get_db_connection

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

REPORTS_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads', 'reports')

def generate_exam_report(exam_id: str = None, date_str: str = None) -> dict:
    """Generate a PDF summary report of exam results & warnings."""
    os.makedirs(REPORTS_DIR, exist_ok=True)
    conn = get_db_connection()

    try:
        # Gather stats
        total_students = conn.execute("SELECT COUNT(*) FROM users WHERE role='student'").fetchone()[0]
        total_warnings = conn.execute("SELECT COUNT(*) FROM warnings").fetchone()[0]
        total_sessions = conn.execute("SELECT COUNT(*) FROM exam_sessions").fetchone()[0]
        passed = conn.execute("SELECT COUNT(*) FROM exam_sessions WHERE result='Pass'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM exam_sessions WHERE result='Fail'").fetchone()[0]

        results = conn.execute("""
            SELECT u.name, u.student_id, e.title, es.score, es.percentage, es.result,
                   es.total_warnings, es.submitted_at
            FROM exam_sessions es
            JOIN users u ON es.student_id = u.id
            JOIN exams e ON es.exam_id = e.id
            WHERE es.status IN ('submitted','terminated')
            ORDER BY es.submitted_at DESC LIMIT 50
        """).fetchall()

        warnings = conn.execute("""
            SELECT w.warning_type, COUNT(*) as cnt
            FROM warnings w GROUP BY w.warning_type ORDER BY cnt DESC
        """).fetchall()

        filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        filepath = os.path.join(REPORTS_DIR, filename)

        if REPORTLAB_AVAILABLE:
            _build_pdf(filepath, total_students, total_warnings, total_sessions,
                       passed, failed, results, warnings)
        else:
            # Fallback: generate plain text report
            _build_text_report(filepath.replace('.pdf', '.txt'),
                               total_students, total_warnings, total_sessions,
                               passed, failed, results, warnings)
            filename = filename.replace('.pdf', '.txt')

        return {'success': True, 'filename': filename, 'path': filepath}

    except Exception as e:
        return {'success': False, 'message': str(e)}
    finally:
        conn.close()

def _build_pdf(filepath, total_students, total_warnings, total_sessions,
               passed, failed, results, warnings):
    """Build PDF using ReportLab."""
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle('Title', parent=styles['Title'],
                                 fontSize=20, textColor=colors.HexColor('#6C63FF'),
                                 spaceAfter=6)
    story.append(Paragraph("AIOEPS - Exam Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}", styles['Normal']))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#6C63FF')))
    story.append(Spacer(1, 0.5*cm))

    # Summary stats
    summary_data = [
        ['Metric', 'Value'],
        ['Total Students', str(total_students)],
        ['Total Sessions', str(total_sessions)],
        ['Passed', str(passed)],
        ['Failed', str(failed)],
        ['Total Warnings', str(total_warnings)],
    ]
    t = Table(summary_data, colWidths=[8*cm, 8*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6C63FF')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F8F9FA'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.8*cm))

    # Results table
    story.append(Paragraph("Student Results", styles['Heading2']))
    story.append(Spacer(1, 0.3*cm))

    res_data = [['Name', 'Student ID', 'Exam', 'Score', '%', 'Result', 'Warnings']]
    for r in results:
        res_data.append([
            r['name'], r['student_id'], r['title'][:20],
            str(r['score']), f"{r['percentage']}%", r['result'] or '-',
            str(r['total_warnings'])
        ])

    rt = Table(res_data, colWidths=[3.5*cm, 2.5*cm, 3*cm, 1.5*cm, 1.5*cm, 1.5*cm, 2*cm])
    rt.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E1B4B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#F0EEFF'), colors.white]),
        ('GRID', (0, 0), (-1, -1), 0.3, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(rt)

    doc.build(story)

def _build_text_report(filepath, total_students, total_warnings,
                       total_sessions, passed, failed, results, warnings):
    """Fallback text report when reportlab is unavailable."""
    with open(filepath, 'w') as f:
        f.write("=" * 60 + "\n")
        f.write("AIOEPS - EXAM REPORT\n")
        f.write(f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"Total Students : {total_students}\n")
        f.write(f"Total Sessions : {total_sessions}\n")
        f.write(f"Passed         : {passed}\n")
        f.write(f"Failed         : {failed}\n")
        f.write(f"Total Warnings : {total_warnings}\n\n")
        f.write("-" * 60 + "\nSTUDENT RESULTS\n" + "-" * 60 + "\n")
        for r in results:
            f.write(f"{r['name']} | {r['student_id']} | {r['title']} | "
                    f"Score: {r['score']} | {r['percentage']}% | {r['result']} | "
                    f"Warnings: {r['total_warnings']}\n")
