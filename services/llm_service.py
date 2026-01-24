"""LLM service for OpenAI interactions."""
import os
import json
from typing import Dict, Any, List, Optional
from openai import OpenAI
import config


def _get_openai_client() -> Optional[OpenAI]:
    """Get OpenAI client."""
    if not config.OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not configured")
    return OpenAI(api_key=config.OPENAI_API_KEY)


def extract_variables_from_text(text: str) -> Dict[str, Any]:
    """
    Extract variable values from text using LLM.
    Returns dict of {variable_name: numeric_value}.
    Raises exception on failure - no silent failures.
    """
    client = _get_openai_client()
    if not client:
        return {}
    
    # Build variable list for prompt
    var_list = ", ".join(sorted(config.CANONICAL_VARIABLES))
    
    system_prompt = (
        "You are a variable extraction assistant. Extract numeric values for lifestyle variables "
        "from user text. Return ONLY a JSON object with variable names as keys and numeric values. "
        "If a variable is mentioned but no value given, set it to 0. "
        "If a variable is not mentioned, do not include it. "
        "When users use approximate language (about, roughly, around, maybe, approximately, like), " # Handle the approximate language
        "extract the numeric value they mention - treat it as an estimate. " # Handle the approximate language
        "For exercise: calculate total WEEKLY minutes (frequency × duration). " # Add frequency patterns. Better exercise parsing
        "Running, cycling, swimming = cardio. Weights, resistance = strength_training. " # Add frequency patterns. Better exercise parsing
        "UNIT CONVERSIONS - water, green tea is in ml/day: 1 glass ≈ 240ml, 1 liter = 1000ml, 1 bottle ≈ 500ml. " # Unit conversion for water
        f"Available variables: {var_list}\n\n"
        "Examples:\n"
        '- "I eat 6 servings of fruits per day" → {"fruits_and_veggies": 6}\n'
        '- "I don\'t want vitamin A" → {"vitamin_a": 0}\n'
        '- "I\'ll take 1000mg vitamin E" → {"vitamin_e": 1000}\n'
        '- "I drink about 5 glasses of water" → {"water": 1200}\n' # Handle approximate language + unit conversion (5×240=1200ml)
        '- "I drink 2 liters of water daily" → {"water": 2000}\n' # Unit conversion example
        '- "I drink about 5 glasses of green tea" → {"green_tea": 1200}\n' # Handle approximate language + unit conversion (5×240=1200ml)
        '- "I drink 2 liters of green tea daily" → {"green_tea": 2000}\n' # Unit conversion example
        '- "I sleep roughly 7 hours" → {"sleep_duration": 7}\n' # Handle the approximate language
        '- "Maybe like 3 alcoholic drinks per week" → {"alcohol": 3}\n' # Handle the approximate language
        '- "I run 3 times a week for 30 minutes" → {"cardio": 90}\n' # Add frequency patterns, Better exercise parsing (3×30=90)
        '- "I lift weights twice weekly, 45 min each" → {"strength_training": 90}\n' # Add frequency patterns, Better exercise parsing
        '- "I do yoga 4x per week for an hour" → {"cardio": 240}\n' # Add frequency patterns, Better exercise parsing
        "Output ONLY valid JSON, no explanation."
    )
    
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        temperature=0.1,
        max_tokens=512,
    )
    
    text_response = (resp.choices[0].message.content or "").strip()
    
    # Extract JSON
    start = text_response.find("{")
    end = text_response.rfind("}")
    if start == -1 or end == -1:
        return {}  # No JSON found, return empty (not an error - might be no variables)
    
    extracted = json.loads(text_response[start:end + 1])
    
    # Filter to only known variables and convert to numeric
    result = {}
    for key, value in extracted.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                result[key] = float(value)
            except (ValueError, TypeError):
                # Skip invalid numeric values
                continue
    
    return result


