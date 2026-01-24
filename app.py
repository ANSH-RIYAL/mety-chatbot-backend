"""FastAPI application for chatbot assistant platform."""
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
from services.metrics_service import metrics_service

app = FastAPI(title="Chatbot Assistant Platform API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models
class OnboardingPayload(BaseModel):
    name: Optional[str] = None
    age: Optional[float] = None
    gender: Optional[int] = None
    # Supplements
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
    # Diet
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
    # Exercise
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


# Helper functions (removed _validate_and_clamp_quality - no longer needed)


def _ensure_user_exists(user_id: str) -> None:
    """Ensure user document exists, create if not. If exists but has optimal values in current/target, reset them."""
    user = firestore_service.get_user(user_id)
    if not user:
        # Initialize plans: current and target start empty (all zeros), optimal has optimal values
        # Create base with all canonical variables set to 0
        base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
        
        # Optimal plan has optimal values
        optimal_plan = base_plan.copy()
        optimal_plan.update(config.OPTIMAL_PLAN)  # Overlay optimal values
        
        firestore_service.create_user(user_id, {
            "profile": {},
            "current_plan": {},  # Start completely empty, not even zeros
            "target_plan": {},  # Start completely empty, not even zeros
            "optimal_plan": optimal_plan.copy(),  # Optimal values
            "vars_extracted": {},
            "last_updated": datetime.utcnow().isoformat()
        })
    else:
        # User exists - check if current_plan or target_plan have optimal values and reset them
        current = user.get("current_plan", {})
        target = user.get("target_plan", {})
        needs_reset = False
        
        # Check if any values match optimal (indicating they shouldn't be there)
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


# Routes
@app.get("/health")
def health():
    return {"status": "ok", "service": "Chatbot Assistant Platform"}


@app.get("/health/metrics")
def health_metrics(
    include_latency: bool = Query(False, description="Include internal latency measurements (slower)"),
    gcp_url: str = Query(None, description="GCP Cloud Run URL to test external latency (e.g., https://xxx.a.run.app)")
):
    """
    Get comprehensive health metrics including compute and latency.
    
    - **include_latency=false**: Fast response with RAM/CPU only (~50ms)
    - **include_latency=true**: Full metrics including Firestore, LLM, prediction API latency (~2-5s)
    - **gcp_url=https://xxx.a.run.app**: Test external GCP Cloud Run endpoint latency
    
    Use for monitoring:
    - Scheduled cron jobs (every 12 hours)
    - Dashboard health checks
    - Performance debugging
    - GCP deployment validation
    """
    return metrics_service.get_full_metrics(include_latency=include_latency, gcp_url=gcp_url)


@app.post("/onboarding/submit")
def onboarding_submit(request: OnboardingRequest):
    """Save onboarding page data to profile and current_plan."""
    _ensure_user_exists(request.user_id)
    
    # Get payload (remove stress_quality and sleep_quality - no longer needed)
    payload_dict = request.payload.dict(exclude_none=True)
    payload_dict.pop("sleep_quality", None)
    payload_dict.pop("stress_quality", None)
    
    # Get existing user (tries Firestore, falls back to local)
    user = firestore_service.get_user(request.user_id)
    profile = user.get("profile", {}) if user else {}
    
    # Merge payload into profile (for name, age, gender)
    profile_data = {k: v for k, v in payload_dict.items() if k in ["name", "age", "gender"]}
    if profile_data:
        profile.update(profile_data)
        firestore_service.update_user_profile(request.user_id, profile)
    
    # Save plan variables to current_plan (not target_plan)
    plan_data = {k: v for k, v in payload_dict.items() if k not in ["name", "age", "gender"]}
    if plan_data:
        # Start fresh - only save what user entered, nothing else
        new_current_plan = {}
        for key, value in plan_data.items():
            if key in config.CANONICAL_VARIABLES:
                try:
                    new_current_plan[key] = float(value)
                except (ValueError, TypeError):
                    pass
        
        # Get existing current_plan and merge ONLY the new values
        existing_current = user.get("current_plan", {}) if user else {}
        existing_current.update(new_current_plan)  # This adds/updates only the new values
        
        # Save it
        firestore_service.update_user_plan(request.user_id, "current_plan", existing_current)
    
    return {"ok": True, "saved_doc": f"users/{request.user_id}"}


@app.get("/plan/get")
def plan_get(user_id: str = Query(...)):
    """Get user plans. Ensures all plans are populated with all variables from CANONICAL_VARIABLES."""
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)  # Tries Firestore, falls back to local
    
    # Get optimal plan (from user or default)
    optimal_plan = user.get("optimal_plan", config.OPTIMAL_PLAN) if user else config.OPTIMAL_PLAN.copy()
    
    # Get current and target plans - these are the user's actual values
    stored_current = user.get("current_plan", {}) if user else {}
    stored_target = user.get("target_plan", {}) if user else {}
    
    # Create base plan with all canonical variables set to 0
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    
    # Start with zeros, then overlay ONLY what's stored (which should only be user-entered values)
    current_plan_full = base_plan.copy()
    for key, value in stored_current.items():
        if key in config.CANONICAL_VARIABLES:
            current_plan_full[key] = float(value)
    
    target_plan_full = base_plan.copy()
    for key, value in stored_target.items():
        if key in config.CANONICAL_VARIABLES:
            target_plan_full[key] = float(value)
    
    # For optimal_plan: start with base, then overlay optimal values
    optimal_plan_full = base_plan.copy()
    optimal_plan_full.update(optimal_plan)  # Optimal values
    
    return {
        "user_id": user_id,
        "current_plan": current_plan_full,
        "target_plan": target_plan_full,
        "optimal_plan": optimal_plan_full,
        "last_updated": user.get("last_updated", datetime.utcnow().isoformat()) if user else datetime.utcnow().isoformat()
    }


