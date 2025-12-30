import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
from collections import defaultdict
import uuid
import calendar

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
    case_focus = db.Column(db.String(100))
    legal_domain = db.Column(db.String(50), default='FAMILY_LAW')
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
    
    # Calculate professional insights
    insights = calculate_case_insights(cases)
    
    return render_template('dashboard.html', user=user, cases=cases, recent_events=recent_events[:5], insights=insights)

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
n    
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
        case_focus=data.get('case_type', 'CUSTODY_PARENTING'),
        legal_domain='FAMILY_LAW'
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
n    \n    event = TimelineEvent(\n        case_id=data.get('case_id'),\n        event_date=event_date,\n        event_title=data.get('event_title'),\n        event_description=data.get('event_description', ''),\n        category=data.get('category', 'PARENTING_TIME'),\n        evidence_type=data.get('evidence_type', ''),\n        impact_level=data.get('impact_level', 'medium'),\n        witness_present=data.get('witness_present', False),\n        police_called=data.get('police_called', False)\n    )\n    \n    db.session.add(event)\n    db.session.commit()\n    \n    return jsonify({'success': True, 'event_id': event.id})

@app.route('/api/timeline_events/<int:case_id>')
ndef get_timeline_events(case_id):\n    if 'user_id' not in session:\n        return jsonify({'error': 'Not authenticated'}), 401\n    \n    events = TimelineEvent.query.filter_by(case_id=case_id).order_by(TimelineEvent.event_date).all()\n    \n    events_data = []\n    for event in events:\n        events_data.append({\n            'id': event.id,\n            'event_date': event.event_date.isoformat(),\n            'event_title': event.event_title,\n            'event_description': event.event_description,\n            'category': event.category,\n            'evidence_type': event.evidence_type,\n            'impact_level': event.impact_level,\n            'witness_present': event.witness_present,\n            'police_called': event.police_called\n        })\n    \n    return jsonify(events_data)

@app.route('/api/export/<int:case_id>')
def export_case(case_id):
n    if 'user_id' not in session:\n        return jsonify({'error': 'Not authenticated'}), 401\n    \n    case = Case.query.get_or_404(case_id)\n    if case.user_id != session['user_id']:\n        return jsonify({'error': 'Unauthorized'}), 403\n    \n    events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date).all()\n    \n    # Generate professional court-ready document\n    export_data = {\n        'case_title': case.case_title,\n        'case_focus': case.case_focus,\n        'legal_domain': case.legal_domain,\n        'created_date': case.created_at.strftime('%B %d, %Y'),\n        'events': [],\n        'summary': generate_case_summary(events),\n        'pattern_analysis': analyze_patterns(events),\n        'evidence_summary': summarize_evidence(events),\n        'chronology': generate_chronology(events)\n    }\n    \n    for event in events:\n        export_data['events'].append({\n            'date': event.event_date.strftime('%B %d, %Y'),\n            'time': event.event_time.strftime('%I:%M %p') if event.event_time else '',\n            'title': event.event_title,\n            'description': event.event_description,\n            'category': get_category_label(event.category),\n            'impact': event.impact_level,\n            'evidence': event.evidence_type or 'Not specified',\n            'witness': 'Yes' if event.witness_present else 'No',\n            'police': 'Yes' if event.police_called else 'No'\n        })\n    \n    return jsonify(export_data)

