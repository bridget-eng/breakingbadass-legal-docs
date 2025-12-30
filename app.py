import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///legaldocs.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

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
    case_focus = db.Column(db.String(100))  # Changed from case_type to case_focus
    legal_domain = db.Column(db.String(50), default='FAMILY_LAW')  # Added for backend categorization
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    timeline_events = db.relationship('TimelineEvent', backref='case', lazy=True)
    documents = db.relationship('Document', backref='case', lazy=True)

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
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    user = User.query.get(session['user_id'])
    cases = Case.query.filter_by(user_id=user.id).all()
    
    # Get recent timeline events
    recent_events = []
    for case in cases:
        events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date.desc()).limit(5).all()
        recent_events.extend(events)
    
    recent_events.sort(key=lambda x: x.event_date, reverse=True)
    
    return render_template('dashboard.html', user=user, cases=cases, recent_events=recent_events[:5])

@app.route('/timeline/<int:case_id>')
def timeline(case_id):
    if 'user_id' not in session:
        return redirect(url_for('index'))
    
    case = Case.query.get_or_404(case_id)
    events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date).all()
    
    return render_template('timeline.html', case=case, events=events)

@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    first_name = data.get('first_name', '')
    last_name = data.get('last_name', '')
    
    if User.query.filter_by(email=email).first():
        return jsonify({'error': 'User already exists'}), 400
    
    user = User(
        email=email,
        password_hash=generate_password_hash(password),
        first_name=first_name,
        last_name=last_name
    )
    
    db.session.add(user)
    db.session.commit()
    
    session['user_id'] = user.id
    return jsonify({'success': True, 'user_id': user.id})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if user and check_password_hash(user.password_hash, password):
        session['user_id'] = user.id
        return jsonify({'success': True, 'user_id': user.id})
    
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'success': True})

@app.route('/api/case', methods=['POST'])
def create_case():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    case = Case(
        user_id=session['user_id'],
        case_title=data.get('case_title'),
        case_focus=data.get('case_type', 'CUSTODY_PARENTING'),  # Using case_focus field
        legal_domain='FAMILY_LAW'  # Backend categorization
    )
    
    db.session.add(case)
    db.session.commit()
    
    return jsonify({'success': True, 'case_id': case.id})

@app.route('/api/timeline_event', methods=['POST'])
def create_timeline_event():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    event_date = datetime.strptime(data.get('event_date'), '%Y-%m-%d').date()
    
    event = TimelineEvent(
        case_id=data.get('case_id'),
        event_date=event_date,
        event_title=data.get('event_title'),
        event_description=data.get('event_description', ''),
        category=data.get('category', 'PARENTING_TIME'),
        evidence_type=data.get('evidence_type', ''),
        impact_level=data.get('impact_level', 'medium'),
        witness_present=data.get('witness_present', False),
        police_called=data.get('police_called', False)
    )
    
    db.session.add(event)
    db.session.commit()
    
    return jsonify({'success': True, 'event_id': event.id})

@app.route('/api/timeline_events/<int:case_id>')
def get_timeline_events(case_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
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
            'police_called': event.police_called
        })
    
    return jsonify(events_data)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
    @app.route('/api/export/<int:case_id>')
def export_case(case_id):
    case = Case.query.get_or_404(case_id)
    events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date).all()
    
    # Generate professional court-ready document
    export_data = {
        'case_title': case.case_title,
        'case_focus': case.case_focus,
        'events': [],
        'summary': generate_case_summary(events),
        'pattern_analysis': analyze_patterns(events),
        'evidence_summary': summarize_evidence(events)
    }
    
    for event in events:
        export_data['events'].append({
            'date': event.event_date.strftime('%B %d, %Y'),
n            'title': event.event_title,
            'description': event.event_description,
            'category': get_category_label(event.category),
            'impact': event.impact_level,
            'evidence': event.evidence_type,
            'witness': 'Yes' if event.witness_present else 'No',
            'police': 'Yes' if event.police_called else 'No'
        })
    
    return jsonify(export_data)
