import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from google.cloud import firestore
from google.oauth2 import service_account
import config


class FirestoreService:
    def __init__(self):
        self.copy_dir = "firestore_copy"
        os.makedirs(self.copy_dir, exist_ok=True)
        for subdir in ["users", "chat_history", "plans_history", "logs"]:
            os.makedirs(os.path.join(self.copy_dir, subdir), exist_ok=True)
        try:
            print("Looking for Firestore credentials at:", config.FIRESTORE_CREDENTIALS)
            print("Absolute path:", os.path.abspath(config.FIRESTORE_CREDENTIALS))

            if os.path.exists(config.FIRESTORE_CREDENTIALS):
                # Local development: use the JSON credentials file
                print("[FIRESTORE] Using credentials file")
                credentials = service_account.Credentials.from_service_account_file(
                    config.FIRESTORE_CREDENTIALS
                )
                self.db = firestore.Client(
                    credentials=credentials,
                    project=credentials.project_id
                )
            else:
                # Cloud Run: use Application Default Credentials with chatbot-display project
                project_id = os.getenv("GCP_PROJECT_ID") or os.getenv("GOOGLE_CLOUD_PROJECT") or "chatbot-display"
                print(f"[FIRESTORE] No credentials file found. Using Application Default Credentials with project: {project_id}")
                self.db = firestore.Client(project=project_id)

            self.firestore_enabled = True
            print("[FIRESTORE] Connection successful!")
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
        try:
            file_path = os.path.join(self.copy_dir, collection, f"{doc_id}.json")
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Warning: Failed to save local copy: {e}")
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
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
            try:
                file_path = os.path.join(self.copy_dir, "users", f"{user_id}.json")
                if os.path.exists(file_path):
                    with open(file_path, "r") as f:
                        return json.load(f)
            except Exception as local_err:
                print(f"Warning: Could not load local copy: {local_err}")
            return None
    
    def create_user(self, user_id: str, data: Dict[str, Any]) -> None:
        data["last_updated"] = datetime.utcnow().isoformat()
        try:
            self.db.collection("users").document(user_id).set(data)
            self._save_local_copy("users", user_id, data)
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: create_user")
            print(f"Error: {str(e)}")
            print(f"Saving to local copy only: firestore_copy/users/{user_id}.json")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
            self._save_local_copy("users", user_id, data)
    
    def update_user_profile(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        try:
            user_ref = self.db.collection("users").document(user_id)
            update_data = {
                "profile": profile_data,
                "last_updated": datetime.utcnow().isoformat()
            }
            user_ref.update(update_data)
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
            existing = self.get_user(user_id) or {}
            existing.update({"profile": profile_data, "last_updated": datetime.utcnow().isoformat()})
            self._save_local_copy("users", user_id, existing)
    
    def update_user_plan(self, user_id: str, plan_type: str, plan_data: Dict[str, Any]) -> None:
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
            existing = self.get_user(user_id) or {}
            existing[plan_type] = plan_data.copy() if isinstance(plan_data, dict) else plan_data
            existing["last_updated"] = datetime.utcnow().isoformat()
            self._save_local_copy("users", user_id, existing)
            print(f"[FIRESTORE] Saved {plan_type} with {len(plan_data)} keys: {list(plan_data.keys())[:10]}")
            print(f"[FIRESTORE] Full {plan_type} data: {plan_data}")
    
    def update_user_vars_extracted(self, user_id: str, vars_data: Dict[str, Any]) -> None:
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
            existing = self.get_user(user_id) or {}
            existing.update({"vars_extracted": vars_data, "last_updated": datetime.utcnow().isoformat()})
            self._save_local_copy("users", user_id, existing)
    
    def persist_chat_message(
        self, user_id: str, role: str, text: str
    ) -> str:
        data = {
            "user_id": user_id,
            "role": role,
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        }
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
            self._save_local_copy("chat_history", doc_id, data)
            return doc_id
    
    def get_chat_history(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
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
        try:
            if self.firestore_enabled and self.db:
                docs = (
                    self.db.collection("chat_history")
                    .where("user_id", "==", user_id)
                    .stream()
                )
                for doc in docs:
                    doc.reference.delete()
                print(f"Cleared chat history for user {user_id} from Firestore")
            else:
                raise Exception("Firestore not enabled")
        except Exception as e:
            print(f"\n{'='*60}")
            print(f"FIRESTORE CONNECTION FAILED: clear_chat_history")
            print(f"Error: {str(e)}")
            print(f"Clearing local copies from firestore_copy/chat_history/")
            print(f"ACTION REQUIRED: Fix Firestore connection")
            print(f"{'='*60}\n")
        try:
            import glob
            pattern = os.path.join(self.copy_dir, "chat_history", f"*_{user_id}_*.json")
            for file_path in glob.glob(pattern):
                os.remove(file_path)
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
            print(f"Warning: Failed to clear local chat history: {e}")
    
    def log_plan_change(
        self, user_id: str, diff: Dict[str, Any], source: str = "ui"
    ) -> str:
        data = {
            "user_id": user_id,
            "diff": diff,
            "timestamp": datetime.utcnow().isoformat(),
            "source": source
        }
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
            self._save_local_copy("plans_history", doc_id, data)
            return doc_id
    
    def save_log(
        self, user_id: str, log_data: Dict[str, Any],
        period_start: str, period_end: str,
        adherence: Dict[str, float]
    ) -> str:
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
            self._save_local_copy("logs", doc_id, data)
            return doc_id


firestore_service = FirestoreService()
