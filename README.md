# 🎓 Department Query Management Portal (DQM Portal)

> **"One Portal. Every Query. Faster Resolution."**  
> An intelligent, college-wide query management and support platform for students, faculty, department staff, and administration.

---

## 🌟 1. Project Overview

In traditional college ecosystems, students and faculty face friction whenever they encounter an academic, technical, financial, or administrative issue. They frequently do not know which specific department handles their problem (e.g. *Accounts vs. Scholarship cell*, *Examination branch vs. Academic section*, *IT helpdesk vs. Administration*).

The **Department Query Management Portal** solves this problem with **Zero-Click Smart Routing**:
- Users simply describe their problem in plain English.
- The system automatically parse536s the query text using an embedded NLP context engine.
- It identifies the **exact department**, categorizes the issue, determines its **priority level (Low, Medium, High, Urgent)**, and routes it directly to the responsible staff queue.
- Department staff receive instant real-time notifications with live 2-way query chat, status progression tracking, SLA response metrics, and 5-star resolution feedback.

---

## 🚀 2. Key Features

- 🤖 **Smart Automatic NLP Routing & Priority Engine (`classifier.py`)**:
  - Automatically identifies target department among 10 college departments without forcing manual selection.
  - Multi-tiered keyword & n-gram context scoring with confidence weighting.
  - Automatic urgency detection (e.g. *emergencies, exam starting in 1 hour, hall ticket blockers* are auto-flagged as `Urgent` or `High`).
  - Live as-you-type AI classification preview on the submission page.
  - Fallback to *General Administration* for edge-case queries requiring manual review.

- 👥 **Role-Based Workspaces & Access Control (RBAC)**:
  - **Student**: Post queries, track progress, real-time chat with staff, upload attachments, reopen queries, rate resolution.
  - **Faculty**: Academic/administrative query submission, fast-track routing, direct staff communication, feedback.
  - **Department Staff**: Dedicated department queue (e.g. *IT, Accounts, Examination, Hostel*), live urgent query banners, assign staff members, change status, internal private staff notes, SLA response timer tracking.
  - **Super Admin**: Executive cockpit, live unresolved/urgent monitor, user management, department SLA targets, and visual analytics.

- ⚡ **Real-Time Communication & Notifications (Flask-SocketIO + AJAX)**:
  - Bidirectional live chat on query pages.
  - Real-time department dashboard alerts when new high/urgent queries arrive.
  - Live typing indicator & status badges.
  - Interactive notification bell with unread badge counter.

- 📊 **SLA Tracking, Response Times & Analytics**:
  - Automatically records `created_at`, `first_response_at`, and `resolved_at`.
  - Calculates and displays average first response times (e.g. *"IT: 8 minutes", "Accounts: 15 minutes"*).
  - Post-resolution 5-star rating collection and feedback comments.
  - Interactive Chart.js analytics for department workload, category breakdown, status lifecycle, and satisfaction.

- 📎 **Secure File Attachments**:
  - Upload screenshots, fee receipts, hall tickets, PDFs, and documents safely.

- 🔒 **Production-Ready Security**:
  - Password hashing with `werkzeug.security` (PBKDF2/SHA256).
  - Session-based authentication with RBAC route protection.
  - SQLite foreign key constraints and transactional integrity.

---

## 🛠️ 3. Technologies Used

- **Backend**: Python 3, Flask 3.0.3, Werkzeug 3.0.3
- **Database**: SQLite3
- **Real-Time**: Flask-SocketIO 5.3.6, Python-EngineIO, Simple-WebSocket
- **Templates**: Jinja2
- **Frontend**: HTML5, CSS3 (Modern SaaS design system with CSS custom variables), Vanilla JavaScript (ES6+)
- **Visualizations**: Chart.js

---

## 💻 4. Installation & Setup

### Prerequisites:
- Python 3.8+ installed on your system.

