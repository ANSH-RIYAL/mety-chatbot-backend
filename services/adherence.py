from typing import Dict, Any, Optional
import math
import config


# Negative features where less is better (ideal is often 0)
NEGATIVE_FEATURES = {
    'alcohol',
    'cigarettes',
    'refined_sugar',
    'artificial_sweetener',
    'fat_trans',
    'grain_refined',
    'meat_unprocessed',
    'meat_processed',
    'meat_poultry',
}


def _build_values_dict() -> Dict[str, Dict[str, float]]:
    """
    Build values_dict structure with optimum and fallback values.
    Uses config.OPTIMAL_PLAN for optimum values and defines fallback values
    for negative features based on typical disease model data.
    """
    values_dict = {}
    
    # Initialize with optimum values from config
    for key, optimum in config.OPTIMAL_PLAN.items():
        values_dict[key] = {
            "optimum": float(optimum),
            "fallback": None
        }
    
    # Set fallback values for negative features
    fallback_values = {
        'alcohol': 6.0,
        'cigarettes': 7.0,
        'grain_refined': 0.5,
        'meat_unprocessed': 2.0,
        'meat_processed': 2.0,
        'meat_poultry': 2.0,
        'refined_sugar': 28.0,  # g/day
        'artificial_sweetener': 140.0,  # mg/day
        'fat_trans': 6.5,  # g/day
    }
    
    for key, fallback in fallback_values.items():
        if key in values_dict:
            values_dict[key]['fallback'] = fallback
    
    return values_dict


def _calc_adherence_to_plan(
    feature: str,
    user_plan: float,
    user_value: float,
    values_dict: Dict[str, Dict[str, float]],
    is_positive_feature: bool = True
) -> Optional[float]:
    """
    Calculate adherence for a single feature & user.
    
    For positive features: more (up to optimum) is better.
    For negative features: less is better (ideal is plan, often 0).
    
    Returns:
        adherence (float in [0,1]) or None if plan/value are invalid.
    """
    if feature not in values_dict:
        return None
    
    optimum = values_dict[feature]['optimum']
    fallback = values_dict[feature]['fallback']
    plan = user_plan
    
    # Handle missing or invalid values
    if user_value is None or plan is None:
        return None
    if math.isnan(user_value) or math.isnan(plan):
        return None
    
    # Positive feature logic
    if is_positive_feature:
        if plan <= 0:
            return 0.0
        
        if user_value <= plan:
            adherence = user_value / plan
        elif user_value <= optimum:
            adherence = 1.0
        else:
            delta = user_value - optimum
            if optimum <= 0:
                return 0.0
            adherence = 1.0 - (delta / optimum)
    
    # Negative feature logic
    else:
        if (fallback is None) or math.isnan(fallback) or fallback == 0:
            fallback = 1.0
        
        if user_value <= plan:
            adherence = 1.0
        else:
            delta = user_value - plan
            adherence = 1.0 - (delta / fallback)
    
    return float(max(0.0, min(1.0, adherence)))


def calculate_adherence(
    logged_values: Dict[str, float],
    target_values: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate adherence metrics comparing logged values against target plan values.
    
    This function computes adherence percentages for diet, exercise, supplement, and lifestyle
    categories by comparing actual logged values against the user's target plan. The adherence
    calculation uses sophisticated logic that handles:
    - Positive features: rewards values up to plan, full adherence between plan and optimum,
      and penalizes exceeding optimum
    - Negative features: full adherence when ≤ plan, with penalties based on fallback values
    
    The function calculates adherence for all 4 categories (diet, exercise, supplement, lifestyle)
    and returns:
    - diet_adherence: Mean adherence for diet-related variables
    - supplement_adherence: Mean adherence for supplement-related variables  
    - total_adherence: Overall mean of all 4 categories (diet, exercise, supplement, lifestyle)
    
    All adherence values are clamped to [0, 1] range.
    """
    # Build values_dict once
    values_dict = _build_values_dict()
    
    # Calculate per-feature adherence
    feature_adherence = {}
    
    for feature in logged_values.keys():
        if feature not in target_values:
            continue
        if feature not in values_dict:
            continue
        
        user_value = logged_values[feature]
        user_plan = target_values[feature]
        
        is_positive = feature not in NEGATIVE_FEATURES
        adherence = _calc_adherence_to_plan(
            feature,
            user_plan,
            user_value,
            values_dict,
            is_positive_feature=is_positive
        )
        
        if adherence is not None:
            feature_adherence[feature] = adherence
    
    # Define category feature lists (matching reference file)
    diet_features = [
        'meat_processed', 'meat_unprocessed', 'meat_poultry',
        'fruits_and_veggies', 'dairy', 'grain_refined', 'grain_unrefined',
        'legumes', 'fat_trans', 'refined_sugar', 'artificial_sweetener',
        'olive_oil', 'dietary_fiber'
    ]
    
    exercise_features = [
        'cardio', 'strength_training'
    ]
    
    supplement_features = [
        'multi_vitamins', 'vitamin_e', 'fish_oil_omega_3', 'calcium'
    ]
    
    lifestyle_features = [
        'sleep_duration', 'sauna_duration', 'sauna_frequency',
        'cigarettes', 'alcohol', 'water', 'calorie_restriction'
    ]
    
    # Calculate category-level adherence
    def get_category_adherence(feature_list):
        """Get list of adherence values for features in the category."""
        adherences = []
        for key in feature_list:
            if key in feature_adherence:
                adherences.append(feature_adherence[key])
        return adherences
    
    diet_adherences = get_category_adherence(diet_features)
    exercise_adherences = get_category_adherence(exercise_features)
    supplement_adherences = get_category_adherence(supplement_features)
    lifestyle_adherences = get_category_adherence(lifestyle_features)
    
    # Calculate mean adherence per category (use None for empty categories to match reference logic)
    diet_adherence = sum(diet_adherences) / len(diet_adherences) if diet_adherences else None
    exercise_adherence = sum(exercise_adherences) / len(exercise_adherences) if exercise_adherences else None
    supplement_adherence = sum(supplement_adherences) / len(supplement_adherences) if supplement_adherences else None
    lifestyle_adherence = sum(lifestyle_adherences) / len(lifestyle_adherences) if lifestyle_adherences else None
    
    # Calculate total adherence as mean of all 4 categories (skip None values, matching reference skipna=True)
    category_adherences = [
        diet_adherence, 
        exercise_adherence,
        supplement_adherence,
        lifestyle_adherence
    ]
    # Filter out None values (categories with no features) for mean calculation
    valid_categories = [adj for adj in category_adherences if adj is not None]
    total_adherence = sum(valid_categories) / len(valid_categories) if valid_categories else 0.0
    
    # Convert None to 0.0 for return values (only diet and supplement are returned)
    diet_adherence = diet_adherence if diet_adherence is not None else 0.0
    supplement_adherence = supplement_adherence if supplement_adherence is not None else 0.0
    
    return {
        "total": round(total_adherence, 2),
        "diet": round(diet_adherence, 2),
        "supplement": round(supplement_adherence, 2)
    }
