import os
import random
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, session, g, jsonify, send_from_directory, abort
)
from flask_socketio import SocketIO, emit, join_room, leave_room

from config import Config
from database import get_db, init_app
from classifier import classify_query, detect_priority
from seed_data import seed_database

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Database Hooks & SocketIO
init_app(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

ONLINE_USERS = {} # user_id -> set of socket session IDs

@app.before_request
def track_user_activity():
    """Updates user activity without writing to the database on every request."""
    user = get_current_user()

    if user and user.get('id'):
        uid = user['id']

        if uid not in ONLINE_USERS:
            ONLINE_USERS[uid] = set()

        last_active = user.get('last_active_at')
        now = datetime.now()

        try:
            if last_active:
                if isinstance(last_active, str):
                    last_active = datetime.strptime(
                        last_active.split('.')[0],
                        '%Y-%m-%d %H:%M:%S'
                    )

                # Update only once every 5 minutes
                if (now - last_active).total_seconds() < 300:
                    return

            db = get_db()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')

            db.execute(
                "UPDATE users SET last_active_at = ? WHERE id = ?",
                (now_str, uid)
            )
            db.commit()

        except Exception:
            pass

@app.after_request
def add_cache_headers(response):
    """Instructs browsers to cache static assets to eliminate reload delays on Render."""
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=86400'
    return response

# -------------------------------------------------------------
# HELPERS & DECORATORS
# -------------------------------------------------------------

def allowed_file(filename):
    """Check if file has an allowed extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            session.clear()
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                session.clear()
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            if user['role'] not in allowed_roles and user['role'] not in ['admin', 'principal']:
                flash('You do not have permission to access that resource.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Retrieve the currently authenticated user from the database as a dictionary.
    Cached on Flask's g object so the DB is queried at most once per request."""
    if hasattr(g, '_current_user'):
        return g._current_user
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or not user['is_active']:
            session.clear()
            g._current_user = None
            return None
        g._current_user = dict(user)
        return g._current_user
    g._current_user = None
    return None

@app.context_processor
def inject_global_context():
    """Inject global variables into all Jinja templates."""
    user = get_current_user()
    unread_notifications_count = 0
    unread_notifications = []
    
    if user:
        db = get_db()
        # Single query: fetch up to 5 latest unread + count in one shot
        notifications = db.execute(
            'SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC LIMIT 5',
            (user['id'],)
        ).fetchall()
        unread_notifications = [dict(n) for n in notifications]
        # Count comes from a lightweight separate query (SQLite COUNT on indexed column is O(1))
        count_row = db.execute(
            'SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0',
            (user['id'],)
        ).fetchone()
        unread_notifications_count = count_row['count'] if count_row else 0
        
    return {
        'current_user': user,
        'unread_notifications_count': unread_notifications_count,
        'unread_notifications': unread_notifications,
        'DEPARTMENTS': Config.DEPARTMENTS,
        'CATEGORIES': Config.CATEGORIES,
        'COURSES_BRANCHES': Config.COURSES_BRANCHES,
        'PRIORITIES': Config.PRIORITIES,
        'STATUSES': Config.STATUSES,
        'now': datetime.now()
    }

def format_datetime(dt_val, fmt='%d %b %Y, %I:%M %p'):
    """Utility to format timestamps as clear readable dates and times (e.g. 04 Sep 2026, 08:30 PM)."""
    if not dt_val:
        return 'N/A'
    try:
        if isinstance(dt_val, str):
            clean_str = dt_val.split('.')[0].replace('T', ' ')
            dt = datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S')
        else:
            dt = dt_val
        return dt.strftime(fmt)
    except Exception:
        return str(dt_val)

app.jinja_env.filters['format_datetime'] = format_datetime

def format_time_ago(dt_str):
    """Utility to accurately format timestamps as human-readable relative time strings without timezone offset errors."""
    if not dt_str:
        return 'Just now'
    try:
        if isinstance(dt_str, str):
            clean_str = dt_str.split('.')[0].replace('T', ' ')
            dt = datetime.strptime(clean_str, '%Y-%m-%d %H:%M:%S')
        else:
            dt = dt_str
        
        now = datetime.now()
        diff = now - dt
        seconds = diff.total_seconds()
        
        # Compensate for tiny sub-minute local clock drifts
        if -60 <= seconds < 0:
            seconds = 0
        elif seconds < -60:
            return dt.strftime('%b %d, %Y')
            
        if seconds < 60:
            return 'Just now'
        elif seconds < 3600:
            mins = max(1, int(seconds // 60))
            return f'{mins}m ago'
        elif seconds < 86400:
            hours = int(seconds // 3600)
            return f'{hours}h ago'
        elif seconds < 604800:
            days = int(seconds // 86400)
            return f'{days}d ago'
        else:
            return dt.strftime('%b %d, %Y')
    except Exception:
        return 'Just now'

app.jinja_env.filters['timeago'] = format_time_ago

def create_notification(user_id, query_id, title, message, notif_type='info'):
    """Helper to store a notification in the database with explicit local timestamp and foreign key validation."""
    if not user_id:
        return
    try:
        db = get_db()
        # Verify user exists
        user_check = db.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        if not user_check:
            return
        # Verify query exists if query_id is given
        if query_id:
            query_check = db.execute("SELECT id FROM queries WHERE id = ?", (query_id,)).fetchone()
            if not query_check:
                query_id = None
                
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        db.execute("""
            INSERT INTO notifications (user_id, query_id, title, message, type, is_read, created_at)
            VALUES (?, ?, ?, ?, ?, 0, ?)
        """, (user_id, query_id, title, message, notif_type, now_str))

    except Exception as e:
        print(f"Notification error bypassed: {e}")

def ensure_demo_accounts(db):
    """Ensures demo accounts for all Faculty roles (Staff, HODs by degree, AO, Principal) and Students exist."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    demo_accounts = [
        # 1. B.Tech Student
        ('Student (B.Tech CSE 3rd Yr)', 'student@college.com', 'student123', 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, 'Student (B.Tech CSE)'),
        
        # 2. M.Tech Student
        ('Student (M.Tech CSE 1st Yr)', 'mtech-student@college.com', 'student123', 'student', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', 1, 'Student (M.Tech CSE)'),

        # 3. B.Tech CSE HOD (UG)
        ('Dr. Grace Hopper (B.Tech CSE HOD)', 'cse-hod@college.com', 'hod123', 'hod', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, 'Head of Department (B.Tech CSE)'),
        
        # 4. B.Tech CSE Staff
        ('Prof. Linus Torvalds', 'cse-staff@college.com', 'staff123', 'staff', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, 'B.Tech CSE Assistant Professor / Staff'),

        # 5. M.Tech CSE HOD (PG)
        ('Dr. Barbara Liskov (M.Tech CSE HOD)', 'mtech-cse-hod@college.com', 'hod123', 'hod', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', None, 'Head of Department (M.Tech CSE)'),
        
        # 6. M.Tech CSE Staff
        ('Prof. Donald Knuth', 'mtech-cse-staff@college.com', 'staff123', 'staff', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', None, 'M.Tech CSE Assistant Professor / Staff'),

        # 7. MCA HOD
        ('Dr. Tim Berners-Lee (MCA HOD)', 'mca-hod@college.com', 'hod123', 'hod', 'PG', 'Master of Computer Applications (MCA)', 'MCA', None, 'Head of Department (MCA)'),

        # 8. MBA HOD
        ('Dr. Peter Drucker (MBA HOD)', 'mba-hod@college.com', 'hod123', 'hod', 'PG', 'Master of Business Administration (MBA)', 'MBA', None, 'Head of Department (MBA)'),

        # 9. Administrative Officer (AO)
        ('Mrs. Eleanor Wright (AO)', 'ao@college.com', 'ao123', 'ao', None, 'Administrative', None, None, 'Administrative Officer (AO)'),
        
        # 10. Office Staff (Administrative)
        ('Mr. Ramesh Kumar (Office Staff)', 'office-staff@college.com', 'staff123', 'office_staff', None, 'Administrative', None, None, 'Office Staff / Admin Assistant'),

        # 11. Principal
        ('Dr. Alan Turing (Principal)', 'principal@college.com', 'principal123', 'principal', None, 'College Administration', None, None, 'Principal'),
        
        # 12. Central Administrator
        ('Central Administrator', 'admin@college.com', 'admin123', 'admin', None, None, None, None, 'Central Administrator')
    ]
    for name, email, pwd, role, level, dept, course, year, desig in demo_accounts:
        try:
            existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
            if not existing:
                db.execute("""
                    INSERT INTO users (name, email, password_hash, role, level, department, course, year, designation, is_active, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (name, email, generate_password_hash(pwd), role, level, dept, course, year, desig, now_str))
            else:
                db.execute("""
                    UPDATE users SET name = ?, password_hash = ?, is_active = 1, role = ?, level = COALESCE(?, level), department = COALESCE(?, department), course = COALESCE(?, course), designation = COALESCE(?, designation) WHERE email = ?
                """, (name, generate_password_hash(pwd), role, level, dept, course, desig, email))
        except Exception as e:
            print(f"Demo sync notice for {email}: {e}")
            
    # Clean up any leftover demo accounts
    old_demo_emails = [
        'faculty@college.com', 'staff@college.com', 'admin-staff@college.com', 'academics-staff@college.com',
        'ece-hod@college.com', 'mech-hod@college.com', 'bca-hod@college.com',
        'diploma-hod@college.com', 'student-cse1@college.com', 'student-aiml@college.com',
        'student-ds@college.com', 'student-ece@college.com', 'student-me@college.com',
        'student-civil@college.com', 'student-bca@college.com', 'student-mba@college.com',
        'student-mca@college.com', 'student-diploma@college.com'
    ]
    for old_email in old_demo_emails:
        try:
            db.execute("DELETE FROM users WHERE email = ?", (old_email,))
        except Exception:
            pass
            
    try:
        db.commit()
    except Exception:
        pass

# -------------------------------------------------------------
# AUTHENTICATION ROUTES
# -------------------------------------------------------------

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        user = get_current_user()
        if user:
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'principal':
                return redirect(url_for('department_dashboard', dept='Others', view='received'))
            elif user['role'] in ['staff', 'hod', 'ao', 'faculty']:
                return redirect(url_for('department_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        
    db = get_db()
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        
        if not email or not password:
            flash('Please enter both email and password.', 'warning')
            return render_template('login.html')
            
        user = db.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        
        if user and check_password_hash(user['password_hash'], password):
            if not user['is_active']:
                flash('Your account has been deactivated. Please contact the administrator.', 'danger')
                return render_template('login.html')
                
            session.clear()
            session['user_id'] = user['id']
            session['name'] = user['name']
            session['email'] = user['email']
            session['role'] = user['role']
            session['department'] = user['department']
            
            flash(f'Welcome back, {user["name"]}!', 'success')
            
            # Redirect to relevant dashboard
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'principal':
                return redirect(url_for('department_dashboard', dept='Others', view='received'))
            elif user['role'] == 'ao':
                return redirect(url_for('department_dashboard', dept='Administrative'))
            elif user['role'] in ['staff', 'office_staff', 'hod', 'faculty']:
                return redirect(url_for('department_dashboard'))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('Invalid email address or password. Please check your credentials.', 'danger')
            
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        role = request.form.get('faculty_role_type', 'staff').strip()
        if role not in ['staff', 'office_staff', 'hod', 'ao', 'principal']:
            role = 'staff'
            
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        level = None
        course = None
        if role in ['staff', 'hod']:
            level = request.form.get('fac_level') or request.form.get('level') or 'UG'
            course = request.form.get('fac_course') or request.form.get('course') or 'B.Tech'
            department = request.form.get('fac_department') or request.form.get('department', '').strip()
            if not department:
                department = 'Computer Science & Engineering (CSE)'
            default_desig = 'Head of Department' if role == 'hod' else 'Department Staff'
            designation = request.form.get('designation', '').strip() or default_desig
        elif role == 'office_staff':
            department = 'Administrative'
            designation = request.form.get('designation', '').strip() or 'Office Staff / Administrative Staff'
        elif role == 'ao':
            department = 'Administrative'
            designation = 'Administrative Officer (AO)'
        elif role == 'principal':
            department = 'College Administration'
            designation = 'Principal'
        else:
            department = 'General'
            designation = 'Faculty'
            
        if not email or not password:
            flash('Email and password are required.', 'warning')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'warning')
            return render_template('register.html')
            
        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'warning')
            return render_template('register.html')
            
        db = get_db()
        existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('An account with this email already exists. Please login instead.', 'danger')
            return render_template('register.html')
            
        try:
            password_hash = generate_password_hash(password)
            db.execute("""
                INSERT INTO users (name, email, password_hash, role, level, department, course, year, phone, designation, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, 1)
            """, (name or 'Faculty Member', email, password_hash, role, level, department, course, phone, designation))
            db.commit()
            
            flash('Registration successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration could not be completed: {str(e)}', 'danger')
            return render_template('register.html')
        
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('index'))

# -------------------------------------------------------------
# GENERAL & USER PORTAL ROUTES
# -------------------------------------------------------------

@app.route('/')
def index():
    """Landing Page with high-impact hero, live classifier demo, and college stats."""
    db = get_db()
    total_queries = db.execute('SELECT COUNT(*) as c FROM queries').fetchone()['c']
    resolved_queries = db.execute("SELECT COUNT(*) as c FROM queries WHERE status = 'Resolved'").fetchone()['c']
    departments_count = db.execute('SELECT COUNT(*) as c FROM departments').fetchone()['c']
    
    # Calculate avg response time across system
    avg_minutes = 12
    return render_template(
        'index.html',
        total_queries=total_queries,
        resolved_queries=resolved_queries,
        departments_count=departments_count,
        avg_minutes=avg_minutes
    )

@app.route('/dashboard')
@login_required
def dashboard():
    user = get_current_user()
    if user['role'] in ['staff', 'office_staff', 'hod']:
        return redirect(url_for('department_dashboard'))
    elif user['role'] == 'ao':
        return redirect(url_for('department_dashboard', dept='Administrative'))
    elif user['role'] == 'principal':
        return redirect(url_for('department_dashboard', dept='Others', view='received'))
    elif user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    
    # User query counts — single aggregation query instead of 5 separate SELECTs
    stats_row = db.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status = 'New' THEN 1 ELSE 0 END) as new,
            SUM(CASE WHEN status IN ('Assigned', 'In Progress') THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN status = 'Waiting for User' THEN 1 ELSE 0 END) as waiting,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved
        FROM queries WHERE user_id = ?
    """, (user['id'],)).fetchone()
    stats = {
        'total': stats_row['total'] or 0,
        'new': stats_row['new'] or 0,
        'in_progress': stats_row['in_progress'] or 0,
        'waiting': stats_row['waiting'] or 0,
        'resolved': stats_row['resolved'] or 0,
    }
    
    # Filter and Search
    status_filter = request.args.get('status', '')
    priority_filter = request.args.get('priority', '')
    search_query = request.args.get('search', '').strip()
    
    sql = """
        SELECT q.*, 
               (SELECT message FROM messages WHERE query_id = q.id ORDER BY created_at DESC LIMIT 1) as last_message,
               (SELECT created_at FROM messages WHERE query_id = q.id ORDER BY created_at DESC LIMIT 1) as last_activity
        FROM queries q
        WHERE q.user_id = ?
    """
    params = [user['id']]
    
    if status_filter:
        sql += " AND q.status = ?"
        params.append(status_filter)
    if priority_filter:
        sql += " AND q.priority = ?"
        params.append(priority_filter)
    if search_query:
        sql += " AND (q.title LIKE ? OR q.description LIKE ? OR q.id LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term])
        
    sql += " ORDER BY q.created_at DESC"
    queries = db.execute(sql, params).fetchall()
    
    return render_template(
        'dashboard.html',
        stats=stats,
        queries=queries,
        current_status=status_filter,
        current_priority=priority_filter,
        search_query=search_query
    )

@app.route('/api/classify-preview', methods=['POST'])
def classify_preview():
    """Live debounced API endpoint to preview department & priority as user types."""
    data = request.get_json() or {}
    title = data.get('title', '')
    description = data.get('description', '')
    
    if not title and not description:
        return jsonify({
            'department': 'General Administration',
            'category': 'General Inquiry',
            'priority': 'Medium',
            'confidence': 0.0,
            'explanation': 'Enter your problem details above to see smart AI routing.'
        })
        
    result = classify_query(description, title)
    return jsonify(result)

@app.route('/submit-query', methods=['GET', 'POST'])
def submit_query():
    user = get_current_user()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        query_type = request.form.get('query_type', 'student').strip()
        is_faculty_query = (query_type == 'faculty' or (user and user['role'] in ['staff', 'faculty', 'hod']))
        
        email_input = request.form.get('email', '').strip().lower()
        name_input = request.form.get('name', '').strip()
        
        if is_faculty_query:
            submitter_role = 'faculty'
            level = request.form.get('faculty_level') or request.form.get('level', 'UG').strip()
            course = request.form.get('faculty_course') or request.form.get('course', 'B.Tech').strip()
            year_val = None
            department_input = request.form.get('faculty_department') or request.form.get('department', '').strip()
            roll_no_input = request.form.get('faculty_id') or request.form.get('employee_id', '').strip() or None
            designation_input = request.form.get('faculty_designation', '').strip() or 'Faculty Member'
        else:
            submitter_role = 'student'
            level = request.form.get('level', 'UG').strip()
            course = request.form.get('course', 'B.Tech').strip()
            year_str = request.form.get('year', '1').strip()
            year_val = int(year_str) if year_str and year_str.isdigit() else 1
            department_input = request.form.get('department', '').strip()
            roll_no_input = request.form.get('roll_no', '').strip()
            designation_input = None
        
        if not title or not description:
            flash('Please provide both a query title and a detailed problem description.', 'warning')
            return render_template('submit_query.html')
            
        # Run smart automatic NLP classification and multi-factor dynamic priority
        classification = classify_query(description, title)
        category = classification['category']  # 'Academics', 'Administrative', 'Others'
        priority = classification['priority']  # 'Critical', 'High', 'Medium', 'Low'
        needs_admin_review = 1 if classification['needs_admin_review'] else 0
        
        # Exact Core Routing Rules:
        # 1. Academics -> Chosen Department & Program HOD
        # 2. Administrative -> AO (Administrative Officer)
        # 3. Others -> Principal
        if category == 'Academics':
            department = department_input if department_input else (user['department'] if user and user.get('department') else 'Computer Science & Engineering (CSE)')
            target_desk = f"{course or ''} {department} HOD".strip()
        elif category == 'Administrative':
            department = 'Administrative'
            target_desk = "Administrative Officer (AO)"
        else: # Others
            department = 'Others'
            target_desk = "Principal"
        
        db = get_db()
        cursor = db.cursor()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Determine submitter user record
        if user:
            submitter_id = user['id']
            cursor.execute("""
                UPDATE users SET level = COALESCE(?, level), course = COALESCE(?, course), year = COALESCE(?, year), department = COALESCE(?, department), designation = COALESCE(?, designation), last_active_at = ? WHERE id = ?
            """, (level, course, year_val, department_input, designation_input, now_str, submitter_id))
        else:
            # Direct anonymous or email-backed submission
            existing_user = None
            if email_input:
                existing_user = db.execute("SELECT id FROM users WHERE email = ?", (email_input,)).fetchone()
                
            if existing_user:
                submitter_id = existing_user['id']
                cursor.execute("""
                    UPDATE users SET level = COALESCE(?, level), course = COALESCE(?, course), year = COALESCE(?, year), department = COALESCE(?, department), designation = COALESCE(?, designation), last_active_at = ? WHERE id = ?
                """, (level, course, year_val, department_input or department, designation_input, now_str, submitter_id))
            else:
                submitter_name = name_input if name_input else ('Faculty Member' if is_faculty_query else 'Student')
                submitter_email = email_input if email_input else f"{'faculty' if is_faculty_query else 'student'}_{int(datetime.now().timestamp())}_{random.randint(1000, 9999)}@college.edu"
                temp_pass = generate_password_hash('portal123')
                cursor.execute("""
                    INSERT INTO users (name, email, password_hash, role, level, course, year, department, roll_no, designation, is_active, last_active_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """, (submitter_name, submitter_email, temp_pass, submitter_role, level, course, year_val, department_input or department, roll_no_input, designation_input, now_str))
                submitter_id = cursor.lastrowid
                
        if submitter_id not in ONLINE_USERS:
            ONLINE_USERS[submitter_id] = set()
                
        try:
            cursor.execute("""
                INSERT INTO queries (user_id, title, description, category, level, course, department, year, priority, status, admin_reviewed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'New', ?, ?, ?)
            """, (submitter_id, title, description, category, level, course, department, year_val, priority, needs_admin_review, now_str, now_str))
            query_id = cursor.lastrowid
            
            # Save initial message
            cursor.execute("""
                INSERT INTO messages (query_id, sender_id, message, created_at)
                VALUES (?, ?, ?, ?)
            """, (query_id, submitter_id, description, now_str))
            message_id = cursor.lastrowid
            
            # Handle optional file attachment
            if 'attachment' in request.files:
                file = request.files['attachment']
                if file and file.filename and allowed_file(file.filename):
                    orig_filename = file.filename
                    ext = orig_filename.rsplit('.', 1)[1].lower()
                    clean_name = secure_filename(orig_filename)
                    saved_filename = f"q{query_id}_{int(datetime.now().timestamp())}_{clean_name}"
                    save_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
                    file.save(save_path)
                    file_size = os.path.getsize(save_path)
                    
                    cursor.execute("""
                        INSERT INTO attachments (query_id, message_id, filename, original_filename, file_size, file_type, filepath, uploaded_by)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (query_id, message_id, saved_filename, orig_filename, file_size, ext, save_path, submitter_id))
                    
                    cursor.execute("""
                        UPDATE messages SET attachment_filename = ?, attachment_path = ? WHERE id = ?
                    """, (orig_filename, saved_filename, message_id))
            
            db.commit()
            
            # Safe Notification Creation to Submitter & Respective Authority
            try:
                create_notification(
                    submitter_id,
                    query_id,
                    'Query Submitted Successfully',
                    f'Your query "#{query_id}: {title}" has been routed to {target_desk}.',
                    'success'
                )
                
                submitter_display = name_input if name_input else (user['name'] if user else ('Faculty Member' if is_faculty_query else 'A Student'))
                notif_title = f"🔴 {priority} Priority Query: {title}" if priority in ['Critical', 'High'] else f"New Query: {title}"
                
                if category == 'Academics':
                    # Notify HOD of this exact department and course/degree
                    if course:
                        dept_hods = db.execute("""
                            SELECT id FROM users 
                            WHERE role = 'hod' AND department = ? AND (course = ? OR course IS NULL)
                        """, (department, course)).fetchall()
                    else:
                        dept_hods = db.execute("SELECT id FROM users WHERE role = 'hod' AND department = ?", (department,)).fetchall()
                        
                    if not dept_hods:
                        dept_hods = db.execute("SELECT id FROM users WHERE role = 'hod' AND department = ?", (department,)).fetchall()
                        
                    for h in dept_hods:
                        create_notification(h['id'], query_id, notif_title, f"New {course or ''} Academic query from {submitter_display} awaiting your staff assignment.", 'urgent' if priority in ['Critical', 'High'] else 'info')
                elif category == 'Administrative':
                    # Notify AO
                    aos = db.execute("SELECT id FROM users WHERE role = 'ao' OR email = 'ao@college.com'").fetchall()
                    for a in aos:
                        create_notification(a['id'], query_id, notif_title, f"New Administrative query from {submitter_display}.", 'urgent' if priority in ['Critical', 'High'] else 'info')
                else:
                    # Others -> Notify Principal
                    principals = db.execute("SELECT id FROM users WHERE role = 'principal' OR role = 'admin' OR email = 'principal@college.com'").fetchall()
                    for p in principals:
                        create_notification(p['id'], query_id, notif_title, f"New Campus Support / Facilities query from {submitter_display}.", 'urgent' if priority in ['Critical', 'High'] else 'info')
            except Exception as notif_err:
                print(f"Notification error bypassed: {notif_err}")

            # Safe SocketIO Emit
            try:
                socketio.emit('new_query_alert', {
                    'query_id': query_id,
                    'title': title,
                    'department': department,
                    'priority': priority,
                    'user_name': name_input if name_input else (user['name'] if user else ('Faculty Member' if is_faculty_query else 'Student')),
                    'user_role': submitter_role,
                    'created_at': now_str
                }, room=f"dept_{department}")
            except Exception as sock_err:
                print(f"Socket emit bypassed: {sock_err}")
                
            return redirect(url_for('query_submitted', query_id=query_id))
            
        except Exception as e:
            db.rollback()
            print(f"Error submitting query: {e}")
            flash(f'An error occurred while submitting your query: {str(e)}', 'danger')
            return render_template('submit_query.html')
        
    return render_template('submit_query.html')

@app.route('/query-submitted/<int:query_id>')
def query_submitted(query_id):
    """Success confirmation page displaying the unique Query ID for tracking."""
    db = get_db()
    query = db.execute("""
        SELECT q.*, u.name as user_name, u.email as user_email, u.roll_no, u.department as student_dept
        FROM queries q
        JOIN users u ON q.user_id = u.id
        WHERE q.id = ?
    """, (query_id,)).fetchone()
    
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('index'))
        
    return render_template('query_success.html', query=query)

@app.route('/track-query', methods=['GET', 'POST'])
def track_query():
    """Direct Query Tracking & Live Two-Way Chat without requiring student password login."""
    query_id_input = request.args.get('query_id') or request.form.get('query_id')
    logged_in_user = get_current_user()

    db = get_db()
    query = None
    messages = []
    attachments = []
    staff_resolver = None
    hod_resolver = None
    submitter_presence = None
    authority_presence = None
    staff_presence = None
    
    # Handle direct reply from tracking page
    if request.method == 'POST' and request.form.get('action') == 'send_reply':
        target_qid = request.form.get('target_query_id')
        reply_text = request.form.get('message', '').strip()
        if target_qid and (reply_text or 'attachment' in request.files):
            q_row = db.execute("SELECT q.*, u.role as user_role FROM queries q JOIN users u ON q.user_id = u.id WHERE q.id = ?", (target_qid,)).fetchone()
            if q_row:
                q_dict = dict(q_row)
                default_sender = 'Faculty (Submitter)' if q_dict.get('user_role') in ['faculty', 'staff'] else 'Student (Submitter)'
                sender_name = request.form.get('sender_name', '').strip() or default_sender
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor = db.cursor()
                cursor.execute("""
                    INSERT INTO messages (query_id, sender_id, message, is_internal_note, created_at)
                    VALUES (?, ?, ?, 0, ?)
                """, (target_qid, q_dict['user_id'], reply_text, now_str))
                msg_id = cursor.lastrowid
                
                # Attachment if any
                if 'attachment' in request.files:
                    file = request.files['attachment']
                    if file and file.filename and allowed_file(file.filename):
                        orig_filename = file.filename
                        ext = orig_filename.rsplit('.', 1)[1].lower()
                        clean_name = secure_filename(orig_filename)
                        saved_filename = f"q{target_qid}_m{msg_id}_{int(datetime.now().timestamp())}_{clean_name}"
                        save_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
                        file.save(save_path)
                        file_size = os.path.getsize(save_path)
                        cursor.execute("""
                            INSERT INTO attachments (query_id, message_id, filename, original_filename, file_size, file_type, filepath, uploaded_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (target_qid, msg_id, saved_filename, orig_filename, file_size, ext, save_path, q_dict['user_id']))
                        cursor.execute("UPDATE messages SET attachment_filename = ?, attachment_path = ? WHERE id = ?", (orig_filename, saved_filename, msg_id))
                        
                cursor.execute("UPDATE queries SET updated_at = ? WHERE id = ?", (now_str, target_qid))
                db.commit()
                
                if q_dict.get('assigned_staff_id'):
                    create_notification(
                        q_dict['assigned_staff_id'],
                        target_qid,
                        f"Student reply on Query #{target_qid}",
                        f"{sender_name}: {reply_text[:60]}...",
                        'message'
                    )
                flash('Your reply has been posted successfully!', 'success')
                return redirect(url_for('track_query', query_id=target_qid))

    if query_id_input:
        clean_id = ''.join(c for c in str(query_id_input) if c.isdigit())
        if clean_id:
            raw_query = db.execute("""
                SELECT q.*, u.name as user_name, u.email as user_email, u.role as user_role, u.roll_no, u.level as user_level, u.course as user_course, u.year as user_year, u.department as user_dept, u.designation as user_designation
                FROM queries q
                JOIN users u ON q.user_id = u.id
                WHERE q.id = ?
            """, (int(clean_id),)).fetchone()
            
            if raw_query:
                query = dict(raw_query)
                messages = db.execute("""
                    SELECT m.*, u.name as sender_name, u.role as sender_role, u.department as sender_department, u.designation as sender_designation
                    FROM messages m
                    JOIN users u ON m.sender_id = u.id
                    WHERE m.query_id = ? AND m.is_internal_note = 0
                    ORDER BY m.created_at ASC
                """, (query['id'],)).fetchall()
                
                attachments = db.execute("""
                    SELECT a.*, u.name as uploader_name
                    FROM attachments a
                    JOIN users u ON a.uploaded_by = u.id
                    WHERE a.query_id = ?
                    ORDER BY a.created_at ASC
                """, (query['id'],)).fetchall()
                
                if query.get('assigned_staff_id'):
                    staff_row = db.execute("SELECT id, name, email, department, designation, phone, role, last_active_at FROM users WHERE id = ?", (query['assigned_staff_id'],)).fetchone()
                    staff_resolver = dict(staff_row) if staff_row else None
                
                query_course = query.get('course')
                if query_course:
                    hod_row = db.execute("""
                        SELECT id, name, email, department, designation, role, last_active_at 
                        FROM users 
                        WHERE role = 'hod' AND department = ? AND (course = ? OR course IS NULL)
                        ORDER BY (CASE WHEN course = ? THEN 1 ELSE 2 END) LIMIT 1
                    """, (query['department'], query_course, query_course)).fetchone()
                else:
                    hod_row = db.execute("SELECT id, name, email, department, designation, role, last_active_at FROM users WHERE role = 'hod' AND department = ? LIMIT 1", (query['department'],)).fetchone()
                hod_resolver = dict(hod_row) if hod_row else None
                
                # Update submitter active status & mark online
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                sub_id = query['user_id']
                try:
                    db.execute("UPDATE users SET last_active_at = ? WHERE id = ?", (now_str, sub_id))
                    db.commit()
                except Exception:
                    pass
                if sub_id not in ONLINE_USERS:
                    ONLINE_USERS[sub_id] = set()
                    
                # 1. Submitter Presence
                sub_row = db.execute("SELECT id, name, role, department, course, level, year, roll_no, designation, last_active_at FROM users WHERE id = ?", (sub_id,)).fetchone()
                sub_dict = dict(sub_row) if sub_row else {}
                is_fac = (sub_dict.get('role') in ['faculty', 'staff']) or (query.get('user_role') in ['faculty', 'staff'])
                sub_role_display = 'Student'
                if sub_dict:
                    if is_fac:
                        desig_str = sub_dict.get('designation') or query.get('user_designation') or 'Faculty'
                        prog_str = f"{query.get('course') or sub_dict.get('course') or ''} {sub_dict.get('department') or query.get('department') or ''}".strip()
                        sub_role_display = f"{desig_str} ({prog_str})".strip()
                    elif sub_dict.get('role') == 'student':
                        c_info = f"{sub_dict.get('course') or query.get('course') or 'UG'} {sub_dict.get('department') or query.get('department') or ''}".strip()
                        y_info = f" - Yr {sub_dict.get('year') or query.get('year')}" if (sub_dict.get('year') or query.get('year')) else ""
                        sub_role_display = f"Student ({c_info}{y_info})"
                    else:
                        sub_role_display = sub_dict.get('role', '').capitalize()
                elif is_fac:
                    sub_role_display = f"Faculty ({query.get('department') or ''})"
                        
                submitter_presence = {
                    'id': sub_dict.get('id', sub_id),
                    'name': sub_dict.get('name') or ('Faculty Member' if is_fac else 'Student Submitter'),
                    'role': sub_role_display,
                    'is_student': not is_fac,
                    'is_faculty': is_fac,
                    'department': sub_dict.get('department') or query.get('department'),
                    'course': sub_dict.get('course') or query.get('course'),
                    'year': sub_dict.get('year') or query.get('year'),
                    'roll_no': sub_dict.get('roll_no') or query.get('roll_no'),
                    'is_online': True,
                    'last_active': 'Just now'
                }

                # 2. Governing Authority Presence (Academics -> HOD, Administrative -> AO, Others -> Principal)
                authority_presence = None
                q_cat = query.get('category', 'Academics')
                if q_cat == 'Administrative':
                    ao_row = db.execute("SELECT id, name, email, role, department, designation, last_active_at FROM users WHERE role = 'ao' ORDER BY id LIMIT 1").fetchone()
                    if ao_row:
                        ao_dict = dict(ao_row)
                        ao_online = ao_dict['id'] in ONLINE_USERS
                        authority_presence = {
                            'id': ao_dict['id'],
                            'name': ao_dict['name'],
                            'email': ao_dict['email'],
                            'role_type': 'ao',
                            'role_title': 'Administrative Officer (AO)',
                            'icon': '🏢',
                            'department': 'Administrative Wing',
                            'designation': ao_dict.get('designation') or 'Administrative Officer',
                            'is_online': ao_online,
                            'last_active': 'Just now' if ao_online else ao_dict.get('last_active_at')
                        }
                elif q_cat == 'Others':
                    prin_row = db.execute("SELECT id, name, email, role, department, designation, last_active_at FROM users WHERE role = 'principal' ORDER BY id LIMIT 1").fetchone()
                    if prin_row:
                        prin_dict = dict(prin_row)
                        prin_online = prin_dict['id'] in ONLINE_USERS
                        authority_presence = {
                            'id': prin_dict['id'],
                            'name': prin_dict['name'],
                            'email': prin_dict['email'],
                            'role_type': 'principal',
                            'role_title': 'Principal Executive Desk',
                            'icon': '🏛️',
                            'department': 'College Leadership',
                            'designation': prin_dict.get('designation') or 'Principal',
                            'is_online': prin_online,
                            'last_active': 'Just now' if prin_online else prin_dict.get('last_active_at')
                        }
                else: # Academics
                    if hod_resolver:
                        hod_online = hod_resolver['id'] in ONLINE_USERS
                        authority_presence = {
                            'id': hod_resolver['id'],
                            'name': hod_resolver['name'],
                            'email': hod_resolver['email'],
                            'role_type': 'hod',
                            'role_title': f"{query_course or ''} Branch HOD".strip(),
                            'icon': '🎓',
                            'department': hod_resolver.get('department') or query.get('department'),
                            'designation': hod_resolver.get('designation') or 'Head of Department',
                            'is_online': hod_online,
                            'last_active': 'Just now' if hod_online else hod_resolver.get('last_active_at')
                        }

                # 3. Staff Resolver Presence
                staff_presence = None
                if staff_resolver:
                    staff_online = staff_resolver['id'] in ONLINE_USERS
                    if staff_resolver.get('role') == 'hod':
                        role_label = 'Assigned Head of Dept (HOD)'
                        desig_label = staff_resolver.get('designation') or 'Head of Department'
                    elif staff_resolver.get('role') == 'office_staff':
                        role_label = 'Office Staff Resolver'
                        desig_label = staff_resolver.get('designation') or 'Office Staff'
                    else:
                        role_label = 'Assigned Staff Resolver'
                        desig_label = staff_resolver.get('designation') or 'Department Staff'

                    staff_presence = {
                        'id': staff_resolver['id'],
                        'name': staff_resolver['name'],
                        'role': role_label,
                        'role_type': staff_resolver.get('role'),
                        'department': staff_resolver.get('department') or query.get('department'),
                        'designation': desig_label,
                        'is_online': staff_online,
                        'last_active': 'Just now' if staff_online else staff_resolver.get('last_active_at')
                    }
            else:
                query = None
                flash(f'No query found with ID #{query_id_input}. Please verify your Query ID and try again.', 'warning')
        else:
            query = None
            flash(f'Invalid Query ID "{query_id_input}". Please enter a valid numeric ID (e.g. 1042).', 'warning')
                
    return render_template(
        'track_query.html',
        query=query,
        messages=messages,
        attachments=attachments,
        staff_resolver=staff_resolver,
        hod_resolver=hod_resolver,
        submitter_presence=submitter_presence if query else None,
        authority_presence=authority_presence if query else None,
        staff_presence=staff_presence if query else None,
        query_id_input=query_id_input
    )

@app.route('/query/<int:query_id>')
@login_required
def query_details(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("""
        SELECT q.*, u.name as user_name, u.email as user_email, u.role as user_role, u.roll_no, u.phone,
               u.designation as user_designation, u.level as user_level, u.course as user_course,
               staff.name as staff_name, staff.email as staff_email, staff.department as staff_department,
               staff.designation as staff_designation, staff.phone as staff_phone
        FROM queries q
        JOIN users u ON q.user_id = u.id
        LEFT JOIN users staff ON q.assigned_staff_id = staff.id
        WHERE q.id = ?
    """, (query_id,)).fetchone()
    
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('dashboard'))
        
    # Authorization checks:
    is_submitter = (user['id'] == query['user_id'])
    is_admin = (user['role'] in ['admin', 'principal'])
    is_ao = (user['role'] == 'ao')
    is_hod = (user['role'] == 'hod')
    is_assigned = (query['assigned_staff_id'] == user['id'])
    is_staff = (user['role'] in ['staff', 'office_staff', 'faculty'])
    
    # Submitter, Central Admin, Principal, AO, HOD, Assigned Resolver, or Department Staff can access
    if not (is_submitter or is_admin or is_ao or is_hod or is_assigned or is_staff):
        flash('Access restricted: You do not have permission to view this query.', 'warning')
        if user['role'] in ['staff', 'office_staff', 'faculty', 'hod', 'ao']:
            return redirect(url_for('department_dashboard'))
        return redirect(url_for('dashboard'))
        
    # Fetch Messages
    messages = db.execute("""
        SELECT m.*, u.name as sender_name, u.role as sender_role, u.department as sender_department
        FROM messages m
        JOIN users u ON m.sender_id = u.id
        WHERE m.query_id = ?
        ORDER BY m.created_at ASC
    """, (query_id,)).fetchall()
    
    # Filter internal notes if student or faculty
    visible_messages = []
    for msg in messages:
        if msg['is_internal_note'] and user['role'] in ['student', 'faculty']:
            continue
        visible_messages.append(msg)
        
    # Attachments
    attachments = db.execute("""
        SELECT a.*, u.name as uploader_name
        FROM attachments a
        JOIN users u ON a.uploaded_by = u.id
        WHERE a.query_id = ?
        ORDER BY a.created_at ASC
    """, (query_id,)).fetchall()
    
    # Department Staff & Admins list for assignment
    if user['role'] == 'hod':
        if user.get('course'):
            dept_staff = db.execute(
                "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty') AND (department = ? OR department IS NULL) AND (course = ? OR course IS NULL) AND is_active = 1 ORDER BY name ASC",
                (user['department'], user['course'])
            ).fetchall()
        else:
            dept_staff = db.execute(
                "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty') AND (department = ? OR department IS NULL) AND is_active = 1 ORDER BY name ASC",
                (user['department'],)
            ).fetchall()
            
        if not dept_staff:
            dept_staff = db.execute(
                "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty') AND is_active = 1 ORDER BY name ASC"
            ).fetchall()
    elif user['role'] == 'ao':
        # AO assigns Office Staff / Administrative Staff
        dept_staff = db.execute(
            "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('office_staff', 'staff') AND (department = 'Administrative' OR department IS NULL) AND is_active = 1 ORDER BY name ASC"
        ).fetchall()
        if not dept_staff:
            dept_staff = db.execute(
                "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('office_staff', 'staff') AND is_active = 1 ORDER BY name ASC"
            ).fetchall()
    else:
        dept_staff = db.execute(
            "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'office_staff', 'faculty', 'admin') AND is_active = 1 ORDER BY department ASC, name ASC"
        ).fetchall()
    
    # Audit Logs
    audit_logs = db.execute("""
        SELECT a.*, u.name as actor_name
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE a.query_id = ?
        ORDER BY a.created_at DESC
    """, (query_id,)).fetchall()
    
    # Calculate Live Presence & Online Status for all 3 key parties: Submitter, Governing Authority (HOD/AO/Principal), and Assigned Staff
    # 1. Submitter Presence
    sub_row = db.execute("SELECT id, name, role, department, course, level, year, roll_no, last_active_at FROM users WHERE id = ?", (query['user_id'],)).fetchone()
    
    sub_is_online = False
    if sub_row:
        if (sub_row['id'] in ONLINE_USERS) or (user and user['id'] == sub_row['id']):
            sub_is_online = True
        elif sub_row['last_active_at']:
            try:
                sub_dt = datetime.strptime(sub_row['last_active_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                if (datetime.now() - sub_dt).total_seconds() < 900:
                    sub_is_online = True
            except Exception:
                pass
                
    try:
        q_dt = datetime.strptime(query['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
        if (datetime.now() - q_dt).total_seconds() < 900:
            sub_is_online = True
    except Exception:
        pass

    sub_role_display = 'Student'
    if sub_row:
        if sub_row['role'] == 'student':
            c_info = f"{sub_row['course'] or query['course'] or 'UG'} {sub_row['department'] or query['department'] or ''}".strip()
            y_info = f" - Yr {sub_row['year'] or query['year']}" if (sub_row['year'] or query['year']) else ""
            sub_role_display = f"Student ({c_info}{y_info})"
        elif sub_row['role'] in ['faculty', 'staff']:
            desig_txt = (sub_row['designation'] if 'designation' in sub_row.keys() and sub_row['designation'] else None) or 'Faculty'
            prog_txt = f"{query['course'] or sub_row['course'] or ''} {sub_row['department'] or query['department'] or ''}".strip()
            sub_role_display = f"{desig_txt} ({prog_txt})".strip()
        else:
            sub_role_display = sub_row['role'].capitalize()
            
    submitter_presence = {
        'id': sub_row['id'] if sub_row else query['user_id'],
        'name': sub_row['name'] if sub_row else 'Student Submitter',
        'role': sub_role_display,
        'is_student': (sub_row['role'] == 'student') if sub_row else True,
        'is_faculty': (sub_row['role'] in ['faculty', 'staff']) if sub_row else False,
        'department': sub_row['department'] if (sub_row and sub_row['department']) else query['department'],
        'course': sub_row['course'] if (sub_row and sub_row['course']) else (query['course'] if 'course' in query.keys() else None),
        'year': sub_row['year'] if (sub_row and sub_row['year']) else (query['year'] if 'year' in query.keys() else None),
        'roll_no': sub_row['roll_no'] if (sub_row and sub_row['roll_no']) else (query['roll_no'] if 'roll_no' in query.keys() else None),
        'is_online': sub_is_online,
        'last_active': 'Just now' if sub_is_online else (sub_row['last_active_at'] if sub_row else query['created_at'])
    }

    # 2. Governing Authority Presence (Academics -> Branch HOD, Administrative -> AO, Others -> Principal)
    authority_presence = None
    q_cat = query['category']
    
    if q_cat == 'Administrative':
        ao_row = db.execute("SELECT id, name, email, role, department, designation, last_active_at FROM users WHERE role = 'ao' ORDER BY id LIMIT 1").fetchone()
        if ao_row:
            ao_online = (ao_row['id'] in ONLINE_USERS) or (user and user['id'] == ao_row['id'])
            authority_presence = {
                'id': ao_row['id'],
                'name': ao_row['name'],
                'email': ao_row['email'],
                'role_type': 'ao',
                'role_title': 'Administrative Officer (AO)',
                'icon': '🏢',
                'department': 'Administrative Wing',
                'designation': ao_row['designation'] or 'Administrative Officer',
                'is_online': ao_online,
                'last_active': 'Just now' if ao_online else ao_row['last_active_at']
            }
    elif q_cat == 'Others':
        prin_row = db.execute("SELECT id, name, email, role, department, designation, last_active_at FROM users WHERE role = 'principal' ORDER BY id LIMIT 1").fetchone()
        if prin_row:
            prin_online = (prin_row['id'] in ONLINE_USERS) or (user and user['id'] == prin_row['id'])
            authority_presence = {
                'id': prin_row['id'],
                'name': prin_row['name'],
                'email': prin_row['email'],
                'role_type': 'principal',
                'role_title': 'Principal Executive Desk',
                'icon': '🏛️',
                'department': 'College Leadership',
                'designation': prin_row['designation'] or 'Principal',
                'is_online': prin_online,
                'last_active': 'Just now' if prin_online else prin_row['last_active_at']
            }
    else: # Academics
        hod_row = None
        target_dept = query['department'] or (sub_row['department'] if sub_row else None)
        target_course = query['course'] if ('course' in query.keys() and query['course']) else (sub_row['course'] if sub_row and 'course' in sub_row.keys() else None)
        
        if target_dept and target_course:
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND department = ? AND course = ?
                ORDER BY id DESC LIMIT 1
            """, (target_dept, target_course)).fetchone()
            
        if not hod_row and target_dept:
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND department = ?
                ORDER BY id DESC LIMIT 1
            """, (target_dept,)).fetchone()
            
        if not hod_row and target_course:
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND course = ?
                ORDER BY id DESC LIMIT 1
            """, (target_course,)).fetchone()
            
        if not hod_row and target_dept not in ['Academics', 'Administrative', 'Others']:
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND (department LIKE ? OR ? LIKE '%' || department || '%')
                ORDER BY id DESC LIMIT 1
            """, (f"%{target_dept}%", target_dept)).fetchone()
            
        if not hod_row:
            hod_row = db.execute("SELECT id, name, email, role, department, designation, last_active_at FROM users WHERE role = 'hod' ORDER BY id LIMIT 1").fetchone()
            
        if hod_row:
            hod_online = (hod_row['id'] in ONLINE_USERS) or (user and user['id'] == hod_row['id'])
            authority_presence = {
                'id': hod_row['id'],
                'name': hod_row['name'],
                'email': hod_row['email'],
                'role_type': 'hod',
                'role_title': f"{target_course or ''} Branch HOD".strip(),
                'icon': '🎓',
                'department': hod_row['department'] or query['department'],
                'designation': hod_row['designation'] or 'Head of Department',
                'is_online': hod_online,
                'last_active': 'Just now' if hod_online else hod_row['last_active_at']
            }
            
    hod_presence = authority_presence

    # 3. Assigned Staff / Resolver Presence
    staff_presence = None
    if query['assigned_staff_id']:
        staff_row = db.execute("SELECT id, name, role, department, designation, last_active_at FROM users WHERE id = ?", (query['assigned_staff_id'],)).fetchone()
        if staff_row:
            staff_online = (staff_row['id'] in ONLINE_USERS) or (user and user['id'] == staff_row['id'])
            if staff_row['role'] == 'hod':
                role_label = 'Assigned Head of Dept (HOD)'
                desig_label = staff_row['designation'] or 'Head of Department'
            elif staff_row['role'] == 'office_staff':
                role_label = 'Office Staff Resolver'
                desig_label = staff_row['designation'] or 'Office Staff'
            else:
                role_label = 'Assigned Staff Resolver'
                desig_label = staff_row['designation'] or 'Department Staff'

            staff_presence = {
                'id': staff_row['id'],
                'name': staff_row['name'],
                'role': role_label,
                'role_type': staff_row['role'],
                'department': staff_row['department'] or query['department'],
                'designation': desig_label,
                'is_online': staff_online,
                'last_active': 'Just now' if staff_online else staff_row['last_active_at']
            }

    # Flag if query is assigned to currently logged-in HOD
    is_assigned_to_current_hod = bool(user and user['role'] == 'hod' and query['assigned_staff_id'] == user['id'])

    # Complete lists of HODs and Staff Resolvers for Principal & Admin assignment selection
    all_hods = db.execute("""
        SELECT id, name, email, role, level, course, department, designation 
        FROM users 
        WHERE role = 'hod' AND is_active = 1 
        ORDER BY level ASC, course ASC, name ASC
    """).fetchall()

    all_staff = db.execute("""
        SELECT id, name, email, role, level, course, department, designation 
        FROM users 
        WHERE role IN ('staff', 'office_staff', 'faculty') AND is_active = 1 
        ORDER BY department ASC, name ASC
    """).fetchall()

    return render_template(
        'query_details.html',
        query=query,
        messages=visible_messages,
        attachments=attachments,
        dept_staff=dept_staff,
        all_hods=all_hods,
        all_staff=all_staff,
        audit_logs=audit_logs,
        submitter_presence=submitter_presence,
        authority_presence=authority_presence,
        staff_presence=staff_presence,
        hod_presence=hod_presence,
        is_assigned_to_current_hod=is_assigned_to_current_hod
    )






@app.route('/query/<int:query_id>/message', methods=['POST'])
@login_required
def post_message(query_id):
    user = get_current_user()
    db = get_db()
    
    # Chief Admin monitors queries and manages staff assignments without direct chat participation
    if user['role'] == 'admin':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'error': 'Chief administrators oversee queries without direct chat participation.'}), 403
        flash('Chief administrators oversee queries without direct chat participation.', 'info')
        return redirect(url_for('query_details', query_id=query_id))

    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query:
        return jsonify({'error': 'Query not found'}), 404
        
    # Permission check: Allowed for Submitter, Assigned Staff/Faculty Resolver, Branch HOD, AO, Principal, Admin, or Department Staff
    is_submitter = (user['id'] == query['user_id'])
    is_assigned_staff = (query['assigned_staff_id'] == user['id'])
    is_branch_hod = (user['role'] == 'hod')
    is_staff = (user['role'] in ['staff', 'office_staff', 'faculty'])
    is_ao = (user['role'] == 'ao')
    is_principal = (user['role'] == 'principal')
    is_admin = (user['role'] == 'admin')
    
    if not (is_submitter or is_assigned_staff or is_branch_hod or is_staff or is_ao or is_principal or is_admin):
        return jsonify({'error': 'Unauthorized to participate in this query chat.'}), 403
        
    message_text = request.form.get('message', '').strip()
    is_internal_note = 1 if request.form.get('is_internal_note') == 'true' and (user['role'] in ['staff', 'office_staff', 'hod', 'ao', 'principal', 'admin'] or (user['role'] == 'faculty' and query['assigned_staff_id'] == user['id'])) else 0
    
    if not message_text and 'attachment' not in request.files:
        return jsonify({'error': 'Message cannot be empty'}), 400
        
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor = db.cursor()
    
    cursor.execute("""
        INSERT INTO messages (query_id, sender_id, message, is_internal_note, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (query_id, user['id'], message_text, is_internal_note, now_str))
    message_id = cursor.lastrowid
    
    # Handle optional attachment
    saved_filename = None
    orig_filename = None
    if 'attachment' in request.files:
        file = request.files['attachment']
        if file and file.filename and allowed_file(file.filename):
            orig_filename = file.filename
            ext = orig_filename.rsplit('.', 1)[1].lower()
            clean_name = secure_filename(orig_filename)
            saved_filename = f"q{query_id}_m{message_id}_{int(datetime.now().timestamp())}_{clean_name}"
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], saved_filename)
            file.save(save_path)
            file_size = os.path.getsize(save_path)
            
            cursor.execute("""
                INSERT INTO attachments (query_id, message_id, filename, original_filename, file_size, file_type, filepath, uploaded_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (query_id, message_id, saved_filename, orig_filename, file_size, ext, save_path, user['id']))
            
            cursor.execute("UPDATE messages SET attachment_filename = ?, attachment_path = ? WHERE id = ?", (orig_filename, saved_filename, message_id))

    # Update first_response_at if staff/office_staff/hod/ao/admin responded for the first time
    if user['role'] in ['staff', 'office_staff', 'hod', 'ao', 'principal', 'admin', 'faculty'] and not is_submitter and not is_internal_note:
        if not query['first_response_at']:
            cursor.execute("UPDATE queries SET first_response_at = ? WHERE id = ?", (now_str, query_id))
            
        # If query was New or Waiting for User, update status to In Progress
        if query['status'] in ['New', 'Waiting for User']:
            cursor.execute("UPDATE queries SET status = 'In Progress' WHERE id = ?", (query_id,))
            
    # If submitter replies, change status to In Progress if it was Waiting for User
    if is_submitter and query['status'] == 'Waiting for User':
        cursor.execute("UPDATE queries SET status = 'In Progress' WHERE id = ?", (query_id,))
        
    cursor.execute("UPDATE queries SET updated_at = ? WHERE id = ?", (now_str, query_id))
    
    # Safe Notifications
    try:
        if is_submitter:
            # Notify assigned staff or department
            if query['assigned_staff_id']:
                create_notification(
                    query['assigned_staff_id'],
                    query_id,
                    f"New reply on Query #{query_id}",
                    f"{user['name']} replied: {message_text[:60]}...",
                    'message'
                )
        elif not is_internal_note:
            # Notify query owner
            sender_role_label = 'HOD' if user['role'] == 'hod' else ('AO' if user['role'] == 'ao' else ('Office Staff' if user['role'] == 'office_staff' else 'Staff'))
            create_notification(
                query['user_id'],
                query_id,
                f"Department reply on Query #{query_id}",
                f"{user['name']} ({user['department'] or sender_role_label}): {message_text[:60]}...",
                'message'
            )
    except Exception as e:
        print(f"Chat notification notice: {e}")
        
    db.commit()
    
    msg_data = {
        'id': message_id,
        'query_id': query_id,
        'sender_id': user['id'],
        'sender_name': user['name'],
        'sender_role': user['role'],
        'message': message_text,
        'is_internal_note': bool(is_internal_note),
        'attachment_filename': orig_filename,
        'attachment_path': saved_filename,
        'created_at': now_str,
        'timeago': 'Just now'
    }
    
    # Broadcast to room
    try:
        socketio.emit('chat_message', msg_data, room=f"query_{query_id}")
    except Exception as e:
        print(f"Socket emit notice: {e}")
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return jsonify({'status': 'success', 'message': msg_data})
    
    flash('Message sent successfully.', 'success')
    return redirect(url_for('query_details', query_id=query_id))

@app.route('/query/<int:query_id>/status', methods=['POST'])
@login_required
@role_required(['staff', 'office_staff', 'hod', 'admin', 'faculty', 'ao', 'principal'])
def update_query_status(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('department_dashboard'))
        
    # Allowed for assigned staff member, office staff, department staff, HOD, AO, Principal, or central admin
    can_update = (
        user['role'] in ['admin', 'principal', 'hod', 'ao', 'staff', 'office_staff'] or 
        query['assigned_staff_id'] == user['id'] or
        (user['role'] == 'faculty' and query['assigned_staff_id'] == user['id'])
    )
    if not can_update:
        flash('Permission restricted: Only the assigned Resolver, Department Head, or Admin can update the query status.', 'danger')
        return redirect(url_for('query_details', query_id=query_id))
        
    new_status = request.form.get('status')
    if new_status not in Config.STATUSES:
        flash('Invalid status selected.', 'danger')
        return redirect(url_for('query_details', query_id=query_id))
        
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    resolved_at = now_str if new_status == 'Resolved' else None
    
    cursor = db.cursor()
    if new_status == 'Resolved':
        cursor.execute("""
            UPDATE queries SET status = ?, resolved_at = ?, updated_at = ? WHERE id = ?

        """, (new_status, resolved_at, now_str, query_id))
    else:
        cursor.execute("""
            UPDATE queries SET status = ?, updated_at = ? WHERE id = ?
        """, (new_status, now_str, query_id))
        
    # Audit log
    cursor.execute("""
        INSERT INTO audit_logs (query_id, user_id, action, details)
        VALUES (?, ?, 'Status Change', ?)
    """, (query_id, user['id'], f"Status changed from '{query['status']}' to '{new_status}'"))
    
    # Notification for user
    create_notification(
        query['user_id'],
        query_id,
        f"Status Updated: Query #{query_id}",
        f"Your query status is now marked as '{new_status}'.",
        'success' if new_status == 'Resolved' else 'info'
    )
    
    db.commit()
    
    # Broadcast event
    socketio.emit('status_update', {
        'query_id': query_id,
        'status': new_status,
        'updated_at': now_str
    }, room=f"query_{query_id}")
    
    flash(f'Query status successfully updated to {new_status}.', 'success')
    return redirect(url_for('query_details', query_id=query_id))

@app.route('/query/<int:query_id>/reassign', methods=['POST'])
@login_required
@role_required(['staff', 'office_staff', 'hod', 'admin', 'ao', 'principal'])
def reassign_query(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('dashboard'))
        
    action_type = request.form.get('action_type', '').strip()
    new_dept = request.form.get('department')
    new_staff_id = request.form.get('assigned_staff_id')
    new_priority = request.form.get('priority')
    
    # Quick Action: HOD or Staff takes the query directly
    if action_type == 'take_query':
        new_staff_id = str(user['id'])
    
    cursor = db.cursor()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_details = []
    
    if new_dept and new_dept in Config.DEPARTMENTS and new_dept != query['department']:
        cursor.execute("""
            UPDATE queries SET department = ?, is_routed_manually = 1, updated_at = ? WHERE id = ?
        """, (new_dept, now_str, query_id))
        log_details.append(f"Department re-routed from {query['department']} to {new_dept}")
        
        # Broadcast to new department room
        socketio.emit('new_query_alert', {
            'query_id': query_id,
            'title': query['title'],
            'department': new_dept,
            'priority': query['priority'],
            'created_at': now_str
        }, room=f"dept_{new_dept}")
        
    if new_priority and new_priority in Config.PRIORITIES and new_priority != query['priority']:
        cursor.execute("""
            UPDATE queries SET priority = ?, updated_at = ? WHERE id = ?
        """, (new_priority, now_str, query_id))
        log_details.append(f"Priority changed to {new_priority}")
        
    if new_staff_id is not None:
        staff_val = int(new_staff_id) if new_staff_id != "" and new_staff_id != "0" else None
        
        # Determine status update
        new_status = 'In Progress' if (action_type == 'take_query' or (staff_val == user['id'] and user['role'] == 'hod')) else ('Assigned' if query['status'] == 'New' else query['status'])
        
        cursor.execute("""
            UPDATE queries SET assigned_staff_id = ?, status = ?, updated_at = ? WHERE id = ?
        """, (staff_val, new_status, now_str, query_id))
        
        if staff_val:
            assigned_target = db.execute("SELECT id, name, role, department, designation FROM users WHERE id = ?", (staff_val,)).fetchone()
            if assigned_target:
                target_name = assigned_target['name']
                target_role = assigned_target['role']
                target_desig = assigned_target['designation'] or ('Head of Department' if target_role == 'hod' else 'Staff')
                
                if staff_val == user['id'] and user['role'] == 'hod':
                    # HOD self-assigns / takes ownership to resolve directly
                    log_details.append(f"HOD {user['name']} self-assigned query to resolve directly")
                    create_notification(
                        query['user_id'],
                        query_id,
                        '🎓 Query In Progress with HOD',
                        f"Department Head {user['name']} has taken your query #{query_id} to resolve directly.",
                        'info'
                    )
                elif user['role'] in ['principal', 'admin'] and target_role == 'hod':
                    # Principal or Admin assigns query to HOD
                    log_details.append(f"Assigned by Principal to HOD {target_name}")
                    create_notification(
                        staff_val,
                        query_id,
                        '🏛️ Query Assigned by Principal',
                        f"Principal assigned Query #{query_id} to you: '{query['title']}'. You can resolve it directly or assign to department staff.",
                        'urgent' if query['priority'] in ['Critical', 'High'] else 'info'
                    )
                    create_notification(
                        query['user_id'],
                        query_id,
                        'Query Assigned to HOD',
                        f"Your query #{query_id} has been assigned to Head of Department ({target_name}) for resolution.",
                        'info'
                    )
                elif user['role'] == 'hod':
                    # HOD delegates to staff/faculty member
                    log_details.append(f"Delegated by HOD {user['name']} to {target_name} ({target_desig})")
                    create_notification(
                        staff_val,
                        query_id,
                        '🎓 Query Assigned by HOD',
                        f"HOD {user['name']} assigned Query #{query_id} to you: '{query['title']}'.",
                        'urgent' if query['priority'] in ['Critical', 'High'] else 'info'
                    )
                    create_notification(
                        query['user_id'],
                        query_id,
                        'Staff Resolver Assigned',
                        f"Your query #{query_id} has been assigned to staff resolver {target_name} ({target_desig}) by Department HOD.",
                        'info'
                    )
                else:
                    log_details.append(f"Assigned to {target_name} ({target_desig})")
                    create_notification(
                        staff_val,
                        query_id,
                        'Query Assigned',
                        f"You have been assigned Query #{query_id}: {query['title']}",
                        'info'
                    )
                    create_notification(
                        query['user_id'],
                        query_id,
                        'Resolver Assigned',
                        f"Your query #{query_id} has been assigned to {target_name}.",
                        'info'
                    )
        else:
            log_details.append("Unassigned staff resolver")

    if log_details:
        cursor.execute("""
            INSERT INTO audit_logs (query_id, user_id, action, details)
            VALUES (?, ?, 'Query Assignment & Routing', ?)
        """, (query_id, user['id'], "; ".join(log_details)))
        
    db.commit()
    
    # Broadcast status / assignment update
    socketio.emit('status_update', {
        'query_id': query_id,
        'status': query['status'],
        'assigned_staff_id': new_staff_id,
        'updated_at': now_str
    }, room=f"query_{query_id}")
    
    flash('Query assignments and resolution flow updated successfully.', 'success')
    return redirect(url_for('query_details', query_id=query_id))

@app.route('/query/<int:query_id>/feedback', methods=['POST'])
@login_required
def submit_feedback(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query or query['user_id'] != user['id']:
        flash('Unauthorized or invalid query.', 'danger')
        return redirect(url_for('dashboard'))
        
    rating = int(request.form.get('rating', 5))
    rating = max(1, min(5, rating))
    comment = request.form.get('comment', '').strip()
    
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO feedback (query_id, user_id, rating, comment)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(query_id) DO UPDATE SET rating = excluded.rating, comment = excluded.comment
    """, (query_id, user['id'], rating, comment))
    
    cursor.execute("""
        INSERT INTO audit_logs (query_id, user_id, action, details)
        VALUES (?, ?, 'Feedback Submitted', ?)
    """, (query_id, user['id'], f"Rated {rating} stars: {comment[:40]}"))
    
    db.commit()
    flash('Thank you! Your resolution feedback has been submitted.', 'success')
    return redirect(url_for('query_details', query_id=query_id))

