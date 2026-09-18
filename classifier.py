import re
import difflib
from collections import Counter

# =======================================================================
# COMPREHENSIVE DOMAIN TAXONOMY & SEMANTIC KNOWLEDGE BASE
# =======================================================================

TAXONOMY = {
    'Academics': {
        'topics': [
            'Faculty and teaching related issues',
            'Classes, lectures, and laboratory sessions',
            'Timetable, schedule conflicts, and period allocation',
            'Syllabus, curriculum coverage, and course progress',
            'Exams, internal assessments, midterms, and semester exams',
            'Question papers, blue prints, and model answer keys',
            'Marks, scoring, grades, CGPA, SGPA, and academic records',
            'Results, revaluation, recounting, supplementary, and backlogs',
            'Assignments, homework, mini projects, major projects, and capstone',
            'Lab practicals, viva voce, records, and manuals',
            'Attendance shortage, condonation, detention, and biometrics',
            'Study materials, textbooks, notes, and library learning resources',
            'Internships, academic calendar, tutorials, and remedial classes',
            'Training programs, CRT training, technical training, coding bootcamps, workshops, skill development, and certifications'
        ],
        'phrases': {
            # Multi-word high-confidence exact/semantic phrases (Weight: 3.5 - 5.0)
            'academic performance': 4.5,
            'academic calendar': 4.5,
            'internal exam': 4.2,
            'internal marks': 4.5,
            'semester exam': 4.2,
            'semester marks': 4.2,
            'mid exam': 4.2,
            'mid marks': 4.5,
            'midterm exam': 4.2,
            'question paper': 4.0,
            'mini project': 4.0,
            'major project': 4.0,
            'project review': 4.0,
            'project guide': 3.8,
            'study material': 4.0,
            'revaluation result': 4.5,
            'recounting result': 4.5,
            'supplementary exam': 4.2,
            'supply exam': 4.2,
            'hall ticket': 4.2,
            'admit card': 4.0,
            'grade card': 4.0,
            'marks memo': 4.2,
            'backlog exam': 4.2,
            'attendance shortage': 4.5,
            'attendance percentage': 4.2,
            'attendance correction': 4.2,
            'lab viva': 4.0,
            'lab record': 4.0,
            'lab practical': 4.0,
            'observation book': 3.8,
            'time table': 4.2,
            'class timetable': 4.5,
            'exam timetable': 4.5,
            'class schedule': 4.2,
            'lecture schedule': 4.2,
            'period clash': 4.2,
            'schedule clash': 4.2,
            'faculty absent': 4.0,
            'teacher not coming': 4.0,
            'class not conducted': 4.0,
            'syllabus incomplete': 4.2,
            'curriculum coverage': 4.0,
            'assignment submission': 4.0,
            'digital library': 3.5,
            'remedial class': 3.8,
            'training program': 4.5,
            'training programs': 4.5,
            'training session': 4.5,
            'training sessions': 4.5,
            'training classes': 4.5,
            'training class': 4.5,
            'training schedule': 4.5,
            'training related': 4.8,
            'technical training': 4.8,
            'skill training': 4.5,
            'skill development': 4.5,
            'crt training': 4.8,
            'crt classes': 4.5,
            'campus recruitment training': 4.8,
            'placement training': 4.8,
            'industrial training': 4.5,
            'internship training': 4.5,
            'summer training': 4.5,
            'coding training': 4.5,
            'coding bootcamp': 4.5,
            'python training': 4.5,
            'java training': 4.5,
            'technical workshop': 4.5,
            'hands on training': 4.5,
            'training batch': 4.2,
            'training timings': 4.2,
            'training trainer': 4.2,
            # Tanglish / Telugu academic phrases
            'marks raledhu': 4.5,
            'marks raaledu': 4.5,
            'marks thakkuva': 4.2,
            'internal marks upload': 4.5,
            'syllabus avvaledhu': 4.2,
            'classes jaragadam ledu': 4.2,
            'sir class ki': 4.0,
            'timetable marchandi': 4.2,
            'hall ticket ravatledu': 4.2,
            'attendance padaledhu': 4.2,
            'training eppudu': 4.5,
            'training classes eppudu': 4.5,
        },
        'keywords': [
            'exam', 'exams', 'examination', 'examinations', 'internal', 'semester', 'mid', 'midterm',
            'midterms', 'marks', 'mark', 'scoring', 'grade', 'grades', 'grading', 'cgpa', 'gpa',
            'sgpa', 'result', 'results', 'revaluation', 'recounting', 're-evaluation', 'supplementary',
            'supply', 'backlog', 'backlogs', 'arrear', 'arrears', 'detention', 'detained', 'condonation',
            'attendance', 'attend', 'biometric', 'class', 'classes', 'classroom', 'classrooms',
            'lecture', 'lectures', 'lecturing', 'subject', 'subjects', 'course', 'courses', 'syllabus',
            'curriculum', 'unit', 'units', 'assignment', 'assignments', 'homework', 'project',
            'projects', 'dissertation', 'thesis', 'capstone', 'lab', 'labs', 'laboratory', 'practical',
            'practicals', 'viva', 'tutorial', 'tutorials', 'faculty', 'professor', 'professors',
            'lecturer', 'lecturers', 'teacher', 'teachers', 'sir', 'madam', 'instructor', 'timetable',
            'timetables', 'schedule', 'schedules', 'scheduling', 'period', 'periods', 'session',
            'sessions', 'calendar', 'credit', 'credits', 'record', 'records', 'notes', 'textbook',
            'textbooks', 'library', 'internship', 'internships', 'learning', 'performance', 'quiz',
            'slip test', 'remedial', 'question bank', 'hallticket', 'hall ticket', 'admit card',
            'grade card', 'marksheet', 'memo', 'training', 'trainings', 'trainer', 'trainers',
            'crt', 'workshop', 'workshops', 'bootcamp', 'bootcamps'
        ],
        'roots': [
            'exam', 'mark', 'grad', 'cgpa', 'gpa', 'sgpa', 'revalu', 'recount', 'supple', 'backlog',
            'arrear', 'attend', 'lectur', 'syllab', 'curricul', 'assign', 'practic', 'viva', 'tutori',
            'facult', 'profess', 'timetabl', 'schedul', 'textbook', 'librar', 'internship', 'hallticket',
            'train', 'trainer', 'crt', 'bootcamp', 'workshop'
        ],
        'weights': {
            'timetable': 3.8, 'timetables': 3.8, 'schedule': 3.5, 'schedules': 3.5, 'scheduling': 3.5,
            'exam': 3.5, 'exams': 3.5, 'examination': 3.5, 'examinations': 3.5, 'internal': 3.2,
            'midterm': 3.5, 'midterms': 3.5, 'marks': 3.5, 'grades': 3.5, 'cgpa': 3.5, 'gpa': 3.5,
            'sgpa': 3.5, 'revaluation': 3.8, 'supplementary': 3.8, 'backlog': 3.8, 'arrears': 3.5,
            'attendance': 3.8, 'syllabus': 3.5, 'curriculum': 3.5, 'faculty': 3.2, 'professor': 3.2,
            'lecturer': 3.2, 'lecture': 2.8, 'subject': 2.8, 'course': 2.6, 'assignment': 3.2,
            'project': 3.0, 'lab': 3.0, 'laboratory': 3.0, 'practical': 3.0, 'viva': 3.2,
            'hallticket': 3.8, 'notes': 2.5, 'textbook': 2.8, 'library': 2.6, 'internship': 3.0,
            'training': 4.8, 'trainings': 4.8, 'trainer': 4.2, 'trainers': 4.2, 'crt': 4.8,
            'workshop': 4.2, 'workshops': 4.2, 'bootcamp': 4.2
        }
    },
    'Administrative': {
        'topics': [
            'Admissions, enrollment, allotment orders, counseling, and registrations',
            'Tuition fee, college fee, exam fee, bus fee, mess fee, challan, and receipts',
            'Fee payment failures, double payment, refund, dues, and no-dues clearance',
            'Bonafide certificates, study certificates, conduct certificates, and TC',
            'Transfer certificates, migration, custody, and original document verification',
            'Scholarships, JVD, e-Pass, NSP, financial aid, and fee reimbursements',
            'Student ID cards, bus passes, and student record corrections (name, dob, address)',
            'Hostel room allotment, hostel admissions, vacating, and caution deposit refund',
            'Transport, bus routes, bus stops, and route passes',
            'Leave applications, on-duty (OD) permissions, gate passes, and out passes',
            'Student ERP portal login, account locked, and password resets',
            'Theft, stolen belongings, thief complaints, missing property, and lost-and-found security reports'
        ],
        'phrases': {
            # Multi-word high-confidence exact/semantic phrases (Weight: 3.5 - 5.0)
            'theft complaint': 4.8,
            'theft incident': 4.8,
            'theft in campus': 4.8,
            'theft in hostel': 4.8,
            'theft in college': 4.8,
            'theft in lab': 4.8,
            'stolen item': 4.8,
            'item stolen': 4.8,
            'items stolen': 4.8,
            'phone stolen': 4.8,
            'mobile stolen': 4.8,
            'laptop stolen': 4.8,
            'wallet stolen': 4.8,
            'money stolen': 4.8,
            'bag stolen': 4.8,
            'bike stolen': 4.8,
            'cycle stolen': 4.8,
            'bicycle stolen': 4.8,
            'calculator stolen': 4.8,
            'watch stolen': 4.8,
            'caught stealing': 4.8,
            'theft case': 4.8,
            'lost property': 4.5,
            'missing property': 4.5,
            'administration office': 4.5,
            'administrative officer': 4.5,
            'ao office': 4.5,
            'tuition fee': 4.5,
            'hostel fee': 4.5,
            'bus fee': 4.5,
            'college fee': 4.5,
            'exam fee': 4.5,
            'fee payment': 4.5,
            'fee receipt': 4.5,
            'fee refund': 4.5,
            'fee challan': 4.5,
            'fee concession': 4.2,
            'fee reimbursement': 4.5,
            'no dues': 4.5,
            'no dues certificate': 4.5,
            'caution deposit': 4.5,
            'education loan': 4.5,
            'financial aid': 4.5,
            'national scholarship': 4.5,
            'jagananna vidya deevena': 4.8,
            'vidya deevena': 4.5,
            'vasathi deevena': 4.5,
            'bonafide certificate': 4.8,
            'study certificate': 4.8,
            'conduct certificate': 4.8,
            'transfer certificate': 4.8,
            'migration certificate': 4.8,
            'custody certificate': 4.8,
            'provisional certificate': 4.5,
            'consolidated marks memo': 4.5,
            'original certificates': 4.5,
            'document verification': 4.5,
            'documents verification': 4.5,
            'student id card': 4.5,
            'id card': 4.2,
            'identity card': 4.2,
            'duplicate id': 4.5,
            'bus pass': 4.5,
            'transport route': 4.2,
            'bus stop': 4.0,
            'name correction': 4.5,
            'address change': 4.5,
            'date of birth change': 4.5,
            'contact details': 4.2,
            'phone number update': 4.2,
            'password reset': 4.5,
            'account locked': 4.2,
            'portal login': 4.2,
            'erp login': 4.2,
            'allotment order': 4.5,
            'admission cancellation': 4.5,
            'seat cancellation': 4.5,
            'counseling rank': 4.2,
            'hostel allotment': 4.5,
            'room allocation': 4.5,
            'room shifting': 4.2,
            'hostel admission': 4.5,
            'on duty': 4.2,
            'duty leave': 4.2,
            'out pass': 4.5,
            'gate pass': 4.5,
            'medical leave': 4.2,
            # Tanglish / Telugu administrative phrases
            'fee kattanu': 4.5,
            'receipt raledhu': 4.5,
            'scholarship padaledhu': 4.5,
            'certificate kavali': 4.5,
            'bonafide kavali': 4.5,
            'bus pass renewal': 4.2,
            'id card poyindi': 4.2,
            'donga paddadu': 4.5,
            'donga dorikadu': 4.5,
            'phone poyindi': 4.5,
            'bag poyindi': 4.5,
            'donga': 4.5
        },
        'keywords': [
            'theft', 'stolen', 'thief', 'thieves', 'stealing', 'stole', 'robbery', 'robbed',
            'admission', 'admissions', 'enrollment', 'enrolment', 'allotment', 'counseling',
            'registration', 'application', 'certificate', 'certificates', 'bonafide', 'conduct',
            'transfer', 'migration', 'custody', 'provisional', 'transcript', 'transcripts',
            'verification', 'documents', 'document', 'fee', 'fees', 'tuition', 'challan', 'receipt',
            'receipts', 'payment', 'payments', 'refund', 'refunds', 'scholarship', 'scholarships',
            'reimbursement', 'epass', 'e-pass', 'jvd', 'nsp', 'loan', 'loans', 'transport', 'bus',
            'route', 'hostel', 'room', 'accommodation', 'mess', 'laundry', 'leave', 'permission',
            'outpass', 'gatepass', 'od', 'office', 'administration', 'administrative', 'grievance',
            'approval', 'cancellation', 'withdrawal', 'identity', 'student id', 'id card', 'smart card',
            'name correction', 'address change', 'dob', 'password', 'login', 'portal', 'erp', 'account',
            'credentials', 'dues', 'clearance', 'caution deposit', 'tc'
        ],
        'roots': [
            'theft', 'stolen', 'thief', 'steal', 'rob',
            'admiss', 'enrol', 'allot', 'counsel', 'regist', 'certific', 'bonafid', 'verif',
            'scholar', 'reimburs', 'tuition', 'challan', 'receipt', 'refund', 'transport',
            'accommodat', 'permiss', 'outpass', 'gatepass', 'administr', 'cancel', 'withdraw',
            'password', 'credential', 'clearanc'
        ],
        'weights': {
            'theft': 4.8, 'stolen': 4.8, 'thief': 4.5, 'thieves': 4.5, 'stealing': 4.2, 'robbery': 4.2,
            'bonafide': 4.5, 'scholarship': 4.2, 'fee': 3.8, 'fees': 3.8, 'tuition': 4.0,
            'challan': 4.0, 'receipt': 3.8, 'refund': 3.8, 'certificate': 3.8, 'certificates': 3.8,
            'admission': 3.8, 'admissions': 3.8, 'enrollment': 3.5, 'registration': 3.2,
            'tc': 4.0, 'transfer': 3.5, 'migration': 3.8, 'documents': 3.2, 'verification': 3.5,
            'leave': 3.2, 'permission': 3.2, 'bus': 3.0, 'transport': 3.2, 'hostel': 3.0,
            'accommodation': 3.2, 'office': 3.0, 'administration': 3.5, 'password': 3.5,
            'login': 3.0, 'portal': 3.0, 'account': 2.8, 'approval': 2.8, 'grievance': 3.0
        }
    },
    'Others': {
        'topics': [
            'Campus physical infrastructure, classrooms, furniture, desks, and doors repair',
            'Electrical, power outages, fans, lights, tube lights, and switches maintenance',
            'Plumbing, water leakage, taps, water coolers, washrooms, and restroom sanitation',
            'Cleanliness, hygiene, dustbins, campus sweeping, and waste disposal',
            'Campus Wi-Fi, LAN internet, network connectivity, and computer hardware issues',
            'Canteen food quality, cafeteria hygiene, mess food taste, and pricing',
            'Campus security, vehicle parking, helmet theft, gate safety, and CCTV surveillance',
            'Sports, games, sports kits, grounds, gym, cultural events, fests, and college clubs',
            'Placement drives, campus interviews, career job openings, and hackathons',
            'Anti-ragging, harassment, bullying, threats, disciplinary misconduct, and safety',
            'Lost & found belongings (wallets, phones, keys, bags, calculators)'
        ],
        'phrases': {
            # Multi-word high-confidence exact/semantic phrases (Weight: 3.5 - 5.0)
            'anti ragging': 5.0,
            'anti-ragging complaint': 5.0,
            'ragging complaint': 5.0,
            'ragging incident': 5.0,
            'senior harassment': 5.0,
            'junior harassment': 5.0,
            'physical assault': 5.0,
            'threatened by': 5.0,
            'sexual harassment': 5.0,
            'power cut': 4.5,
            'complete power cut': 4.8,
            'short circuit': 5.0,
            'electric shock': 5.0,
            'fire hazard': 5.0,
            'fan not working': 4.5,
            'light not working': 4.5,
            'tube light': 4.0,
            'water leakage': 4.5,
            'tap broken': 4.5,
            'tap leaking': 4.5,
            'water cooler': 4.5,
            'drinking water problem': 4.5,
            'washroom cleaning': 4.5,
            'toilet clean': 4.5,
            'restroom dirty': 4.5,
            'bad smell': 4.2,
            'campus cleanliness': 4.5,
            'dustbin missing': 4.0,
            'wi fi connection': 4.5,
            'wifi connection': 4.5,
            'internet not working': 4.5,
            'lan cable': 4.0,
            'slow internet': 4.2,
            'canteen food': 4.5,
            'food quality': 4.5,
            'mess food quality': 4.5,
            'stale food': 4.8,
            'dirty plates': 4.2,
            'bike parking': 4.2,
            'car parking': 4.2,
            'parking security': 4.5,
            'security guard': 4.0,
            'cctv camera': 4.0,
            'lost and found': 4.5,
            'lost item': 4.5,
            'found item': 4.2,
            'sports ground': 4.2,
            'cultural fest': 4.5,
            'annual day': 4.2,
            'tech fest': 4.5,
            'hackathon registration': 4.2,
            'placement drive': 4.5,
            'interview schedule': 4.2,
            'projector not working': 4.5,
            'bench broken': 4.2,
            'chair broken': 4.2,
            'ac not cooling': 4.5,
            # Tanglish / Telugu facilities & security phrases
            'water ravadam ledu': 4.5,
            'power ledu': 4.5,
            'current poyindi': 4.5,
            'fan tiragadam ledu': 4.5,
            'canteen food bagoledu': 4.5,
            'seniors ragging': 5.0,
            'item poyindi': 4.2
        },
        'keywords': [
            'maintenance', 'repair', 'broken', 'damage', 'furniture', 'bench', 'chair', 'desk',
            'door', 'window', 'infrastructure', 'electricity', 'electrical', 'power', 'fan',
            'light', 'bulb', 'switch', 'socket', 'plug', 'short circuit', 'ac', 'cooler', 'projector',
            'plumbing', 'water', 'leakage', 'leak', 'tap', 'washroom', 'restroom', 'toilet',
            'bathroom', 'sanitation', 'cleanliness', 'cleaning', 'clean', 'dirty', 'dustbin', 'garbage',
            'trash', 'hygiene', 'sweeping', 'smell', 'mosquito', 'internet', 'wifi', 'wi-fi',
            'lan', 'ethernet', 'network', 'speed', 'router', 'canteen', 'cafeteria', 'food',
            'mess food', 'snack', 'tea', 'parking', 'vehicle', 'bike', 'bicycle', 'car', 'security',
            'guard', 'cctv', 'camera', 'lost', 'found', 'wallet', 'purse', 'phone',
            'sports', 'game', 'cricket', 'football', 'volleyball', 'gym', 'ground', 'fest',
            'festival', 'cultural', 'event', 'club', 'association', 'hackathon', 'competition',
            'placement', 'career', 'job', 'interview', 'recruitment', 'tpo', 'alumni',
            'ragging', 'anti-ragging', 'antiragging', 'harassment', 'bullying', 'intimidation',
            'abuse', 'misconduct', 'threatening', 'fight', 'suggestion', 'feedback', 'inquiry'
        ],
        'roots': [
            'maintain', 'repair', 'electr', 'plumb', 'sanitat', 'clean', 'washroom', 'restroom',
            'toilet', 'canteen', 'park', 'secur', 'ragging', 'harass', 'bulli', 'intimidat',
            'hackathon', 'placement', 'recruit', 'infrastructur'
        ],
        'weights': {
            'ragging': 5.0, 'anti-ragging': 5.0, 'antiragging': 5.0, 'harassment': 4.8, 'bullying': 4.8,
            'wifi': 4.0, 'wi-fi': 4.0, 'internet': 4.0, 'cleanliness': 3.8, 'sanitation': 3.8,
            'washroom': 3.8, 'restroom': 3.8, 'toilet': 3.8, 'water': 3.2, 'leakage': 3.8,
            'electricity': 3.8, 'electrical': 3.8, 'power': 3.5, 'fan': 3.5, 'light': 3.2,
            'maintenance': 3.5, 'repair': 3.5, 'broken': 3.5, 'canteen': 3.8, 'food': 3.5,
            'parking': 3.8, 'security': 3.5, 'lost': 3.5, 'found': 3.2, 'sports': 3.5,
            'fest': 3.5, 'festival': 3.5, 'cultural': 3.5, 'hackathon': 3.8, 'placement': 3.8,
            'infrastructure': 3.5, 'projector': 3.8
        }
    }
}

