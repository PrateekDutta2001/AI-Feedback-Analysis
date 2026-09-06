# InsightAI

Enterprise Feedback Intelligence Platform.

InsightAI turns raw customer, user, and employee feedback into structured operational intelligence: sentiment, emotion, category, intent, priority, severity, topics, duplicates, and recommended actions.

## Overview

The platform is a production-style full-stack application:

- Frontend: HTML5, CSS3, vanilla JavaScript, Chart.js
- Backend: Python, FastAPI, SQLAlchemy
- ML: scikit-learn TF-IDF + Logistic Regression
- Database: SQLite
- No React, no paid APIs, no external LLM dependency

On first startup the application creates the database, imports a realistic dummy dataset, trains models if they are missing, generates insights and alerts, and serves the UI at `http://localhost:8000`.

## Features

- Manual feedback capture and CSV import with validation
- Automatic ML analysis after every create/import
- Dashboard KPIs, charts, and dynamic AI insights
- Feedback explorer with search, filters, sort, pagination, bulk actions
- Detail drawer with explanations, similar records, and recommended actions
- Topic discovery, aspect analysis, department and product rankings
- Alert center with read/resolve/delete
- Model center with real train/test metrics and retraining
- CSV/JSON export, audit trail, health endpoint, Swagger docs

## Architecture

```text
                 ┌──────────────────────┐
                 │      User Browser    │
                 │ HTML/CSS/JavaScript  │
                 └──────────┬───────────┘
                            │
                            ▼
                 ┌──────────────────────┐
                 │      FastAPI API     │
                 │   REST Architecture  │
                 └──────────┬───────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
       ┌────────────┐ ┌────────────┐ ┌────────────┐
       │ Feedback   │ │ Analytics  │ │ ML Engine  │
       │ Service    │ │ Service    │ │            │
       └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
             │              │              │
             └──────────────┼──────────────┘
                            ▼
                    ┌───────────────┐
                    │    SQLite     │
                    └───────────────┘
```

## Application flow

1. The browser loads the InsightAI shell from FastAPI static files.
2. Each view requests JSON from `/api/*`.
3. Services query SQLite and, when needed, run the ML pipeline.
4. Aggregations power dashboards, insights, and alerts.
5. Important actions are written to `audit_logs` and rotating log files.

## Feedback processing flow

```text
User submits feedback
        ↓
Input validation
        ↓
Text preprocessing
        ↓
TF-IDF vectorization
        ↓
Sentiment model
        ↓
Emotion model
        ↓
Category model
        ↓
Intent model
        ↓
Keyword extraction
        ↓
Aspect detection
        ↓
Severity scoring
        ↓
Priority engine
        ↓
Duplicate detection
        ↓
Recommendation engine
        ↓
Database
        ↓
Dashboard / Analytics / Alerts
```

## Data flow

```text
CSV
 │
 ▼
Upload API
 │
 ▼
Validation
 │
 ▼
Normalization
 │
 ▼
Database
 │
 ▼
ML Pipeline
 │
 ├── Sentiment
 ├── Emotion
 ├── Category
 ├── Intent
 ├── Keywords
 ├── Topics
 ├── Priority
 └── Similarity
 │
 ▼
Analytics
 │
 ▼
Dashboard
```

## Model architecture

```text
Raw Text
   │
   ▼
Cleaning
   │
   ▼
TF-IDF
   │
   ├─────────────┐
   ▼             ▼
Sentiment     Emotion
Classifier    Classifier
   │             │
   └──────┬──────┘
          ▼
      Categories
          │
          ▼
        Intent
          │
          ▼
   Priority Engine
```

Classifiers are persisted in `models/*.joblib` and are loaded once at startup. They are not retrained on every request.

## Database schema

### feedback

`id`, `feedback_id`, `customer_id`, `text`, `date`, `product`, `department`, `channel`, `location`, `segment`, `rating`, `status`, `is_duplicate`, `duplicate_of_id`, `created_at`, `updated_at`

### feedback_analysis

`id`, `feedback_pk`, `sentiment`, `sentiment_score`, `sentiment_positive`, `sentiment_neutral`, `sentiment_negative`, `emotion`, `emotion_score`, `category`, `category_score`, `intent`, `intent_score`, `priority`, `priority_score`, `priority_reasons`, `severity`, `keywords`, `topics`, `aspects`, `recommendation`, `explanation`, `analyzed_at`

### alerts

`id`, `alert_id`, `type`, `severity`, `message`, `feedback_id`, `status`, `created_at`, `resolved_at`

### Additional tables

- `products`, `departments`, `users`
- `datasets`
- `model_registry`
- `audit_logs`

Indexes exist on common filter columns such as date, product, department, channel, sentiment, category, and priority.

## API architecture

All JSON endpoints return:

