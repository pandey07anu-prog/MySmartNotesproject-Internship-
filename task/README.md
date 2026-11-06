# Smart Notes Assistant

An intelligent, native Windows desktop application and standalone FastAPI classification service powered by a genuinely trained machine-learning model.

---

## Project Structure

```text
task/
|-- data/                                 # Assessment datasets (read-only)
|   |-- train.csv                         # 156 labeled training examples
|   |-- validation.csv                    # 50 labeled validation examples
|   |-- out_of_scope_examples.csv         # 12 out-of-scope non-domain notes
|   |-- starter_notes.json                # 12 starter notes (IDs N001-N012)
|   +-- search_queries.json               # 15 fixed benchmark search queries
|
|-- src/                                  # Source code modules
|   |-- __init__.py
|   |-- data_ingestion.py                 # Data loading, inspection & validation
|   |-- model_trainer.py                  # ML pipeline, training, evaluation & serialization
|   |-- uncertainty.py                    # Confidence-based uncertainty detection module
|   |-- notes_storage.py                  # Atomic, schema-validated JSON storage engine
|   |-- notes_manager.py                  # Notes CRUD, filtering, ID generation & ML integration
|   |-- search_engine.py                  # Keyword and TF-IDF Cosine Similarity search engine
|   |-- api.py                            # FastAPI REST service & input validation
|   +-- gui/                              # Native CustomTkinter desktop interface
|       |-- __init__.py
|       |-- app.py                        # Main window shell, sidebar, and view router
|       |-- theme.py                      # Dark/Light palettes, Segoe UI fonts, config persistence
|       |-- components.py                 # Stat cards, badges, note cards, modals, empty states
|       |-- api_client.py                 # Non-blocking threaded REST client
|       |-- backend_manager.py            # Local Uvicorn daemon lifecycle manager
|       +-- views/                        # Feature screens
|           |-- __init__.py
|           |-- dashboard.py              # Command center with dynamic metrics & distribution
|           |-- notes_view.py             # Notes library with grid/list, chips & sorting
|           |-- note_editor.py            # Intelligent modal with live ML preview & character counter
|           |-- search_view.py            # Dedicated TF-IDF & keyword search workspace
|           +-- settings_view.py          # Theme customizer & system diagnostics
|
|-- assets/                               # Desktop brand assets
|   |-- app_icon.ico                      # Windows application multi-resolution icon
|   +-- app_icon.png                      # High-resolution application logo
|
|-- scripts/                              # Reproducibility & verification scripts
|   |-- verify_model.py                   # Fresh-process artifact verification script
|   |-- verify_phase5_persistence.py      # 10-step lifecycle persistence verification script
|   |-- verify_phase7_live.py             # Phase 7 live Windows server & latency benchmark
|   +-- verify_gui_visual.py              # Phase 8 Windows visual verification & screenshot capture
|
|-- tests/                                # Automated test suite (pytest)
|   |-- __init__.py
|   |-- test_data_ingestion.py            # Phase 2 ingestion tests (9 tests)
|   |-- test_model.py                     # Phase 3 model & inference tests (7 tests)
|   |-- test_uncertainty.py               # Phase 4 uncertainty tests (31 tests)
|   |-- test_notes_storage.py             # Phase 5 storage & atomic write tests (13 tests)
|   |-- test_notes_manager.py             # Phase 5 CRUD & persistence tests (24 tests)
|   |-- test_search_engine.py             # Phase 6 search engine tests (16 tests)
|   |-- test_search_evaluation.py         # Phase 6 Hit Rate @ 3 benchmark tests (4 tests)
|   |-- test_api.py                       # Phase 7 FastAPI backend tests (18 tests)
|   +-- test_gui.py                       # Phase 8 GUI, API client & state tests (15 tests)
|
|-- models/                               # Serialized ML artifacts
|   |-- tfidf_vectorizer.joblib           # Fitted TfidfVectorizer
|   |-- notes_classifier.joblib           # Fitted LogisticRegression
|   +-- notes_pipeline.joblib             # Combined scikit-learn Pipeline
|
|-- results/                              # Reports and metric logs
|   |-- phase3_model_report.md            # Complete Phase 3 ML report
|   |-- phase4_uncertainty_report.md      # Complete Phase 4 Uncertainty report
|   |-- phase6_search_report.md           # Complete Phase 6 Search benchmark report
|   +-- screenshots/                      # Phase 8 genuine Windows application screenshots
|       |-- 01_dashboard_dark.png
|       |-- 02_all_notes_grid.png
|       |-- 03_all_notes_list.png
|       |-- 04_study_category.png
|       |-- 05_money_category.png
|       |-- 06_travel_category.png
|       |-- 07_shopping_category.png
|       |-- 08_search_results.png
|       |-- 09_note_editor_preview.png
|       |-- 10_settings_diagnostics.png
|       +-- 11_dashboard_light.png
|
|-- main.py                               # Desktop application launcher
|-- templates/                            # Assessment submission templates
|-- examples/                             # Candidate pack evaluation examples
|   +-- test_api.py                       # Evaluator smoke test script
|-- .venv/                                # Isolated Python 3.10 virtual environment
|-- requirements.txt                      # Dependencies (staged by phase)
|-- pytest.ini                            # Test configuration
|-- train.py                              # Single-command training & evaluation runner
|-- evaluate_uncertainty.py               # Single-command uncertainty evaluation runner
|-- evaluate_search.py                    # Single-command search benchmarking runner
+-- README.md                             # Technical documentation
```

