import sys
import os
import time
import random
import statistics
import concurrent.futures
import psutil

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

WORKFLOWS = [
    'Home',
    'Login',
    'Student Dashboard',
    'Faculty Dashboard',
    'HOD Dashboard',
    'Principal Dashboard',
    'Department Dashboard',
    'Notifications Centre',
    'Query Details',
    'Take Query',
    'Assign Query',
    'Escalate Query',
    'Status Update',
    'Post Message',
    'HOD <-> Principal Comm',
    'Analytics',
    'Query Classification',
    'Logout'
]

def execute_action(action_name, idx):
    t0 = time.perf_counter()
    status_code = 0
    sqlite_err = False
    try:
        with app.test_client() as c:
            if action_name == 'Home':
                resp = c.get('/')
            elif action_name == 'Login':
                resp = c.post('/login', data={'email': 'student@college.com', 'password': 'student123'})
            elif action_name == 'Student Dashboard':
                set_sess(c, 'student')
                resp = c.get('/dashboard')
            elif action_name == 'Faculty Dashboard':
                set_sess(c, 'faculty')
                resp = c.get('/dashboard')
            elif action_name == 'HOD Dashboard':
                set_sess(c, 'hod')
                resp = c.get('/department-dashboard')
            elif action_name == 'Principal Dashboard':
                set_sess(c, 'principal')
                resp = c.get('/department-dashboard?dept=Others&view=received')
            elif action_name == 'Department Dashboard':
                set_sess(c, 'staff')
                resp = c.get('/department-dashboard')
            elif action_name == 'Notifications Centre':
                set_sess(c, 'student')
                resp = c.get('/notifications')
            elif action_name == 'Query Details':
                set_sess(c, 'student')
                resp = c.get('/query/1')
            elif action_name == 'Take Query':
                set_sess(c, 'principal')
                resp = c.post('/query/1/reassign', data={'action_type': 'take_query'})
            elif action_name == 'Assign Query':
                set_sess(c, 'hod')
                resp = c.post('/query/1/reassign', data={'action_type': 'reassign', 'assigned_staff_id': '4'})
            elif action_name == 'Escalate Query':
                set_sess(c, 'hod')
                resp = c.post('/query/1/reassign', data={'action_type': 'escalate_principal'})
            elif action_name == 'Status Update':
                set_sess(c, 'staff')
                resp = c.post('/query/1/status', data={'status': 'In Progress'})
            elif action_name == 'Post Message':
                set_sess(c, 'student')
                resp = c.post('/query/1/message', data={'message': f'Stress note {idx}'})
            elif action_name == 'HOD <-> Principal Comm':
                set_sess(c, 'hod')
                resp = c.post('/api/admin-hod-messages/3', json={'partner_id': 11, 'message': f'Direct note {idx}'})
            elif action_name == 'Analytics':
                set_sess(c, 'admin')
                resp = c.get('/api/analytics-data')
            elif action_name == 'Query Classification':
                resp = c.post('/api/classify-preview', json={'title': f'Hostel issue {idx}', 'description': 'The lab projector wifi connection in room 302 stopped responding'})
            elif action_name == 'Logout':
                resp = c.get('/logout')
            else:
                resp = c.get('/')
                
            status_code = resp.status_code
            if 'locked' in (resp.data.decode('utf-8', errors='ignore')).lower():
                sqlite_err = True
    except Exception as ex:
        if 'locked' in str(ex).lower() or 'busy' in str(ex).lower():
            sqlite_err = True
        status_code = 500
        
    dur = (time.perf_counter() - t0) * 1000
    return action_name, dur, status_code, sqlite_err

