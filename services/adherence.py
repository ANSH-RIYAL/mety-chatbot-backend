"""Adherence calculation service."""
from typing import Dict, Any
import config


def calculate_adherence(
    logged_values: Dict[str, float],
    target_values: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate adherence metrics.
    Returns: {"total": float, "diet": float, "supplement": float}
    """
    # Diet adherence
    diet_values = []
    for key in config.DIET_KEYS:
        if key in logged_values and key in target_values and target_values[key] > 0:
            ratio = logged_values[key] / target_values[key]
            diet_values.append(min(ratio, 1.0))  # Cap at 1.0
    
    diet_adherence = sum(diet_values) / len(diet_values) if diet_values else 0.0
    
    # Supplement adherence
    supplement_values = []
    for key in config.SUPPLEMENT_KEYS:
        if key in logged_values and key in target_values and target_values[key] > 0:
            ratio = logged_values[key] / target_values[key]
            supplement_values.append(min(ratio, 1.0))
    
    supplement_adherence = sum(supplement_values) / len(supplement_values) if supplement_values else 0.0
    
    # Total adherence (overall mean)
    all_values = diet_values + supplement_values
    total_adherence = sum(all_values) / len(all_values) if all_values else 0.0
    
    return {
        "total": round(total_adherence, 2),
        "diet": round(diet_adherence, 2),
        "supplement": round(supplement_adherence, 2)
    }

