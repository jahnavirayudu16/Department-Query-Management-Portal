import re

# 3 Primary Categories & Department Keywords Mapping
CATEGORY_KEYWORDS = {
    'Academics': {
        'keywords': [
            # Studies & Classes
            'attendance', 'attendance issue', 'attendance shortage', 'timetable', 'class schedule',
            'class cancellation', 'class rescheduling', 'rescheduling', 'cancelled class', 'sub change',
            'subject', 'subject allocation', 'course registration', 'subject change', 'elective',
            'elective subject', 'faculty allocation', 'faculty', 'professor', 'lecture', 'assignment',
            'assignment issue', 'assignment submission', 'assignment deadline', 'study materials',
            'notes availability', 'notes', 'curriculum', 'syllabus', 'academic calendar', 'academic leave',
            'academic permission', 'leave permission',
            # Exams & Marks
            'exam', 'examination', 'internal marks', 'external marks', 'marks', 'result', 'results',
            'grade', 'cgpa', 'gpa', 'exam schedule', 'exam registration', 'hall ticket', 'admit card',
            'exam center', 'revaluation', 'rechecking', 'supplementary exam', 'supplementary', 'supply',
            'backlog', 'backlog subject', 'backlogs', 'midterm', 'mid sem', 'end sem',
            # Labs, Projects & Academic Events
            'lab session', 'lab', 'laboratory', 'lab equipment', 'project guidance', 'mini project',
            'major project', 'project evaluation', 'project review', 'internship approval',
            'seminar', 'workshop', 'workshops', 'academic event', 'placement training', 'academic training'
        ],
        'weights': {
            'attendance': 3.5, 'hall ticket': 3.5, 'internal marks': 3.5, 'marks': 3.0,
            'exam': 3.0, 'revaluation': 3.0, 'backlog': 3.0, 'result': 2.5, 'assignment': 2.5,
            'syllabus': 2.5, 'timetable': 2.5, 'lab': 2.5, 'project': 2.5, 'elective': 2.5
        }
    },
    'Administrative': {
        'keywords': [
            # Fees & Finance
            'fee', 'fees', 'fee payment', 'payment', 'tuition', 'tuition fee', 'fee receipt',
            'receipt', 'refund', 'fee refund', 'fine', 'penalty', 'dues', 'challan', 'transaction',
            'scholarship', 'scholarship amount', 'scholarship document', 'government scheme',
            'bank details', 'bank update',
            # Certificates & Identity
            'bonafide', 'bonafide certificate', 'study certificate', 'custody certificate',
            'transfer certificate', 'tc', 'migration', 'migration certificate', 'id card',
            'id card correction', 'identity card', 'noc', 'no objection certificate',
            # Admissions, Records & Permissions
            'admission', 'admission issue', 'document verification', 'document submission',
            'documents', 'personal details correction', 'name correction', 'address correction',
            'phone update', 'email update', 'student records', 'permission request', 'approvals',
            'approval', 'event permission', 'internship permission', 'industrial visit permission',
            'iv permission', 'exam permission', 'hostel administration', 'transport administration',
            'college rules', 'college policies', 'office query', 'administrative'
        ],
        'weights': {
            'bonafide': 4.0, 'transfer certificate': 4.0, 'migration': 3.5, 'scholarship': 3.5,
            'fee': 3.0, 'payment': 3.0, 'receipt': 3.0, 'refund': 3.0, 'id card': 3.5,
            'admission': 3.0, 'noc': 3.5, 'verification': 2.5, 'penalty': 2.5
        }
    },
    'Others': {
        'keywords': [
            # Hostel & Mess
            'hostel', 'hostel issue', 'room allocation', 'room', 'hostel maintenance', 'mess',
            'food', 'mess food', 'canteen', 'food quality', 'drinking water', 'water leakage',
            'leakage', 'roommate', 'warden',
            # Campus Infrastructure & Utilities
            'electricity', 'power cut', 'wifi', 'wi-fi', 'internet', 'computer', 'system issue',
            'pc issue', 'lab pc', 'portal', 'website', 'app', 'login', 'password reset',
            'cleanliness', 'campus cleanliness', 'classroom maintenance', 'furniture', 'bench',
            'desk', 'washroom', 'bathroom', 'restroom', 'toilet', 'parking', 'ac', 'fan',
            'projector', 'smart classroom', 'plumbing', 'electrical',
            # Transport, Security & Sports
            'transport', 'bus', 'bus issue', 'bus route', 'bus timing', 'driver', 'bus pass',
            'security', 'security issue', 'lost and found', 'lost', 'found', 'campus safety',
            'sports', 'sports facilities', 'gym', 'cultural activities', 'student club',
            'club', 'campus event', 'fest', 'general suggestion', 'complaint', 'complaints',
            'feedback', 'general issue'
        ],
        'weights': {
            'hostel': 3.5, 'mess': 3.5, 'wifi': 3.5, 'wi-fi': 3.5, 'bus': 3.5, 'water': 3.0,
            'portal': 3.0, 'washroom': 3.5, 'cleanliness': 3.0, 'projector': 3.0, 'parking': 2.5
        }
    }
}

