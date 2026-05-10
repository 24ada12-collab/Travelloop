from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import os
import json

app = Flask(__name__)
app.secret_key = 'traveloop_secret_key_2025'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///traveloop.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ─────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    phone = db.Column(db.String(20))
    city = db.Column(db.String(100))
    country = db.Column(db.String(100))
    password_hash = db.Column(db.String(256), nullable=False)
    bio = db.Column(db.Text)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    trips = db.relationship('Trip', backref='user', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('TripNote', backref='user', lazy=True, cascade='all, delete-orphan')
    checklist_items = db.relationship('ChecklistItem', backref='user', lazy=True, cascade='all, delete-orphan')
    posts = db.relationship('CommunityPost', backref='user', lazy=True, cascade='all, delete-orphan')


class Trip(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    destination = db.Column(db.String(200))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    total_budget = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='upcoming')  # ongoing, upcoming, completed
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sections = db.relationship('ItinerarySection', backref='trip', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('TripNote', backref='trip', lazy=True, cascade='all, delete-orphan')
    expenses = db.relationship('Expense', backref='trip', lazy=True, cascade='all, delete-orphan')
    checklist_items = db.relationship('ChecklistItem', backref='trip', lazy=True, cascade='all, delete-orphan')


class ItinerarySection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    section_type = db.Column(db.String(50), default='activity')  # travel, hotel, activity
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.Float, default=0)
    location = db.Column(db.String(200))
    order_index = db.Column(db.Integer, default=0)


class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.String(300))
    qty_details = db.Column(db.String(100))
    unit_cost = db.Column(db.Float, default=0)
    amount = db.Column(db.Float, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TripNote(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    note_date = db.Column(db.Date, default=date.today)
    stop = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class ChecklistItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(100), default='General')
    item_name = db.Column(db.String(200), nullable=False)
    is_packed = db.Column(db.Boolean, default=False)


class CommunityPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip.id'), nullable=True)
    title = db.Column(db.String(300))
    content = db.Column(db.Text)
    destination = db.Column(db.String(200))
    likes = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        user = User.query.get(session['user_id'])
        if not user or not user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def get_trip_status(trip):
    today = date.today()
    if trip.start_date and trip.end_date:
        if today < trip.start_date:
            return 'upcoming'
        elif trip.start_date <= today <= trip.end_date:
            return 'ongoing'
        else:
            return 'completed'
    return trip.status

# ─────────────────────────────────────────
# AUTH ROUTES
# ─────────────────────────────────────────

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['user_name'] = user.first_name
            session['is_admin'] = user.is_admin
            return redirect(url_for('dashboard'))
        flash('Invalid email or password.', 'error')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        city = request.form.get('city', '').strip()
        country = request.form.get('country', '').strip()
        password = request.form.get('password', '')
        bio = request.form.get('bio', '').strip()
        if not first_name or not email or not password:
            flash('Please fill in all required fields.', 'error')
            return render_template('register.html')
        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'error')
            return render_template('register.html')
        user = User(
            first_name=first_name, last_name=last_name, email=email,
            phone=phone, city=city, country=country, bio=bio,
            password_hash=generate_password_hash(password)
        )
        db.session.add(user)
        db.session.commit()
        session['user_id'] = user.id
        session['user_name'] = user.first_name
        session['is_admin'] = False
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ─────────────────────────────────────────
# DASHBOARD
# ─────────────────────────────────────────

@app.route('/dashboard')
@login_required
def dashboard():
    user = User.query.get(session['user_id'])
    trips = Trip.query.filter_by(user_id=user.id).order_by(Trip.created_at.desc()).all()
    for t in trips:
        t.status = get_trip_status(t)
    recent_trips = trips[:3]
    community_posts = CommunityPost.query.order_by(CommunityPost.created_at.desc()).limit(5).all()
    top_destinations = ['Paris', 'Tokyo', 'New York', 'Bali', 'Rome']
    return render_template('dashboard.html', user=user, trips=trips,
                           recent_trips=recent_trips, community_posts=community_posts,
                           top_destinations=top_destinations)

# ─────────────────────────────────────────
# TRIPS
# ─────────────────────────────────────────

