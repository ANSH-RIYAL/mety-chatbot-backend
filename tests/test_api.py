"""Test script for API endpoints."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
import json

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing /health...")
    resp = requests.get(f"{BASE_URL}/health")
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}\n")

def test_onboarding():
    """Test onboarding submit."""
    print("Testing /onboarding/submit...")
    data = {
        "user_id": "test_user_123",
        "page": "About Me",
        "payload": {
            "name": "Test User",
            "age": 30,
            "gender": 0,
            "stress_quality": 1,
            "sleep_quality": 2
        }
    }
    resp = requests.post(f"{BASE_URL}/onboarding/submit", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.json()}\n")

def test_plan_get():
    """Test plan get."""
    print("Testing /plan/get...")
    resp = requests.get(f"{BASE_URL}/plan/get?user_id=test_user_123")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")

def test_plan_update():
    """Test plan update."""
    print("Testing /plan/update...")
    data = {
        "user_id": "test_user_123",
        "diff": {
            "fruits_and_veggies": 7,
            "olive_oil": 30
        }
    }
    resp = requests.post(f"{BASE_URL}/plan/update", json=data)
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")

def test_chat():
    """Test chat endpoint."""
    print("Testing /chat...")
    data = {
        "user_id": "test_user_123",
        "messages": [
            {"role": "user", "text": "I don't want Vitamin A"},
            {"role": "user", "text": "I'll eat 6 servings of fruits per day"}
        ],
        "options": {
            "auto_apply_extracted_vars": False,
            "recent_plan_snapshot": {}
        }
    }
    resp = requests.post(f"{BASE_URL}/chat", json=data)
    print(f"Status: {resp.status_code}")
    response_data = resp.json()
    print(f"Assistant message: {response_data.get('assistant_message', '')[:100]}...")
    print(f"Vars extracted: {response_data.get('vars_extracted', {})}")
    print(f"Diff detected: {response_data.get('diff_detected', {})}\n")

def test_user_vars():
    """Test user vars endpoint."""
    print("Testing /user/vars...")
    resp = requests.get(f"{BASE_URL}/user/vars?user_id=test_user_123")
    print(f"Status: {resp.status_code}")
    print(f"Response: {json.dumps(resp.json(), indent=2)}\n")

if __name__ == "__main__":
    print("=" * 50)
    print("API Testing")
    print("=" * 50)
    print()
    
    try:
        test_health()
        test_onboarding()
        test_plan_get()
        test_plan_update()
        test_user_vars()
        test_chat()
        print("All tests completed!")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Make sure the server is running on localhost:8000")
    except Exception as e:
        print(f"ERROR: {e}")