# =======================================================================
# COMPOUND WORDS & NORMALIZATION MAP
# =======================================================================

COMPOUND_SPLITS = {
    'timetable': ('time', 'table'),
    'timetables': ('time', 'tables'),
    'midterm': ('mid', 'term'),
    'midterms': ('mid', 'terms'),
    'textbook': ('text', 'book'),
    'textbooks': ('text', 'books'),
    'classroom': ('class', 'room'),
    'classrooms': ('class', 'rooms'),
    'washroom': ('wash', 'room'),
    'washrooms': ('wash', 'rooms'),
    'restroom': ('rest', 'room'),
    'restrooms': ('rest', 'rooms'),
    'extracurricular': ('extra', 'curricular'),
    'bonafide': ('bona', 'fide'),
    'antiragging': ('anti', 'ragging'),
    'wifi': ('wi', 'fi'),
    'hallticket': ('hall', 'ticket'),
    'halltickets': ('hall', 'tickets'),
    'questionpaper': ('question', 'paper'),
    'studymaterial': ('study', 'material'),
    'academiccalendar': ('academic', 'calendar'),
    'miniproject': ('mini', 'project'),
    'tuitionfee': ('tuition', 'fee'),
    'hostelfee': ('hostel', 'fee'),
    'studentid': ('student', 'id'),
    'idcard': ('id', 'card'),
    'watercooler': ('water', 'cooler'),
    'powercut': ('power', 'cut'),
    'shortcircuit': ('short', 'circuit'),
    'crttraining': ('crt', 'training'),
    'placementtraining': ('placement', 'training'),
    'technicaltraining': ('technical', 'training'),
    'codingtraining': ('coding', 'training'),
    'skilltraining': ('skill', 'training')
}