---

## Setup & Environment Configuration

### 1. Prerequisites
- **OS:** Windows 10/11 (64-bit)
- **Python:** Python 3.10.11

### 2. Activate Virtual Environment
Open PowerShell inside the `task` root directory:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Phase Dependencies
```powershell
pip install -r requirements.txt
```

---

## Reproducible Execution Commands

### 1. Launch SMART NOTES Desktop Application (Primary Entrypoint)
Automatically verifies/starts the local FastAPI service and opens the native CustomTkinter desktop interface:
```powershell
python main.py
```

### 2. Run Desktop GUI Visual Verification & Screenshot Capture
Runs the automated verification suite across all 11 application views and records authentic high-resolution screenshots to `results/screenshots/`:
```powershell
python scripts/verify_gui_visual.py
```

### 3. Run Automated Tests
Executes the full test suite (Phase 2 data + Phase 3 ML + Phase 4 uncertainty + Phase 5 storage/manager + Phase 6 search + Phase 7 API + Phase 8 GUI/Client = 137 tests):
```powershell
pytest -v
```

### 4. Run Machine Learning Training & Evaluation
Fits baseline and improved models on `train.csv`, evaluates on `validation.csv`, selects final model, saves artifacts into `models/`, and writes the report to `results/phase3_model_report.md`:
```powershell
python train.py
```

### 5. Verify Saved Artifacts in a Separate Process
```powershell
python scripts/verify_model.py
```

### 6. Run Confidence-Based Uncertainty Evaluation
Evaluates thresholds (0.35, 0.40, 0.45) on validation and out-of-scope notes without retraining, prints comparison table, and generates `results/phase4_uncertainty_report.md`:
```powershell
python evaluate_uncertainty.py
```

### 7. Start FastAPI Backend Service (Standalone)
Launches the local, headless REST API server on `127.0.0.1:8000`:
```powershell
python -m uvicorn src.api:app --host 127.0.0.1 --port 8000
```

### 8. Run External Evaluator Smoke Test
Tests the live `POST /classify` endpoint against the candidate-pack test suite:
```powershell
python examples/test_api.py --url http://127.0.0.1:8000/classify
```

### 9. Run Phase 7 Live Windows Verification & Latency Benchmark
Starts a live Uvicorn instance, measures cold startup and warm latencies, verifies all HTTP endpoints, runs the external smoke test, and cleanly shuts down:
```powershell
python scripts/verify_phase7_live.py
```

### 10. Run Search Engine Retrieval Benchmark
Evaluates Keyword Search and TF-IDF Cosine Similarity Search across 15 benchmark queries (including 3 vocabulary-mismatched queries) against the 12 starter notes and writes the report to `results/phase6_search_report.md`:
```powershell
python evaluate_search.py
```

### 11. Run Dataset Ingestion & Integrity Check
```powershell
python src/data_ingestion.py
```

### 12. Run Phase 5 Persistence Verification Workflow
Executes the 10-step lifecycle test verifying starter-note loading, CRUD operations, atomic persistence, and non-reuse of deleted IDs across manager re-initializations:
```powershell
python scripts/verify_phase5_persistence.py
```

