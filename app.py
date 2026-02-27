import os
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from datetime import datetime
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import config
from services.firestore_service import firestore_service
from services.llm_service import (
    extract_variables_from_text,
    extract_constraints_from_conversation,
    generate_plan_diffs_with_constraints,
    generate_assistant_reply,
    merge_extracted_vars_to_diff
)
from services.prediction_api import call_lifespan_api
from services.adherence import calculate_adherence

app = FastAPI(title="Chatbot Assistant Platform API")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIST_DIR = os.path.join(BASE_DIR, "final_frontend", "dist")
if os.path.isdir(FRONTEND_DIST_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST_DIR, html=True), name="frontend")

@app.get("/")
def serve_frontend_index():
    index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if not os.path.exists(index_path):
        raise HTTPException(status_code=404, detail="Frontend dist/index.html not found")
    return FileResponse(index_path)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OnboardingPayload(BaseModel):
    name: Optional[str] = None
    age: Optional[float] = None
    gender: Optional[int] = None
    multi_vitamins: Optional[float] = None
    dietary_fiber: Optional[float] = None
    protein_supplements: Optional[float] = None
    magnesium: Optional[float] = None
    vitamin_a: Optional[float] = None
    vitamin_k: Optional[float] = None
    vitamin_d: Optional[float] = None
    folic_acid: Optional[float] = None
    vitamin_b6: Optional[float] = None
    vitamin_b12: Optional[float] = None
    vitamin_e: Optional[float] = None
    zinc: Optional[float] = None
    calcium: Optional[float] = None
    iron: Optional[float] = None
    olive_oil: Optional[float] = None
    fish_oil_omega_3: Optional[float] = None
    green_tea: Optional[float] = None
    vitamin_c: Optional[float] = None
    alcohol: Optional[float] = None
    dairy: Optional[float] = None
    grain_refined: Optional[float] = None
    grain_unrefined: Optional[float] = None
    fruits_and_veggies: Optional[float] = None
    legumes: Optional[float] = None
    meat_processed: Optional[float] = None
    meat_unprocessed: Optional[float] = None
    meat_poultry: Optional[float] = None
    refined_sugar: Optional[float] = None
    artificial_sweetener: Optional[float] = None
    cardio: Optional[float] = None
    strength_training: Optional[float] = None
    sauna_duration: Optional[float] = None
    sauna_frequency: Optional[float] = None
    water: Optional[float] = None


class OnboardingRequest(BaseModel):
    user_id: str
    page: str
    payload: OnboardingPayload
    timestamp: Optional[str] = None


class PlanUpdateRequest(BaseModel):
    user_id: str
    diff: Dict[str, float]
    timestamp: Optional[str] = None


class LogSubmitRequest(BaseModel):
    user_id: str
    log: Dict[str, float]
    period_start: str
    period_end: str


class LifespanPredictRequest(BaseModel):
    user_id: str
    input: Dict[str, float]


class ChatOptions(BaseModel):
    auto_apply_extracted_vars: bool = False


class ChatRequest(BaseModel):
    user_id: str
    message: str  # Only the latest message
    options: ChatOptions
    timestamp: Optional[str] = None


def _ensure_user_exists(user_id: str) -> None:
    user = firestore_service.get_user(user_id)
    if not user:
        base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
        optimal_plan = base_plan.copy()
        optimal_plan.update(config.OPTIMAL_PLAN)
        
        firestore_service.create_user(user_id, {
            "profile": {},
            "current_plan": {},
            "target_plan": {},
            "optimal_plan": optimal_plan.copy(),
            "vars_extracted": {},
            "last_updated": datetime.utcnow().isoformat()
        })
    else:
        current = user.get("current_plan", {})
        target = user.get("target_plan", {})
        needs_reset = False
        for key, value in list(current.items()):
            if key in config.OPTIMAL_PLAN and value == config.OPTIMAL_PLAN[key]:
                del current[key]
                needs_reset = True
        for key, value in list(target.items()):
            if key in config.OPTIMAL_PLAN and value == config.OPTIMAL_PLAN[key]:
                del target[key]
                needs_reset = True
        
        if needs_reset:
            if current:
                firestore_service.update_user_plan(user_id, "current_plan", current)
            if target:
                firestore_service.update_user_plan(user_id, "target_plan", target)


@app.get("/health")
def health():
    return {"status": "ok", "service": "Chatbot Assistant Platform"}


