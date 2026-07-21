"""
SafeNet AI - PDF Report Generator
==================================
Generates professional PDF reports for URL scan history.
Supports filtering by report type, date range, and user plan.
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfgen import canvas
from datetime import datetime, timedelta
from io import BytesIO
import os


class ReportGenerator:
    """
    Generate professional PDF reports for SafeNet AI scan history.
    """
    
    def __init__(self, user_email, user_plan, scans_data, report_type='all', date_range=None):
        """
        Initialize the report generator.
        
        Args:
            user_email (str): User's email address
            user_plan (str): User's current plan (free, basic, pro, pro_plus, enterprise)
            scans_data (list): List of scan records
            report_type (str): Type of report - 'all', 'phishing', 'legitimate'
            date_range (str): Date range filter - '7', '30', 'custom', or None
        """
        self.user_email = user_email
        self.user_plan = user_plan
        self.scans_data = scans_data
        self.report_type = report_type
        self.date_range = date_range
        self.buffer = BytesIO()
        
        # Plan display names
        self.plan_display = {
            'free': 'Free',
            'basic': 'Basic',
            'pro': 'Pro',
            'pro_plus': 'Pro Plus',
            'enterprise': 'Enterprise'
        }
        
        # Premium plans (for watermark logic)
        self.premium_plans = ['pro', 'pro_plus', 'enterprise']
        
    def generate(self):
        """
        Generate the PDF report and return as BytesIO buffer.
        
        Returns:
            BytesIO: PDF file buffer
        """
        # Create PDF document
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=1*inch,
            bottomMargin=0.75*inch
        )
        
        # Container for PDF elements
        story = []
        
        # Get styles
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=colors.HexColor('#7C3AED'),  # Professional purple
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Times-Bold'  # More professional font
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#666666'),
            spaceAfter=6,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#1a1a2e'),
            spaceAfter=10,
            spaceBefore=15,
            fontName='Helvetica-Bold'
        )
        
        # ========== HEADER SECTION ==========
        story.append(Paragraph("SafeNet AI", title_style))
        story.append(Paragraph("Scan Security Report", subtitle_style))
        story.append(Spacer(1, 0.2*inch))
        
        # User info table
        user_info_data = [
            ['User Email:', self.user_email],
            ['Current Plan:', self.plan_display.get(self.user_plan, 'Free')],
            ['Report Type:', self.report_type.capitalize()],
            ['Generated Date:', datetime.utcnow().strftime('%B %d, %Y')]
        ]
        
        user_info_table = Table(user_info_data, colWidths=[2*inch, 4.5*inch])
        user_info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#333333')),
            ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#666666')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        story.append(user_info_table)
        story.append(Spacer(1, 0.3*inch))
        
        # ========== SUMMARY SECTION ==========
        story.append(Paragraph("Summary", heading_style))
        
        # Calculate statistics
        total_scans = len(self.scans_data)
        phishing_count = sum(1 for scan in self.scans_data if scan.get('prediction', '').lower() in ['phishing'])
        legitimate_count = sum(1 for scan in self.scans_data if scan.get('prediction', '').lower() in ['legitimate', 'safe'])
        suspicious_count = sum(1 for scan in self.scans_data if scan.get('prediction', '').lower() in ['suspicious'])
        
        # Accuracy note
        accuracy_note = "Results based on AI-powered multi-layer detection system"
        
        summary_data = [
            ['Total URLs Scanned:', str(total_scans)],
            ['Phishing Detected:', str(phishing_count)],
            ['Legitimate URLs:', str(legitimate_count)],
            ['Suspicious URLs:', str(suspicious_count)],
            ['Detection Method:', accuracy_note]
        ]
        
        summary_table = Table(summary_data, colWidths=[2.5*inch, 4*inch])
        summary_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f0f0f0')),
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 0.3*inch))
        
        # ========== TABLE SECTION ==========
        story.append(Paragraph("Scan History", heading_style))
        
        # Check if free user and limit scans
        is_free_user = self.user_plan == 'free'
        scans_to_show = self.scans_data[:10] if is_free_user else self.scans_data
        
        if is_free_user and total_scans > 10:
            # Add upgrade message for free users
            upgrade_msg = Paragraph(
                f"<i>⚠️ Free plan: Showing only 10 of {total_scans} scans. "
                f"Upgrade to Pro or Pro+ to export all scans.</i>",
                ParagraphStyle('UpgradeNote', parent=styles['Normal'], 
                              fontSize=9, textColor=colors.HexColor('#ff6b6b'),
                              spaceAfter=10, alignment=TA_CENTER)
            )
            story.append(upgrade_msg)
        
        # Table header
        table_data = [['#', 'URL', 'Result', 'Risk Level', 'Scan Date']]
        
        # Add scan rows
        for idx, scan in enumerate(scans_to_show, 1):
            url = scan.get('url', 'N/A')
            
            # Wrap URL in Paragraph for proper text wrapping
            url_style = ParagraphStyle(
                'URLStyle',
                parent=styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#333333'),
                wordWrap='CJK',  # Enable word wrapping
                leading=10
            )
            url_para = Paragraph(url, url_style)
            
            result = scan.get('prediction', 'Unknown')
            confidence = scan.get('confidence', 0)
            
            # Determine risk level
            if result.lower() in ['phishing']:
                risk_level = 'High'
            elif result.lower() in ['suspicious']:
                risk_level = 'Medium'
            else:
                risk_level = 'Low'
            
            # Format date
            timestamp = scan.get('timestamp')
            if timestamp:
                if isinstance(timestamp, str):
                    scan_date = timestamp
                else:
                    scan_date = timestamp.strftime('%b %d, %Y')
            else:
                scan_date = 'N/A'
            
            table_data.append([
                str(idx),
                url_para,  # Use Paragraph instead of plain string
                result,
                risk_level,
                scan_date
            ])

        
        # Create table
        scan_table = Table(table_data, colWidths=[0.4*inch, 3*inch, 1*inch, 0.9*inch, 1.2*inch])
        
        # Table style
        table_style = [
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # Index column
            ('ALIGN', (1, 1), (1, -1), 'LEFT'),    # URL column
            ('ALIGN', (2, 1), (-1, -1), 'CENTER'), # Other columns
            ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]
        
        # Color code results
        for idx, scan in enumerate(scans_to_show, 1):
            result = scan.get('prediction', 'Unknown').lower()
            if result == 'phishing':
                table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.HexColor('#e74c3c')))
                table_style.append(('FONTNAME', (2, idx), (2, idx), 'Helvetica-Bold'))
            elif result == 'suspicious':
                table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.HexColor('#f39c12')))
            elif result in ['legitimate', 'safe']:
                table_style.append(('TEXTCOLOR', (2, idx), (2, idx), colors.HexColor('#27ae60')))
        
        scan_table.setStyle(TableStyle(table_style))
        story.append(scan_table)
        
        # ========== FOOTER SECTION ==========
        story.append(Spacer(1, 0.4*inch))
        
        footer_text = "Generated by SafeNet AI – AI-Powered URL Security"
        footer_para = Paragraph(
            footer_text,
            ParagraphStyle('Footer', parent=styles['Normal'],
                          fontSize=9, textColor=colors.HexColor('#999999'),
                          alignment=TA_CENTER)
        )
        story.append(footer_para)
        
        # Add watermark for premium users
        if self.user_plan in self.premium_plans:
            watermark_text = f"✓ {self.plan_display[self.user_plan]} Feature"
            watermark_para = Paragraph(
                watermark_text,
                ParagraphStyle('Watermark', parent=styles['Normal'],
                              fontSize=8, textColor=colors.HexColor('#3498db'),
                              alignment=TA_CENTER, spaceAfter=5)
            )
            story.append(Spacer(1, 0.1*inch))
            story.append(watermark_para)
        
        # Build PDF
        doc.build(story, onFirstPage=self._add_page_number, onLaterPages=self._add_page_number)
        
        # Reset buffer position
        self.buffer.seek(0)
        return self.buffer
    
    def _add_page_number(self, canvas, doc):
        """
        Add page number to each page.
        """
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(colors.HexColor('#999999'))
        canvas.drawRightString(7.5*inch, 0.5*inch, text)
        canvas.restoreState()


def generate_scan_report(user_email, user_plan, scans_data, report_type='all', date_range=None):
    """
    Helper function to generate a scan report.
    
    Args:
        user_email (str): User's email
        user_plan (str): User's plan
        scans_data (list): List of scan records
        report_type (str): 'all', 'phishing', or 'legitimate'
        date_range (str): '7', '30', 'custom', or None
        
    Returns:
        BytesIO: PDF buffer
    """
    generator = ReportGenerator(user_email, user_plan, scans_data, report_type, date_range)
    return generator.generate()
