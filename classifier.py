import re

# Comprehensive Taxonomy for the 3 Primary Pillars
TAXONOMY = {
    'Academics': {
        'topics': [
            'Faculty / teaching related issues',
            'Classes regular ga jaragakapovadam (Irregular class conduction)',
            'Timetable problems and schedule conflicts',
            'Syllabus complete kakapovadam (Incomplete syllabus)',
            'Exams / internal marks issues',
            'Assignments & projects related problems',
            'Lab / practical classes issues',
            'Study materials / notes availability',
            'Attendance discrepancies and shortage',
            'Doubts clarification / academic guidance',
            'Course registration / subject selection issues',
            'Results / revaluation related issues'
        ],
        'keywords': [
            # Teaching & Classes
            'faculty', 'professor', 'teaching', 'teacher', 'lecture', 'lecturer', 'faculty behavior',
            'teaching quality', 'class not conducted', 'classes not regular', 'irregular classes',
            'class cancelled', 'class cancellation', 'rescheduled class', 'no faculty', 'subject teacher',
            # Timetable & Syllabus
            'timetable', 'time table', 'schedule clash', 'class timing clash', 'overlapping periods',
            'syllabus', 'syllabus incomplete', 'portion pending', 'curriculum', 'units not covered',
            'syllabus completion',
            # Exams, Marks & Results
            'exam', 'examination', 'midterm', 'mid exams', 'internal marks', 'external marks', 'mid marks',
            'marks discrepancy', 'marks reduced', 'marks error', 'result', 'results', 'grade card',
            'sgpa', 'cgpa', 'revaluation', 'rechecking', 're-evaluation', 'supplementary', 'backlog',
            'supply exam', 'hall ticket', 'admit card', 'exam center', 'exam schedule',
            # Assignments, Projects & Labs
            'assignment', 'assignment submission', 'assignment deadline', 'project', 'mini project',
            'major project', 'project guide', 'project review', 'project evaluation', 'internship approval',
            'lab', 'laboratory', 'practical', 'lab equipment', 'lab experiment', 'lab records',
            'lab marks', 'lab exam', 'computer lab', 'chemistry lab', 'physics lab',
            # Materials, Attendance & Guidance
            'notes', 'study material', 'study materials', 'textbook', 'reference book', 'lecture slides',
            'attendance', 'attendance shortage', 'marked absent', 'condonation', 'detention',
            'doubt clarification', 'doubts', 'academic guidance', 'mentor', 'mentorship',
            'course registration', 'elective', 'subject selection', 'open elective', 'professional elective'
        ],
        'weights': {
            'hall ticket': 4.0, 'internal marks': 3.8, 'revaluation': 3.5, 'exam': 3.2,
            'attendance': 3.2, 'syllabus': 3.0, 'timetable': 3.0, 'faculty': 2.8,
            'assignment': 2.5, 'lab': 2.8, 'project': 2.8, 'marks': 3.0, 'result': 3.0
        }
    },
    'Administrative': {
        'topics': [
            'Admission / registration problems',
            'Fee payment / fee receipt issues',
            'Bonafide / certificates / documents',
            'ID card related issues',
            'Hostel / transport administration',
            'Scholarship processing (JVD, NSP, e-Pass)',
            'Leave permissions and On-Duty (OD) approvals',
            'Student records correction (Name, DOB, Phone)',
            'Department / office services',
            'Staff assignment / workload issues',
            'Approvals / permissions getting delayed',
            'Communication from administration'
        ],
        'keywords': [
            # Admissions & Registration
            'admission', 'allotment', 'seat allotment', 'counseling', 'document verification',
            'registration error', 'admission cancellation', 'enrollment', 'admission portal',
            # Fees & Financials
            'fee', 'fees', 'tuition fee', 'fee payment', 'payment failed', 'receipt', 'fee receipt',
            'challan', 'transaction', 'money deducted', 'refund', 'fee refund', 'fine', 'penalty', 'dues',
            # Certificates & Identity Cards
            'bonafide', 'bonafide certificate', 'study certificate', 'custody certificate', 'conduct certificate',
            'transfer certificate', 'tc', 'migration', 'migration certificate', 'id card', 'identity card',
            'id card correction', 'rfid', 'smart card', 'noc', 'no objection certificate',
            # Scholarships & Living Admin
            'scholarship', 'scholarship status', 'jvd', 'nsp', 'e-pass', 'biometric authentication',
            'scholarship verification', 'hostel administration', 'hostel fee', 'room allocation admin',
            'transport fee', 'bus pass', 'bus fee', 'bus route admin',
            # Approvals, Permissions & Records
            'leave permission', 'medical leave', 'on duty', 'od permission', 'gate pass', 'out pass',
            'approval delay', 'principal signature', 'hod signature', 'permission request',
            'record correction', 'name correction', 'spelling mistake', 'dob correction', 'phone update',
            'email update', 'address change', 'office clerk', 'admin circular', 'official notice'
        ],
        'weights': {
            'bonafide': 4.0, 'tc': 4.0, 'transfer certificate': 4.0, 'scholarship': 3.8,
            'fee': 3.2, 'fee receipt': 3.8, 'id card': 3.5, 'migration': 3.5, 'admission': 3.2,
            'refund': 3.0, 'leave permission': 2.8, 'record correction': 2.8
        }
    },
    'Others': {
        'topics': [
            'Campus maintenance (Furniture, doors, windows)',
            'Electrical / plumbing problems (Power, fans, water taps)',
            'Cleanliness / sanitation (Washrooms, dustbins, campus hygiene)',
            'Wi-Fi / internet issues (Campus network, bandwidth)',
            'Library facilities (Books, digital library, timings)',
            'Canteen / food issues (Mess food quality, hygiene)',
            'Security concerns (Guard posts, CCTV, campus safety)',
            'Parking problems (Bikes, cars, bicycle stand)',
            'Sports / extracurricular facilities (Ground, gym, equipment)',
            'Harassment / general complaints (Ragging, safety, bullying)',
            'Lost & found (Wallets, calculators, bags, keys)',
            'Suggestions / feedback',
            'Any issue that does not fit Academics or Administrative'
        ],
        'keywords': [
            # Infrastructure & Repairs
            'maintenance', 'campus maintenance', 'broken bench', 'desk', 'furniture', 'door broken',
            'window broken', 'projector', 'smart board', 'ac', 'air conditioner', 'ceiling',
            'electricity', 'electrical', 'power cut', 'blackout', 'switchboard', 'spark', 'fan not working',
            'light not working', 'tube light', 'plumbing', 'tap leak', 'water leakage', 'pipe burst',
            'no water', 'drainage', 'toilet', 'washroom', 'restroom', 'bathroom',
            # Sanitation & Health
            'cleanliness', 'hygiene', 'unhygienic', 'sanitation', 'dustbin', 'garbage', 'dirty washroom',
            # IT & Internet
            'wifi', 'wi-fi', 'internet', 'network', 'router', 'no connection', 'slow internet', 'lan cable',
            # Canteen & Mess
            'canteen', 'food', 'mess', 'mess food', 'canteen food', 'food quality', 'drinking water',
            'water cooler', 'spoiled food', 'ro plant',
            # Security, Safety & Harassment
            'security', 'security guard', 'cctv', 'campus safety', 'night safety', 'harassment',
            'ragging', 'bullying', 'misbehavior', 'threat', 'panic', 'emergency',
            # Amenities, Sports & General
            'parking', 'parking space', 'cycle stand', 'helmet lost', 'sports', 'ground', 'gym',
            'cricket kit', 'football kit', 'sports room', 'library', 'library books', 'digital library',
            'lost and found', 'lost item', 'lost wallet', 'lost id', 'found', 'suggestion', 'feedback', 'general'
        ],
        'weights': {
            'ragging': 5.0, 'harassment': 4.5, 'wifi': 3.5, 'wi-fi': 3.5, 'mess': 3.5,
            'washroom': 3.5, 'cleanliness': 3.0, 'water': 3.0, 'electricity': 3.0,
            'canteen': 3.0, 'library': 2.8, 'parking': 2.5, 'sports': 2.5
        }
    }
}

