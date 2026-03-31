import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from django.core.files.base import ContentFile

def generate_agreement_pdf(application, admin):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- TOP TITLE ---
    p.setFont("Helvetica-Bold", 22)
    p.drawCentredString(width/2, height - 50, "CONVENTION DE STAGE")
    p.setFont("Helvetica-Bold", 18)
    p.drawCentredString(width/2, height - 80, "ENTRE")

    # --- HEADER BOXES ---
    # Left Box: University
    p.setLineWidth(1)
    p.rect(40, height - 210, 230, 110) # X, Y, Width, Height
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 120, f"UNIVERSITY OF {str(admin.university).upper()}")
    p.setFont("Helvetica", 8)
    p.drawString(50, height - 135, "New Town Ali Mendjeli, Constantine – Algeria")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(50, height - 160, "Represented by:")
    p.setFont("Helvetica", 9)
    p.drawString(50, height - 175, "The Vice Rector in charge of")
    p.drawString(50, height - 185, "External Relations")
    p.drawString(50, height - 200, "Tel/Fax : + 00 213 031 82 45 79")

    # Center "AND"
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width/2, height - 160, "AND")

    # Right Box: Company
    p.rect(width - 270, height - 210, 230, 110)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(width - 260, height - 120, "THE COMPANY (Name & Address)")
    p.setFont("Helvetica", 9)
    p.drawString(width - 260, height - 140, f"{str(application.offer.company.companyName)}")
    p.drawString(width - 260, height - 150, f"{str(application.offer.company.location)}")
    p.setFont("Helvetica-Bold", 9)
    p.drawString(width - 260, height - 170, "Represented by:")
    p.setFont("Helvetica", 9)
    p.drawString(width - 260, height - 185, "The Director / Manager")
    p.drawString(width - 260, height - 200, f"Tel: {str(application.offer.company.phoneNumber or '................')}")

    # --- STUDENT DATA SECTION (The Big Box) ---
    p.setLineWidth(1.5)
    p.rect(40, height - 540, 515, 310) # Big border
    p.setFont("Helvetica-Bold", 14)
    # Underline effect
    p.drawCentredString(width/2, height - 260, "STUDENT INFORMATION DATA")
    p.line(width/2 - 100, height - 265, width/2 + 100, height - 265)
    
    p.setFont("Helvetica", 11)
    y_start = height - 300
    line_height = 24
    
    p.drawString(50, y_start, f"Full Name: {application.student.lastName} {application.student.firstName}")
    p.drawString(50, y_start - line_height, f"Faculty: {str(admin.faculty)}")
    p.drawString(50, y_start - (line_height*2), f"Department: {str(admin.department)}")
    p.drawString(50, y_start - (line_height*3), f"Student ID Card No: {str(application.student.IDCardNumber or 'N/A')}      Social Security No: ....................")
    p.drawString(50, y_start - (line_height*4), f"Phone Number: {str(application.student.phoneNumber)}")
    p.drawString(50, y_start - (line_height*5), f"Degree Pursued: Computer Science (L3TI)")
    p.drawString(50, y_start - (line_height*6), f"Internship Topic: {str(application.offer.title)}")
    p.drawString(50, y_start - (line_height*7), f"Academic Supervisor: {str(admin.firstName)} {str(admin.lastName)}")
    
    try:
        duration = (application.offer.deadline - application.offer.startingDay).days
    except:
        duration = "................"

    p.drawString(50, y_start - (line_height*8), f"Duration of Internship: {duration} Days")
    p.drawString(50, y_start - (line_height*9), f"Starting Date: {str(application.offer.startingDay)}      Ending Date: {str(application.offer.deadline)}")

    # --- SIGNATURES ---
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 600, "Department Head Approval:")
    p.drawString(50, height - 700, "For the Company")
    p.drawRightString(width - 50, height - 700, "For the University")

    # --- PAGE 2: ARTICLES ---
    p.showPage()
    p.setFont("Helvetica-Bold", 14)
    p.drawCentredString(width/2, height - 50, "TERMS AND CONDITIONS")
    
    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 100, "Article 1: Object")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 120, f"The purpose of this agreement is to define the conditions for hosting students within the")
    p.drawString(50, height - 135, f"company {str(application.offer.company.companyName)} for a practical internship.")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 170, "Article 2: Goal of the Internship")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 190, "The internship is intended to provide the student with a practical application of the theoretical")
    p.drawString(50, height - 205, "knowledge taught at the university.")

    p.setFont("Helvetica-Bold", 12)
    p.drawString(50, height - 240, "Article 3: Confidentiality")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 260, "The student must maintain professional secrecy regarding all internal company data and projects.")

    # Footer
    p.drawCentredString(width/2, 30, "Digitally Generated by Stag.io - University of Constantine 2")

    p.save()
    buffer.seek(0)
    return ContentFile(buffer.read(), name=f"convention_{application.id}.pdf")