     1	import os
     2	import json
     3	from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
     4	from flask_sqlalchemy import SQLAlchemy
     5	from flask_cors import CORS
     6	from werkzeug.security import generate_password_hash, check_password_hash
     7	from datetime import datetime, date
     8	import uuid
     9	
    10	app = Flask(__name__)
    11	app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    12	app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///legaldocs.db')
    13	app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    14	
    15	db = SQLAlchemy(app)
    16	CORS(app)
    17	
    18	# Database Models
    19	class User(db.Model):
    20	    id = db.Column(db.Integer, primary_key=True)
    21	    email = db.Column(db.String(120), unique=True, nullable=False)
    22	    password_hash = db.Column(db.String(200), nullable=False)
    23	    first_name = db.Column(db.String(50))
    24	    last_name = db.Column(db.String(50))
    25	    subscription_tier = db.Column(db.String(20), default='basic')
    26	    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    27	    cases = db.relationship('Case', backref='user', lazy=True)
    28	
    29	class Case(db.Model):
    30	    id = db.Column(db.Integer, primary_key=True)
    31	    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    32	    case_title = db.Column(db.String(200), nullable=False)
    33	    case_focus = db.Column(db.String(100))  # Changed from case_type to case_focus
    34	    legal_domain = db.Column(db.String(50), default='FAMILY_LAW')  # Added for backend categorization
    35	    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    36	    timeline_events = db.relationship('TimelineEvent', backref='case', lazy=True)
    37	    documents = db.relationship('Document', backref='case', lazy=True)
    38	
    39	class TimelineEvent(db.Model):
    40	    id = db.Column(db.Integer, primary_key=True)
    41	    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    42	    event_date = db.Column(db.Date, nullable=False)
    43	    event_time = db.Column(db.Time)
    44	    event_title = db.Column(db.String(200), nullable=False)
    45	    event_description = db.Column(db.Text)
    46	    category = db.Column(db.String(50))
    47	    evidence_type = db.Column(db.String(100))
    48	    impact_level = db.Column(db.String(20))
    49	    witness_present = db.Column(db.Boolean, default=False)
    50	    police_called = db.Column(db.Boolean, default=False)
    51	    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    52	
    53	class Document(db.Model):
    54	    id = db.Column(db.Integer, primary_key=True)
    55	    case_id = db.Column(db.Integer, db.ForeignKey('case.id'), nullable=False)
    56	    filename = db.Column(db.String(255), nullable=False)
    57	    original_filename = db.Column(db.String(255))
    58	    document_type = db.Column(db.String(50))
    59	    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    60	    file_size = db.Column(db.Integer)
    61	    evidence_category = db.Column(db.String(100))
    62	
    63	# Routes
    64	@app.route('/')
    65	def index():
    66	    return render_template('index.html')
    67	
    68	@app.route('/dashboard')
    69	def dashboard():
    70	    if 'user_id' not in session:
    71	        return redirect(url_for('index'))
    72	    
    73	    user = User.query.get(session['user_id'])
    74	    cases = Case.query.filter_by(user_id=user.id).all()
    75	    
    76	    # Get recent timeline events
    77	    recent_events = []
    78	    for case in cases:
    79	        events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date.desc()).limit(5).all()
    80	        recent_events.extend(events)
    81	    
    82	    recent_events.sort(key=lambda x: x.event_date, reverse=True)
    83	    
    84	    return render_template('dashboard.html', user=user, cases=cases, recent_events=recent_events[:5])
    85	
    86	@app.route('/timeline/<int:case_id>')
    87	def timeline(case_id):
    88	    if 'user_id' not in session:
    89	        return redirect(url_for('index'))
    90	    
    91	    case = Case.query.get_or_404(case_id)
    92	    events = TimelineEvent.query.filter_by(case_id=case.id).order_by(TimelineEvent.event_date).all()
    93	    
    94	    return render_template('timeline.html', case=case, events=events)
    95	
    96	@app.route('/api/register', methods=['POST'])
    97	def register():
    98	    data = request.json
    99	    email = data.get('email')
   100	    password = data.get('password')
   101	    first_name = data.get('first_name', '')
   102	    last_name = data.get('last_name', '')
   103	    
   104	    if User.query.filter_by(email=email).first():
   105	        return jsonify({'error': 'User already exists'}), 400
   106	    
   107	    user = User(
   108	        email=email,
   109	        password_hash=generate_password_hash(password),
   110	        first_name=first_name,
   111	        last_name=last_name
   112	    )
   113	    
   114	    db.session.add(user)
   115	    db.session.commit()
   116	    
   117	    session['user_id'] = user.id
   118	    return jsonify({'success': True, 'user_id': user.id})
   119	
   120	@app.route('/api/login', methods=['POST'])
   121	def login():
   122	    data = request.json
   123	    email = data.get('email')
   124	    password = data.get('password')
   125	    
   126	    user = User.query.filter_by(email=email).first()
   127	    
   128	    if user and check_password_hash(user.password_hash, password):
   129	        session['user_id'] = user.id
   130	        return jsonify({'success': True, 'user_id': user.id})
   131	    
   132	    return jsonify({'error': 'Invalid credentials'}), 401
   133	
   134	@app.route('/api/logout', methods=['POST'])
   135	def logout():
   136	    session.pop('user_id', None)
   137	    return jsonify({'success': True})
   138	
   139	@app.route('/api/case', methods=['POST'])
   140	def create_case():
   141	    if 'user_id' not in session:
   142	        return jsonify({'error': 'Not authenticated'}), 401
   143	    
   144	    data = request.json
   145	    case = Case(
   146	        user_id=session['user_id'],
   147	        case_title=data.get('case_title'),
   148	        case_focus=data.get('case_type', 'CUSTODY_PARENTING'),  # Using case_focus field
   149	        legal_domain='FAMILY_LAW'  # Backend categorization
   150	    )
   151	    
   152	    db.session.add(case)
   153	    db.session.commit()
   154	    
   155	    return jsonify({'success': True, 'case_id': case.id})
   156	
   157	@app.route('/api/timeline_event', methods=['POST'])
   158	def create_timeline_event():
   159	    if 'user_id' not in session:
   160	        return jsonify({'error': 'Not authenticated'}), 401
   161	    
   162	    data = request.json
   163	    event_date = datetime.strptime(data.get('event_date'), '%Y-%m-%d').date()
   164	    
   165	    event = TimelineEvent(
   166	        case_id=data.get('case_id'),
   167	        event_date=event_date,
   168	        event_title=data.get('event_title'),
   169	        event_description=data.get('event_description', ''),
   170	        category=data.get('category', 'PARENTING_TIME'),
   171	        evidence_type=data.get('evidence_type', ''),
   172	        impact_level=data.get('impact_level', 'medium'),
   173	        witness_present=data.get('witness_present', False),
   174	        police_called=data.get('police_called', False)
   175	    )
   176	    
   177	    db.session.add(event)
   178	    db.session.commit()
   179	    
   180	    return jsonify({'success': True, 'event_id': event.id})
   181	
   182	@app.route('/api/timeline_events/<int:case_id>')
   183	def get_timeline_events(case_id):
   184	    if 'user_id' not in session:
   185	        return jsonify({'error': 'Not authenticated'}), 401
   186	    
   187	    events = TimelineEvent.query.filter_by(case_id=case_id).order_by(TimelineEvent.event_date).all()
   188	    
   189	    events_data = []
   190	    for event in events:
   191	        events_data.append({
   192	            'id': event.id,
   193	            'event_date': event.event_date.isoformat(),
   194	            'event_title': event.event_title,
   195	            'event_description': event.event_description,
   196	            'category': event.category,
   197	            'evidence_type': event.evidence_type,
   198	            'impact_level': event.impact_level,
   199	            'witness_present': event.witness_present,
   200	            'police_called': event.police_called
   201	        })
   202	    
   203	    return jsonify(events_data)
   204	
   205	if __name__ == '__main__':
   206	    with app.app_context():
   207	        db.create_all()
   208	    app.run(debug=True, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
