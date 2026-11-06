# Smart Notes Assistant — AI-Powered SaaS Platform
> *Your thoughts, intelligently organized.*

A production-grade, multi-user SaaS application featuring genuine machine learning text classification, vector-space search, confidence-based uncertainty detection, and an Apple-inspired productivity interface.

Developed for the AI Engineering Internship technical assessment.

---

## 1. Project Overview & Architecture

Smart Notes Assistant automatically organizes personal notes into four distinct domains—**Study**, **Money**, **Travel**, and **Shopping**—using a machine learning pipeline trained strictly on provided datasets. Notes outside the four target categories are flagged as **Uncertain** using probability calibration, preventing confident misclassification.

```text
smart-notes-assistant/
├── app/
│   ├── config.py                 # Pydantic environment configuration
│   ├── dependencies.py           # JWT cookie/header extraction & auth guards
│   ├── main.py                   # FastAPI application, CORS & static mounting
│   ├── database/
│   │   └── mongodb.py            # MongoDB Atlas manager with MongoMock fallback
│   ├── models/                   # Document structures
│   ├── schemas/                  # Pydantic v2 schemas (Auth, Note, User)
│   ├── routes/
│   │   ├── auth.py               # Authentication & session refresh endpoints
│   │   ├── classification.py     # Official POST /classify contract endpoint
│   │   ├── dashboard.py          # Real-time statistics & seeding endpoints
│   │   ├── notes.py              # User-isolated note CRUD operations
│   │   ├── search.py             # TF-IDF Cosine Similarity & Keyword search
│   │   └── users.py              # Profile management & account deletion
│   ├── services/
│   │   ├── authentication.py     # Argon2 password hashing & PyJWT tokens
│   │   ├── classifier.py         # Sub-second ML inference & uncertainty logic
│   │   ├── email.py              # SMTP email dispatcher with dev inbox
│   │   ├── note_service.py       # MongoDB CRUD with user ownership isolation
│   │   └── search.py             # TF-IDF & Keyword retrieval engine
│   └── static/                   # Premium Apple-inspired Frontend
│       ├── index.html            # Public landing & workspace SPA
│       ├── css/
│       │   ├── style.css         # Dark theme (#08090C) & glassmorphism
│       │   ├── auth.css          # Auth forms & strength meters
│       │   └── preloader.css     # 6-second cinematic preloader
│       └── js/
│           ├── app.js            # Coordinator, router & health probe
│           ├── auth.js           # Authentication & session handlers
│           └── notes.js          # Notes CRUD, live ML preview & search
├── data/
│   ├── train.csv                 # 156 labeled training examples
│   ├── validation.csv            # 50 held-out validation examples
│   ├── out_of_scope_examples.csv # 12 non-domain test notes
│   ├── starter_notes.json        # 12 official starter notes (N001-N012)
│   └── search_queries.json       # 15 benchmark retrieval queries
├── model/
│   └── classifier.joblib         # Serialized Scikit-learn ML pipeline
├── tests/
│   ├── conftest.py               # Pytest setup & sys.path configuration
│   ├── test_api.py               # Official contract & error input tests
│   ├── test_auth.py              # Registration, login, logout, verification
│   ├── test_classifier.py        # ML predictions & uncertainty detection
│   ├── test_database.py          # MongoDB persistence & index integrity
│   ├── test_search.py            # Keyword & TF-IDF Hit Rate @ 3 tests
│   └── test_security.py          # Cross-user isolation & auth guard tests
├── examples/
│   └── test_api.py               # Official assessment validation script
├── train.py                      # One-command reproducible model trainer
├── evaluate_search.py            # Search evaluation benchmark runner
├── evaluate_uncertainty.py       # Uncertainty threshold benchmark runner
├── requirements.txt              # Production Python dependencies
├── render.yaml                   # Infrastructure-as-code for Render
├── .env.example                  # Environment configuration template
├── README.md                     # Technical documentation
├── RESULTS.md                    # Empirical ML metrics & error analysis
└── AI_WORKFLOW.md                # AI engineering workflow & debugging log
```