def clean_text(text):
    """Normalize text by lowercasing and trimming."""
    if not text:
        return ""
    return text.lower().strip()

# =======================================================================
# INTELLIGENT MULTI-FACTOR DYNAMIC PRIORITY ENGINE
# =======================================================================

# 1. Life Safety, Physical Security, Severe Harassment, Health & Hazard (Absolute Critical)
CRITICAL_SAFETY_PATTERNS = [
    r'\bragging\b', r'\bragged\b', r'\brag\b', r'\banti-ragging\b',
    r'\bharassment\b', r'\bharassed\b', r'\bsexual harassment\b',
    r'\bbullying\b', r'\bbullied\b', r'\bthreatened\b', r'\bphysical assault\b',
    r'\belectric shock\b', r'\bshort circuit\b', r'\bfire hazard\b', r'\bfire in\b',
    r'\bgas leak\b', r'\bflooding in hostel\b', r'\bbuilding collapse\b',
    r'\bfood poisoning\b', r'\bcontaminated water\b', r'\bvomiting mess food\b',
    r'\bmedical emergency\b', r'\blife threatening\b', r'\bsevere depression\b'
]

# 2. Critical Timelines (Exam in 1h, Ongoing Exam Block, Cut-off Today)
CRITICAL_DEADLINE_PATTERNS = [
    r'\bexam starts in\b', r'\bexam is in 1 hour\b', r'\bexam in 1 hour\b',
    r'\bexam starting now\b', r'\bexam starts right now\b', r'\bexam today\b',
    r'\bongoing exam\b', r'\bonline exam interrupted\b', r'\bduring online exam\b',
    r'\bcannot enter exam hall\b', r'\bhall ticket error right before exam\b',
    r'\bexam portal blocked today\b', r'\blast day to submit fee today\b',
    r'\bdeadline in 1 hour\b', r'\btoday is the last date\b', r'\bcut-off today\b'
]