@app.route('/query/<int:query_id>/reopen', methods=['POST'])
@login_required
def reopen_query(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query or (query['user_id'] != user['id'] and user['role'] not in ['staff', 'admin']):
        flash('Unauthorized.', 'danger')
        return redirect(url_for('dashboard'))
        
    reason = request.form.get('reason', 'User requested to reopen the query.').strip()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor = db.cursor()
    cursor.execute("""
        UPDATE queries SET status = 'Reopened', updated_at = ? WHERE id = ?
    """, (now_str, query_id))
    
    # Post message explaining reopening
    cursor.execute("""
        INSERT INTO messages (query_id, sender_id, message, created_at)
        VALUES (?, ?, ?, ?)
    """, (query_id, user['id'], f"[QUERY REOPENED]: {reason}", now_str))
    
    cursor.execute("""
        INSERT INTO audit_logs (query_id, user_id, action, details)
        VALUES (?, ?, 'Query Reopened', ?)
    """, (query_id, user['id'], reason))
    
    # Notify department staff
    dept_staff = db.execute("SELECT id FROM users WHERE department = ? AND role = 'staff'", (query['department'],)).fetchall()
    for staff in dept_staff:
        create_notification(staff['id'], query_id, f"Query #{query_id} Reopened", f"{user['name']} reopened query: {reason[:60]}", 'urgent')
        
    db.commit()
    
    socketio.emit('status_update', {
        'query_id': query_id,
        'status': 'Reopened',
        'updated_at': now_str
    }, room=f"query_{query_id}")
    
    flash('Query has been reopened and department staff notified.', 'warning')
    return redirect(url_for('query_details', query_id=query_id))

@app.route('/uploads/<filename>')
@login_required
def download_attachment(filename):
    """Securely serve uploaded attachments."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# -------------------------------------------------------------
# FACULTY WORKSPACE SELECTOR
# -------------------------------------------------------------

@app.route('/faculty-choice')
@login_required
@role_required(['faculty'])
def faculty_choice():
    return render_template('faculty_choice.html')

# -------------------------------------------------------------
# DEPARTMENT RESOLUTION QUEUE (STAFF & FACULTY)
# -------------------------------------------------------------

@app.route('/department-dashboard')
@login_required
@role_required(['staff', 'office_staff', 'hod', 'admin', 'faculty', 'ao', 'principal'])
def department_dashboard():
    user = get_current_user()
    is_resolver = user['role'] in ['staff', 'office_staff', 'faculty']
    
    dept_param = request.args.get('dept')
    if is_resolver:
        if user['role'] == 'office_staff':
            dept = dept_param if dept_param else 'Administrative'
        else:
            dept = dept_param if dept_param else (user['department'] if user['department'] else 'All Departments')
    elif user['role'] == 'ao':
        dept = dept_param if dept_param else 'Administrative'
    elif user['role'] in ['principal', 'admin']:
        dept = dept_param if dept_param else 'All'
    else:
        dept = dept_param if dept_param else (user['department'] if user['department'] else 'Academics')
    
    db = get_db()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Compute stats — single aggregation query per role branch instead of 5 separate SELECTs
    if is_resolver:
        s = db.execute("""
            SELECT
                SUM(CASE WHEN status IN ('New','Assigned') THEN 1 ELSE 0 END) as new,
                SUM(CASE WHEN priority IN ('Critical','Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN priority = 'High' AND status != 'Resolved' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN status IN ('Assigned','In Progress') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?) THEN 1 ELSE 0 END) as resolved_today
            FROM queries WHERE assigned_staff_id = ?
        """, (f"{today_str}%", f"{today_str}%", user['id'])).fetchone()
        stats = {'new': s['new'] or 0, 'urgent': s['urgent'] or 0, 'high': s['high'] or 0,
                 'in_progress': s['in_progress'] or 0, 'resolved_today': s['resolved_today'] or 0}
        resp_rows = db.execute("""
            SELECT created_at, first_response_at FROM queries 
            WHERE assigned_staff_id = ? AND first_response_at IS NOT NULL
        """, (user['id'],)).fetchall()
    elif user['role'] == 'hod' and user.get('course'):
        hod_c = user['course']
        s = db.execute("""
            SELECT
                SUM(CASE WHEN status = 'New' THEN 1 ELSE 0 END) as new,
                SUM(CASE WHEN priority IN ('Critical','Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN priority = 'High' AND status != 'Resolved' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN status IN ('Assigned','In Progress') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?) THEN 1 ELSE 0 END) as resolved_today
            FROM queries
            WHERE (((department = ? OR ? = 'All') AND (course = ? OR course IS NULL)) OR assigned_staff_id = ?)
        """, (f"{today_str}%", f"{today_str}%", dept, dept, hod_c, user['id'])).fetchone()
        stats = {'new': s['new'] or 0, 'urgent': s['urgent'] or 0, 'high': s['high'] or 0,
                 'in_progress': s['in_progress'] or 0, 'resolved_today': s['resolved_today'] or 0}
        resp_rows = db.execute("""
            SELECT created_at, first_response_at FROM queries 
            WHERE (((department = ? OR ? = 'All') AND (course = ? OR course IS NULL)) OR assigned_staff_id = ?) AND first_response_at IS NOT NULL
        """, (dept, dept, hod_c, user['id'])).fetchall()
    elif user['role'] == 'hod':
        s = db.execute("""
            SELECT
                SUM(CASE WHEN status = 'New' THEN 1 ELSE 0 END) as new,
                SUM(CASE WHEN priority IN ('Critical','Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN priority = 'High' AND status != 'Resolved' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN status IN ('Assigned','In Progress') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?) THEN 1 ELSE 0 END) as resolved_today
            FROM queries
            WHERE (department = ? OR ? = 'All' OR assigned_staff_id = ?)
        """, (f"{today_str}%", f"{today_str}%", dept, dept, user['id'])).fetchone()
        stats = {'new': s['new'] or 0, 'urgent': s['urgent'] or 0, 'high': s['high'] or 0,
                 'in_progress': s['in_progress'] or 0, 'resolved_today': s['resolved_today'] or 0}
        resp_rows = db.execute("""
            SELECT created_at, first_response_at FROM queries 
            WHERE (department = ? OR ? = 'All' OR assigned_staff_id = ?) AND first_response_at IS NOT NULL
        """, (dept, dept, user['id'])).fetchall()
    else:
        s = db.execute("""
            SELECT
                SUM(CASE WHEN status = 'New' THEN 1 ELSE 0 END) as new,
                SUM(CASE WHEN priority IN ('Critical','Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN priority = 'High' AND status != 'Resolved' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN status IN ('Assigned','In Progress') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?) THEN 1 ELSE 0 END) as resolved_today
            FROM queries
            WHERE (department = ? OR ? = 'All' OR ? = 'All Departments')
        """, (f"{today_str}%", f"{today_str}%", dept, dept, dept)).fetchone()
        stats = {'new': s['new'] or 0, 'urgent': s['urgent'] or 0, 'high': s['high'] or 0,
                 'in_progress': s['in_progress'] or 0, 'resolved_today': s['resolved_today'] or 0}
        resp_rows = db.execute("""
            SELECT created_at, first_response_at FROM queries 
            WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND first_response_at IS NOT NULL
        """, (dept, dept, dept)).fetchall()

    
    avg_resp_display = "10 minutes"
    if resp_rows:
        total_mins = 0
        valid_count = 0
        for r in resp_rows:
            try:
                c = datetime.strptime(r['created_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                f = datetime.strptime(r['first_response_at'].split('.')[0], '%Y-%m-%d %H:%M:%S')
                diff_mins = max(1, int((f - c).total_seconds() / 60))
                total_mins += diff_mins
                valid_count += 1
            except Exception:
                pass
        if valid_count > 0:
            avg_m = total_mins // valid_count
            if avg_m < 60:
                avg_resp_display = f"{avg_m} minutes"
            else:
                avg_resp_display = f"{round(avg_m/60, 1)} hours"
                
    # Filter Queue
    view_mode = request.args.get('view', '')
    priority_filter = request.args.get('priority', '')
    status_filter = request.args.get('status', '')
    search_query = request.args.get('search', '').strip()
    
    sql = """
        SELECT q.*, u.name as user_name, u.role as user_role, u.roll_no,
               staff.name as staff_name,
               (SELECT message FROM messages WHERE query_id = q.id ORDER BY created_at DESC LIMIT 1) as last_message,
               CASE 
                   WHEN q.priority IN ('Critical', 'Urgent') THEN 1
                   WHEN q.priority = 'High' THEN 2
                   WHEN q.priority = 'Medium' THEN 3
                   ELSE 4
               END as priority_order
        FROM queries q
        JOIN users u ON q.user_id = u.id
        LEFT JOIN users staff ON q.assigned_staff_id = staff.id
        WHERE 1=1
    """
    params = []
    
    if is_resolver:
        staff_dept = user['department'] if user.get('department') else 'Computer Science & Engineering (CSE)'
        if user['role'] == 'office_staff':
            staff_dept = 'Administrative'
            
        if view_mode == 'received':
            # Department's incoming received query queue
            sql += " AND (q.department = ? OR q.department = 'Academics')"
            params.append(staff_dept)
        elif view_mode == 'unresolved':
            sql += " AND q.assigned_staff_id = ? AND q.status != 'Resolved'"
            params.append(user['id'])
        elif view_mode == 'resolved':
            sql += " AND q.assigned_staff_id = ? AND q.status = 'Resolved'"
            params.append(user['id'])
        else:
            # view_mode in ['assigned', ''] (default for resolver): queries specifically assigned to them from HOD / Principal / AO
            sql += " AND q.assigned_staff_id = ?"
            params.append(user['id'])
            if dept_param and dept_param not in ['All', 'All Departments', '']:
                sql += " AND q.department = ?"
                params.append(dept_param)
    elif user['role'] == 'hod':
        hod_c = user.get('course')
        if view_mode == 'assigned':
            # Specifically queries assigned directly to this HOD (e.g. by Principal or Leadership)
            sql += " AND q.assigned_staff_id = ?"
            params.append(user['id'])
        elif view_mode == 'delegated':
            # Queries delegated to staff resolvers
            if hod_c:
                sql += " AND (q.department = ? OR ? = 'All') AND (q.course = ? OR q.course IS NULL) AND q.assigned_staff_id IS NOT NULL AND q.assigned_staff_id != ?"
                params.extend([dept, dept, hod_c, user['id']])
            else:
                sql += " AND (q.department = ? OR ? = 'All') AND q.assigned_staff_id IS NOT NULL AND q.assigned_staff_id != ?"
                params.extend([dept, dept, user['id']])
        elif view_mode in ['received', 'all', '']:
            # All received queries for this department
            if hod_c:
                sql += " AND (q.department = ? OR ? = 'All') AND (q.course = ? OR q.course IS NULL)"
                params.extend([dept, dept, hod_c])
            else:
                sql += " AND (q.department = ? OR ? = 'All')"
                params.extend([dept, dept])
        else:
            # unresolved, resolved, unassigned, recent
            if hod_c:
                sql += " AND (((q.department = ? OR ? = 'All') AND (q.course = ? OR q.course IS NULL)) OR q.assigned_staff_id = ?)"
                params.extend([dept, dept, hod_c, user['id']])
            else:
                sql += " AND (q.department = ? OR ? = 'All' OR q.assigned_staff_id = ?)"
                params.extend([dept, dept, user['id']])
    elif user['role'] == 'ao':
        if view_mode == 'assigned':
            # Specifically queries assigned directly to AO (e.g. from Principal) or assigned administrative team queries
            sql += " AND (q.assigned_staff_id = ? OR (q.department = 'Administrative' AND q.assigned_staff_id IS NOT NULL))"
            params.append(user['id'])
        elif view_mode == 'delegated':
            sql += " AND q.department = 'Administrative' AND q.assigned_staff_id IS NOT NULL AND q.assigned_staff_id != ?"
            params.append(user['id'])
        elif view_mode in ['received', 'all', '']:
            # All received queries for Administrative Desk
            sql += " AND q.department = 'Administrative'"
        else:
            sql += " AND (q.department = 'Administrative' OR q.assigned_staff_id = ?)"
            params.append(user['id'])
    else:
        # Principal / Central Admin see department queries
        if dept and dept not in ['All', 'All Departments']:
            sql += " AND q.department = ?"
            params.append(dept)
        
    if view_mode in ['received', 'all', 'assigned', 'delegated'] or (is_resolver and view_mode in ['unresolved', 'resolved']):
        pass  # Filter already applied above
    elif view_mode == 'unassigned' and user['role'] in ['hod', 'admin', 'ao', 'principal']:
        sql += " AND q.assigned_staff_id IS NULL AND q.status != 'Resolved'"
    elif view_mode == 'unresolved':
        sql += " AND q.status != 'Resolved'"
    elif view_mode == 'resolved':
        sql += " AND q.status = 'Resolved'"
    elif view_mode == 'recent':
        pass  # will order by created_at DESC
    else:
        view_mode = 'received'
        
    if priority_filter:
        if priority_filter in ['Critical', 'Urgent']:
            sql += " AND q.priority IN ('Critical', 'Urgent')"
        else:
            sql += " AND q.priority = ?"
            params.append(priority_filter)
    if status_filter:
        sql += " AND q.status = ?"
        params.append(status_filter)
    if search_query:
        sql += " AND (q.title LIKE ? OR q.description LIKE ? OR u.name LIKE ? OR q.id LIKE ?)"
        term = f"%{search_query}%"
        params.extend([term, term, term, term])
        
    if view_mode == 'recent':
        sql += " ORDER BY q.created_at DESC"
    else:
        sql += " ORDER BY priority_order ASC, q.created_at DESC"
        
    queries = db.execute(sql, params).fetchall()
    
    # Counts for quick tabs — aggregated per role branch instead of 5-6 separate SELECTs
    delegated_count = 0
    if is_resolver:
        staff_dept = user['department'] if user.get('department') else 'Computer Science & Engineering (CSE)'
        if user['role'] == 'office_staff':
            staff_dept = 'Administrative'
        tc = db.execute("""
            SELECT
                COUNT(*) as total_dept_count,
                SUM(CASE WHEN assigned_staff_id = ? THEN 1 ELSE 0 END) as assigned_count,
                SUM(CASE WHEN (department = ? OR department = 'Academics') AND assigned_staff_id IS NULL AND status != 'Resolved' THEN 1 ELSE 0 END) as unassigned_count,
                SUM(CASE WHEN assigned_staff_id = ? AND status != 'Resolved' THEN 1 ELSE 0 END) as unresolved_count,
                SUM(CASE WHEN assigned_staff_id = ? AND status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM queries WHERE (department = ? OR department = 'Academics')
        """, (user['id'], staff_dept, user['id'], user['id'], staff_dept)).fetchone()
        total_dept_count = tc['total_dept_count'] or 0
        assigned_count = tc['assigned_count'] or 0
        unassigned_count = tc['unassigned_count'] or 0
        unresolved_count = tc['unresolved_count'] or 0
        resolved_count = tc['resolved_count'] or 0
    elif user['role'] == 'hod' and user.get('course'):
        hod_c = user['course']
        tc = db.execute("""
            SELECT
                SUM(CASE WHEN (department = ? OR ? = 'All') AND (course = ? OR course IS NULL) THEN 1 ELSE 0 END) as total_dept_count,
                SUM(CASE WHEN assigned_staff_id = ? THEN 1 ELSE 0 END) as assigned_count,
                SUM(CASE WHEN (department = ? OR ? = 'All') AND (course = ? OR course IS NULL) AND assigned_staff_id IS NOT NULL AND assigned_staff_id != ? THEN 1 ELSE 0 END) as delegated_count,
                SUM(CASE WHEN (department = ? OR ? = 'All') AND (course = ? OR course IS NULL) AND assigned_staff_id IS NULL AND status != 'Resolved' THEN 1 ELSE 0 END) as unassigned_count,
                SUM(CASE WHEN (((department = ? OR ? = 'All') AND (course = ? OR course IS NULL)) OR assigned_staff_id = ?) AND status != 'Resolved' THEN 1 ELSE 0 END) as unresolved_count,
                SUM(CASE WHEN (((department = ? OR ? = 'All') AND (course = ? OR course IS NULL)) OR assigned_staff_id = ?) AND status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM queries
        """, (dept, dept, hod_c,
              user['id'],
              dept, dept, hod_c, user['id'],
              dept, dept, hod_c,
              dept, dept, hod_c, user['id'],
              dept, dept, hod_c, user['id'])).fetchone()
        total_dept_count = tc['total_dept_count'] or 0
        assigned_count = tc['assigned_count'] or 0
        delegated_count = tc['delegated_count'] or 0
        unassigned_count = tc['unassigned_count'] or 0
        unresolved_count = tc['unresolved_count'] or 0
        resolved_count = tc['resolved_count'] or 0
    elif user['role'] == 'hod':
        tc = db.execute("""
            SELECT
                SUM(CASE WHEN department = ? OR ? = 'All' THEN 1 ELSE 0 END) as total_dept_count,
                SUM(CASE WHEN assigned_staff_id = ? THEN 1 ELSE 0 END) as assigned_count,
                SUM(CASE WHEN (department = ? OR ? = 'All') AND assigned_staff_id IS NOT NULL AND assigned_staff_id != ? THEN 1 ELSE 0 END) as delegated_count,
                SUM(CASE WHEN (department = ? OR ? = 'All') AND assigned_staff_id IS NULL AND status != 'Resolved' THEN 1 ELSE 0 END) as unassigned_count,
                SUM(CASE WHEN (department = ? OR ? = 'All' OR assigned_staff_id = ?) AND status != 'Resolved' THEN 1 ELSE 0 END) as unresolved_count,
                SUM(CASE WHEN (department = ? OR ? = 'All' OR assigned_staff_id = ?) AND status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM queries
        """, (dept, dept,
              user['id'],
              dept, dept, user['id'],
              dept, dept,
              dept, dept, user['id'],
              dept, dept, user['id'])).fetchone()
        total_dept_count = tc['total_dept_count'] or 0
        assigned_count = tc['assigned_count'] or 0
        delegated_count = tc['delegated_count'] or 0
        unassigned_count = tc['unassigned_count'] or 0
        unresolved_count = tc['unresolved_count'] or 0
        resolved_count = tc['resolved_count'] or 0
    elif user['role'] == 'ao':
        tc = db.execute("""
            SELECT
                COUNT(*) as total_dept_count,
                SUM(CASE WHEN assigned_staff_id = ? OR assigned_staff_id IS NOT NULL THEN 1 ELSE 0 END) as assigned_count,
                SUM(CASE WHEN assigned_staff_id IS NOT NULL AND assigned_staff_id != ? THEN 1 ELSE 0 END) as delegated_count,
                SUM(CASE WHEN assigned_staff_id IS NULL AND status != 'Resolved' THEN 1 ELSE 0 END) as unassigned_count,
                SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END) as unresolved_count,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM queries WHERE department = 'Administrative'
        """, (user['id'], user['id'])).fetchone()
        total_dept_count = tc['total_dept_count'] or 0
        assigned_count = tc['assigned_count'] or 0
        delegated_count = tc['delegated_count'] or 0
        unassigned_count = tc['unassigned_count'] or 0
        unresolved_count = tc['unresolved_count'] or 0
        resolved_count = tc['resolved_count'] or 0
    else:
        tc = db.execute("""
            SELECT
                COUNT(*) as total_dept_count,
                SUM(CASE WHEN assigned_staff_id IS NOT NULL THEN 1 ELSE 0 END) as assigned_count,
                SUM(CASE WHEN assigned_staff_id IS NULL AND status != 'Resolved' THEN 1 ELSE 0 END) as unassigned_count,
                SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END) as unresolved_count,
                SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_count
            FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments')
        """, (dept, dept, dept)).fetchone()
        total_dept_count = tc['total_dept_count'] or 0
        assigned_count = tc['assigned_count'] or 0
        delegated_count = assigned_count
        unassigned_count = tc['unassigned_count'] or 0
        unresolved_count = tc['unresolved_count'] or 0
        resolved_count = tc['resolved_count'] or 0

    
    # Department info
    dept_info = db.execute("SELECT * FROM departments WHERE name = ?", (dept,)).fetchone()
    
    return render_template(
        'department_dashboard.html',
        dept=dept,
        dept_info=dept_info,
        stats=stats,
        queries=queries,
        avg_resp_display=avg_resp_display,
        current_view=view_mode,
        current_priority=priority_filter,
        current_status=status_filter,
        search_query=search_query,
        unresolved_count=unresolved_count,
        unassigned_count=unassigned_count,
        assigned_count=assigned_count,
        delegated_count=delegated_count,
        resolved_count=resolved_count,
        total_dept_count=total_dept_count
    )

# -------------------------------------------------------------
# ADMIN DASHBOARD & MANAGEMENT ROUTES
# -------------------------------------------------------------

@app.route('/admin-dashboard')
@login_required
@role_required(['admin'])
def admin_dashboard():
    db = get_db()
    
    u_stats = db.execute("""
        SELECT
            COUNT(*) as total_users,
            SUM(CASE WHEN role = 'student' THEN 1 ELSE 0 END) as students,
            SUM(CASE WHEN role = 'faculty' THEN 1 ELSE 0 END) as faculty,
            SUM(CASE WHEN role = 'staff' THEN 1 ELSE 0 END) as staff,
            SUM(CASE WHEN role = 'admin' THEN 1 ELSE 0 END) as admins
        FROM users
    """).fetchone()

    q_stats = db.execute("""
        SELECT
            COUNT(*) as total_queries,
            SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END) as pending_queries,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved_queries,
            SUM(CASE WHEN priority IN ('Critical', 'Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent_queries
        FROM queries
    """).fetchone()

    stats = {
        'total_users': u_stats['total_users'] or 0,
        'students': u_stats['students'] or 0,
        'faculty': u_stats['faculty'] or 0,
        'staff': u_stats['staff'] or 0,
        'admins': u_stats['admins'] or 0,
        'total_queries': q_stats['total_queries'] or 0,
        'pending_queries': q_stats['pending_queries'] or 0,
        'resolved_queries': q_stats['resolved_queries'] or 0,
        'urgent_queries': q_stats['urgent_queries'] or 0
    }
    
    # 3 Category Metrics (Prominent Big Cards) - single aggregated query
    category_cards = []
    cat_meta = {
        'Academics': {'icon': '📚', 'color': '#4f46e5', 'tagline': 'Studies, Exams, Marks, Hall Tickets & Timetables'},
        'Administrative': {'icon': '🏢', 'color': '#0284c7', 'tagline': 'Fees, Receipts, Scholarships, Bonafide & ID Cards'},
        'Others': {'icon': '🔧', 'color': '#d97706', 'tagline': 'Hostel, Mess Food, Campus Wi-Fi, Labs & Transport'}
    }
    cat_rows = db.execute("""
        SELECT
            category,
            COUNT(*) as total,
            SUM(CASE WHEN status != 'Resolved' THEN 1 ELSE 0 END) as unresolved,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
            SUM(CASE WHEN priority IN ('Critical', 'Urgent') AND status != 'Resolved' THEN 1 ELSE 0 END) as urgent
        FROM queries
        GROUP BY category
    """).fetchall()
    cat_data_map = {r['category']: r for r in cat_rows}
    dept_rows = db.execute("SELECT name, head_name, contact_email FROM departments").fetchall()
    dept_meta_map = {d['name']: d for d in dept_rows}

    for cat in Config.CATEGORIES:
        c_stat = cat_data_map.get(cat)
        d_info = dept_meta_map.get(cat)
        category_cards.append({
            'name': cat,
            'icon': cat_meta[cat]['icon'],
            'color': cat_meta[cat]['color'],
            'tagline': cat_meta[cat]['tagline'],
            'total': c_stat['total'] if c_stat else 0,
            'unresolved': c_stat['unresolved'] if c_stat else 0,
            'resolved': c_stat['resolved'] if c_stat else 0,
            'urgent': c_stat['urgent'] if c_stat else 0,
            'head_name': d_info['head_name'] if d_info else 'Desk Lead',
            'contact_email': d_info['contact_email'] if d_info else 'support@college.com'
        })

    # HODs list with live presence and branch workload stats
    hod_list = db.execute("""
        SELECT u.id, u.name, u.email, u.department, u.last_active_at, u.designation,
               (SELECT COUNT(*) FROM queries WHERE department = u.department) as query_count,
               (SELECT COUNT(*) FROM queries WHERE department = u.department AND status != 'Resolved') as unresolved_count
        FROM users u
        WHERE u.role = 'hod' AND u.is_active = 1
        ORDER BY u.department ASC
    """).fetchall()

    return render_template(
        'admin_dashboard.html',
        stats=stats,
        category_cards=category_cards,
        hod_list=hod_list
    )

@app.route('/admin/communicate-hod')
@login_required
@role_required(['admin', 'principal'])
def admin_communicate_hod():
    db = get_db()
    
    # Query all active HODs with their academic hierarchy attributes
    hod_rows = db.execute("""
        SELECT u.id, u.name, u.email, u.level, u.course, u.department, u.designation, u.last_active_at,
               (SELECT COUNT(*) FROM admin_hod_messages WHERE sender_id = u.id AND is_read = 0) as unread_count,
               (SELECT COUNT(*) FROM queries WHERE department = u.department AND status != 'Resolved') as pending_queries
        FROM users u
        WHERE u.role = 'hod' AND u.is_active = 1
        ORDER BY u.level ASC, u.course ASC, u.name ASC
    """).fetchall()
    
    hods = []
    for h in hod_rows:
        hods.append({
            'id': h['id'],
            'name': h['name'],
            'email': h['email'],
            'level': h['level'] or 'UG',
            'course': h['course'] or 'B.Tech',
            'department': h['department'] or 'General Department',
            'designation': h['designation'] or 'Head of Department (HOD)',
            'last_active_at': h['last_active_at'],
            'is_online': (h['id'] in ONLINE_USERS),
            'unread_count': h['unread_count'],
            'pending_queries': h['pending_queries']
        })
        
    return render_template(
        'admin_communicate_hod.html',
        hods=hods,
        academic_levels=Config.ACADEMIC_LEVELS,
        courses_branches=Config.COURSES_BRANCHES
    )

@app.route('/api/admin-hod-messages/<int:hod_id>', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal', 'hod'])
def admin_hod_messages(hod_id):
    user = get_current_user()
    db = get_db()
    
    # Permission verification
    if user['role'] == 'hod' and user['id'] != hod_id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    admin_user = db.execute("SELECT id, name FROM users WHERE role = 'admin' LIMIT 1").fetchone()
    admin_id = admin_user['id'] if admin_user else 1
    
    if request.method == 'POST':
        message_text = request.form.get('message', '').strip() or (request.get_json() or {}).get('message', '').strip()
        if not message_text:
            return jsonify({'error': 'Message cannot be empty'}), 400
            
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sender_id = user['id']
        receiver_id = hod_id if user['role'] in ['admin', 'principal'] else admin_id
        
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO admin_hod_messages (sender_id, receiver_id, department, message, is_read, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (sender_id, receiver_id, user['department'] or 'College Administration', message_text, now_str))
        msg_id = cursor.lastrowid
        
        # Send Notification
        create_notification(
            receiver_id,
            None,
            f"Direct Message from {user['name']}",
            f"{message_text[:60]}...",
            'message'
        )
        db.commit()
        
        msg_payload = {
            'id': msg_id,
            'sender_id': sender_id,
            'sender_name': user['name'],
            'sender_role': user['role'],
            'message': message_text,
            'created_at': now_str,
            'timeago': 'Just now'
        }
        
        # Broadcast SocketIO
        socketio.emit('admin_hod_chat', msg_payload, room=f"admin_hod_{hod_id}")
        return jsonify({'status': 'success', 'message': msg_payload})
        
    # GET: Mark received messages as read
    try:
        db.execute("UPDATE admin_hod_messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?", (user['id'], hod_id if user['role'] in ['admin', 'principal'] else admin_id))
        db.commit()
    except Exception:
        pass

    # GET: Fetch message history
    curr_admin_id = user['id'] if user['role'] in ['admin', 'principal'] else admin_id
    rows = db.execute("""
        SELECT m.*, u.name as sender_name, u.role as sender_role
        FROM admin_hod_messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
    """, (curr_admin_id, hod_id, hod_id, curr_admin_id)).fetchall()
    
    msg_list = []
    for r in rows:
        msg_list.append({
            'id': r['id'],
            'sender_id': r['sender_id'],
            'sender_name': r['sender_name'],
            'sender_role': r['sender_role'],
            'message': r['message'],
            'created_at': r['created_at'],
            'timeago': format_time_ago(r['created_at']),
            'is_me': (r['sender_id'] == user['id'])
        })
        
    return jsonify({'messages': msg_list})

@app.route('/admin/users', methods=['GET', 'POST'])
@login_required
@role_required(['admin', 'principal'])
def admin_users():
    db = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', 'college123')
            role = request.form.get('role', 'student')
            department = request.form.get('department', '')
            roll_no = request.form.get('roll_no', '')
            designation = request.form.get('designation', '')
            
            if not name or not email:
                flash('Name and Email are required.', 'warning')
            else:
                existing = db.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
                if existing:
                    flash('User with this email already exists.', 'danger')
                else:
                    db.execute("""
                        INSERT INTO users (name, email, password_hash, role, department, roll_no, designation, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 1)
                    """, (name, email, generate_password_hash(password), role, department, roll_no, designation))
                    db.commit()
                    flash(f'User {name} created successfully.', 'success')
                    
        elif action == 'toggle_status':
            user_id = request.form.get('user_id')
            if user_id:
                uid = int(user_id)
                db.execute("UPDATE users SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (uid,))
                db.commit()
                updated_user = db.execute("SELECT is_active, role FROM users WHERE id = ?", (uid,)).fetchone()
                status_str = "Activated" if updated_user and updated_user['is_active'] == 1 else "Deactivated"
                flash(f'User account has been {status_str}.', 'success')
            
        return redirect(url_for('admin_users'))
        
    # Search and Filter Users
    role_filter = request.args.get('role', '')
    dept_filter = request.args.get('department', '')
    search = request.args.get('search', '').strip()
    
    sql = "SELECT * FROM users WHERE 1=1"
    params = []
    
    if role_filter:
        sql += " AND role = ?"
        params.append(role_filter)
    if dept_filter:
        sql += " AND department = ?"
        params.append(dept_filter)
    if search:
        sql += " AND (name LIKE ? OR email LIKE ? OR roll_no LIKE ?)"
        term = f"%{search}%"
        params.extend([term, term, term])
        
    sql += " ORDER BY created_at DESC"
    users = db.execute(sql, params).fetchall()
    
    return render_template(
        'users.html',
        users=users,
        current_role=role_filter,
        current_dept=dept_filter,
        search=search
    )

@app.route('/admin/reset-database', methods=['GET', 'POST'])
def reset_database_endpoint():
    """Clean reset of database to pristine demo state with degree-specific routing."""
    seed_database(force_reset=True)
    flash('Database cleanly reset with fresh degree-specific HODs, Staff, and demo records!', 'success')
    return redirect(url_for('login'))

@app.route('/admin/departments', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def admin_departments():
    db = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'create':
            name = request.form.get('name', '').strip()
            code = request.form.get('code', '').strip().upper()
            description = request.form.get('description', '').strip()
            head_name = request.form.get('head_name', '').strip()
            contact_email = request.form.get('contact_email', '').strip()
            avg_resp = int(request.form.get('avg_response_minutes', 15))
            
            if name and code:
                try:
                    db.execute("""
                        INSERT INTO departments (name, code, description, head_name, contact_email, avg_response_minutes)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (name, code, description, head_name, contact_email, avg_resp))
                    db.commit()
                    flash(f'Department "{name}" created.', 'success')
                except sqlite3.IntegrityError:
                    flash('Department name or code already exists.', 'danger')
                    
        elif action == 'update_sla':
            dept_id = request.form.get('dept_id')
            new_sla = int(request.form.get('avg_response_minutes', 15))
            db.execute("UPDATE departments SET avg_response_minutes = ? WHERE id = ?", (new_sla, dept_id))
            db.commit()
            flash('Department SLA response target updated.', 'success')
            
        return redirect(url_for('admin_departments'))
        
    departments = db.execute("""
        SELECT d.*,
               (SELECT COUNT(*) FROM queries WHERE department = d.name) as query_count,
               (SELECT COUNT(*) FROM users WHERE department = d.name AND role = 'staff') as staff_count
        FROM departments d
        ORDER BY d.name ASC
    """).fetchall()
    
    return render_template('departments.html', departments=departments)
@app.route('/admin/analytics')
@login_required
@role_required(['admin', 'hod', 'ao', 'principal'])
def admin_analytics():
    return render_template('analytics.html')

@app.route('/hod/analytics')
@login_required
@role_required(['hod', 'admin', 'ao', 'principal'])
def hod_analytics():
    return render_template('analytics.html')

@app.route('/api/analytics-data')
@login_required
@role_required(['admin', 'hod', 'ao', 'principal'])
def analytics_data():
    user = get_current_user()
    db = get_db()
    role = user['role']
    is_hod = (role == 'hod')
    is_ao = (role == 'ao')
    is_principal = (role == 'principal')
    is_admin = (role == 'admin')
    hod_dept = user['department'] or ''
    
    # Helper to compute pillar metrics — single aggregation query instead of 7 separate queries
    def compute_pillar(cat_condition, topic_sql):
        agg = db.execute(f"""
            SELECT
                COUNT(q.id) as total,
                SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as solved,
                SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN q.assigned_staff_id IS NOT NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN q.assigned_staff_id IS NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as unassigned,
                SUM(CASE WHEN q.priority IN ('Critical', 'Urgent') AND q.status != 'Resolved' THEN 1 ELSE 0 END) as urgent,
                SUM(CASE WHEN q.status = 'New' THEN 1 ELSE 0 END) as new_q
            FROM queries q WHERE {cat_condition}
        """).fetchone()
        t_q = agg['total'] or 0
        s_q = agg['solved'] or 0
        p_q = agg['pending'] or 0
        a_q = agg['assigned'] or 0
        u_q = agg['unassigned'] or 0
        urg_q = agg['urgent'] or 0
        n_q = agg['new_q'] or 0
        
        st_rows = db.execute(f"SELECT q.status, COUNT(q.id) as c FROM queries q WHERE {cat_condition} GROUP BY q.status ORDER BY c DESC").fetchall()
        pr_rows = db.execute(f"SELECT q.priority, COUNT(q.id) as c FROM queries q WHERE {cat_condition} GROUP BY q.priority ORDER BY c DESC").fetchall()
        tp_rows = db.execute(f"SELECT ({topic_sql}) as topic, COUNT(q.id) as c FROM queries q WHERE {cat_condition} GROUP BY topic ORDER BY c DESC").fetchall()
        yr_rows = db.execute(f"""
            SELECT 
                CASE 
                    WHEN u.role = 'faculty' THEN 'Faculty Submissions'
                    WHEN q.year = 1 OR u.year = 1 THEN '1st Year Students'
                    WHEN q.year = 2 OR u.year = 2 THEN '2nd Year Students'
                    WHEN q.year = 3 OR u.year = 3 THEN '3rd Year Students'
                    WHEN q.year = 4 OR u.year = 4 THEN '4th Year Students'
                    ELSE 'General Submissions'
                END as y_lbl,
                COUNT(q.id) as c
            FROM queries q
            LEFT JOIN users u ON q.user_id = u.id
            WHERE {cat_condition}
            GROUP BY y_lbl
            ORDER BY c DESC
        """).fetchall()

        return {
            'summary': {
                'total': t_q,
                'solved': s_q,
                'pending': p_q,
                'assigned': a_q,
                'unassigned': u_q,
                'urgent': urg_q,
                'new': n_q,
                'solved_percent': round((s_q / t_q * 100), 1) if t_q > 0 else 0
            },
            'statuses': {'labels': [r['status'] for r in st_rows], 'data': [r['c'] for r in st_rows]},
            'priorities': {'labels': [r['priority'] for r in pr_rows], 'data': [r['c'] for r in pr_rows]},
            'topics': {'labels': [r['topic'] for r in tp_rows], 'data': [r['c'] for r in tp_rows]},
            'years': {'labels': [r['y_lbl'] for r in yr_rows], 'data': [r['c'] for r in yr_rows]}
        }

    # SQL Topic extractors
    principal_topic_sql = """
        CASE
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%wifi%' OR LOWER(q.title || ' ' || q.description) LIKE '%wi-fi%' OR LOWER(q.title || ' ' || q.description) LIKE '%internet%' OR LOWER(q.title || ' ' || q.description) LIKE '%network%' THEN 'Wi-Fi & Internet'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%hostel%' OR LOWER(q.title || ' ' || q.description) LIKE '%mess%' OR LOWER(q.title || ' ' || q.description) LIKE '%food%' OR LOWER(q.title || ' ' || q.description) LIKE '%canteen%' THEN 'Hostel & Food Mess'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%clean%' OR LOWER(q.title || ' ' || q.description) LIKE '%sanitat%' OR LOWER(q.title || ' ' || q.description) LIKE '%washroom%' OR LOWER(q.title || ' ' || q.description) LIKE '%water%' THEN 'Cleanliness & Sanitation'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%electric%' OR LOWER(q.title || ' ' || q.description) LIKE '%power%' OR LOWER(q.title || ' ' || q.description) LIKE '%plumb%' OR LOWER(q.title || ' ' || q.description) LIKE '%fan%' OR LOWER(q.title || ' ' || q.description) LIKE '%light%' THEN 'Electrical & Plumbing'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%bus%' OR LOWER(q.title || ' ' || q.description) LIKE '%transport%' OR LOWER(q.title || ' ' || q.description) LIKE '%parking%' THEN 'Transport & Buses'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%library%' OR LOWER(q.title || ' ' || q.description) LIKE '%book%' THEN 'Library Facilities'
            ELSE 'Campus Maintenance & General'
        END
    """

    ao_topic_sql = """
        CASE
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%fee%' OR LOWER(q.title || ' ' || q.description) LIKE '%receipt%' OR LOWER(q.title || ' ' || q.description) LIKE '%dues%' OR LOWER(q.title || ' ' || q.description) LIKE '%refund%' THEN 'Fee Payment & Receipts'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%scholarship%' OR LOWER(q.title || ' ' || q.description) LIKE '%jvd%' OR LOWER(q.title || ' ' || q.description) LIKE '%epass%' THEN 'Scholarship Processing'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%bonafide%' OR LOWER(q.title || ' ' || q.description) LIKE '%certificate%' OR LOWER(q.title || ' ' || q.description) LIKE '%tc%' OR LOWER(q.title || ' ' || q.description) LIKE '%document%' THEN 'Bonafide & Certificates'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%id card%' OR LOWER(q.title || ' ' || q.description) LIKE '%id%' OR LOWER(q.title || ' ' || q.description) LIKE '%badge%' THEN 'ID Card & Badges'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%admiss%' OR LOWER(q.title || ' ' || q.description) LIKE '%registra%' THEN 'Admission & Registration'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%leave%' OR LOWER(q.title || ' ' || q.description) LIKE '%permission%' OR LOWER(q.title || ' ' || q.description) LIKE '%approval%' THEN 'Approvals & Clearances'
            ELSE 'Office & General Admin'
        END
    """

    hod_topic_sql = """
        CASE
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%exam%' OR LOWER(q.title || ' ' || q.description) LIKE '%mark%' OR LOWER(q.title || ' ' || q.description) LIKE '%result%' OR LOWER(q.title || ' ' || q.description) LIKE '%reval%' OR LOWER(q.title || ' ' || q.description) LIKE '%mid%' THEN 'Exams & Internal Marks'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%attend%' THEN 'Attendance Discrepancies'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%lab%' OR LOWER(q.title || ' ' || q.description) LIKE '%practical%' OR LOWER(q.title || ' ' || q.description) LIKE '%system%' THEN 'Lab & Practical Sessions'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%faculty%' OR LOWER(q.title || ' ' || q.description) LIKE '%teach%' OR LOWER(q.title || ' ' || q.description) LIKE '%class%' OR LOWER(q.title || ' ' || q.description) LIKE '%lecture%' THEN 'Faculty & Classes'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%syllabus%' OR LOWER(q.title || ' ' || q.description) LIKE '%subject%' OR LOWER(q.title || ' ' || q.description) LIKE '%course%' THEN 'Syllabus & Course Issues'
            WHEN LOWER(q.title || ' ' || q.description) LIKE '%project%' OR LOWER(q.title || ' ' || q.description) LIKE '%assign%' THEN 'Assignments & Projects'
            ELSE 'Academic Guidance & Notes'
        END
    """

    # FAST-PATH FOR HOD: Compute ONLY the HOD's own branch data, skip all other desk calculations
    if is_hod:
        hod_course = user.get('course') or 'B.Tech'
        if hod_course:
            b_cond = f"(q.category = 'Academics' OR q.department NOT IN ('Administrative', 'Others')) AND (q.department = '{hod_dept}' OR q.department IS NULL) AND (q.course = '{hod_course}' OR q.course IS NULL)"
            where_clause = "WHERE (q.department = ? OR u.department = ?) AND (q.course = ? OR u.course = ? OR q.course IS NULL)"
            params = [hod_dept, hod_dept, hod_course, hod_course]
        else:
            b_cond = f"(q.category = 'Academics' OR q.department NOT IN ('Administrative', 'Others')) AND (q.department = '{hod_dept}' OR q.department IS NULL)"
            where_clause = "WHERE (q.department = ? OR u.department = ?)"
            params = [hod_dept, hod_dept]

        branch_analysis = compute_pillar(b_cond, hod_topic_sql)
        branch_analysis['branch_name'] = f"{hod_course} {hod_dept}".strip()
        branch_analysis['course'] = hod_course
        branch_analysis['department'] = hod_dept

        # Single-query staff workload for branch
        staff_sql = """
            SELECT u.id, u.name, u.email, u.designation,
                   COUNT(q.id) as assigned,
                   SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User', 'Assigned') THEN 1 ELSE 0 END) as pending
            FROM users u
            LEFT JOIN queries q ON q.assigned_staff_id = u.id
            WHERE u.role IN ('staff', 'faculty') AND (u.department = ? OR u.department IS NULL) AND u.is_active = 1
        """
        staff_params = [hod_dept]
        if hod_course:
            staff_sql += " AND (u.course = ? OR u.course IS NULL)"
            staff_params.append(hod_course)
        staff_sql += " GROUP BY u.id ORDER BY u.name ASC"
        s_rows = db.execute(staff_sql, staff_params).fetchall()
        branch_analysis['staff_workload'] = [{
            'id': s['id'],
            'name': s['name'],
            'email': s['email'],
            'designation': s['designation'] or 'Department Staff Resolver',
            'assigned': s['assigned'] or 0,
            'resolved': s['resolved'] or 0,
            'pending': s['pending'] or 0,
            'solved_percent': round(((s['resolved'] or 0) / s['assigned'] * 100), 1) if s['assigned'] else 0
        } for s in s_rows]

        # Single-query summary
        sum_row = db.execute(f"""
            SELECT
                COUNT(q.id) as total,
                SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as solved,
                SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN q.assigned_staff_id IS NOT NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN q.assigned_staff_id IS NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as unassigned,
                SUM(CASE WHEN q.status = 'New' THEN 1 ELSE 0 END) as new_q
            FROM queries q LEFT JOIN users u ON q.user_id = u.id {where_clause}
        """, params).fetchone()
        t_tot = sum_row['total'] or 0
        s_sol = sum_row['solved'] or 0
        summary = {
            'total': t_tot,
            'solved': s_sol,
            'pending': sum_row['pending'] or 0,
            'assigned': sum_row['assigned'] or 0,
            'unassigned': sum_row['unassigned'] or 0,
            'new': sum_row['new_q'] or 0,
            'solved_percent': round((s_sol / t_tot * 100), 1) if t_tot > 0 else 0
        }

        year_rows = db.execute(f"""
            SELECT 
                CASE 
                    WHEN u.role = 'faculty' THEN 'Faculty Submissions'
                    WHEN u.year = 1 THEN '1st Year Students'
                    WHEN u.year = 2 THEN '2nd Year Students'
                    WHEN u.year = 3 THEN '3rd Year Students'
                    WHEN u.year = 4 THEN '4th Year Students'
                    ELSE 'General Campus'
                END as year_label,
                COUNT(q.id) as count
            FROM queries q
            LEFT JOIN users u ON q.user_id = u.id
            {where_clause}
            GROUP BY year_label
            ORDER BY count DESC
        """, params).fetchall()

        cat_rows = db.execute(f"""
            SELECT q.category, COUNT(q.id) as count
            FROM queries q
            LEFT JOIN users u ON q.user_id = u.id
            {where_clause}
            GROUP BY q.category
            ORDER BY count DESC
        """, params).fetchall()

        status_rows = db.execute(f"""
            SELECT q.status, COUNT(q.id) as count
            FROM queries q
            LEFT JOIN users u ON q.user_id = u.id
            {where_clause}
            GROUP BY q.status
            ORDER BY count DESC
        """, params).fetchall()

        return jsonify({
            'role': role,
            'is_hod': True,
            'is_ao': False,
            'is_principal': False,
            'is_admin': False,
            'user_dept': hod_dept,
            'user_course': user.get('course'),
            'branch_analysis': branch_analysis,
            'summary': summary,
            'years': {'labels': [r['year_label'] for r in year_rows], 'data': [r['count'] for r in year_rows]},
            'categories': {'labels': [r['category'] for r in cat_rows], 'data': [r['count'] for r in cat_rows]},
            'statuses': {'labels': [r['status'] for r in status_rows], 'data': [r['count'] for r in status_rows]}
        })

    # 1. Principal Desk Analysis (Category = 'Others' or department = 'Others')
    principal_analysis = compute_pillar("(q.category = 'Others' OR q.department = 'Others')", principal_topic_sql)
    prin_dept_rows = db.execute("""
        SELECT COALESCE(u.department, q.department, 'General Campus') as dept_name, COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        WHERE (q.category = 'Others' OR q.department = 'Others')
        GROUP BY dept_name
        ORDER BY count DESC
    """).fetchall()
    principal_analysis['departments'] = {'labels': [r['dept_name'] for r in prin_dept_rows], 'data': [r['count'] for r in prin_dept_rows]}

    # 2. AO Desk Analysis (Category = 'Administrative' or department = 'Administrative')
    ao_analysis = compute_pillar("(q.category = 'Administrative' OR q.department = 'Administrative')", ao_topic_sql)
    
    # AO Administrative Office Staff List with resolution statistics — single aggregated query
    ao_staff_rows = db.execute("""
        SELECT u.id, u.name, u.email, u.designation,
               COUNT(q.id) as assigned,
               SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
               SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User', 'Assigned') THEN 1 ELSE 0 END) as pending
        FROM users u
        LEFT JOIN queries q ON q.assigned_staff_id = u.id
        WHERE u.role IN ('office_staff', 'staff') AND (u.department = 'Administrative' OR u.department IS NULL) AND u.is_active = 1
        GROUP BY u.id
        ORDER BY u.name ASC
    """).fetchall()
    if not ao_staff_rows:
        ao_staff_rows = db.execute("""
            SELECT u.id, u.name, u.email, u.designation,
                   COUNT(q.id) as assigned,
                   SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as resolved,
                   SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User', 'Assigned') THEN 1 ELSE 0 END) as pending
            FROM users u
            LEFT JOIN queries q ON q.assigned_staff_id = u.id
            WHERE u.role IN ('office_staff', 'staff') AND u.is_active = 1
            GROUP BY u.id
            ORDER BY u.name ASC
        """).fetchall()
        
    ao_analysis['staff_workload'] = [{
        'id': s['id'],
        'name': s['name'],
        'email': s['email'],
        'designation': s['designation'] or 'Office Staff / Administrative Staff',
        'assigned': s['assigned'] or 0,
        'resolved': s['resolved'] or 0,
        'pending': s['pending'] or 0,
        'solved_percent': round(((s['resolved'] or 0) / s['assigned'] * 100), 1) if s['assigned'] else 0
    } for s in ao_staff_rows]

    # 3. HODs Academic Analysis (Category = 'Academics' or academic branches)
    hod_analysis = compute_pillar("(q.category = 'Academics' OR q.department NOT IN ('Administrative', 'Others'))", hod_topic_sql)

    # HOD Branch breakdown
    hod_dept_rows = db.execute("""
        SELECT COALESCE(q.department, 'Computer Science & Engineering (CSE)') as dept_name, COUNT(q.id) as count
        FROM queries q
        WHERE (q.category = 'Academics' OR q.department NOT IN ('Administrative', 'Others'))
        GROUP BY dept_name
        ORDER BY count DESC
    """).fetchall()
    hod_analysis['departments'] = {'labels': [r['dept_name'] for r in hod_dept_rows], 'data': [r['count'] for r in hod_dept_rows]}

    # HOD Degree breakdown
    hod_deg_rows = db.execute("""
        SELECT COALESCE(q.course, 'B.Tech') as degree_name, COUNT(q.id) as count
        FROM queries q
        WHERE (q.category = 'Academics' OR q.department NOT IN ('Administrative', 'Others'))
        GROUP BY degree_name
        ORDER BY count DESC
    """).fetchall()
    hod_analysis['degrees'] = {'labels': [r['degree_name'] for r in hod_deg_rows], 'data': [r['count'] for r in hod_deg_rows]}

    # HOD Table Performance Summary — single aggregation per HOD
    hod_users = db.execute("""
        SELECT id, name, email, role, level, course, department, designation 
        FROM users 
        WHERE role = 'hod' AND is_active = 1
        ORDER BY level ASC, course ASC, name ASC
    """).fetchall()
    hod_table = []
    for h in hod_users:
        h_dept = h['department']
        h_course = h['course']
        if h_course:
            cond = "(q.department = ? OR ? = 'All') AND (q.course = ? OR q.course IS NULL)"
            h_params = [h_dept, h_dept, h_course]
        else:
            cond = "(q.department = ? OR ? = 'All')"
            h_params = [h_dept, h_dept]
            
        h_stat = db.execute(f"""
            SELECT
                COUNT(q.id) as total,
                SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as solved,
                SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User', 'Assigned') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN q.assigned_staff_id IS NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as unassigned
            FROM queries q WHERE {cond}
        """, h_params).fetchone()
        t_q = h_stat['total'] or 0
        s_q = h_stat['solved'] or 0
        p_q = h_stat['pending'] or 0
        u_q = h_stat['unassigned'] or 0
        
        hod_table.append({
            'id': h['id'],
            'name': h['name'],
            'email': h['email'],
            'level': h['level'] or 'UG',
            'course': h_course or 'B.Tech',
            'department': h_dept or 'Computer Science & Engineering (CSE)',
            'designation': h['designation'] or 'Head of Department (HOD)',
            'total': t_q,
            'solved': s_q,
            'pending': p_q,
            'unassigned': u_q,
            'solved_percent': round((s_q / t_q * 100), 1) if t_q > 0 else 0
        })
    hod_analysis['hod_table'] = hod_table

    # Scoped where clause based on user role
    where_clause = ""
    params = []
    if is_ao:
        where_clause = "WHERE (q.department = 'Administrative' OR q.category = 'Administrative')"
        params = []
        
    # Queries by Department / Branch (Campus Overview)
    dept_rows = db.execute(f"""
        SELECT COALESCE(u.department, q.department, 'General Campus') as dept_name, COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY dept_name
        ORDER BY count DESC
    """, params).fetchall()

    # Queries by Student Year of Study (Campus Overview)
    year_rows = db.execute(f"""
        SELECT 
            CASE 
                WHEN u.role = 'faculty' THEN 'Faculty Submissions'
                WHEN u.year = 1 THEN '1st Year Students'
                WHEN u.year = 2 THEN '2nd Year Students'
                WHEN u.year = 3 THEN '3rd Year Students'
                WHEN u.year = 4 THEN '4th Year Students'
                ELSE 'General Campus'
            END as year_label,
            COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY year_label
        ORDER BY count DESC
    """, params).fetchall()

    # Department × Year Cross Matrix Breakdown
    matrix_rows = db.execute(f"""
        SELECT 
            COALESCE(u.department, q.department, 'General Campus') as dept_name,
            SUM(CASE WHEN u.year = 1 THEN 1 ELSE 0 END) as yr1,
            SUM(CASE WHEN u.year = 2 THEN 1 ELSE 0 END) as yr2,
            SUM(CASE WHEN u.year = 3 THEN 1 ELSE 0 END) as yr3,
            SUM(CASE WHEN u.year = 4 THEN 1 ELSE 0 END) as yr4,
            SUM(CASE WHEN u.role = 'faculty' THEN 1 ELSE 0 END) as faculty_count,
            COUNT(q.id) as total_count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY dept_name
        ORDER BY total_count DESC
    """, params).fetchall()

    matrix_list = []
    for r in matrix_rows:
        matrix_list.append({
            'dept_name': r['dept_name'],
            'yr1': r['yr1'],
            'yr2': r['yr2'],
            'yr3': r['yr3'],
            'yr4': r['yr4'],
            'faculty_count': r['faculty_count'],
            'total_count': r['total_count']
        })
    
    # Queries by Category (Campus Overview)
    cat_rows = db.execute(f"""
        SELECT q.category, COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.category
        ORDER BY count DESC
    """, params).fetchall()
    
    # Queries by Status (Campus Overview)
    status_rows = db.execute(f"""
        SELECT q.status, COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.status
        ORDER BY count DESC
    """, params).fetchall()
    
    # Queries by Priority (Campus Overview)
    priority_rows = db.execute(f"""
        SELECT q.priority, COUNT(q.id) as count
        FROM queries q
        LEFT JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.priority
        ORDER BY count DESC
    """, params).fetchall()
    
    # Branch-specific analysis (None for central admin/principal/AO)
    branch_analysis = None

    # Summary Metrics (Campus Overview) — single aggregated query
    sum_row = db.execute(f"""
        SELECT
            COUNT(q.id) as total,
            SUM(CASE WHEN q.status = 'Resolved' THEN 1 ELSE 0 END) as solved,
            SUM(CASE WHEN q.status IN ('In Progress', 'Waiting for User') THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN q.assigned_staff_id IS NOT NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as assigned,
            SUM(CASE WHEN q.assigned_staff_id IS NULL AND q.status != 'Resolved' THEN 1 ELSE 0 END) as unassigned,
            SUM(CASE WHEN q.status = 'New' THEN 1 ELSE 0 END) as new_q
        FROM queries q LEFT JOIN users u ON q.user_id = u.id {where_clause}
    """, params).fetchone()
    total_q = sum_row['total'] or 0
    solved_q = sum_row['solved'] or 0
    
    summary = {
        'total': total_q,
        'solved': solved_q,
        'pending': sum_row['pending'] or 0,
        'assigned': sum_row['assigned'] or 0,
        'unassigned': sum_row['unassigned'] or 0,
        'new': sum_row['new_q'] or 0,
        'solved_percent': round((solved_q / total_q * 100), 1) if total_q > 0 else 0
    }
    
    if is_hod:
        return jsonify({
            'role': role,
            'is_hod': True,
            'is_ao': False,
            'is_principal': False,
            'is_admin': False,
            'user_dept': hod_dept,
            'user_course': user.get('course'),
            'branch_analysis': branch_analysis,
            'summary': summary,
            'years': {'labels': [r['year_label'] for r in year_rows], 'data': [r['count'] for r in year_rows]},
            'categories': {'labels': [r['category'] for r in cat_rows], 'data': [r['count'] for r in cat_rows]},
            'statuses': {'labels': [r['status'] for r in status_rows], 'data': [r['count'] for r in status_rows]}
        })

    return jsonify({
        'role': role,
        'is_hod': is_hod,
        'is_ao': is_ao,
        'is_principal': is_principal,
        'is_admin': is_admin,
        'user_dept': hod_dept,
        'user_course': user.get('course'),
        'principal_analysis': principal_analysis,
        'ao_analysis': ao_analysis,
        'hod_analysis': hod_analysis,
        'branch_analysis': branch_analysis,
        'summary': summary,
        'departments': {'labels': [r['dept_name'] for r in dept_rows], 'data': [r['count'] for r in dept_rows]},
        'years': {'labels': [r['year_label'] for r in year_rows], 'data': [r['count'] for r in year_rows]},
        'matrix': matrix_list,
        'categories': {'labels': [r['category'] for r in cat_rows], 'data': [r['count'] for r in cat_rows]},
        'statuses': {'labels': [r['status'] for r in status_rows], 'data': [r['count'] for r in status_rows]},
        'priorities': {'labels': [r['priority'] for r in priority_rows], 'data': [r['count'] for r in priority_rows]}
    })

# -------------------------------------------------------------
# NOTIFICATIONS & PROFILE
@app.route('/notifications')
@login_required
def notifications():
    user = get_current_user()
    db = get_db()
    
    all_notifs = db.execute("""
        SELECT n.*, q.title as query_title
        FROM notifications n
        LEFT JOIN queries q ON n.query_id = q.id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
    """, (user['id'],)).fetchall()
    
    return render_template('notifications.html', notifications=all_notifs)

@app.route('/notifications/mark-read', methods=['POST'])
@login_required
def mark_notifications_read():
    user = get_current_user()
    db = get_db()
    notif_id = request.form.get('notif_id')
    
    if notif_id:
        db.execute("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user['id']))
    else:
        db.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user['id'],))
        
    db.commit()
    return jsonify({'status': 'success'})

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = get_current_user()
    db = get_db()
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'update_info':
            name = request.form.get('name', '').strip()
            phone = request.form.get('phone', '').strip()
            department = request.form.get('department', '').strip()
            
            if name:
                db.execute("UPDATE users SET name = ?, phone = ?, department = ? WHERE id = ?", (name, phone, department, user['id']))
                db.commit()
                session['name'] = name
                session['department'] = department
                flash('Profile updated successfully.', 'success')
                
        elif action == 'change_password':
            curr_pass = request.form.get('current_password', '')
            new_pass = request.form.get('new_password', '')
            confirm_pass = request.form.get('confirm_password', '')
            
            if not check_password_hash(user['password_hash'], curr_pass):
                flash('Incorrect current password.', 'danger')
            elif new_pass != confirm_pass:
                flash('New passwords do not match.', 'warning')
            elif len(new_pass) < 6:
                flash('New password must be at least 6 characters.', 'warning')
            else:
                db.execute("UPDATE users SET password_hash = ? WHERE id = ?", (generate_password_hash(new_pass), user['id']))
                db.commit()
                flash('Password changed successfully.', 'success')
                
        return redirect(url_for('profile'))
        
    return render_template('profile.html', user=user)

# -------------------------------------------------------------
# FLASK-SOCKETIO REAL-TIME HANDLERS & PRESENCE TRACKING
# -------------------------------------------------------------

ONLINE_USERS = {} # user_id -> set of socket session IDs

@socketio.on('user_presence_connect')
def handle_presence_connect(data):
    """Tracks active online users and updates last active timestamp."""
    user_id = data.get('user_id')
    if user_id:
        if user_id not in ONLINE_USERS:
            ONLINE_USERS[user_id] = set()
        ONLINE_USERS[user_id].add(request.sid)
        
        # Update last_active_at in DB using local timestamp
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        try:
            db = get_db()
            db.execute("UPDATE users SET last_active_at = ? WHERE id = ?", (now_str, user_id))
            db.commit()
        except Exception:
            pass
        
        emit('presence_update', {'user_id': user_id, 'is_online': True, 'last_active': 'Just now'}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Handles user disconnection and broadcasts offline status."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for uid, sids in list(ONLINE_USERS.items()):
        if request.sid in sids:
            sids.remove(request.sid)
            if not sids:
                del ONLINE_USERS[uid]
                try:
                    db = get_db()
                    db.execute("UPDATE users SET last_active_at = ? WHERE id = ?", (now_str, uid))
                    db.commit()
                except Exception:
                    pass
                emit('presence_update', {'user_id': uid, 'is_online': False, 'last_active': 'Just now'}, broadcast=True)
            break

@socketio.on('join_query')
def handle_join_query(data):
    query_id = data.get('query_id')
    if query_id:
        room = f"query_{query_id}"
        join_room(room)

@socketio.on('leave_query')
def handle_leave_query(data):
    query_id = data.get('query_id')
    if query_id:
        room = f"query_{query_id}"
        leave_room(room)

@socketio.on('join_department')
def handle_join_department(data):
    dept = data.get('department')
    if dept:
        room = f"dept_{dept}"
        join_room(room)

@socketio.on('join_admin_hod')
def handle_join_admin_hod(data):
    hod_id = data.get('hod_id')
    if hod_id:
        room = f"admin_hod_{hod_id}"
        join_room(room)

@socketio.on('leave_admin_hod')
def handle_leave_admin_hod(data):
    hod_id = data.get('hod_id')
    if hod_id:
        room = f"admin_hod_{hod_id}"
        leave_room(room)

@socketio.on('typing_indicator')
def handle_typing(data):
    query_id = data.get('query_id')
    user_name = data.get('user_name')
    is_typing = data.get('is_typing', False)
    if query_id:
        emit('user_typing', {'user_name': user_name, 'is_typing': is_typing}, room=f"query_{query_id}", include_self=False)

# -------------------------------------------------------------
# APPLICATION STARTUP
# -------------------------------------------------------------

def initialize_application():
    """Initializes the database and ensures 3-category structure and demo accounts."""
    seed_database(force_reset=False)

if __name__ == '__main__':
    initialize_application()
    print("=" * 65)
    print("🚀 DEPARTMENT QUERY MANAGEMENT PORTAL")
    print("📍 URL: http://127.0.0.1:5000")
    print("✨ Demo Accounts:")
    print("   • 👨‍🎓 B.Tech Student:     student@college.com / student123")
    print("   • 👨‍🎓 M.Tech Student:     mtech-student@college.com / student123")
    print("   • 🎓 B.Tech CSE HOD:     cse-hod@college.com / hod123")
    print("   • 👩‍🏫 B.Tech CSE Staff:   cse-staff@college.com / staff123")
    print("   • 🎓 M.Tech CSE HOD:     mtech-cse-hod@college.com / hod123")
    print("   • 👩‍🏫 M.Tech CSE Staff:   mtech-cse-staff@college.com / staff123")
    print("   • 🏢 AO (Admin Officer): ao@college.com / ao123")
    print("   • 💼 Office Staff:       office-staff@college.com / staff123")
    print("   • 🏛️ Principal:          principal@college.com / principal123")
    print("   • ⚡ Central Admin:       admin@college.com / admin123")
    print("=" * 65)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
