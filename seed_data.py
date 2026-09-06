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
        print("Seeding pristine demo users and degree-specific HODs...")
        users_data = [
            # 1. B.Tech Demo Student (CSE - 3rd Year)
            ('Student (B.Tech CSE 3rd Yr)', 'student@college.com', generate_password_hash('student123'), 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, '', '23B91A0501', 'Student (B.Tech CSE)', 1, now_str),
            
            # 2. M.Tech Demo Student (CSE - 1st Year)
            ('Student (M.Tech CSE 1st Yr)', 'mtech-student@college.com', generate_password_hash('student123'), 'student', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', 1, '', '25B91D5801', 'Student (M.Tech CSE)', 1, now_str),

            # 3. B.Tech CSE HOD (UG)
            ('Dr. Grace Hopper (B.Tech CSE HOD)', 'cse-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Head of Department (B.Tech CSE)', 1, now_str),
            
            # 4. B.Tech CSE Staff
            ('Prof. Linus Torvalds', 'cse-staff@college.com', generate_password_hash('staff123'), 'staff', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'B.Tech CSE Assistant Professor / Staff', 1, now_str),

            # 5. M.Tech CSE HOD (PG)
            ('Dr. Barbara Liskov (M.Tech CSE HOD)', 'mtech-cse-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', None, '', '', 'Head of Department (M.Tech CSE)', 1, now_str),
            
            # 6. M.Tech CSE Staff
            ('Prof. Donald Knuth', 'mtech-cse-staff@college.com', generate_password_hash('staff123'), 'staff', 'PG', 'Computer Science & Engineering (CSE)', 'M.Tech', None, '', '', 'M.Tech CSE Assistant Professor / Staff', 1, now_str),

            # 7. MCA HOD
            ('Dr. Tim Berners-Lee (MCA HOD)', 'mca-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'Master of Computer Applications (MCA)', 'MCA', None, '', '', 'Head of Department (MCA)', 1, now_str),

            # 8. MBA HOD
            ('Dr. Peter Drucker (MBA HOD)', 'mba-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'Master of Business Administration (MBA)', 'MBA', None, '', '', 'Head of Department (MBA)', 1, now_str),

            # 9. Administrative Officer (AO)
            ('Mrs. Eleanor Wright (AO)', 'ao@college.com', generate_password_hash('ao123'), 'ao', None, 'Administrative', None, None, '', '', 'Administrative Officer (AO)', 1, now_str),
            
            # 10. Office Staff (Administrative)
            ('Mr. Ramesh Kumar (Office Staff)', 'office-staff@college.com', generate_password_hash('staff123'), 'office_staff', None, 'Administrative', None, None, '', '', 'Office Staff / Admin Assistant', 1, now_str),

            # 11. Principal
            ('Dr. Alan Turing (Principal)', 'principal@college.com', generate_password_hash('principal123'), 'principal', None, 'College Administration', None, None, '', '', 'Principal', 1, now_str),
            
            # 12. Central Administrator
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
        
        s_btech = user_id_map.get('student@college.com')
        s_mtech = user_id_map.get('mtech-student@college.com')
        cse_staff_uid = user_id_map.get('cse-staff@college.com')
        mtech_staff_uid = user_id_map.get('mtech-cse-staff@college.com')
        ao_uid = user_id_map.get('ao@college.com')
        office_staff_uid = user_id_map.get('office-staff@college.com')
        principal_uid = user_id_map.get('principal@college.com')
        
        print("Seeding demo queries with distinct B.Tech vs M.Tech degree routing and AO Office Staff assignment...")
        sample_queries = [
            # 1. B.Tech CSE Query - In Progress (Assigned to B.Tech CSE Staff)
            {
                'user_id': s_btech,
                'title': 'Operating Systems Lab System 14 Crash during practical',
                'description': 'System 14 in CSE Lab 2 has an OS kernel panic during Linux threading experiments. Need replacement.',
                'category': 'Academics',
                'level': 'UG',
                'course': 'B.Tech',
                'department': 'Computer Science & Engineering (CSE)',
                'year': 3,
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': cse_staff_uid,
                'created_at': now - timedelta(hours=5),
                'first_response_at': now - timedelta(hours=4, minutes=45),
                'updated_at': now - timedelta(hours=2)
            },
            # 2. B.Tech CSE Query - New / Unassigned (For B.Tech CSE HOD to assign)
            {
                'user_id': s_btech,
                'title': 'Data Structures Internal Marks Discrepancy',
                'description': 'Midterm 2 marks for DSA are uploaded as 14/30 instead of 28/30. Answer script verified with lecturer.',
                'category': 'Academics',
                'level': 'UG',
                'course': 'B.Tech',
                'department': 'Computer Science & Engineering (CSE)',
                'year': 3,
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None, # Unassigned for B.Tech CSE HOD to assign!
                'created_at': now - timedelta(hours=3),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=3)
            },
            # 3. M.Tech CSE Query - New / Unassigned (Strictly for M.Tech CSE HOD to assign!)
            {
                'user_id': s_mtech,
                'title': 'Advanced Algorithms Research Paper IEEE Journal Access',
                'description': 'IEEE Xplore repository digital library credentials are not activating for M.Tech CSE 1st Year research dissertation batch.',
                'category': 'Academics',
                'level': 'PG',
                'course': 'M.Tech',
                'department': 'Computer Science & Engineering (CSE)',
                'year': 1,
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None, # Unassigned for M.Tech CSE HOD to assign!
                'created_at': now - timedelta(hours=2),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=2)
            },
            # 4. Administrative Wing Query - New / Unassigned (For AO to assign to Office Staff!)
            {
                'user_id': s_btech,
                'title': 'Semester tuition fee payment of 45,000 not updated in receipts',
                'description': 'Completed fee payment via NetBanking with Ref #TXN983241, but account still shows dues.',
                'category': 'Administrative',
                'level': 'UG',
                'course': 'B.Tech',
                'department': 'Administrative',
                'year': 3,
                'priority': 'Medium',
                'status': 'New',
                'assigned_staff_id': None, # Unassigned for AO to assign to Office Staff!
                'created_at': now - timedelta(hours=6),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=6)
            },
            # 5. Administrative Wing Query - In Progress (Assigned to Office Staff)
            {
                'user_id': s_btech,
                'title': 'Urgent Bonafide Certificate required for Passport Verification',
                'description': 'Applied for Bonafide certificate online 3 days ago. Need physical seal and signature from administrative office.',
                'category': 'Administrative',
                'level': 'UG',
                'course': 'B.Tech',
                'department': 'Administrative',
                'year': 3,
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': office_staff_uid,
                'created_at': now - timedelta(hours=4),
                'first_response_at': now - timedelta(hours=3, minutes=30),
                'updated_at': now - timedelta(hours=1)
            },
            # 6. Others Desk Query (Assigned to Principal / Facilities Lead)
            {
                'user_id': s_btech,
                'title': 'Campus Wi-Fi connectivity dropped in South Block Hostel',
                'description': 'Wi-Fi router on 2nd floor South Block has no internet gateway since yesterday evening.',
                'category': 'Others',
                'level': 'UG',
                'course': 'B.Tech',
                'department': 'Others',
                'year': 3,
                'priority': 'High',
                'status': 'In Progress',
                'assigned_staff_id': principal_uid,
                'created_at': now - timedelta(hours=2),
                'first_response_at': now - timedelta(hours=1, minutes=40),
                'updated_at': now - timedelta(minutes=40)
            }
        ]
        
        for q in sample_queries:
            cursor.execute("""
                INSERT INTO queries (user_id, title, description, category, level, course, department, year, priority, status, assigned_staff_id, created_at, first_response_at, resolved_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                q['user_id'], q['title'], q['description'], q['category'], q['level'], q['course'], q['department'], q['year'],
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