@app.get("/debug/firestore")
def debug_firestore():
    """Check Firestore connection status - use this to diagnose issues on deployed URL."""
    result = {
        "firestore_enabled": firestore_service.firestore_enabled,
        "credentials_file_path": config.FIRESTORE_CREDENTIALS,
        "credentials_file_exists": os.path.exists(config.FIRESTORE_CREDENTIALS),
        "env_GCP_PROJECT_ID": os.getenv("GCP_PROJECT_ID", "NOT SET"),
        "env_GOOGLE_CLOUD_PROJECT": os.getenv("GOOGLE_CLOUD_PROJECT", "NOT SET"),
        "env_GOOGLE_APPLICATION_CREDENTIALS": os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "NOT SET"),
    }
    
    if firestore_service.firestore_enabled and firestore_service.db:
        try:
            collections = [c.id for c in firestore_service.db.collections()]
            result["connection_test"] = "SUCCESS"
            result["collections_found"] = collections
        except Exception as e:
            result["connection_test"] = f"FAILED: {str(e)}"
    else:
        result["connection_test"] = "SKIPPED - Firestore not enabled"
    
    return result


@app.post("/onboarding/submit")
def onboarding_submit(request: OnboardingRequest):
    _ensure_user_exists(request.user_id)
    payload_dict = request.payload.dict(exclude_none=True)
    payload_dict.pop("sleep_quality", None)
    payload_dict.pop("stress_quality", None)
    user = firestore_service.get_user(request.user_id)
    profile = user.get("profile", {}) if user else {}
    profile_data = {k: v for k, v in payload_dict.items() if k in ["name", "age", "gender"]}
    if profile_data:
        profile.update(profile_data)
        firestore_service.update_user_profile(request.user_id, profile)
    plan_data = {k: v for k, v in payload_dict.items() if k not in ["name", "age", "gender"]}
    if plan_data:
        new_current_plan = {}
        for key, value in plan_data.items():
            if key in config.CANONICAL_VARIABLES:
                try:
                    new_current_plan[key] = float(value)
                except (ValueError, TypeError):
                    pass
        existing_current = user.get("current_plan", {}) if user else {}
        existing_current.update(new_current_plan)
        firestore_service.update_user_plan(request.user_id, "current_plan", existing_current)
    
    return {"ok": True, "saved_doc": f"users/{request.user_id}"}


@app.get("/plan/get")
def plan_get(user_id: str = Query(...)):
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)
    optimal_plan = user.get("optimal_plan", config.OPTIMAL_PLAN) if user else config.OPTIMAL_PLAN.copy()
    stored_current = user.get("current_plan", {}) if user else {}
    stored_target = user.get("target_plan", {}) if user else {}
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    current_plan_full = base_plan.copy()
    for key, value in stored_current.items():
        if key in config.CANONICAL_VARIABLES:
            current_plan_full[key] = float(value)
    target_plan_full = base_plan.copy()
    for key, value in stored_target.items():
        if key in config.CANONICAL_VARIABLES:
            target_plan_full[key] = float(value)
    optimal_plan_full = base_plan.copy()
    optimal_plan_full.update(optimal_plan)

    return {
        "user_id": user_id,
        "profile": user.get("profile", {}) if user else {},
        "current_plan": current_plan_full,
        "target_plan": target_plan_full,
        "optimal_plan": optimal_plan_full,
        "last_updated": user.get("last_updated", datetime.utcnow().isoformat()) if user else datetime.utcnow().isoformat()
    }


@app.post("/plan/update")
def plan_update(request: PlanUpdateRequest):
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)
    unknown_keys = [k for k in request.diff.keys() if k not in config.CANONICAL_VARIABLES]
    if unknown_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown keys: {unknown_keys}"
        )
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    current_target = user.get("target_plan", {}) if user else {}
    target_plan = {}
    for key, value in current_target.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                target_plan[key] = float(value)
            except (ValueError, TypeError):
                pass
    for key, value in request.diff.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                target_plan[key] = float(value)
            except (ValueError, TypeError):
                pass
    for key in target_plan:
        try:
            target_plan[key] = float(target_plan[key])
        except (ValueError, TypeError):
            target_plan[key] = 0.0
    target_plan_to_save = {}
    for key, value in target_plan.items():
        if value != 0 and value is not None:
            target_plan_to_save[key] = value
    print(f"[PLAN UPDATE] Saving target_plan with {len(target_plan_to_save)} non-zero values:")
    print(f"[PLAN UPDATE] Keys: {list(target_plan_to_save.keys())}")
    print(f"[PLAN UPDATE] Sample values: {dict(list(target_plan_to_save.items())[:5])}")
    firestore_service.update_user_plan(request.user_id, "target_plan", target_plan_to_save)
    user_after = firestore_service.get_user(request.user_id)
    saved_target = user_after.get("target_plan", {}) if user_after else {}
    print(f"[PLAN UPDATE] After save, target_plan has {len(saved_target)} keys")
    print(f"[PLAN UPDATE] Saved keys: {list(saved_target.keys())[:10]}")
    firestore_service.log_plan_change(
        request.user_id,
        request.diff,
        source="ui"
    )
    
    return {
        "ok": True,
        "new_target_plan": target_plan,
        "applied_diff": request.diff
    }