```json
{
  "success": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

Key routes:

- `GET /api/health`
- `GET /api/dashboard`
- `GET/POST /api/feedback`
- `GET /api/feedback/{id}`
- `POST /api/feedback/analyze`
- `POST /api/feedback/bulk-analyze`
- `POST /api/upload`
- `POST /api/import`
- `GET /api/analytics/sentiment|trends|categories|emotions|departments|products|topics|aspects`
- `GET /api/insights`
- `GET/PATCH/DELETE /api/alerts`
- `GET /api/models`
- `POST /api/models/train`
- `GET /api/export/csv`
- `GET /api/export/json`

Interactive docs: [http://localhost:8000/docs](http://localhost:8000/docs) and [http://localhost:8000/redoc](http://localhost:8000/redoc).

### Sample analysis response

```json
{
  "success": true,
  "data": {
    "feedback_id": "FB-10023",
    "text": "The delivery was extremely late.",
    "analysis": {
      "sentiment": {
        "label": "negative",
        "confidence": 0.96
      },
      "emotion": {
        "label": "frustration",
        "confidence": 0.89
      },
      "category": "Delivery",
      "intent": "Complaint",
      "priority": "high",
      "severity": 4
    }
  }
}
```

## Folder structure

```text
backend/app/          FastAPI app, services, ML, utilities
backend/tests/        pytest suite
frontend/             HTML, CSS, JavaScript
data/                 training_data.csv, dummy_feedback.csv
models/               persisted scikit-learn pipelines
logs/                 app.log, error.log, audit.log
exports/              generated CSV/JSON files
```

## Model training and inference

Training uses `data/training_data.csv` with a stratified 80/20 split. Metrics stored in the registry are real accuracy, precision, recall, F1, and confusion matrices.

Inference cleans text, vectorizes with the saved TF-IDF vocabulary, then runs the four classifiers plus deterministic priority, severity, keyword, aspect, similarity, and recommendation steps.

Retrain from **ML Models → Retrain Models** or `POST /api/models/train`.

## Duplicate detection

New feedback is compared with recent records using TF-IDF cosine similarity. Matches at or above `SIMILARITY_THRESHOLD` (default `0.85`) are flagged and shown in the detail drawer.

## Topic discovery

KMeans clusters TF-IDF vectors of the current filtered corpus. Each topic includes a generated name, count, sentiment mix, keywords, and a short trend series.

## Analytics calculation

All dashboard numbers are queried from SQLite. KPI deltas compare the current window with the previous window of the same length. Insights are assembled from those statistics; they are not hardcoded.

## Alert generation

Rules create alerts for critical open feedback, negative sentiment spikes, emerging terms, rating drops, duplicate spikes, and high-volume categories. Operators can mark alerts read, resolve them, filter them, or delete them.

## Security

- CORS origins come from `CORS_ORIGINS`
- Pydantic and explicit validators for ratings, channels, and uploads
- CSV type and size limits
- SQLAlchemy parameterized queries
- Frontend XSS escaping
- Generic 500 messages; stack traces stay in `logs/error.log`
- No secrets in source. Copy `.env.example` to `.env`

## Logging

Rotating files:

- `logs/app.log`
- `logs/error.log`
- `logs/audit.log`

Audit events include `FEEDBACK_CREATED`, `CSV_IMPORTED`, `MODEL_RETRAINED`, `EXPORT_GENERATED`, and `ALERT_RESOLVED`.

## Configuration

See `.env.example` for `APP_NAME`, `DATABASE_URL`, directory paths, CORS, and `SIMILARITY_THRESHOLD`.

## Local setup

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
python backend/run.py
```

Application: [http://localhost:8000](http://localhost:8000)

Swagger: [http://localhost:8000/docs](http://localhost:8000/docs)

Reload mode:

```bash
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

The first start generates datasets, trains models if needed, imports 2,000+ dummy records, and analyzes them. Later starts reuse existing model files and the SQLite database.

## Testing

```bash
pytest
```

The suite covers health, feedback CRUD, analysis, dashboard, analytics, upload/export, ML predictions, priority, keywords, similarity, and database filtering.

## Deployment

### Uvicorn

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### Gunicorn

```bash
gunicorn backend.app.main:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

SQLite is intended for single-process use. For multi-worker production, move `DATABASE_URL` to a shared SQL database.

### Docker

```bash
docker compose up --build
```

The image runs as a non-root user, exposes a healthcheck, and persists database, models, logs, and exports through volumes.

## Troubleshooting

- **Blank dashboard:** wait for first-run analysis to finish, then refresh.
- **Model errors:** delete `models/*.joblib` and restart, or use Retrain Models.
- **CSV rejected:** confirm `.csv` extension and required columns: `text`, `date`, `product`, `department`, `channel`, `location`, `segment`, `rating`.
- **Port in use:** change `PORT` in `.env`.
- **Tests seeing production data:** tests use `insightai-test.db` and `APP_ENV=test`.

## License

Internal demonstration software for InsightAI.
