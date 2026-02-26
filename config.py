# import os
# from typing import Dict, Any
# from dotenv import load_dotenv
# load_dotenv("secrets.env")
# load_dotenv(".env")
# os.getenv("OPENAI_API_KEY")

# os.environ["OPENAI_API_KEY"] = OPEN_API_KEY
# OPTIMAL_PLAN: Dict[str, Any] = {
#     "alcohol": 0,
#     "artificial_sweetener": 0,
#     "calcium": 0,
#     "calorie_restriction": 1,
#     "cardio": 35.4955,
#     "dairy": 3.7126,
#     "dietary_fiber": 60,
#     "fat_trans": 0,
#     "fish_oil_omega_3": 1.8869,
#     "fruits_and_veggies": 8.4319,
#     "grain_refined": 0,
#     "grain_unrefined": 2.8861,
#     "green_tea": 1116.753,
#     "legumes": 6.0511,
#     "meat_poultry": 0,
#     "meat_processed": 0,
#     "meat_unprocessed": 0,
#     "multi_vitamins": 1,
#     "olive_oil": 50,
#     "refined_sugar": 0,
#     "sauna_duration": 38.2,
#     "sauna_frequency": 3.034,
#     "sleep_duration": 7,
#     "strength_training": 96.4597,
#     "vitamin_e": 1000,
#     "water": 1901.2292,
# }

# CANONICAL_VARIABLES = {
#     "alcohol", "calorie_restriction", "dairy", "fat_trans", "grain_refined",
#     "grain_unrefined", "legumes", "meat_processed", "meat_unprocessed",
#     "meat_poultry", "fruits_and_veggies", "water", "refined_sugar",
#     "artificial_sweetener", "cardio", "strength_training", "sleep_duration",
#     "sauna_duration", "sauna_frequency",
#     "multi_vitamins", "vitamin_e", "calcium", "dietary_fiber",
#     "fish_oil_omega_3", "green_tea", "olive_oil",
#     "protein_supplements", "magnesium", "vitamin_a", "vitamin_k", "vitamin_d",
#     "folic_acid", "vitamin_b6", "vitamin_b12", "zinc", "iron", "vitamin_c",
#     "gender", "age", "name"
# }

# DIET_KEYS = {
#     "fruits_and_veggies", "dietary_fiber", "olive_oil", "grain_unrefined",
#     "grain_refined", "legumes", "dairy", "refined_sugar", "artificial_sweetener",
#     "alcohol", "meat_processed", "meat_unprocessed", "meat_poultry", "fat_trans"
# }

# SUPPLEMENT_KEYS = {
#     "multi_vitamins", "vitamin_e", "fish_oil_omega_3", "calcium",
#     "green_tea", "dietary_fiber", "olive_oil"
# }

# VARIABLE_GROUPS = {
#     "supplements": {
#         "multi_vitamins", "dietary_fiber", "protein_supplements", "magnesium",
#         "vitamin_a", "vitamin_k", "vitamin_d", "folic_acid", "vitamin_b6",
#         "vitamin_b12", "vitamin_e", "zinc", "calcium", "iron", "olive_oil",
#         "fish_oil_omega_3", "green_tea", "vitamin_c"
#     },
#     "diet": {
#         "alcohol", "dairy", "grain_refined", "grain_unrefined", "fruits_and_veggies",
#         "legumes", "meat_processed", "meat_unprocessed", "meat_poultry",
#         "refined_sugar", "artificial_sweetener", "fat_trans", "calorie_restriction"
#     },
#     "lifestyle": {
#         "cardio", "strength_training", "sauna_duration", "sauna_frequency", "water",
#         "sleep_duration"
#     }
# }

# VARIABLE_TAGS = {
#     "multi_vitamins": ["supplement"],
#     "vitamin_a": ["supplement"],
#     "vitamin_k": ["supplement"],
#     "vitamin_d": ["supplement"],
#     "folic_acid": ["supplement"],
#     "vitamin_b6": ["supplement"],
#     "vitamin_b12": ["supplement"],
#     "vitamin_e": ["supplement"],
#     "vitamin_c": ["supplement"],
#     "zinc": ["supplement"],
#     "calcium": ["supplement"],
#     "iron": ["supplement"],
#     "magnesium": ["supplement"],
#     "protein_supplements": ["supplement"],
#     "fish_oil_omega_3": ["supplement"],
#     "green_tea": ["supplement"],
#     "dietary_fiber": ["supplement", "diet"],
#     "olive_oil": ["supplement", "diet"],
#     "meat_processed": ["meat", "non_veg"],
#     "meat_unprocessed": ["meat", "non_veg"],
#     "meat_poultry": ["meat", "non_veg"],
#     "grain_refined": ["refined_grains"],
# }

