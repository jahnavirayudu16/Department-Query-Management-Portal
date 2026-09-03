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
        """Test student registering with anonymous/optional name."""
        res = self.client.post('/register', data={
            'name': '',
            'email': 'fearless.student@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'student',
            'course': 'B.Tech',
            'year': '3',
            'department': 'Computer Science & Engineering (CSE)',
            'roll_no': ''
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)

    def test_staff_registration_with_required_name(self):
        """Test department staff registering with explicit staff name for assignment."""
        res = self.client.post('/register', data={
            'staff_name': 'Dr. Sarah Jenkins',
            'email': 'sarah.jenkins@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'staff',
            'department': 'Academics',
            'designation': 'Senior Academic Coordinator'
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

    def test_admin_registration_without_department(self):
        """Test Central Admin registering without department/wing."""
        res = self.client.post('/register', data={
            'staff_name': 'Central Dean of Exams',
            'email': 'central.dean@college.com',
            'password': 'password123',
            'confirm_password': 'password123',
            'role': 'admin',
            'designation': 'Central Dean'
        }, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn(b'Registration successful', res.data)


    def test_staff_and_admin_cannot_post_queries(self):
        """Verify that staff and central admin are forbidden from accessing query submission."""
        # Staff test
        self.client.post('/login', data={'email': 'staff@college.com', 'password': 'staff123'})
        res = self.client.get('/submit-query', follow_redirects=True)
        self.assertIn(b'Access restricted', res.data)

        # Admin test
        self.client.post('/login', data={'email': 'admin@college.com', 'password': 'admin123'})
        res = self.client.get('/submit-query', follow_redirects=True)
        self.assertIn(b'Access restricted', res.data)

if __name__ == '__main__':
    unittest.main()
