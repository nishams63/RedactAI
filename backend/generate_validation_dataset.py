import os
import json
import uuid
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from pypdf import PdfWriter, PdfReader
from PIL import Image

DATASET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "validation_dataset")
ROBUSTNESS_DIR = os.path.join(DATASET_DIR, "robustness")

os.makedirs(DATASET_DIR, exist_ok=True)
for sub in ["nda", "employment_contract", "service_agreement", "invoice", "government_form", "medical_record", "court_order"]:
    os.makedirs(os.path.join(DATASET_DIR, sub), exist_ok=True)
for sub in ["scanned_pdf", "digital_pdf", "image_only", "corrupted", "password_protected", "large_pdf"]:
    os.makedirs(os.path.join(ROBUSTNESS_DIR, sub), exist_ok=True)


def create_simple_pdf(filename, title, content_list):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>{title}</b>", styles["Heading1"]), Spacer(1, 10)]
    for text in content_list:
        story.append(Paragraph(text, styles["Normal"]))
        story.append(Spacer(1, 6))
    doc.build(story)


def create_large_pdf(filename, title, pages_count=101):
    doc = SimpleDocTemplate(filename, pagesize=letter)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"<b>{title}</b>", styles["Heading1"]), Spacer(1, 10)]
    for i in range(1, pages_count + 1):
        story.append(Paragraph(f"Page {i} of this large legal file containing mock public text.", styles["Normal"]))
        story.append(Spacer(1, 6))
        from reportlab.platypus import PageBreak
        story.append(PageBreak())
    doc.build(story)


print("Generating versioned validation dataset...")

# 1. NDA
nda_path = os.path.join(DATASET_DIR, "nda", "nda_1.pdf")
nda_content = [
    "MUTUAL NON-DISCLOSURE AGREEMENT",
    "This Non-Disclosure Agreement ('Agreement') is entered into by and between Acme Corporation, located at Bangalore, Karnataka, and John Doe, residing in Mumbai, Maharashtra.",
    "Aadhaar Number of John Doe is 1234-5678-9012. PAN card is ABCDE1234F. Phone: +91 98765 43210. Email: john.doe@example.com.",
    "The parties agree to keep all proprietary business information confidential. Any leak of these private documents will lead to legal action."
]
create_simple_pdf(nda_path, "Mutual NDA Agreement", nda_content)

nda_gt = {
    "expected_sensitivity": "Confidential",
    "expected_risk_level": "HIGH",
    "expected_entities": [
        {"entity_type": "ORGANIZATION", "value": "Acme Corporation"},
        {"entity_type": "PERSON", "value": "John Doe"},
        {"entity_type": "AADHAAR", "value": "1234-5678-9012"},
        {"entity_type": "PAN", "value": "ABCDE1234F"},
        {"entity_type": "EMAIL", "value": "john.doe@example.com"},
        {"entity_type": "PHONE", "value": "+91 98765 43210"}
    ],
    "ground_truth_text": " ".join(nda_content)
}
with open(os.path.join(DATASET_DIR, "nda", "nda_1.gt.json"), "w") as f:
    json.dump(nda_gt, f, indent=2)

# 2. Employment Contract
emp_path = os.path.join(DATASET_DIR, "employment_contract", "emp_1.pdf")
emp_content = [
    "EMPLOYMENT CONTRACT AGREEMENT",
    "This contract is signed between TechSolutions Pvt Ltd, Bangalore, and Jane Smith, residing at Pune, Maharashtra.",
    "Salary packages: INR 15,00,000 per annum. Bank Account details: HDFC Bank A/c 501001234567, IFSC HDFC0000123.",
    "The employee shall start on 2026-07-15 as Senior Developer."
]
create_simple_pdf(emp_path, "Employment Agreement", emp_content)

emp_gt = {
    "expected_sensitivity": "Confidential",
    "expected_risk_level": "HIGH",
    "expected_entities": [
        {"entity_type": "ORGANIZATION", "value": "TechSolutions Pvt Ltd"},
        {"entity_type": "PERSON", "value": "Jane Smith"},
        {"entity_type": "BANK_ACCOUNT", "value": "501001234567"},
        {"entity_type": "IFSC", "value": "HDFC0000123"}
    ],
    "ground_truth_text": " ".join(emp_content)
}
with open(os.path.join(DATASET_DIR, "employment_contract", "emp_1.gt.json"), "w") as f:
    json.dump(emp_gt, f, indent=2)