@app.route('/trips')
@login_required
def trips():
    user = User.query.get(session['user_id'])
    all_trips = Trip.query.filter_by(user_id=user.id).order_by(Trip.created_at.desc()).all()
    for t in all_trips:
        t.status = get_trip_status(t)
    ongoing = [t for t in all_trips if t.status == 'ongoing']
    upcoming = [t for t in all_trips if t.status == 'upcoming']
    completed = [t for t in all_trips if t.status == 'completed']
    q = request.args.get('q', '')
    if q:
        all_trips = [t for t in all_trips if q.lower() in t.title.lower() or (t.destination and q.lower() in t.destination.lower())]
    return render_template('trips.html', user=user, ongoing=ongoing, upcoming=upcoming,
                           completed=completed, q=q)

@app.route('/trips/create', methods=['GET', 'POST'])
@login_required
def create_trip():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        destination = request.form.get('destination', '').strip()
        description = request.form.get('description', '').strip()
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        total_budget = request.form.get('total_budget', 0)
        is_public = request.form.get('is_public') == 'on'
        if not title:
            flash('Trip title is required.', 'error')
            return render_template('create_trip.html')
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        trip = Trip(
            user_id=session['user_id'], title=title, destination=destination,
            description=description, start_date=start_date, end_date=end_date,
            total_budget=float(total_budget) if total_budget else 0,
            is_public=is_public
        )
        db.session.add(trip)
        db.session.commit()
        # Add default checklist items
        defaults = [
            ('Documents', 'Passport'), ('Documents', 'Flight Tickets (printed)'),
            ('Documents', 'Travel Insurance'), ('Documents', 'Hotel Booking Confirmation'),
            ('Clothing', 'Casual Shirts'), ('Clothing', 'Trousers / Jeans'),
            ('Clothing', 'Comfortable Walking Shoes'), ('Clothing', 'Light Jacket / Windbreaker'),
            ('Electronics', 'Phone Charger'), ('Electronics', 'Universal Power Adapter'),
            ('Electronics', 'Earphones / Headphones'),
        ]
        for cat, item in defaults:
            ci = ChecklistItem(trip_id=trip.id, user_id=session['user_id'], category=cat, item_name=item)
            db.session.add(ci)
        db.session.commit()
        flash('Trip created successfully!', 'success')
        return redirect(url_for('itinerary', trip_id=trip.id))
    suggestions = ['Paris', 'Tokyo', 'New York', 'Bali', 'Rome', 'London', 'Dubai', 'Singapore', 'Sydney', 'Barcelona']
    return render_template('create_trip.html', suggestions=suggestions)

