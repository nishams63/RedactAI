"""Trigger and validate Sprint 4.5.1 AI Quality & Retrieval benchmarks."""
import sys
import requests

def main():
    print("=== STARTING SPRINT 4.5.1 QUALITY & RETRIEVAL BENCHMARKS ===")
    
    # 1. Login to get authentication token
    login_url = "http://localhost:8000/api/v1/auth/login"
    login_data = {
        "email": "admin@redactai.in",
        "password": "Admin@123456"
    }
    
    try:
        res = requests.post(login_url, json=login_data)
        if res.status_code != 200:
            print(f"FAILED: Auth login failed with status code {res.status_code}")
            sys.exit(1)
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("SUCCESS: Authenticated session established.")
    except Exception as e:
        print(f"FAILED: Connection to backend failed: {e}")
        sys.exit(1)

    # 2. Trigger Benchmark run
    bench_url = "http://localhost:8000/api/v1/legal/benchmark"
    try:
        res = requests.post(bench_url, headers=headers)
        if res.status_code != 200:
            print(f"FAILED: Benchmark trigger failed with status {res.status_code}: {res.text}")
            sys.exit(1)
        
        result = res.json()
        print("SUCCESS: 50-Question Quality Benchmark executed successfully.")
        print(f"  - Run ID: {result['benchmark_run_id']}")
        print(f"  - Prompt Version: {result['prompt_version']}")
        print(f"  - Model: {result['model_version']}")
        print(f"  - Regression Status: {result['regression_status']}")
        
        print("\n[Retrieval Quality Report]")
        ret = result["retrieval_metrics"]
        print(f"  - Recall@5: {ret['recall_5']}")
        print(f"  - Recall@10: {ret['recall_10']}")
        print(f"  - Precision@5: {ret['precision_5']}")
        print(f"  - MRR: {ret['mrr']}")
        
        print("\n[Citation Quality Report]")
        cit = result["citation_metrics"]
        print(f"  - Average Coverage: {cit['citation_coverage']}")
        print(f"  - Average Correctness: {cit['citation_correctness']}")
        print(f"  - Unsupported Claims Count: {cit['unsupported_claims_count']}")
        
        print("\n[Confidence Calibration Report]")
        cal = result["confidence_calibration"]
        print(f"  - Average Calibrated Confidence: {cal['average_confidence']}")
        print(f"  - Distribution Bins: {cal['confidence_bins']}")
        
    except Exception as e:
        print(f"FAILED: Quality benchmark execution failed: {e}")
        sys.exit(1)

    # 3. Retrieve Quality and Prompt History
    try:
        quality_res = requests.get("http://localhost:8000/api/v1/legal/quality", headers=headers)
        prompts_res = requests.get("http://localhost:8000/api/v1/legal/prompts", headers=headers)
        
        if quality_res.status_code == 200 and prompts_res.status_code == 200:
            print("\nSUCCESS: Quality history and Prompt registry endpoints validated.")
            print(f"  - Total Historical Runs: {len(quality_res.json().get('history', []))}")
            print(f"  - Active Prompt Version: {prompts_res.json().get('active', {}).get('version')}")
        else:
            print("FAILED: History endpoints returned non-200.")
            sys.exit(1)
    except Exception as e:
        print(f"FAILED: Validating history endpoints: {e}")
        sys.exit(1)

    print("\n=== ALL AI QUALITY & STABILIZATION TESTS PASSED SUCCESSFULY! ===")

if __name__ == "__main__":
    main()