@app.post("/plan/update")
def plan_update(request: PlanUpdateRequest):
    """Update target plan with diff. Ensures all variables present but doesn't overlay optimal values."""
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)  # Tries Firestore, falls back to local
    
    # Validate keys
    unknown_keys = [k for k in request.diff.keys() if k not in config.CANONICAL_VARIABLES]
    if unknown_keys:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown keys: {unknown_keys}"
        )
    
    # Create base with all canonical variables set to 0 (NOT optimal values)
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    
    # Get current target plan (only non-zero values are stored)
    current_target = user.get("target_plan", {}) if user else {}
    
    # Start with existing target values, then apply new diff on top
    # This way we preserve all existing target values and add/update with new diff
    target_plan = {}
    # First, copy all existing target values
    for key, value in current_target.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                target_plan[key] = float(value)
            except (ValueError, TypeError):
                pass
    
    # Then, apply new diff (this adds new values or overwrites existing ones)
    for key, value in request.diff.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                target_plan[key] = float(value)
            except (ValueError, TypeError):
                pass
    
    # Ensure numeric types
    for key in target_plan:
        try:
            target_plan[key] = float(target_plan[key])
        except (ValueError, TypeError):
            target_plan[key] = 0.0
    
    # Only save NON-ZERO values to database (don't save zeros)
    # This ensures that when we read it back, we only get the actual values
    target_plan_to_save = {}
    for key, value in target_plan.items():
        if value != 0 and value is not None:
            target_plan_to_save[key] = value
    
    print(f"[PLAN UPDATE] Saving target_plan with {len(target_plan_to_save)} non-zero values:")
    print(f"[PLAN UPDATE] Keys: {list(target_plan_to_save.keys())}")
    print(f"[PLAN UPDATE] Sample values: {dict(list(target_plan_to_save.items())[:5])}")
    
    # Update in Firestore (tries Firestore, falls back to local)
    # Only save non-zero values
    firestore_service.update_user_plan(request.user_id, "target_plan", target_plan_to_save)
    
    # Verify what was saved
    user_after = firestore_service.get_user(request.user_id)
    saved_target = user_after.get("target_plan", {}) if user_after else {}
    print(f"[PLAN UPDATE] After save, target_plan has {len(saved_target)} keys")
    print(f"[PLAN UPDATE] Saved keys: {list(saved_target.keys())[:10]}")
    
    # Log to plans_history (tries Firestore, falls back to local)
    firestore_service.log_plan_change(
        request.user_id,
        request.diff,
        source="ui",
        plan_type="target"  # This is a target plan update
    )
    
    return {
        "ok": True,
        "new_target_plan": target_plan,  # Full plan with all variables
        "applied_diff": request.diff
    }