# 3. Service Agreement
service_path = os.path.join(DATASET_DIR, "service_agreement", "service_1.pdf")
service_content = [
    "MASTER SERVICES AGREEMENT",
    "This Agreement is made between CloudBuilders Inc and ClientCorp India.",
    "Scope: Cloud migration services for global deployment. No sensitive personal information will be exchanged.",
    "The terms of services shall be governed by the laws of India."
]
create_simple_pdf(service_path, "Service Agreement", service_content)

service_gt = {
    "expected_sensitivity": "Internal",
    "expected_risk_level": "MEDIUM",
    "expected_entities": [
        {"entity_type": "ORGANIZATION", "value": "CloudBuilders Inc"},
        {"entity_type": "ORGANIZATION", "value": "ClientCorp India"}
    ],
    "ground_truth_text": " ".join(service_content)
}
with open(os.path.join(DATASET_DIR, "service_agreement", "service_1.gt.json"), "w") as f:
    json.dump(service_gt, f, indent=2)

# 4. Invoice
invoice_path = os.path.join(DATASET_DIR, "invoice", "invoice_1.pdf")
invoice_content = [
    "TAX INVOICE",
    "Invoice No: INV-2026-0091. Date: 2026-07-01. Vendor: OfficeSupplies Ltd.",
    "Bill To: admin@redactai.in. Total Amount Due: INR 45,200.00.",
    "Transfer to account HDFC Bank A/c 99912345678, IFSC HDFC0000999."
]
create_simple_pdf(invoice_path, "Tax Invoice", invoice_content)

invoice_gt = {
    "expected_sensitivity": "Internal",
    "expected_risk_level": "MEDIUM",
    "expected_entities": [
        {"entity_type": "EMAIL", "value": "admin@redactai.in"},
        {"entity_type": "BANK_ACCOUNT", "value": "99912345678"},
        {"entity_type": "IFSC", "value": "HDFC0000999"}
    ],
    "ground_truth_text": " ".join(invoice_content)
}
with open(os.path.join(DATASET_DIR, "invoice", "invoice_1.gt.json"), "w") as f:
    json.dump(invoice_gt, f, indent=2)

# 5. Government Form
gov_path = os.path.join(DATASET_DIR, "government_form", "gov_1.pdf")
gov_content = [
    "GOVERNMENT OF INDIA - FORM 16 / TAX RETRIEVAL",
    "Permanent Account Number (PAN): FGHIJ5678K.",
    "Name of Taxpayer: Rajesh Kumar. Aadhaar Card Number: 9876-5432-1098.",
    "Address: Flat 201, Shanti Apartments, New Delhi, 110001."
]
create_simple_pdf(gov_path, "Form 16 Tax Statement", gov_content)

gov_gt = {
    "expected_sensitivity": "Confidential",
    "expected_risk_level": "HIGH",
    "expected_entities": [
        {"entity_type": "PAN", "value": "FGHIJ5678K"},
        {"entity_type": "PERSON", "value": "Rajesh Kumar"},
        {"entity_type": "AADHAAR", "value": "9876-5432-1098"},
        {"entity_type": "PIN_CODE", "value": "110001"}
    ],
    "ground_truth_text": " ".join(gov_content)
}
with open(os.path.join(DATASET_DIR, "government_form", "gov_1.gt.json"), "w") as f:
    json.dump(gov_gt, f, indent=2)

# 6. Medical Record
med_path = os.path.join(DATASET_DIR, "medical_record", "med_1.pdf")
med_content = [
    "HEALTHCARE CLINICAL REPORT",
    "Patient: Suresh Patel. Age: 45. Clinical Code: MED-9921.",
    "Diagnosis: Severe acute gastritis and hypertension. Patient is advised rest.",
    "Doctor: Dr. Vikram Mehta. Hospital: City Heart Care."
]
create_simple_pdf(med_path, "Medical Discharge Summary", med_content)

med_gt = {
    "expected_sensitivity": "Highly Confidential",
    "expected_risk_level": "HIGH",
    "expected_entities": [
        {"entity_type": "PERSON", "value": "Suresh Patel"},
        {"entity_type": "PERSON", "value": "Dr. Vikram Mehta"},
        {"entity_type": "ORGANIZATION", "value": "City Heart Care"}
    ],
    "ground_truth_text": " ".join(med_content)
}
with open(os.path.join(DATASET_DIR, "medical_record", "med_1.gt.json"), "w") as f:
    json.dump(med_gt, f, indent=2)

