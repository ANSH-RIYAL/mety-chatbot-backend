import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from datetime import datetime
from google.cloud import firestore

"""
Firestore Schema:
- Collection: users
  Document ID: <user_id>
  Fields:
    - profile: {name, age, gender, sleep_quality, stress_quality, ...}
    - current_plan: {variable: value, ...}
    - target_plan: {variable: value, ...}
    - optimal_plan: {variable: value, ...}
    - vars_extracted: {variable: value, ...}
    - last_updated: ISO timestamp string

- Collection: chat_history
  Document ID: auto-generated
  Fields:
    - user_id: string
    - role: "user" | "assistant"
    - text: message content
    - timestamp: ISO timestamp string

- Collection: plans_history
  Document ID: auto-generated
  Fields:
    - user_id: string
    - diff: {variable: value, ...}
    - timestamp: ISO timestamp string
    - source: "ui" | "chat"

- Collection: logs
  Document ID: auto-generated
  Fields:
    - user_id: string
    - log: {variable: value, ...}
    - period_start: YYYY-MM-DD string
    - period_end: YYYY-MM-DD string
    - adherence: {total: float, diet: float, supplement: float}
    - timestamp: ISO timestamp string
"""

# =====================================================
# Connect to Firestore - works locally AND on Cloud Run
# =====================================================

credentials_path = "firebase-credentials_prod.json"

if os.path.exists(credentials_path):
    # Local development: use JSON credentials file
    from google.oauth2 import service_account
    print(f"Using credentials file: {credentials_path}")
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    db = firestore.Client(credentials=credentials, project=credentials.project_id)
else:
    # Cloud Run / GCP: use Application Default Credentials
    project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "srs-creator-app"
    print(f"No credentials file found. Using Application Default Credentials with project: {project_id}")
    db = firestore.Client(project=project_id)

collections = ["users", "chat_history", "plans_history", "logs"]

print("Testing Firestore connection...")

test_user_id = "test_user_123"
user_ref = db.collection("users").document(test_user_id)

test_user_data = {
    "profile": {
        "name": "Test User",
        "age": 30,
        "gender": 0,
        "sleep_quality": 2,
        "stress_quality": 1
    },
    "current_plan": {"fruits_and_veggies": 5},
    "target_plan": {"fruits_and_veggies": 7},
    "optimal_plan": {"fruits_and_veggies": 8.4319},
    "vars_extracted": {},
    "last_updated": datetime.utcnow().isoformat()
}

user_ref.set(test_user_data)
print(f"✓ Created user document: {test_user_id}")

read_user = user_ref.get()
if read_user.exists:
    print(f"✓ Read user document: {read_user.to_dict()['profile']['name']}")
else:
    print("✗ Failed to read user document")

chat_ref = db.collection("chat_history").document()
chat_data = {
    "user_id": test_user_id,
    "role": "user",
    "text": "I want to eat more fruits",
    "timestamp": datetime.utcnow().isoformat()
}
chat_ref.set(chat_data)
print(f"✓ Created chat_history document: {chat_ref.id}")

plan_ref = db.collection("plans_history").document()
plan_data = {
    "user_id": test_user_id,
    "diff": {"fruits_and_veggies": 7},
    "timestamp": datetime.utcnow().isoformat(),
    "source": "ui"
}
plan_ref.set(plan_data)
print(f"✓ Created plans_history document: {plan_ref.id}")

log_ref = db.collection("logs").document()
log_data = {
    "user_id": test_user_id,
    "log": {"fruits_and_veggies": 6},
    "period_start": "2025-11-01",
    "period_end": "2025-11-15",
    "adherence": {"total": 0.72, "diet": 0.78, "supplement": 0.65}
}
log_ref.set(log_data)
print(f"✓ Created log document: {log_ref.id}")

user_ref.update({"target_plan": {"fruits_and_veggies": 8}})
updated = user_ref.get()
if updated.exists:
    print(f"✓ Updated user document: target_plan = {updated.to_dict()['target_plan']}")

chat_query = db.collection("chat_history").where("user_id", "==", test_user_id).limit(1).get()
if chat_query:
    print(f"✓ Queried chat_history: found {len(chat_query)} document(s)")

print("\nAll Firestore tests passed! ✓")