@app.post("/plan/apply-target-to-current")
def plan_apply_target_to_current(user_id: str = Query(...)):
    """Apply target plan to current plan (copy target values to current)."""
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)  # Tries Firestore, falls back to local
    
    # Get target plan (only non-zero values are stored)
    stored_target = user.get("target_plan", {}) if user else {}
    
    # If target plan is empty, nothing to apply
    if not stored_target:
        return {"ok": True, "message": "Target plan is empty, nothing to apply"}
    
    # Create base with all canonical variables set to 0
    base_plan = {var: 0.0 for var in config.CANONICAL_VARIABLES}
    
    # Get current plan (only non-zero values are stored)
    stored_current = user.get("current_plan", {}) if user else {}
    
    # Build full target plan: start with zeros, then overlay stored target values
    full_target_plan = base_plan.copy()
    for key, value in stored_target.items():
        if key in config.CANONICAL_VARIABLES:
            full_target_plan[key] = float(value)
    
    # Build full current plan: start with zeros, then overlay stored current values
    full_current_plan = base_plan.copy()
    for key, value in stored_current.items():
        if key in config.CANONICAL_VARIABLES:
            full_current_plan[key] = float(value)
    
    # Calculate diff (what changed from current to target)
    diff = {}
    for key in config.CANONICAL_VARIABLES:
        current_val = full_current_plan.get(key, 0)
        target_val = full_target_plan.get(key, 0)
        if target_val != current_val:
            diff[key] = target_val
    
    # NEW CURRENT PLAN = TARGET PLAN (target values completely replace current)
    # Only save non-zero values to database
    new_current_plan_to_save = {}
    for key, value in full_target_plan.items():
        if value != 0 and value is not None:
            new_current_plan_to_save[key] = value
    
    # Update current plan to match target plan (target values replace current)
    firestore_service.update_user_plan(user_id, "current_plan", new_current_plan_to_save)
    
    # Log the change with timestamp (for logging areas)
    if diff:
        firestore_service.log_plan_change(
            user_id, 
            diff, 
            source="apply_target_to_current",
            plan_type="current"  # Applying to current plan
        )
    
    # Clear target plan (reset to empty - only save non-zero, so empty dict)
    firestore_service.update_user_plan(user_id, "target_plan", {})
    
    return {"ok": True, "message": "Target plan applied to current plan"}


@app.post("/chat/clear")
def chat_clear(user_id: str = Query(...)):
    """Clear chat history for a user."""
    _ensure_user_exists(user_id)
    
    # Clear chat history (tries Firestore, falls back to local)
    firestore_service.clear_chat_history(user_id)
    
    return {"ok": True, "message": "Chat history cleared"}


@app.post("/log/submit")
def log_submit(request: LogSubmitRequest):
    """Submit log and calculate adherence."""
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)  # Tries Firestore, falls back to local
    target_plan = user.get("target_plan", {}) if user else {}
    
    # Calculate adherence
    adherence = calculate_adherence(request.log, target_plan)
    
    # Save log (tries Firestore, falls back to local)
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
    """Predict lifespan and risk ratios."""
    # Only send variables with values (no defaults per spec)
    result = call_lifespan_api(request.input)
    
    if "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result