# 3. High Scope / High Impact Outages (Campus-wide / Department-wide / Whole Hostel)
CAMPUS_SCOPE_PATTERNS = [
    r'\bentire college\b', r'\bwhole college\b', r'\bwhole campus\b', r'\bentire campus\b',
    r'\ball students\b', r'\bwhole university\b', r'\ball departments\b',
    r'\bcentral server down\b', r'\bmain portal crashed\b'
]

DEPT_SCOPE_PATTERNS = [
    r'\bentire department\b', r'\bwhole department\b', r'\bwhole branch\b',
    r'\bentire hostel\b', r'\bwhole hostel\b', r'\bentire block\b', r'\bwhole block\b',
    r'\bentire lab\b', r'\bwhole lab\b', r'\ball computers in lab\b',
    r'\ball systems in\b', r'\bentire classroom\b', r'\ball students of\b',
    r'\bentire class\b', r'\bwhole batch\b', r'\ball sections\b'
]

PERSONAL_SCOPE_PATTERNS = [
    r'\bmy laptop\b', r'\bmy phone\b', r'\bmy mobile\b', r'\bmy system\b',
    r'\bmy room tap\b', r'\bmy single\b', r'\bfor me\b', r'\bmy personal\b'
]

# 4. Academic & Administrative Urgency Indicators
HIGH_IMPACT_PATTERNS = [
    r'\bexam tomorrow\b', r'\bexam is tomorrow\b', r'\bhall ticket missing\b',
    r'\bhall ticket not downloading\b', r'\bcannot download hall ticket\b',
    r'\badmit card error\b', r'\battendance detention\b', r'\bdetained list\b',
    r'\bfailed payment\b', r'\bmoney deducted receipt not\b', r'\bdouble payment\b',
    r'\bbonafide needed tomorrow\b', r'\bscholarship cut-off tomorrow\b',
    r'\bno water in hostel\b', r'\bcomplete power cut\b', r'\bwater contamination\b',
    r'\bprojector not working in class\b', r'\bportal login failed\b'
]

LOW_IMPACT_PATTERNS = [
    r'\bhow to\b', r'\bcan i know\b', r'\bprocedure for\b', r'\bwhat is the process\b',
    r'\btimings\b', r'\blibrary timings\b', r'\brules regarding\b', r'\bguidelines\b',
    r'\bjust a suggestion\b', r'\bfeedback regarding\b', r'\bgeneral query\b',
    r'\bminor\b', r'\bwhenever possible\b', r'\bno rush\b', r'\bgeneral information\b'
]

