# Mety Chatbot Backend

FastAPI backend for the Mety Chatbot platform, deployed on GCP Cloud Run.

## Live URL

**Production:** https://mety-chatbot-api-172415469528.us-central1.run.app

## Tech Stack

- **Framework:** FastAPI + Uvicorn
- **Database:** Google Firestore
- **LLM:** OpenAI GPT
- **Hosting:** GCP Cloud Run

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/health/metrics` | GET | System metrics |
| `/plan/get` | GET | Get user's plan |
| `/plan/update` | POST | Update user's plan |
| `/chat/message` | POST | Send chat message |
| `/onboarding/submit` | POST | Submit onboarding data |

## Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=your-key

# Run server
python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

## CI/CD

Auto-deploys to Cloud Run on push to `main` via GitHub Actions.

**Required Secrets:**
- `GCP_SA_KEY` - Service account JSON
- `GCP_PROJECT_ID` - GCP project ID
- `GCP_REGION` - Deployment region

## Project Structure

```
├── app.py              # FastAPI application
├── config.py           # Configuration
├── Dockerfile          # Container config
├── requirements.txt    # Dependencies
└── services/
    ├── firestore_service.py   # Database operations
    ├── llm_service.py         # OpenAI integration
    ├── prediction_api.py      # Lifespan prediction
    ├── adherence.py           # Adherence calculations
    └── metrics_service.py     # System metrics
```
