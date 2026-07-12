"""Validation Script for Level 3 Legal AI & SLM components."""
import sys
import os
import requests
import json

def run_validation():
    print("=== STARTING LEVEL 3 LEGAL AI VALIDATION ===")
    
    # 1. Login and get token
    login_url = "http://localhost:8000/api/v1/auth/login"
    try:
        res = requests.post(login_url, json={"email": "admin@redactai.in", "password": "Admin@123456"})
        if res.status_code != 200:
            print(f"FAILED: Seed login failed with status {res.status_code}")
            sys.exit(1)
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"FAILED: Connection to local server failed: {e}")
        sys.exit(1)
        
    print("SUCCESS: Authenticated session established.")

    # 2. Verify Knowledge Base retrieval
    kb_url = "http://localhost:8000/api/v1/legal/knowledge"
    res = requests.get(kb_url, headers=headers)
    if res.status_code == 200 and res.json()["total_chunks"] == 12:
        print(f"SUCCESS: Versioned Knowledge Base loaded. Found {res.json()['total_chunks']} chunks.")
    else:
        print(f"FAILED: Knowledge Base load error: {res.status_code} ({res.text})")
        sys.exit(1)

    # 3. Retrieve documents to perform tests
    doc_url = "http://localhost:8000/api/v1/documents"
    res = requests.get(doc_url, headers=headers)
    docs = res.json().get("documents", [])
    if not docs:
        print("FAILED: No processed documents available for testing. Upload a document first.")
        sys.exit(1)
        
    test_doc = docs[0]
    print(f"Using document '{test_doc['title']}' (ID: {test_doc['id']}) for downstream validation.")

    # 4. Validate Clause Analysis
    anal_url = f"http://localhost:8000/api/v1/legal/analyze/{test_doc['id']}"
    res = requests.post(anal_url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"SUCCESS: Clause analysis generated. Extracted {len(data['clauses'])} clauses.")
    else:
        print(f"FAILED: Clause analysis endpoint failed: {res.status_code}")
        sys.exit(1)

    # 5. Validate Compliance Engine
    comp_url = f"http://localhost:8000/api/v1/legal/compliance/{test_doc['id']}"
    res = requests.post(comp_url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"SUCCESS: Compliance Engine ran. Score: {data['compliance_score']}, Status: {data['compliance_status']}.")
    else:
        print(f"FAILED: Compliance endpoint failed: {res.status_code}")
        sys.exit(1)

    # 6. Validate Document Summarization
    sum_url = f"http://localhost:8000/api/v1/legal/summarize/{test_doc['id']}"
    res = requests.post(sum_url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        print(f"SUCCESS: Document summarizer complete.")
        print(f"  - Reasoning Engine Used: {data['reasoning_engine']}")
    else:
        print(f"FAILED: Summarization endpoint failed: {res.status_code}")
        sys.exit(1)

    # 7. Validate Q&A Chat & Citations
    chat_url = "http://localhost:8000/api/v1/legal/chat"
    chat_payload = {
        "document_id": str(test_doc["id"]),
        "question": "What is the penalty under IT Act Section 72A?"
    }
    res = requests.post(chat_url, json=chat_payload, headers=headers)
    if res.status_code == 200:
        data = res.json()
        print("SUCCESS: Explainable RAG Q&A completed.")
        print(f"  - Reasoning Engine: {data['reasoning_engine']}")
        print(f"  - Confidence Score: {data['confidence_score']}")
        print(f"  - Citations validated: {len(data['citations'])}")
    else:
        print(f"FAILED: Q&A chat endpoint failed: {res.status_code}")
        sys.exit(1)

    # 8. Validate Human Review logging
    review_url = "http://localhost:8000/api/v1/legal/review"
    review_payload = {
        "document_id": str(test_doc["id"]),
        "category": "COMPLIANCE",
        "ai_recommendation": {"score": 90},
        "reviewer_decision": "APPROVED",
        "reviewer_comments": "Validated compliant layout.",
        "final_decision": {"score": 90}
    }
    res = requests.post(review_url, json=review_payload, headers=headers)
    if res.status_code == 200:
        print("SUCCESS: Human Review workflow submitted and logged to feedback database.")
    else:
        print(f"FAILED: Human Review submission failed: {res.status_code}")
        sys.exit(1)

    print("=== ALL LEVEL 3 LEGAL AI COMPONENT VALIDATIONS PASSED SUCCESSFULY! ===")

if __name__ == "__main__":
    run_validation()
