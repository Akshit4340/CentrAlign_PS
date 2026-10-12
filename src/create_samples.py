# src/create_samples.py
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from PIL import Image, ImageDraw, ImageFont

def generate_pdf_invoice(filepath: str, vendor: str, amount: float, due_date: str, invoice_num: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter

    # Header banner
    c.setFillColor(colors.HexColor("#1e293b"))
    c.rect(0, height - 100, width, 100, fill=True, stroke=False)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(50, height - 60, "OFFICIAL VENDOR INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(width - 200, height - 55, f"Invoice: {invoice_num}")
    c.drawString(width - 200, height - 75, f"Issued: 2026-10-01")

    # Vendor info
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, height - 140, "Vendor Details:")
    
    c.setFont("Helvetica", 12)
    c.drawString(50, height - 165, f"Company Name: {vendor}")
    c.drawString(50, height - 185, "Billing Department: Enterprise Solutions Group")
    c.drawString(50, height - 205, "Email: billing@companyx-enterprises.com")

    # Payment details
    c.setFont("Helvetica-Bold", 14)
    c.drawString(320, height - 140, "Payment Terms:")
    c.setFont("Helvetica", 12)
    c.drawString(320, height - 165, f"Due Date: {due_date}")
    c.drawString(320, height - 185, "Payment Method: ACH / Direct Deposit")
    c.drawString(320, height - 205, "Status: PENDING PROCESSING")

    # Table header
    c.setFillColor(colors.HexColor("#334155"))
    c.rect(50, height - 250, width - 100, 25, fill=True, stroke=False)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(60, height - 243, "Description")
    c.drawString(350, height - 243, "Qty")
    c.drawString(420, height - 243, "Rate")
    c.drawString(500, height - 243, "Amount")

    # Table rows
    c.setFillColor(colors.HexColor("#1e293b"))
    c.setFont("Helvetica", 11)
    c.drawString(60, height - 280, "Cloud Compute Infrastructure - Tier 2")
    c.drawString(355, height - 280, "1")
    c.drawString(415, height - 280, f"${amount:.2f}")
    c.drawString(495, height - 280, f"${amount:.2f}")

    c.setStrokeColor(colors.HexColor("#cbd5e1"))
    c.line(50, height - 300, width - 50, height - 300)

    # Total Box
    c.setFillColor(colors.HexColor("#f1f5f9"))
    c.rect(width - 240, height - 370, 190, 55, fill=True, stroke=True)
    
    c.setFillColor(colors.HexColor("#0f172a"))
    c.setFont("Helvetica-Bold", 12)
    c.drawString(width - 225, height - 335, "Total Balance Due:")
    c.setFont("Helvetica-Bold", 16)
    c.setFillColor(colors.HexColor("#0284c7"))
    c.drawString(width - 225, height - 360, f"${amount:.2f} USD")

    # Footer note
    c.setFillColor(colors.HexColor("#64748b"))
    c.setFont("Helvetica-Oblique", 10)
    c.drawString(50, 60, "Please submit payment electronically according to standard corporate Net-30 agreement terms.")
    c.drawString(50, 45, "Confidential Document - For CentrAlign Enterprise Accounts Payable Internal Ledger Only.")

    c.save()
    print(f"Generated PDF: {filepath}")

def generate_image_invoice(filepath: str, vendor: str, amount: float, due_date: str, invoice_num: str):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    img = Image.new("RGB", (700, 900), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Top banner
    draw.rectangle([(0, 0), (700, 120)], fill=(30, 41, 59))
    draw.text((40, 40), "VENDOR INVOICE RECEIPT", fill=(255, 255, 255))
    draw.text((450, 45), f"Inv #: {invoice_num}", fill=(220, 230, 242))
    draw.text((450, 75), f"Due Date: {due_date}", fill=(220, 230, 242))

    # Content
    draw.rectangle([(40, 160), (660, 320)], outline=(203, 213, 225), width=2, fill=(248, 250, 252))
    draw.text((60, 180), f"Vendor Name: {vendor}", fill=(15, 23, 42))
    draw.text((60, 215), "Account Category: Operating Expense / SaaS", fill=(71, 85, 105))
    draw.text((60, 250), f"Payment Due Date: {due_date}", fill=(15, 23, 42))
    draw.text((60, 285), f"Total Authorized Amount: ${amount:.2f}", fill=(2, 132, 199))

    # Table preview
    draw.rectangle([(40, 350), (660, 390)], fill=(51, 65, 85))
    draw.text((60, 360), "Line Item Description", fill=(255, 255, 255))
    draw.text((540, 360), "Subtotal", fill=(255, 255, 255))

    draw.text((60, 415), "Professional Engineering Consultation Services", fill=(30, 41, 59))
    draw.text((540, 415), f"${amount:.2f}", fill=(30, 41, 59))

    # Total callout
    draw.rectangle([(400, 520), (660, 600)], fill=(241, 245, 249), outline=(2, 132, 199), width=2)
    draw.text((420, 535), "Net Payable Balance:", fill=(15, 23, 42))
    draw.text((420, 565), f"${amount:.2f} USD", fill=(2, 132, 199))

    # Watermark / Note
    draw.text((40, 830), "Automated Extraction Document for CentrAlign Task Worker Demo.", fill=(148, 163, 184))
    
    img.save(filepath)
    print(f"Generated Image: {filepath}")

if __name__ == "__main__":
    generate_pdf_invoice("samples/invoice_company_x.pdf", "Company X", 450.75, "2026-11-15", "INV-2026-001")
    generate_pdf_invoice("samples/invoice_acme_corp.pdf", "Acme Corp", 895.00, "2026-12-05", "INV-2026-088")
    generate_image_invoice("samples/invoice_company_x.png", "Company X", 450.75, "2026-11-15", "INV-2026-001")
    generate_image_invoice("samples/invoice_apex_tech.png", "Apex Global", 1280.00, "2026-11-30", "INV-2026-554")
