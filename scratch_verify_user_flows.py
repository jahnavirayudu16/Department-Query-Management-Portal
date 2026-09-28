import sys
import time
sys.path.insert(0, r"c:\Users\jahna\OneDrive\Desktop\DQM Portal")
from app import app
from scratch_test_flows import set_sess

def verify_single_user_experience():
    print("=== MANUAL SINGLE-USER WORKFLOW VERIFICATION (<1s TARGET) ===")
    
    with app.test_client() as c:
        # 1. Student Submit Query
        set_sess(c, 'student')
        t0 = time.perf_counter()
        resp = c.post('/submit-query', data={
            'title': 'Single User Experience Verification Query',
            'department': 'Computer Science & Engineering (CSE)',
            'category': 'Academics',
            'priority': 'Medium',
            'description': 'Verifying responsiveness for final submission quality assurance'
        }, follow_redirects=False)
        d_submit = (time.perf_counter() - t0) * 1000
        print(f"1. Student Submit Query:      Status={resp.status_code} | Duration={d_submit:.2f}ms | (<1s: {d_submit < 1000})")
        
        # 2. Staff/HOD Open Query
        set_sess(c, 'hod')
        t0 = time.perf_counter()
        resp = c.get('/query/1')
        d_open = (time.perf_counter() - t0) * 1000
        print(f"2. HOD Open Query:            Status={resp.status_code} | Duration={d_open:.2f}ms | (<1s: {d_open < 1000})")

        # 3. Principal Take Query
        set_sess(c, 'principal')
        t0 = time.perf_counter()
        resp = c.post('/query/1/reassign', data={'action_type': 'take_query'}, follow_redirects=False)
        d_take = (time.perf_counter() - t0) * 1000
        print(f"3. Principal Take Query:      Status={resp.status_code} | Duration={d_take:.2f}ms | (<1s: {d_take < 1000})")

        # 4. HOD Assign Query
        set_sess(c, 'hod')
        t0 = time.perf_counter()
        resp = c.post('/query/1/reassign', data={'action_type': 'reassign', 'assigned_staff_id': '4'}, follow_redirects=False)
        d_assign = (time.perf_counter() - t0) * 1000
        print(f"4. HOD Assign Query:          Status={resp.status_code} | Duration={d_assign:.2f}ms | (<1s: {d_assign < 1000})")

        # 5. HOD Escalate Query to Principal
        set_sess(c, 'hod')
        t0 = time.perf_counter()
        resp = c.post('/query/1/reassign', data={'action_type': 'escalate_principal'}, follow_redirects=False)
        d_esc = (time.perf_counter() - t0) * 1000
        print(f"5. HOD Escalate to Principal: Status={resp.status_code} | Duration={d_esc:.2f}ms | (<1s: {d_esc < 1000})")

        # 6. Staff Status Update
        set_sess(c, 'staff')
        t0 = time.perf_counter()
        resp = c.post('/query/1/status', data={'status': 'In Progress'}, follow_redirects=False)
        d_status = (time.perf_counter() - t0) * 1000
        print(f"6. Staff Status Update:       Status={resp.status_code} | Duration={d_status:.2f}ms | (<1s: {d_status < 1000})")

        # 7. Post Message
        set_sess(c, 'student')
        t0 = time.perf_counter()
        resp = c.post('/query/1/message', data={'message': 'Thank you for following up!'}, follow_redirects=False)
        d_msg = (time.perf_counter() - t0) * 1000
        print(f"7. Student Post Message:      Status={resp.status_code} | Duration={d_msg:.2f}ms | (<1s: {d_msg < 1000})")

        # 8. HOD <-> Principal Chat Send & History
        set_sess(c, 'principal')
        t0 = time.perf_counter()
        resp = c.post('/api/admin-hod-messages/3', json={'partner_id': 3, 'message': 'Principal response to HOD'}, follow_redirects=False)
        d_chat_post = (time.perf_counter() - t0) * 1000
        print(f"8. Principal -> HOD Chat:     Status={resp.status_code} | Duration={d_chat_post:.2f}ms | (<1s: {d_chat_post < 1000})")

        t0 = time.perf_counter()
        resp = c.get('/api/admin-hod-messages/3')
        d_chat_get = (time.perf_counter() - t0) * 1000
        print(f"9. Fetch HOD <-> Prin Chat:   Status={resp.status_code} | Duration={d_chat_get:.2f}ms | (<1s: {d_chat_get < 1000})")

if __name__ == '__main__':
    verify_single_user_experience()
