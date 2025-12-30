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
    # Heroku PostgreSQL
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL').replace("postgres://", "postgresql://", 1)
else:
    # Local development
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///legaldocs.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# Initialize extensions
db = SQLAlchemy(app)
CORS(app)

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

class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    case_title = db.Column(db.String(200), nullable=False)
    case_focus = db.Column(db.String(100))
    legal_domain = db.Column(db.String(50), default='FAMILY_LAW')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timeline_events = db.relationship('TimelineEvent', backref='case', lazy=True, cascade='all, delete-orphan')
    documents = db.relationship('Document', backref='case', lazy=True, cascade='all, delete-orphan')

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
        return render_template('index.html')
    except Exception as e:
        logger.error(f"Error rendering index: {str(e)}")
        return "Internal Server Error", 500

@app.route('/dashboard')
def dashboard():
    try:
        if 'user_id' not in session:
            return redirect(url_for('index'))
        
        user = User.query.get(session['user_id'])
        if not user:
            session.pop('user_id', None)
            return redirect(url_for('index'))
        
        cases = Case.query.filter_by(user_id=user.id).all()
        
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
        logger.info(f"User registered: {email}")
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
            logger.info(f"User logged in: {email}")
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

@app.route('/api/case', methods=['POST'])
def create_case():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        case_title = data.get('case_title', '').strip()
        case_focus = data.get('case_focus', 'CUSTODY_PARENTING')
        
        if not case_title:
            return jsonify({'error': 'Case title is required'}), 400
        
        case = Case(
            user_id=session['user_id'],
            case_title=case_title,
            case_focus=case_focus,
            legal_domain='FAMILY_LAW'
        )
        
        db.session.add(case)
        db.session.commit()
        
        logger.info(f"Case created: {case_title} by user {session['user_id']}")
        return jsonify({'success': True, 'case_id': case.id})
        
    except Exception as e:
        logger.error(f"Case creation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Case creation failed'}), 500

@app.route('/api/timeline_event', methods=['POST'])
def create_timeline_event():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        case_id = data.get('case_id')
        event_date_str = data.get('event_date')
        event_title = data.get('event_title', '').strip()
        
        if not case_id or not event_date_str or not event_title:
            return jsonify({'error': 'Case ID, event date, and event title are required'}), 400
        
        # Parse date
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Verify case exists and belongs to user
        case = Case.query.get(case_id)
        if not case or case.user_id != session['user_id']:
            return jsonify({'error': 'Case not found or access denied'}), 404
        
        event = TimelineEvent(
            case_id=case_id,
            event_date=event_date,
            event_title=event_title,
            event_description=data.get('event_description', '').strip(),
            category=data.get('category', 'PARENTING_TIME'),
            evidence_type=data.get('evidence_type', ''),
            impact_level=data.get('impact_level', 'medium'),
            witness_present=data.get('witness_present', False),
            police_called=data.get('police_called', False)
        )
        
        db.session.add(event)
        db.session.commit()
        
        logger.info(f"Timeline event created: {event_title} for case {case_id}")
        return jsonify({'success': True, 'event_id': event.id})
        
    except Exception as e:
        logger.error(f"Timeline event creation error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Timeline event creation failed'}), 500

@app.route('/api/timeline_events/<int:case_id>')
def get_timeline_events(case_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        # Verify case exists and belongs to user
        case = Case.query.get(case_id)
        if not case or case.user_id != session['user_id']:
            return jsonify({'error': 'Case not found or access denied'}), 404
        
        events = TimelineEvent.query.filter_by(case_id=case_id).order_by(TimelineEvent.event_date).all()
        
        events_data = []
        for event in events:
            events_data.append({
                'id': event.id,
                'event_date': event.event_date.isoformat(),
                'event_title': event.event_title,
                'event_description': event.event_description,
                'category': event.category,
                'evidence_type': event.evidence_type,
                'impact_level': event.impact_level,
                'witness_present': event.witness_present,
                'police_called': event.police_called,
                'created_at': event.created_at.isoformat()
            })
        
        return jsonify(events_data)
        
    except Exception as e:
        logger.error(f"Get timeline events error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve timeline events'}), 500

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
