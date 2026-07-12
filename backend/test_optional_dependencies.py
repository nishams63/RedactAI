import sys
import unittest

# Force importing dependencies through optional dependencies overrides
from core.optional_dependencies import _MOCK_OVERRIDES, OptionalDependencyManager

class TestOptionalDependencies(unittest.TestCase):
    def setUp(self):
        _MOCK_OVERRIDES.clear()

    def tearDown(self):
        _MOCK_OVERRIDES.clear()

    def test_all_dependencies_present(self):
        # Simulate all dependencies present
        for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr"]:
            _MOCK_OVERRIDES[dep] = True
        
        for dep in _MOCK_OVERRIDES:
            self.assertTrue(OptionalDependencyManager.is_installed(dep))
        
        status = OptionalDependencyManager.get_all_status()
        self.assertEqual(status["torch"]["availability"], "Available")

    def test_all_dependencies_missing(self):
        # Simulate all dependencies missing
        for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr"]:
            _MOCK_OVERRIDES[dep] = False
            
        for dep in _MOCK_OVERRIDES:
            self.assertFalse(OptionalDependencyManager.is_installed(dep))
            
        status = OptionalDependencyManager.get_all_status()
        self.assertEqual(status["torch"]["availability"], "Unavailable")

    def test_router_imports_without_torch(self):
        # With torch unavailable, importing routers should not raise any ModuleNotFoundError
        for dep in ["torch", "transformers", "sentence_transformers", "onnxruntime", "xgboost", "spacy", "easyocr", "paddleocr"]:
            _MOCK_OVERRIDES[dep] = False

        # Clear existing modules to force re-evaluation of imports
        for m in list(sys.modules.keys()):
            if m.startswith("api.v1") or m.startswith("services.deep_learning"):
                del sys.modules[m]

        try:
            from api.v1.router import api_v1_router
            self.assertIsNotNone(api_v1_router)
        except Exception as e:
            self.fail(f"Application failed to import or initialize with mocked missing dependencies: {e}")

if __name__ == "__main__":
    unittest.main()