---

## 2. Technology Stack

- **Backend:** Python 3.13, FastAPI, Pydantic v2, Uvicorn.
- **Database:** MongoDB Atlas (with automatic in-memory MongoMock fallback for offline dev & tests), PyMongo.
- **Authentication & Security:** Argon2 password hashing (`argon2-cffi`), JWT access tokens (`PyJWT`), secure HTTP-only cookies (`SameSite=Lax`), session refresh tokens.
- **Machine Learning:** Scikit-learn, Pandas, NumPy, TF-IDF Vectorizer, Logistic Regression, Joblib.
- **Search Retrieval:** TF-IDF Cosine Similarity and Token-Overlap Keyword Search.
- **Testing:** Pytest, FastAPI TestClient.
- **Frontend:** Vanilla HTML5, CSS3, ES6 JavaScript, Fetch API (Zero external heavyweight frameworks).
- **Deployment:** Render web service & MongoDB Atlas cluster.

---

## 3. Key Features

1. **6-Second Cinematic Preloader:**
   - 0.0–1.0s: Ambient glow, emergent particles, central neural symbol.
   - 1.0–2.0s: Light trails connecting intelligence core.
   - 2.0–3.0s: Brand typography fade-in: *"SMART NOTES ASSISTANT"*.
   - 3.0–4.0s: Product domain indicators (*Study*, *Money*, *Travel*, *Shopping*).
   - 4.0–5.0s: Circular progress & *"Preparing your workspace..."*.
   - 5.0–6.0s: Smooth transition into workspace.
   - Genuine status checking: Never fakes database connection status.
2. **Apple-Inspired Dark Design:**
   - Visual identity inspired by macOS and Apple Notes.
   - Primary: `#08090C`, Secondary: `#101116`, Cards: `#17191F`, Elevated: `#1D2028`.
   - Text: `#F5F5F7`, Secondary text: `#989AA3`. Soft electric blue and restrained violet accents.
3. **Multi-User Isolation & Security:**
   - All private notes strictly enforce `user_id` query constraints at the database level.
   - User A can never view, edit, search, or delete User B's notes.
4. **Starter Notes Idempotency:**
   - Users can load the 12 official starter notes (`data/starter_notes.json`, `N001`–`N012`) with one click.
   - Seeding multiple times never creates duplicates or overwrites existing records.
   - New user-created notes are sequentially assigned `N013`, `N014`, ..., never reusing `N001`–`N012`.
5. **Real-Time Classification Preview:**
   - Typing in the note editor triggers a debounced live ML classification preview showing the predicted category, confidence percentage, and uncertainty status.

---

## 4. Local Installation & Setup

### Prerequisites
- Python 3.10+ (Tested on Python 3.13.2)
- Git

### Installation Steps

