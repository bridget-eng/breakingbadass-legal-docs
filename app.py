import os
import json
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import uuid

# Configure logging for production
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Production-ready configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# Database configuration - Heroku compatible
if os.environ.get('DATABASE_URL'):
    # Heroku PostgreSQL - fix the postgres:// to postgresql://
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
    logger.info("Using PostgreSQL database")
else:
    # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///legaldocs.db'
    logger.info("Using SQLite database")

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = False  # Disable for API endpoints
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    subscription_tier = db.Column(db.String(20), default='basic')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    cases = db.relationship('Case', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    case_title = db.Column(db.String(200), nullable=False)
    case_focus = db.Column(db.String(100))
    legal_domain = db.Column(db.String(50), default='FAMILY_LAW')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timeline_events = db.relationship('TimelineEvent', backref='case', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='case', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Case {self.case_title}>'

class TimelineEvent(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    event_time = db.Column(db.Time)
    event_title = db.Column(db.String(200), nullable=False)
    event_description = db.Column(db.Text)
    category = db.Column(db.String(50))
    evidence_type = db.Column(db.String(100))
    impact_level = db.Column(db.String(20))
    witness_present = db.Column(db.Boolean, default=False)
    police_called = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255))
    document_type = db.Column(db.String(50))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    file_size = db.Column(db.Integer)
    evidence_category = db.Column(db.String(100))

# Routes
@app.route('/')
def index():
    try:
        # If user is already logged in, redirect to dashboard
        if 'user_id' in session:
            return redirect(url_for('dashboard'))
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return "Internal Server Error", 500

@app.route('/dashboard')
def dashboard():
    try:
        logger.info(f"Dashboard accessed - Session user_id: {session.get('user_id')}")
        
        if 'user_id' not in session:
            logger.info("No user_id in session, redirecting to index")
            return redirect(url_for('index'))
        
        user = User.query.get(session['user_id'])
        if not user:
            logger.info(f"User not found with id {session['user_id']}, clearing session")
            session.pop('user_id', None)
            return redirect(url_for('index'))
        
        cases = Case.query.filter_by(user_id=user.id).all()
        logger.info(f"Found {len(cases)} cases for user {user.email}")
        
        # Get recent timeline events
        recent_events = []
        for case in cases:
            events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date.desc()).limit(5).all()
            recent_events.extend(events)
        
        recent_events.sort(key=lambda x: x.event_date, reverse=True)
        
        return render_template('dashboard.html', user=user, cases=cases, recent_events=recent_events[:5])
    except Exception as e:
        logger.error(f"Error rendering dashboard: {str(e)}")
        return "Internal Server Error", 500

@app.route('/timeline/<int:case_id>')
def timeline(case_id):
    try:
        if 'user_id' not in session:
            return redirect(url_for('index'))
        
        case = Case.query.get_or_404(case_id)
        
        # Verify user owns this case
        if case.user_id != session['user_id']:
            return redirect(url_for('dashboard'))
        
        events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date).all()
        
        return render_template('timeline.html', case=case, events=events)
    except Exception as e:
        logger.error(f"Error rendering timeline: {str(e)}")
        return "Internal Server Error", 500

# API Routes
@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Check if user exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'User already exists'}), 400
        
        # Create user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name
        )
        
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        logger.info(f"User registered and logged in: {email}, session user_id: {user.id}")
        return jsonify({'success': True, 'user_id': user.id})
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Registration failed'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            logger.info(f"User logged in: {email}, session user_id: {user.id}")
            return jsonify({'success': True, 'user_id': user.id})
        
        return jsonify({'error': 'Invalid credentials'}), 401
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/logout', methods=['POST'])
def logout():
    try:
        session.pop('user_id', None)
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('index.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return "Internal Server Error", 500

# Health check endpoint for Heroku
@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.utcnow().isoformat()}), 200

# Production entry point
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    
    # Initialize database
    with app.app_context():
        try:
            db.create_all()
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
    
    app.run(debug=debug, host='0.0.0.0', port=port)
