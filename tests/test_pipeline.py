"""Comprehensive pipeline test - walk through entire flow."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"
TEST_USER_ID = f"test_user_{int(datetime.now().timestamp())}"

def print_section(title):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_step(step_name, func):
    print(f"\n▶ {step_name}")
    try:
        result = func()
        print(f"✓ Success")
        return result
    except Exception as e:
        print(f"✗ Failed: {e}")
        return None

print_section("COMPREHENSIVE PIPELINE TEST")
print(f"Test User ID: {TEST_USER_ID}")

# Step 1: Health check
test_step("Health Check", lambda: requests.get(f"{BASE_URL}/health").json())

# Step 2: Onboarding - About Me
print_section("ONBOARDING: About Me")
about_me_data = test_step("Submit About Me", lambda: requests.post(
    f"{BASE_URL}/onboarding/submit",
    json={
        "user_id": TEST_USER_ID,
        "page": "About Me",
        "payload": {
            "name": "Test User",
            "age": 30,
            "gender": 0,
            "stress_quality": 1,
            "sleep_quality": 2
        }
    }
).json())
print(f"Response: {json.dumps(about_me_data, indent=2)}")

# Step 3: Get Plan (should have optimal plan)
print_section("GET PLAN")
plan_data = test_step("Get Plan", lambda: requests.get(
    f"{BASE_URL}/plan/get?user_id={TEST_USER_ID}"
).json())
print(f"Current Plan: {plan_data.get('current_plan', {})}")
print(f"Target Plan: {plan_data.get('target_plan', {})}")
print(f"Optimal Plan Keys: {list(plan_data.get('optimal_plan', {}).keys())[:5]}...")

# Step 4: Update Plan
print_section("UPDATE PLAN")
update_result = test_step("Update Target Plan", lambda: requests.post(
    f"{BASE_URL}/plan/update",
    json={
        "user_id": TEST_USER_ID,
        "diff": {
            "fruits_and_veggies": 7,
            "olive_oil": 30
        }
    }
).json())
print(f"Applied Diff: {update_result.get('applied_diff', {})}")
print(f"New Target Plan (sample): {dict(list(update_result.get('new_target_plan', {}).items())[:3])}")

# Step 5: Chat - Variable Extraction
print_section("CHAT: Variable Extraction")
chat_response = test_step("Chat - Extract Variables", lambda: requests.post(
    f"{BASE_URL}/chat",
    json={
        "user_id": TEST_USER_ID,
        "messages": [
            {"role": "user", "text": "I don't want Vitamin A"},
            {"role": "user", "text": "I'll eat 6 servings of fruits per day"}
        ],
        "options": {
            "auto_apply_extracted_vars": False,
            "recent_plan_snapshot": {}
        }
    }
).json())

print(f"\nAssistant Message: {chat_response.get('assistant_message', '')[:200]}...")
print(f"\nVars Extracted: {chat_response.get('vars_extracted', {})}")
print(f"Diff Detected: {chat_response.get('diff_detected', {})}")
print(f"Unknown Keys: {chat_response.get('unknown_keys', [])}")
print(f"\nSuggested Plan (sample): {dict(list(chat_response.get('suggested_plan', {}).items())[:5])}")
print(f"\nLifespan Projection: {chat_response.get('lifespan_projection', {})}")
print(f"\nActions: {chat_response.get('actions', [])}")

# Step 6: Chat - With Auto-apply
print_section("CHAT: Auto-apply Variables")
chat_auto = test_step("Chat - Auto-apply", lambda: requests.post(
    f"{BASE_URL}/chat",
    json={
        "user_id": TEST_USER_ID,
        "messages": [
            {"role": "user", "text": "I'll take 50g of olive oil daily"}
        ],
        "options": {
            "auto_apply_extracted_vars": True,
            "recent_plan_snapshot": {}
        }
    }
).json())
print(f"Vars Extracted: {chat_auto.get('vars_extracted', {})}")
print(f"Diff Detected: {chat_auto.get('diff_detected', {})}")

# Step 7: Verify Plan Updated
print_section("VERIFY PLAN UPDATED")
updated_plan = test_step("Get Updated Plan", lambda: requests.get(
    f"{BASE_URL}/plan/get?user_id={TEST_USER_ID}"
).json())
print(f"Target Plan (fruits_and_veggies): {updated_plan.get('target_plan', {}).get('fruits_and_veggies', 'N/A')}")
print(f"Target Plan (olive_oil): {updated_plan.get('target_plan', {}).get('olive_oil', 'N/A')}")

# Step 8: Log Submit
print_section("LOG SUBMIT")
log_result = test_step("Submit Log", lambda: requests.post(
    f"{BASE_URL}/log/submit",
    json={
        "user_id": TEST_USER_ID,
        "log": {
            "fruits_and_veggies": 6,
            "olive_oil": 25
        },
        "period_start": "2025-11-01",
        "period_end": "2025-11-15"
    }
).json())
print(f"Log ID: {log_result.get('log_id', 'N/A')}")
print(f"Adherence: {log_result.get('adherence', {})}")

# Step 9: Lifespan Predict
print_section("LIFESPAN PREDICT")
lifespan_result = test_step("Predict Lifespan", lambda: requests.post(
    f"{BASE_URL}/lifespan/predict",
    json={
        "user_id": TEST_USER_ID,
        "input": {
            "age": 30,
            "gender": 0,
            "fruits_and_veggies": 6,
            "dietary_fiber": 25
        }
    }
).json())
print(f"Lifespan: {lifespan_result.get('all_cause_mortality_predicted_lifespan', 'N/A')}")
print(f"Cancer RR: {lifespan_result.get('cancer_predicted_rr', 'N/A')}")
print(f"Cardio RR: {lifespan_result.get('cardio_vascular_disease_predicted_rr', 'N/A')}")

# Step 10: Get User Vars
print_section("GET USER VARS")
user_vars = test_step("Get User Vars", lambda: requests.get(
    f"{BASE_URL}/user/vars?user_id={TEST_USER_ID}"
).json())
print(f"Vars Extracted: {user_vars.get('vars_extracted', {})}")
print(f"Target Plan (sample): {dict(list(user_vars.get('target_plan', {}).items())[:3])}")

print_section("PIPELINE TEST COMPLETE")
print(f"\n✓ All steps executed")
print(f"Test User ID: {TEST_USER_ID}")
print("\nNote: Check responses above to verify:")
print("  1. Variables are properly extracted (not empty)")
print("  2. Suggested plan is generated (not just optimal plan)")
print("  3. Lifespan projection is returned")
print("  4. No dummy workarounds or silent failures")

