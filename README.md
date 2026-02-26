# Chatbot Assistant Platform

FastAPI backend for the website chatbot assistant platform.

## Setup

1. **Enable Firestore API** (if not already enabled):
   - Visit: https://console.developers.google.com/apis/api/firestore.googleapis.com/overview?project=srs-creator-app
   - Or use: `gcloud services enable firestore.googleapis.com --project=srs-creator-app`

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Environment variables**:
   - `OPENAI_API_KEY` is loaded from `secrets.env`
   - `FIRESTORE_CREDENTIALS` defaults to `firebase-credentials_prod.json`
   - `LIFESPAN_API_URL` defaults to the production API URL

## Running

```bash
python app.py
```

Or with uvicorn:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## API Endpoints

- `GET /health` - Health check
- `POST /onboarding/submit` - Submit onboarding page data
- `GET /plan/get?user_id=<id>` - Get user plans
- `POST /plan/update` - Update target plan with diff
- `POST /log/submit` - Submit log and calculate adherence
- `POST /lifespan/predict` - Predict lifespan and risk ratios
- `POST /chat` - Main chat orchestration endpoint
- `GET /user/vars?user_id=<id>` - Get user vars_extracted and target_plan

## Testing

Run the test scripts:
```bash
python tests/test_api.py
python tests/test_pipeline.py
python tests/test_firestore.py
```

Make sure the server is running on `localhost:8000` first.

## Documentation

See `docs/` directory for:
- `common_document.md` - System overview and shared schemas
- `backend_document.md` - Backend routes and implementation details
- `frontend_document.md` - Frontend pages and components
- `test_everything_manually.md` - Manual testing procedures