# 7. Court Order
court_path = os.path.join(DATASET_DIR, "court_order", "court_1.pdf")
court_content = [
    "IN THE HIGH COURT OF DELHI AT NEW DELHI",
    "Case No: WP(C) 10234 of 2026. Order Date: 2026-07-09.",
    "Petitioner: Devendra Yadav. Respondent: Union of India & Others.",
    "Before Hon'ble Mr. Justice Sanjay Kishan Kaul. The writ petition is disposed of with directions."
]
create_simple_pdf(court_path, "Delhi High Court Order", court_content)

court_gt = {
    "expected_sensitivity": "Public",
    "expected_risk_level": "LOW",
    "expected_entities": [
        {"entity_type": "PERSON", "value": "Devendra Yadav"},
        {"entity_type": "PERSON", "value": "Sanjay Kishan Kaul"},
        {"entity_type": "ORGANIZATION", "value": "Union of India"}
    ],
    "ground_truth_text": " ".join(court_content)
}
with open(os.path.join(DATASET_DIR, "court_order", "court_1.gt.json"), "w") as f:
    json.dump(court_gt, f, indent=2)

# --- Robustness Files ---

# A. Digital PDF
digital_path = os.path.join(ROBUSTNESS_DIR, "digital_pdf", "robust_digital.pdf")
digital_text = ["This is a standard Digital PDF file with selectable text. No PII is included."]
create_simple_pdf(digital_path, "Digital PDF Document", digital_text)
with open(os.path.join(ROBUSTNESS_DIR, "digital_pdf", "robust_digital.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": " ".join(digital_text)}, f, indent=2)

# B. Large PDF
large_path = os.path.join(ROBUSTNESS_DIR, "large_pdf", "robust_large.pdf")
create_large_pdf(large_path, "Large multi-page PDF document", 101)
with open(os.path.join(ROBUSTNESS_DIR, "large_pdf", "robust_large.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": "Page 1 of this large legal file containing mock public text."}, f, indent=2)

# C. Corrupted PDF
corrupted_path = os.path.join(ROBUSTNESS_DIR, "corrupted", "robust_corrupted.pdf")
with open(corrupted_path, "wb") as f:
    f.write(b"%PDF-1.4\n%error_junk_corrupted_file_bytes_999999\n")
with open(os.path.join(ROBUSTNESS_DIR, "corrupted", "robust_corrupted.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": "", "should_fail": True}, f, indent=2)

# D. Password Protected PDF
pw_temp_path = os.path.join(ROBUSTNESS_DIR, "password_protected", "temp_pw.pdf")
create_simple_pdf(pw_temp_path, "Confidential Document", ["This is encrypted text."])
pw_path = os.path.join(ROBUSTNESS_DIR, "password_protected", "robust_password.pdf")
reader = PdfReader(pw_temp_path)
writer = PdfWriter()
for page in reader.pages:
    writer.add_page(page)
writer.encrypt("password")
with open(pw_path, "wb") as f:
    writer.write(f)
os.remove(pw_temp_path)
with open(os.path.join(ROBUSTNESS_DIR, "password_protected", "robust_password.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": "", "should_fail": True}, f, indent=2)

# E. Image-only Document
image_path = os.path.join(ROBUSTNESS_DIR, "image_only", "robust_image.png")
# Generate a valid PNG using PIL
img = Image.new('RGB', (100, 100), color='black')
img.save(image_path)
with open(os.path.join(ROBUSTNESS_DIR, "image_only", "robust_image.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": ""}, f, indent=2)

# F. Scanned PDF
scanned_path = os.path.join(ROBUSTNESS_DIR, "scanned_pdf", "robust_scanned.pdf")
doc = SimpleDocTemplate(scanned_path, pagesize=letter)
from reportlab.platypus import Image as RLImage
story = [RLImage(image_path, width=200, height=200)]
doc.build(story)
with open(os.path.join(ROBUSTNESS_DIR, "scanned_pdf", "robust_scanned.gt.json"), "w") as f:
    json.dump({"expected_sensitivity": "Public", "expected_risk_level": "LOW", "expected_entities": [], "ground_truth_text": ""}, f, indent=2)

print("Versioned validation dataset created successfully!")