# Synonyms & Stem Normalizer Dictionary
SYNONYM_MAP = {
    'trainings': 'training',
    'trainig': 'training',
    'traing': 'training',
    'timetabel': 'timetable',
    'time-table': 'timetable',
    'time_table': 'timetable',
    'schedul': 'schedule',
    'schedules': 'schedule',
    'scheduling': 'schedule',
    'scheduled': 'schedule',
    'attendence': 'attendance',
    'attandance': 'attendance',
    'attending': 'attendance',
    'syllubus': 'syllabus',
    'syllubas': 'syllabus',
    'curriculam': 'curriculum',
    'profesor': 'professor',
    'lecturer': 'faculty',
    'teacher': 'faculty',
    'asignments': 'assignment',
    'asignment': 'assignment',
    'submision': 'submission',
    'revalution': 'revaluation',
    're-evaluation': 'revaluation',
    'suplementary': 'supplementary',
    'certifcate': 'certificate',
    'certifikate': 'certificate',
    'bonofide': 'bonafide',
    'bona-fide': 'bonafide',
    'schollarship': 'scholarship',
    'scholorship': 'scholarship',
    'cleenliness': 'cleanliness',
    'cleanness': 'cleanliness',
    'electrisity': 'electricity',
    'maintanance': 'maintenance',
    'ragin': 'ragging',
    'harasment': 'harassment',
    'bully': 'bullying',
    'wi-fi': 'wifi',
    'ac': 'ac',
    'airconditioner': 'ac',
    'air-conditioner': 'ac'
}