# openai_key_raw = os.getenv("OPENAI_API_KEY", "")
# OPENAI_API_KEY = openai_key_raw.strip() if openai_key_raw else ""
# if not OPENAI_API_KEY:
#     try:
#         with open("secrets.env", "r") as f:
#             for line in f:
#                 if line.startswith("OPENAI_API_KEY"):
#                     OPENAI_API_KEY = line.split("=", 1)[1].strip()
#                     break
#     except Exception:
#         pass

# LIFESPAN_API_URL = os.getenv(
#     "LIFESPAN_API_URL",
#     "https://mlmodel.myyouthspan.com/prediction_model_test/"
# )
# FIRESTORE_CREDENTIALS = os.getenv(
#     "FIRESTORE_CREDENTIALS",
#     "firebase-credentials_prod.json"
# )

"""
Configuration and constants for METY Chatbot Backend
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv

# ---------------------------------------------------
# Load environment variables (optional support)
# ---------------------------------------------------

load_dotenv("secrets.env")
load_dotenv(".env")

# ---------------------------------------------------
# 🔐 OPENAI CONFIG (INLINE KEY - TEMPORARY)
# ---------------------------------------------------

# ⚠️ You are intentionally keeping it inline for now.
# Replace with env variable later before production.
os.getenv("OPENAI_API_KEY")

# Ensure it is available in os.environ for other modules
# os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY


# ---------------------------------------------------
# Firestore Credentials
# ---------------------------------------------------

FIRESTORE_CREDENTIALS = os.getenv(
    "FIRESTORE_CREDENTIALS",
    "firebase-credentials_prod.json"
)


# ---------------------------------------------------
# Lifespan Prediction API
# ---------------------------------------------------

LIFESPAN_API_URL = os.getenv(
    "LIFESPAN_API_URL",
    "https://mlmodel.myyouthspan.com/prediction_model_test/"
)


# ---------------------------------------------------
# Chat Rate Limit (seconds)
# ---------------------------------------------------

try:
    CHAT_RATE_LIMIT_SECONDS = float(os.getenv("CHAT_RATE_LIMIT_SECONDS", "4"))
except ValueError:
    CHAT_RATE_LIMIT_SECONDS = 4.0


# ---------------------------------------------------
# Optimal Plan Values
# ---------------------------------------------------

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


# ---------------------------------------------------
# Canonical Variables
# ---------------------------------------------------

CANONICAL_VARIABLES = {
    "alcohol", "calorie_restriction", "dairy", "fat_trans", "grain_refined",
    "grain_unrefined", "legumes", "meat_processed", "meat_unprocessed",
    "meat_poultry", "fruits_and_veggies", "water", "refined_sugar",
    "artificial_sweetener", "cardio", "strength_training", "sleep_duration",
    "sauna_duration", "sauna_frequency",
    "multi_vitamins", "vitamin_e", "calcium", "dietary_fiber",
    "fish_oil_omega_3", "green_tea", "olive_oil",
    "protein_supplements", "magnesium", "vitamin_a", "vitamin_k", "vitamin_d",
    "folic_acid", "vitamin_b6", "vitamin_b12", "zinc", "iron", "vitamin_c",
    "gender", "age", "name"
}


# ---------------------------------------------------
# Variable Groups
# ---------------------------------------------------

VARIABLE_GROUPS = {
    "supplements": {
        "multi_vitamins", "dietary_fiber", "protein_supplements", "magnesium",
        "vitamin_a", "vitamin_k", "vitamin_d", "folic_acid", "vitamin_b6",
        "vitamin_b12", "vitamin_e", "zinc", "calcium", "iron", "olive_oil",
        "fish_oil_omega_3", "green_tea", "vitamin_c"
    },
    "diet": {
        "alcohol", "dairy", "grain_refined", "grain_unrefined",
        "fruits_and_veggies", "legumes", "meat_processed",
        "meat_unprocessed", "meat_poultry",
        "refined_sugar", "artificial_sweetener",
        "fat_trans", "calorie_restriction"
    },
    "lifestyle": {
        "cardio", "strength_training", "sauna_duration",
        "sauna_frequency", "water", "sleep_duration"
    }
}


# ---------------------------------------------------
# Variable Tags
# ---------------------------------------------------

VARIABLE_TAGS = {
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
    "dietary_fiber": ["supplement", "diet"],
    "olive_oil": ["supplement", "diet"],
    "meat_processed": ["meat", "non_veg"],
    "meat_unprocessed": ["meat", "non_veg"],
    "meat_poultry": ["meat", "non_veg"],
    "grain_refined": ["refined_grains"],
}
