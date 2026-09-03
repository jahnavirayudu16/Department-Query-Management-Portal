import os
import sqlite3
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash
from config import Config
from models import init_db

def seed_database(force_reset=True):
    """Seeds the database strictly with the 3 main departments: Academics, Administrative, Others, plus demo accounts."""
    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)
    db_path = Config.DATABASE
    
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    init_db(conn)
    cursor = conn.cursor()
    
    if force_reset:
        cursor.execute("DELETE FROM feedback")
        cursor.execute("DELETE FROM attachments")
        cursor.execute("DELETE FROM audit_logs")
        cursor.execute("DELETE FROM notifications")
        cursor.execute("DELETE FROM messages")
        cursor.execute("DELETE FROM queries")
        cursor.execute("DELETE FROM users")
        cursor.execute("DELETE FROM departments")
        try:
            cursor.execute("DELETE FROM sqlite_sequence")
        except Exception:
            pass
        conn.commit()
    
    # Check if 3 departments already exist
    cursor.execute("SELECT COUNT(*) FROM departments")
    dept_count = cursor.fetchone()[0]
    
    if dept_count != 3:
        departments_data = [
            ('Academics', 'ACAD', 'Studies, attendance, internal/external marks, exam schedules, hall tickets, revaluations, assignments, lab sessions & projects', 'book-open', 'Dr. Alan Turing', 'academics-staff@college.com', 12),
            ('Administrative', 'ADMIN', 'Fee payments, receipts, fee refunds, scholarships, bonafide/transfer certificates, ID cards, admissions & permissions', 'building', 'Mrs. Eleanor Wright', 'admin-staff@college.com', 15),
            ('Others', 'OTHER', 'Hostel, mess food, campus Wi-Fi, systems, cleanliness, library books, bus routes, sports, security & general issues', 'help-circle', 'David Kumar', 'staff@college.com', 10)
        ]
        cursor.executemany("""
            INSERT INTO departments (name, code, description, icon, head_name, contact_email, avg_response_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, departments_data)
        conn.commit()

    # Seed Demo Users
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        now = datetime.now()
        print("Seeding pristine 3-category demo users...")
        users_data = [
            # 1. Student (Anonymous)
            ('Student', 'student@college.com', generate_password_hash('student123'), 'student', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, '', '', 'Student', 1),
            
            # 2. Faculty
            ('Faculty Member', 'faculty@college.com', generate_password_hash('faculty123'), 'faculty', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Faculty', 1),
            
            # 3. Academics Staff
            ('Dr. Alan Turing', 'academics-staff@college.com', generate_password_hash('staff123'), 'staff', 'Academics', None, None, '', '', 'Academics Coordinator', 1),
            
            # 4. Administrative Staff
            ('Mrs. Eleanor Wright', 'admin-staff@college.com', generate_password_hash('staff123'), 'staff', 'Administrative', None, None, '', '', 'Administrative Officer', 1),
            
            # 5. Others Staff
            ('David Kumar', 'staff@college.com', generate_password_hash('staff123'), 'staff', 'Others', None, None, '', '', 'Campus Support Lead', 1),
            
            # 6. Admin
            ('Central Administrator', 'admin@college.com', generate_password_hash('admin123'), 'admin', None, None, None, '', '', 'Central Administrator', 1)
        ]
        
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, role, department, course, year, phone, roll_no, designation, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()
        
        # Read exact newly assigned user IDs dynamically
        cursor.execute("SELECT id, email FROM users")
        user_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        student_uid = user_id_map.get('student@college.com')
        acad_staff_uid = user_id_map.get('academics-staff@college.com')
        admin_staff_uid = user_id_map.get('admin-staff@college.com')
        others_staff_uid = user_id_map.get('staff@college.com')
        
        print("Seeding sample queries across 3 categories: Academics, Administrative, Others...")
        sample_queries = [
            # Academics (Handled by Dr. Alan Turing)
            {
                'user_id': student_uid,
                'title': 'Internal marks incorrect for DSP subject',
                'description': 'In the recently published internal assessment portal, my marks for Digital Signal Processing are entered as 12/30, whereas my corrected answer sheet showed 27/30.',
                'category': 'Academics',
                'department': 'Academics',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(hours=5),
                'first_response_at': now - timedelta(hours=4, minutes=45),
                'updated_at': now - timedelta(hours=2)
            },
            {
                'user_id': student_uid,
                'title': 'Attendance percentage shortage correction in LMS',
                'description': 'My attendance for Operating Systems shows 64% due to medical leave not being approved yet. I have submitted the medical certificate to the department.',
                'category': 'Academics',
                'department': 'Academics',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(hours=3),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=3)
            },
            {
                'user_id': student_uid,
                'title': 'Cannot download hall ticket for supplementary exam',
                'description': 'When clicking download admit card for 3rd semester supplementary exam, the server gives an invalid token error. Exam starts in two days.',
                'category': 'Academics',
                'department': 'Academics',
                'priority': 'High',
                'status': 'Assigned',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(hours=1),
                'first_response_at': now - timedelta(minutes=45),
                'updated_at': now - timedelta(minutes=30)
            },
            
            # Administrative (Handled by Mrs. Eleanor Wright)
            {
                'user_id': student_uid,
                'title': 'My semester fee payment of 45,000 is not updated',
                'description': 'I completed the semester fee payment via NetBanking yesterday with Ref #TXN983241, but my student account still shows dues pending.',
                'category': 'Administrative',
                'department': 'Administrative',
                'priority': 'Medium',
                'status': 'In Progress',
                'assigned_staff_id': admin_staff_uid,
                'created_at': now - timedelta(hours=6),
                'first_response_at': now - timedelta(hours=5),
                'updated_at': now - timedelta(hours=2)
            },
            {
                'user_id': student_uid,
                'title': 'Need urgent bonafide certificate for passport application',
                'description': 'I require an urgent bonafide certificate stating that I am a regular student for passport appointment verification next week.',
                'category': 'Administrative',
                'department': 'Administrative',
                'priority': 'Low',
                'status': 'Resolved',
                'assigned_staff_id': admin_staff_uid,
                'created_at': now - timedelta(days=2),
                'first_response_at': now - timedelta(days=1, hours=22),
                'resolved_at': now - timedelta(days=1, hours=10),
                'updated_at': now - timedelta(days=1, hours=10)
            },
            {
                'user_id': student_uid,
                'title': 'Scholarship disbursement amount not credited',
                'description': 'State merit scholarship was approved in October, but the credit has not reflected in my student stipend account.',
                'category': 'Administrative',
                'department': 'Administrative',
                'priority': 'Medium',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=4),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=4)
            },
            
            # Others (Handled by David Kumar)
            {
                'user_id': student_uid,
                'title': 'Campus Wi-Fi is not working in computer lab 3',
                'description': 'The campus Wi-Fi access point in Computer Lab 3 is constantly dropping connection for all students.',
                'category': 'Others',
                'department': 'Others',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': others_staff_uid,
                'created_at': now - timedelta(hours=2),
                'first_response_at': now - timedelta(hours=1, minutes=40),
                'updated_at': now - timedelta(minutes=40)
            },
            {
                'user_id': student_uid,
                'title': 'Severe water leakage in hostel room 314',
                'description': 'Block B Room 314 has water dripping continuously from the ceiling pipe since morning. Please send maintenance urgently.',
                'category': 'Others',
                'department': 'Others',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': others_staff_uid,
                'created_at': now - timedelta(hours=3),
                'first_response_at': now - timedelta(hours=2),
                'updated_at': now - timedelta(hours=1)
            },
            {
                'user_id': student_uid,
                'title': 'Mess food quality issue during dinner',
                'description': 'The dinner served in the south block mess yesterday was undercooked and the drinking water cooler needs filter replacement.',
                'category': 'Others',
                'department': 'Others',
                'priority': 'Medium',
                'status': 'Resolved',
                'assigned_staff_id': others_staff_uid,
                'created_at': now - timedelta(days=1),
                'first_response_at': now - timedelta(hours=18),
                'resolved_at': now - timedelta(hours=12),
                'updated_at': now - timedelta(hours=12)
            }
        ]
        
        for q in sample_queries:
            cursor.execute("""
                INSERT INTO queries (user_id, title, description, category, department, priority, status, assigned_staff_id, created_at, first_response_at, resolved_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q['user_id'], q['title'], q['description'], q['category'], q['department'],
                q['priority'], q['status'], q['assigned_staff_id'],
                q['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                q['first_response_at'].strftime('%Y-%m-%d %H:%M:%S') if q['first_response_at'] else None,
                q['resolved_at'].strftime('%Y-%m-%d %H:%M:%S') if q.get('resolved_at') else None,
                q['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            ))
            query_id = cursor.lastrowid
            
            # Initial message
            cursor.execute("""
                INSERT INTO messages (query_id, sender_id, message, created_at)
                VALUES (?, ?, ?, ?)
            """, (query_id, q['user_id'], q['description'], q['created_at'].strftime('%Y-%m-%d %H:%M:%S')))
            
            # Staff response
            if q['first_response_at']:
                staff_id = q['assigned_staff_id'] or 5
                cursor.execute("""
                    INSERT INTO messages (query_id, sender_id, message, created_at)
                    VALUES (?, ?, ?, ?)
                """, (
                    query_id,
                    staff_id,
                    "Hello, we have received your query and our team is looking into this immediately.",
                    q['first_response_at'].strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                if q['status'] == 'Resolved' and q.get('resolved_at'):
                    cursor.execute("""
                        INSERT INTO messages (query_id, sender_id, message, created_at)
                        VALUES (?, ?, ?, ?)
                    """, (
                        query_id,
                        staff_id,
                        "The issue has been resolved. Please verify on your end. Feel free to rate your experience.",
                        q['resolved_at'].strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    
                    cursor.execute("""
                        INSERT INTO feedback (query_id, user_id, rating, comment, created_at)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        query_id,
                        q['user_id'],
                        5,
                        "Prompt resolution and clear response. Thank you!",
                        q['resolved_at'].strftime('%Y-%m-%d %H:%M:%S')
                    ))

        conn.commit()
    
    conn.close()
    print("Database seeding completed!")

if __name__ == '__main__':
    seed_database()