@app.post("/chat")
def chat(request: ChatRequest):
    """Main chat orchestration endpoint.
    
    Receives only the latest message, fetches previous messages from Firestore.
    Stores new message, processes, and returns response.
    """
    _ensure_user_exists(request.user_id)
    user = firestore_service.get_user(request.user_id)  # Tries Firestore, falls back to local
    
    # Persist the new user message to Firestore
    firestore_service.persist_chat_message(
        request.user_id,
        "user",
        request.message
    )
    
    # Fetch previous chat history from Firestore (for context and variable extraction)
    chat_history = firestore_service.get_chat_history(request.user_id, limit=50)
    
    # Build messages list for LLM (all messages from history + new one)
    all_messages = []
    for msg in chat_history:
        all_messages.append({
            "role": msg.get("role", "user"),
            "text": msg.get("text", "")
        })
    # Add the new message (already persisted, but add to list for processing)
    all_messages.append({
        "role": "user",
        "text": request.message
    })
    
    # Extract variables from last 2 user messages (for feature extraction)
    user_messages = [msg["text"] for msg in all_messages if msg["role"] == "user"][-2:]
    vars_extracted = {}
    for msg_text in user_messages:
        try:
            extracted = extract_variables_from_text(msg_text)
            vars_extracted.update(extracted)
        except Exception as e:
            # Log error but continue - variable extraction failure shouldn't break chat
            print(f"Warning: Variable extraction failed: {e}")
    
    # Filter unknown keys
    unknown_keys = [k for k in vars_extracted.keys() if k not in config.CANONICAL_VARIABLES]
    vars_extracted = {
        k: v for k, v in vars_extracted.items()
        if k in config.CANONICAL_VARIABLES
    }
    
    # Get current plan and target plan
    current_plan = user.get("current_plan", {}) if user else {}
    target_plan = user.get("target_plan", {}) if user else {}
    
    # Combine target + current: target values where they exist, otherwise current values
    # This represents the "current target plan" that the user is working with
    combined_target_current = current_plan.copy()
    combined_target_current.update(target_plan)  # Target plan values override current plan values
    
    # Create diff using modular function - compare extracted vars to combined plan
    diff_detected = merge_extracted_vars_to_diff(vars_extracted, combined_target_current)
    
    # Note: auto_apply_extracted_vars is handled on frontend only - we don't update backend here
    # The frontend will update its local state and show values in target plan section
    # Backend only updates when user explicitly saves (via /plan/update or /plan/apply-target-to-current)
    
    # Update vars_extracted in user doc (for tracking, not for auto-applying)
    if vars_extracted:
        existing_vars = user.get("vars_extracted", {}) if user else {}
        existing_vars.update(vars_extracted)
        firestore_service.update_user_vars_extracted(request.user_id, existing_vars)
    
    # Generate suggested plan (for My Plan page - recommendation happens there)
    current_plan = user.get("current_plan", {}) if user else {}
    target_plan = user.get("target_plan", {}) if user else {}
    optimal_plan = user.get("optimal_plan", config.OPTIMAL_PLAN) if user else config.OPTIMAL_PLAN.copy()
    
    # Combine target + current: target values where they exist, otherwise current values
    # This represents the "current target plan" that the user is working with
    combined_target_current = current_plan.copy()
    combined_target_current.update(target_plan)  # Target plan values override current plan values
    
    # Debug: Log what's being sent to LLM
    print(f"\n[DEBUG] Generating suggested plan for user {request.user_id}:")
    print(f"  current_plan keys: {len(current_plan)} (sample: {dict(list(current_plan.items())[:3])})")
    print(f"  target_plan keys: {len(target_plan)} (sample: {dict(list(target_plan.items())[:3])})")
    print(f"  combined_target_current keys: {len(combined_target_current)} (sample: {dict(list(combined_target_current.items())[:3])})")
    
    # Extract constraints from conversation (for plan generation context)
    try:
        constraints = extract_constraints_from_conversation(all_messages)
    except Exception as e:
        # If constraint extraction fails, use empty constraints
        print(f"Warning: Constraint extraction failed: {e}")
        constraints = {}
    
    # Generate plan diffs (for recommendation - used in My Plan page)
    # LLM will return diffs to apply to combined_target_current
    conversation_text = " ".join([msg["text"] for msg in all_messages[-5:]])
    try:
        suggested_plan_diffs = generate_plan_diffs_with_constraints(
            combined_target_current,
            optimal_plan,
            constraints,
            conversation_text
        )
    except Exception as e:
        # If plan generation fails, return empty diffs
        print(f"Warning: Plan generation failed: {e}")
        suggested_plan_diffs = {}
    
    # Call lifespan API with suggested plan
    # suggested_plan_diffs are diffs, so combine with (target + current) to get full plan for prediction
    lifespan_projection = {}
    if suggested_plan_diffs:
        # Combine target + current, then apply suggested diffs to get full suggested plan
        full_suggested_plan = combined_target_current.copy()
        full_suggested_plan.update(suggested_plan_diffs)
        
        # Only send prediction API variables
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
        
        # Get age and gender from profile if not in plan
        if "age" not in prediction_input:
            profile_data = user.get("profile", {}) if user else {}
            if profile_data.get("age"):
                prediction_input["age"] = float(profile_data["age"])
        if "gender" not in prediction_input:
            profile_data = user.get("profile", {}) if user else {}
            if profile_data.get("gender") is not None:
                prediction_input["gender"] = float(profile_data["gender"])
        
        if len(prediction_input) >= 2:  # At least age and gender
            projection = call_lifespan_api(prediction_input)
            if "error" not in projection:
                lifespan_projection = projection
                # Cache predictions in user document
                try:
                    firestore_service.update_user_predictions(
                        request.user_id,
                        lifespan=projection.get("all_cause_mortality_predicted_lifespan", 0),
                        risk_ratios={
                            "cancer": projection.get("cancer_predicted_rr", 0),
                            "cardiovascular": projection.get("cardio_vascular_disease_predicted_rr", 0),
                            "depression": projection.get("depression_predicted_rr", 0),
                            "diabetes": projection.get("diabetes_predicted_rr", 0),
                            "stroke": projection.get("stroke_predicted_rr", 0)
                        },
                        input_plan="suggested"
                    )
                except Exception as e:
                    print(f"Warning: Failed to cache predictions: {e}")
    
    # Generate assistant reply with context showing alignment
    # Calculate alignment between current/target and optimal for conversational context
    context_parts = []
    
    # Calculate alignment for each category
    def calculate_alignment(plan_dict, optimal_dict, group_vars):
        """Calculate how close plan is to optimal for a group."""
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
    
    # Include constraints if any
    if constraints:
        context_parts.append(f"User constraints: {constraints}")
    
    # Include extracted variables if any (recently mentioned)
    if vars_extracted:
        context_parts.append(f"Recently mentioned: {vars_extracted}")
    
    context_prefix = "\n".join(context_parts) if context_parts else ""
    try:
        assistant_message = generate_assistant_reply(all_messages, context_prefix)
    except Exception as e:
        # Fallback message if LLM fails
        print(f"Error generating assistant reply: {e}")
        assistant_message = "I understand your preferences. Let me help you adjust your plan."
    
    # Build actions BEFORE persist_chat_message (so we can include in metadata)
    actions = []
    if diff_detected and not request.options.auto_apply_extracted_vars:
        # Ask to apply change for first detected variable
        first_key = list(diff_detected.keys())[0]
        actions.append({
            "type": "ask_apply_change",
            "payload": {first_key: diff_detected[first_key]}
        })
    
    # Persist assistant message with metadata
    firestore_service.persist_chat_message(
        request.user_id,
        "assistant",
        assistant_message,
        metadata={
            "suggested_plan": suggested_plan_diffs if suggested_plan_diffs else None,
            "vars_extracted": vars_extracted if vars_extracted else None,
            "actions": actions if actions else None
        }
    )
    
    # suggested_plan_diffs are already diffs - no need to merge with optimal
    # These are the changes to apply to (target + current) plan
    
    return {
        "assistant_message": assistant_message,
        "suggested_plan": suggested_plan_diffs,  # Diffs to apply to (target + current) plan
        "diff_detected": diff_detected,
        "vars_extracted": vars_extracted,
        "unknown_keys": unknown_keys,
        "lifespan_projection": lifespan_projection,
        "actions": actions
    }


@app.get("/user/vars")
def user_vars(user_id: str = Query(...)):
    """Get user vars_extracted and target_plan."""
    _ensure_user_exists(user_id)
    user = firestore_service.get_user(user_id)  # Tries Firestore, falls back to local
    
    return {
        "user_id": user_id,
        "vars_extracted": user.get("vars_extracted", {}) if user else {},
        "target_plan": user.get("target_plan", {}) if user else {}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

