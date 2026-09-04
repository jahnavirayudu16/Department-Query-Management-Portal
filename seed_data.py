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
        print("Seeding pristine demo users and HODs across multiple departments...")
        users_data = [
            # 1. Main Student (CSE - 3rd Year)
            ('Student (CSE 3rd Yr)', 'student@college.com', generate_password_hash('student123'), 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 3, '', '', 'Student', 1),
            
            # 2. Additional Students for Year & Dept Analytics (B.Tech, Degree, MBA, MCA, Diploma)
            ('Student (CSE 1st Yr)', 'student-cse1@college.com', generate_password_hash('student123'), 'student', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', 1, '', '', 'Student', 1),
            ('Student (AI & ML 2nd Yr)', 'student-aiml@college.com', generate_password_hash('student123'), 'student', 'UG', 'Artificial Intelligence & Machine Learning (AIML)', 'B.Tech', 2, '', '', 'Student', 1),
            ('Student (AI & DS 3rd Yr)', 'student-ds@college.com', generate_password_hash('student123'), 'student', 'UG', 'Artificial Intelligence & Data Science (AIDS)', 'B.Tech', 3, '', '', 'Student', 1),
            ('Student (ECE 2nd Yr)', 'student-ece@college.com', generate_password_hash('student123'), 'student', 'UG', 'Electronics & Communication Engineering (ECE)', 'B.Tech', 2, '', '', 'Student', 1),
            ('Student (ME 4th Yr)', 'student-me@college.com', generate_password_hash('student123'), 'student', 'UG', 'Mechanical Engineering (Mech)', 'B.Tech', 4, '', '', 'Student', 1),
            ('Student (Civil 1st Yr)', 'student-civil@college.com', generate_password_hash('student123'), 'student', 'UG', 'Civil Engineering (Civil)', 'B.Tech', 1, '', '', 'Student', 1),
            ('Student (BCA 1st Yr)', 'student-bca@college.com', generate_password_hash('student123'), 'student', 'UG', 'Bachelor of Computer Applications (BCA)', 'Degree', 1, '', '', 'Student', 1),
            ('Student (MBA 2nd Yr)', 'student-mba@college.com', generate_password_hash('student123'), 'student', 'PG', 'MBA (Business Analytics)', 'MBA', 2, '', '', 'Student', 1),
            ('Student (MCA 1st Yr)', 'student-mca@college.com', generate_password_hash('student123'), 'student', 'PG', 'Master of Computer Applications (MCA - Regular)', 'MCA', 1, '', '', 'Student', 1),
            ('Student (Diploma Mech 2nd Yr)', 'student-diploma@college.com', generate_password_hash('student123'), 'student', 'Diploma', 'Diploma in Mechanical Engineering (DME)', 'Diploma', 2, '', '', 'Student', 1),

            # 3. Faculty
            ('Faculty Member', 'faculty@college.com', generate_password_hash('faculty123'), 'faculty', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Assistant Professor', 1),
            
            # 4. Department HODs
            ('Dr. Grace Hopper (CSE HOD)', 'cse-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'Head of Department (CSE)', 1),
            ('Prof. Ada Lovelace (ECE HOD)', 'ece-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Electronics & Communication Engineering (ECE)', 'B.Tech', None, '', '', 'Head of Department (ECE)', 1),
            ('Dr. Nikola Tesla (Mech HOD)', 'mech-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Mechanical Engineering (Mech)', 'B.Tech', None, '', '', 'Head of Department (Mechanical)', 1),
            ('Prof. Dennis Ritchie (BCA HOD)', 'bca-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Bachelor of Computer Applications (BCA)', 'Degree', None, '', '', 'Head of Department (BCA)', 1),
            ('Dr. Alexander Fleming (Pharmacy HOD)', 'pharm-hod@college.com', generate_password_hash('hod123'), 'hod', 'UG', 'Bachelor of Pharmacy (B.Pharm - Core)', 'B.Pharmacy', None, '', '', 'Head of Department (Pharmacy)', 1),
            ('Dr. Peter Drucker (MBA HOD)', 'mba-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'MBA (Business Analytics)', 'MBA', None, '', '', 'Head of Department (MBA)', 1),
            ('Dr. Barbara Liskov (MCA HOD)', 'mca-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'Master of Computer Applications (MCA - Regular)', 'MCA', None, '', '', 'Head of Department (MCA)', 1),
            ('Dr. Claude Shannon (M.Tech HOD)', 'mtech-hod@college.com', generate_password_hash('hod123'), 'hod', 'PG', 'M.Tech (Computer Science & Engineering)', 'M.Tech', None, '', '', 'Head of Department (M.Tech)', 1),
            ('Prof. James Gosling (Diploma HOD)', 'diploma-hod@college.com', generate_password_hash('hod123'), 'hod', 'Diploma', 'Diploma in Computer Engineering (DCME)', 'Diploma (Polytechnic)', None, '', '', 'Head of Department (Diploma)', 1),
            
            # 5. CSE Department Staff
            ('Prof. Linus Torvalds', 'cse-staff@college.com', generate_password_hash('staff123'), 'staff', 'UG', 'Computer Science & Engineering (CSE)', 'B.Tech', None, '', '', 'CSE Department Coordinator', 1),

            # 6. Academics Staff
            ('Dr. Alan Turing', 'academics-staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Academics', None, None, '', '', 'Academics Coordinator', 1),
            
            # 7. Administrative Staff
            ('Mrs. Eleanor Wright', 'admin-staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Administrative', None, None, '', '', 'Administrative Officer', 1),
            
            # 8. Others Staff
            ('David Kumar', 'staff@college.com', generate_password_hash('staff123'), 'staff', None, 'Others', None, None, '', '', 'Campus Support Lead', 1),
            
            # 9. Central Admin
            ('Central Administrator', 'admin@college.com', generate_password_hash('admin123'), 'admin', None, None, None, None, '', '', 'Central Administrator', 1)
        ]
        
        cursor.executemany("""
            INSERT INTO users (name, email, password_hash, role, level, department, course, year, phone, roll_no, designation, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, users_data)
        conn.commit()
        
        # Read exact newly assigned user IDs dynamically
        cursor.execute("SELECT id, email FROM users")
        user_id_map = {row[1]: row[0] for row in cursor.fetchall()}
        
        s_cse3 = user_id_map.get('student@college.com')
        s_cse1 = user_id_map.get('student-cse1@college.com')
        s_aiml = user_id_map.get('student-aiml@college.com')
        s_ds3 = user_id_map.get('student-ds@college.com')
        s_ece2 = user_id_map.get('student-ece@college.com')
        s_me4 = user_id_map.get('student-me@college.com')
        s_civ1 = user_id_map.get('student-civil@college.com')
        s_bca1 = user_id_map.get('student-bca@college.com')
        s_mba2 = user_id_map.get('student-mba@college.com')
        s_mca1 = user_id_map.get('student-mca@college.com')
        s_dip2 = user_id_map.get('student-diploma@college.com')
        fac_uid = user_id_map.get('faculty@college.com')

        cse_staff_uid = user_id_map.get('cse-staff@college.com')
        acad_staff_uid = user_id_map.get('academics-staff@college.com')
        admin_staff_uid = user_id_map.get('admin-staff@college.com')
        others_staff_uid = user_id_map.get('staff@college.com')
        
        print("Seeding diverse queries across all departments, branches, and student years...")
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
            {
                'user_id': s_cse1,
                'title': 'Cannot access Python Lab Portal from hostel',
                'description': '1st year CSE student unable to login to Python online lab portal server.',
                'category': 'Academics',
                'department': 'Computer Science & Engineering (CSE)',
                'priority': 'Medium',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=2),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=2)
            },
            
            # AI & ML (2nd Year)
            {
                'user_id': s_aiml,
                'title': 'GPU Server access for Deep Learning Lab',
                'description': '2nd year AI&ML batch requesting access keys for the Deep Learning CUDA workstation in Lab 4.',
                'category': 'Academics',
                'department': 'CSE (AI & Machine Learning)',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=4),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=4)
            },

            # Data Science (3rd Year)
            {
                'user_id': s_ds3,
                'title': 'Big Data Analytics dataset cluster permission denied',
                'description': 'Hadoop cluster nodes returning authorization error when executing map-reduce jobs for semester assignment.',
                'category': 'Academics',
                'department': 'CSE (Data Science)',
                'priority': 'Medium',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=7),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=7)
            },

            # ECE Queries (2nd Year)
            {
                'user_id': s_ece2,
                'title': 'Digital Logic Design lab kit malfunction',
                'description': 'Breadboards and IC timer kits in ECE Lab 1 are faulty and not providing stable 5V output.',
                'category': 'Academics',
                'department': 'Electronics & Communication Engineering (ECE)',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=6),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=6)
            },
            {
                'user_id': s_ece2,
                'title': 'Attendance shortage due to medical leave not recorded',
                'description': 'Medical leave submitted for 4 days fever in ECE department office is still showing absent in portal.',
                'category': 'Academics',
                'department': 'Electronics & Communication Engineering (ECE)',
                'priority': 'Medium',
                'status': 'In Progress',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(days=1),
                'first_response_at': now - timedelta(hours=20),
                'updated_at': now - timedelta(hours=10)
            },

            # Mechanical Engineering (4th Year)
            {
                'user_id': s_me4,
                'title': 'Final Year Major Project Guide allocation request',
                'description': '4th year ME batch #4 requesting Robotics / Automation faculty guide approval.',
                'category': 'Academics',
                'department': 'Mechanical Engineering (ME)',
                'priority': 'Medium',
                'status': 'In Progress',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(days=1, hours=4),
                'first_response_at': now - timedelta(days=1),
                'updated_at': now - timedelta(hours=8)
            },

            # Civil Engineering (1st Year)
            {
                'user_id': s_civ1,
                'title': 'Engineering Mechanics tutorial class schedule conflict',
                'description': '1st year Civil tutorial clashes with Physics laboratory on Thursday afternoon.',
                'category': 'Academics',
                'department': 'Civil Engineering (CE)',
                'priority': 'Low',
                'status': 'Resolved',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(days=2),
                'first_response_at': now - timedelta(days=1, hours=20),
                'resolved_at': now - timedelta(days=1, hours=10),
                'updated_at': now - timedelta(days=1, hours=10)
            },

            # BCA (1st Year)
            {
                'user_id': s_bca1,
                'title': 'Web Technologies HTML5/CSS Lab record verification',
                'description': 'BCA 1st year web design lab manual submissions and viva dates clarification needed.',
                'category': 'Academics',
                'department': 'Bachelor of Computer Applications (BCA)',
                'priority': 'Medium',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=8),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=8)
            },

            # MBA (2nd Year)
            {
                'user_id': s_mba2,
                'title': 'Business Analytics SPSS Software license expired',
                'description': 'SPSS statistics tool license in MBA computer laboratory expired yesterday. Midterm project pending.',
                'category': 'Academics',
                'department': 'MBA (Business Analytics)',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=3),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=3)
            },

            # MCA (1st Year)
            {
                'user_id': s_mca1,
                'title': 'Advanced Java Frameworks elective registration',
                'description': 'Option to select Spring Boot / Cloud Microservices elective is not appearing on the student portal.',
                'category': 'Academics',
                'department': 'Master of Computer Applications (MCA - Regular)',
                'priority': 'Medium',
                'status': 'In Progress',
                'assigned_staff_id': acad_staff_uid,
                'created_at': now - timedelta(days=1),
                'first_response_at': now - timedelta(hours=14),
                'updated_at': now - timedelta(hours=6)
            },

            # Diploma Mechanical (2nd Year)
            {
                'user_id': s_dip2,
                'title': 'Workshop lathe machine safety guard maintenance',
                'description': 'Safety guard on CNC Lathe machine #3 in Diploma mechanical workshop is loose.',
                'category': 'Academics',
                'department': 'Diploma in Mechanical Engineering (DME)',
                'priority': 'High',
                'status': 'New',
                'assigned_staff_id': None,
                'created_at': now - timedelta(hours=5),
                'first_response_at': None,
                'updated_at': now - timedelta(hours=5)
            },

            # Faculty Academic Query
            {
                'user_id': fac_uid,
                'title': 'Smart Board projector HDMI input not responding in Seminar Hall 1',
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

            # Administrative Wing Queries
            {
                'user_id': s_cse3,
                'title': 'Semester tuition fee payment of 45,000 not updated',
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
            {
                'user_id': s_me4,
                'title': 'Urgent Bonafide certificate for passport verification',
                'description': 'Require bonafide certificate for visa/passport appointment scheduled for next week.',
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

            # Others Desk Queries (Hostel / Wi-Fi)
            {
                'user_id': s_cse1,
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
            },
            {
                'user_id': s_ece2,
                'title': 'Drinking water cooler filter replacement in Block B',
                'description': 'Water dispenser filter indicator is red on 1st floor Block B.',
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
