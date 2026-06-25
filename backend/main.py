import os
from flask import Flask, request, jsonify, send_from_directory, session
from werkzeug.security import generate_password_hash, check_password_hash

from logs import setup_logging
from db import init_db, create_user, get_user_by_email, get_user_by_id, create_checkin, get_checkins, get_checkin_count, seed_demo_data
from processor import parse_symptoms, calculate_overall_severity, detect_mood
from ai_summary import generate_clinical_summary
from formatter import format_dashboard_data

logger = setup_logging()

app = Flask(__name__)
app.secret_key = 'healthsync-ai-fixed-secret-key'

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'frontend')


# ── Page routes ──

@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/login')
def login_page():
    return send_from_directory(FRONTEND_DIR, 'login.html')


@app.route('/register')
def register_page():
    return send_from_directory(FRONTEND_DIR, 'register.html')


@app.route('/dashboard')
def dashboard_page():
    return send_from_directory(FRONTEND_DIR, 'dashboard.html')


@app.route('/style.css')
def css():
    return send_from_directory(FRONTEND_DIR, 'style.css')


@app.route('/script.js')
def js():
    return send_from_directory(FRONTEND_DIR, 'script.js')


# ── Auth API ──

@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    full_name = (data.get('full_name') or '').strip()
    username = (data.get('username') or '').strip()

    if not all([email, password, full_name, username]):
        return jsonify({'error': 'All fields are required'}), 400

    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    password_hash = generate_password_hash(password)
    user_id = create_user(username, email, password_hash, full_name)

    if user_id is None:
        return jsonify({'error': 'Email or username already exists'}), 409

    logger.info(f"New user registered: {email}")
    return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201


@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not all([email, password]):
        return jsonify({'error': 'Email and password required'}), 400

    user = get_user_by_email(email)
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user['id']
    session['user_email'] = user['email']

    logger.info(f"User logged in: {email}")
    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'name': user['full_name'],
            'email': user['email']
        }
    }), 200


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'message': 'Logged out'}), 200


@app.route('/api/me', methods=['GET'])
def api_me():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 401

    return jsonify({'user': user}), 200


# ── Checkin API ──

@app.route('/api/checkin', methods=['POST'])
def api_checkin():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    symptoms_text = (data.get('symptoms') or '').strip()
    if not symptoms_text:
        return jsonify({'error': 'Please describe your symptoms'}), 400

    mood = data.get('mood') or 'okay'
    medications = (data.get('medications') or '').strip()
    notes = (data.get('notes') or '').strip()

    symptoms = parse_symptoms(symptoms_text)
    severity = calculate_overall_severity(symptoms)
    health_score = (10 - severity) * 10

    checkin_id = create_checkin(user_id, symptoms_text, symptoms, severity, health_score, mood, medications, notes)

    logger.info(f"New checkin #{checkin_id} for user {user_id}, severity={severity}")
    return jsonify({
        'message': 'Check-in recorded',
        'checkin_id': checkin_id,
        'severity': severity,
        'health_score': health_score,
        'symptoms': symptoms
    }), 201


# ── Dashboard API ──

@app.route('/api/dashboard', methods=['GET'])
def api_dashboard():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    user = get_user_by_id(user_id)
    if not user:
        session.clear()
        return jsonify({'error': 'User not found'}), 401

    checkins = get_checkins(user_id, limit=30)
    total = get_checkin_count(user_id)
    user['total_checkins'] = total

    # Get or generate summary without duplicating
    summary = None
    if len(checkins) >= 2:
        from db import get_latest_summary
        summary = get_latest_summary(user_id)
        if not summary:
            summary = generate_clinical_summary(user_id)
        else:
            summary = dict(summary)
    elif len(checkins) == 1:
        summary = {
            'text': "Not enough data for a full clinical summary. At least 2 check-ins are required for trend analysis.",
            'trend': 'stable', 'trend_percent': 0,
            'total_checkins': 1,
            'period_start': checkins[0]['created_at'][:10],
            'period_end': checkins[0]['created_at'][:10]
        }
    else:
        summary = {
            'text': "No check-in data yet. Submit your first check-in to begin tracking.",
            'trend': 'stable', 'trend_percent': 0,
            'total_checkins': 0, 'period_start': '', 'period_end': ''
        }

    dashboard = format_dashboard_data(user, checkins, summary)
    return jsonify(dashboard), 200


# ── Seed route ──

@app.route('/api/seed', methods=['POST'])
def api_seed():
    result = seed_demo_data()
    if result:
        return jsonify({'message': 'Demo data seeded successfully. Login with sarah@healthsync.ai / patient123'}), 201
    return jsonify({'message': 'Demo data already exists'}), 200


# ── Init & Run ──

if __name__ == '__main__':
    init_db()
    seed_demo_data()
    logger.info("HealthSync AI starting on http://localhost:5000")
    app.run(debug=True, port=5000)