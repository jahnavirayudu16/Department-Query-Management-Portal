import os
import unittest
import sqlite3
from classifier import classify_query, detect_priority
from app import app
from seed_data import seed_database
from config import Config

class TestDQMSystem(unittest.TestCase):
    
    def setUp(self):
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.client = app.test_client()
        seed_database()

    def test_classifier_3_categories(self):
        """Verify the NLP classification engine against the 3 primary categories: Academics, Administrative, Others."""
        test_cases = [
            # 1. Academics
            ("My internal marks are incorrect for DSP subject.", "Academics"),
            ("Attendance percentage shortage correction in Operating Systems.", "Academics"),
            ("Cannot download hall ticket for supplementary exam.", "Academics"),
            ("When will the midterm exam timetable be published?", "Academics"),
            ("Assignment submission deadline extension requested.", "Academics"),
            ("Need guidance regarding mini project and lab viva.", "Academics"),
            ("Study material and textbook not available in library.", "Academics"),
            ("Revaluation result and backlog record clarification.", "Academics"),
            ("CRT training schedule and batch timings.", "Academics"),
            ("Need technical training for campus placements.", "Academics"),
            ("When will python training classes start?", "Academics"),
            ("Skill development and coding bootcamp query.", "Academics"),
            ("Internship training and industrial workshop details.", "Academics"),
            
            # 2. Administrative
            ("My semester fee payment of 45,000 is not updated.", "Administrative"),
            ("Need urgent bonafide certificate for passport application.", "Administrative"),
            ("Scholarship disbursement amount has not been credited.", "Administrative"),
            ("Need study certificate and transfer certificate verification.", "Administrative"),
            ("Name correction in college student records.", "Administrative"),
            ("Hostel fee refund and room accommodation approval.", "Administrative"),
            ("Bus pass and transport route request.", "Administrative"),
            ("Password reset for student portal login ID account.", "Administrative"),
            ("Theft incident in computer lab, my laptop was stolen.", "Administrative"),
            ("Someone stole my wallet from hostel room, please take action on this theft.", "Administrative"),
            ("Phone stolen near cafeteria, theft complaint.", "Administrative"),
            
            # 3. Others
            ("Campus Wi-Fi is not working in computer lab.", "Others"),
            ("Severe water leakage in hostel washroom.", "Others"),
            ("Canteen food quality and cleanliness issue.", "Others"),
            ("Annual sports competition and cultural fest registration.", "Others"),
            ("Anti-ragging complaint regarding harassment by seniors.", "Others"),
            ("Placement hackathon and campus recruitment drive details.", "Others"),
            ("Campus parking security and lost item inquiry.", "Others"),
            ("Random general query without specific words", "Others")
        ]
        
        for text, expected_cat in test_cases:
            result = classify_query(text, text)
            print(f"Testing Query: '{text}' -> Classified: {result['category']} ({result['priority']})")
            self.assertEqual(result['category'], expected_cat, f"Failed for '{text}': expected {expected_cat}, got {result['category']}")

    def test_priority_detection(self):
        """Test specific priority detection patterns."""
        self.assertEqual(detect_priority("Urgent emergency critical short circuit"), "Critical")
        self.assertEqual(detect_priority("The server is broken and not working"), "High")
        self.assertEqual(detect_priority("Status is pending approval"), "Medium")
        self.assertEqual(detect_priority("What are the working hours and timings?"), "Low")

    def test_principal_can_assign_to_hod_or_staff(self):
        """Verify Principal can assign a query to either an HOD or a Staff Resolver."""
        # 1. Login as Principal
        self.client.post('/login', data={'email': 'principal@college.com', 'password': 'principal123'})
        
        # 2. Principal assigns query #1 to HOD (User ID 3: CSE HOD)
        res_hod = self.client.post('/query/1/reassign', data={
            'assigned_staff_id': '3',
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(res_hod.status_code, 200)
        self.assertIn(b'Query assignments updated successfully', res_hod.data)
        
        # Verify in DB
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q1 = db.execute("SELECT assigned_staff_id FROM queries WHERE id = 1").fetchone()
        self.assertEqual(q1['assigned_staff_id'], 3)
        
        # 3. Principal assigns query #1 to Staff resolver (User ID 4: CSE Staff)
        res_staff = self.client.post('/query/1/reassign', data={
            'assigned_staff_id': '4',
            'priority': 'Critical'
        }, follow_redirects=True)
        self.assertEqual(res_staff.status_code, 200)
        self.assertIn(b'Query assignments updated successfully', res_staff.data)
        
        q2 = db.execute("SELECT assigned_staff_id, priority FROM queries WHERE id = 1").fetchone()
        self.assertEqual(q2['assigned_staff_id'], 4)
        self.assertEqual(q2['priority'], 'Critical')
        db.close()

    def test_keywords_with_and_without_spaces(self):
        """Verify keywords match accurately BOTH with spaces and without spaces (concatenated)."""
        space_pairs = [
            # Academics
            ("internal exam marks", "Academics"),
            ("internalexam marks", "Academics"),
            ("semester exam portion", "Academics"),
            ("semesterexam portion", "Academics"),
            ("mid exam timetable", "Academics"),
            ("midexam timetable", "Academics"),
            ("question paper review", "Academics"),
            ("questionpaper review", "Academics"),
            ("mini project evaluation", "Academics"),
            ("miniproject evaluation", "Academics"),
            ("study material download", "Academics"),
            ("studymaterial download", "Academics"),
            ("academic calendar release", "Academics"),
            ("academiccalendar release", "Academics"),
            ("hall ticket missing", "Academics"),
            ("hallticket missing", "Academics"),
            ("crt training batch", "Academics"),
            ("crttraining batch", "Academics"),
            ("technical training session", "Academics"),
            ("technicaltraining session", "Academics"),
            
            # Administrative
            ("tuition fee payment", "Administrative"),
            ("tuitionfee payment", "Administrative"),
            ("hostel fee refund", "Administrative"),
            ("hostelfee refund", "Administrative"),
            ("student id card", "Administrative"),
            ("studentid card", "Administrative"),
            ("idcard correction", "Administrative"),
            ("financial aid processing", "Administrative"),
            ("financialaid processing", "Administrative"),
            ("password reset request", "Administrative"),
            ("passwordreset request", "Administrative"),
            ("name correction in certificate", "Administrative"),
            ("namecorrection in certificate", "Administrative"),
            ("bona fide certificate", "Administrative"),
            ("bonafide certificate", "Administrative"),
            
            # Others
            ("anti ragging issue", "Others"),
            ("antiragging issue", "Others"),
            ("wi fi connection problem", "Others"),
            ("wifi connection problem", "Others"),
            ("senior harassment incident", "Others"),
            ("seniorharassment incident", "Others"),
            ("ragging complaint against hostel", "Others"),
            ("raggingcomplaint against hostel", "Others")
        ]
        
        for phrase, expected_cat in space_pairs:
            res = classify_query(title=phrase, description=phrase)
            self.assertEqual(res['category'], expected_cat, f"Failed for '{phrase}': expected {expected_cat}, got {res['category']}")

    def test_timetable_and_schedule_queries(self):
        """Verify timetable and class scheduling queries route strictly to Academics."""
        timetable_cases = [
            ("timetable", "Academics"),
            ("time table", "Academics"),
            ("time-table", "Academics"),
            ("timetabel", "Academics"),
            ("midterm exam timetable clash", "Academics"),
            ("B.Tech 3rd year class timetable update", "Academics"),
            ("Lecture schedule and period timing", "Academics"),
            ("Faculty rescheduling 4th period class", "Academics")
        ]
        for query, expected in timetable_cases:
            res = classify_query(description=query, title=query)
            self.assertEqual(res['category'], expected, f"Failed for '{query}': expected {expected}, got {res['category']}")

    def test_typos_and_fuzzy_variations(self):
        """Verify typos and spelling variations are accurately resolved."""
        typo_cases = [
            ("attendence percentage shortage", "Academics"),
            ("syllubus not covered by faculty", "Academics"),
            ("schollarship amount delayed in portal", "Administrative"),
            ("bonofide certifcate verification request", "Administrative"),
            ("washroom cleenliness and bad smell", "Others"),
            ("electrisity and fan broken in room", "Others")
        ]
        for query, expected in typo_cases:
            res = classify_query(description=query, title=query)
            self.assertEqual(res['category'], expected, f"Failed for '{query}': expected {expected}, got {res['category']}")

    def test_contextual_disambiguation(self):
        """Verify queries with cross-domain keywords disambiguate to the correct category."""
        disambiguation_cases = [
            ("Exam fee payment receipt pending", "Administrative"),
            ("Exam timetable and syllabus portion", "Academics"),
            ("Hostel room tap water leakage", "Others"),
            ("Hostel room admission allotment", "Administrative"),
            ("Classroom projector and fan repair", "Others"),
            ("Classroom faculty lecture cancelled", "Academics")
        ]
        for query, expected in disambiguation_cases:
            res = classify_query(description=query, title=query)
            self.assertEqual(res['category'], expected, f"Failed for '{query}': expected {expected}, got {res['category']}")

    def test_tanglish_vernacular_queries(self):
        """Verify Telugu/Tanglish queries route accurately."""
        tanglish_cases = [
            ("Internal marks raledhu sir please update", "Academics"),
            ("Syllabus avvaledhu classes jaragadam ledu", "Academics"),
            ("Fee kattanu kani portal lo receipt raledhu", "Administrative"),
            ("Scholarship amount padaledhu account lo", "Administrative"),
            ("Hostel washroom lo water ravadam ledu", "Others"),
            ("Seniors hostel daggara ragging chesthunnaru", "Others"),
            ("Training classes eppudu start avthayi?", "Academics")
        ]
        for query, expected in tanglish_cases:
            res = classify_query(description=query, title=query)
            self.assertEqual(res['category'], expected, f"Failed for '{query}': expected {expected}, got {res['category']}")



    def test_post_reply_and_view_details_no_error(self):
        """Verify staff/HOD can post message reply and view query details without any NameError."""
        # 1. Login as CSE Staff (User ID 4)
        self.client.post('/login', data={'email': 'cse-staff@college.com', 'password': 'staff123'})
        
        # 2. View Query Details page
        res_view = self.client.get('/query/1')
        self.assertEqual(res_view.status_code, 200)
        self.assertIn(b'Query #1', res_view.data)
        
        # 3. Post a reply
        res_reply = self.client.post('/query/1/message', data={
            'message': 'We are looking into your query and will resolve shortly.'
        }, follow_redirects=True)
        self.assertEqual(res_reply.status_code, 200)
        self.assertIn(b'We are looking into your query', res_reply.data)

    def test_api_classify_preview_endpoint(self):
        """Verify /api/classify-preview returns accurate real-time category and priority preview."""
        res = self.client.post('/api/classify-preview', json={
            'title': 'Internal marks discrepancy in DBMS',
            'description': 'Marks entered incorrectly in student portal.'
        })
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data['category'], 'Academics')
        self.assertIn('priority', data)
        self.assertIn('explanation', data)


    def test_anonymous_student_registration(self):
        """Test student registering with UG Level, Program, Branch, Year, and optional Regd ID."""
        res = self.client.post('/register', data={
            'name': 'Fearless Student',
            'email': 'fearless.student@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'student',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Artificial Intelligence & Data Science (AIDS)',
            'year': '2',
            'roll_no': '22B91A5401'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

    def test_faculty_registration_as_hod(self):
        """Test faculty registering with HOD role and branch."""
        res = self.client.post('/register', data={
            'name': 'Dr. Sarah Jenkins',
            'email': 'sarah.jenkins@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'faculty',
            'faculty_role_type': 'hod',
            'faculty_department': 'Computer Science & Engineering (CSE)',
            'designation': 'Head of Department'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

    def test_faculty_registration_as_admin(self):
        """Test registering as Central Admin."""
        res = self.client.post('/register', data={
            'name': 'Central Admin Officer',
            'email': 'central.officer@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'faculty',
            'faculty_role_type': 'admin',
            'designation': 'Central Administrator'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

    def test_department_staff_demo_login(self):
        """Test Department Staff demo login."""
        res = self.client.post('/login', data={
            'email': 'staff@college.com',
            'password': 'staff123'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

    def test_logout_redirects_to_homepage(self):
        """Test that logout immediately redirects user to home page ('/')."""
        self.client.post('/login', data={'email': 'student@college.com', 'password': 'student123'})
        res = self.client.get('/logout', follow_redirects=False)
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.headers['Location'].endswith('/'))

    def test_admin_deactivation_toggle(self):
        """Test that admin can deactivate and reactivate a user."""
        self.client.post('/login', data={'email': 'admin@college.com', 'password': 'admin123'})
        res = self.client.post('/admin/users', data={
            'action': 'toggle_status',
            'user_id': '1'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'User account has been', res.data)

    def test_staff_assignment_on_query(self):
        """Test assigning a staff member by ID to a query by Chief Admin."""
        self.client.post('/login', data={'email': 'admin@college.com', 'password': 'admin123'})
        res = self.client.post('/query/1/reassign', data={
            'assigned_staff_id': '3',
            'priority': 'High',
            'department': 'Academics'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

    def test_staff_solves_query_and_updates_status(self):
        """Test that department staff can update query status to In Progress / Resolved."""
        self.client.post('/login', data={'email': 'academics-staff@college.com', 'password': 'staff123'})
        res = self.client.post('/query/1/status', data={
            'status': 'Resolved'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Query status successfully updated to Resolved', res.data)

    def test_hod_assigns_department_staff(self):
        """Verify that HOD can login and assign queries to their department staff."""
        # Login as CSE HOD
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res = self.client.post('/query/2/reassign', data={
            'assigned_staff_id': '4',
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Query assignments updated successfully', res.data)

    def test_admin_pie_chart_analytics_api(self):
        """Verify that Central Admin analytics endpoint returns Department and Student Year distributions."""
        self.client.post('/login', data={'email': 'admin@college.com', 'password': 'admin123'})
        res = self.client.get('/api/analytics-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn('departments', data)
        self.assertIn('years', data)
        self.assertIn('matrix', data)
        self.assertIn('categories', data)
        self.assertTrue(len(data['departments']['labels']) > 0)
        self.assertTrue(len(data['years']['labels']) > 0)

    def test_hod_branch_pie_chart_analytics_api(self):
        """Verify that HOD analytics endpoint returns branch-specific year and category distributions."""
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res = self.client.get('/api/analytics-data')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data['is_hod'])
        self.assertIn('years', data)
        self.assertIn('categories', data)

    def test_admin_hod_messaging(self):
        """Verify direct message flow between Central Admin and Branch HOD."""
        # 1. Admin sends message to CSE HOD (id: 3)
        self.client.post('/login', data={'email': 'admin@college.com', 'password': 'admin123'})
        res = self.client.post('/api/admin-hod-messages/3', json={'message': 'Please review pending lab query.'})
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json()['status'], 'success')

        # 2. HOD fetches messages
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res2 = self.client.get('/api/admin-hod-messages/3')
        self.assertEqual(res2.status_code, 200)
        messages = res2.get_json()['messages']
        self.assertTrue(any('Please review pending lab query' in m['message'] for m in messages))

    def test_degree_specific_routing_btech_vs_mtech(self):
        """Verify that B.Tech queries ONLY appear in B.Tech HOD queue, and M.Tech queries ONLY appear in M.Tech HOD queue."""
        # 1. Submit B.Tech CSE Query
        res1 = self.client.post('/submit-query', data={
            'query_type': 'student',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'B.Tech DBMS Lab MySQL Connection Issue',
            'description': 'Students cannot connect to MySQL server on CSE Lab 4 during practical session.'
        }, follow_redirects=True)
        self.assertEqual(res1.status_code, 200)

        # 2. Submit M.Tech CSE Query
        res2 = self.client.post('/submit-query', data={
            'query_type': 'student',
            'level': 'PG',
            'course': 'M.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '1',
            'title': 'M.Tech Deep Learning GPU Cluster Allocation',
            'description': 'NVIDIA A100 GPU cluster access keys required for M.Tech dissertation batch.'
        }, follow_redirects=True)
        self.assertEqual(res2.status_code, 200)

        # 3. Check B.Tech CSE HOD Dashboard -> Must see B.Tech query, MUST NOT see M.Tech query
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res_btech_hod = self.client.get('/department-dashboard')
        self.assertEqual(res_btech_hod.status_code, 200)
        self.assertIn(b'B.Tech DBMS Lab MySQL Connection Issue', res_btech_hod.data)
        self.assertNotIn(b'M.Tech Deep Learning GPU Cluster Allocation', res_btech_hod.data)

        # 4. Check M.Tech CSE HOD Dashboard -> Must see M.Tech query, MUST NOT see B.Tech query
        self.client.post('/login', data={'email': 'mtech-cse-hod@college.com', 'password': 'hod123'})
        res_mtech_hod = self.client.get('/department-dashboard')
        self.assertEqual(res_mtech_hod.status_code, 200)
        self.assertIn(b'M.Tech Deep Learning GPU Cluster Allocation', res_mtech_hod.data)
        self.assertNotIn(b'B.Tech DBMS Lab MySQL Connection Issue', res_mtech_hod.data)

    def test_administrative_and_principal_routing(self):
        """Verify that Administrative queries route to AO and Others queries route to Principal."""
        # Administrative query
        self.client.post('/submit-query', data={
            'query_type': 'student',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'Fee Receipt Verification Delay',
            'description': 'Tuition fee payment challan submitted 5 days ago but receipt is still pending.'
        }, follow_redirects=True)

        # AO logs in
        self.client.post('/login', data={'email': 'ao@college.com', 'password': 'ao123'})
        res_ao = self.client.get('/department-dashboard?dept=Administrative')
        self.assertEqual(res_ao.status_code, 200)
        self.assertIn(b'Fee Receipt Verification Delay', res_ao.data)

        # Others query
        self.client.post('/submit-query', data={
            'query_type': 'student',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'Hostel Cleanliness Issue',
            'description': 'Hostel water cooler and corridor cleaning requested.'
        }, follow_redirects=True)

        # Principal logs in
        self.client.post('/login', data={'email': 'principal@college.com', 'password': 'principal123'})
        res_prin = self.client.get('/department-dashboard?dept=Others')
        self.assertEqual(res_prin.status_code, 200)
        self.assertIn(b'Hostel Cleanliness Issue', res_prin.data)

    def test_post_query_no_autofocus(self):
        """Verify /submit-query page does not contain autofocus on title input to ensure top of page opens cleanly."""
        res = self.client.get('/submit-query')
        self.assertEqual(res.status_code, 200)
        self.assertNotIn(b'autofocus', res.data)
        self.assertIn(b'Student Academic Details', res.data)

    def test_query_details_active_participants_and_presence(self):
        """Verify query details page renders accurate Submitter, Authority (HOD/AO/Principal), and Assigned Staff presence cards."""
        # 1. Login as B.Tech CSE HOD and view Query #1
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res = self.client.get('/query/1')
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Active Query Participants', res.data)
        self.assertIn(b'Branch HOD', res.data)
        self.assertIn(b'Online Now', res.data)

    def test_department_dashboard_tabs_received_and_assigned(self):
        """Verify that Department Dashboard supports Received, Assigned (From Principal), and Delegated tabs."""
        # Login as B.Tech CSE HOD
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        
        # 1. Received queries view
        res_recv = self.client.get('/department-dashboard?view=received')
        self.assertEqual(res_recv.status_code, 200)
        self.assertIn(b'Received Queries', res_recv.data)
        self.assertIn(b'Assigned Queries (From Principal)', res_recv.data)
        self.assertIn(b'Delegated to Staff', res_recv.data)

        # 2. Assigned queries view
        res_assigned = self.client.get('/department-dashboard?view=assigned')
        self.assertEqual(res_assigned.status_code, 200)

        # 3. Delegated queries view
        res_delegated = self.client.get('/department-dashboard?view=delegated')
        self.assertEqual(res_delegated.status_code, 200)

        # 4. Unassigned queries view
        res_unassigned = self.client.get('/department-dashboard?view=unassigned')
        self.assertEqual(res_unassigned.status_code, 200)

    def test_principal_assign_to_hod_and_hod_delegation_flow(self):
        """Verify workflow: Principal assigns to HOD -> HOD sees it in dashboard -> HOD can resolve directly or delegate to staff."""
        # 1. Post a query under Others (routed to Principal desk)
        self.client.post('/submit-query', data={
            'query_type': 'student',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'Lab Computer Power Surge Issue',
            'description': 'Frequent power trip in computer lab 3 causing machine shutdowns.'
        }, follow_redirects=True)

        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q = db.execute("SELECT * FROM queries WHERE title = 'Lab Computer Power Surge Issue'").fetchone()
        self.assertIsNotNone(q)
        query_id = q['id']
        db.close()

        # 2. Principal logs in and assigns this query to B.Tech CSE HOD (User ID 3)
        self.client.post('/login', data={'email': 'principal@college.com', 'password': 'principal123'})
        res_assign = self.client.post(f'/query/{query_id}/reassign', data={
            'assigned_staff_id': '3',
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(res_assign.status_code, 200)

        # Verify DB assigned_staff_id is HOD
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q_assigned = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
        self.assertEqual(q_assigned['assigned_staff_id'], 3)
        db.close()

        # 3. HOD logs in and checks dashboard
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        
        # Check Assigned Queries (From Principal) tab
        res_hod_assigned = self.client.get('/department-dashboard?view=assigned')
        self.assertEqual(res_hod_assigned.status_code, 200)
        self.assertIn(b'Lab Computer Power Surge Issue', res_hod_assigned.data)
        self.assertIn(b'Assigned to You (From Principal)', res_hod_assigned.data)

        # 4. HOD views query details
        res_hod_details = self.client.get(f'/query/{query_id}')
        self.assertEqual(res_hod_details.status_code, 200)
        self.assertIn(b'Assigned to You (HOD Desk)', res_hod_details.data)
        self.assertIn(b'Resolution & Status Desk', res_hod_details.data)

        # 5. HOD delegates query to CSE Staff Resolver (User ID 4)
        res_delegate = self.client.post(f'/query/{query_id}/reassign', data={
            'assigned_staff_id': '4',
            'priority': 'High'
        }, follow_redirects=True)
        self.assertEqual(res_delegate.status_code, 200)

        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q_delegated = db.execute("SELECT * FROM queries WHERE id = ?", (query_id,)).fetchone()
        self.assertEqual(q_delegated['assigned_staff_id'], 4)
        db.close()

        # 6. Assigned Staff logs in and resolves the query
        self.client.get('/logout')
        self.client.post('/login', data={'email': 'cse-staff@college.com', 'password': 'staff123'})
        res_staff_dash = self.client.get('/department-dashboard')
        self.assertEqual(res_staff_dash.status_code, 200)
        self.assertIn(b'Lab Computer Power Surge Issue', res_staff_dash.data)

        res_resolve = self.client.post(f'/query/{query_id}/status', data={
            'status': 'Resolved'
        }, follow_redirects=True)
        self.assertEqual(res_resolve.status_code, 200)

        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q_final = db.execute("SELECT status FROM queries WHERE id = ?", (query_id,)).fetchone()
        self.assertEqual(q_final['status'], 'Resolved')
        db.close()

    def test_faculty_staff_ao_hod_principal_no_track_query_status(self):
        """Verify that Faculty, Staff, AO, HOD, and Principal do not have Track Query Status in navbar/home and get redirected to official desks."""
        # 1. Test Faculty
        self.client.post('/login', data={'email': 'prof.sharma@college.com', 'password': 'faculty123'})
        res_fac_home = self.client.get('/')
        self.assertNotIn(b'Track Query Status', res_fac_home.data)
        self.assertIn(b'My Workspace', res_fac_home.data)
        
        res_fac_track = self.client.get('/track-query', follow_redirects=False)
        self.assertEqual(res_fac_track.status_code, 302)
        self.assertIn('/dashboard', res_fac_track.headers['Location'])
        self.client.get('/logout')

        # 2. Test Staff
        self.client.post('/login', data={'email': 'cse-staff@college.com', 'password': 'staff123'})
        res_st_home = self.client.get('/')
        self.assertNotIn(b'Track Query Status', res_st_home.data)
        self.assertIn(b'Received Queries', res_st_home.data)
        self.assertIn(b'Assigned Queries', res_st_home.data)
        
        res_st_track = self.client.get('/track-query', follow_redirects=False)
        self.assertEqual(res_st_track.status_code, 302)
        self.assertIn('/department-dashboard', res_st_track.headers['Location'])
        self.client.get('/logout')

        # 3. Test HOD
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res_hod_home = self.client.get('/')
        self.assertNotIn(b'Track Query Status', res_hod_home.data)
        self.assertIn(b'Received Queries', res_hod_home.data)
        self.assertIn(b'Assigned Queries (from Principal)', res_hod_home.data)
        
        # Accessing /track-query directly as HOD redirects to department dashboard
        res_hod_track = self.client.get('/track-query', follow_redirects=False)
        self.assertEqual(res_hod_track.status_code, 302)
        self.assertIn('/department-dashboard', res_hod_track.headers['Location'])
        
        # Accessing /track-query?query_id=1 as HOD redirects to query_details
        res_hod_track_q = self.client.get('/track-query?query_id=1', follow_redirects=False)
        self.assertEqual(res_hod_track_q.status_code, 302)
        self.assertIn('/query/1', res_hod_track_q.headers['Location'])
        self.client.get('/logout')

        # 4. Test AO
        self.client.post('/login', data={'email': 'ao@college.com', 'password': 'ao123'})
        res_ao_home = self.client.get('/')
        self.assertNotIn(b'Track Query Status', res_ao_home.data)
        self.assertIn(b'Received Queries', res_ao_home.data)
        self.assertIn(b'Assigned Queries (from Principal)', res_ao_home.data)
        
        res_ao_track = self.client.get('/track-query', follow_redirects=False)
        self.assertEqual(res_ao_track.status_code, 302)
        self.assertIn('Administrative', res_ao_track.headers['Location'])
        self.client.get('/logout')

        # 5. Test Principal
        self.client.post('/login', data={'email': 'principal@college.com', 'password': 'principal123'})
        res_princ_home = self.client.get('/')
        self.assertNotIn(b'Track Query Status', res_princ_home.data)
        self.assertNotIn(b'Track Status', res_princ_home.data)
        self.assertIn(b'Principal Desk', res_princ_home.data)
        
        res_princ_track = self.client.get('/track-query', follow_redirects=False)
        self.assertEqual(res_princ_track.status_code, 302)
        self.assertIn('Others', res_princ_track.headers['Location'])
        self.client.get('/logout')

        # 6. Verify unauthenticated student still sees Track Query Status
        res_guest_home = self.client.get('/')
        self.assertIn(b'Track Query Status', res_guest_home.data)

    def test_post_query_and_trace_flow(self):
        """Verify complete flow: submit query -> view confirmation -> track query status & send reply."""
        # 1. Post a new Academic query as student
        res_submit = self.client.post('/submit-query', data={
            'query_type': 'student',
            'name': 'Rahul Varma',
            'email': 'rahul.test@college.edu',
            'roll_no': '21A91A0588',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'Operating System Lab Viva Timetable Clarification',
            'description': 'Kindly provide the detailed batch schedule and timetable for OS practical exam.'
        }, follow_redirects=True)
        self.assertEqual(res_submit.status_code, 200)
        self.assertIn(b'Your Query is Logged!', res_submit.data)
        
        # Get query ID from database
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q = db.execute("SELECT * FROM queries WHERE title = 'Operating System Lab Viva Timetable Clarification'").fetchone()
        self.assertIsNotNone(q)
        qid = q['id']
        db.close()

        # 2. Track query via /track-query?query_id=<qid>
        res_track = self.client.get(f'/track-query?query_id={qid}')
        self.assertEqual(res_track.status_code, 200)
        self.assertIn(b'Operating System Lab Viva Timetable Clarification', res_track.data)
        self.assertIn(b'Active Query Participants', res_track.data)
        self.assertIn(b'Rahul Varma', res_track.data)
        self.assertIn(b'Branch HOD', res_track.data)

        # 3. Post a student reply from the tracking page
        res_reply = self.client.post('/track-query', data={
            'action': 'send_reply',
            'target_query_id': str(qid),
            'message': 'Also need syllabus details for Viva.',
            'sender_name': 'Rahul Varma'
        }, follow_redirects=True)
        self.assertEqual(res_reply.status_code, 200)
        self.assertIn(b'Also need syllabus details for Viva.', res_reply.data)

        # 4. Post an Administrative query (e.g. Theft) & Track
        res_admin = self.client.post('/submit-query', data={
            'query_type': 'student',
            'name': 'Pooja Reddy',
            'email': 'pooja.test@college.edu',
            'roll_no': '21A91A0599',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '3',
            'title': 'Theft complaint regarding lost mobile',
            'description': 'My mobile phone was stolen in campus cafeteria.'
        }, follow_redirects=True)
        self.assertEqual(res_admin.status_code, 200)
        self.assertIn(b'Your Query is Logged!', res_admin.data)
        
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q_adm = db.execute("SELECT * FROM queries WHERE title = 'Theft complaint regarding lost mobile'").fetchone()
        self.assertIsNotNone(q_adm)
        self.assertEqual(q_adm['category'], 'Administrative')
        db.close()
        
        res_track_adm = self.client.get(f'/track-query?query_id={q_adm["id"]}')
        self.assertEqual(res_track_adm.status_code, 200)
        self.assertIn(b'Administrative Officer (AO)', res_track_adm.data)

        # 5. Post a Campus Support / Others query & Track
        res_oth = self.client.post('/submit-query', data={
            'query_type': 'student',
            'name': 'Kiran Kumar',
            'email': 'kiran.test@college.edu',
            'roll_no': '21A91A0512',
            'level': 'UG',
            'course': 'B.Tech',
            'department': 'Computer Science & Engineering (CSE)',
            'year': '2',
            'title': 'Campus Wi-Fi connectivity broken',
            'description': 'Wi-Fi connection is not working in block 2.'
        }, follow_redirects=True)
        self.assertEqual(res_oth.status_code, 200)
        
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q_oth = db.execute("SELECT * FROM queries WHERE title = 'Campus Wi-Fi connectivity broken'").fetchone()
        self.assertIsNotNone(q_oth)
        self.assertEqual(q_oth['category'], 'Others')
        db.close()
        
        res_track_oth = self.client.get(f'/track-query?query_id={q_oth["id"]}')
        self.assertEqual(res_track_oth.status_code, 200)
        self.assertIn(b'Principal Executive Desk', res_track_oth.data)

    def test_navigation_received_and_assigned_queries_for_faculty_hod_ao(self):
        """Verify navigation bar explicitly presents Received Queries and Assigned Queries for Faculty, HOD, and AO."""
        # 1. HOD: Received Queries and Assigned Queries (from Principal)
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res_hod = self.client.get('/department-dashboard')
        self.assertEqual(res_hod.status_code, 200)
        self.assertIn(b'Received Queries', res_hod.data)
        self.assertIn(b'Assigned Queries (from Principal)', res_hod.data)
        
        # Test clicking Assigned Queries tab
        res_hod_assigned = self.client.get('/department-dashboard?view=assigned')
        self.assertEqual(res_hod_assigned.status_code, 200)
        
        # Test clicking Received Queries tab
        res_hod_received = self.client.get('/department-dashboard?view=received')
        self.assertEqual(res_hod_received.status_code, 200)
        self.client.get('/logout')

        # 2. AO: Received Queries and Assigned Queries (from Principal)
        self.client.post('/login', data={'email': 'ao@college.com', 'password': 'ao123'})
        res_ao = self.client.get('/department-dashboard?dept=Administrative')
        self.assertEqual(res_ao.status_code, 200)
        self.assertIn(b'Received Queries', res_ao.data)
        self.assertIn(b'Assigned Queries (from Principal)', res_ao.data)
        
        # Test AO assigned and received views
        res_ao_assigned = self.client.get('/department-dashboard?dept=Administrative&view=assigned')
        self.assertEqual(res_ao_assigned.status_code, 200)
        res_ao_received = self.client.get('/department-dashboard?dept=Administrative&view=received')
        self.assertEqual(res_ao_received.status_code, 200)
        self.client.get('/logout')

        # 3. Faculty / Staff: Received Queries and Assigned Queries (from HOD/Principal)
        self.client.post('/login', data={'email': 'cse-staff@college.com', 'password': 'staff123'})
        res_staff = self.client.get('/department-dashboard')
        self.assertEqual(res_staff.status_code, 200)
        self.assertIn(b'Received Queries', res_staff.data)
        self.assertIn(b'Assigned Queries (from HOD/Principal)', res_staff.data)
        
        res_staff_assigned = self.client.get('/department-dashboard?view=assigned')
        self.assertEqual(res_staff_assigned.status_code, 200)
        res_staff_received = self.client.get('/department-dashboard?view=received')
        self.assertEqual(res_staff_received.status_code, 200)
        self.client.get('/logout')

    def test_faculty_query_tracking_shows_faculty_role(self):
        """Verify that faculty queries tracked via /track-query display Faculty (You) instead of Student (You)."""
        # Submit a faculty query
        res = self.client.post('/submit-query', data={
            'query_type': 'faculty',
            'department': 'Computer Science & Engineering (CSE)',
            'title': 'Faculty Salary Increment Request',
            'description': 'Increment the salary as per annual review.'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)

        # Extract query id
        import re
        m = re.search(r'#(\d+)', res.data.decode('utf-8'))
        self.assertIsNotNone(m)
        qid = m.group(1)

        # Track query status
        track_res = self.client.get(f'/track-query?query_id={qid}')
        self.assertEqual(track_res.status_code, 200)
        content = track_res.data.decode('utf-8')
        self.assertIn('Faculty (You)', content)
        self.assertIn('Faculty Query', content)
        self.assertNotIn('Student (You)', content)

    def test_faculty_academic_hierarchy_submission(self):
        """Verify faculty query submission with academic level (UG, PG), course, department, designation."""
        # Submit a PG Faculty query (e.g. M.Tech in CSE)
        res_pg = self.client.post('/submit-query', data={
            'query_type': 'faculty',
            'faculty_level': 'PG',
            'faculty_course': 'M.Tech',
            'faculty_department': 'Computer Science & Engineering (CSE)',
            'faculty_designation': 'Associate Professor',
            'faculty_id': 'FAC-PG-001',
            'name': 'Dr. Sharma',
            'email': 'dr.sharma@college.edu',
            'title': 'M.Tech Lab GPU Server Allocation',
            'description': 'Need additional GPU cluster server for M.Tech advanced deep learning projects.'
        }, follow_redirects=True)
        self.assertEqual(res_pg.status_code, 200)

        # Check DB records
        db = sqlite3.connect(Config.DATABASE_PATH)
        db.row_factory = sqlite3.Row
        q = db.execute("SELECT * FROM queries WHERE title = 'M.Tech Lab GPU Server Allocation'").fetchone()
        self.assertIsNotNone(q)
        self.assertEqual(q['level'], 'PG')
        self.assertEqual(q['course'], 'M.Tech')
        self.assertEqual(q['department'], 'Computer Science & Engineering (CSE)')

        # Check user record
        u = db.execute("SELECT * FROM users WHERE email = 'dr.sharma@college.edu'").fetchone()
        self.assertIsNotNone(u)
        self.assertEqual(u['level'], 'PG')
        self.assertEqual(u['course'], 'M.Tech')
        self.assertEqual(u['department'], 'Computer Science & Engineering (CSE)')
        self.assertEqual(u['designation'], 'Associate Professor')
        self.assertEqual(u['roll_no'], 'FAC-PG-001')
        qid = q['id']
        db.close()

        # Track query displays M.Tech and Faculty details
        res_track = self.client.get(f'/track-query?query_id={qid}')
        self.assertEqual(res_track.status_code, 200)
        track_html = res_track.data.decode('utf-8')
        self.assertIn('Associate Professor', track_html)
        self.assertIn('M.Tech', track_html)

        # HOD views query details with faculty designation
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res_det = self.client.get(f'/query/{qid}')
        self.assertEqual(res_det.status_code, 200)
        det_html = res_det.data.decode('utf-8')
        self.assertIn('Associate Professor', det_html)
        self.assertIn('M.Tech', det_html)
        self.client.get('/logout')

    def test_track_query_non_existent_and_attribute_error_prevention(self):
        """Verify tracking non-existent IDs displays 'No Query Found', does not crash with AttributeError, and opens only valid queries."""
        # 1. Non-existent query ID
        res_missing = self.client.get('/track-query?query_id=99999')
        self.assertEqual(res_missing.status_code, 200)
        missing_html = res_missing.data.decode('utf-8')
        self.assertIn('No Query Found for ID #99999', missing_html)
        self.assertNotIn('Resolution Lifecycle Progress:', missing_html)

        # 2. Invalid non-numeric query ID
        res_invalid = self.client.get('/track-query?query_id=invalid_xyz')
        self.assertEqual(res_invalid.status_code, 200)
        invalid_html = res_invalid.data.decode('utf-8')
        self.assertIn('Invalid Query ID', invalid_html)
        self.assertNotIn('Resolution Lifecycle Progress:', invalid_html)

        # 3. Existing query (ID 1) opens cleanly without AttributeError
        res_valid = self.client.get('/track-query?query_id=1')
        self.assertEqual(res_valid.status_code, 200)
        valid_html = res_valid.data.decode('utf-8')
        self.assertIn('Query #1', valid_html)
        self.assertIn('Resolution Lifecycle Progress:', valid_html)
        self.assertNotIn('No Query Found for ID', valid_html)

        # 4. Logged-in Staff tracks non-existent ID -> shows No Query Found, does not crash
        self.client.post('/login', data={'email': 'cse-staff@college.com', 'password': 'staff123'})
        res_staff_missing = self.client.get('/track-query?query_id=88888')
        self.assertEqual(res_staff_missing.status_code, 200)
        staff_missing_html = res_staff_missing.data.decode('utf-8')
        self.assertIn('No Query Found for ID #88888', staff_missing_html)

        # Logged-in Staff tracks existing ID -> opens query and provides Resolution Desk button
        res_staff_valid = self.client.get('/track-query?query_id=1')
        self.assertEqual(res_staff_valid.status_code, 200)
        staff_valid_html = res_staff_valid.data.decode('utf-8')
        self.assertIn('Query #1', staff_valid_html)
        self.assertIn('Open in Resolution Desk', staff_valid_html)
        self.client.get('/logout')

if __name__ == '__main__':
    unittest.main()


