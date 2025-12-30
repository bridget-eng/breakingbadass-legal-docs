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
    communications = db.relationship('Communication', backref='user', lazy=True)

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

# NEW: Communication Model for Documentation
class Communication(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    time = db.Column(db.Time, nullable=False)
    platform = db.Column(db.String(50), nullable=False)
    sender = db.Column(db.String(100), nullable=False)
    recipient = db.Column(db.String(100), nullable=False)
    message_content = db.Column(db.Text, nullable=False)
    neutral_summary = db.Column(db.Text, nullable=False)
    evidence_type = db.Column(db.String(50))
    evidence_summary = db.Column(db.Text)
    court_order_relevance = db.Column(db.Boolean, default=False)
    missed_exchange_reference = db.Column(db.Boolean, default=False)
    refusal_to_provide_info = db.Column(db.Boolean, default=False)
    inappropriate_tone = db.Column(db.Boolean, default=False)
    marking = db.Column(db.String(20), default='documentation')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
        
        # Get user with error handling
        try:
            user = User.query.get(session['user_id'])
        except Exception as e:
            logger.error(f"Database error getting user: {str(e)}")
            session.pop('user_id', None)
            return redirect(url_for('index'))
        
        if not user:
            logger.info(f"User not found with id {session['user_id']}, clearing session")
            session.pop('user_id', None)
            return redirect(url_for('index'))
        
        # Get cases with error handling
        try:
            cases = Case.query.filter_by(user_id=user.id).all()
            logger.info(f"Found {len(cases)} cases for user {user.email}")
        except Exception as e:
            logger.error(f"Database error getting cases: {str(e)}")
            cases = []
        
        # Get recent timeline events
        recent_events = []
        try:
            for case in cases:
                events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date.desc()).limit(5).all()
                recent_events.extend(events)
            recent_events.sort(key=lambda x: x.event_date, reverse=True)
            logger.info(f"Found {len(recent_events)} recent events")
        except Exception as e:
            logger.error(f"Database error getting timeline events: {str(e)}")
            recent_events = []
        
        return render_template('dashboard.html', user=user, cases=cases, recent_events=recent_events[:5])
    except Exception as e:
        logger.error(f"Critical error in dashboard: {str(e)}")
        return "Dashboard temporarily unavailable. Please try again.", 500

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

# Communication Log Routes
@app.route('/api/communication', methods=['POST'])
def add_communication():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Create communication entry
        communication = Communication(
            user_id=session['user_id'],
            date=datetime.strptime(data.get('date'), '%Y-%m-%d').date(),
            time=datetime.strptime(data.get('time'), '%H:%M').time(),
            platform=data.get('platform'),
            sender=data.get('sender'),
            recipient=data.get('recipient'),
            message_content=data.get('messageContent'),
            neutral_summary=data.get('neutralSummary'),
            evidence_type=data.get('evidenceType'),
            evidence_summary=data.get('evidenceSummary'),
            court_order_relevance=data.get('courtOrderRelevance', False),
            missed_exchange_reference=data.get('missedExchangeReference', False),
            refusal_to_provide_info=data.get('refusalToProvideInfo', False),
            inappropriate_tone=data.get('inappropriateTone', False),
            marking=data.get('marking', 'documentation')
        )
        
        db.session.add(communication)
        db.session.commit()
        
        return jsonify({'success': True, 'communication_id': communication.id})
        
    except Exception as e:
        logger.error(f"Communication error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Communication entry failed'}), 500

@app.route('/api/communications')
def get_communications():
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        communications = Communication.query.filter_by(user_id=session['user_id']).order_by(Communication.date.desc()).all()
        
        communications_data = []
        for comm in communications:
            communications_data.append({
                'id': comm.id,
                'date': comm.date.isoformat(),
                'time': comm.time.strftime('%H:%M'),
                'platform': comm.platform,
                'sender': comm.sender,
                'recipient': comm.recipient,
                'message_content': comm.message_content,
                'neutral_summary': comm.neutral_summary,
                'evidence_type': comm.evidence_type,
                'evidence_summary': comm.evidence_summary,
                'court_order_relevance': comm.court_order_relevance,
                'missed_exchange_reference': comm.missed_exchange_reference,
                'refusal_to_provide_info': comm.refusal_to_provide_info,
                'inappropriate_tone': comm.inappropriate_tone,
                'marking': comm.marking,
                'created_at': comm.created_at.isoformat()
            })
        
        return jsonify(communications_data)
        
    except Exception as e:
        logger.error(f"Get communications error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve communications'}), 500

@app.route('/api/communication/<int:comm_id>', methods=['DELETE'])
def delete_communication(comm_id):
    try:
        if 'user_id' not in session:
            return jsonify({'error': 'Not authenticated'}), 401
        
        communication = Communication.query.get_or_404(comm_id)
        
        # Verify user owns this communication
        if communication.user_id != session['user_id']:
            return jsonify({'error': 'Access denied'}), 403
        
        db.session.delete(communication)
        db.session.commit()
        
        return jsonify({'success': True})
        
    except Exception as e:
        logger.error(f"Delete communication error: {str(e)}")
        return jsonify({'error': 'Delete failed'}), 500

# Page Routes for New Features
@app.route('/communication-log')
def communication_log():
    try:
        if 'user_id' not in session:
            return redirect(url_for('index'))
        
        return render_template('communication_log.html')
    except Exception as e:
        logger.error(f"Error rendering communication log: {str(e)}")
        return "Internal Server Error", 500

@app.route('/timeline-event')
def timeline_event_form():
    try:
        if 'user_id' not in session:
            return redirect(url_for('index'))
        
        return render_template('timeline_event_form.html')
    except Exception as e:
        logger.error(f"Error rendering timeline event form: {str(e)}")
        return "Internal Server Error", 500

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
