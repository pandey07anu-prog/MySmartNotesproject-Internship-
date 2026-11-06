# AI_WORKFLOW — Engineering Process & Verification

## 1. Development & AI Tools Used
- **Primary AI Assistant:** Antigravity / Gemini 3.8 Flash (Code generation, architecture design, and refactoring).
- **Core Backend:** Python 3.13, FastAPI 0.135, Uvicorn, Pydantic v2, PyMongo, Motor, MongoMock.
- **Machine Learning & Analytics:** Scikit-learn, Pandas, NumPy, Joblib.
- **Security & Crypto:** Argon2-cffi, PyJWT.
- **Testing:** Pytest, FastAPI TestClient, and official assessment script `examples/test_api.py`.
- **Frontend:** Vanilla HTML5, CSS3, ES6 JavaScript, Fetch API, responsive glassmorphism.

---

## 2. One Delegated Task & Prompt

### Actual Prompt Submitted:
> *"Implement the evaluation function for search retrieval in Python that calculates Hit Rate @ 3 across the 15 queries in data/search_queries.json against data/starter_notes.json, comparing basic keyword token overlap with TF-IDF cosine similarity, and reporting failed queries."*

### What Was Kept:
- The TF-IDF cosine similarity vectorization using `TfidfVectorizer(sublinear_tf=True)` and ranking with `np.argsort`.
- The calculation formula for Hit Rate @ 3 ($\text{Hits} / \text{Total}$).
- The parsing and extraction of the 15 evaluation queries from JSON.

### What Was Changed:
- Added a custom tokenizer with regex `(?u)\b\w+\b|[₹$€£]` to ensure currency symbols like `₹` in `N006` (`"Move ₹2,000 into savings"`) are preserved during tokenization.
- Added explicit minimum relevance threshold (`min_similarity=0.05`) to discard zero-similarity notes instead of returning arbitrary non-matching notes.
- Added Windows console UTF-8 reconfigure (`sys.stdout.reconfigure(encoding="utf-8")`) to prevent `UnicodeEncodeError` when printing currency symbols in PowerShell.

---

## 3. One Problem Caught & Resolved

### Problem: Pydantic v2 Serialization Crash in Request Validation Handler
- **Symptom:** During automated execution of the official assessment smoke test (`python examples/test_api.py`), testing the invalid body `{"text": "   "}` caused an internal HTTP 500 server exception instead of the required HTTP 422:
  ```text
  TypeError: Object of type ValueError is not JSON serializable
  ```
- **How It Was Discovered:** Executing the official assessment test runner `examples/test_api.py --url http://127.0.0.1:8000/classify` directly against the live FastAPI Uvicorn process.
- **Root Cause:** In Pydantic v2, `exc.errors()` contains a `ctx` dictionary containing the raw Python `ValueError` instance thrown by the `@field_validator`. When passed into Starlette's `JSONResponse`, standard `json.dumps()` crashed attempting to serialize the Python exception object.
- **Fix & Verification:**
  Reconstructed clean dictionary representations of the validation errors in `app/main.py` by extracting only serializable keys (`type`, `loc`, `msg` as `str`), safely passing the formatted payload to `JSONResponse(status_code=422)`.
  Re-running `examples/test_api.py` proved the fix:
  ```text
  PASS whitespace text -> HTTP 422 (expected 4xx)
  PASS empty text -> HTTP 422 (expected 4xx)
  All format checks passed.
  Return code: 0
  ```

---

## 4. Time Spent
- **Total focused effort:** ~7.5 hours (Architecture, ML training, API development, Apple-inspired UI, authentication, test suite, and verification).

