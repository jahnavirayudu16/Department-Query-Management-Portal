# 🎓 Department Query Management Portal (DQM Portal)

> **"One Portal. Every Query. Faster Resolution."**  
> An intelligent, college-wide query management and multi-tier institutional governance platform for students, faculty, department staff, HODs, AO, and college leadership.

---

## 🌟 1. Project Overview

In traditional college ecosystems, students and faculty face major communication hurdles when dealing with academic discrepancies, fee receipts, scholarships, lab system crashes, or campus maintenance. They frequently do not know which specific desk or degree department handles their problem (e.g. *B.Tech CSE vs. M.Tech CSE HOD*, *Administrative Officer vs. Office Staff*, *Examination branch vs. Academic lab*).

The **Department Query Management Portal (DQM Portal)** provides an automated, degree-aware, multi-tier institutional governance system:
- **Zero-Click Smart Routing**: Automatically routes queries into the 3 core college wings: **Academics**, **Administrative**, and **Others**.
- **Degree-Specific Scoping**: Academic queries are routed strictly by degree program — **B.Tech CSE** queries route to the B.Tech CSE HOD and teaching staff, while **M.Tech CSE** queries route strictly to the M.Tech CSE HOD.
- **Hierarchical Oversight & Analytics**:
  - **🏛️ Principal**: 3-Pillar Executive Analysis Cockpit (**Principal Desk**, **AO Administrative Desk**, **Academic HODs Desk** + Total Campus Overview).
  - **🏢 Administrative Officer (AO)**: 2-Pillar Analysis Cockpit (**AO Operations Desk** + **Academic HODs Status**) and Office Staff assignment desk.
  - **🎓 Heads of Department (HODs)**: Branch Visual Analytics (Academic Topics, Student Year Distribution, Status Lifecycle, Urgency) and Department Staff Resolvers Workload Table.
  - **💼 Office Staff**: Administrative resolvers handling fees, scholarships, and certificates assigned by AO.
  - **👩‍🏫 Department Teaching Staff**: Resolvers handling internal marks, lab crashes, exams, and attendance assigned by HOD.
  - **👨‍🎓 Students & Faculty**: Post issues, track real-time resolution timelines, engage in live 2-way chat, and submit 5-star feedback.

---

## 🚀 2. Core Features & Capabilities

### 🤖 1. Smart NLP & Degree-Aware Routing Engine (`classifier.py`)
- Automatically analyzes query titles and descriptions using an embedded NLP context engine with n-gram keyword weighting.
- Classifies queries into the 3 main wings:
  - **Academics**: Exams, internal marks, attendance, practical labs, syllabus, and project issues (scoped to UG/PG degree and department).
  - **Administrative**: Fee payments, receipts, scholarships (JVD/ePASS), bonafide/transfer certificates, ID cards, and permissions.
  - **Others (Principal / Campus Desk)**: Campus Wi-Fi, hostel food, cleanliness, sanitation, transport, library, and infrastructure.
- Automatic urgency detection flags time-critical blockers as `Critical` or `Urgent`.

### 👥 2. Multi-Tier Role-Based Access Control (RBAC)

| Role | Responsibility & Dashboard Scope |
| :--- | :--- |
| **👨‍🎓 Student** | Post queries, track progress, real-time chat with resolvers, upload attachments, reopen queries, rate resolution. |
| **👩‍🏫 Faculty** | Submit departmental/teaching queries, track status, and coordinate directly with resolvers. |
| **👩‍🏫 Department Staff** | Resolve academic queries assigned by HOD, update statuses, post internal private notes, and chat with students. |
| **💼 Office Staff** | Administrative resolvers handling fee payment issues, scholarship processing, and certificates assigned by AO. |
| **🎓 Head of Department (HOD)** | Degree-scoped queue (B.Tech vs M.Tech), assign staff, track staff workload, and view Branch Visual Analytics. |
| **🏢 Administrative Officer (AO)** | Oversee Administrative Wing, assign queries to Office Staff, and view **2-Pillar Analytics** (AO Desk + HODs). |
| **🏛️ Principal** | College executive oversight, manage Others desk queries, direct HOD communication, and **3-Pillar Analytics**. |
| **⚡ Central Administrator** | Manage users, configure departments & SLA response targets, monitor global campus matrix, and reset database. |

