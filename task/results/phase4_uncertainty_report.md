# Phase 4: Production-Ready Uncertainty Detection & Evaluation Report

**Project:** Smart Notes Assistant  
**Module:** Confidence-Based Uncertainty Detection (`src/uncertainty.py`)  
**Evaluator:** `evaluate_uncertainty.py`  
**Evaluation Datasets:** `data/validation.csv` (50 samples), `data/out_of_scope_examples.csv` (12 samples)  
**Status:** Complete, Verified, & Deterministic  

---

## 1. Project Objective

The objective of Phase 4 is to establish a robust, confidence-based uncertainty detection mechanism that equips the Smart Notes Assistant with a reliable self-assessment capability.

The system makes two decoupled decisions for each note:
1. **Category Prediction:** Selects the most likely category from the four allowed domains (`Study`, `Money`, `Travel`, `Shopping`).
2. **Uncertainty Decision:** Compares model confidence against a validated threshold to decide if the prediction should be flagged as uncertain (`uncertain = true/false`).

**Core Architectural Principles:**
- **Four-Class Invariance:** No fifth category (e.g. `'Out of Scope'`) is introduced. Low-confidence notes retain their best-guess predicted category while being explicitly marked as uncertain.
- **Zero Heuristics:** No keyword lookup tables, hardcoded regex rules, or external LLM API calls are used. Uncertainty is derived strictly from the trained classifier's probability distribution.
- **Zero Retraining:** The exact approved Phase 3 model artifact is evaluated without alteration.

---

## 2. Model Artifact Information

- **Loaded Model Artifact:** `models\notes_pipeline.joblib`
- **Architecture:** Scikit-learn Pipeline (`TfidfVectorizer` + `LogisticRegression` with $C=2.0$ and stop-word filtering).
- **Supported Categories:** ['Study', 'Money', 'Travel', 'Shopping']
- **Training Invariance:** Model was loaded strictly as read-only; no training operations were executed during this phase.

---

## 3. Mathematical Confidence Formula & Boundary Behavior

### Mathematical Formulation
For an input text $x$, the multinomial logistic regression model computes class probabilities via the softmax function:
$$P(y = c \mid x) = \frac{\exp(z_c)}{\sum_{k \in \mathcal{C}} \exp(z_k)}, \quad \text{where } z_c = w_c^T \phi(x) + b_c$$

The prediction and confidence are formulated as:
- **Predicted Category:** $$\hat{c} = \arg\max_{c \in \mathcal{C}} P(y = c \mid x)$$
- **Confidence Score:** $$S(x) = \max_{c \in \mathcal{C}} P(y = c \mid x) = P(y = \hat{c} \mid x)$$

### Exact Threshold Boundary Rules
Given a validated operating threshold $\tau \in [0.0, 1.0]$:

| Condition | Operational Decision | Meaning |
|---|:---:|---|
| $S(x) < \tau$ | `uncertain = true` | Model confidence is strictly below cutoff; note is flagged as uncertain. |
| $S(x) = \tau$ | `uncertain = false` | Model confidence meets threshold exactly; note is accepted as confident. |
| $S(x) > \tau$ | `uncertain = false` | Model confidence strictly exceeds cutoff; note is accepted as confident. |

---

## 4. Mandatory Threshold Comparison Table

The fixed thresholds (0.35, 0.40, 0.45) were evaluated across the 50 validation samples and 12 out-of-scope samples. All values are generated directly from code execution:

| Threshold | Validation uncertain | Validation rate | OOS flagged uncertain | OOS detection rate | Incorrect but confident |
|---|---:|---:|---:|---:|---:|
| 0.35 | 11 | 22.0% | 7 | 58.3% | 1 |
| 0.40 | 16 | 32.0% | 9 | 75.0% | 0 |
| 0.45 | 17 | 34.0% | 10 | 83.3% | 0 |

---

## 5. Detailed Dataset Evaluations

### 5.1 Validation Dataset Evaluation (`data/validation.csv`, 50 examples)

| Threshold | Total Samples | Correct Predictions | Incorrect Predictions | Flagged Uncertain | Confident | Incorrect but Confident |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.35 | 50 | 43 | 7 | 11 | 39 | **1** |
| 0.40 | 50 | 43 | 7 | 16 | 34 | **0** |
| 0.45 | 50 | 43 | 7 | 17 | 33 | **0** |

### 5.2 Out-of-Scope Dataset Evaluation (`data/out_of_scope_examples.csv`, 12 examples)

| Threshold | Total Samples | Flagged Uncertain (Detected) | Detection Rate | Unflagged (False Acceptance) | Unflagged Rate |
|:---:|:---:|:---:|:---:|:---:|:---:|
| 0.35 | 12 | 7 | 58.3% | 5 | 41.7% |
| 0.40 | 12 | 9 | 75.0% | 3 | 25.0% |
| 0.45 | 12 | 10 | 83.3% | 2 | 16.7% |

---

## 6. Incorrect but Confident Predictions (Silent Failure Analysis)

An **incorrect but confident** prediction occurs when the model makes a wrong classification that is nevertheless accepted as confident ($S(x) \ge \tau$). This represents a dangerous silent failure mode for user trust.

### At Threshold $\tau = 0.35$ (1 silent error(s)):
| Row # | Note Text | Actual Category | Predicted Category | Confidence | Probability Distribution |
|:---:|:---|:---:|:---:|:---:|:---|
| 12 | "I must reach the railway station by 2 PM." | **Travel** | `Study` | 0.3634 | Money: 0.14, Shopping: 0.15, Study: 0.36, Travel: 0.35 |