def clean_text(text):
    """Normalize text by lowercasing, replacing punctuation/hyphens with spaces, and trimming."""
    if not text:
        return ""
    # Standardize Telugu/English text
    cleaned = text.lower()
    cleaned = re.sub(r'[\r\n\t]+', ' ', cleaned)
    cleaned = re.sub(r'[^\w\s\'-]', ' ', cleaned)
    return cleaned.strip()

def tokenize(text):
    """Splits cleaned text into alphanumeric tokens."""
    cleaned = clean_text(text)
    # Split on whitespace and hyphens
    tokens = [t for t in re.split(r'[\s\-_]+', cleaned) if t and len(t) > 1]
    return tokens

# =======================================================================
# CONTEXTUAL DISAMBIGUATION RULES
# =======================================================================

def apply_contextual_disambiguation(combined_text, scores):
    """
    Resolves category ambiguity for queries containing terms spanning multiple domains.
    For example:
    - "Exam fee" -> Administrative (Fee aspect takes precedence)
    - "Hostel room tap broken" -> Others (Facility repair takes precedence)
    - "Classroom fan not working" -> Others (Maintenance takes precedence)
    - "Lab PC mouse broken" -> Others (Hardware issue takes precedence)
    - "Exam schedule / timetable / Training" -> Academics
    - "Theft / Stolen item" -> Administrative (AO Desk)
    """
    text = combined_text.lower()
    
    # Rule 1: Fee / Payment context strongly indicates Administrative
    if re.search(r'\b(tuition fee|hostel fee|bus fee|exam fee|college fee|fee payment|fee receipt|fee refund|challan|due|scholarship|bonafide|transfer certificate|tc|migration|custody)\b', text):
        if not re.search(r'\b(ragging|harassment|broken|fan|leakage|water|toilet|washroom)\b', text):
            scores['Administrative'] = scores.get('Administrative', 0.0) + 6.0
            
    # Rule 2: Physical breakdowns in classroom/lab/hostel -> Others (Campus Maintenance)
    if re.search(r'\b(fan|light|tube light|switch|socket|ac|projector|broken|leakage|tap|washroom|toilet|restroom|cleanliness|wifi|internet|canteen|food quality|stale)\b', text):
        if re.search(r'\b(not working|broken|repair|clean|leak|power cut|short circuit|dirty|bad smell)\b', text):
            scores['Others'] = scores.get('Others', 0.0) + 6.0
            
    # Rule 3: Safety / Ragging / Bullying / Harassment -> strictly Others (Principal)
    if re.search(r'\b(ragging|anti-ragging|harassment|bullying|intimidation|threatened|abuse|physical assault)\b', text):
        scores['Others'] = scores.get('Others', 0.0) + 12.0
        
    # Rule 4: Timetable / Schedule / Exam / Marks / Syllabus / Attendance / Training -> Academics
    if re.search(r'\b(timetable|time table|schedule|syllabus|curriculum|internal marks|semester marks|cgpa|gpa|revaluation|attendance shortage|hall ticket|admit card|faculty absent|training|crt|crt training|technical training|coding training|placement training|skill development|skill training|workshop|bootcamp)\b', text):
        if not re.search(r'\b(fee|payment|challan|receipt|refund|scholarship|bonafide|broken|fan|tap|theft|stolen)\b', text):
            scores['Academics'] = scores.get('Academics', 0.0) + 8.0

    # Rule 5: Theft / Stolen items / Thief complaints -> Administrative (AO Desk)
    if re.search(r'\b(theft|stolen|thief|thieves|stealing|robbery|robbed|wallet stolen|phone stolen|laptop stolen|money stolen|bag stolen|cycle stolen|bike stolen|items stolen|stolen item)\b', text):
        scores['Administrative'] = scores.get('Administrative', 0.0) + 12.0

    return scores