---

## Phase 5: Notes Management & Persistent Storage Architecture

Phase 5 establishes a robust, decoupled, and tested backend for notes persistence and management.

### 1. Architectural Layers

- **Storage Engine (`src/notes_storage.py`):**
  - Manages low-level read/write operations for `data/notes.json`.
  - **Atomic Writes:** Implements atomic file replacement via temporary files (`os.replace`) to ensure incomplete writes or crashes never corrupt stored notes.
  - **Data Integrity:** Rejects corrupted JSON or invalid schema structures without overwriting disk contents with an empty database or resetting counters.
  - **UTF-8 & Symbol Preservation:** Guarantees strict UTF-8 serialization preserving international and currency characters (e.g. `₹`).
  - **Deep-Copy Isolation:** Returns deep copies of data structures to prevent in-memory side effects.

- **Notes Manager (`src/notes_manager.py`):**
  - High-level business logic managing note lifecycles and ML classification.
  - **Persistent Monotonic ID Generation:** Sequential IDs (`N001` to `N012` for starter notes, `N013` onwards for user notes). Persisted via `next_id` counter and **never reuses deleted IDs**.
  - **Starter Notes Synchronization:** Idempotently loads `data/starter_notes.json` with conflict detection; leaves source files untouched.
  - **Full CRUD Support:** `add_note()`, `get_note()`, `get_all_notes()`, `filter_by_category()`, `update_note()`, and `delete_note()`.
  - **Input Validation:** Enforces non-empty, non-whitespace string requirements and a 1000-character upper limit without silent truncation.
  - **ML Pipeline Integration:** Integrates the trained `models/notes_pipeline.joblib` artifact loaded once upon initialization. Classifies notes into the 4 allowed categories (`Study`, `Money`, `Travel`, `Shopping`) and calculates uncertainty using the calibrated $\tau = 0.40$ threshold.

### 2. JSON Storage Schema (`data/notes.json`)

```json
{
  "version": 1,
  "next_id": 13,
  "notes": [
    {
      "id": "N001",
      "text": "My Python test is on Friday at 10 AM.",
      "category": "Study",
      "confidence": 0.8842,
      "uncertain": false,
      "created_at": "2026-11-04T06:00:00.000000+00:00",
      "updated_at": "2026-11-04T06:00:00.000000+00:00"
    }
  ]
}
```

---

## Phase 6: Search Engine Architecture & Benchmark Evaluation

Phase 6 implements and evaluates two distinct, decoupled search algorithms across all saved personal notes.

### 1. Search Implementations

- **Keyword-Based Search Baseline (`keyword`):**
  - Text normalization: Lowercasing, punctuation handling, and regex tokenization.
  - Query tokens filtered against standard English stopwords.
  - Scoring formula: $\text{Score} = \text{Coverage} + 0.5 \times \text{TF}_{\text{density}} + \text{Bonus}_{\text{exact}}$, where coverage is the fraction of query terms satisfied, TF density weights matching token frequency, and exact phrase match adds a bonus.
  - Zero-match filtering: Notes with score $\le 0.0$ are excluded. Ties broken deterministically by Note ID.

- **TF-IDF Cosine Similarity Search (`tfidf`):**
  - Dynamic `TfidfVectorizer` (with English stop-word filtering) fitted on the active notes collection.
  - Queries transformed into the identical TF-IDF space and evaluated via cosine similarity:
    $$\text{sim}(q, d) = \frac{q \cdot d}{\|q\|_2 \|d\|_2} \in [0.0, 1.0]$$
  - Clean zero-vector handling: queries with no in-vocabulary words return `[]`.
  - Filtered by non-meaningful score cutoff ($\text{sim} \le 1e-5$).
  - Ties broken deterministically by Note ID ascending.

- **NotesManager Integration:**
  - Integrated via `NotesManager.search_notes(query, method='tfidf', top_k=3)`.
  - Searches all saved notes (starter notes + user notes).
  - Dynamically reflects note additions, edits, and deletions immediately without stale cache artifacts.

### 2. Retrieval Benchmark (Hit Rate @ 3)

Evaluated across 15 fixed queries (`data/search_queries.json`) against the 12 starter notes (`data/starter_notes.json`):

