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
    
    # Exhaustive Course & Branch / Specialization Mapping
    COURSES_BRANCHES = {
        'B.Tech': {
            'years': [1, 2, 3, 4],
            'branches': [
                'Computer Science & Engineering (CSE)',
                'CSE (AI & Machine Learning)',
                'CSE (Data Science)',
                'CSE (Cyber Security)',
                'Information Technology (IT)',
                'Electronics & Communication Engineering (ECE)',
                'Electrical & Electronics Engineering (EEE)',
                'Mechanical Engineering (ME)',
                'Civil Engineering (CE)',
                'Chemical Engineering',
                'Biotechnology Engineering',
                'Agricultural Engineering'
            ]
        },
        'Diploma': {
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
        'Degree': {
            'years': [1, 2, 3],
            'branches': [
                'Bachelor of Computer Applications (BCA)',
                'B.Sc (Computer Science)',
                'B.Sc (Data Science)',
                'B.Sc (Mathematics, Physics, Chemistry - MPC)',
                'B.Sc (Biotechnology / Microbiology)',
                'B.Com (General)',
                'B.Com (Computers / E-Commerce)',
                'Bachelor of Business Administration (BBA)',
                'B.A (Economics / Literature / History)'
            ]
        },
        'M.Tech': {
            'years': [1, 2],
            'branches': [
                'M.Tech (Computer Science & Engineering)',
                'M.Tech (VLSI & Embedded Systems)',
                'M.Tech (Power Electronics)',
                'M.Tech (CAD / CAM)',
                'M.Tech (Structural Engineering)',
                'M.Tech (Data Science & AI)'
            ]
        },
        'MCA': {
            'years': [1, 2],
            'branches': [
                'Master of Computer Applications (MCA - Regular)',
                'MCA (Data Analytics & Cloud Systems)'
            ]
        },
        'MBA': {
            'years': [1, 2],
            'branches': [
                'MBA (Finance Management)',
                'MBA (Marketing Management)',
                'MBA (Human Resource Management - HR)',
                'MBA (Business Analytics)',
                'MBA (Operations & Supply Chain)'
            ]
        }
    }
    
    # Priority Levels
    PRIORITIES = ['Low', 'Medium', 'High', 'Urgent']
    
    # Query Statuses
    STATUSES = ['New', 'Assigned', 'In Progress', 'Waiting for User', 'Resolved']