# =======================================================================
# FUZZY & ROOT MATCHING HELPERS
# =======================================================================

def get_fuzzy_keyword_match(token, category_keywords, cutoff=0.82):
    """
    Performs fuzzy matching for a token against domain keywords to catch spelling typos.
    Returns matched keyword if similarity >= cutoff, else None.
    """
    if len(token) < 4:
        return None
    matches = difflib.get_close_matches(token, category_keywords, n=1, cutoff=cutoff)
    if matches:
        return matches[0]
    return None

def build_kw_pattern(kw):
    """
    Generates a robust regex pattern matching keyword with/without spaces and hyphens.
    Example: 'internal exam' matches 'internal exam', 'internalexam', 'internal-exam', 'internal exams'.
    """
    kw_clean = kw.lower().strip()
    
    parts = [p for p in re.split(r'[-\s]+', kw_clean) if p]
    if len(parts) == 1 and kw_clean in COMPOUND_SPLITS:
        parts = list(COMPOUND_SPLITS[kw_clean])
        
    if not parts:
        return r'\b' + re.escape(kw_clean) + r'\b'
        
    if len(parts) > 1:
        escaped_parts = []
        for i, p in enumerate(parts):
            if i == len(parts) - 1:
                # Plural/singular flexibility on final token
                if len(p) > 2 and not p.endswith(('s', 'es')):
                    escaped_parts.append(re.escape(p) + r'(?:s|es)?')
                elif p.endswith('s') and len(p) > 3:
                    singular = re.escape(p[:-1])
                    escaped_parts.append(r'(?:' + singular + r'|' + re.escape(p) + r')')
                else:
                    escaped_parts.append(re.escape(p))
            else:
                escaped_parts.append(re.escape(p))
        base_pattern = r'[-\s]*'.join(escaped_parts)
        return r'\b' + base_pattern + r'\b'
    else:
        single = parts[0]
        if len(single) > 2 and not single.endswith(('s', 'es')):
            return r'\b' + re.escape(single) + r'(?:s|es)?\b'
        elif single.endswith('s') and len(single) > 3:
            singular = re.escape(single[:-1])
            return r'\b(?:' + singular + r'|' + re.escape(single) + r')\b'
        else:
            return r'\b' + re.escape(single) + r'\b'

