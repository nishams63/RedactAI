import os
import sys
import json
import unittest

# 1. Clean up existing report files to verify fresh generation
workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
backend_dir = os.path.dirname(os.path.abspath(__file__))

for folder in [workspace_dir, backend_dir]:
    for name in ["STARTUP_COMPATIBILITY_REPORT.md", "DEPENDENCY_MANIFEST.json"]:
        path = os.path.join(folder, name)
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass

# 2. Simulate Render Free Tier with all optional dependencies unavailable
from core.optional_dependencies import _MOCK_OVERRIDES
for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr", "reportlab"]:
    _MOCK_OVERRIDES[dep] = False

# 3. Load FastAPI application and lifespan components
from fastapi.testclient import TestClient
from main import app
from core.optional_dependencies import OptionalDependencyManager
from services.legal_ai.embedder import LocalSentenceEmbedder
from services.deep_learning.predictor import LegalBERTClassifier

class TestRenderStartup(unittest.TestCase):
    def setUp(self):
        from core.optional_dependencies import _MOCK_OVERRIDES
        for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr", "reportlab"]:
            _MOCK_OVERRIDES[dep] = False

    def tearDown(self):
        from core.optional_dependencies import _MOCK_OVERRIDES
        _MOCK_OVERRIDES.clear()

    def test_render_deployment_startup(self):
        """Simulate and verify the application startup lifecycle on the Render Free Tier."""
        # Check that OptionalDependencyManager reports everything as unavailable
        for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr", "reportlab"]:
            self.assertFalse(OptionalDependencyManager.is_installed(dep))
        
        # Trigger startup/lifespan events using TestClient
        with TestClient(app) as client:
            # A. Confirm FastAPI liveness returns 200
            response = client.get("/health/liveness")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "alive")

            # B. Confirm API system health check dependencies endpoint returns 200
            response = client.get("/api/v1/system/dependencies")
            self.assertEqual(response.status_code, 200)
            deps_data = response.json()
            # Assert all mocked dependencies are registered as uninstalled
            for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr"]:
                self.assertIn(dep, deps_data)
                self.assertFalse(deps_data[dep]["installed"])
                self.assertEqual(deps_data[dep]["availability"], "Unavailable")

            # C. Verify reports and manifests exist in both backend and workspace root directories
            for folder in [workspace_dir, backend_dir]:
                manifest_path = os.path.join(folder, "DEPENDENCY_MANIFEST.json")
                report_path = os.path.join(folder, "STARTUP_COMPATIBILITY_REPORT.md")
                
                self.assertTrue(os.path.exists(manifest_path), f"Missing DEPENDENCY_MANIFEST.json in {folder}")
                self.assertTrue(os.path.exists(report_path), f"Missing STARTUP_COMPATIBILITY_REPORT.md in {folder}")

                # Verify grade inside manifest matches E (all dependencies missing)
                with open(manifest_path, "r") as f:
                    manifest = json.load(f)
                    self.assertEqual(manifest["grade"], "E")
                    self.assertFalse(manifest["dependencies"]["torch"]["installed"])

            # D. Verify that rule-based fallbacks remain fully functional
            # Sentence embedder should set use_fallback=True
            embedder = LocalSentenceEmbedder()
            self.assertTrue(embedder.use_fallback)
            
            # Predictor should fallback successfully to rule-based prediction without raising ModuleNotFoundError
            classifier = LegalBERTClassifier()
            res = classifier.predict({"text": "confidential contract info"}, "confidential contract info")
            self.assertIn("predicted_class", res)
            self.assertIn("confidence", res)

            # E. Verify PDF generation fails gracefully (503 Service Unavailable) when reportlab is not installed
            pdf_report_path = os.path.join(backend_dir, "local_storage", "reports", "Security_Report.pdf")
            err_path = pdf_report_path.replace(".pdf", "_error.txt")
            for p in [pdf_report_path, err_path]:
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
            
            # Get auth token first
            login_resp = client.post("/api/v1/auth/login", json={
                "email": "admin@redactai.in",
                "password": "Admin@123456"
            })
            self.assertEqual(login_resp.status_code, 200)
            token = login_resp.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}

            response = client.get("/api/v1/security/report/download", headers=headers)
            self.assertEqual(response.status_code, 503)
            self.assertIn("reportlab", response.json()["detail"].lower())

            print("\n=======================================================")
            print("  [PASS] RENDER STARTUP SIMULATION VERIFICATION SUCCESSFUL")
            print("=======================================================\n")

if __name__ == "__main__":
    unittest.main()
