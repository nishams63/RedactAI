from database.session import SessionLocal
from services.legal_ai.security_checker import SecurityChecker

db = SessionLocal()
checker = SecurityChecker(db)
print("Executing security checker suite...")
print(checker.execute_security_tests())
db.close()
print("Vulnerability suite tests executed successfully.")