# =======================================================================
# INTELLIGENT MULTI-FACTOR DYNAMIC PRIORITY ENGINE
# =======================================================================

CRITICAL_SAFETY_PATTERNS = [
    r'\bragging\b', r'\bragged\b', r'\brag\b', r'\banti-ragging\b',
    r'\bharassment\b', r'\bharassed\b', r'\bsexual harassment\b',
    r'\bbullying\b', r'\bbullied\b', r'\bthreatened\b', r'\bphysical assault\b',
    r'\belectric shock\b', r'\bshort circuit\b', r'\bfire hazard\b', r'\bfire in\b',
    r'\bgas leak\b', r'\bflooding in hostel\b', r'\bbuilding collapse\b',
    r'\bfood poisoning\b', r'\bcontaminated water\b', r'\bvomiting mess food\b',
    r'\bmedical emergency\b', r'\blife threatening\b', r'\bsevere depression\b',
    r'\bintimidation\b', r'\babuse\b', r'\bmisconduct\b', r'\bthreatening\b'
]

CRITICAL_DEADLINE_PATTERNS = [
    r'\bexam starts in\b', r'\bexam is in 1 hour\b', r'\bexam in 1 hour\b',
    r'\bexam starting now\b', r'\bexam starts right now\b', r'\bexam today\b',
    r'\bongoing exam\b', r'\bonline exam interrupted\b', r'\bduring online exam\b',
    r'\bcannot enter exam hall\b', r'\bhall ticket error right before exam\b',
    r'\bexam portal blocked today\b', r'\blast day to submit fee today\b',
    r'\bdeadline in 1 hour\b', r'\btoday is the last date\b', r'\bcut-off today\b'
]

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