1. **Clone repository:**
   ```bash
   git clone <repository-url>
   cd Annu_Intern
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables:**
   Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
   *Note: If `MONGODB_URI` is left blank, the application automatically uses an in-memory MongoMock database, enabling immediate local evaluation without external configuration!*

---

## 5. Machine Learning Training & Evaluation

Train the model and reproduce the metrics reported in `RESULTS.md`:

```bash
python train.py
```

### Training Output Summary:
- **Baseline Accuracy:** 0.6800 | **Macro-F1:** 0.7079
- **Improved Model Accuracy:** **0.8600** | **Macro-F1:** **0.8544**
- **Artifact:** Saved to `model/classifier.joblib`.

### Evaluate Uncertainty Thresholds:
```bash
python evaluate_uncertainty.py
```
- At the operational threshold ($\tau = 0.50$), **91.7%** (11/12) of out-of-scope non-domain notes are flagged as `uncertain: true`.

### Evaluate Search Retrieval:
```bash
python evaluate_search.py
```
- **Hit Rate @ 3:** **80.0%** (12/15 benchmark queries successfully retrieved in top 3).
- Compares Keyword vs TF-IDF search, clearly reporting failed queries due to vocabulary mismatch.

---

## 6. Running the Application

Start the local server with Uvicorn:

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- **Application UI:** [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Interactive Swagger API Docs:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **Health Endpoint:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 7. Automated Testing & Assessment Verification

### Official Assessment Smoke Test (`examples/test_api.py`)
While your backend is running on port 8000, run the official assessment test:
```bash
python examples/test_api.py --url http://127.0.0.1:8000/classify
```
**Expected Result:**
```text
PASS valid note 'Revise for my biology examination.' -> HTTP 200, {'category': 'Study', 'uncertain': False, 'confidence': 0.7371} (13 ms)
PASS valid note 'Check my bank balance.' -> HTTP 200, {'category': 'Money', 'uncertain': False, 'confidence': 0.5643} (3 ms)
PASS valid note 'Book a train to Pune.' -> HTTP 200, {'category': 'Travel', 'uncertain': False, 'confidence': 0.722} (2 ms)
PASS valid note 'Purchase a pair of shoes.' -> HTTP 200, {'category': 'Shopping', 'uncertain': False, 'confidence': 0.5479} (25 ms)
PASS valid note 'Move ₹2,000 into savings before the 1st.' -> HTTP 200, {'category': 'Money', 'uncertain': False, 'confidence': 0.5768} (2 ms)
PASS valid note 'Call grandma this weekend.' -> HTTP 200, {'category': 'Study', 'uncertain': True, 'confidence': 0.2861} (14 ms)
PASS whitespace text -> HTTP 422 (expected 4xx)
PASS empty text -> HTTP 422 (expected 4xx)
PASS missing text field -> HTTP 422 (expected 4xx)
PASS text is a number -> HTTP 422 (expected 4xx)
PASS text is null -> HTTP 422 (expected 4xx)
PASS malformed JSON -> HTTP 422 (expected 4xx)
PASS server still answers after invalid requests
PASS same note gives the same response twice

All format checks passed.
```

### Full Automated Pytest Suite
Run the 19 automated tests covering authentication, database persistence, classifier performance, search retrieval, and multi-user security isolation:
```bash
pytest -v tests/
```

---

## 8. Render Deployment Instructions

The application is pre-configured for zero-downtime deployment on Render:

1. Push your code to a public GitHub repository.
2. In Render Dashboard, click **New > Web Service** and connect your GitHub repository.
3. Select **Python** runtime.
4. Set Build Command:
   ```bash
   pip install -r requirements.txt && python train.py
   ```
5. Set Start Command:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
6. Add Environment Variables:
   - `MONGODB_URI`: Your MongoDB Atlas connection string.
   - `JWT_SECRET_KEY`: A secure 32+ character random string.
   - `ENVIRONMENT`: `production`
   - `COOKIE_SECURE`: `true`
7. Click **Create Web Service**. Render will build the model, start Uvicorn, and provide your public URL.

---

## 9. API Specification Summary

### POST `/classify` (Official Contract)
- **Request:** `{"text": "Confirm the Jaipur hotel booking."}`
- **Response:** `{"category": "Travel", "uncertain": false, "confidence": 0.784}`
- **Status:** 200 OK (or 422 on invalid/empty input).

### Note Management APIs (Authenticated)
- `POST /notes` — Create and auto-classify note.
- `GET /notes` — Retrieve user notes (optional `?category=Study`).
- `GET /notes/{note_id}` — Retrieve single note with ownership verification.
- `PUT /notes/{note_id}` — Update and re-classify note.
- `DELETE /notes/{note_id}` — Delete note with ownership verification.
- `POST /notes/seed` — Seed starter notes (`N001`–`N012`) idempotently.
- `GET /search?q=...&method=tfidf` — Retrieve ranked matching notes.
- `GET /stats` — Real-time personal workspace counts.

---

## 10. License
Developed strictly for educational and internship technical assessment purposes. All assessment datasets and testing harnesses are preserved as originally provided.