# Priority detection rules & tokens
URGENT_PATTERNS = [
    # Ragging, Harassment, Safety & Life Emergencies
    r'\bragging\b', r'\bragged\b', r'\brag\b', r'\bharassment\b', r'\bharassed\b',
    r'\bbullying\b', r'\bbullied\b', r'\bthreatened\b', r'\babuse\b', r'\banti-ragging\b',
    r'\banti ragging\b', r'\bmental distress\b', r'\bpanic\b', r'\bemergency\b',
    r'\blife threatening\b', r'\bmedical emergency\b', r'\bfire\b', r'\belectric shock\b',
    r'\bshort circuit\b', r'\bgas leak\b', r'\bflooding\b', r'\blockout\b',
    
    # Critical Time-Sensitive Exam & Hall Ticket Blocks
    r'\bhall ticket not downloading\b', r'\bhall ticket error\b', r'\bcannot download hall ticket\b',
    r'\bhall ticket missing\b', r'\bexam today\b', r'\bexam starts in\b', r'\bstarts in 1 hour\b',
    r'\bin 1 hour\b', r'\bstarts in one hour\b', r'\btoday itself\b', r'\bright now\b',
    r'\bdeadline today\b', r'\blast day today\b', r'\bexam center entry\b', r'\burgent\b', r'\bcritical\b', r'\bimmediately\b'
]

HIGH_PRIORITY_PATTERNS = [
    # Exams, Results & Academic Deadlines
    r'\bexam tomorrow\b', r'\bexam is tomorrow\b', r'\bhall ticket\b', r'\badmit card\b',
    r'\bexam registration\b', r'\bsupplementary exam\b', r'\brevaluation deadline\b',
    r'\binternal marks\b', r'\bmarks discrepancy\b', r'\battendance shortage\b',
    r'\bdetention\b', r'\bcondonation\b', r'\bsemester results\b', r'\bresult correction\b',
    
    # Critical Infrastructure, IT & Living Outages
    r'\bnot working\b', r'\bportal is down\b', r'\bcannot login\b', r'\bcannot access\b',
    r'\bfailed transaction\b', r'\bmoney deducted\b', r'\bfee payment failed\b',
    r'\bwater leak\b', r'\bleakage\b', r'\bno water\b', r'\bpower cut\b', r'\bblackout\b',
    r'\bbroken\b', r'\bserver down\b', r'\bunable to open\b', r'\bdeadline tomorrow\b',
    r'\bsevere\b', r'\bcannot download\b', r'\bfood poisoning\b', r'\bspoiled food\b',
    r'\bdrinking water contaminated\b'
]

MEDIUM_PRIORITY_PATTERNS = [
    r'\bnot updated\b', r'\bpending\b', r'\bcorrection\b', r'\bdelay\b',
    r'\bdiscrepancy\b', r'\bstatus\b', r'\brenewal\b', r'\bapplied\b',
    r'\bwaiting for\b', r'\bnot credited\b', r'\bdeducted\b', r'\bsyllabus\b',
    r'\btimetable\b', r'\bbonafide\b', r'\bstudy certificate\b', r'\bbus route\b'
]

LOW_PRIORITY_PATTERNS = [
    r'\btimings\b', r'\btiming\b', r'\bprocedure\b', r'\bprocess\b',
    r'\bhow to\b', r'\bcan i know\b', r'\binformation\b', r'\bquery\b',
    r'\bwhat is\b', r'\bwhere can\b', r'\bguidelines\b', r'\brules\b',
    r'\bgeneral\b', r'\bdetails regarding\b', r'\bworking hours\b', r'\bgeneral query\b'
]

def clean_text(text):
    """Normalize text by lowercasing and trimming."""
    if not text:
        return ""
    return text.lower().strip()

def detect_priority(text, title=""):
    """Detects priority level (Urgent, High, Medium, Low)."""
    combined = clean_text(f"{title} {text}")
    
    for pattern in URGENT_PATTERNS:
        if re.search(pattern, combined):
            return "Urgent"
            
    for pattern in HIGH_PRIORITY_PATTERNS:
        if re.search(pattern, combined):
            return "High"
            
    for pattern in MEDIUM_PRIORITY_PATTERNS:
        if re.search(pattern, combined):
            return "Medium"
            
    for pattern in LOW_PRIORITY_PATTERNS:
        if re.search(pattern, combined):
            return "Low"
            
    if '!' in title or 'URGENT' in title or 'HELP' in title:
        return "High"
        
    return "Medium"

def classify_query(description, title=""):
    """
    Classifies a query into one of the 3 Primary Categories:
    1. Academics
    2. Administrative
    3. Others
    """
    combined_raw = f"{title} {description}"
    combined_text = clean_text(combined_raw)
    
    scores = {}
    matched_keywords = {}
    
    for cat, data in CATEGORY_KEYWORDS.items():
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

    # If no specific matches, default to 'Others'
    if not scores:
        category = 'Others'
        department = 'Others'
        confidence = 0.40
        needs_admin_review = False
        explanation = "General campus query automatically routed to the Others Department Desk."
    else:
        sorted_cats = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_cat, best_score = sorted_cats[0]
        
        total_score = sum(scores.values())
        confidence = min(0.98, max(0.60, round(best_score / (total_score + 1.0), 2)))
        
        category = best_cat
        department = best_cat
        needs_admin_review = False
        top_kws = ", ".join(f"'{k}'" for k in matched_keywords[best_cat][:3])
        explanation = f"Matched key terms ({top_kws}) relating directly to {best_cat}."

    priority = detect_priority(description, title)
    
    return {
        'department': department,
        'category': category,
        'priority': priority,
        'confidence': confidence,
        'needs_admin_review': needs_admin_review,
        'explanation': explanation
    }
