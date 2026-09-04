import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dqm-secret-key-college-portal-2026-secure')
    DATABASE = os.path.join(BASE_DIR, 'database.db')
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max-limit
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx', 'txt', 'zip'}
    
    # Strictly only 3 Primary Categories / Departments throughout the whole website
    DEPARTMENTS = [
        'Academics',
        'Administrative',
        'Others'
    ]
    
    CATEGORIES = [
        'Academics',
        'Administrative',
        'Others'
    ]
    
    # Academic Levels & Program Hierarchies
    ACADEMIC_LEVELS = {
        'UG': ['B.Tech', 'Degree', 'B.Pharmacy'],
        'PG': ['M.Tech', 'MCA', 'MBA', 'M.Sc', 'M.Pharmacy'],
        'Diploma': ['Diploma (Polytechnic)', 'D.Pharmacy']
    }
    
    # Exhaustive Course & Branch / Specialization Mapping
    COURSES_BRANCHES = {
        'B.Tech': {
            'level': 'UG',
            'years': [1, 2, 3, 4],
            'branches': [
                'Computer Science & Engineering (CSE)',
                'Information Technology (IT)',
                'Artificial Intelligence & Data Science (AIDS)',
                'Artificial Intelligence & Machine Learning (AIML)',
                'Electronics & Communication Engineering (ECE)',
                'Civil Engineering (Civil)',
                'Electrical & Electronics Engineering (EEE)',
                'Mechanical Engineering (Mech)',
                'Chemical Engineering',
                'Biotechnology Engineering',
                'Agricultural Engineering',
                'Automobile Engineering',
                'Aerospace Engineering'
            ]
        },
        'Degree': {
            'level': 'UG',
            'years': [1, 2, 3],
            'branches': [
                'Bachelor of Computer Applications (BCA)',
                'B.Sc (Computer Science)',
                'B.Sc (Data Science)',
                'B.Sc (Mathematics, Physics, Chemistry - MPC)',
                'B.Sc (Biotechnology / Microbiology)',
                'B.Com (General)',
                'B.Com (Computer Applications)',
                'Bachelor of Business Administration (BBA)',
                'B.A (Economics / Literature / History)'
            ]
        },
        'B.Pharmacy': {
            'level': 'UG',
            'years': [1, 2, 3, 4],
            'branches': [
                'Bachelor of Pharmacy (B.Pharm - Core)',
                'Pharmaceutical Chemistry',
                'Pharmacology & Toxicology'
            ]
        },
        'M.Tech': {
            'level': 'PG',
            'years': [1, 2],
            'branches': [
                'M.Tech (Computer Science & Engineering)',
                'M.Tech (VLSI & Embedded Systems)',
                'M.Tech (Data Science & AI)',
                'M.Tech (Power Electronics & Drives)',
                'M.Tech (CAD / CAM Robotics)',
                'M.Tech (Structural Engineering)'
            ]
        },
        'MCA': {
            'level': 'PG',
            'years': [1, 2],
            'branches': [
                'Master of Computer Applications (MCA - Regular)',
                'MCA (Data Analytics & Cloud Systems)',
                'MCA (Artificial Intelligence)'
            ]
        },
        'MBA': {
            'level': 'PG',
            'years': [1, 2],
            'branches': [
                'MBA (Finance Management)',
                'MBA (Marketing Management)',
                'MBA (Human Resource Management - HR)',
                'MBA (Business Analytics)',
                'MBA (Operations & Supply Chain)',
                'MBA (Hospital & Healthcare Management)'
            ]
        },
        'M.Sc': {
            'level': 'PG',
            'years': [1, 2],
            'branches': [
                'M.Sc (Computer Science)',
                'M.Sc (Data Science & Analytics)',
                'M.Sc (Organic Chemistry)',
                'M.Sc (Applied Mathematics)',
                'M.Sc (Biotechnology)'
            ]
        },
        'M.Pharmacy': {
            'level': 'PG',
            'years': [1, 2],
            'branches': [
                'M.Pharm (Pharmaceutics)',
                'M.Pharm (Pharmacology)',
                'M.Pharm (Pharmaceutical Analysis)'
            ]
        },
        'Diploma (Polytechnic)': {
            'level': 'Diploma',
            'years': [1, 2, 3],
            'branches': [
                'Diploma in Computer Engineering (DCME)',
                'Diploma in Electronics & Communication (DECE)',
                'Diploma in Electrical & Electronics (DEEE)',
                'Diploma in Mechanical Engineering (DME)',
                'Diploma in Civil Engineering (DCE)',
                'Diploma in Automobile Engineering'
            ]
        },
        'D.Pharmacy': {
            'level': 'Diploma',
            'years': [1, 2],
            'branches': [
                'Diploma in Pharmacy (D.Pharm - 2 Year Core)'
            ]
        }
    }
    
    # Priority Levels
    PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
    
    # Query Statuses
    STATUSES = ['New', 'Assigned', 'In Progress', 'Waiting for User', 'Resolved']
