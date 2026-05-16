"""
app.py - Main Flask Application Entry Point
AIOEPS - AI Based Online Examination Proctoring System
============================================================
Run: python app.py
API Base URL: http://localhost:5000/api
============================================================
"""

import os
import sys

# ─── Add backend directory to path ───────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from database.db import init_db

# ─── Import Route Blueprints ──────────────────────────────────────────────────
from routes.auth_routes    import auth_bp
from routes.student_routes import student_bp
from routes.admin_routes   import admin_bp
from routes.proctor_routes import proctor_bp

def create_app():
    """Application Factory."""
    app = Flask(__name__, static_folder='../frontend', static_url_path='')

    # ─── Load Config ─────────────────────────────────────────────────────────
    app.config.from_object(Config)

    # ─── Extensions ──────────────────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    JWTManager(app)

    # ─── Initialize Database ─────────────────────────────────────────────────
    with app.app_context():
        init_db(app)

    # ─── Register Blueprints ──────────────────────────────────────────────────
    app.register_blueprint(auth_bp,    url_prefix='/api/auth')
    app.register_blueprint(student_bp, url_prefix='/api/student')
    app.register_blueprint(admin_bp,   url_prefix='/api/admin')
    app.register_blueprint(proctor_bp, url_prefix='/api/proctor')

    # ─── Serve Frontend Pages ─────────────────────────────────────────────────
    @app.route('/')
    def index():
        return send_from_directory('../frontend', 'index.html')

    @app.route('/student/<path:filename>')
    def student_page(filename):
        return send_from_directory('../frontend/student', filename)

    @app.route('/admin/<path:filename>')
    def admin_page(filename):
        return send_from_directory('../frontend/admin', filename)

    # ─── Health Check ─────────────────────────────────────────────────────────
    @app.route('/api/health')
    def health():
        return jsonify({
            'status': 'ok',
            'system': 'AIOEPS',
            'version': '1.0.0',
            'message': 'AI Based Online Examination Proctoring System is running'
        })

    # ─── Report Download ──────────────────────────────────────────────────────
    @app.route('/api/admin/download-report', methods=['GET'])
    def download_report():
        from flask_jwt_extended import jwt_required, get_jwt_identity
        from services.report_service import generate_exam_report
        from flask import send_file
        result = generate_exam_report()
        if result['success']:
            return send_file(result['path'], as_attachment=True, download_name=result['filename'])
        return jsonify(result), 500

    # ─── 404 Handler ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({'error': 'Endpoint not found', 'status': 404}), 404

    # ─── 500 Handler ─────────────────────────────────────────────────────────
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({'error': 'Internal server error', 'status': 500}), 500

    return app

# ─── Entry Point ──────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app = create_app()
    print("\n" + "="*60)
    print("  🛡️  AIOEPS - AI Proctoring System")
    print("  🌐  http://localhost:5000")
    print("  📋  API: http://localhost:5000/api/health")
    print("="*60 + "\n")
    app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=Config.DEBUG
    )