def detect_priority(text, title=""):
    """
    Intelligently determines priority (Critical, High, Medium, Low) based on:
    - Life Safety, Security, Harassment, Health Risks
    - Timeline & Deadlines (e.g. ongoing exam vs general inquiry)
    - Impact Scope (Individual vs Classroom/Lab/Dept vs Campus-wide)
    - Service Outage Severity (Minor personal glitch vs Full department blackout)
    """
    combined = clean_text(f"{title} {text}")
    
    # 1. Absolute Safety / Security / Harassment / Life Emergency -> CRITICAL
    for p in CRITICAL_SAFETY_PATTERNS:
        if re.search(p, combined):
            return "Critical"
            
    # 2. Imminent Exam or Today Deadline Blocker -> CRITICAL
    for p in CRITICAL_DEADLINE_PATTERNS:
        if re.search(p, combined):
            return "Critical"
            
    # 3. Check Scope of Outage / Impact
    has_campus_scope = any(re.search(p, combined) for p in CAMPUS_SCOPE_PATTERNS)
    has_dept_scope = any(re.search(p, combined) for p in DEPT_SCOPE_PATTERNS)
    has_personal_scope = any(re.search(p, combined) for p in PERSONAL_SCOPE_PATTERNS)
    
    # Wi-Fi / Internet Outage contextual prioritization
    if re.search(r'\b(wifi|wi-fi|internet|network)\b', combined):
        if re.search(r'\b(exam|test|online test|placement test)\b', combined):
            return "Critical"
        if has_campus_scope:
            return "Critical"
        if has_dept_scope or re.search(r'\b(lab|library|entire|hostel block)\b', combined):
            return "High"
        if has_personal_scope:
            return "Medium"
        return "Medium"
        
    # Water / Electricity contextual prioritization
    if re.search(r'\b(water|drinking water|power|electricity|leakage)\b', combined):
        if re.search(r'\b(no drinking water|contaminated|spark|shock)\b', combined):
            return "Critical"
        if has_dept_scope or has_campus_scope or re.search(r'\b(hostel|entire block|building|washrooms)\b', combined):
            return "High"
        if has_personal_scope or re.search(r'\b(tap|minor drip|single fan)\b', combined):
            return "Medium"
        return "Medium"

    # 4. High Impact Academic & Administrative deadlines
    for p in HIGH_IMPACT_PATTERNS:
        if re.search(p, combined):
            return "High"
            
    # If entire department/hostel is impacted by any issue -> High
    if has_campus_scope or has_dept_scope:
        return "High"
        
    # 5. Low Impact / Informational / Minor
    for p in LOW_IMPACT_PATTERNS:
        if re.search(p, combined):
            return "Low"
            
    # If title has exclamation or urgent keyword without critical trigger
    if 'urgent' in combined or 'important' in combined:
        return "High"
        
    return "Medium"

def classify_query(description, title=""):
    """
    Classifies a query into one of the 3 Primary Categories:
    1. Academics
    2. Administrative
    3. Others
    And computes real-time intelligent dynamic priority (Critical, High, Medium, Low).
    """
    combined_raw = f"{title} {description}"
    combined_text = clean_text(combined_raw)
    
    scores = {}
    matched_keywords = {}
    
    for cat, data in TAXONOMY.items():
        cat_score = 0.0
        matched = []
        
        for kw in data['keywords']:
            pattern = r'\b' + re.escape(kw) + r'\b'
            matches = re.findall(pattern, combined_text)
            if matches:
                weight = data['weights'].get(kw, 1.5)
                cat_score += weight * len(matches)
                matched.append(kw)
                
        if cat_score > 0:
            scores[cat] = cat_score
            matched_keywords[cat] = matched

    if not scores:
        category = 'Others'
        department = 'Others'
        confidence = 0.45
        needs_admin_review = False
        explanation = "General campus query automatically assigned to the Others Resolution Desk."
    else:
        sorted_cats = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_cat, best_score = sorted_cats[0]
        
        total_score = sum(scores.values())
        confidence = min(0.98, max(0.60, round(best_score / (total_score + 1.0), 2)))
        
        category = best_cat
        department = best_cat
        needs_admin_review = False
        top_kws = ", ".join(f"'{k}'" for k in matched_keywords[best_cat][:3])
        explanation = f"Matched key attributes ({top_kws}) corresponding to {best_cat}."

    priority = detect_priority(description, title)
    
    return {
        'department': department,
        'category': category,
        'priority': priority,
        'confidence': confidence,
        'needs_admin_review': needs_admin_review,
        'explanation': explanation
    }
