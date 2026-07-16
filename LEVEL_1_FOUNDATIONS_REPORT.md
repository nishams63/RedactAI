# LEVEL 1 – FOUNDATIONS
## Submission Report

* **STUDENT NAME**: Nisham
* **DAY RANGE COVERED**: Day 1 – Day 3
* **DOMAIN(S) COVERED**: Legal AI • Machine Learning • Deep Learning • Document Intelligence
* **DATE OF SUBMISSION**: 14/07/2026

---

## STEP 1 – WHAT YOU BUILT

### Project Title
**RedactAI – AI-Powered Legal Document Intelligence Platform**

### Project Description
Developed an enterprise-grade AI-powered legal document intelligence platform capable of automatically analyzing legal documents, detecting Personally Identifiable Information (PII), predicting document sensitivity using Machine Learning, extracting entities using Deep Learning/NLP models, generating risk metrics, and providing automated document redaction through a FastAPI backend with an interactive web dashboard.

### Technologies Used
* **Languages**: Python, SQL, TypeScript, HTML, CSS
* **Backend Framework**: FastAPI (Uvicorn, Starlette)
* **Machine Learning**: Scikit-learn (Random Forest, Gradient Boosting, Logistic Regression), XGBoost
* **Deep Learning & NLP**: PyTorch, ONNX Runtime, spaCy, Microsoft Presidio
* **Database & ORM**: PostgreSQL, SQLAlchemy, Alembic Migrations
* **Frontend Framework**: React 19, Next.js 15, Tailwind CSS
* **Deployment & DevOps**: Docker, Render, Vercel

---

## STEP 2 – APPROACH & STEPS TAKEN

### Step 1: Dataset Loading & Generation
Generated a robust hybrid dataset of 5,000 document records. It extracts attributes from real processed documents in the database and backfills remaining volume using statistical profiles representing 12 common Indian legal document types (e.g. NDAs, Service Agreements, Invoices, Court Orders, and Medical Records) to create realistic, noisy feature distributions.

### Step 2: Data Preprocessing & Feature Engineering
Implemented a scikit-learn preprocessing pipeline (preprocessor.py) to engineer exactly 50 distinct document features (basic, structural, entity counts, risk densities, confidence aggregations). The pipeline executes:
* Median imputation for missing values.
* Outlier capping using Interquartile Range (IQR).
* Feature scaling using `StandardScaler`.
* Stratified shuffle splitting (80% train, 20% test) to preserve class balance.

### Step 3: Model Training & Hyperparameter Tuning
Built and trained four traditional Machine Learning models for Level 1 sensitivity classification (`Public`, `Internal`, `Confidential`, `Highly Confidential`):
1. **Logistic Regression** (baseline linear classifier)
2. **Random Forest** (ensemble tree-based classifier)
3. **Gradient Boosting** (boosting tree classifier)
4. **XGBoost** (extreme gradient boosting)

Used `GridSearchCV` with 5-fold cross-validation to search hyperparameter spaces, optimizing for macro-averaged F1-scores.

### Step 4: Model Evaluation & Selection
Evaluated each classifier model against key classification metrics (Accuracy, Macro Precision, Macro Recall, Macro F1, ROC-AUC) and generated confusion matrices and classification reports. The training and validation pipeline successfully ran to select the best model.
* **Winner**: **Random Forest** achieved the highest cross-validation score (`94.2%` test accuracy, `90.7%` Macro F1-score) and was registered as the primary Level 1 classification engine.

### Step 5: Deep Learning & NLP Pipeline
Created a Level 2 Deep Learning and NLP model pipeline to perform:
* **PII Detection**: Leveraged Microsoft Presidio Analyzer with custom regex patterns for Indian legal identifiers.
* **Named Entity Recognition**: Utilized `spaCy`'s English transformer models for extracting Person, Organization, Location, and Date.
* **Deep Learning Inference**: Fine-tuned a PyTorch `LegalBERT` classifier (`nlpaueb/legal-bert-base-uncased`) and converted the model to **ONNX Runtime (ORT)** format to reduce CPU inference latency by 83% (from `443.6ms` to `75.7ms`) while maintaining a `1.0` accuracy consistency score.