| Search Method | Overall Hit Rate @ 3 | Ordinary Queries (12) | Vocabulary Mismatch (3) |
|---|:---:|:---:|:---:|
| **Keyword Search** | 12 / 15 (**80.0%**) | 12 / 12 (**100.0%**) | 0 / 3 (**0.0%**) |
| **TF-IDF Search (Selected)** | 12 / 15 (**80.0%**) | 12 / 12 (**100.0%**) | 0 / 3 (**0.0%**) |

- **Selected Default Search Engine:** **TF-IDF Cosine Similarity Search** (`method='tfidf'`).
- **Empirical Rationale:** While both methods achieve 100% on ordinary queries, TF-IDF effectively downweights common words via IDF, yielding fewer spurious ties and providing clean, normalized similarity scores in $[0.0, 1.0]$.
- **Known Limitation:** Neither lexical algorithm can bridge vocabulary mismatch (e.g., *"settle power utility invoice"* vs *"Pay electricity bill"*), achieving 0% on disjoint synonym queries without semantic embeddings.

---

## Phase 7: FastAPI Backend Engineering & Integration Architecture

Phase 7 implements a high-performance, strictly validated local REST service (`src/api.py`) bridging the future native Windows desktop application (Phase 8) to the trained ML model, persistence engine, and search retrieval systems.

### 1. Architectural Highlights

- **Headless Local Daemon:** Binds strictly to `127.0.0.1:8000`. Generates zero external network egress and requires no browser or web frontend.
- **Single-Load Lifespan Management:** Loads the scikit-learn classification pipeline (`models/notes_pipeline.joblib`) once upon application startup into `app.state.notes_manager`. The model is reused across all requests with zero disk reloading overhead.
- **Process-Local Concurrency Control:** Write mutations (`POST /notes`, `PUT /notes/{id}`, `DELETE /notes/{id}`, `POST /notes/load-starter`) are synchronized via `asyncio.Lock()`, guaranteeing storage consistency across concurrent requests.
- **Strict Pydantic Input Validation:** Enforces strict string typing (`StrictStr`), rejecting integers, floats, booleans, lists, and dicts with `422 Unprocessable Content`. Enforces 1–1000 character boundaries and rejects empty or whitespace-only strings.
- **Error Masking & Information Hiding:** Custom Starlette/FastAPI exception handlers catch all internal errors and format clean JSON messages. Stack traces, file paths, and environment internals are never leaked.
- **Full UTF-8 & Currency Preservation:** Flawlessly processes Unicode text, including the Indian Rupee symbol (`₹`).

### 2. Complete REST Endpoint Reference

| Method | Endpoint | Query / Body Params | Status Code | Description |
|---|---|---|:---:|---|
| `GET` | `/health` | None | `200` / `503` | Readiness check; verifies model and storage subsystems. |
| `POST` | `/classify` | `{"text": str}` | `200` / `422` | Decoupled ML classification returning `category`, `confidence`, `uncertain`. |
| `GET` | `/notes` | `category` (optional) | `200` / `422` | Lists all notes; filters by category if provided. |
| `POST` | `/notes` | `{"text": str}` | `201` / `422` | Adds note, triggers ML classification, assigns persistent ID (`N013+`). |
| `GET` | `/notes/{id}` | Path: `id` | `200` / `404` | Retrieves single note by ID. |
| `PUT` | `/notes/{id}` | Path: `id`, Body: `{"text": str}` | `200` / `404` / `422` | Updates note text and re-runs ML classification. |
| `DELETE` | `/notes/{id}` | Path: `id` | `200` / `404` | Deletes note; retired ID is never recycled. |
| `GET` | `/search` | `query`, `method` (`tfidf`\|`keyword`), `top_k` | `200` / `422` | Searches saved notes using TF-IDF cosine similarity or keyword matching. |
| `POST` | `/notes/load-starter`| None | `200` / `409` | Idempotently loads starter notes `N001`–`N012`; returns 409 on conflict. |

### 3. External Smoke Test & Verification

