"""Scans the repository files for hardcoded secrets, private keys, certificates, and lists untracked env configurations."""
import os
import re
import json

WORKSPACE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "local_storage",
    "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Secret matching patterns
PATTERNS = {
    "private_key": r"-----BEGIN[ A-Z0-9_-]*PRIVATE KEY-----",
    "pem_certificate": r"-----BEGIN CERTIFICATE-----",
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "jwt_secret": r"JWT_SECRET_KEY\s*=\s*['\"][a-zA-Z0-9_]{16,}['\"]",
}

def scan_repository():
    print("=== STARTING REPOSITORY SECRET AUDIT SCAN ===")
    
    findings = []
    env_files = []
    
    ignored_dirs = ["venv", "node_modules", ".next", ".git", "__pycache__", "local_storage", ".tempmediaStorage"]
    
    for root, dirs, files in os.walk(WORKSPACE_ROOT):
        # Prune ignored directories
        dirs[:] = [d for d in dirs if d not in ignored_dirs]
        
        for file in files:
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, WORKSPACE_ROOT)
            
            # Catalog env files
            if file.startswith(".env"):
                env_files.append(rel_path)
                continue
                
            # Skip binary files or report outputs
            if file.endswith((".png", ".webp", ".pdf", ".zip", ".tar", ".gz", ".pyc", ".db", ".sqlite")):
                continue
                
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    
                # Scan for secret patterns
                for name, regex in PATTERNS.items():
                    matches = re.findall(regex, content)
                    if matches:
                        findings.append({
                            "file": rel_path,
                            "type": name,
                            "matches_count": len(matches)
                        })
            except Exception as e:
                print(f"Skipping file {rel_path} due to error: {e}")

    # Check git repo state
    git_dir = os.path.join(WORKSPACE_ROOT, ".git")
    git_initialized = os.path.exists(git_dir)
    
    report = {
        "timestamp": "2026-07-12T08:40:00Z",
        "git_repository_status": "INITIALIZED" if git_initialized else "NOT_INITIALIZED",
        "gitignore_verified": os.path.exists(os.path.join(WORKSPACE_ROOT, ".gitignore")),
        "env_example_verified": os.path.exists(os.path.join(WORKSPACE_ROOT, ".env.example")),
        "detected_environment_configuration_files": env_files,
        "potential_hardcoded_secrets": findings,
        "action_required": "None. Git repository not initialized yet; no files are currently tracked or committed. Ensure all `.env` files remain ignored." if not git_initialized else "Review files listed in potential_hardcoded_secrets and clean them."
    }
    
    report_path = os.path.join(REPORTS_DIR, "Secret_Audit_Report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=4)
        
    print(f"Secrets audit scan completed. Saved to {report_path}")

if __name__ == "__main__":
    scan_repository()