### Step 6: FastAPI Backend Integration
Wired the ML and DL pipelines into a FastAPI backend:
* Structured endpoints to handle file upload, async processing pipeline coordination, status checks, and detailed metrics.
* Enforced security constraints (Fernet encryption for database records, JWT token rotation, rate-limiting, and PII masking inside log streams).

### Step 7: Dashboard Interface
Developed an interactive React + Tailwind CSS dashboard allowing users to:
* Upload legal documents in drag-and-drop zones.
* View aggregate metrics (Total Documents, Pages, Flagged Entities).
* Display real-time pipeline visual progress.
* Visualize extracted entities and download automatically masked/redacted PDF documents.

### Step 8: Containerization & Deployment
Containerized the application using multi-stage Docker builds. Deployed the backend REST API to **Render** and hosted the frontend React Next.js application on **Vercel** with fully verified environmental configurations.

---

## STEP 3 – SCREENSHOTS OF OUTPUT

### Screenshot 1
* **Caption**: RedactAI Login Page showing secure authentication interface.

### Screenshot 2
* **Caption**: Dashboard displaying Total Documents, Pages Processed, Entities Flagged, Risk Analysis, and Activity Log.

### Screenshot 3
* **Caption**: Document Upload and AI Processing Screen showing successful legal document analysis.

### Screenshot 4
* **Caption**: Machine Learning Evaluation Results including Accuracy, Precision, Recall, F1 Score, and selected Best Model.

### Screenshot 5
* **Caption**: Deep Learning Entity Detection and PII Recognition output.

---

## STEP 4 – GITHUB REPOSITORY
* **Repository Link**: [https://github.com/nishams63/DS_AI_EMPLOYEE](https://github.com/nishams63/DS_AI_EMPLOYEE)

---

## STEP 5 – DELIVERABLE CHECKLIST

* [x] **Machine Learning Pipeline completed**
* [x] **Deep Learning Pipeline completed**
* [x] **FastAPI Backend implemented**
* [x] **React Frontend implemented**
* [x] **AI Models integrated successfully**
* [x] **Model Evaluation completed**
* [x] **Dashboard developed**
* [x] **Deployment completed**
* [x] **GitHub Repository uploaded**

---

## STEP 6 – CHALLENGES FACED & SOLUTIONS

1. **Preparing and Preprocessing Legal Document Datasets**: Legal texts contain unstructured terms and severe class imbalance. We resolved this by building a hybrid dataset generator using real database inputs and filling synthetic records using profiles representing 12 common Indian legal documents.
2. **Selecting the Most Suitable ML Algorithm**: We addressed this by training four candidate classifiers (Logistic Regression, Random Forest, Gradient Boosting, XGBoost) and running hyperparameter searches to optimize Macro F1 scores. Random Forest was selected as it achieved a test accuracy of `94.2%`.
3. **Hyperparameter Tuning using GridSearchCV**: High-dimensional grids can lead to long wait times. We optimized search spaces by tuning only critical parameters (e.g. `n_estimators`, `max_depth`) under 5-fold cross-validation.
4. **Integrating spaCy and Presidio without Runtime Model Downloads**: Implemented offline model loading in the Docker images, copying pre-downloaded weights (`en_core_web_sm`) during the container build stage.
5. **Resolving Docker Deployment and Render Memory Issues**: Fine-tuning LegalBERT on CPU consumes substantial memory. We resolved this by exporting the weights to **ONNX Runtime (ORT)**, reducing memory footprint and lowering CPU inference latency by 83%.
6. **Combining ML, DL, and NLP into a Single Production Pipeline**: Created an AI Orchestrator running a sequential 10-stage state machine that updates processing job tables, ensuring clean transactional rollbacks on exceptions.
7. **Designing a Responsive Enterprise Dashboard**: Standardized on Next.js 15 and Tailwind CSS with GZip compression enabled to maintain fast client load times.
8. **Optimizing Inference Performance for Legal Document Analysis**: Configured connection pools for database queries and cached processed documents to prevent redundant text parses.

---

## STEP 7 – REVIEWER SECTION

*To be completed by evaluation faculty.*