### At Threshold $\tau = 0.40$ (0 silent error(s)):
- **None.** Every single misclassified validation note was successfully caught and marked uncertain.

### At Threshold $\tau = 0.45$ (0 silent error(s)):
- **None.** Every single misclassified validation note was successfully caught and marked uncertain.

---

## 7. Out-of-Scope False Acceptance Analysis (Leakage into 4 Classes)

When an out-of-scope note exhibits confidence $\ge \tau$, it is falsely accepted into one of the four categories.
Below are the genuinely calculated linear decision-score contributions ($z_c = b_c + \sum_i x_i w_{c,i}$) derived directly from the fitted TF-IDF vectorizer and Logistic Regression model.

> [!NOTE] Linear Decision Scores vs Causal Explanations: The token contributions below represent components of the linear logit ($z_c = b_c + \sum_i x_i w_{c,i}$) prior to the softmax transform. They indicate which vocabulary features aligned with training class coefficients to push confidence above threshold, rather than causal explanations or calibrated posterior probabilities.

### At Threshold $\tau = 0.35$ (5 unflagged note(s)):
| Row # | Out-of-Scope Text | Falsely Accepted As | Confidence | Intercept ($b_c$) | Top Positive Token Contributions ($x_i w_{c,i}$) | Logit ($z_c$) |
|:---:|:---|:---:|:---:|:---:|:---|:---:|
| 2 | "Doctor's appointment on Tuesday at 4 PM." | `Study` | 0.4970 | +0.1395 | `pm` (+0.4055), `tuesday` (+0.2941) | +0.8391 |
| 6 | "Drink more water every day." | `Money` | 0.5035 | -0.1227 | `water` (+0.9805) | +0.8578 |
| 8 | "Charge the power bank tonight." | `Money` | 0.4476 | -0.1227 | `bank` (+1.0528) | +0.7395 |
| 9 | "Remember to take vitamins after breakfast." | `Travel` | 0.3681 | +0.0191 | `remember` (+0.4031) | +0.4222 |
| 10 | "Take the trash out on Thursday night." | `Study` | 0.3654 | +0.1395 | `thursday` (+0.2802) | +0.4197 |

### At Threshold $\tau = 0.40$ (3 unflagged note(s)):
| Row # | Out-of-Scope Text | Falsely Accepted As | Confidence | Intercept ($b_c$) | Top Positive Token Contributions ($x_i w_{c,i}$) | Logit ($z_c$) |
|:---:|:---|:---:|:---:|:---:|:---|:---:|
| 2 | "Doctor's appointment on Tuesday at 4 PM." | `Study` | 0.4970 | +0.1395 | `pm` (+0.4055), `tuesday` (+0.2941) | +0.8391 |
| 6 | "Drink more water every day." | `Money` | 0.5035 | -0.1227 | `water` (+0.9805) | +0.8578 |
| 8 | "Charge the power bank tonight." | `Money` | 0.4476 | -0.1227 | `bank` (+1.0528) | +0.7395 |

### At Threshold $\tau = 0.45$ (2 unflagged note(s)):
| Row # | Out-of-Scope Text | Falsely Accepted As | Confidence | Intercept ($b_c$) | Top Positive Token Contributions ($x_i w_{c,i}$) | Logit ($z_c$) |
|:---:|:---|:---:|:---:|:---:|:---|:---:|
| 2 | "Doctor's appointment on Tuesday at 4 PM." | `Study` | 0.4970 | +0.1395 | `pm` (+0.4055), `tuesday` (+0.2941) | +0.8391 |
| 6 | "Drink more water every day." | `Money` | 0.5035 | -0.1227 | `water` (+0.9805) | +0.8578 |

---

## 8. Operating Threshold Recommendation & Trade-Off Analysis

### Recommended Operating Threshold: $\tau = 0.40$

### Empirical Justification
1. **Zero Silent Errors:** At $\tau = 0.40$, **100% of validation errors are intercepted** (0 incorrect but confident predictions). At $\tau = 0.35$, note `"I must reach the railway station by 2 PM."` slips through with confidence 0.3634, creating a silent error.
2. **75.0% Out-of-Scope Rejection:** Catches 9 out of 12 completely unrelated personal notes without needing explicit out-of-scope training.
3. **Preserving In-Scope Usability:** Retains **68.0% of valid notes (34/50)** as confident, ensuring legitimate user notes are not excessively flagged as uncertain.
4. **Comparison with $\tau = 0.45$:** While $\tau = 0.45$ increases out-of-scope detection by 1 note (83.3% vs 75.0% by catching *'Charge the power bank tonight'*), it drops in-scope confident acceptance to 66.0%. Thus, $\tau = 0.40$ represents the optimal balanced operating point, with $\tau = 0.45$ serving as a viable safety-critical alternative.

---

## 9. Limitations & Practical Caveats

1. **Sample Size Constraints:** The validation set contains 50 notes and the out-of-scope set contains 12 notes. These numbers represent empirical indicators rather than asymptotic guarantees.
2. **Uncalibrated Model Confidence:** Maximum softmax probabilities from logistic regression represent relative model margin confidence scores, not true Bayesian posterior correctness probabilities. No formal calibration (e.g. Platt scaling, isotonic regression, or conformal prediction) is claimed.
3. **Polysemous Out-of-Scope Vulnerability:** Notes that happen to contain high-weight training tokens (e.g. *'water'* in *'Drink more water'*, *'bank'* in *'power bank'*, *'pm'* in *'Doctor appointment'*) receive elevated confidence because the linear bag-of-words representation lacks semantic compositionality.

---

## 10. Reproduction Command

Execute the evaluation and report generator from project root with a single command:
```powershell
python evaluate_uncertainty.py
```
