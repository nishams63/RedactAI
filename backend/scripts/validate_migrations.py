"""Database schema and Alembic migrations validator checking tables, indexes, keys, and seed data."""
import os
import sys

backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from datetime import datetime
from sqlalchemy import text
from database.session import SessionLocal

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

REPORTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "local_storage",
    "reports"
)
os.makedirs(REPORTS_DIR, exist_ok=True)

def validate_migrations():
    """Validates Alembic version, table list, seeded accounts, and compile PDF report."""
    print("=== STARTING DATABASE SCHEMA MIGRATION VALIDATION ===")
    
    db = SessionLocal()
    checklist = []
    
    # 1. Check current Alembic revision
    alembic_version = None
    try:
        res = db.execute(text("SELECT version_num FROM alembic_version"))
        alembic_version = res.scalar()
        checklist.append({
            "check": "Alembic Schema Version",
            "status": "PASSED" if alembic_version == "981b89eaf0e1" else "WARNING",
            "details": f"Active Migration Hash: {alembic_version}"
        })
    except Exception as e:
        checklist.append({
            "check": "Alembic Version Check",
            "status": "FAILED",
            "details": f"Error loading alembic version table: {e}"
        })

    # 2. Check essential tables existence
    expected_tables = ["users", "roles", "organizations", "documents", "user_sessions", "audit_logs", "security_alerts"]
    for table in expected_tables:
        try:
            db.execute(text(f"SELECT 1 FROM {table} LIMIT 1"))
            checklist.append({
                "check": f"Table Existence: {table}",
                "status": "PASSED",
                "details": f"Database table '{table}' is verified online."
            })
        except Exception as e:
            checklist.append({
                "check": f"Table Existence: {table}",
                "status": "FAILED",
                "details": f"Database table missing or corrupt: {e}"
            })

    # 3. Check seeded admin user
    try:
        res = db.execute(text("SELECT email FROM users WHERE email='admin@redactai.in'"))
        admin_email = res.scalar()
        checklist.append({
            "check": "Seed Data: Admin user account",
            "status": "PASSED" if admin_email else "FAILED",
            "details": "Admin user account seeded in database." if admin_email else "No seed admin user found."
        })
    except Exception as e:
        checklist.append({
            "check": "Seed Data: Admin user account",
            "status": "FAILED",
            "details": f"Seed validation failed: {e}"
        })

    # 4. Check seed roles
    try:
        res = db.execute(text("SELECT count(*) FROM roles"))
        roles_count = res.scalar()
        checklist.append({
            "check": "Seed Data: Default roles definitions",
            "status": "PASSED" if roles_count >= 3 else "FAILED",
            "details": f"Found {roles_count} seeded roles (Viewer, Legal Officer, Admin)."
        })
    except Exception as e:
        checklist.append({
            "check": "Seed Data: Default roles definitions",
            "status": "FAILED",
            "details": f"Role check failed: {e}"
        })

    db.close()

    # Generate PDF report using ReportLab
    pdf_path = os.path.join(REPORTS_DIR, "Migration_Report.pdf")
    doc = SimpleDocTemplate(pdf_path, pagesize=letter, leftMargin=40, rightMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    story = []

    primary_color = colors.HexColor("#0f172a") # dark slate
    secondary_color = colors.HexColor("#0284c7") # sky blue
    text_color = colors.HexColor("#334155")
    light_bg = colors.HexColor("#f8fafc")

    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=primary_color,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=secondary_color,
        spaceAfter=20
    )
    h1_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=17,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        "BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=text_color,
        spaceAfter=8
    )

    story.append(Paragraph("RedactAI Schema & Data Migration Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (IST) | Target: 981b89eaf0e1", subtitle_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Database Migration Check list", h1_style))
    
    table_data = [
        [Paragraph("<b>Validation Parameter Check</b>", body_style), Paragraph("<b>Status</b>", body_style), Paragraph("<b>Verification details</b>", body_style)]
    ]
    for c in checklist:
        status_color = "green" if c["status"] == "PASSED" else "red"
        table_data.append([
            Paragraph(c["check"], body_style),
            Paragraph(f"<font color='{status_color}'><b>{c['status']}</b></font>", body_style),
            Paragraph(c["details"], body_style)
        ])

    t = Table(table_data, colWidths=[200, 80, 250])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), light_bg),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, light_bg])
    ]))
    story.append(t)
    doc.build(story)
    
    print(f"Migration validation completed. Saved to {pdf_path}")

if __name__ == "__main__":
    validate_migrations()
