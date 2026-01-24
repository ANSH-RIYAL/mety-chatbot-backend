"""
Metrics service for monitoring compute and latency.
Provides RAM usage, latency measurements across API components.
Uses averaging approach for reliable latency measurements.
"""

import os
import time
import psutil
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Callable, List
import config


class MetricsService:
    """Service for measuring compute and latency metrics."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = datetime.utcnow()
    
    # -------------------------------------------------------
    # Helper: Measure average latency over multiple runs
    # (Inspired by colleague's latency.py approach)
    # -------------------------------------------------------
    def _measure_avg(self, fn: Callable, n: int = 3) -> Dict[str, Any]:
        """
        Run a function n times and return average latency.
        
        Args:
            fn: Function to measure (should return something or raise)
            n: Number of runs to average over
        
        Returns:
            Dict with avg_ms, min_ms, max_ms, runs
        """
        times: List[float] = []
        last_error = None
        
        for _ in range(n):
            try:
                start = time.perf_counter()
                fn()
                elapsed = (time.perf_counter() - start) * 1000  # Convert to ms
                times.append(elapsed)
            except Exception as e:
                last_error = str(e)
        
        if not times:
            return {"error": last_error or "All runs failed"}
        
        return {
            "avg_ms": round(sum(times) / len(times), 2),
            "min_ms": round(min(times), 2),
            "max_ms": round(max(times), 2),
            "runs": len(times),
        }
        
    def get_ram_usage(self) -> Dict[str, Any]:
        """Get current RAM usage for this process."""
        try:
            mem_info = self.process.memory_info()
            return {
                "rss_mb": round(mem_info.rss / (1024 * 1024), 2),  # Resident Set Size
                "vms_mb": round(mem_info.vms / (1024 * 1024), 2),  # Virtual Memory Size
                "percent": round(self.process.memory_percent(), 2),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_cpu_usage(self) -> Dict[str, Any]:
        """Get current CPU usage."""
        try:
            return {
                "process_percent": round(self.process.cpu_percent(interval=0.1), 2),
                "system_percent": round(psutil.cpu_percent(interval=0.1), 2),
                "cpu_count": psutil.cpu_count(),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def get_system_memory(self) -> Dict[str, Any]:
        """Get overall system memory."""
        try:
            mem = psutil.virtual_memory()
            return {
                "total_gb": round(mem.total / (1024**3), 2),
                "available_gb": round(mem.available / (1024**3), 2),
                "used_percent": round(mem.percent, 2),
            }
        except Exception as e:
            return {"error": str(e)}
    
    def measure_endpoint_latency(self, base_url: str = "http://localhost:8000", n: int = 3) -> Dict[str, Any]:
        """
        Measure latency for key API endpoints (averaged over n runs).
        
        Returns latency in milliseconds for each endpoint.
        """
        latencies = {}
        
        # Test /health endpoint
        def test_health():
            requests.get(f"{base_url}/health", timeout=5)
        latencies["health"] = self._measure_avg(test_health, n)
        
        # Test /plan/get endpoint (read operation)
        def test_plan_get():
            requests.get(f"{base_url}/plan/get", params={"user_id": "metrics_test_user"}, timeout=10)
        latencies["plan_get"] = self._measure_avg(test_plan_get, n)
        
        return latencies
    
    def measure_firestore_latency(self, n: int = 3) -> Dict[str, Any]:
        """Measure Firestore read/write latency (averaged over n runs)."""
        from services.firestore_service import firestore_service
        
        latencies = {}
        test_user_id = "_metrics_latency_test_"
        
        # Measure write latency
        def test_write():
            firestore_service.create_user(test_user_id, {
                "profile": {"name": "Latency Test"},
                "current_plan": {},
                "target_plan": {},
                "last_updated": datetime.utcnow().isoformat()
            })
        latencies["write"] = self._measure_avg(test_write, n)
        latencies["write"]["operation"] = "create_user"
        
        # Measure read latency
        def test_read():
            firestore_service.get_user(test_user_id)
        latencies["read"] = self._measure_avg(test_read, n)
        latencies["read"]["operation"] = "get_user"
        
        # Cleanup: Delete test user after measurements
        try:
            if firestore_service.db:
                firestore_service.db.collection("users").document(test_user_id).delete()
                latencies["cleanup"] = "success"
            else:
                # Local fallback - delete local file
                import os
                local_path = f"firestore_copy/users/{test_user_id}.json"
                if os.path.exists(local_path):
                    os.remove(local_path)
                latencies["cleanup"] = "success (local)"
        except Exception as e:
            latencies["cleanup"] = f"failed: {str(e)}"
        
        return latencies
    
    def measure_llm_latency(self, n: int = 2) -> Dict[str, Any]:
        """Measure OpenAI API latency (averaged over n runs, default 2 to save API calls)."""
        from services.llm_service import extract_variables_from_text
        
        def test_llm():
            extract_variables_from_text("I drink 5 glasses of water")
        
        result = self._measure_avg(test_llm, n)
        result["operation"] = "extract_variables"
        return result
    
    def measure_prediction_api_latency(self, n: int = 2) -> Dict[str, Any]:
        """Measure external prediction API latency (averaged over n runs)."""
        from services.prediction_api import call_lifespan_api
        
        # Minimal input for latency test
        test_input = {
            "age": 35,
            "gender": 0,
            "cardio": 30,
            "sleep_duration": 7
        }
        
        def test_prediction():
            result = call_lifespan_api(test_input)
            if "error" in result:
                raise Exception(result["error"])
        
        result = self._measure_avg(test_prediction, n)
        result["operation"] = "lifespan_predict"
        return result
    
    def measure_external_gcp_latency(self, gcp_url: str, n: int = 3) -> Dict[str, Any]:
        """
        Measure latency for external GCP Cloud Run endpoints.
        Also fetches remote compute metrics if /health/metrics is available.
        
        Args:
            gcp_url: Base URL of the GCP Cloud Run service (e.g., "https://xxx.a.run.app")
            n: Number of runs to average over
        
        Returns:
            Dict with latency measurements and remote compute data
        """
        result = {
            "gcp_url": gcp_url,
            "endpoint_latency": {},
            "remote_compute": None
        }
        
        # Test /health endpoint
        def test_health():
            requests.get(f"{gcp_url}/health", timeout=10)
        result["endpoint_latency"]["health"] = self._measure_avg(test_health, n)
        
        # Test /chat endpoint (if available)
        def test_chat():
            requests.post(
                f"{gcp_url}/chat",
                json={"user_id": "metrics_test", "message": "test", "options": {"auto_apply_extracted_vars": False}},
                timeout=30
            )
        result["endpoint_latency"]["chat"] = self._measure_avg(test_chat, n)
        
        # Test /plan/get endpoint
        def test_plan_get():
            requests.get(f"{gcp_url}/plan/get", params={"user_id": "metrics_test"}, timeout=10)
        result["endpoint_latency"]["plan_get"] = self._measure_avg(test_plan_get, n)
        
        # Fetch remote compute metrics from /health/metrics endpoint
        try:
            response = requests.get(f"{gcp_url}/health/metrics", timeout=15)
            if response.status_code == 200:
                remote_data = response.json()
                result["remote_compute"] = {
                    "ram": remote_data.get("compute", {}).get("ram"),
                    "cpu": remote_data.get("compute", {}).get("cpu"),
                    "system_memory": remote_data.get("compute", {}).get("system_memory"),
                    "uptime": remote_data.get("uptime"),
                }
            else:
                result["remote_compute"] = {"error": f"Status {response.status_code}"}
        except Exception as e:
            result["remote_compute"] = {"error": str(e), "note": "GCP endpoint may not have /health/metrics"}
        
        return result
    
    def get_uptime(self) -> Dict[str, Any]:
        """Get server uptime."""
        uptime = datetime.utcnow() - self.start_time
        return {
            "started_at": self.start_time.isoformat(),
            "uptime_seconds": round(uptime.total_seconds(), 2),
            "uptime_human": str(uptime).split('.')[0]  # HH:MM:SS format
        }
    
    def get_full_metrics(
        self, 
        include_latency: bool = False, 
        latency_runs: int = 3,
        gcp_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get comprehensive metrics snapshot.
        
        Args:
            include_latency: If True, also measure internal endpoint latencies (slower)
            latency_runs: Number of runs to average latency measurements over
            gcp_url: Optional GCP Cloud Run URL to test external latency
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime": self.get_uptime(),
            "compute": {
                "ram": self.get_ram_usage(),
                "cpu": self.get_cpu_usage(),
                "system_memory": self.get_system_memory(),
            }
        }
        
        if include_latency:
            metrics["latency"] = {
                "firestore": self.measure_firestore_latency(n=latency_runs),
                "llm": self.measure_llm_latency(n=min(latency_runs, 2)),  # Cap at 2 to save API calls
                "prediction_api": self.measure_prediction_api_latency(n=min(latency_runs, 2)),
            }
            metrics["latency_config"] = {
                "runs_per_measurement": latency_runs,
                "note": "Latency values are averaged over multiple runs for reliability"
            }
        
        # Test external GCP endpoints if URL provided
        if gcp_url:
            metrics["external_gcp"] = self.measure_external_gcp_latency(gcp_url, n=latency_runs)
        
        return metrics


# Global instance
metrics_service = MetricsService()