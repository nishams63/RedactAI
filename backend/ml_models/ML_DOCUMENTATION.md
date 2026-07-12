# RedactAI — Level 1 Machine Learning Baseline Documentation

## Architecture Overview

The Level 1 ML pipeline predicts the **Sensitivity Label** (`Public`, `Internal`, `Confidential`, `Highly Confidential`) of a document after it has passed through the Document Intelligence Layer.

We use traditional Machine Learning algorithms (Logistic Regression, Random Forest, Gradient Boosting, XGBoost) combined with structured feature engineering, avoiding Deep Learning per the Level 1 evaluation rubric.

## Dataset Strategy

### Hybrid Dataset Generation
Since real processed documents may be sparse during initial deployment, we implemented a **Hybrid Dataset Generator**. 
- It extracts features from all actual `Processed` documents in the database.
- It backfills the remaining volume up to the requested size (e.g., 5,000 samples) using statistical profiles of 12 common Indian legal document types (e.g., NDAs, Court Orders, Aadhaar copies).
- It ensures a realistic, noisy distribution of features mimicking real-world OCR/NER artifacts.

### Deterministic Labeling Rules
A single source of truth (`apply_sensitivity_label` in `config.py`) labels both real and synthetic vectors deterministically based on business rules:
1. **Highly Confidential**: `critical_count >= 3` OR `(aadhaar + passport + bank) >= 2`
2. **Confidential**: `high_count >= 3` OR `critical_count >= 1` OR `contains_gov_id`
3. **Internal**: `total_entities >= 5` OR `medium_count >= 3`
4. **Public**: Everything else.

## Feature Engineering

We extract exactly 50 features from the structured intelligence tables (`DocumentMetadata`, `DocumentPage`, `DocumentBlock`, `DocumentEntity`):

1. **Basic (4)**: `num_pages`, `total_words`, `total_characters`, `avg_sentence_length`
2. **Structural (6)**: Counts of headers, footers, tables, images, signatures, stamps.
3. **Entities & PII (21)**: Counts of specific NER/PII entities (Person, Org, Aadhaar, PAN, Bank Account, etc.)
4. **Metadata & Risk (10)**: Language encoding, encryption status, digital signatures, max/avg confidence, risk level bins.
5. **Engineered (9)**:
   - Density features: `pii_density`, `entity_density`, `risk_density`
   - Aggregate ratios: `critical_ratio`, `avg_entities_per_page`
   - Boolean flags: `contains_gov_id`, `contains_financial_data`, `contains_legal_terms`

## Preprocessing Pipeline

Implemented in `services/ml/preprocessor.py` using `scikit-learn`:
- **Imputation**: Median strategy for any missing values.
- **Outlier Handling**: IQR (Interquartile Range) capping to handle OCR spikes.
- **Scaling**: `StandardScaler` (zero mean, unit variance).
- **Encoding**: Label encoding for the 4 sensitivity classes.
- **Splitting**: `StratifiedShuffleSplit` (80/20) to maintain class balance.

All preprocessing artifacts (`scaler.joblib`, `imputer.joblib`, `label_encoder.joblib`) are persisted to ensure reproducible inference.

## Model Selection & Tuning

We evaluate 4 traditional algorithms:
- **Logistic Regression**: Serves as a linear baseline.
- **Random Forest**: Handles non-linear feature interactions well and resists overfitting.
- **Gradient Boosting**: Sequential tree building for higher accuracy.
- **XGBoost**: Highly optimized gradient boosting (fails over gracefully if the C++ library cannot be installed).

### Hyperparameter Tuning
We use `GridSearchCV` with 5-fold cross-validation on the training set, optimizing for `f1_macro` to account for class imbalances. 

### Experiment Tracking
Every training run is logged to the `experiment_runs` and `model_evaluations` tables, satisfying the CTO's requirement for MLOps tracking.

## Integration & Inference

1. **Auto-Prediction**: When the AI Orchestrator successfully completes processing (Stage 10), it invokes the `MLPredictor` asynchronously to generate a sensitivity prediction.
2. **API Access**: The `/api/v1/ml/predict/{id}` endpoint allows on-demand prediction.
3. **Dashboard**: The React dashboard fetches evaluation metrics, confusion matrices, and feature importance data directly from the backend.
