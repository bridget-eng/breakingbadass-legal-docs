import os
import json
import logging
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
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
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initialize extensions
db = SQLAlchemy(app)
CORS(app, supports_credentials=True)
csrf = CSRFProtect(app)

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
            events = TimelineEvent.query.filter_by(case_id
