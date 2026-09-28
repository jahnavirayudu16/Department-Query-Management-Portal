import sys
import os
import time
import json
import sqlite3
from flask import session

sys.path.insert(0, r"c:\Users\jahna\OneDrive\Desktop\DQM Portal")
from app import app

ACCOUNTS = {
    'admin': {'id': 12, 'role': 'admin', 'dept': 'Computer Science & Engineering (CSE)', 'course': 'B.Tech', 'name': 'Central Administrator'},
    'principal': {'id': 11, 'role': 'principal', 'dept': 'Others', 'course': 'B.Tech', 'name': 'Dr. Alan Turing'},
    'hod': {'id': 3, 'role': 'hod', 'dept': 'Computer Science & Engineering (CSE)', 'course': 'B.Tech', 'name': 'Dr. Grace Hopper'},
    'staff': {'id': 4, 'role': 'staff', 'dept': 'Computer Science & Engineering (CSE)', 'course': 'B.Tech', 'name': 'Prof. Linus Torvalds'},
    'faculty': {'id': 28, 'role': 'faculty', 'dept': 'General', 'course': 'B.Tech', 'name': 'Faculty Member'},
    'student': {'id': 1, 'role': 'student', 'dept': 'Computer Science & Engineering (CSE)', 'course': 'B.Tech', 'name': 'Student'}
}

def set_sess(client, role):
    u = ACCOUNTS[role]
    with client.session_transaction() as s:
        s['user_id'] = u['id']
        s['role'] = u['role']
        s['department'] = u['dept']
        s['course'] = u['course']
        s['name'] = u['name']
        s['_fresh'] = True

def test_all_flows():
    print("Testing each flow individually...")
    flows = [
        ('Home', lambda c: c.get('/')),
        ('Login', lambda c: c.post('/login', data={'email': 'student@college.com', 'password': 'student123'})),
        ('Student Dashboard', lambda c: (set_sess(c, 'student'), c.get('/dashboard'))[1]),
        ('Faculty Dashboard', lambda c: (set_sess(c, 'faculty'), c.get('/dashboard'))[1]),
        ('HOD Dashboard', lambda c: (set_sess(c, 'hod'), c.get('/department-dashboard'))[1]),
        ('Principal Dashboard', lambda c: (set_sess(c, 'principal'), c.get('/department-dashboard?dept=Others&view=received'))[1]),
        ('Department Dashboard', lambda c: (set_sess(c, 'staff'), c.get('/department-dashboard'))[1]),
        ('Notifications Centre', lambda c: (set_sess(c, 'student'), c.get('/notifications'))[1]),
        ('Query Details', lambda c: (set_sess(c, 'student'), c.get('/query/1'))[1]),
        ('Take Query', lambda c: (set_sess(c, 'principal'), c.post('/query/1/reassign', data={'action_type': 'take_query'}))[1]),
        ('Assign Query', lambda c: (set_sess(c, 'hod'), c.post('/query/1/reassign', data={'action_type': 'reassign', 'assigned_staff_id': '4'}))[1]),
        ('Escalate Query', lambda c: (set_sess(c, 'hod'), c.post('/query/1/reassign', data={'action_type': 'escalate_principal'}))[1]),
        ('Status Update', lambda c: (set_sess(c, 'staff'), c.post('/query/1/status', data={'status': 'In Progress'}))[1]),
        ('Post Message', lambda c: (set_sess(c, 'student'), c.post('/query/1/message', data={'message': 'Load test verification note'}))[1]),
        ('HOD <-> Principal Msg', lambda c: (set_sess(c, 'hod'), c.post('/api/admin-hod-messages/3', json={'partner_id': 11, 'message': 'HOD-Principal communication test'}))[1]),
        ('Analytics', lambda c: (set_sess(c, 'admin'), c.get('/analytics'))[1]),
        ('Query Classification', lambda c: c.post('/api/classify-preview', json={'title': 'Projector wifi issue', 'description': 'The lab projector cannot connect to network wifi'})),
        ('Logout', lambda c: c.get('/logout'))
    ]

    with app.test_client() as client:
        for name, fn in flows:
            t0 = time.perf_counter()
            resp = fn(client)
            dur = (time.perf_counter() - t0) * 1000
            print(f"[{name:<25}] Status: {resp.status_code} | Duration: {dur:.2f}ms")

if __name__ == '__main__':
    test_all_flows()
