"""Configuration and constants."""
import os
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv("secrets.env")
load_dotenv(".env")  # Also try .env file

# Optimal plan values (matching prediction API variables)
# Note: stroke_predicted_rr is an output, not an input variable
OPTIMAL_PLAN: Dict[str, Any] = {
    "alcohol": 0,
    "artificial_sweetener": 0,
    "calcium": 0,
    "calorie_restriction": 1,
    "cardio": 35.4955,
    "dairy": 3.7126,
    "dietary_fiber": 60,
    "fat_trans": 0,
    "fish_oil_omega_3": 1.8869,
    "fruits_and_veggies": 8.4319,
    "grain_refined": 0,
    "grain_unrefined": 2.8861,
    "green_tea": 1116.753,
    "legumes": 6.0511,
    "meat_poultry": 0,
    "meat_processed": 0,
    "meat_unprocessed": 0,
    "multi_vitamins": 1,
    "olive_oil": 50,
    "refined_sugar": 0,
    "sauna_duration": 38.2,
    "sauna_frequency": 3.034,
    "sleep_duration": 7,
    "strength_training": 96.4597,
    "vitamin_e": 1000,
    "water": 1901.2292,
}

# Canonical variable schema (all possible keys - matches frontend PlanVariables)
# Total: 42 variables (prediction API works on 28, but we support all for feature extraction)
CANONICAL_VARIABLES = {
    # Prediction API variables (28)
    "alcohol", "calorie_restriction", "dairy", "fat_trans", "grain_refined",
    "grain_unrefined", "legumes", "meat_processed", "meat_unprocessed",
    "meat_poultry", "fruits_and_veggies", "water", "refined_sugar",
    "artificial_sweetener", "cardio", "strength_training", "sleep_duration",
    "sauna_duration", "sauna_frequency",
    "multi_vitamins", "vitamin_e", "calcium", "dietary_fiber",
    "fish_oil_omega_3", "green_tea", "olive_oil",
    # Additional variables for feature extraction (not in prediction API)
    "protein_supplements", "magnesium", "vitamin_a", "vitamin_k", "vitamin_d",
    "folic_acid", "vitamin_b6", "vitamin_b12", "zinc", "iron", "vitamin_c",
    # Profile variables
    "gender", "age", "name"
}

# Category keys for adherence calculation
DIET_KEYS = {
    "fruits_and_veggies", "dietary_fiber", "olive_oil", "grain_unrefined",
    "grain_refined", "legumes", "dairy", "refined_sugar", "artificial_sweetener",
    "alcohol", "meat_processed", "meat_unprocessed", "meat_poultry", "fat_trans"
}

SUPPLEMENT_KEYS = {
    "multi_vitamins", "vitamin_e", "fish_oil_omega_3", "calcium",
    "green_tea", "dietary_fiber", "olive_oil"
}

# Variable groups for constraint extraction and conversational flow
VARIABLE_GROUPS = {
    "supplements": {
        "multi_vitamins", "dietary_fiber", "protein_supplements", "magnesium",
        "vitamin_a", "vitamin_k", "vitamin_d", "folic_acid", "vitamin_b6",
        "vitamin_b12", "vitamin_e", "zinc", "calcium", "iron", "olive_oil",
        "fish_oil_omega_3", "green_tea", "vitamin_c"
    },
    "diet": {
        "alcohol", "dairy", "grain_refined", "grain_unrefined", "fruits_and_veggies",
        "legumes", "meat_processed", "meat_unprocessed", "meat_poultry",
        "refined_sugar", "artificial_sweetener", "fat_trans", "calorie_restriction"
    },
    "lifestyle": {
        "cardio", "strength_training", "sauna_duration", "sauna_frequency", "water",
        "sleep_duration"
    }
}

# Variable tags for constraint mapping
VARIABLE_TAGS = {
    # Supplement variables
    "multi_vitamins": ["supplement"],
    "vitamin_a": ["supplement"],
    "vitamin_k": ["supplement"],
    "vitamin_d": ["supplement"],
    "folic_acid": ["supplement"],
    "vitamin_b6": ["supplement"],
    "vitamin_b12": ["supplement"],
    "vitamin_e": ["supplement"],
    "vitamin_c": ["supplement"],
    "zinc": ["supplement"],
    "calcium": ["supplement"],
    "iron": ["supplement"],
    "magnesium": ["supplement"],
    "protein_supplements": ["supplement"],
    "fish_oil_omega_3": ["supplement"],
    "green_tea": ["supplement"],
    "dietary_fiber": ["supplement", "diet"],  # Can be both
    "olive_oil": ["supplement", "diet"],  # Can be both
    # Meat variables
    "meat_processed": ["meat", "non_veg"],
    "meat_unprocessed": ["meat", "non_veg"],
    "meat_poultry": ["meat", "non_veg"],
    # Refined grains
    "grain_refined": ["refined_grains"],
}

# Environment variables
# Handle OPENAI_API_KEY from secrets.env (may have spaces around =)
openai_key_raw = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_KEY = openai_key_raw.strip() if openai_key_raw else ""

# If not found, try reading from secrets.env directly
if not OPENAI_API_KEY:
    try:
        with open("secrets.env", "r") as f:
            for line in f:
                if line.startswith("OPENAI_API_KEY"):
                    OPENAI_API_KEY = line.split("=", 1)[1].strip()
                    break
    except Exception:
        pass

LIFESPAN_API_URL = os.getenv(
    "LIFESPAN_API_URL",
    "https://mlmodel.myyouthspan.com/prediction_model_test/"
)
FIRESTORE_CREDENTIALS = os.getenv(
    "FIRESTORE_CREDENTIALS",
    "firebase-credentials_prod.json"
)

