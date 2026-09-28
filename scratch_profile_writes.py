import sys
import os
import time
import statistics
import concurrent.futures

sys.path.insert(0, r"c:\Users\jahna\OneDrive\Desktop\DQM Portal")
from app import app

USER_ACCOUNTS = {
    'admin': {'id': 12, 'role': 'admin', 'dept': 'Computer Science & Engineering (CSE)'},
    'principal': {'id': 11, 'role': 'principal', 'dept': 'Others'},
    'hod': {'id': 37, 'role': 'hod', 'dept': 'Computer Science & Engineering (CSE)', 'course': 'B.Tech'},
    'staff': {'id': 4, 'role': 'staff', 'dept': 'Computer Science & Engineering (CSE)'},
    'student': {'id': 1, 'role': 'student', 'dept': 'Computer Science & Engineering (CSE)'}
}

def set_client_session(client, role='admin'):
    user_info = USER_ACCOUNTS.get(role, USER_ACCOUNTS['admin'])
    with client.session_transaction() as sess:
        sess['user_id'] = user_info['id']
        sess['role'] = user_info['role']
        sess['department'] = user_info['dept']
        if 'course' in user_info:
            sess['course'] = user_info['course']
        sess['_fresh'] = True

def profile_single_action(action_name, concurrency=100, num_requests=200):
    latencies = []
    errors = 0
    
    def worker(i):
        t0 = time.perf_counter()
        try:
            with app.test_client() as client:
                if action_name == 'Post Message':
                    set_client_session(client, 'student')
                    resp = client.post('/query/1/message', data={'message': f'Test note {i}'})
                elif action_name == 'Status Update':
                    set_client_session(client, 'staff')
                    resp = client.post('/query/1/status', data={'status': 'In Progress'})
                elif action_name == 'Take Query':
                    set_client_session(client, 'principal')
                    resp = client.post('/query/1/reassign', data={'action_type': 'take_query'})
                elif action_name == 'Assign Query':
                    set_client_session(client, 'hod')
                    resp = client.post('/query/1/reassign', data={'action_type': 'reassign', 'assigned_staff_id': '4'})
                elif action_name == 'Escalate Query':
                    set_client_session(client, 'hod')
                    resp = client.post('/query/1/reassign', data={'action_type': 'escalate_principal'})
                elif action_name == 'HOD Msg Post':
                    set_client_session(client, 'hod')
                    resp = client.post('/api/admin-hod-messages/37', json={'partner_id': 11, 'message': f'HOD note {i}'})
                else:
                    set_client_session(client, 'student')
                    resp = client.get('/query/1')
                    
                dur = (time.perf_counter() - t0) * 1000
                if resp.status_code >= 400:
                    return dur, False
                return dur, True
        except Exception:
            dur = (time.perf_counter() - t0) * 1000
            return dur, False

    start_wall = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(worker, i) for i in range(num_requests)]
        for f in concurrent.futures.as_completed(futures):
            dur, ok = f.result()
            latencies.append(dur)
            if not ok:
                errors += 1
                
    total_time = time.perf_counter() - start_wall
    latencies.sort()
    avg = statistics.mean(latencies)
    p50 = statistics.median(latencies)
    p95 = latencies[int(len(latencies)*0.95)]
    p99 = latencies[int(len(latencies)*0.99)]
    max_l = max(latencies)
    
    print(f"{action_name:<20} | C={concurrency:3d} | Reqs: {num_requests:3d} in {total_time:5.2f}s | RPS: {num_requests/total_time:5.1f} | Avg: {avg:6.1f}ms | p50: {p50:6.1f}ms | p95: {p95:6.1f}ms | p99: {p99:6.1f}ms | Max: {max_l:7.1f}ms | Errs: {errors}")

if __name__ == '__main__':
    for c in [50, 100, 200]:
        print(f"\n==================== CONCURRENCY LEVEL: {c} ====================")
        for act in ['Status Update', 'Take Query', 'Post Message', 'HOD Msg Post']:
            profile_single_action(act, concurrency=c, num_requests=c*2)