HIGH_IMPACT_PATTERNS = [
    r'\bexam tomorrow\b', r'\bexam is tomorrow\b', r'\bhall ticket missing\b',
    r'\bhall ticket not downloading\b', r'\bcannot download hall ticket\b',
    r'\badmit card error\b', r'\battendance detention\b', r'\bdetained list\b',
    r'\bfailed payment\b', r'\bmoney deducted receipt not\b', r'\bdouble payment\b',
    r'\bbonafide needed tomorrow\b', r'\bscholarship cut-off tomorrow\b',
    r'\bno water in hostel\b', r'\bcomplete power cut\b', r'\bwater contamination\b',
    r'\bprojector not working in class\b', r'\bportal login failed\b',
    r'\bbroken\b', r'\bsevere water leakage\b', r'\bleakage in hostel\b'
]

LOW_IMPACT_PATTERNS = [
    r'\bhow to\b', r'\bcan i know\b', r'\bprocedure for\b', r'\bwhat is the process\b',
    r'\btimings\b', r'\blibrary timings\b', r'\brules regarding\b', r'\bguidelines\b',
    r'\bjust a suggestion\b', r'\bfeedback regarding\b', r'\bgeneral query\b',
    r'\bminor\b', r'\bwhenever possible\b', r'\bno rush\b', r'\bgeneral information\b'
]

def detect_priority(text, title=""):
    """
    Determines priority (Critical, High, Medium, Low) based on life safety, deadlines,
    impact scope, and urgency cues.
    """
    combined = clean_text(f"{title} {text}")
    
    if re.search(r'\b(emergency|short circuit|fire hazard|gas leak)\b', combined):
        return "Critical"

    # 1. Absolute Safety / Harassment / Life Emergency -> Critical
    for p in CRITICAL_SAFETY_PATTERNS:
        if re.search(p, combined):
            return "Critical"
            
    # 2. Imminent Exam or Today Deadline -> Critical
    for p in CRITICAL_DEADLINE_PATTERNS:
        if re.search(p, combined):
            return "Critical"
            
    # 3. Scope of Outage / Impact
    has_campus_scope = any(re.search(p, combined) for p in CAMPUS_SCOPE_PATTERNS)
    has_dept_scope = any(re.search(p, combined) for p in DEPT_SCOPE_PATTERNS)
    has_personal_scope = any(re.search(p, combined) for p in PERSONAL_SCOPE_PATTERNS)
    
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
            
    if has_campus_scope or has_dept_scope:
        return "High"
        
    # 5. Low Impact / Informational
    for p in LOW_IMPACT_PATTERNS:
        if re.search(p, combined):
            return "Low"
            
    if 'urgent' in combined or 'important' in combined:
        return "High"
        
    return "Medium"

# =======================================================================
# CORE MULTI-LAYER NLP CLASSIFICATION ENGINE
# =======================================================================