The FastAPI service was verified against the official candidate pack smoke test script (`examples/test_api.py`):
```text
PASS valid note 'Revise for my biology examination.' -> HTTP 200, {'category': 'Study', 'uncertain': False, 'confidence': 0.7371} (19 ms)
PASS valid note 'Check my bank balance.' -> HTTP 200, {'category': 'Money', 'uncertain': False, 'confidence': 0.5643} (16 ms)
PASS valid note 'Book a train to Pune.' -> HTTP 200, {'category': 'Travel', 'uncertain': False, 'confidence': 0.722} (15 ms)
PASS valid note 'Purchase a pair of shoes.' -> HTTP 200, {'category': 'Shopping', 'uncertain': False, 'confidence': 0.5479} (19 ms)
PASS valid note 'Move ₹2,000 into savings before the 1st.' -> HTTP 200, {'category': 'Money', 'uncertain': False, 'confidence': 0.5768} (7 ms)
PASS valid note 'Call grandma this weekend.' -> HTTP 200, {'category': 'Study', 'uncertain': True, 'confidence': 0.2861} (5 ms)
PASS valid note 'Pay the rent. Pay the rent. Pa... (980 chars)' -> HTTP 200, {'category': 'Money', 'uncertain': False, 'confidence': 0.6875} (6 ms)
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

---

## Phase 8: Premium Native Windows Desktop Application Architecture

Phase 8 introduces **SMART NOTES**—a commercial-grade, native Windows desktop application built with Python 3.10 and **CustomTkinter**, integrating all machine-learning, uncertainty detection, atomic storage, and search capabilities developed in Phases 1–7.

### 1. Visual Identity & Design System

- **Brand Name:** SMART NOTES
- **Tagline:** *Think. Organize. Remember.*
- **Design Philosophy:** Minimalist, information-rich aesthetic inspired by modern AI productivity software (Notion, Linear).
- **Dual Palette (Dark & Light):**
  - **Dark Midnight Theme:** Main `#151625`, Sidebar `#191A2C`, Cards `#252940`, Primary Accent `#927FEA`, Text `#F6F5FB`, Borders `#353750`.
  - **Crisp Light Theme:** Main `#F5F4FA`, Sidebar `#FFFFFF`, Cards `#FFFFFF`, Primary Accent `#7966D8`, Text `#242438`, Borders `#E6E3F0`.
- **Category Colors:**
  - **Study:** `#A78BFA` (Soft Purple)
  - **Money:** `#6CCFA8` (Mint / Emerald)
  - **Travel:** `#78B9F5` (Sky Blue)
  - **Shopping:** `#F08F9A` (Rose / Coral)
- **Typography:** Segoe UI with consistent font hierarchy (headings, body, captions, monospace IDs).

### 2. Feature Workspaces & Application Views

1. **Dashboard Command Center (`src/gui/views/dashboard.py`):**
   - Time-aware greeting (`"Good morning / afternoon / evening"`) and current date.
   - 5 Dynamic Stat Cards: Total Notes, Study, Money, Travel, Shopping with category indicators and proportions.
   - Proportional Category Distribution Bar with interactive color-coded legend.
   - Recent Notes Stream with category badges, timestamps, and confidence/uncertainty indicators.
   - Quick Action buttons: `+ Add Note`, `Search`, `Load Starter Notes`.
2. **Notes Library Workspace (`src/gui/views/notes_view.py`):**
   - Interactive category filter chips (`All`, `Study`, `Money`, `Travel`, `Shopping`).
   - Dynamic real-time client-side keyword filtering.
   - Sorting options: `Newest first`, `Oldest first`, `Category A-Z`.
   - Grid / List layout switcher with responsive `NoteCard` widgets.
   - Hover elevation, direct edit actions, and confirmation modals for deletion.
3. **Intelligent Note Editor Dialog (`src/gui/views/note_editor.py`):**
   - Distraction-free modal editor with strict 0–1000 character boundary tracking.
   - Live debounced AI classification preview calling `POST /classify`.
   - Predicted category badge, model confidence percentage, and honest uncertainty warning (`⚠ Needs Review`).
   - Prevention of duplicate submissions during asynchronous save operations.
4. **Search Experience Workspace (`src/gui/views/search_view.py`):**
   - Prominent search input with auto-clear and enter-to-search triggers.
   - Search method switcher: **TF-IDF Cosine Similarity** (Default) vs **Keyword Search**.
   - Ranked result cards displaying relevance rank (`#1`), numerical cosine similarity (`Score: 0.7580`), and highlighted snippets.