@app.route('/trips/<int:trip_id>')
@login_required
def trip_detail(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        flash('Access denied.', 'error')
        return redirect(url_for('trips'))
    trip.status = get_trip_status(trip)
    sections = ItinerarySection.query.filter_by(trip_id=trip_id).order_by(ItinerarySection.order_index).all()
    expenses = Expense.query.filter_by(trip_id=trip_id).all()
    total_spent = sum(e.amount for e in expenses)
    return render_template('trip_detail.html', trip=trip, sections=sections,
                           expenses=expenses, total_spent=total_spent)

@app.route('/trips/<int:trip_id>/delete', methods=['POST'])
@login_required
def delete_trip(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        flash('Access denied.', 'error')
        return redirect(url_for('trips'))
    db.session.delete(trip)
    db.session.commit()
    flash('Trip deleted.', 'success')
    return redirect(url_for('trips'))

# ─────────────────────────────────────────
# ITINERARY
# ─────────────────────────────────────────

@app.route('/trips/<int:trip_id>/itinerary', methods=['GET', 'POST'])
@login_required
def itinerary(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        return redirect(url_for('trips'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        section_type = request.form.get('section_type', 'activity')
        start_date_str = request.form.get('start_date', '')
        end_date_str = request.form.get('end_date', '')
        budget = request.form.get('budget', 0)
        location = request.form.get('location', '').strip()
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date() if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date() if end_date_str else None
        count = ItinerarySection.query.filter_by(trip_id=trip_id).count()
        section = ItinerarySection(
            trip_id=trip_id, title=title, description=description,
            section_type=section_type, start_date=start_date, end_date=end_date,
            budget=float(budget) if budget else 0, location=location, order_index=count
        )
        db.session.add(section)
        db.session.commit()
        flash('Section added!', 'success')
        return redirect(url_for('itinerary', trip_id=trip_id))
    sections = ItinerarySection.query.filter_by(trip_id=trip_id).order_by(ItinerarySection.order_index).all()
    return render_template('itinerary.html', trip=trip, sections=sections)

@app.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    section = ItinerarySection.query.get_or_404(section_id)
    trip = Trip.query.get(section.trip_id)
    if trip.user_id != session['user_id']:
        return redirect(url_for('trips'))
    db.session.delete(section)
    db.session.commit()
    return redirect(url_for('itinerary', trip_id=section.trip_id))

# ─────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────

@app.route('/search')
@login_required
def search():
    q = request.args.get('q', '')
    search_type = request.args.get('type', 'activity')
    results = []
    activities_db = [
        {'name': 'Paragliding', 'type': 'adventure', 'cost': 80, 'duration': '3 hours', 'city': 'Interlaken'},
        {'name': 'Eiffel Tower Visit', 'type': 'sightseeing', 'cost': 25, 'duration': '2 hours', 'city': 'Paris'},
        {'name': 'Sushi Making Class', 'type': 'food', 'cost': 60, 'duration': '2.5 hours', 'city': 'Tokyo'},
        {'name': 'Scuba Diving', 'type': 'adventure', 'cost': 120, 'duration': '4 hours', 'city': 'Bali'},
        {'name': 'Colosseum Tour', 'type': 'sightseeing', 'cost': 30, 'duration': '2 hours', 'city': 'Rome'},
        {'name': 'Street Food Tour', 'type': 'food', 'cost': 40, 'duration': '3 hours', 'city': 'Bangkok'},
        {'name': 'Hot Air Balloon', 'type': 'adventure', 'cost': 200, 'duration': '1 hour', 'city': 'Cappadocia'},
        {'name': 'Museum of Modern Art', 'type': 'culture', 'cost': 25, 'duration': '2 hours', 'city': 'New York'},
        {'name': 'Bungee Jumping', 'type': 'adventure', 'cost': 150, 'duration': '2 hours', 'city': 'Queenstown'},
        {'name': 'Wine Tasting', 'type': 'food', 'cost': 50, 'duration': '2 hours', 'city': 'Bordeaux'},
        {'name': 'Safari Tour', 'type': 'adventure', 'cost': 300, 'duration': 'Full day', 'city': 'Nairobi'},
        {'name': 'Temple Hopping', 'type': 'culture', 'cost': 15, 'duration': '4 hours', 'city': 'Kyoto'},
    ]
    cities_db = [
        {'name': 'Paris', 'country': 'France', 'cost_index': 'High', 'popularity': 'Very Popular', 'region': 'Europe'},
        {'name': 'Tokyo', 'country': 'Japan', 'cost_index': 'High', 'popularity': 'Very Popular', 'region': 'Asia'},
        {'name': 'Bali', 'country': 'Indonesia', 'cost_index': 'Low', 'popularity': 'Popular', 'region': 'Asia'},
        {'name': 'New York', 'country': 'USA', 'cost_index': 'Very High', 'popularity': 'Very Popular', 'region': 'Americas'},
        {'name': 'Rome', 'country': 'Italy', 'cost_index': 'Medium', 'popularity': 'Very Popular', 'region': 'Europe'},
        {'name': 'London', 'country': 'UK', 'cost_index': 'High', 'popularity': 'Very Popular', 'region': 'Europe'},
        {'name': 'Dubai', 'country': 'UAE', 'cost_index': 'High', 'popularity': 'Popular', 'region': 'Middle East'},
        {'name': 'Barcelona', 'country': 'Spain', 'cost_index': 'Medium', 'popularity': 'Popular', 'region': 'Europe'},
        {'name': 'Sydney', 'country': 'Australia', 'cost_index': 'High', 'popularity': 'Popular', 'region': 'Oceania'},
        {'name': 'Singapore', 'country': 'Singapore', 'cost_index': 'High', 'popularity': 'Popular', 'region': 'Asia'},
    ]
    if search_type == 'activity':
        results = [a for a in activities_db if not q or q.lower() in a['name'].lower() or q.lower() in a['type'].lower() or q.lower() in a['city'].lower()]
    else:
        results = [c for c in cities_db if not q or q.lower() in c['name'].lower() or q.lower() in c['country'].lower() or q.lower() in c['region'].lower()]
    user = User.query.get(session['user_id'])
    user_trips = Trip.query.filter_by(user_id=user.id).all()
    return render_template('search.html', q=q, search_type=search_type, results=results, user_trips=user_trips)

# ─────────────────────────────────────────
# EXPENSES / INVOICE
# ─────────────────────────────────────────

@app.route('/trips/<int:trip_id>/expenses', methods=['GET', 'POST'])
@login_required
def expenses(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        return redirect(url_for('trips'))
    if request.method == 'POST':
        category = request.form.get('category', '').strip()
        description = request.form.get('description', '').strip()
        qty_details = request.form.get('qty_details', '').strip()
        unit_cost = float(request.form.get('unit_cost', 0))
        amount = float(request.form.get('amount', 0))
        expense = Expense(trip_id=trip_id, category=category, description=description,
                          qty_details=qty_details, unit_cost=unit_cost, amount=amount)
        db.session.add(expense)
        db.session.commit()
        flash('Expense added!', 'success')
        return redirect(url_for('expenses', trip_id=trip_id))
    expense_list = Expense.query.filter_by(trip_id=trip_id).all()
    subtotal = sum(e.amount for e in expense_list)
    tax = round(subtotal * 0.05, 2)
    discount = 50 if subtotal > 1000 else 0
    grand_total = subtotal + tax - discount
    by_category = {}
    for e in expense_list:
        by_category[e.category] = by_category.get(e.category, 0) + e.amount
    return render_template('expenses.html', trip=trip, expenses=expense_list,
                           subtotal=subtotal, tax=tax, discount=discount,
                           grand_total=grand_total, by_category=json.dumps(by_category))

@app.route('/expenses/<int:expense_id>/delete', methods=['POST'])
@login_required
def delete_expense(expense_id):
    expense = Expense.query.get_or_404(expense_id)
    trip_id = expense.trip_id
    db.session.delete(expense)
    db.session.commit()
    return redirect(url_for('expenses', trip_id=trip_id))

# ─────────────────────────────────────────
# NOTES
# ─────────────────────────────────────────

@app.route('/trips/<int:trip_id>/notes', methods=['GET', 'POST'])
@login_required
def notes(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        return redirect(url_for('trips'))
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        stop = request.form.get('stop', '').strip()
        note_date_str = request.form.get('note_date', '')
        note_date = datetime.strptime(note_date_str, '%Y-%m-%d').date() if note_date_str else date.today()
        note = TripNote(trip_id=trip_id, user_id=session['user_id'],
                        title=title, content=content, stop=stop, note_date=note_date)
        db.session.add(note)
        db.session.commit()
        flash('Note added!', 'success')
        return redirect(url_for('notes', trip_id=trip_id))
    filter_by = request.args.get('filter', 'all')
    notes_q = TripNote.query.filter_by(trip_id=trip_id)
    if filter_by == 'stop':
        notes_q = notes_q.filter(TripNote.stop != '')
    all_notes = notes_q.order_by(TripNote.created_at.desc()).all()
    return render_template('notes.html', trip=trip, notes=all_notes, filter_by=filter_by)

@app.route('/notes/<int:note_id>/delete', methods=['POST'])
@login_required
def delete_note(note_id):
    note = TripNote.query.get_or_404(note_id)
    trip_id = note.trip_id
    if note.user_id != session['user_id']:
        return redirect(url_for('trips'))
    db.session.delete(note)
    db.session.commit()
    return redirect(url_for('notes', trip_id=trip_id))

# ─────────────────────────────────────────
# CHECKLIST
# ─────────────────────────────────────────

@app.route('/trips/<int:trip_id>/checklist', methods=['GET', 'POST'])
@login_required
def checklist(trip_id):
    trip = Trip.query.get_or_404(trip_id)
    if trip.user_id != session['user_id']:
        return redirect(url_for('trips'))
    if request.method == 'POST':
        item_name = request.form.get('item_name', '').strip()
        category = request.form.get('category', 'General').strip()
        if item_name:
            ci = ChecklistItem(trip_id=trip_id, user_id=session['user_id'],
                               item_name=item_name, category=category)
            db.session.add(ci)
            db.session.commit()
        return redirect(url_for('checklist', trip_id=trip_id))
    items = ChecklistItem.query.filter_by(trip_id=trip_id).all()
    categories = {}
    for item in items:
        categories.setdefault(item.category, []).append(item)
    packed = sum(1 for i in items if i.is_packed)
    return render_template('checklist.html', trip=trip, categories=categories,
                           total=len(items), packed=packed)

@app.route('/checklist/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_checklist(item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    item.is_packed = not item.is_packed
    db.session.commit()
    return redirect(url_for('checklist', trip_id=item.trip_id))

@app.route('/checklist/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_checklist(item_id):
    item = ChecklistItem.query.get_or_404(item_id)
    trip_id = item.trip_id
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('checklist', trip_id=trip_id))

@app.route('/trips/<int:trip_id>/checklist/reset', methods=['POST'])
@login_required
def reset_checklist(trip_id):
    items = ChecklistItem.query.filter_by(trip_id=trip_id).all()
    for item in items:
        item.is_packed = False
    db.session.commit()
    return redirect(url_for('checklist', trip_id=trip_id))

# ─────────────────────────────────────────
# COMMUNITY
# ─────────────────────────────────────────

@app.route('/community', methods=['GET', 'POST'])
@login_required
def community():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '').strip()
        destination = request.form.get('destination', '').strip()
        trip_id = request.form.get('trip_id')
        post = CommunityPost(user_id=session['user_id'], title=title, content=content,
                             destination=destination, trip_id=int(trip_id) if trip_id else None)
        db.session.add(post)
        db.session.commit()
        flash('Post shared!', 'success')
        return redirect(url_for('community'))
    q = request.args.get('q', '')
    posts_q = CommunityPost.query
    if q:
        posts_q = posts_q.filter(CommunityPost.title.ilike(f'%{q}%') | CommunityPost.destination.ilike(f'%{q}%'))
    posts = posts_q.order_by(CommunityPost.created_at.desc()).all()
    user = User.query.get(session['user_id'])
    user_trips = Trip.query.filter_by(user_id=user.id, is_public=True).all()
    return render_template('community.html', posts=posts, user=user, user_trips=user_trips, q=q)

@app.route('/community/<int:post_id>/like', methods=['POST'])
@login_required
def like_post(post_id):
    post = CommunityPost.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return redirect(url_for('community'))

# ─────────────────────────────────────────
# PROFILE
# ─────────────────────────────────────────

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.first_name = request.form.get('first_name', user.first_name).strip()
        user.last_name = request.form.get('last_name', user.last_name).strip()
        user.phone = request.form.get('phone', user.phone).strip()
        user.city = request.form.get('city', user.city).strip()
        user.country = request.form.get('country', user.country).strip()
        user.bio = request.form.get('bio', user.bio).strip()
        db.session.commit()
        session['user_name'] = user.first_name
        flash('Profile updated!', 'success')
        return redirect(url_for('profile'))
    trips = Trip.query.filter_by(user_id=user.id).all()
    for t in trips:
        t.status = get_trip_status(t)
    preplanned = [t for t in trips if t.status == 'upcoming']
    previous = [t for t in trips if t.status == 'completed']
    return render_template('profile.html', user=user, preplanned=preplanned, previous=previous)

# ─────────────────────────────────────────
# ADMIN
# ─────────────────────────────────────────

@app.route('/admin')
@admin_required
def admin():
    total_users = User.query.count()
    total_trips = Trip.query.count()
    total_posts = CommunityPost.query.count()
    users = User.query.order_by(User.created_at.desc()).all()
    trips = Trip.query.order_by(Trip.created_at.desc()).all()
    for t in trips:
        t.status = get_trip_status(t)
    # Top destinations
    dest_counts = {}
    for t in trips:
        if t.destination:
            dest_counts[t.destination] = dest_counts.get(t.destination, 0) + 1
    top_destinations = sorted(dest_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    return render_template('admin.html', total_users=total_users, total_trips=total_trips,
                           total_posts=total_posts, users=users, trips=trips,
                           top_destinations=top_destinations)

@app.route('/admin/toggle_admin/<int:user_id>', methods=['POST'])
@admin_required
def toggle_admin(user_id):
    user = User.query.get_or_404(user_id)
    if user.id != session['user_id']:
        user.is_admin = not user.is_admin
        db.session.commit()
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    if user_id == session['user_id']:
        flash("Cannot delete yourself.", 'error')
        return redirect(url_for('admin'))
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('User deleted.', 'success')
    return redirect(url_for('admin'))

# ─────────────────────────────────────────
# INIT DB + SEED
# ─────────────────────────────────────────

def seed_data():
    if User.query.count() == 0:
        admin = User(
            first_name='Admin', last_name='User', email='admin@traveloop.com',
            city='San Francisco', country='USA',
            password_hash=generate_password_hash('admin123'),
            is_admin=True, bio='Platform Administrator'
        )
        demo = User(
            first_name='James', last_name='Anderson', email='james@demo.com',
            city='London', country='UK',
            password_hash=generate_password_hash('demo123'),
            bio='Avid traveler exploring the world one city at a time.'
        )
        db.session.add_all([admin, demo])
        db.session.commit()

        trip1 = Trip(user_id=demo.id, title='Europe Adventure', destination='Paris & Rome',
                     description='Exploring the best of Western Europe.',
                     start_date=date(2025, 6, 1), end_date=date(2025, 6, 15),
                     total_budget=20000, is_public=True, status='upcoming')
        db.session.add(trip1)
        db.session.commit()

        sections = [
            ItinerarySection(trip_id=trip1.id, title='Flight to Paris', section_type='travel',
                             description='DEL → PAR direct flight', start_date=date(2025, 6, 1),
                             end_date=date(2025, 6, 1), budget=12000, location='Delhi Airport', order_index=0),
            ItinerarySection(trip_id=trip1.id, title='Hotel Booking - Paris', section_type='hotel',
                             description='3 nights at Hotel Le Marais', start_date=date(2025, 6, 2),
                             end_date=date(2025, 6, 4), budget=9000, location='Paris', order_index=1),
            ItinerarySection(trip_id=trip1.id, title='Eiffel Tower Visit', section_type='activity',
                             description='Evening visit with dinner cruise',
                             start_date=date(2025, 6, 3), end_date=date(2025, 6, 3),
                             budget=500, location='Paris', order_index=2),
        ]
        db.session.add_all(sections)

        expenses = [
            Expense(trip_id=trip1.id, category='hotel', description='Hotel booking Paris',
                    qty_details='3 nights', unit_cost=3000, amount=9000),
            Expense(trip_id=trip1.id, category='travel', description='Flight bookings (DEL → PAR)',
                    qty_details='1', unit_cost=12000, amount=12000),
        ]
        db.session.add_all(expenses)

        defaults = [
            ('Documents', 'Passport'), ('Documents', 'Flight Tickets (printed)'),
            ('Documents', 'Travel Insurance'), ('Documents', 'Hotel Booking Confirmation'),
            ('Clothing', 'Casual Shirts'), ('Clothing', 'Trousers / Jeans'),
            ('Clothing', 'Comfortable Walking Shoes'), ('Clothing', 'Light Jacket / Windbreaker'),
            ('Electronics', 'Phone Charger'), ('Electronics', 'Universal Power Adapter'),
            ('Electronics', 'Earphones / Headphones'),
        ]
        for cat, item in defaults:
            ci = ChecklistItem(trip_id=trip1.id, user_id=demo.id, category=cat, item_name=item,
                               is_packed=(cat == 'Documents' and item != 'Hotel Booking Confirmation'))
            db.session.add(ci)

        notes_data = [
            TripNote(trip_id=trip1.id, user_id=demo.id, title='Hotel check-in details - Paris stop',
                     content='Check in after 2pm, room 302, breakfast included (7-10am)',
                     stop='Paris', note_date=date(2025, 6, 2)),
            TripNote(trip_id=trip1.id, user_id=demo.id, title='Airport taxi info',
                     content='Pre-booked taxi from hotel to CDG airport. Pickup at 6am.',
                     stop='Paris', note_date=date(2025, 6, 5)),
        ]
        db.session.add_all(notes_data)

        post = CommunityPost(user_id=demo.id, trip_id=trip1.id,
                             title='Planning my Europe Adventure – Tips Welcome!',
                             content='Heading to Paris and Rome in June. Any must-see places or hidden gems?',
                             destination='Paris & Rome')
        db.session.add(post)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        seed_data()
    app.run(debug=True, port=5000)