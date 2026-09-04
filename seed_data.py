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
        cursor.execute("PRAGMA foreign_keys = OFF")
        tables = ['feedback', 'attachments', 'audit_logs', 'notifications', 'messages', 'queries', 'users', 'departments']
        for t in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {t}")
        conn.commit()
        init_db(conn)
        cursor.execute("PRAGMA foreign_keys = ON")
    
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
        now_str = now.strftime('%Y-%m-%d %H:%M:%S')
        print("Seeding pristine demo users and HOD strictly for 1 primary department (CSE)...")
        users_data = [
            # 1. Main Demo Student (CSE - 3rd Year)
            ('Student (CSE 3rd Yr)', 'student@college.com', generate_password_hash('student123'), 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, '', '23B91A0501', 'Student', 1, now_str),
            
            # 2. Main Demo Faculty (CSE)
            ('Faculty Member (CSE)', 'faculty@college.com', generate_password_hash('faculty123'), 'faculty', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Assistant Professor', 1, now_str),
            
            # 3. Main Demo HOD (CSE HOD Only)
            ('Dr. Grace Hopper (CSE HOD)', 'cse-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Head of Department (CSE)', 1, now_str),
            
            # 4. CSE Department Staff
            ('Prof. Linus Torvalds', 'cse-staff@college.com', generate_password_hash('staff123'), 'staff', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'CSE Department Coordinator', 1, now_str),

            # 5. Academics Wing Resolver Staff
            ('Dr. Alan Turing', 'academics-staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Academics', None, None, '', '', 'Academics Coordinator', 1, now_str),
            
            # 6. Administrative Wing Resolver Staff
            ('Mrs. Eleanor Wright', 'admin-staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Administrative', None, None, '', '', 'Administrative Officer', 1, now_str),
            
            # 7. Others Wing Resolver Staff
            ('David Kumar', 'staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Others', None, None, '', '', 'Campus Support Lead', 1, now_str),
            
            # 8. Central Admin
            ('Central Administrator', 'admin@college.com', generate_password_hash('admin123'), 'admin', None, None, None, None, '', '', 'Central Administrator', 1, now_str)
        ]
        
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, role, level, department, course, year, phone, roll_no, designation, is_active, last_active_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()
        
        # Read exact newly assigned user IDs dynamically
        cursor.execute("SELECT id, email FROM users")
        user_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        s_cse3 = user_id_map.get('student@college.com')
        fac_uid = user_id_map.get('faculty@college.com')
        cse_staff_uid = user_id_map.get('cse-staff@college.com')
        acad_staff_uid = user_id_map.get('academics-staff@college.com')
        admin_staff_uid = user_id_map.get('admin-staff@college.com')
        others_staff_uid = user_id_map.get('staff@college.com')
        
        print("Seeding demo queries strictly for CSE and primary service wings...")
        sample_queries = [
            # CSE Queries
            {
                'user_id': s_cse3,
                'title': 'Operating Systems Lab System 14 Crash during practical',
                'description': 'System 14 in CSE Lab 2 has an OS kernel panic during Linux threading experiments. Need replacement.',
                'category': 'Academics',
                'department': 'Computer Science & Engineering (CSE)',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': cse_staff_uid,
                'created_at': now - timedelta(hours=5),
                'first_response_at': now - timedelta(hours=4, minutes=45),
                'updated_at': now - timedelta(hours=2)
            },
            {
                'user_id': s_cse3,
                'title': 'Data Structures Internal Marks Discrepancy',
                'description': 'Midterm 2 marks for DSA are uploaded as 14/30 instead of 28/30. Answer script verified with lecturer.',
                'category': 'Academics',
                'department': 'Computer Science & Engineering (CSE)',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None, # Unassigned for CSE HOD to assign!
                'created_at': now - timedelta(hours=3),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=3)
            },
            # Faculty Academic Query
            {
                'user_id': fac_uid,
                'title': 'Smart Board projector HDMI input not responding in CSE Seminar Hall 1',
                'description': 'Digital interactive podium display is showing No Signal. Faculty guest lecture at 3 PM today.',
                'category': 'Academics',
                'department': 'Computer Science & Engineering (CSE)',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': cse_staff_uid,
                'created_at': now - timedelta(hours=1, minutes=30),
                'first_response_at': now - timedelta(minutes=45),
                'updated_at': now - timedelta(minutes=45)
            },
            # Administrative Wing Query
            {
                'user_id': s_cse3,
                'title': 'Semester tuition fee payment of 45,000 not updated in receipts',
                'description': 'Completed fee payment via NetBanking with Ref #TXN983241, but account still shows dues.',
                'category': 'Administrative',
                'department': 'Administrative',
                'priority': 'Medium',
                'status': 'In Progress',
                'assigned_staff_id': admin_staff_uid,
                'created_at': now - timedelta(hours=6),
                'first_response_at': now - timedelta(hours=5),
                'updated_at': now - timedelta(hours=2)
            },
            # Others Desk Query (Hostel / Wi-Fi)
            {
                'user_id': s_cse3,
                'title': 'Campus Wi-Fi connectivity dropped in South Block Hostel',
                'description': 'Wi-Fi router on 2nd floor South Block has no internet gateway since yesterday evening.',
                'category': 'Others',
                'department': 'Others',
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': others_staff_uid,
                'created_at': now - timedelta(hours=2),
                'first_response_at': now - timedelta(hours=1, minutes=40),
                'updated_at': now - timedelta(minutes=40)
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