5. **Settings & System Diagnostics (`src/gui/views/settings_view.py`):**
   - Interface theme switcher (`Dark`, `Light`, `System`) with persistent configuration in `data/app_config.json`.
   - Live system diagnostics: FastAPI Backend connectivity, ML Model readiness (τ = 0.40), and Persistent Storage status.
   - Data management: Idempotent starter notes synchronization.
   - Platform environment information (Python 3.10.11, Windows 11 64-bit, CustomTkinter 6.0.0).

### 3. Non-Blocking Architecture & Concurrency

- **Threaded API Client (`src/gui/api_client.py`):**
  - Uses `concurrent.futures.ThreadPoolExecutor(max_workers=4)` for all HTTP network calls.
  - Zero main-thread blocking: CustomTkinter UI animations and interactions remain 100% fluid.
  - Main-thread safety: Callbacks are safely marshaled to the Tkinter event loop via `tk_root.after(0, ...)`.
- **Backend Lifecycle Daemon Manager (`src/gui/backend_manager.py`):**
  - Probes `http://127.0.0.1:8000/health` on startup. Reuses existing service if active.
  - If not active, automatically spawns a child Uvicorn process binding strictly to `127.0.0.1:8000` with `CREATE_NO_WINDOW`.
  - Tracks child process ownership; cleanly terminates the owned child process upon window exit without affecting external servers.

### 4. Visual Verification & Gallery

The desktop application was visually verified on Windows 11. 11 high-resolution authentic pixel screenshots were captured via Windows GDI and saved to `results/screenshots/`:

| Screen / Feature | Screenshot File | Description |
|---|---|---|
| **Dashboard (Dark)** | `01_dashboard_dark.png` | Command center with dynamic stats, distribution, and recent notes. |
| **All Notes (Grid)** | `02_all_notes_grid.png` | Library grid view with search toolbar and category filter chips. |
| **All Notes (List)** | `03_all_notes_list.png` | Compact list view with aligned metadata. |
| **Study Category** | `04_study_category.png` | Filtered view showing academic and study notes. |
| **Money Category** | `05_money_category.png` | Financial notes displaying preserved Indian Rupee (`₹`) symbol. |
| **Travel Category** | `06_travel_category.png` | Travel and transit notes. |
| **Shopping Category**| `07_shopping_category.png`| Shopping and purchase notes. |
| **Search Workspace** | `08_search_results.png` | Ranked results with TF-IDF cosine similarity scores. |
| **Note Editor** | `09_note_editor_preview.png` | Modal dialog showing live ML classification preview and uncertainty warning. |
| **Settings & Diagnostics** | `10_settings_diagnostics.png` | System status cards, theme selector, and starter notes sync. |
| **Dashboard (Light)**| `11_dashboard_light.png` | Dashboard rendered in clean light theme. |

---

## Phase Status Summary

- **Phase 1 (Workspace Audit & Architecture Planning):** Completed & Approved.
- **Phase 2 (Environment Setup & Data Foundation):** Completed & Verified.
  - Isolated Python 3.10 virtual environment configured.
  - Phase 2 dependencies installed (`pandas`, `pytest`).
  - All 4 original datasets verified and validated for schema, categories, and encoding.
  - Modular `src/data_ingestion.py` implemented.
  - SHA-256 data integrity check verified with zero file alterations.
- **Phase 3 (Machine Learning Model Development):** Completed & Verified.
  - Baseline model trained: 68.0% Accuracy, 0.7079 Macro-F1.
  - One justified improvement implemented: Stop words removal, currency symbol (`₹`) preservation, and regularization tuning ($C=2.0$).
  - Improved model performance: **86.0% Accuracy (+18.0%), 0.8544 Macro-F1 (+0.1465)**.
  - Artifacts saved to `models/` (`tfidf_vectorizer.joblib`, `notes_classifier.joblib`, `notes_pipeline.joblib`).
  - Loading verified in an independent Python process.
  - Complete error analysis on all 7 validation mistakes documented in `results/phase3_model_report.md`.
  - Automated test suite expanded to 16 tests (all 16 passing).
- **Phase 4 (Production-Ready Uncertainty Detection & Evaluation):** Completed & Verified.
  - Confidence-based uncertainty detection module implemented (`src/uncertainty.py`).
  - Strict boundary rule enforced: `uncertain = (confidence < threshold)`.
  - Evaluated fixed thresholds: 0.35, 0.40, and 0.45 on `validation.csv` (50 samples) and `out_of_scope_examples.csv` (12 samples).
  - Recommended operating threshold: **$\tau = 0.40$** (catches 100% of validation errors, 0 incorrect but confident predictions, and detects 75.0% of out-of-scope notes).
  - Programmatic report generated at `results/phase4_uncertainty_report.md`.
  - Full automated test suite expanded to **47 tests (all 47 passing)**.