# Professional Analysis Functions
def calculate_case_insights(cases):\n    \"\"\"Calculate professional case insights for dashboard\"\"\"\n    insights = {\n        'total_cases': len(cases),\n        'priority_events': 0,\n        'documentation_quality': 'Good',\n        'court_readiness': 'Preparation Phase'\n    }\n    \n    total_events = 0\n    high_impact_events = 0\n    events_with_evidence = 0\n    \n    for case in cases:\n        events = TimelineEvent.query.filter_by(case_id=case.id).all()\n        total_events += len(events)\n        \n        for event in events:\n            if event.impact_level in ['high', 'critical'] or event.police_called:\n                high_impact_events += 1\n            if event.evidence_type:\n                events_with_evidence += 1\n    \n    insights['priority_events'] = high_impact_events\n    \n    # Calculate documentation quality\n    if total_events > 0:\n        evidence_ratio = events_with_evidence / total_events\n        if evidence_ratio > 0.8:\n            insights['documentation_quality'] = 'Excellent'\n        elif evidence_ratio > 0.6:\n            insights['documentation_quality'] = 'Good'\n        elif evidence_ratio > 0.3:\n            insights['documentation_quality'] = 'Fair'\n        else:\n            insights['documentation_quality'] = 'Needs Improvement'\n    \n    # Calculate court readiness\n    if len(cases) > 0 and total_events > 10:\n        insights['court_readiness'] = 'Court Ready'\n    elif len(cases) > 0 and total_events > 5:\n        insights['court_readiness'] = 'Near Ready'\n    \n    return insights\n\ndef generate_case_summary(events):\n    \"\"\"Generate professional paralegal-grade case summary\"\"\"\n    if not events:\n        return {\n            'total_events': 0,\n            'date_range': 'No events recorded',\n            'categories': {},\n            'impact_distribution': {},\n            'key_concerns': [],\n            'recommendations': ['Begin documenting events immediately']\n        }\n    \n    summary = {\n        'total_events': len(events),\n        'date_range': f\"{events[0].event_date.strftime('%B %d, %Y')} to {events[-1].event_date.strftime('%B %d, %Y')}\",\n        'categories': {},\n        'impact_distribution': {},\n        'key_concerns': [],\n        'recommendations': []\n    }\n    \n    for event in events:\n        # Categorize by type\n        category_label = get_category_label(event.category)\n        if category_label not in summary['categories']:\n            summary['categories'][category_label] = 0\n        summary['categories'][category_label] += 1\n        \n        # Impact distribution\n        if event.impact_level not in summary['impact_distribution']:\n            summary['impact_distribution'][event.impact_level] = 0\n        summary['impact_distribution'][event.impact_level] += 1\n        \n        # Key concerns (high impact, police called, etc.)\n        if event.impact_level in ['high', 'critical'] or event.police_called:\n            summary['key_concerns'].append({\n                'date': event.event_date.strftime('%B %d, %Y'),\n                'title': event.event_title,\n                'reason': 'High impact event' if event.impact_level in ['high', 'critical'] else 'Police involvement',\n                'priority': 'Critical' if event.impact_level == 'critical' else 'High'\n            })\n    \n    # Generate recommendations\n    if len(events) < 5:\n        summary['recommendations'].append('Continue documenting events to build stronger case foundation')\n    \n    if len([e for e in events if e.evidence_type]) < len(events) * 0.5:\n        summary['recommendations'].append('Add more evidence documentation to strengthen timeline')\n    \n    if len([e for e in events if e.category in ['SAFETY_CONCERN', 'DOMESTIC_VIOLENCE']]) > 0:\n        summary['recommendations'].append('Consider seeking immediate legal protection due to safety concerns')\n    \n    if len(events) >= 10:\n        summary['recommendations'].append('Timeline shows sufficient documentation for court presentation')\n    \n    return summary\n\ndef analyze_patterns(events):\n    \"\"\"Analyze patterns in timeline events for coercive control and abuse indicators\"\"\"\n    patterns = {\n        'communication_frequency': 0,\n        'safety_concerns': 0,\n        'order_violations': 0,\n        'escalation_indicators': [],\n        'pattern_summary': 'No significant patterns detected'\n    }\n    \n    # Analyze by month\n    monthly_events = defaultdict(list)\n    for event in events:\n        month_key = event.event_date.strftime('%Y-%m')\n        monthly_events[month_key].append(event)\n    \n    # Look for escalation patterns\n    previous_impact = None\n    escalation_count = 0\n    for event in sorted(events, key=lambda x: x.event_date):\n        if previous_impact and event.impact_level in ['high', 'critical'] and previous_impact in ['low', 'medium']:\n            escalation_count += 1\n            patterns['escalation_indicators'].append({\n                'date': event.event_date.strftime('%B %d, %Y'),\n                'title': event.event_title,\n                'from': previous_impact,\n                'to': event.impact_level\n            })\n        previous_impact = event.impact_level\n    \n    # Count categories\n    for event in events:\n        if event.category == 'COMMUNICATION':\n            patterns['communication_frequency'] += 1\n        elif event.category == 'SAFETY_CONCERN':\n            patterns['safety_concerns'] += 1\n        elif event.category == 'ORDER_COMPLIANCE':\n            patterns['order_violations'] += 1\n    \n    # Generate pattern summary\n    if escalation_count > 2:\n        patterns['pattern_summary'] = 'Escalating pattern detected - recommend immediate legal consultation'\n    elif patterns['safety_concerns'] > 3:\n        patterns['pattern_summary'] = 'Multiple safety concerns indicate potential abuse pattern'\n    elif patterns['communication_frequency'] > 10:\n        patterns['pattern_summary'] = 'High frequency of communication issues suggesting coercive control'\n    elif patterns['order_violations'] > 2:\n        patterns['pattern_summary'] = 'Repeated order violations demonstrate non-compliance pattern'\n    else:\n        patterns['pattern_summary'] = 'Events show typical family court case progression'\n    \n    return patterns\n\ndef summarize_evidence(events):\n    \"\"\"Summarize evidence quality and completeness\"\"\"\n    evidence_summary = {\n        'total_events': len(events),\n        'events_with_evidence': 0,\n        'evidence_types': {},\n        'witness_events': 0,\n        'police_events': 0,\n        'quality_score': 0\n    }\n    \n    for event in events:\n        if event.evidence_type:\n            evidence_summary['events_with_evidence'] += 1\n            if event.evidence_type not in evidence_summary['evidence_types']:\n                evidence_summary['evidence_types'][event.evidence_type] = 0\n            evidence_summary['evidence_types'][event.evidence_type] += 1\n        \n        if event.witness_present:\n            evidence_summary['witness_events'] += 1\n        \n        if event.police_called:\n            evidence_summary['police_events'] += 1\n    \n    # Calculate quality score (0-100)\n    if events:\n        evidence_ratio = evidence_summary['events_with_evidence'] / len(events)\n        witness_bonus = min(evidence_summary['witness_events'] / len(events), 0.3)\n        police_bonus = min(evidence_summary['police_events'] / len(events), 0.2)\n        evidence_summary['quality_score'] = int((evidence_ratio + witness_bonus + police_bonus) * 100)\n    \n    return evidence_summary\n\ndef generate_chronology(events):\n    \"\"\"Generate professional chronological summary\"\"\"\n    chronology = []\n    \n    for i, event in enumerate(events, 1):\n        chronology.append({\n            'number': i,\n            'date': event.event_date.strftime('%B %d, %Y'),\n            'title': event.event_title,\n            'category': get_category_label(event.category),\n            'impact': event.impact_level,\n            'days_since_previous': (event.event_date - events[i-1].event_date).days if i > 1 else 0\n        })\n    \n    return chronology\n\ndef get_category_label(category):\n    \"\"\"Get human-readable category labels\"\"\"\n    labels = {\n        'PARENTING_TIME': 'Parenting Time & Custody',\n        'CHILD_WELLBEING': 'Child Wellbeing & Care',\n        'COMMUNICATION': 'Communication & Co-Parenting',\n        'ORDER_COMPLIANCE': 'Order Compliance / Non-Compliance',\n        'SAFETY_CONCERN': 'Safety Concerns',\n        'FINANCIAL': 'Financial & Support Issues',\n        'LEGAL_EVENT': 'Legal / Court-Related Event'\n    }\n    return labels.get(category, category.replace('_', ' ').title())

if __name__ == '__main__':\n    with app.app_context():\n        db.create_all()\n    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
