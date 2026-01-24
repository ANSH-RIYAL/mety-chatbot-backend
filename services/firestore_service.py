"""Firestore service for database operations."""
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from google.cloud import firestore
from google.oauth2 import service_account
import config


class FirestoreService:
    """Service for Firestore database operations."""
    
    def __init__(self):
        # Ensure firestore_copy directory exists first
        self.copy_dir = "firestore_copy"
        os.makedirs(self.copy_dir, exist_ok=True)
        for subdir in ["users", "chat_history", "plans_history", "logs"]:
            os.makedirs(os.path.join(self.copy_dir, subdir), exist_ok=True)
        
        # Try to initialize Firestore, fall back to local-only if credentials missing
        try:
            if not os.path.exists(config.FIRESTORE_CREDENTIALS):
                raise FileNotFoundError(f"Credentials file not found: {config.FIRESTORE_CREDENTIALS}")
            
            credentials = service_account.Credentials.from_service_account_file(
                config.FIRESTORE_CREDENTIALS
            )
            self.db = firestore.Client(
                credentials=credentials,
                project=credentials.project_id
            )
            self.firestore_enabled = True
        except Exception as e:
            self.db = None
            self.firestore_enabled = False
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: {e}")
            print(f"All Firestore operations will use local copies only.")
            print(f"Local copies saved to: {self.copy_dir}/")
            print(f"ACTION REQUIRED: Fix Firestore connection or add credentials file.")
            print(f"{'='*60}\n")
    
    def _save_local_copy(self, collection: str, doc_id: str, data: Dict[str, Any]) -> None:
        """Save a local copy of Firestore data."""
        try:
            file_path = os.path.join(self.copy_dir, collection, f"{doc_id}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            # Don't fail if local copy fails
            print(f"Warning: Failed to save local copy: {e}")
    
    # User operations
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user document. Tries Firestore first, falls back to local copy."""
        try:
            doc = self.db.collection("users").document(user_id).get()
            if doc.exists:
                return doc.to_dict()
            return None
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: get_user")
            print(f"Error: {str(e)}")
            print(f"Falling back to local copy from firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Try to load from local copy
            try:
                file_path = os.path.join(self.copy_dir, "users", f"{user_id}.json")
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        return json.load(f)
            except Exception as local_err:
                print(f"Warning: Could not load local copy: {local_err}")
            return None  # Return None if both Firestore and local copy fail
    
    def create_user(self, user_id: str, data: Dict[str, Any]) -> None:
        """Create user document (overwrite if exists). Tries Firestore first, saves to local copy always."""
        data["last_updated"] = datetime.utcnow().isoformat()
        try:
            # Use set() without merge to ensure we overwrite any existing data
            # This ensures current_plan and target_plan start with zeros, not optimal values
            self.db.collection("users").document(user_id).set(data)
            self._save_local_copy("users", user_id, data)
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: create_user")
            print(f"Error: {str(e)}")
            print(f"Saving to local copy only: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Save to local copy even if Firestore fails
            self._save_local_copy("users", user_id, data)
            # Don't raise - allow operation to continue with local copy
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        """Update user profile (merge into existing). Tries Firestore first, falls back to local."""
        try:
            user_ref = self.db.collection("users").document(user_id)
            update_data = {
                "profile": profile_data,
                "last_updated": datetime.utcnow().isoformat()
            }
            user_ref.update(update_data)
            # Get full document for local copy
            doc = user_ref.get()
            if doc.exists:
                self._save_local_copy("users", user_id, doc.to_dict())
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: update_user_profile")
            print(f"Error: {str(e)}")
            print(f"Updating local copy: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Get existing user data and merge
            existing = self.get_user(user_id) or {}
            existing.update({"profile": profile_data, "last_updated": datetime.utcnow().isoformat()})
            self._save_local_copy("users", user_id, existing)
            # Don't raise - allow operation to continue with local copy
    
    def update_user_plan(self, user_id: str, plan_type: str, plan_data: Dict[str, Any]) -> None:
        """Update user plan (current_plan, target_plan, or optimal_plan). Tries Firestore first, falls back to local."""
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({
                plan_type: plan_data,
                "last_updated": datetime.utcnow().isoformat()
            })
            # Get full document for local copy
            doc = user_ref.get()
            if doc.exists:
                self._save_local_copy("users", user_id, doc.to_dict())
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: update_user_plan ({plan_type})")
            print(f"Error: {str(e)}")
            print(f"Updating local copy: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Get existing user data and update
            existing = self.get_user(user_id) or {}
            # IMPORTANT: Replace the entire plan_type field, don't merge
            # This ensures we don't keep old zero values
            existing[plan_type] = plan_data.copy() if isinstance(plan_data, dict) else plan_data
            existing["last_updated"] = datetime.utcnow().isoformat()
            self._save_local_copy("users", user_id, existing)
            print(f"[FIRESTORE] Saved {plan_type} with {len(plan_data)} keys: {list(plan_data.keys())[:10]}")
            print(f"[FIRESTORE] Full {plan_type} data: {plan_data}")
            # Don't raise - allow operation to continue with local copy
    
    def update_user_vars_extracted(self, user_id: str, vars_data: Dict[str, Any]) -> None:
        """Update vars_extracted dictionary. Tries Firestore first, falls back to local."""
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({
                "vars_extracted": vars_data,
                "last_updated": datetime.utcnow().isoformat()
            })
            # Get full document for local copy
            doc = user_ref.get()
            if doc.exists:
                self._save_local_copy("users", user_id, doc.to_dict())
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: update_user_vars_extracted")
            print(f"Error: {str(e)}")
            print(f"Updating local copy: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Get existing user data and update
            existing = self.get_user(user_id) or {}
            existing.update({"vars_extracted": vars_data, "last_updated": datetime.utcnow().isoformat()})
            self._save_local_copy("users", user_id, existing)
            # Don't raise - allow operation to continue with local copy
    
    """ 
    Update cached predictions in user document.
    """
    def update_user_predictions(
        self, user_id: str, 
        lifespan: float,
        risk_ratios: Dict[str, float],
        input_plan: str = "target"
    ) -> None:
        """
        Update cached predictions in user document.
        
        Args:
            user_id: User ID
            lifespan: Predicted lifespan in years
            risk_ratios: Dict with keys: cancer, cardiovascular, depression, diabetes, stroke
            input_plan: Which plan was used for prediction ("current" or "target")
        """
        predictions_data = {
            "lifespan": lifespan,
            "risk_ratios": risk_ratios,
            "calculated_at": datetime.utcnow().isoformat(),
            "input_plan": input_plan
        }
        try:
            user_ref = self.db.collection("users").document(user_id)
            user_ref.update({
                "predictions": predictions_data,
                "last_updated": datetime.utcnow().isoformat()
            })
            # Get full document for local copy
            doc = user_ref.get()
            if doc.exists:
                self._save_local_copy("users", user_id, doc.to_dict())
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: update_user_predictions")
            print(f"Error: {str(e)}")
            print(f"Updating local copy: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Get existing user data and update
            existing = self.get_user(user_id) or {}
            existing.update({"predictions": predictions_data, "last_updated": datetime.utcnow().isoformat()})
            self._save_local_copy("users", user_id, existing)
            # Don't raise - allow operation to continue with local copy
    
    # Chat history operations
    def persist_chat_message(
        self, user_id: str, role: str, text: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Persist a chat message to chat_history collection.
        
        Args:
            user_id: User ID
            role: "user" or "assistant"
            text: Message content
            metadata: Optional dict with suggested_plan, vars_extracted, actions
        """
        data = {
            "user_id": user_id,
            "role": role,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        }
        # Add metadata if provided
        if metadata:
            data["metadata"] = metadata
        try:
            doc_ref = self.db.collection("chat_history").document()
            doc_ref.set(data)
            self._save_local_copy("chat_history", doc_ref.id, data)
            return doc_ref.id
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: persist_chat_message")
            print(f"Error: {str(e)}")
            doc_id = f"local_{int(datetime.utcnow().timestamp() * 1000000)}"
            print(f"Saving to local copy: firestore_copy/chat_history/{doc_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Save to local copy even if Firestore fails
            self._save_local_copy("chat_history", doc_id, data)
            return doc_id  # Return local ID instead of raising
    
    def get_chat_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get chat history for a user. Tries Firestore first, falls back to local copies."""
        try:
            docs = (
                self.db.collection("chat_history")
                .where("user_id", "==", user_id)
                .order_by("timestamp", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .get()
            )
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: get_chat_history")
            print(f"Error: {str(e)}")
            print(f"Falling back to local copies from firestore_copy/chat_history/")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Try to load from local copies
            try:
                chat_dir = os.path.join(self.copy_dir, "chat_history")
                if os.path.exists(chat_dir):
                    results = []
                    for filename in os.listdir(chat_dir):
                        if filename.endswith(".json"):
                            try:
                                with open(os.path.join(chat_dir, filename), "r") as f:
                                    msg = json.load(f)
                                    if msg.get("user_id") == user_id:
                                        results.append(msg)
                            except:
                                continue
                    results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
                    return results[:limit]
            except Exception as local_err:
                print(f"Warning: Could not load local chat history: {local_err}")
            return []
    
    def clear_chat_history(self, user_id: str) -> None:
        """Clear all chat history for a user. Uses batched deletes for cost safety."""
        try:
            if self.firestore_enabled and self.db:
                # Delete in batches of 100 to avoid unbounded reads (cost safety)
                deleted_count = 0
                while True:
                    docs = (
                        self.db.collection("chat_history")
                        .where("user_id", "==", user_id)
                        .limit(100)  # Cost safety: batch of 100
                        .get()
                    )
                    if not docs:
                        break
                    for doc in docs:
                        doc.reference.delete()
                        deleted_count += 1
                # Only log if actually deleted something (reduce log noise)
                if deleted_count > 0:
                    print(f"Cleared {deleted_count} chat messages for user {user_id}")
            else:
                raise Exception("Firestore not enabled")
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: clear_chat_history")
            print(f"Error: {str(e)}")
            print(f"Clearing local copies from firestore_copy/chat_history/")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
        
        # Always clear local copies
        try:
            import glob
            pattern = os.path.join(self.copy_dir, "chat_history", f"*_{user_id}_*.json")
            for file_path in glob.glob(pattern):
                os.remove(file_path)
            # Also try pattern without user_id prefix
            pattern2 = os.path.join(self.copy_dir, "chat_history", "*.json")
            for file_path in glob.glob(pattern2):
                try:
                    with open(file_path, "r") as f:
                        data = json.load(f)
                        if data.get("user_id") == user_id:
                            os.remove(file_path)
                except Exception:
                    pass
            print(f"Cleared local chat history copies for user {user_id}")
        except Exception as e:
            print(f"Warning: Failed to clear local chat history: {e}")  # Return empty list if both Firestore and local copy fail
    
    # Plan history operations
    def log_plan_change(
        self, user_id: str, diff: Dict[str, Any], 
        source: str = "ui",
        plan_type: str = "target",
        previous_values: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a plan change to plans_history collection.
        
        Args:
            user_id: User ID
            diff: The changes that were made
            source: Where the change came from ("chat", "ui", "onboarding")
            plan_type: Which plan was changed ("current" or "target")
            previous_values: Optional - values before the change
        """
        data = {
            "user_id": user_id,
            "diff": diff,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source,
            "plan_type": plan_type
        }
        # Add previous_values if provided
        if previous_values:
            data["previous_values"] = previous_values
        try:
            doc_ref = self.db.collection("plans_history").document()
            doc_ref.set(data)
            self._save_local_copy("plans_history", doc_ref.id, data)
            return doc_ref.id
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: log_plan_change")
            print(f"Error: {str(e)}")
            doc_id = f"local_{int(datetime.utcnow().timestamp() * 1000000)}"
            print(f"Saving to local copy: firestore_copy/plans_history/{doc_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Save to local copy even if Firestore fails
            self._save_local_copy("plans_history", doc_id, data)
            return doc_id  # Return local ID instead of raising
    
    # Log operations
    def save_log(
        self, user_id: str, log_data: Dict[str, Any],
        period_start: str, period_end: str,
        adherence: Dict[str, float]
    ) -> str:
        """Save a log entry to logs collection. Tries Firestore first, falls back to local."""
        data = {
            "user_id": user_id,
            "log": log_data,
            "period_start": period_start,
            "period_end": period_end,
            "adherence": adherence,
            "timestamp": datetime.utcnow().isoformat()
        }
        try:
            doc_ref = self.db.collection("logs").document()
            doc_ref.set(data)
            self._save_local_copy("logs", doc_ref.id, data)
            return doc_ref.id
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: save_log")
            print(f"Error: {str(e)}")
            doc_id = f"local_{int(datetime.utcnow().timestamp() * 1000000)}"
            print(f"Saving to local copy: firestore_copy/logs/{doc_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            # Save to local copy even if Firestore fails
            self._save_local_copy("logs", doc_id, data)
            return doc_id  # Return local ID instead of raising


# Global instance
firestore_service = FirestoreService()

