"""Prediction API service."""
from typing import Dict, Any
import requests
import config


def call_lifespan_api(plan_obj: Dict[str, Any]) -> Dict[str, Any]:
    """
    Call the lifespan prediction API.
    Only sends variables that have values (no defaults needed per spec).
    """
    try:
        resp = requests.post(
            config.LIFESPAN_API_URL,
            json=plan_obj,
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        return {
            "error": str(e),
            "success": False
        }

