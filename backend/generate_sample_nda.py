import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def generate_pdf():
    pdf_filename = "sample_indian_nda.pdf"
    doc = SimpleDocTemplate(
        pdf_filename,
        pagesize=letter,
        rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72
    )
    
    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        name='TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        alignment=1, # Center
        spaceAfter=20,
        textColor=colors.HexColor('#1A365D')
    )
    
    subtitle_style = ParagraphStyle(
        name='SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        alignment=1,
        spaceAfter=30,
        textColor=colors.HexColor('#4A5568')
    )
    
    body_style = ParagraphStyle(
        name='BodyStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        spaceAfter=12,
        textColor=colors.HexColor('#2D3748')
    )
    
    section_style = ParagraphStyle(
        name='SectionStyle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#2B6CB0')
    )
    
    story = []
    
    # Header / Title
    story.append(Paragraph("MUTUAL NON-DISCLOSURE AGREEMENT", title_style))
    story.append(Paragraph("This Agreement is entered into and made effective as of 10th July 2026.", subtitle_style))
    story.append(Spacer(1, 10))
    
    # Parties
    parties_text = (
        "<b>BY AND BETWEEN:</b><br/><br/>"
        "<b>1. REDACTAI TECHNOLOGIES PRIVATE LIMITED</b>, a company incorporated under the Companies Act, 2013, "
        "having its registered office at 84, MG Road, Ashok Nagar, Bengaluru, Karnataka - 560001 (hereinafter referred to "
        "as the <b>'Disclosing Party'</b>, which expression shall unless repugnant to the context mean and include its successors "
        "and permitted assigns); and<br/><br/>"
        "<b>2. MR. RAJESH KUMAR SHARMA</b>, an individual, residing at Flat No. 402, Sai Enclave, Sector 15, "
        "Dwarka, New Delhi - 110075, having PAN Number: <b>APSPS1234K</b> and Aadhaar Number: <b>9876 5432 1098</b> "
        "(hereinafter referred to as the <b>'Receiving Party'</b>, which expression shall unless repugnant to the context mean "
        "and include his heirs, executors, and administrators).<br/><br/>"
        "The Disclosing Party and the Receiving Party are individually referred to as a <b>'Party'</b> and collectively as "
        "the <b>'Parties'</b>."
    )
    story.append(Paragraph(parties_text, body_style))
    story.append(Spacer(1, 15))
    
    # Purpose
    story.append(Paragraph("1. PURPOSE", section_style))
    purpose_text = (
        "The Parties wish to enter into discussions regarding a potential business relationship in connection with "
        "AI-powered compliance and legal document workflow solutions (the 'Proposed Transaction'). In the course of these "
        "discussions, the Disclosing Party may disclose certain confidential, proprietary, or personal data to the Receiving Party, "
        "including proprietary algorithms, user details, and system statistics."
    )
    story.append(Paragraph(purpose_text, body_style))
    
    # Confidential Information
    story.append(Paragraph("2. DEFINITION OF CONFIDENTIAL INFORMATION", section_style))
    conf_text = (
        "For the purposes of this Agreement, 'Confidential Information' shall include all information, whether oral, "
        "written, electronic, or in any other form, disclosed by the Disclosing Party. This includes but is not limited to "
        "personally identifiable information (PII) such as Aadhaar numbers, PAN details, bank account details, and phone numbers "
        "(e.g., +91-9876543210), email addresses (e.g., rajesh.sharma@example.com), and corporate secrets."
    )
    story.append(Paragraph(conf_text, body_style))
    
    # Obligations
    story.append(Paragraph("3. OBLIGATIONS OF RECEIVING PARTY", section_style))
    ob_text = (
        "The Receiving Party agrees to maintain the confidentiality of all Confidential Information and shall not disclose "
        "such information to any third party without prior written consent. The Receiving Party shall protect such information "
        "with the same degree of care (but no less than a reasonable standard of care) that it uses to protect its own "
        "confidential information."
    )
    story.append(Paragraph(ob_text, body_style))
    story.append(Spacer(1, 20))
    
    # Signatures
    sig_text = (
        "<b>IN WITNESS WHEREOF</b>, the Parties hereto have executed this Mutual Non-Disclosure Agreement as of the date first "
        "written above.<br/><br/><br/>"
        "<b>For RedactAI Technologies Pvt. Ltd.:</b><br/>"
        "Authorized Signatory: _______________________<br/>"
        "Name: Amit Verma<br/>"
        "Title: Director<br/><br/><br/>"
        "<b>For Receiving Party:</b><br/>"
        "Signature: _______________________<br/>"
        "Name: Rajesh Kumar Sharma<br/>"
        "Date: 10th July 2026"
    )
    story.append(Paragraph(sig_text, body_style))
    
    doc.build(story)
    print(f"Sample NDA PDF successfully generated at: {os.path.abspath(pdf_filename)}")

if __name__ == "__main__":
    generate_pdf()