- **Phase 5 (Notes Management, Storage Engine & ML Integration):** Completed & Verified.
  - Low-level persistence module implemented (`src/notes_storage.py`) with atomic writes, corrupted JSON protection, schema validation, and UTF-8 / `₹` symbol preservation.
  - Notes manager business logic implemented (`src/notes_manager.py`) with full CRUD, category filtering across 4 valid categories, monotonic unique ID generation starting at N013, non-reuse of deleted IDs, idempotent starter notes loading, and genuine Phase 4 ML pipeline integration.
  - 10-step persistence verification workflow script implemented (`scripts/verify_phase5_persistence.py`).
  - Total automated test suite expanded to **84 tests (all 84 passing)**.
  - Zero modifications to protected dataset and model files confirmed via SHA-256 baseline verification.
- **Phase 6 (Search Engine Development & Retrieval Benchmarking):** Completed & Verified.
  - Separate search module implemented (`src/search_engine.py`) offering both Keyword Search and TF-IDF Cosine Similarity Search.
  - 15 fixed benchmark queries created (`data/search_queries.json`), including 3 programmatically verified vocabulary-mismatched queries.
  - Retrieval benchmark runner implemented (`evaluate_search.py`), evaluating Hit Rate @ 3 and generating `results/phase6_search_report.md`.
  - Both methods achieved 100.0% Hit Rate @ 3 on ordinary queries (12/12) and 0.0% on vocabulary-mismatched queries (0/3), for 80.0% overall.
  - TF-IDF selected as default engine for superior noise reduction and normalized cosine similarity scoring.
  - Integrated dynamically into `NotesManager.search_notes()` with automatic index updates on add, update, and delete.
  - Full automated test suite expanded to **104 tests (all 104 passing)**.
  - Zero modifications to protected dataset and model files confirmed via SHA-256 baseline verification.
- **Phase 7 (FastAPI Backend Engineering, Integration, Security & Full Verification):** Completed & Verified.
  - High-performance, headless local REST API service implemented (`src/api.py`).
  - Factory pattern `create_app()` with single-load model lifecycle management.
  - Process-local mutation synchronization via `asyncio.Lock()` protecting all write operations.
  - Decoupled `POST /classify` and complete CRUD endpoints (`POST`, `GET`, `PUT`, `DELETE /notes`).
  - TF-IDF and keyword search integrated into `GET /search`.
  - Idempotent starter-note loading via `POST /notes/load-starter`.
  - Strict input validation rejecting non-strings, numbers, empty/whitespace inputs with HTTP 422.
  - Complete error masking preventing internal stack traces or path leakage.
  - 100% compliance on external smoke test (`examples/test_api.py`) with Indian Rupee (`₹`) symbol support.
  - Sub-20ms warm classification latency measured in live Windows verification.
  - Full automated test suite expanded to **122 tests (all 122 passing in ~7.5s)**.
  - Zero modifications to protected dataset, model, and previous results files confirmed via SHA-256 verification.
- **Phase 8 (Premium Native Windows Desktop Application):** Completed & Verified.
  - Native Windows desktop application implemented with **CustomTkinter** (`main.py`, `src/gui/`).
  - Distinctive visual identity: **SMART NOTES — Think. Organize. Remember.**
  - Complete feature suite: Command center dashboard, notes library with grid/list modes, category chips, intelligent note editor dialog with live ML preview, dedicated TF-IDF search workspace, and settings/diagnostics view.
  - Honest uncertainty indicators displaying model confidence and amber warning badges (`⚠ Needs Review`).
  - Asynchronous background worker threads with thread-safe UI callback dispatching.
  - Automatic child backend process lifecycle management with clean teardown on exit.
  - 11 genuine Windows pixel screenshots captured to `results/screenshots/`.
  - Full automated test suite expanded to **137 tests (all 137 passing in ~11s)**.
  - Zero modifications to protected datasets and ML artifacts confirmed via SHA-256 baseline verification.