@app.post("/plan/apply-target-to-current")
def plan_apply_target_to_current(user_id: str = Query(...)):
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)
    stored_target = user.get("target_plan", {}) if user else {}
    if not stored_target:
        return {"ok": True, "message": "Target plan is empty, nothing to apply"}
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    stored_current = user.get("current_plan", {}) if user else {}
    full_target_plan = base_plan.copy()
    for key, value in stored_target.items():
        if key in config.CANONICAL_VARIABLES:
            full_target_plan[key] = float(value)
    full_current_plan = base_plan.copy()
    for key, value in stored_current.items():
        if key in config.CANONICAL_VARIABLES:
            full_current_plan[key] = float(value)
    diff = {}
    for key in config.CANONICAL_VARIABLES:
        current_val = full_current_plan.get(key, 0)
        target_val = full_target_plan.get(key, 0)
        if target_val != current_val:
            diff[key] = target_val
    new_current_plan_to_save = {}
    for key, value in full_target_plan.items():
        if value != 0 and value is not None:
            new_current_plan_to_save[key] = value
    firestore_service.update_user_plan(user_id, "current_plan", new_current_plan_to_save)
    if diff:
        firestore_service.log_plan_change(user_id, diff, source="apply_target_to_current")
    firestore_service.update_user_plan(user_id, "target_plan", {})
    
    return {"ok": True, "message": "Target plan applied to current plan"}


@app.post("/chat/clear")
def chat_clear(user_id: str = Query(...)):
    _ensure_user_exists(user_id)
    firestore_service.clear_chat_history(user_id)
    
    return {"ok": True, "message": "Chat history cleared"}


@app.post("/log/submit")
def log_submit(request: LogSubmitRequest):
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)
    stored_target = user.get("target_plan", {}) if user else {}
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    target_plan = base_plan.copy()
    for key, value in stored_target.items():
        if key in config.CANONICAL_VARIABLES:
            target_plan[key] = float(value) 
    adherence = calculate_adherence(request.log, target_plan)
    log_id = firestore_service.save_log(
        request.user_id,
        request.log,
        request.period_start,
        request.period_end,
        adherence
    )
    
    return {
        "ok": True,
        "log_id": log_id,
        "adherence": adherence
    }


@app.post("/lifespan/predict")
def lifespan_predict(request: LifespanPredictRequest):
    result = call_lifespan_api(request.input)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@app.post("/chat")