def run_concurrency_stage(concurrency, num_requests):
    print(f"\n================================================================================")
    print(f"BENCHMARK STAGE: {concurrency} CONCURRENT USERS ({num_requests} TOTAL REQUESTS)")
    print(f"================================================================================")
    
    cpu_before = psutil.cpu_percent(interval=0.1)
    ram_before = psutil.virtual_memory().percent
    
    # Generate balanced request distribution among 18 workflows
    actions = [WORKFLOWS[i % len(WORKFLOWS)] for i in range(num_requests)]
    random.shuffle(actions)
    
    t_start = time.perf_counter()
    results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(execute_action, act, i) for i, act in enumerate(actions)]
        for f in concurrent.futures.as_completed(futures):
            results.append(f.result())
            
    total_elapsed = time.perf_counter() - t_start
    cpu_after = psutil.cpu_percent(interval=0.1)
    ram_after = psutil.virtual_memory().percent
    
    all_latencies = [r[1] for r in results]
    all_latencies.sort()
    
    status_counts = {'2xx': 0, '3xx': 0, '4xx': 0, '5xx': 0}
    sqlite_locks = sum(1 for r in results if r[3])
    errors = 0
    
    by_workflow = {w: {'latencies': [], 'errors': 0, 'sqlite_err': 0} for w in WORKFLOWS}
    
    for act, dur, sc, sq in results:
        if 200 <= sc < 300:
            status_counts['2xx'] += 1
        elif 300 <= sc < 400:
            status_counts['3xx'] += 1
        elif 400 <= sc < 500:
            status_counts['4xx'] += 1
            errors += 1
        else:
            status_counts['5xx'] += 1
            errors += 1
            
        by_workflow[act]['latencies'].append(dur)
        if sc >= 400:
            by_workflow[act]['errors'] += 1
        if sq:
            by_workflow[act]['sqlite_err'] += 1
            
    rps = num_requests / total_elapsed if total_elapsed > 0 else 0
    avg_lat = statistics.mean(all_latencies)
    p50 = statistics.median(all_latencies)
    p95 = all_latencies[int(len(all_latencies) * 0.95)] if len(all_latencies) > 0 else 0
    p99 = all_latencies[int(len(all_latencies) * 0.99)] if len(all_latencies) > 0 else 0
    max_lat = max(all_latencies)
    err_rate = (errors / num_requests) * 100
    
    print(f"Total Requests:      {num_requests}")
    print(f"Elapsed Time:        {total_elapsed:.2f}s")
    print(f"Requests / Second:   {rps:.1f} RPS")
    print(f"Latency Avg:         {avg_lat:.1f} ms")
    print(f"Latency p50:         {p50:.1f} ms")
    print(f"Latency p95:         {p95:.1f} ms")
    print(f"Latency p99:         {p99:.1f} ms")
    print(f"Latency Max:         {max_lat:.1f} ms")
    print(f"Error Rate:          {err_rate:.2f}% ({errors} errors)")
    print(f"HTTP Status Codes:   2xx={status_counts['2xx']}, 3xx={status_counts['3xx']}, 4xx={status_counts['4xx']}, 5xx={status_counts['5xx']}")
    print(f"SQLite Locks/Busy:   {sqlite_locks}")
    print(f"CPU Utilization:     {cpu_after:.1f}% (before: {cpu_before:.1f}%)")
    print(f"RAM Utilization:     {ram_after:.1f}% (before: {ram_before:.1f}%)")
    
    print("\n--- Per-Workflow Latency Breakdown ---")
    print(f"{'Workflow':<25} | {'Reqs':<5} | {'p50':<8} | {'p95':<8} | {'p99':<8} | {'Max':<8} | {'Errs':<5}")
    print("-" * 75)
    for w in WORKFLOWS:
        w_lats = sorted(by_workflow[w]['latencies'])
        w_reqs = len(w_lats)
        w_errs = by_workflow[w]['errors']
        if w_reqs > 0:
            w_p50 = statistics.median(w_lats)
            w_p95 = w_lats[int(w_reqs * 0.95)] if w_reqs > 1 else w_lats[0]
            w_p99 = w_lats[int(w_reqs * 0.99)] if w_reqs > 1 else w_lats[0]
            w_max = max(w_lats)
            print(f"{w:<25} | {w_reqs:<5} | {w_p50:>6.1f}ms | {w_p95:>6.1f}ms | {w_p99:>6.1f}ms | {w_max:>6.1f}ms | {w_errs:<5}")

    return {
        'concurrency': concurrency,
        'requests': num_requests,
        'elapsed': total_elapsed,
        'rps': rps,
        'avg': avg_lat,
        'p50': p50,
        'p95': p95,
        'p99': p99,
        'max': max_lat,
        'errors': errors,
        'status_counts': status_counts,
        'sqlite_locks': sqlite_locks,
        'cpu': cpu_after,
        'ram': ram_after,
        'by_workflow': {w: {
            'reqs': len(by_workflow[w]['latencies']),
            'p50': statistics.median(sorted(by_workflow[w]['latencies'])) if by_workflow[w]['latencies'] else 0,
            'p95': sorted(by_workflow[w]['latencies'])[int(len(by_workflow[w]['latencies']) * 0.95)] if len(by_workflow[w]['latencies']) > 1 else 0,
            'p99': sorted(by_workflow[w]['latencies'])[int(len(by_workflow[w]['latencies']) * 0.99)] if len(by_workflow[w]['latencies']) > 1 else 0,
            'max': max(by_workflow[w]['latencies']) if by_workflow[w]['latencies'] else 0,
            'errors': by_workflow[w]['errors']
        } for w in WORKFLOWS}
    }

def main():
    stages = [
        (1, 18),
        (10, 50),
        (50, 150),
        (100, 300),
        (250, 500),
        (500, 1000),
        (1000, 2000)
    ]
    
    all_summary = []
    for c, n in stages:
        summary = run_concurrency_stage(c, n)
        all_summary.append(summary)
        time.sleep(0.5)
        
    with open('benchmark_staged_results.json', 'w') as f:
        json.dump(all_summary, f, indent=2)
    print("\nBenchmark completed and saved to benchmark_staged_results.json")

if __name__ == '__main__':
    main()
