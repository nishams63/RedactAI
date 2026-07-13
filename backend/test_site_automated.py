"""Automated Site Verification Script — Tests all major API endpoints."""
import os
import sys
import json
import time
import requests

BASE_URL = "http://localhost:8000"
API = f"{BASE_URL}/api/v1"

results = {}
token = None
headers = {}


def log_result(test_name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results[test_name] = {"status": status, "detail": detail}
    icon = "[PASS]" if passed else "[FAIL]"
    print(f"  {icon} {test_name}: {detail}")


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def run_tests():
    global token, headers

    print("=" * 60)
    print("  REDACTAI AUTOMATED SITE VERIFICATION")
    print(f"  Target: {BASE_URL}")
    print(f"  Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # ========================================================
    section("1. HEALTH & LIVENESS CHECKS")
    # ========================================================

    # Health endpoint (root-level in main.py)
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=10)
        log_result("GET /health", r.status_code == 200,
                   f"Status: {r.status_code}, Body: {r.json()}")
    except Exception as e:
        log_result("GET /health", False, str(e))

    # Liveness endpoint (root-level in main.py)
    try:
        r = requests.get(f"{BASE_URL}/health/liveness", timeout=10)
        log_result("GET /health/liveness", r.status_code == 200,
                   f"Status: {r.status_code}, Body: {r.json()}")
    except Exception as e:
        log_result("GET /health/liveness", False, str(e))

    # System dependencies (mounted at /api/v1/system/dependencies)
    try:
        r = requests.get(f"{API}/system/dependencies", timeout=10)
        log_result("GET /api/v1/system/dependencies", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /api/v1/system/dependencies", False, str(e))

    # Release liveness (mounted at /api/v1/release/health/liveness)
    try:
        r = requests.get(f"{API}/release/health/liveness", timeout=10)
        log_result("GET /api/v1/release/health/liveness", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /api/v1/release/health/liveness", False, str(e))

    # ========================================================
    section("2. AUTHENTICATION")
    # ========================================================

    # Login as Admin
    try:
        r = requests.post(f"{API}/auth/login", json={
            "email": "admin@redactai.in",
            "password": "Admin@123456"
        }, timeout=10)
        if r.status_code == 200:
            token = r.json().get("access_token")
            headers = {"Authorization": f"Bearer {token}"}
            log_result("POST /auth/login (Admin)", True, "Token acquired")
        else:
            log_result("POST /auth/login (Admin)", False,
                       f"Status: {r.status_code}, Body: {r.text[:200]}")
    except Exception as e:
        log_result("POST /auth/login (Admin)", False, str(e))

    if not token:
        print("\n[FATAL] Cannot proceed without authentication token.")
        return

    # Get current user — roles is list[str] per schema
    try:
        r = requests.get(f"{API}/users/me", headers=headers, timeout=10)
        if r.status_code == 200:
            user = r.json()
            log_result("GET /users/me", True,
                       f"User: {user.get('email')}, Roles: {user.get('roles', [])}")
        else:
            log_result("GET /users/me", False, f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /users/me", False, str(e))

    # Unauthorized access must be blocked
    try:
        r = requests.get(f"{API}/documents", timeout=10)
        log_result("Unauthorized access blocked", r.status_code in (401, 403),
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("Unauthorized access blocked", False, str(e))

    # ========================================================
    section("3. DASHBOARD & DOCUMENTS")
    # ========================================================

    # Dashboard stats
    try:
        r = requests.get(f"{API}/documents/dashboard", headers=headers, timeout=10)
        log_result("GET /documents/dashboard", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /documents/dashboard", False, str(e))

    # Document listing
    doc_id = None
    try:
        r = requests.get(f"{API}/documents", headers=headers, timeout=10)
        if r.status_code == 200:
            docs = r.json().get("documents", [])
            if docs:
                doc_id = docs[0].get("id")
            log_result("GET /documents", True, f"Found {len(docs)} documents")
        else:
            log_result("GET /documents", False, f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /documents", False, str(e))

    # Document upload
    try:
        pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "sample_indian_nda.pdf")
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                content = f.read()
        else:
            content = b"%PDF-1.5\n%..."
        files = {"file": ("test_upload.pdf", content, "application/pdf")}
        data = {"title": "Automated Test Upload"}
        r = requests.post(f"{API}/documents/upload", files=files, data=data,
                          headers=headers, timeout=30)
        if r.status_code == 201:
            uploaded = r.json().get("document", {}).get("id")
            if uploaded:
                doc_id = uploaded
            log_result("POST /documents/upload", True,
                       f"Uploaded doc ID: {uploaded}")
        elif r.status_code == 400 and "duplicate" in r.text.lower():
            log_result("POST /documents/upload", True,
                       f"Duplicate blocked (expected): {r.status_code}")
        else:
            log_result("POST /documents/upload", False,
                       f"Status: {r.status_code}, Body: {r.text[:200]}")
    except Exception as e:
        log_result("POST /documents/upload", False, str(e))

    # ========================================================
    section("4. DOCUMENT DETAIL (OCR VERIFICATION)")
    # ========================================================

    if doc_id:
        try:
            r = requests.get(f"{API}/documents/{doc_id}", headers=headers, timeout=10)
            if r.status_code == 200:
                doc_data = r.json()
                log_result("GET /documents/<id> (detail)", True,
                           f"Title: {doc_data.get('title')}, Status: {doc_data.get('status')}")
            else:
                log_result("GET /documents/<id> (detail)", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("GET /documents/<id> (detail)", False, str(e))
    else:
        log_result("GET /documents/<id> (detail)", False, "No document available")

    # Local preview auth checks
    if doc_id:
        try:
            r = requests.get(f"{API}/documents/local-preview/uploads/{doc_id}/test_upload.pdf?token={token}", timeout=10)
            log_result("GET /documents/local-preview (Query token auth)", r.status_code != 401, f"Status: {r.status_code}")
        except Exception as e:
            log_result("GET /documents/local-preview (Query token auth)", False, str(e))

    # ========================================================
    section("5. ML PREDICTION")
    # ========================================================

    # ML model listing
    try:
        r = requests.get(f"{API}/ml/models", headers=headers, timeout=10)
        log_result("GET /ml/models", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /ml/models", False, str(e))

    if doc_id:
        try:
            r = requests.post(f"{API}/ml/predict/{doc_id}", headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /ml/predict/<id>", True,
                           f"Label: {data.get('predicted_label')}, Score: {data.get('sensitivity_score')}")
            else:
                log_result("POST /ml/predict/<id>", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /ml/predict/<id>", False, str(e))

    # ML evaluation
    try:
        r = requests.get(f"{API}/ml/evaluation", headers=headers, timeout=10)
        log_result("GET /ml/evaluation", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /ml/evaluation", False, str(e))

    # ========================================================
    section("6. DL PREDICTION")
    # ========================================================

    # DL model listing
    try:
        r = requests.get(f"{API}/dl/models", headers=headers, timeout=10)
        log_result("GET /dl/models", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /dl/models", False, str(e))

    if doc_id:
        try:
            r = requests.post(f"{API}/dl/predict/{doc_id}", headers=headers, timeout=120)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /dl/predict/<id>", True,
                           f"Label: {data.get('predicted_label')}, Score: {data.get('sensitivity_score')}")
            else:
                log_result("POST /dl/predict/<id>", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /dl/predict/<id>", False, str(e))

    # DL evaluation
    try:
        r = requests.get(f"{API}/dl/evaluation", headers=headers, timeout=10)
        log_result("GET /dl/evaluation", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /dl/evaluation", False, str(e))

    # ========================================================
    section("7. LEGAL AI")
    # ========================================================

    # Knowledge Base
    try:
        r = requests.get(f"{API}/legal/knowledge", headers=headers, timeout=10)
        if r.status_code == 200:
            kb = r.json()
            log_result("GET /legal/knowledge", True,
                       f"Total chunks: {kb.get('total_chunks')}")
        else:
            log_result("GET /legal/knowledge", False, f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /legal/knowledge", False, str(e))

    if doc_id:
        # Clause Analysis
        try:
            r = requests.post(f"{API}/legal/analyze/{doc_id}", headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /legal/analyze/<id>", True,
                           f"Clauses: {len(data.get('clauses', []))}")
            else:
                log_result("POST /legal/analyze/<id>", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /legal/analyze/<id>", False, str(e))

        # Compliance
        try:
            r = requests.post(f"{API}/legal/compliance/{doc_id}",
                              headers=headers, timeout=60)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /legal/compliance/<id>", True,
                           f"Score: {data.get('compliance_score')}, Status: {data.get('compliance_status')}")
            else:
                log_result("POST /legal/compliance/<id>", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /legal/compliance/<id>", False, str(e))

        # Summarization (SLM — can take up to 120s on cold start)
        try:
            r = requests.post(f"{API}/legal/summarize/{doc_id}",
                              headers=headers, timeout=300)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /legal/summarize/<id>", True,
                           f"Engine: {data.get('reasoning_engine')}")
            else:
                log_result("POST /legal/summarize/<id>", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /legal/summarize/<id>", False, str(e))

        # Q&A Chat (RAG + SLM — can take up to 120s)
        try:
            r = requests.post(f"{API}/legal/chat", json={
                "document_id": str(doc_id),
                "question": "What is the penalty under IT Act Section 72A?"
            }, headers=headers, timeout=300)
            if r.status_code == 200:
                data = r.json()
                log_result("POST /legal/chat (RAG Q&A)", True,
                           f"Engine: {data.get('reasoning_engine')}, Confidence: {data.get('confidence_score')}")
            else:
                log_result("POST /legal/chat (RAG Q&A)", False,
                           f"Status: {r.status_code}")
        except Exception as e:
            log_result("POST /legal/chat (RAG Q&A)", False, str(e))

    # Legal model info
    try:
        r = requests.get(f"{API}/legal/models", headers=headers, timeout=10)
        log_result("GET /legal/models", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /legal/models", False, str(e))

    # ========================================================
    section("8. SECURITY DASHBOARD")
    # ========================================================

    try:
        r = requests.get(f"{API}/security/stats", headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            log_result("GET /security/stats", True,
                       f"Score: {data.get('score', {}).get('total')}/100")
        else:
            log_result("GET /security/stats", False, f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /security/stats", False, str(e))

    try:
        r = requests.get(f"{API}/security/sessions", headers=headers, timeout=10)
        if r.status_code == 200:
            sessions = r.json()
            log_result("GET /security/sessions", True,
                       f"Active sessions: {len(sessions)}")
        else:
            log_result("GET /security/sessions", False, f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /security/sessions", False, str(e))

    try:
        r = requests.get(f"{API}/security/audit", headers=headers, timeout=10)
        log_result("GET /security/audit", r.status_code == 200,
                   f"Status: {r.status_code}")
    except Exception as e:
        log_result("GET /security/audit", False, str(e))

    try:
        r = requests.post(f"{API}/security/test", headers=headers, timeout=30)
        if r.status_code == 200:
            data = r.json()
            log_result("POST /security/test (OWASP Suite)", True,
                       f"Tests: {data.get('tests_run')}, Passed: {data.get('passed')}, Failed: {data.get('failed')}")
        else:
            log_result("POST /security/test (OWASP Suite)", False,
                       f"Status: {r.status_code}")
    except Exception as e:
        log_result("POST /security/test (OWASP Suite)", False, str(e))

    try:
        r = requests.get(f"{API}/security/report/download", headers=headers, timeout=15)
        log_result("GET /security/report/download (PDF)", r.status_code == 200,
                   f"Status: {r.status_code}, Content-Type: {r.headers.get('content-type', 'N/A')}")
    except Exception as e:
        log_result("GET /security/report/download (PDF)", False, str(e))

    # ========================================================
    section("9. RBAC ENFORCEMENT")
    # ========================================================

    # Register a Viewer user dynamically, then test RBAC
    try:
        r = requests.post(f"{API}/auth/register", json={
            "email": "testviewer@redactai.in",
            "password": "Viewer@123456",
            "full_name": "Test Viewer"
        }, timeout=10)
        if r.status_code in (201, 200):
            viewer_token = r.json().get("access_token")
            log_result("POST /auth/register (Viewer)", True, "Viewer user created")
        elif r.status_code in (400, 409) or "exist" in r.text.lower():
            # Already exists — login instead
            r2 = requests.post(f"{API}/auth/login", json={
                "email": "testviewer@redactai.in",
                "password": "Viewer@123456"
            }, timeout=10)
            if r2.status_code == 200:
                viewer_token = r2.json().get("access_token")
                log_result("POST /auth/login (Viewer)", True, "Viewer login OK")
            else:
                viewer_token = None
                log_result("POST /auth/login (Viewer)", False,
                           f"Status: {r2.status_code}")
        else:
            viewer_token = None
            log_result("POST /auth/register (Viewer)", False,
                       f"Status: {r.status_code}, Body: {r.text[:200]}")

        if viewer_token:
            viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

            # Viewer blocked from security audit (Admin-only)
            r3 = requests.get(f"{API}/security/audit", headers=viewer_headers, timeout=10)
            log_result("RBAC: Non-admin blocked from /security/audit",
                       r3.status_code == 403, f"Status: {r3.status_code}")

            # Viewer blocked from security tests (Admin-only)
            r4 = requests.post(f"{API}/security/test", headers=viewer_headers, timeout=10)
            log_result("RBAC: Non-admin blocked from /security/test",
                       r4.status_code == 403, f"Status: {r4.status_code}")
    except Exception as e:
        log_result("RBAC tests", False, str(e))

    # ========================================================
    # FINAL SUMMARY
    # ========================================================
    print("\n")
    print("=" * 60)
    print("  VERIFICATION SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v["status"] == "PASS")
    failed = sum(1 for v in results.values() if v["status"] == "FAIL")
    total = len(results)

    print(f"\n  Total Tests: {total}")
    print(f"  Passed:      {passed}")
    print(f"  Failed:      {failed}")
    print(f"  Pass Rate:   {round(passed / total * 100, 1)}%")

    if failed > 0:
        print(f"\n  FAILED TESTS:")
        for name, data in results.items():
            if data["status"] == "FAIL":
                print(f"    [FAIL] {name}: {data['detail']}")

    if passed == total:
        grade = "A+"
    elif failed <= 1:
        grade = "A"
    elif failed <= 2:
        grade = "B"
    elif failed <= 4:
        grade = "C"
    else:
        grade = "D"

    print(f"\n  Site Grade: {grade}")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
