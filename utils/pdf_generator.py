# pdf_generator.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from io import BytesIO
from datetime import datetime

def generate_invoice_pdf(payment):
    """Generate a PDF invoice for a payment"""
    buffer = BytesIO()
    
    # Create the PDF object using ReportLab
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=72,
        leftMargin=72,
        topMargin=72,
        bottomMargin=72
    )
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Get styles
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name='Center',
        parent=styles['Heading1'],
        alignment=1,
    ))
    
    # Add invoice header
    elements.append(Paragraph("INVOICE", styles['Center']))
    elements.append(Spacer(1, 20))
    
    # Add company details
    elements.append(Paragraph("Your Company Name", styles['Heading2']))
    elements.append(Paragraph("123 Business Street", styles['Normal']))
    elements.append(Paragraph("City, State, ZIP", styles['Normal']))
    elements.append(Paragraph("Email: support@yourcompany.com", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Add invoice details
    invoice_info = [
        ['Invoice Number:', payment.invoice_number],
        ['Date:', payment.created_at.strftime('%Y-%m-%d')],
        ['Order ID:', payment.razorpay_order_id],
        ['Payment ID:', payment.razorpay_payment_id or 'N/A'],
    ]
    
    # Create invoice info table
    info_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 20))
    
    # Add billing details if available
    if hasattr(payment, 'invoice_address'):
        addr = payment.invoice_address
        elements.append(Paragraph("Bill To:", styles['Heading3']))
        elements.append(Paragraph(f"{addr.full_name}", styles['Normal']))
        if addr.company_name:
            elements.append(Paragraph(f"{addr.company_name}", styles['Normal']))
        elements.append(Paragraph(f"{addr.street_address}", styles['Normal']))
        elements.append(Paragraph(f"{addr.city}, {addr.state} {addr.postal_code}", styles['Normal']))
        elements.append(Paragraph(f"{addr.country}", styles['Normal']))
        if addr.gst_number:
            elements.append(Paragraph(f"GST: {addr.gst_number}", styles['Normal']))
        elements.append(Spacer(1, 20))
    
    # Add subscription details
    subscription_data = [
        ['Description', 'Amount'],
        [f"{payment.subscription.plan} Subscription", f"{payment.currency} {payment.base_amount:.2f}"],
        ['GST', f"{payment.currency} {payment.gst_amount:.2f}"],
        ['Total', f"{payment.currency} {payment.total_amount:.2f}"]
    ]
    
    # Create subscription table
    sub_table = Table(subscription_data, colWidths=[4*inch, 2*inch])
    sub_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(sub_table)
    
    # Add footer
    elements.append(Spacer(1, 30))
    elements.append(Paragraph("Thank you for your business!", styles['Normal']))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    return buffer