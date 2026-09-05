import os
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
            if user['role'] not in allowed_roles and user['role'] != 'admin':
                flash('You do not have permission to access that resource.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def get_current_user():
    """Retrieve the currently authenticated user from the database."""
    if 'user_id' in session:
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
        if not user or not user['is_active']:
            session.clear()
            return None
        return user
    return None

@app.context_processor
def inject_global_context():
    """Inject global variables into all Jinja templates."""
    user = get_current_user()
    unread_notifications_count = 0
    unread_notifications = []
    
    if user:
        db = get_db()
        notifications = db.execute(
            'SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC LIMIT 5',
            (user['id'],)
        ).fetchall()
        unread_notifications = [dict(n) for n in notifications]
        
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
        db.commit()
    except Exception as e:
        print(f"Notification error bypassed: {e}")

def ensure_demo_accounts(db):
    """Ensures demo accounts strictly for 1 department (CSE) and primary resolvers exist."""
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    demo_accounts = [
        ('Student (CSE 3rd Yr)', 'student@college.com', 'student123', 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, 'Student'),
        ('Faculty Member (CSE)', 'faculty@college.com', 'faculty123', 'faculty', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, 'Assistant Professor'),
        ('Dr. Grace Hopper (CSE HOD)', 'cse-hod@college.com', 'hod123', 'hod', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, 'Head of Department (CSE)'),
        ('Prof. Linus Torvalds', 'cse-staff@college.com', 'staff123', 'staff', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, 'CSE Department Coordinator'),
        ('Dr. Alan Turing', 'academics-staff@college.com', 'staff123', 'staff', None, 'Academics', None, None, 'Academics Coordinator'),
        ('Mrs. Eleanor Wright', 'admin-staff@college.com', 'staff123', 'staff', None, 'Administrative', None, None, 'Administrative Officer'),
        ('David Kumar', 'staff@college.com', 'staff123', 'staff', None, 'Others', None, None, 'Campus Support Lead'),
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
            
    # Clean up any leftover demo accounts for other departments
    old_demo_emails = [
        'ece-hod@college.com', 'mech-hod@college.com', 'bca-hod@college.com',
        'mba-hod@college.com', 'mca-hod@college.com', 'mtech-hod@college.com',
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
            
            flash(f'Welcome back!', 'success')
            
            # Redirect to relevant dashboard
            if user['role'] == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user['role'] == 'staff':
                return redirect(url_for('department_dashboard'))
            elif user['role'] == 'faculty':
                return redirect(url_for('faculty_choice'))
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
        primary_role = request.form.get('role', 'student').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        name = request.form.get('name', '').strip()
        
        if primary_role == 'student':
            role = 'student'
            level = request.form.get('level', 'UG').strip()
            course = request.form.get('course', 'B.Tech').strip()
            department = request.form.get('department', '').strip()
            year_str = request.form.get('year', '').strip()
            year_val = int(year_str) if year_str and year_str.isdigit() else 1
            roll_no = request.form.get('roll_no', '').strip()
            designation = 'Student'
            if not name:
                name = 'Student'
        else:
            # Faculty / HOD / Admin
            faculty_role_type = request.form.get('faculty_role_type', 'faculty').strip()
            if faculty_role_type not in ['faculty', 'hod', 'admin']:
                faculty_role_type = 'faculty'
            role = faculty_role_type
            roll_no = ''
            year_val = None
            
            if role == 'admin':
                level = None
                course = None
                department = None
                designation = request.form.get('designation', '').strip() or 'Central Administrator'
                name = name or 'Administrator'
            elif role == 'hod':
                level = request.form.get('fac_level', 'UG').strip()
                course = request.form.get('fac_course', 'B.Tech').strip()
                department = request.form.get('fac_department', '').strip()
                designation = request.form.get('designation', '').strip() or f"Head of Department ({department or 'Academic'})"
                name = name or f"HOD ({department or 'Department'})"
            else:
                # Faculty Resolver
                fac_cat = request.form.get('faculty_category', 'Academics').strip()
                level = request.form.get('fac_level', 'UG').strip()
                course = request.form.get('fac_course', 'B.Tech').strip()
                department = request.form.get('fac_department', '').strip()
                if not department:
                    department = fac_cat
                designation = request.form.get('designation', '').strip() or f"Faculty Member ({department})"
                name = name or 'Faculty Member'
        
        phone = request.form.get('phone', '').strip()
        
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
                INSERT INTO users (name, email, password_hash, role, level, department, course, year, phone, roll_no, designation, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (name, email, password_hash, role, level, department, course, year_val, phone, roll_no, designation))
            db.commit()
            
            flash('Registration successful! You can now log in securely.', 'success')
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
    if user['role'] in ['staff', 'hod']:
        return redirect(url_for('department_dashboard'))
    elif user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
        
    db = get_db()
    
    # User query counts
    stats = {
        'total': db.execute('SELECT COUNT(*) FROM queries WHERE user_id = ?', (user['id'],)).fetchone()[0],
        'new': db.execute("SELECT COUNT(*) FROM queries WHERE user_id = ? AND status = 'New'", (user['id'],)).fetchone()[0],
        'in_progress': db.execute("SELECT COUNT(*) FROM queries WHERE user_id = ? AND status IN ('Assigned', 'In Progress')", (user['id'],)).fetchone()[0],
        'waiting': db.execute("SELECT COUNT(*) FROM queries WHERE user_id = ? AND status = 'Waiting for User'", (user['id'],)).fetchone()[0],
        'resolved': db.execute("SELECT COUNT(*) FROM queries WHERE user_id = ? AND status = 'Resolved'", (user['id'],)).fetchone()[0],
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
@login_required
@role_required(['student', 'faculty'])
def submit_query():
    user = get_current_user()
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        
        if not title or not description:
            flash('Please provide both a query title and a detailed description.', 'warning')
            return render_template('submit_query.html')
            
        # Run smart automatic routing
        classification = classify_query(description, title)
        category = classification['category']
        priority = classification['priority']
        needs_admin_review = 1 if classification['needs_admin_review'] else 0
        
        # Routing: Link query to the student's branch/department so their branch HOD gets it directly!
        if user['department']:
            department = user['department']
        else:
            department = classification['department']
        
        db = get_db()
        cursor = db.cursor()
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        try:
            cursor.execute("""
                INSERT INTO queries (user_id, title, description, category, department, priority, status, admin_reviewed, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 'New', ?, ?, ?)
            """, (user['id'], title, description, category, department, priority, needs_admin_review, now_str, now_str))
            query_id = cursor.lastrowid
            
            # Save initial message
            cursor.execute("""
                INSERT INTO messages (query_id, sender_id, message, created_at)
                VALUES (?, ?, ?, ?)
            """, (query_id, user['id'], description, now_str))
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
                    """, (query_id, message_id, saved_filename, orig_filename, file_size, ext, save_path, user['id']))
                    
                    # Update message with attachment info
                    cursor.execute("""
                        UPDATE messages SET attachment_filename = ?, attachment_path = ? WHERE id = ?
                    """, (orig_filename, saved_filename, message_id))
            
            db.commit()
            
            # Safe Notification Creation
            try:
                create_notification(
                    user['id'],
                    query_id,
                    'Query Submitted Successfully',
                    f'Your query "#{query_id}: {title}" has been automatically routed to the {department} Department.',
                    'success'
                )
                
                dept_receivers = db.execute("""
                    SELECT id, role FROM users 
                    WHERE (department = ? OR department = ? OR (role = 'hod' AND department = ?))
                      AND role IN ('hod', 'staff', 'faculty')
                """, (department, category, department)).fetchall()
                
                for receiver in dept_receivers:
                    notif_title = f"🔴 Urgent Query: {title}" if priority == 'Urgent' else f"New Query: {title}"
                    create_notification(
                        receiver['id'],
                        query_id,
                        notif_title,
                        f"New {priority} priority query from {user['name']} in {department}.",
                        'urgent' if priority == 'Urgent' else 'info'
                    )
            except Exception as notif_err:
                print(f"Notification error bypassed: {notif_err}")

            # Safe SocketIO Emit
            try:
                socketio.emit('new_query_alert', {
                    'query_id': query_id,
                    'title': title,
                    'department': department,
                    'priority': priority,
                    'user_name': user['name'],
                    'user_role': user['role'],
                    'created_at': now_str
                }, room=f"dept_{department}")
            except Exception as sock_err:
                print(f"Socket emit bypassed: {sock_err}")
                
            flash(f'Your query has been automatically routed to the {department} Department with {priority} priority.', 'success')
            return redirect(url_for('query_details', query_id=query_id))
            
        except Exception as e:
            db.rollback()
            print(f"Error submitting query: {e}")
            flash(f'An error occurred while submitting your query: {str(e)}', 'danger')
            return render_template('submit_query.html')

        
    return render_template('submit_query.html')

@app.route('/query/<int:query_id>')
@login_required
def query_details(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("""
        SELECT q.*, u.name as user_name, u.email as user_email, u.role as user_role, u.roll_no, u.phone,
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
    is_admin = (user['role'] == 'admin')
    is_hod = (user['role'] == 'hod')
    is_assigned = (query['assigned_staff_id'] == user['id'])
    is_staff = (user['role'] in ['staff', 'faculty'])
    
    # Submitter, Central Admin, HOD, Assigned Resolver, or Department Staff can access
    if not (is_submitter or is_admin or is_hod or is_assigned or is_staff):
        flash('Access restricted: You do not have permission to view this query.', 'warning')
        if user['role'] in ['staff', 'faculty', 'hod']:
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
        dept_staff = db.execute(
            "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty') AND (department = ? OR department IS NULL) AND is_active = 1 ORDER BY name ASC",
            (user['department'],)
        ).fetchall()
        if not dept_staff:
            dept_staff = db.execute(
                "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty') AND is_active = 1 ORDER BY name ASC"
            ).fetchall()
    else:
        dept_staff = db.execute(
            "SELECT id, name, email, role, department, designation FROM users WHERE role IN ('staff', 'faculty', 'admin') AND is_active = 1 ORDER BY department ASC, name ASC"
        ).fetchall()
    
    # Audit Logs
    audit_logs = db.execute("""
        SELECT a.*, u.name as actor_name
        FROM audit_logs a
        LEFT JOIN users u ON a.user_id = u.id
        WHERE a.query_id = ?
        ORDER BY a.created_at DESC
    """, (query_id,)).fetchall()
    
    # Calculate Live Presence & Online Status for all 3 key parties: Submitter, Assigned Staff, Branch HOD
    # 1. Submitter Presence
    sub_row = db.execute("SELECT id, name, role, department, course, level, last_active_at FROM users WHERE id = ?", (query['user_id'],)).fetchone()
    submitter_presence = {
        'id': sub_row['id'] if sub_row else query['user_id'],
        'name': sub_row['name'] if sub_row else 'Submitter',
        'role': sub_row['role'].capitalize() if sub_row else 'Student',
        'is_online': (sub_row['id'] in ONLINE_USERS) if sub_row else False,
        'last_active': sub_row['last_active_at'] if sub_row else None
    }

    # 2. Assigned Staff Presence
    staff_presence = None
    if query['assigned_staff_id']:
        staff_row = db.execute("SELECT id, name, role, department, designation, last_active_at FROM users WHERE id = ?", (query['assigned_staff_id'],)).fetchone()
        if staff_row:
            staff_presence = {
                'id': staff_row['id'],
                'name': staff_row['name'],
                'role': 'Assigned Resolver',
                'department': staff_row['department'] or query['department'],
                'designation': staff_row['designation'] or 'Department Staff',
                'is_online': (staff_row['id'] in ONLINE_USERS),
                'last_active': staff_row['last_active_at']
            }

    # 3. Branch HOD Presence & Details (Strictly matching registered HOD for this department)
    hod_row = None
    target_dept = query['department'] or (sub_row['department'] if sub_row else None)
    if target_dept:
        # 1. Exact match by department
        hod_row = db.execute("""
            SELECT id, name, email, role, department, designation, last_active_at 
            FROM users 
            WHERE role = 'hod' AND department = ?
            ORDER BY id DESC LIMIT 1
        """, (target_dept,)).fetchone()
        
        # 2. Match by course if submitter belongs to specific academic course
        if not hod_row and sub_row and ('course' in sub_row.keys() and sub_row['course']):
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND course = ?
                ORDER BY id DESC LIMIT 1
            """, (sub_row['course'],)).fetchone()
            
        # 3. Fuzzy match on branch name
        if not hod_row and target_dept not in ['Academics', 'Administrative', 'Others']:
            hod_row = db.execute("""
                SELECT id, name, email, role, department, designation, last_active_at 
                FROM users 
                WHERE role = 'hod' AND (department LIKE ? OR ? LIKE '%' || department || '%')
                ORDER BY id DESC LIMIT 1
            """, (f"%{target_dept}%", target_dept)).fetchone()

    hod_presence = None
    if hod_row:
        hod_presence = {
            'id': hod_row['id'],
            'name': hod_row['name'],
            'email': hod_row['email'],
            'role': 'Branch HOD',
            'department': hod_row['department'] or query['department'],
            'designation': hod_row['designation'] or 'Head of Department',
            'is_online': (hod_row['id'] in ONLINE_USERS),
            'last_active': hod_row['last_active_at']
        }

    return render_template(
        'query_details.html',
        query=query,
        messages=visible_messages,
        attachments=attachments,
        dept_staff=dept_staff,
        audit_logs=audit_logs,
        submitter_presence=submitter_presence,
        staff_presence=staff_presence,
        hod_presence=hod_presence
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
        
    # Permission check: Allowed for Submitter, Assigned Staff/Faculty Resolver, Branch HOD, Admin, or Department Staff
    is_submitter = (user['id'] == query['user_id'])
    is_assigned_staff = (query['assigned_staff_id'] == user['id'])
    is_branch_hod = (user['role'] == 'hod')
    is_staff = (user['role'] in ['staff', 'faculty'])
    is_admin = (user['role'] == 'admin')
    
    if not (is_submitter or is_assigned_staff or is_branch_hod or is_staff or is_admin):
        return jsonify({'error': 'Unauthorized to participate in this query chat.'}), 403
        
    message_text = request.form.get('message', '').strip()
    is_internal_note = 1 if request.form.get('is_internal_note') == 'true' and (user['role'] in ['staff', 'hod', 'admin'] or (user['role'] == 'faculty' and query['assigned_staff_id'] == user['id'])) else 0
    
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

    # Update first_response_at if staff/hod/admin responded for the first time
    if user['role'] in ['staff', 'hod', 'admin', 'faculty'] and not is_submitter and not is_internal_note:
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
            sender_role_label = 'HOD' if user['role'] == 'hod' else 'Staff'
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
def update_query_status(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('department_dashboard'))
        
    # Allowed for assigned staff member, department staff, HOD, or central admin
    can_update = (
        user['role'] in ['admin', 'hod', 'staff'] or 
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
@role_required(['staff', 'hod', 'admin'])
def reassign_query(query_id):
    user = get_current_user()
    db = get_db()
    
    query = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
    if not query:
        flash('Query not found.', 'danger')
        return redirect(url_for('dashboard'))
        
    new_dept = request.form.get('department')
    new_staff_id = request.form.get('assigned_staff_id')
    new_priority = request.form.get('priority')
    
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
        cursor.execute("""
            UPDATE queries SET assigned_staff_id = ?, status = CASE WHEN status = 'New' THEN 'Assigned' ELSE status END, updated_at = ? WHERE id = ?
        """, (staff_val, now_str, query_id))
        
        if staff_val:
            assigned_staff = db.execute("SELECT name FROM users WHERE id = ?", (staff_val,)).fetchone()
            name_str = assigned_staff['name'] if assigned_staff else f"Staff ID {staff_val}"
            log_details.append(f"Assigned to {name_str}")
            create_notification(staff_val, query_id, 'Query Assigned', f"You have been assigned Query #{query_id}: {query['title']}", 'info')

    if log_details:
        cursor.execute("""
            INSERT INTO audit_logs (query_id, user_id, action, details)
            VALUES (?, ?, 'Query Assignment & Routing', ?)
        """, (query_id, user['id'], "; ".join(log_details)))
        
    db.commit()
    flash('Query assignments updated successfully.', 'success')
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
@role_required(['staff', 'hod', 'admin', 'faculty'])
def department_dashboard():
    user = get_current_user()
    is_resolver = user['role'] in ['staff', 'faculty']
    
    dept_param = request.args.get('dept')
    if is_resolver:
        dept = dept_param if dept_param else (user['department'] if user['department'] else 'All Departments')
    else:
        dept = dept_param if dept_param else (user['department'] if user['department'] else 'Academics')
    
    db = get_db()
    today_str = datetime.now().strftime('%Y-%m-%d')
    
    # Compute stats
    if is_resolver:
        stats = {
            'new': db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND status IN ('New', 'Assigned')", (user['id'],)).fetchone()[0],
            'urgent': db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND priority = 'Urgent' AND status != 'Resolved'", (user['id'],)).fetchone()[0],
            'high': db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND priority = 'High' AND status != 'Resolved'", (user['id'],)).fetchone()[0],
            'in_progress': db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND status IN ('Assigned', 'In Progress')", (user['id'],)).fetchone()[0],
            'resolved_today': db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?)", (user['id'], f"{today_str}%", f"{today_str}%")).fetchone()[0]
        }
        resp_rows = db.execute("""
            SELECT created_at, first_response_at FROM queries 
            WHERE assigned_staff_id = ? AND first_response_at IS NOT NULL
        """, (user['id'],)).fetchall()
    else:
        stats = {
            'new': db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND status = 'New'", (dept, dept, dept)).fetchone()[0],
            'urgent': db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND priority = 'Urgent' AND status != 'Resolved'", (dept, dept, dept)).fetchone()[0],
            'high': db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND priority = 'High' AND status != 'Resolved'", (dept, dept, dept)).fetchone()[0],
            'in_progress': db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND status IN ('Assigned', 'In Progress')", (dept, dept, dept)).fetchone()[0],
            'resolved_today': db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND status = 'Resolved' AND (resolved_at LIKE ? OR updated_at LIKE ?)", (dept, dept, dept, f"{today_str}%", f"{today_str}%")).fetchone()[0]
        }
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
                   WHEN q.priority = 'Urgent' THEN 1
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
        # Staff and Faculty resolvers see all queries assigned to them
        sql += " AND q.assigned_staff_id = ?"
        params.append(user['id'])
        if dept_param and dept_param not in ['All', 'All Departments', '']:
            sql += " AND q.department = ?"
            params.append(dept_param)
    else:
        # HOD / Central Admin see department queries
        if dept and dept not in ['All', 'All Departments']:
            sql += " AND q.department = ?"
            params.append(dept)
        
    if view_mode == 'unresolved' or not view_mode:
        sql += " AND q.status != 'Resolved'"
    elif view_mode == 'unassigned' and user['role'] in ['hod', 'admin']:
        sql += " AND q.assigned_staff_id IS NULL AND q.status != 'Resolved'"
    elif view_mode == 'all':
        pass  # all queries
    elif view_mode == 'recent':
        pass  # will order by created_at DESC
        
    if priority_filter:
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
    
    # Counts for quick tabs
    if is_resolver:
        unresolved_count = db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ? AND status != 'Resolved'", (user['id'],)).fetchone()[0]
        unassigned_count = 0
        total_dept_count = db.execute("SELECT COUNT(*) FROM queries WHERE assigned_staff_id = ?", (user['id'],)).fetchone()[0]
    else:
        unresolved_count = db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND status != 'Resolved'", (dept, dept, dept)).fetchone()[0]
        unassigned_count = db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments') AND assigned_staff_id IS NULL AND status != 'Resolved'", (dept, dept, dept)).fetchone()[0]
        total_dept_count = db.execute("SELECT COUNT(*) FROM queries WHERE (department = ? OR ? = 'All' OR ? = 'All Departments')", (dept, dept, dept)).fetchone()[0]
    
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
    
    stats = {
        'total_users': db.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'students': db.execute("SELECT COUNT(*) FROM users WHERE role = 'student'").fetchone()[0],
        'faculty': db.execute("SELECT COUNT(*) FROM users WHERE role = 'faculty'").fetchone()[0],
        'staff': db.execute("SELECT COUNT(*) FROM users WHERE role = 'staff'").fetchone()[0],
        'admins': db.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'").fetchone()[0],
        'total_queries': db.execute("SELECT COUNT(*) FROM queries").fetchone()[0],
        'pending_queries': db.execute("SELECT COUNT(*) FROM queries WHERE status != 'Resolved'").fetchone()[0],
        'resolved_queries': db.execute("SELECT COUNT(*) FROM queries WHERE status = 'Resolved'").fetchone()[0],
        'urgent_queries': db.execute("SELECT COUNT(*) FROM queries WHERE priority = 'Urgent' AND status != 'Resolved'").fetchone()[0]
    }
    
    # 3 Category Metrics (Prominent Big Cards)
    category_cards = []
    cat_meta = {
        'Academics': {'icon': '📚', 'color': '#4f46e5', 'tagline': 'Studies, Exams, Marks, Hall Tickets & Timetables'},
        'Administrative': {'icon': '🏢', 'color': '#0284c7', 'tagline': 'Fees, Receipts, Scholarships, Bonafide & ID Cards'},
        'Others': {'icon': '🔧', 'color': '#d97706', 'tagline': 'Hostel, Mess Food, Campus Wi-Fi, Labs & Transport'}
    }
    for cat in Config.CATEGORIES:
        tot = db.execute("SELECT COUNT(*) FROM queries WHERE category = ?", (cat,)).fetchone()[0]
        unresolved = db.execute("SELECT COUNT(*) FROM queries WHERE category = ? AND status != 'Resolved'", (cat,)).fetchone()[0]
        resolved = db.execute("SELECT COUNT(*) FROM queries WHERE category = ? AND status = 'Resolved'", (cat,)).fetchone()[0]
        urgent = db.execute("SELECT COUNT(*) FROM queries WHERE category = ? AND priority = 'Urgent' AND status != 'Resolved'", (cat,)).fetchone()[0]
        dept_row = db.execute("SELECT head_name, contact_email FROM departments WHERE name = ?", (cat,)).fetchone()
        
        category_cards.append({
            'name': cat,
            'icon': cat_meta[cat]['icon'],
            'color': cat_meta[cat]['color'],
            'tagline': cat_meta[cat]['tagline'],
            'total': tot,
            'unresolved': unresolved,
            'resolved': resolved,
            'urgent': urgent,
            'head_name': dept_row['head_name'] if dept_row else 'Desk Lead',
            'contact_email': dept_row['contact_email'] if dept_row else 'support@college.com'
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
@role_required(['admin'])
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
@role_required(['admin', 'hod'])
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
        receiver_id = hod_id if user['role'] == 'admin' else admin_id
        
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO admin_hod_messages (sender_id, receiver_id, department, message, is_read, created_at)
            VALUES (?, ?, ?, ?, 0, ?)
        """, (sender_id, receiver_id, user['department'] or 'Central Administration', message_text, now_str))
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
        db.execute("UPDATE admin_hod_messages SET is_read = 1 WHERE receiver_id = ? AND sender_id = ?", (user['id'], hod_id if user['role'] == 'admin' else admin_id))
        db.commit()
    except Exception:
        pass

    # GET: Fetch message history
    rows = db.execute("""
        SELECT m.*, u.name as sender_name, u.role as sender_role
        FROM admin_hod_messages m
        JOIN users u ON m.sender_id = u.id
        WHERE (m.sender_id = ? AND m.receiver_id = ?)
           OR (m.sender_id = ? AND m.receiver_id = ?)
        ORDER BY m.created_at ASC
    """, (admin_id, hod_id, hod_id, admin_id)).fetchall()
    
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
@role_required(['admin'])
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
@role_required(['admin', 'hod'])
def admin_analytics():
    return render_template('analytics.html')

@app.route('/hod/analytics')
@login_required
@role_required(['hod', 'admin'])
def hod_analytics():
    return render_template('analytics.html')

@app.route('/api/analytics-data')
@login_required
@role_required(['admin', 'hod'])
def analytics_data():
    user = get_current_user()
    db = get_db()
    is_hod = (user['role'] == 'hod')
    hod_dept = user['department'] or ''
    
    # Base filter for HOD
    where_clause = ""
    params = []
    if is_hod and hod_dept:
        where_clause = "WHERE (q.department = ? OR u.department = ?)"
        params = [hod_dept, hod_dept]
        
    # 1. Queries by Department / Branch
    if not is_hod:
        dept_rows = db.execute("""
            SELECT COALESCE(u.department, q.department, 'General Campus') as dept_name, COUNT(q.id) as count
            FROM queries q
            JOIN users u ON q.user_id = u.id
            GROUP BY dept_name
            ORDER BY count DESC
        """).fetchall()
    else:
        dept_rows = db.execute(f"""
            SELECT COALESCE(u.department, q.department, ?) as dept_name, COUNT(q.id) as count
            FROM queries q
            JOIN users u ON q.user_id = u.id
            {where_clause}
            GROUP BY dept_name
        """, (hod_dept, *params)).fetchall()

    # 2. Queries by Student Year of Study
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
        JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY year_label
        ORDER BY count DESC
    """, params).fetchall()

    # 3. Department × Year Cross Matrix Breakdown
    matrix_rows = db.execute("""
        SELECT 
            COALESCE(u.department, q.department, 'General Campus') as dept_name,
            SUM(CASE WHEN u.year = 1 THEN 1 ELSE 0 END) as yr1,
            SUM(CASE WHEN u.year = 2 THEN 1 ELSE 0 END) as yr2,
            SUM(CASE WHEN u.year = 3 THEN 1 ELSE 0 END) as yr3,
            SUM(CASE WHEN u.year = 4 THEN 1 ELSE 0 END) as yr4,
            SUM(CASE WHEN u.role = 'faculty' THEN 1 ELSE 0 END) as faculty_count,
            COUNT(q.id) as total_count
        FROM queries q
        JOIN users u ON q.user_id = u.id
        GROUP BY dept_name
        ORDER BY total_count DESC
    """).fetchall()

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
    
    # 4. Queries by Category
    cat_rows = db.execute(f"""
        SELECT q.category, COUNT(q.id) as count
        FROM queries q
        JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.category
        ORDER BY count DESC
    """, params).fetchall()
    
    # 5. Queries by Status
    status_rows = db.execute(f"""
        SELECT q.status, COUNT(q.id) as count
        FROM queries q
        JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.status
        ORDER BY count DESC
    """, params).fetchall()
    
    # 6. Queries by Priority
    priority_rows = db.execute(f"""
        SELECT q.priority, COUNT(q.id) as count
        FROM queries q
        JOIN users u ON q.user_id = u.id
        {where_clause}
        GROUP BY q.priority
        ORDER BY count DESC
    """, params).fetchall()
    
    return jsonify({
        'is_hod': is_hod,
        'user_dept': hod_dept,
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
    print("✨ 3-Category Demo Accounts:")
    print("   • 👨‍🎓 Student:           student@college.com / student123")
    print("   • 👩‍🏫 Faculty:           faculty@college.com / faculty123")
    print("   • 📚 Academics Staff:   academics-staff@college.com / staff123")
    print("   • 🏢 Admin Staff:       admin-staff@college.com / staff123")
    print("   • 🔧 Others Staff:      staff@college.com / staff123")
    print("   • ⚡ Central Admin:     admin@college.com / admin123")
    print("=" * 65)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