### 📊 3. Executive Analytics & Visual Cockpits (`/admin/analytics` & `/hod/analytics`)
- **🏛️ Principal Cockpit (3 Pillars)**:
  - **Pillar 1: Principal Desk Analysis**: Wi-Fi, Food, Cleanliness, Electrical, Transport topic breakdowns and priority distribution.
  - **Pillar 2: AO Administrative Analysis**: Fee receipts, scholarships, certificates distribution and student year breakdown.
  - **Pillar 3: Academic HODs Analysis**: B.Tech vs M.Tech vs MCA vs MBA degree distribution, academic topic chart, and HOD performance scorecard table.
  - **Pillar 4: Total Campus Overview**: Global department pie chart, student year distribution, and Department × Student Year Cross-Matrix.
- **🏢 AO Cockpit (2 Pillars)**:
  - **Pillar 1: AO Administrative Operations (My Desk)**: Real-time fee, scholarship, certificate lifecycle metrics.
  - **Pillar 2: Academic HODs Status**: Degree branch progress, resolution rates, and unassigned academic tickets.
- **🎓 HOD Branch Analytics Cockpit**:
  - **Branch KPI Summary Cards**: Total branch queries, resolved rate %, active investigations, unassigned backlog, and urgent issues.
  - **Academic Problem Topics Distribution (Doughnut Chart)**: Exams, Internal Marks, Labs, Attendance, Syllabus, Assignments.
  - **Student Year of Study Volume (Pie Chart)**: 1st Yr, 2nd Yr, 3rd Yr, 4th Yr, and Faculty submissions in that branch.
  - **Resolution Status Lifecycle & Urgency Levels**: Status stages and priority levels.
  - **Department Staff Resolvers Workload Table**: Workload, resolved counts, and direct assignment links for department faculty.
  - **College HODs Scorecard Tab**: Cross-branch comparison with other degree HODs across the college.

### ⚡ 4. Real-Time Communication & Timeline Tracking
- **Flask-SocketIO Live Chat**: 2-way instant messaging between query submitters and assigned resolvers.
- **🔒 Internal Staff Notes**: Resolvers and HODs can leave yellow internal notes hidden from students.
- **Live Online Presence**: Tracks active users and shows real-time online/offline badges.
- **Status Progression Timeline**: Visual step tracker (`New` → `In Progress` → `Resolved` → `Closed`).
- **Notification Center**: Real-time bell counter and desktop notifications for status updates and messages.

### ✍️ 5. Streamlined Registration & Authentication
- **AO & Office Staff Registration**: Only requires **Name, Official Email, and Password** (skips academic degree/branch dropdowns).
- **Academic Staff & HOD Registration**: Dynamically populates Academic Level (UG/PG/Diploma), Degree Course (B.Tech, M.Tech, MCA, MBA), and Department Branch.
- **1-Click Fast Demo Logins**: Instant login buttons on `/login` for all roles.

---

## 🛠️ 3. Technologies Used

- **Backend**: Python 3.8+, Flask 3.0.3, Werkzeug 3.0.3
- **Database**: SQLite3 with strict Foreign Key constraints and indexed lookups
- **Real-Time Messaging**: Flask-SocketIO 5.3.6, Python-EngineIO, Simple-WebSocket
- **Templates**: Jinja2 with custom datetime and relative time filters
- **Frontend Design**: Modern SaaS CSS design system with CSS custom properties (variables), responsive flex/grid layouts, and semantic HTML5
- **Visualizations**: Chart.js for responsive doughnut, pie, and bar charts
- **Testing**: Python `unittest` test suite

---

## 💻 4. Installation & Setup

### Prerequisites
- Python 3.8 or higher installed on your machine.

### Step 1: Navigate to the Project Directory
```bash
cd "DQM Portal"
```

### Step 2: Install Required Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Initialize / Seed Database
To populate the database with pristine demo accounts, degree-specific HODs, Office Staff, and sample queries:
```bash
python seed_data.py
```

### Step 4: Run the Application
```bash
python app.py
```

Open your web browser and navigate to:
```
http://127.0.0.1:5000
```

---

## 🔑 5. Preloaded Demo Accounts & Credentials

You can use the **1-Click Demo Login** buttons on the `/login` page or log in with any of these credentials:

