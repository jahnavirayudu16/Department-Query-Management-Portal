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
            ("My internal marks are incorrect for DSP subject.", "Academics", "High"),
            ("Attendance percentage shortage correction in Operating Systems.", "Academics", "High"),
            ("Cannot download hall ticket for supplementary exam.", "Academics", "High"),
            ("When will the midterm exam timetable be published?", "Academics", "Medium"),
            ("Assignment submission deadline extension requested.", "Academics", "Medium"),
            
            # 2. Administrative
            ("My semester fee payment of 45,000 is not updated.", "Administrative", "Medium"),
            ("Need urgent bonafide certificate for passport application.", "Administrative", "Low"),
            ("Scholarship disbursement amount has not been credited.", "Administrative", "Medium"),
            ("Need study certificate and transfer certificate verification.", "Administrative", "Medium"),
            ("Name correction in college student records.", "Administrative", "Medium"),
            
            # 3. Others
            ("Campus Wi-Fi is not working in computer lab.", "Others", "High"),
            ("Severe water leakage in hostel room 314.", "Others", "High"),
            ("The college bus on route 4 was delayed today.", "Others", "Medium"),
            ("Drinking water cooler in mess needs filter replacement.", "Others", "Medium"),
            ("Projector in smart classroom 204 is broken.", "Others", "High"),
            ("Random general query without specific words", "Others", "Medium")
        ]
        
        for text, expected_cat, expected_priority in test_cases:
            result = classify_query(text, text)
            print(f"Testing Query: '{text}' -> Classified: {result['category']} ({result['priority']})")
            self.assertEqual(result['category'], expected_cat, f"Failed for '{text}': expected {expected_cat}, got {result['category']}")
            self.assertEqual(result['priority'], expected_priority, f"Failed priority for '{text}': expected {expected_priority}, got {result['priority']}")

    def test_priority_detection(self):
        """Test specific priority detection patterns."""
        self.assertEqual(detect_priority("Urgent emergency critical short circuit"), "Urgent")
        self.assertEqual(detect_priority("The server is broken and not working"), "High")
        self.assertEqual(detect_priority("Status is pending approval"), "Medium")
        self.assertEqual(detect_priority("What are the working hours and timings?"), "Low")

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

    def test_hod_branch_analytics_view_and_api(self):
        """Verify that HOD can access /hod/analytics and receive branch-scoped analytics data."""
        # 1. Login as B.Tech CSE HOD
        self.client.post('/login', data={'email': 'cse-hod@college.com', 'password': 'hod123'})
        res_page = self.client.get('/hod/analytics')
        self.assertEqual(res_page.status_code, 200)
        self.assertIn(b'Branch Analytics', res_page.data)
        self.assertIn(b'tab-branch', res_page.data)

        # 2. Verify API returns branch_analysis
        res_api = self.client.get('/api/analytics-data')
        self.assertEqual(res_api.status_code, 200)
        data = res_api.get_json()
        self.assertTrue(data['is_hod'])
        self.assertIn('branch_analysis', data)
        self.assertIsNotNone(data['branch_analysis'])
        self.assertEqual(data['branch_analysis']['course'], 'B.Tech')
        self.assertIn('staff_workload', data['branch_analysis'])

if __name__ == '__main__':
    unittest.main()