def chat(request: ChatRequest):
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)
    firestore_service.persist_chat_message(
        request.user_id,
        "user",
        request.message
    )
    chat_history = firestore_service.get_chat_history(request.user_id, limit=50)
    all_messages = []
    for msg in chat_history:
        all_messages.append({
            "role": msg.get("role", "user"),
            "text": msg.get("text", "")
        })
    all_messages.append({
        "role": "user",
        "text": request.message
    })
    user_messages = [msg["text"] for msg in all_messages if msg["role"] == "user"][-2:]
    vars_extracted = {}
    for msg_text in user_messages:
        try:
            extracted = extract_variables_from_text(msg_text)
            vars_extracted.update(extracted)
        except Exception as e:
            print(f"Warning: Variable extraction failed: {e}")
    unknown_keys = [k for k in vars_extracted.keys() if k not in config.CANONICAL_VARIABLES]
    vars_extracted = {
        k: v for k, v in vars_extracted.items()
        if k in config.CANONICAL_VARIABLES
    }
    current_plan = user.get("current_plan", {}) if user else {}
    target_plan = user.get("target_plan", {}) if user else {}
    combined_target_current = current_plan.copy()
    combined_target_current.update(target_plan)
    diff_detected = merge_extracted_vars_to_diff(vars_extracted, combined_target_current)
    if vars_extracted:
        existing_vars = user.get("vars_extracted", {}) if user else {}
        existing_vars.update(vars_extracted)
        firestore_service.update_user_vars_extracted(request.user_id, existing_vars)
    current_plan = user.get("current_plan", {}) if user else {}
    target_plan = user.get("target_plan", {}) if user else {}
    optimal_plan = user.get("optimal_plan", config.OPTIMAL_PLAN) if user else config.OPTIMAL_PLAN.copy()
    combined_target_current = current_plan.copy()
    combined_target_current.update(target_plan)
    print(f"\n[DEBUG] Generating suggested plan for user {request.user_id}:")
    print(f"  current_plan keys: {len(current_plan)} (sample: {dict(list(current_plan.items())[:3])})")
    print(f"  target_plan keys: {len(target_plan)} (sample: {dict(list(target_plan.items())[:3])})")
    print(f"  combined_target_current keys: {len(combined_target_current)} (sample: {dict(list(combined_target_current.items())[:3])})")
    try:
        constraints = extract_constraints_from_conversation(all_messages)
    except Exception as e:
        print(f"Warning: Constraint extraction failed: {e}")
        constraints = {}
    conversation_text = " ".join([msg["text"] for msg in all_messages[-5:]])
    try:
        suggested_plan_diffs = generate_plan_diffs_with_constraints(
            combined_target_current,
            optimal_plan,
            constraints,
            conversation_text
        )
    except Exception as e:
        print(f"Warning: Plan generation failed: {e}")
        suggested_plan_diffs = {}
    lifespan_projection = {}
    if suggested_plan_diffs:
        full_suggested_plan = combined_target_current.copy()
        full_suggested_plan.update(suggested_plan_diffs)
        prediction_vars = [
            "alcohol", "calorie_restriction", "cardio", "dairy", "dietary_fiber",
            "fat_trans", "fish_oil_omega_3", "fruits_and_veggies", "gender",
            "grain_refined", "grain_unrefined", "green_tea", "legumes",
            "meat_poultry", "meat_processed", "meat_unprocessed", "multi_vitamins",
            "olive_oil", "refined_sugar", "artificial_sweetener", "sauna_duration",
            "sauna_frequency", "sleep_duration", "strength_training",
            "vitamin_e", "water", "age"
        ]
        prediction_input = {}
        for var in prediction_vars:
            val = full_suggested_plan.get(var)
            if val is not None and val != 0:
                prediction_input[var] = float(val)
        if "age" not in prediction_input:
            profile_data = user.get("profile", {}) if user else {}
            if profile_data.get("age"):
                prediction_input["age"] = float(profile_data["age"])
        if "gender" not in prediction_input:
            profile_data = user.get("profile", {}) if user else {}
            if profile_data.get("gender") is not None:
                prediction_input["gender"] = float(profile_data["gender"])
        if len(prediction_input) >= 2:
            projection = call_lifespan_api(prediction_input)
            if "error" not in projection:
                lifespan_projection = projection
    context_parts = []
    def calculate_alignment(plan_dict, optimal_dict, group_vars):
        if not plan_dict or not optimal_dict:
            return None
        ratios = []
        for var in group_vars:
            if var in optimal_dict and optimal_dict[var] != 0:
                current_val = plan_dict.get(var, 0)
                optimal_val = optimal_dict[var]
                if optimal_val > 0:
                    ratio = min(current_val / optimal_val, 1.0) if current_val >= 0 else 0
                    ratios.append(ratio)
        if ratios:
            return sum(ratios) / len(ratios)
        return None
    alignment_info = []
    for group_name, group_vars in config.VARIABLE_GROUPS.items():
        alignment = calculate_alignment(combined_target_current, optimal_plan, group_vars)
        if alignment is not None:
            if alignment >= 0.8:
                alignment_info.append(f"{group_name}: close to optimal ({alignment:.0%})")
            elif alignment <= 0.5:
                alignment_info.append(f"{group_name}: needs work ({alignment:.0%})")
    if alignment_info:
        context_parts.append(f"Plan alignment: {'; '.join(alignment_info)}")
    if constraints:
        context_parts.append(f"User constraints: {constraints}")
    if vars_extracted:
        context_parts.append(f"Recently mentioned: {vars_extracted}")
    context_prefix = "\n".join(context_parts) if context_parts else ""
    try:
        assistant_message = generate_assistant_reply(all_messages, context_prefix)
    except Exception as e:
        print(f"Error generating assistant reply: {e}")
        assistant_message = "I understand your preferences. Let me help you adjust your plan."
    firestore_service.persist_chat_message(
        request.user_id,
        "assistant",
        assistant_message
    )
    actions = []
    if diff_detected and not request.options.auto_apply_extracted_vars:
        first_key = list(diff_detected.keys())[0]
        actions.append({
            "type": "ask_apply_change",
            "payload": {first_key: diff_detected[first_key]}
        })
    
    return {
        "assistant_message": assistant_message,
        "suggested_plan": suggested_plan_diffs,
        "diff_detected": diff_detected,
        "vars_extracted": vars_extracted,
        "unknown_keys": unknown_keys,
        "lifespan_projection": lifespan_projection,
        "actions": actions
    }


@app.get("/user/vars")
def user_vars(user_id: str = Query(...)):
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)
    
    return {
        "user_id": user_id,
        "vars_extracted": user.get("vars_extracted", {}) if user else {},
        "target_plan": user.get("target_plan", {}) if user else {}
    }

API_PREFIXES = (
    "health", "debug", "onboarding", "plan", "chat", "log", "lifespan", "user"
)

@app.get("/{path:path}")
def spa_fallback(path: str):
    if path.startswith(API_PREFIXES) or path.startswith(("assets",)):
        raise HTTPException(status_code=404, detail="Not found")
    index_path = os.path.join(FRONTEND_DIST_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="dist/index.html not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