def classify_query(description="", title=""):
    """
    Classifies a query into one of the 3 Primary Categories:
    1. Academics
    2. Administrative
    3. Others
    
    Employs a multi-layered NLP scoring architecture:
    - Layer 1: High-weight Exact & Space-Agnostic Multi-word Phrases (with 1.6x Title boost)
    - Layer 2: Keyword pattern matching (handling compound splits and inflections)
    - Layer 3: Stem & Root matching for morphological variations
    - Layer 4: Fuzzy Levenshtein matching to absorb typos and spelling variations
    - Layer 5: Contextual Disambiguation Rules to handle multi-domain terms
    """
    title_raw = title or ""
    desc_raw = description or ""
    title_text = clean_text(title_raw)
    desc_text = clean_text(desc_raw)
    combined_text = clean_text(f"{title_text} {desc_text}")
    
    if not combined_text:
        return {
            'department': 'Others',
            'category': 'Others',
            'priority': 'Medium',
            'confidence': 0.50,
            'needs_admin_review': False,
            'explanation': 'General campus query automatically assigned to Others Resolution Desk.'
        }
        
    scores = {'Academics': 0.0, 'Administrative': 0.0, 'Others': 0.0}
    matched_features = {'Academics': [], 'Administrative': [], 'Others': []}
    
    tokens = tokenize(combined_text)
    title_tokens = tokenize(title_text)
    
    # -------------------------------------------------------------
    # Layer 1: High-Weight Phrase Matching
    # -------------------------------------------------------------
    for cat, data in TAXONOMY.items():
        phrases = data.get('phrases', {})
        for phrase, phrase_weight in phrases.items():
            pattern = build_kw_pattern(phrase)
            
            title_hits = len(re.findall(pattern, title_text)) if title_text else 0
            desc_hits = len(re.findall(pattern, desc_text)) if desc_text else 0
            
            total_hits = title_hits + desc_hits
            if total_hits == 0 and combined_text:
                total_hits = len(re.findall(pattern, combined_text))
                
            if total_hits > 0:
                score_gain = (title_hits * phrase_weight * 1.6) + (desc_hits * phrase_weight)
                if score_gain == 0:
                    score_gain = total_hits * phrase_weight
                scores[cat] += score_gain
                matched_features[cat].append(phrase)

    # -------------------------------------------------------------
    # Layer 2: Keyword Pattern Matching (with Compound Word Resolution)
    # -------------------------------------------------------------
    for cat, data in TAXONOMY.items():
        keywords = data.get('keywords', [])
        # Sort by length descending so longer words match first
        sorted_kws = sorted(keywords, key=len, reverse=True)
        
        for kw in sorted_kws:
            kw_clean = kw.lower().strip()
            # If already matched in phrase layer, skip redundant single-word duplicate
            if any(kw_clean in m for m in matched_features[cat]):
                continue
                
            pattern = build_kw_pattern(kw_clean)
            
            title_hits = len(re.findall(pattern, title_text)) if title_text else 0
            desc_hits = len(re.findall(pattern, desc_text)) if desc_text else 0
            
            total_hits = title_hits + desc_hits
            if total_hits == 0 and combined_text:
                total_hits = len(re.findall(pattern, combined_text))
                
            if total_hits > 0:
                base_w = data['weights'].get(kw_clean, 2.2)
                score_gain = (title_hits * base_w * 1.6) + (desc_hits * base_w)
                if score_gain == 0:
                    score_gain = total_hits * base_w
                scores[cat] += score_gain
                matched_features[cat].append(kw_clean)

    # -------------------------------------------------------------
    # Layer 3: Morphological Root & Stem Matching
    # -------------------------------------------------------------
    for cat, data in TAXONOMY.items():
        roots = data.get('roots', [])
        for root in roots:
            # Check if any token starts with the root
            for t in tokens:
                if len(t) >= len(root) and t.startswith(root):
                    # Only add if root wasn't already matched as keyword
                    if not any(root in m for m in matched_features[cat]):
                        weight = 1.8
                        if t in title_tokens:
                            weight *= 1.6
                        scores[cat] += weight
                        matched_features[cat].append(t)
                        break

    # -------------------------------------------------------------
    # Layer 4: Fuzzy Typo & Spelling Variation Matcher
    # -------------------------------------------------------------
    # If a token did not match exactly, test closeness to domain keywords
    for t in tokens:
        if len(t) >= 4:
            # Check direct synonym map first
            if t in SYNONYM_MAP:
                canonical = SYNONYM_MAP[t]
                for cat, data in TAXONOMY.items():
                    if canonical in data['keywords'] or any(canonical in p for p in data.get('phrases', {})):
                        if canonical not in matched_features[cat]:
                            scores[cat] += 2.8
                            matched_features[cat].append(f"{t} ({canonical})")
            else:
                for cat, data in TAXONOMY.items():
                    fuzzy_match = get_fuzzy_keyword_match(t, data['keywords'], cutoff=0.82)
                    if fuzzy_match and not any(fuzzy_match in m for m in matched_features[cat]):
                        scores[cat] += 2.0
                        matched_features[cat].append(f"{t} (~{fuzzy_match})")

    # -------------------------------------------------------------
    # Layer 5: Contextual Disambiguation
    # -------------------------------------------------------------
    scores = apply_contextual_disambiguation(combined_text, scores)

    # -------------------------------------------------------------
    # Determine Final Classification & Confidence
    # -------------------------------------------------------------
    # Filter out categories with 0 score
    active_scores = {k: v for k, v in scores.items() if v > 0}
    
    if not active_scores:
        category = 'Others'
        department = 'Others'
        confidence = 0.50
        needs_admin_review = False
        explanation = "General campus query automatically assigned to Others Resolution Desk."
    else:
        sorted_cats = sorted(active_scores.items(), key=lambda item: item[1], reverse=True)
        best_cat, best_score = sorted_cats[0]
        
        total_score = sum(active_scores.values())
        # Confidence calibrated between 0.60 and 0.98
        confidence = min(0.98, max(0.60, round(best_score / (total_score + 0.5), 2)))
        
        category = best_cat
        department = best_cat
        needs_admin_review = bool(confidence < 0.40)
        
        features = matched_features.get(best_cat, [])
        if features:
            top_features = ", ".join(f"'{f}'" for f in features[:3])
            explanation = f"Matched key attributes ({top_features}) corresponding to {best_cat}."
        else:
            explanation = f"Identified contextual relevance corresponding to {best_cat}."

    priority = detect_priority(desc_raw, title_raw)
    
    return {
        'department': department,
        'category': category,
        'priority': priority,
        'confidence': confidence,
        'needs_admin_review': needs_admin_review,
        'explanation': explanation
    }