def extract_constraints_from_conversation(messages: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Extract constraints/preferences from conversation using LLM.
    Returns structured constraints like {"no_vitamin_a": true, "no_meat": true}.
    Raises exception on failure - no silent failures.
    """
    client = _get_openai_client()
    if not client:
        return {}
    
    # Get last few user messages for context
    user_messages = [
        msg["text"] for msg in messages
        if msg.get("role") == "user"
    ][-5:]  # Last 5 user messages
    
    if not user_messages:
        return {}
    
    conversation_text = "\n".join(user_messages)
    
    # Build variable groups info for prompt
    import config
    groups_info = []
    for group_name, variables in config.VARIABLE_GROUPS.items():
        var_list = ", ".join(sorted(variables))
        groups_info.append(f"{group_name}: {var_list}")
    
    system_prompt = (
        "Extract user constraints and preferences from conversation. "
        "Return ONLY a JSON object with constraint keys and boolean values.\n\n"
        "Variable groups for reference:\n" + "\n".join(groups_info) + "\n\n"
        "Constraint keys to detect:\n"
        "- no_supplements: user doesn't want ANY supplements (maps to all supplement variables)\n"
        "- no_meat: user doesn't want meat (vegetarian/vegan - maps to meat_processed, meat_unprocessed, meat_poultry)\n"
        "- vegetarian: user is vegetarian (maps to meat variables)\n"
        "- vegan: user is vegan (maps to meat + dairy variables)\n"
        "- no_refined_grains: user avoids refined grains (maps to grain_refined)\n"
        "- no_vitamin_a: user doesn't want vitamin A specifically\n"
        "- no_sleep_changes: user can't/won't change sleep schedule\n"
        "- no_exercise: user can't/won't do exercise\n"
        "\n"
        "Examples:\n"
        '- "I don\'t want supplements" → {"no_supplements": true}\n'
        '- "I\'m vegetarian" → {"vegetarian": true, "no_meat": true}\n'
        '- "I can\'t change my sleep" → {"no_sleep_changes": true}\n'
        "\n"
        "If no constraints mentioned, return empty object {}.\n"
        "Output ONLY valid JSON, no explanation."
    )
    
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": conversation_text}
        ],
        temperature=0.1,
        max_tokens=256,
    )
    
    text_response = (resp.choices[0].message.content or "").strip()
    start = text_response.find("{")
    end = text_response.rfind("}")
    if start == -1 or end == -1:
        return {}  # No constraints found
    
    return json.loads(text_response[start:end + 1])


def generate_plan_diffs_with_constraints(
    current_target_plan: Dict[str, Any],
    optimal_plan: Dict[str, Any],
    constraints: Dict[str, Any],
    conversation_context: str = ""
) -> Dict[str, Any]:
    """
    Generate suggested plan DIFFS using LLM.
    Returns diffs to apply to current_target_plan (which is target + current combined).
    The LLM handles all constraint application non-deterministically - no hardcoded mappings.
    Raises exception on failure - no silent failures.
    """
    client = _get_openai_client()
    if not client:
        # Fallback: return empty diffs
        return {}
    
    # Build variable groups info for LLM context
    groups_info = []
    for group_name, variables in config.VARIABLE_GROUPS.items():
        var_list = ", ".join(sorted(variables))
        groups_info.append(f"{group_name}: {var_list}")
    
    # LLM call to generate plan diffs - LLM handles all constraint application non-deterministically
    system_prompt = (
        "You are a lifestyle plan generator. Generate suggested changes (diffs) to the user's current target plan.\n\n"
        "Variable groups for reference:\n" + "\n".join(groups_info) + "\n\n"
        "Rules:\n"
        "- Compare the current target plan with the optimal plan\n"
        "- Generate a JSON object with ALL variables that should be changed to move toward optimal\n"
        "- Include variables that are currently 0 or missing but should have optimal values\n"
        "- Include variables that differ from optimal values\n"
        "- Respect user constraints (e.g., if they say 'no supplements', set all supplement-related variables to 0)\n"
        "- Respect user preferences (e.g., if they specify a value like 'water: 3000', use that value)\n"
        "- Balance between optimal and current target plan, but prioritize moving toward optimal\n"
        "- Include ALL prediction API variables that should be adjusted (sleep_duration, calorie_restriction, etc.)\n"
        "- Return ONLY a JSON object with variable names and numeric values\n"
        "- Output ONLY valid JSON, no explanation."
    )
    
    # Build constraints description for LLM (let it interpret, don't hardcode mappings)
    constraints_desc = ""
    if constraints:
        constraints_desc = f"\nUser constraints/preferences: {json.dumps(constraints)}\n"
        constraints_desc += "Interpret these constraints and apply them appropriately. If user says 'no supplements', set all supplement variables to 0.\n"
    
    user_prompt = (
        f"Optimal plan: {json.dumps(optimal_plan)}\n\n"
        f"Current target plan (target + current combined): {json.dumps(current_target_plan)}\n"
        f"{constraints_desc}"
        f"Conversation context: {conversation_context}\n\n"
        "Generate suggested changes (diffs) to apply to the current target plan. Include ALL variables that should be adjusted to move toward optimal values, including variables currently at 0 that should have optimal values. Respect user constraints and preferences from the conversation. Output JSON only."
    )
    
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        top_p=0.95,
        max_tokens=2048,
    )
    
    text_response = (resp.choices[0].message.content or "").strip()
    
    # Extract JSON (similar to existing implementation's pattern)
    start = text_response.find("{")
    end = text_response.rfind("}")
    if start == -1 or end == -1:
        # Fallback to empty diffs if no JSON found
        return {}
    
    suggested = json.loads(text_response[start:end + 1])
    
    # Validate: only known variables, numeric types
    # Return only the diffs (variables that should change)
    # Include variables that differ from current OR are missing/zero but should have optimal values
    validated_diffs = {}
    for key, value in suggested.items():
        if key in config.CANONICAL_VARIABLES:
            try:
                num_val = float(value)
                # Include if it's different from current target plan
                # Also include if current is 0/missing and optimal has a value (should move toward optimal)
                current_val = current_target_plan.get(key, 0)
                optimal_val = optimal_plan.get(key, 0)
                
                # Include if different from current, OR if current is 0 and optimal has a value
                if num_val != current_val:
                    validated_diffs[key] = num_val
                elif current_val == 0 and optimal_val != 0 and num_val == optimal_val:
                    # Include if LLM suggests optimal value for a currently-zero variable
                    validated_diffs[key] = num_val
            except (ValueError, TypeError):
                # Skip invalid values
                continue
    
    return validated_diffs


def generate_assistant_reply(
    messages: List[Dict[str, str]],
    context_prefix: str = ""
) -> str:
    """
    Generate assistant reply using OpenAI.
    Based on reference implementation - concise, conversational, no markdown.
    Raises exception on failure - no silent failures.
    """
    client = _get_openai_client()
    if not client:
        return "Service not configured with OPENAI_API_KEY."
    
    # System instruction based on reference implementation
    import config
    
    # Build variable groups for context
    groups_summary = []
    for group_name, variables in config.VARIABLE_GROUPS.items():
        examples = list(variables)[:3]  # First 3 as examples
        examples_str = ", ".join(examples)
        if len(variables) > 3:
            examples_str += ", etc."
        groups_summary.append(f"{group_name} (e.g. {examples_str})")
    
    system_instruction = (
        "You are a friendly lifestyle assistant. Keep replies concise and concrete.\n\n"
        "Goal: help the user choose simple changes across variables our system predicts on.\n"
        "Avoid medical claims. No meds or supplements unless the user brings them up, and respect when they say no supplements.\n\n"
        "Variable categories available:\n" + "\n".join(f"- {g}" for g in groups_summary) + "\n\n"
        "Conversation guidance:\n"
        "- BE SPECIFIC: Use actual numbers from user's plan (e.g., 'increase fruits from 3 to 5 servings' not 'eat more fruits')\n"  # Be specific
        "- NO REPETITION: Don't repeat praise or questions you've already said in this conversation\n"  # Avoid repetition
        "- When user asks about a category, give 2-3 CONCRETE changes with numbers\n"  # Concrete suggestions
        "- PRIORITY FIRST: Lead with the highest-impact change. Say 'The biggest improvement would be...' or 'Most impactful: ...'\n"  # Priority highlighting
        "- High-impact variables: sleep_duration, cardio, alcohol, fruits_and_veggies, strength_training (mention these first)\n"  # Priority highlighting
        "- Show alignment: mention which areas are close to optimal vs which need work\n"
        "- Keep responses short (2-3 sentences max)\n"
        "- Use natural conversation flow, don't ask the same question twice\n"
        "- Example good response: 'The biggest impact would be adding cardio - going from 10 to 25 min/week. Also consider: increase fruits/veggies from 3 to 5, reduce alcohol from 5 to 3.'\n"  # Example with priority
        "\n"
        "IMPORTANT FORMATTING RULES:\n"
        "- NO markdown formatting (no **, no bolding, no asterisks, no _)\n"
        "- Use \\n line breaks before any lists or numbered items\n"
        "- Keep responses conversational and brief (2-3 sentences max)\n"
        "- Use plain text only, no special formatting\n"
    )
    
    formatted_messages = [{"role": "system", "content": system_instruction}]
    for msg in messages:
        role = msg.get("role", "user")
        text = msg.get("text", "")
        if role == "user":
            text = f"{context_prefix}\n{text}" if context_prefix else text
        formatted_messages.append({
            "role": "assistant" if role == "assistant" else "user",
            "content": text
        })
    
    resp = client.chat.completions.create(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        messages=formatted_messages,
        temperature=0.8,
        top_p=0.95,
        max_tokens=512,  # Reduced from 2048 to keep responses concise
    )
    
    reply = (resp.choices[0].message.content or "").strip()
    
    # Post-process to remove any markdown that might have slipped through
    # Remove **, __, *, etc. but keep the text
    import re
    reply = re.sub(r'\*\*([^*]+)\*\*', r'\1', reply)  # Remove **bold**
    reply = re.sub(r'__([^_]+)__', r'\1', reply)  # Remove __bold__
    reply = re.sub(r'\*([^*]+)\*', r'\1', reply)  # Remove *italic*
    reply = re.sub(r'_([^_]+)_', r'\1', reply)  # Remove _italic_
    
    return reply


def merge_extracted_vars_to_diff(
    extracted: Dict[str, float],
    current_target_plan: Dict[str, float]
) -> Dict[str, float]:
    """
    Merge extracted variables into a diff.
    Only includes variables that differ from current target plan.
    """
    diff = {}
    for key, value in extracted.items():
        if key not in current_target_plan or current_target_plan[key] != value:
            diff[key] = value
    return diff