| Role | Name | Email | Password | Access Scope |
| :--- | :--- | :--- | :--- | :--- |
| 🏛️ **Principal** | Dr. Alan Turing | `principal@college.com` | `principal123` | 3-Pillar Executive Cockpit, Received Queries (Others Desk), HOD Messaging |
| 🏢 **Admin Officer (AO)** | Mrs. Eleanor Wright | `ao@college.com` | `ao123` | 2-Pillar Analytics, Administrative Queue, Office Staff Assignment |
| 💼 **Office Staff** | Mr. Ramesh Kumar | `office-staff@college.com` | `staff123` | Administrative Resolver (Fees, Scholarships, Certificates) |
| 🎓 **B.Tech CSE HOD** | Dr. Grace Hopper | `cse-hod@college.com` | `hod123` | B.Tech CSE Queue, Staff Assignment, B.Tech CSE Branch Analytics |
| 🎓 **M.Tech CSE HOD** | Dr. Barbara Liskov | `mtech-cse-hod@college.com` | `hod123` | M.Tech CSE Queue, Staff Assignment, M.Tech CSE Branch Analytics |
| 🎓 **MCA HOD** | Dr. Tim Berners-Lee | `mca-hod@college.com` | `hod123` | MCA Department Queue & Analytics |
| 🎓 **MBA HOD** | Dr. Peter Drucker | `mba-hod@college.com` | `hod123` | MBA Department Queue & Analytics |
| 👩‍🏫 **B.Tech CSE Staff** | Prof. Linus Torvalds | `cse-staff@college.com` | `staff123` | B.Tech CSE Teaching Staff Resolver |
| 👩‍🏫 **M.Tech CSE Staff** | Prof. Donald Knuth | `mtech-cse-staff@college.com` | `staff123` | M.Tech CSE Teaching Staff Resolver |
| 👨‍🎓 **B.Tech Student** | Student (B.Tech CSE 3rd Yr) | `student@college.com` | `student123` | Student Workspace (UG - B.Tech CSE 3rd Year) |
| 👨‍🎓 **M.Tech Student** | Student (M.Tech CSE 1st Yr) | `mtech-student@college.com` | `student123` | Student Workspace (PG - M.Tech CSE 1st Year) |
| ⚡ **Central Admin** | Central Administrator | `admin@college.com` | `admin123` | Full Administrative Cockpit, Users Directory, System SLAs |

---

## 📁 6. Project Directory Structure

```
DQM Portal/
├── app.py                     # Main Flask application, SocketIO handlers & route controllers
├── config.py                  # System configuration, departments, courses & priorities
├── database.py                # Database connection utilities & query execution helpers
├── models.py                  # SQLite schema definitions & table initialization
├── classifier.py              # Smart NLP routing engine & priority classifier
├── seed_data.py               # Database seeder with realistic college accounts & sample queries
├── requirements.txt           # Python dependency specifications
├── test_suite.py              # Unit & integration test suite
├── README.md                  # Comprehensive project documentation
│
├── uploads/                   # Secure storage for query file attachments
│
├── static/
│   ├── css/
│   │   └── style.css          # Modern SaaS CSS design system
│   └── js/
│       ├── main.js            # Core UI, notifications, dynamic dropdowns, toast alerts
│       ├── chat.js            # Real-time WebSocket + AJAX chat engine
│       └── charts.js          # Chart.js visualizations for Principal, AO & HOD analytics
│
└── templates/
    ├── base.html              # Base layout (responsive sidebar, navbar, sockets, footer)
    ├── index.html             # Landing page with live classifier sandbox
    ├── login.html             # Role-based login with 1-click demo accounts
    ├── register.html          # Registration form (Academic vs Administrative role separation)
    ├── dashboard.html         # Student & Faculty workspace dashboard
    ├── submit_query.html      # Query submission form with live NLP classification preview
    ├── track_query.html       # Public ticket tracking timeline
    ├── query_details.html     # Ticket details, resolver chat, assignment desks, internal notes
    ├── department_dashboard.html # Department / HOD / AO / Staff resolution queue
    ├── admin_dashboard.html   # Central Admin executive cockpit
    ├── admin_communicate_hod.html # Principal & HOD real-time direct messaging channel
    ├── users.html             # User directory & account management
    ├── departments.html       # Department SLA management
    ├── analytics.html         # Executive 3-Pillar & 2-Pillar analytics & HOD branch analytics
    ├── notifications.html     # Notification center
    └── profile.html           # User profile & security settings
```

---

## 🧪 7. Running Automated Tests

To execute the automated unit and integration tests:
```bash
python test_suite.py
```

The test suite validates:
- **NLP Routing Accuracy**: Validates correct wing, category, and priority detection.
- **Degree-Specific Scoping**: Confirms B.Tech queries route exclusively to B.Tech HOD and M.Tech queries to M.Tech HOD.
- **AO & Office Staff Workflow**: Verifies AO queue visibility, Office Staff assignment, and 2-pillar data access.
- **HOD Branch Analytics**: Validates `/hod/analytics` access, branch-scoped metrics, topics, and staff workload API.
- **Real-Time Messaging**: Tests chat messaging and notifications.
- **RBAC Route Security**: Verifies role restrictions across student, staff, HOD, AO, and Principal routes.

---

## 📄 8. License

This project is open-source and available under the **MIT License**.