### Step 1: Clone or Navigate to the Project Directory
```bash
cd "DQM Portal"
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

---

## 🏃 5. How to Run the Application

Run the application using:
```bash
python app.py
```

Once started, open your web browser and navigate to:
```
http://127.0.0.1:5000
```

> **Note**: On the very first launch, `app.py` automatically initializes `database.db` and populates realistic demo accounts, sample queries, chat conversations, and notifications.

---

## 🔑 6. Demo Login Credentials

The portal includes pre-seeded demo accounts. You can either type these credentials or click the **1-Click Demo Login** buttons on the `/login` page:

| Role | Email | Password | Dashboard Features |
| :--- | :--- | :--- | :--- |
| **👨‍🎓 Student** | `student@college.com` | `student123` | Post queries, track status, real-time chat, rate resolution |
| **👩‍🏫 Faculty** | `faculty@college.com` | `faculty123` | Faculty academic & facility query workflow, attachments |
| **🛠️ IT Staff** | `it@college.com` | `it123` | IT queue, Wi-Fi/Portal issues, assign staff, internal notes |
| **💳 Accounts Staff** | `accounts@college.com` | `accounts123` | Fee payment disputes, challans, refund management |
| **📝 Exam Staff** | `exam@college.com` | `exam123` | Hall tickets, marks discrepancy, semester results |
| **⚡ Super Admin** | `admin@college.com` | `admin123` | Full cockpit, user management, SLA targets, visual analytics |

---

## 📁 7. Project Structure

```
DQM Portal/
├── app.py                     # Main Flask Application & SocketIO entrypoint
├── config.py                  # App configuration & settings
├── database.py                # Database connection & helpers (SQLite3)
├── models.py                  # Schema definitions & DB initialization
├── classifier.py              # Smart NLP/keyword routing & priority detection engine
├── seed_data.py               # Preloaded demo accounts & realistic college queries
├── requirements.txt           # Python dependencies
├── test_suite.py              # Automated test suite
├── README.md                  # Complete documentation
│
├── uploads/                   # Secure storage for attachments
│
├── static/
│   ├── css/
│   │   └── style.css          # Modern SaaS CSS design system
│   └── js/
│       ├── main.js            # Core UI, notification dropdown, live preview, toasts
│       ├── chat.js            # Real-time WebSocket + AJAX chat engine
│       └── charts.js          # Interactive Chart.js analytics
│
└── templates/
    ├── base.html              # Core layout (navbar, sidebar, toasts, socket client)
    ├── index.html             # Landing page with live classifier sandbox & demo cards
    ├── login.html             # Auth login with 1-click Demo Account quick-fill tabs
    ├── register.html          # Registration for Students & Faculty
    ├── dashboard.html         # User Dashboard (Query stats, tracker, quick post)
    ├── submit_query.html      # "Post New Query" with live AI department prediction
    ├── query_details.html     # Real-time communication, timeline, staff actions & feedback
    ├── department_dashboard.html # Department Staff queue, urgent alerts & metrics
    ├── admin_dashboard.html   # Admin executive cockpit & system health
    ├── users.html             # Admin user management & role control
    ├── departments.html       # Admin department management & SLA overview
    ├── analytics.html         # Visual reports (Chart.js response times, department loads)
    ├── notifications.html     # Notification center
    └── profile.html           # User profile & account security
```

---

## 🧠 8. Explanation of Automatic Query Routing

The routing engine in `classifier.py` operates in three phases:

1. **Semantic Tokenization & Keyword Scoring**:
   - The query title and problem description are normalized and matched against domain-specific keyword dictionaries with differential weights (e.g. `bonafide: 4.0`, `hall ticket: 3.5`, `wifi: 3.5`, `tuition: 3.0`).
   - Keyword n-grams (phrases like *"water leak"*, *"payment failed"*, *"internal marks"*) prevent token misattribution.

2. **Department Assignment & Confidence Calculation**:
   - Scores across all 10 departments (*Accounts, Examination, Academic, IT, Administration, Student Welfare, Hostel, Library, Transport, General Administration*) are computed.
   - The highest scoring department is chosen. If confidence falls below the certainty threshold, it routes to `General Administration` and flags `needs_admin_review = 1`.

3. **Priority Detection**:
   - Evaluates urgency triggers (*"in one hour"*, *"emergency"*, *"immediately"*, *"short circuit"*, *"portal down"*, *"exam tomorrow"*) to automatically assign `Urgent`, `High`, `Medium`, or `Low`.

---

## 🔮 9. Future AI / NLP Improvements

For future institutional expansion:
1. **Transformer / LLM Fine-Tuning**: Integrate small local LLMs (e.g. Gemma / Llama 3) via Ollama or hosted Gemini API for zero-shot intent reasoning and automated draft replies.
2. **Multi-Lingual Support**: Add multilingual BERT embeddings to support queries submitted in regional languages.
3. **Automated FAQ Auto-Resolution**: When a student enters a common procedural question (e.g. *"What are the library timings?"* or *"Where is the fee challan counter?"*), suggest instant answers from an institutional knowledge base before filing the ticket.
4. **Voice & WhatsApp Integration**: Connect WhatsApp Business API or IVR voice queries into the centralized DQM routing queue.

---

## 🧪 10. Running Automated Tests

To run the automated verification test suite:
```bash
python test_suite.py
```
This tests:
- NLP routing accuracy for all sample queries.
- Priority detection edge cases.
- Real-time classification preview API.
- Authentication and session handling.
- Full query submission, chat messaging, and feedback lifecycle.
