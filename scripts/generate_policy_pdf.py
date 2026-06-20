"""Script to programmatically generate a realistic, multi-page compliance policy PDF.

This script uses reportlab to generate 'Compliance_Policy_Manual.pdf' containing
the safety guidelines, callout boxes, and policy references that the parser will parse.
"""

from pathlib import Path
import os

def generate_pdf(output_path: str | Path):
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.units import inch
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
        from reportlab.pdfgen import canvas
    except ImportError:
        print("Error: 'reportlab' is required to generate the PDF manual.")
        print("Please run: pip install reportlab")
        return

    print(f"Generating PDF compliance manual at: {output_path}")

    # NumberedCanvas pattern for Page X of Y
    class NumberedCanvas(canvas.Canvas):
        def __init__(self, *args, **kwargs):
            canvas.Canvas.__init__(self, *args, **kwargs)
            self._saved_page_states = []

        def showPage(self):
            self._saved_page_states.append(dict(self.__dict__))
            self._startPage()

        def save(self):
            num_pages = len(self._saved_page_states)
            for state in self._saved_page_states:
                self.__dict__.update(state)
                self.draw_page_number(num_pages)
                canvas.Canvas.showPage(self)
            canvas.Canvas.save(self)

        def draw_page_number(self, page_count):
            if self._pageNumber == 1:
                # Suppress header/footer on cover page
                return
            self.saveState()
            self.setFont("Helvetica", 8)
            self.setFillColor(colors.HexColor("#555555"))
            
            # Header
            self.drawString(54, 750, "GLOBAL MANUFACTURING INC. — EHS COMPLIANCE MANUAL v2.1")
            self.setStrokeColor(colors.HexColor("#CCCCCC"))
            self.setLineWidth(0.5)
            self.line(54, 742, letter[0]-54, 742)
            
            # Footer
            page_text = f"Page {self._pageNumber} of {page_count}"
            self.drawRightString(letter[0] - 54, 36, page_text)
            self.drawString(54, 36, "CONFIDENTIAL — INTERNAL USE ONLY")
            self.line(54, 48, letter[0]-54, 48)
            self.restoreState()

    # Document Setup
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=72,
        bottomMargin=72
    )

    styles = getSampleStyleSheet()
    
    # Custom Styles
    title_style = ParagraphStyle(
        'CoverTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=28,
        leading=34,
        textColor=colors.HexColor("#1A365D"),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'CoverSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor("#4A5568"),
        alignment=1, # Center
        spaceAfter=40
    )

    metadata_style = ParagraphStyle(
        'CoverMetadata',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#718096"),
        alignment=1,
    )

    h1_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1A365D"),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'SubSectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#2B6CB0"),
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#2D3748"),
        spaceAfter=8
    )

    bullet_style = ParagraphStyle(
        'BulletCustom',
        parent=body_style,
        leftIndent=20,
        firstLineIndent=-10,
        spaceAfter=4
    )

    callout_warning_style = ParagraphStyle(
        'CalloutWarning',
        parent=body_style,
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#7B341E")
    )

    callout_critical_style = ParagraphStyle(
        'CalloutCritical',
        parent=body_style,
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#742A2A")
    )

    def make_callout(text, is_critical=False):
        color_bg = colors.HexColor("#FFF5F5") if is_critical else colors.HexColor("#FFFAF0")
        color_border = colors.HexColor("#E53E3E") if is_critical else colors.HexColor("#DD6B20")
        style = callout_critical_style if is_critical else callout_warning_style
        
        tbl_data = [[Paragraph(text, style)]]
        tbl = Table(tbl_data, colWidths=[letter[0] - 108])
        tbl.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), color_bg),
            ('BOX', (0,0), (-1,-1), 1.5, color_border),
            ('TOPPADDING', (0,0), (-1,-1), 10),
            ('BOTTOMPADDING', (0,0), (-1,-1), 10),
            ('LEFTPADDING', (0,0), (-1,-1), 12),
            ('RIGHTPADDING', (0,0), (-1,-1), 12),
        ]))
        return tbl

    story = []

    # PAGE 1: COVER PAGE
    story.append(Spacer(1, 2 * inch))
    story.append(Paragraph("ENVIRONMENT, HEALTH & SAFETY<br/>COMPLIANCE MANUAL", title_style))
    story.append(Paragraph("Standard Operating Policies & Behavioral Safety Standards", subtitle_style))
    story.append(Spacer(1, 1.5 * inch))
    story.append(Paragraph("<b>Version:</b> 2.1<br/><b>Effective Date:</b> June 2026<br/><b>Approved By:</b> EHS Directorate<br/><b>Target:</b> All Facility Personnel & Contractors", metadata_style))
    story.append(PageBreak())

    # PAGE 2: TABLE OF CONTENTS
    story.append(Paragraph("Table of Contents", h1_style))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Section 1: Executive Safety Commitment .............................................................. Page 3", body_style))
    story.append(Paragraph("Section 2: Site Access Requirements ..................................................................... Page 4", body_style))
    story.append(Paragraph("Section 3: Personal Protective Equipment (PPE) Standards .................................. Page 5", body_style))
    story.append(Paragraph("Section 4: Pedestrian Zone Safety & Walkway Protocol ......................................... Page 6", body_style))
    story.append(Paragraph("Section 5: Electrical Equipment & Panel Operations ............................................. Page 7", body_style))
    story.append(Paragraph("Section 6: Material Handling & Heavy Vehicle Constraints ................................... Page 8", body_style))
    story.append(Paragraph("Section 7: Machinery Access & Maintenance Intervention ................................... Page 9", body_style))
    story.append(Paragraph("Section 8: Incident Reporting & Emergency Protocols ......................................... Page 10", body_style))
    story.append(Paragraph("Section 9: Hazardous Materials & Chemical Handling ........................................... Page 11", body_style))
    story.append(Paragraph("Section 10: Egress & Fire Prevention Controls ....................................................... Page 12", body_style))
    story.append(Paragraph("Section 11: Supervisor Roles & Auditing Framework ............................................. Page 13", body_style))
    story.append(Paragraph("Section 12: Continuous Safety Training Standards ................................................ Page 14", body_style))
    story.append(Paragraph("Section 13: Summary Matrix and Policy Sign-off .................................................. Page 15", body_style))
    story.append(PageBreak())

    # PAGE 3: SECTION 1
    story.append(Paragraph("Section 1: Executive Safety Commitment", h1_style))
    story.append(Paragraph("At Global Manufacturing Inc., the health and safety of our workforce is our paramount priority. We commit to providing a hazard-free work environment, state-of-the-art protective systems, and robust oversight mechanisms to prevent all workplace incidents. Every manager, employee, and contractor is empowered and required to halt operations if an unsafe condition or behavior is observed.", body_style))
    story.append(Paragraph("Our Zero-Incident Culture dictates that behavioral safety rules are non-negotiable. Any violation of designated EHS policies will be logged, categorized, and escalated for corrective action. Through continuous observation and digital monitoring, we ensure compliance with regulatory frameworks and corporate safety goals.", body_style))
    story.append(PageBreak())

    # PAGE 4: SECTION 2
    story.append(Paragraph("Section 2: Site Access Requirements", h1_style))
    story.append(Paragraph("All personnel entering the industrial floor must possess a valid site induction clearance and wear the basic mandated site security credentials. Visitors must be accompanied by an authorized escort at all times. Standard entry gates require badge-in validation to ensure capacity constraints are not breached.", body_style))
    story.append(Paragraph("Before stepping onto the factory floor, personnel must receive the daily EHS shift briefing outlining specific hazards, active maintenance zones, and heavy machinery operations planned for the day. Failure to badge in or bypass of access control systems will trigger an immediate EHS security event.", body_style))
    story.append(PageBreak())

    # PAGE 5: SECTION 3: PPE STANDARDS
    story.append(Paragraph("Section 3: Personal Protective Equipment (PPE) Standards", h1_style))
    story.append(Paragraph("Section 3.1: High-Visibility PPE Requirements", h2_style))
    story.append(Paragraph("The factory floor is classified as an active industrial zone. High-visibility clothing is mandatory for all personnel to ensure they are visible to vehicle operators, crane operators, and machinery systems. The designated visibility color for general personnel is high-visibility neon green.", body_style))
    
    warn_vest = (
        "<b>WARNING</b><br/>"
        "<b>Policy Reference:</b> Section 3.1 - Personal Protective Equipment<br/>"
        "<b>Rule:</b> All personnel operating on or traversing the active work areas must wear a high-visibility green safety vest. "
        "Failure to wear a high-visibility green safety vest is classified as a <b>MEDIUM</b> severity violation.<br/>"
        "<b>Observable Indicators:</b> Personnel wearing red, black, or standard clothing without a neon green safety vest layer on the torso. "
        "A compliant person must exhibit a visible green pixel ratio exceeding 15% in their upper torso region.<br/>"
        "<b>Escalation Trigger:</b> If a person without a safety vest is detected within the active loading zones or close to active forklifts, "
        "the severity escalates to <b>HIGH</b>."
    )
    story.append(make_callout(warn_vest, is_critical=False))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Failure to comply with PPE regulations not only puts the individual at risk but also invalidates general insurance coverages. Spot audits will be performed by floor supervisors daily.", body_style))
    story.append(PageBreak())

    # PAGE 6: SECTION 4: PEDESTRIAN SAFETY
    story.append(Paragraph("Section 4: Pedestrian Zone Safety & Walkway Protocol", h1_style))
    story.append(Paragraph("Section 4.2: Pedestrian Zones and Safe Walkways", h2_style))
    story.append(Paragraph("To isolate pedestrians from heavy machinery and forklift traffic, the facility utilizes painted floor markings. All pedestrians must restrict their movements to designated safe walkways, marked on the floor with thick green border lines.", body_style))
    
    warn_walkway = (
        "<b>WARNING</b><br/>"
        "<b>Policy Reference:</b> Section 4.2.1 - Pedestrian Safety Zones<br/>"
        "<b>Rule:</b> Pedestrians must remain within designated safe walkways at all times. "
        "Stepping outside the green floor markings is classified as a <b>MEDIUM</b> severity violation.<br/>"
        "<b>Observable Indicators:</b> Person bounding box center or lower body foot region failing to overlap green walkway pixels. "
        "Walkway boundary lines are painted in standard safety green.<br/>"
        "<b>Contextual Escalation Rules:</b><br/>"
        "- If a pedestrian steps outside the walkway and their proximity to active machinery is less than 1.0 meter (person_proximity_to_machinery < 1.0), the violation severity escalates to <b>HIGH</b>.<br/>"
        "- If a pedestrian steps outside the walkway while a heavy vehicle is operating in the zone (forklift_operating == true), the violation severity escalates to <b>HIGH</b>."
    )
    story.append(make_callout(warn_walkway, is_critical=False))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Designated walkways must be kept clear of all materials, inventory, and debris. Any blockage in the walkway must be reported immediately and cleared.", body_style))
    story.append(PageBreak())

    # PAGE 7: SECTION 5: ELECTRICAL SAFETY
    story.append(Paragraph("Section 5: Electrical Equipment & Panel Operations", h1_style))
    story.append(Paragraph("Section 5.2: Electrical Panels and Cabinets", h2_style))
    story.append(Paragraph("All electrical panel covers and machine control cabinets must remain closed and secured to prevent accidental contact with energized components. Only qualified electricians are permitted to open panel doors for testing or maintenance.", body_style))
    
    warn_panel = (
        "<b>WARNING</b><br/>"
        "<b>Policy Reference:</b> Section 5.2.2 - Electrical Safety Controls<br/>"
        "<b>Rule:</b> Electrical or machine control panel covers must never be left open during standard operation. "
        "An open panel cover represents an immediate shock hazard and is classified as a <b>MEDIUM</b> severity violation.<br/>"
        "<b>Observable Indicators:</b> Panel door visible in an open state, exposing internal wiring or components.<br/>"
        "<b>Contextual Escalation Rules:</b><br/>"
        "- If the panel cover remains open for a duration exceeding 300 seconds (duration_open > 300), the severity escalates to <b>HIGH</b>.<br/>"
        "- If unauthorized personnel are detected near the open panel (person_proximity_to_panel < 1.0), the severity escalates to <b>HIGH</b>."
    )
    story.append(make_callout(warn_panel, is_critical=False))
    story.append(Spacer(1, 10))
    story.append(Paragraph("After completing maintenance, panels must be locked and signed off. Floor supervisors must verify all locks are in place during end-of-shift walk-throughs.", body_style))
    story.append(PageBreak())

    # PAGE 8: SECTION 6: MATERIAL HANDLING
    story.append(Paragraph("Section 6: Material Handling & Heavy Vehicle Constraints", h1_style))
    story.append(Paragraph("Section 6.3: Forklift Carrying Load Limits", h2_style))
    story.append(Paragraph("Forklifts are vital to factory logistics, but overload conditions can lead to tipped vehicles, dropped loads, and severe injury. Operators must verify load weights and load volumes prior to transport. The height and count of stacked items on the forks must not obstruct the forward vision of the operator.", body_style))
    
    crit_forklift = (
        "<b>CRITICAL SAFETY NOTICE</b><br/>"
        "<b>Policy Reference:</b> Section 6.3.2 - Material Handling Equipment<br/>"
        "<b>Rule:</b> Forklifts must not exceed carrying load volume limits. Carrying more than 2 stacked blocks or pallets is strictly prohibited. "
        "Forklift overloading is classified as a <b>CRITICAL</b> severity violation due to immediate tipping hazard.<br/>"
        "<b>Observable Indicators:</b> The count of stacked rectangular blocks or pallets on the forklift forks is 3 or more (block_count >= 3).<br/>"
        "<b>Action Required:</b> Immediate real-time alert trigger, supervisor notification, and forklift operation halt."
    )
    story.append(make_callout(crit_forklift, is_critical=True))
    story.append(Spacer(1, 10))
    story.append(Paragraph("All forklift operators must undergo annual recertification. Vehicles must be inspected before every shift, with documentation logged in the EHS system.", body_style))
    story.append(PageBreak())

    # PAGE 9: SECTION 7: MACHINERY INTERVENTION
    story.append(Paragraph("Section 7: Machinery Access & Maintenance Intervention", h1_style))
    story.append(Paragraph("Section 7.2: Equipment Intervention Authorization", h2_style))
    story.append(Paragraph("Intervention or maintenance on operating machinery is the leading cause of industrial injury. Standard operation does not permit personnel to cross machine guards or place hands near moving parts. Lockout-Tagout (LOTO) protocols must be initiated before any intervention.", body_style))
    
    crit_intervention = (
        "<b>CRITICAL SAFETY NOTICE</b><br/>"
        "<b>Policy Reference:</b> Section 7.2.1 - Machinery Safety Guarding<br/>"
        "<b>Rule:</b> Personnel must not perform interventions on active machinery without authorization and compliance indicators. "
        "Unauthorized equipment intervention is classified as a <b>HIGH</b> severity violation.<br/>"
        "<b>Observable Indicators:</b> Hands or body parts in close proximity to active machinery parts. "
        "Personnel without a neon green safety vest interacting with active equipment.<br/>"
        "<b>Contextual Escalation Rules:</b><br/>"
        "- If multiple unauthorized persons are detected interacting with the equipment simultaneously (personnel_count > 1), "
        "the severity escalates to <b>CRITICAL</b>."
    )
    story.append(make_callout(crit_intervention, is_critical=True))
    story.append(Spacer(1, 10))
    story.append(Paragraph("LOTO locks must be red and individually keyed. The key must remain in the custody of the technician performing the work. Duplicate keys are prohibited.", body_style))
    story.append(PageBreak())

    # PAGES 10-15: SUPPLEMENTAL REGULATIONS
    story.append(Paragraph("Section 8: Incident Reporting & Emergency Protocols", h1_style))
    story.append(Paragraph("All incidents, near-misses, and minor injuries must be logged within 24 hours of occurrence. The EHS digital logger must be updated by the supervising officer. If a critical incident occurs, the floor must be evacuated immediately, and sirens activated.", body_style))
    story.append(Paragraph("Emergency stop buttons are located at every major workstation. They must remain unobstructed and clearly marked with red circular backing.", body_style))
    story.append(PageBreak())

    story.append(Paragraph("Section 9: Hazardous Materials & Chemical Handling", h1_style))
    story.append(Paragraph("Chemical storage is confined to Room 104, which is equipped with specialized ventilation and secondary containment systems. Materials Safety Data Sheets (MSDS) are stored in the yellow binders at the entrance of the chemical handling bay.", body_style))
    story.append(Paragraph("PPE for chemical transfer includes face shields, neoprene gloves, and chemical-resistant aprons. Bypassing safety showers during chemical handling is a serious violation.", body_style))
    story.append(PageBreak())

    story.append(Paragraph("Section 10: Egress & Fire Prevention Controls", h1_style))
    story.append(Paragraph("Fire doors must not be wedged open or blocked by inventory. A minimum clearance of 36 inches must be maintained in front of all electrical panels, fire extinguishers, and emergency exits. Fire drills are scheduled semi-annually, and participation is mandatory for all shifts.", body_style))
    story.append(Paragraph("Egress pathways are marked on the facility ceiling with illuminated exit signs. Floor paths must match the overhead indicators.", body_style))
    story.append(PageBreak())

    story.append(Paragraph("Section 11: Supervisor Roles & Auditing Framework", h1_style))
    story.append(Paragraph("Supervisors hold joint responsibility for their shift's safety metrics. Weekly safety audits must review the compliance event log generated by the automated detection systems. Any HIGH or CRITICAL violations must have a documented follow-up interview and corrective action plan.", body_style))
    story.append(Paragraph("Audit reports must be submitted to the corporate compliance portal by Friday 5:00 PM local time. Late submissions will trigger EHS department review.", body_style))
    story.append(PageBreak())

    story.append(Paragraph("Section 12: Continuous Safety Training Standards", h1_style))
    story.append(Paragraph("Continuous learning is fundamental to EHS compliance. All machine operators must complete 10 hours of refresher safety training annually. Virtual reality simulations will be used to train personnel on heavy vehicle avoidance and panel operations.", body_style))
    story.append(Paragraph("Contractors must complete a 1-hour site briefing prior to starting work. Clearances are valid for 90 days, after which briefing must be repeated.", body_style))
    story.append(PageBreak())

    story.append(Paragraph("Section 13: Summary Matrix and Policy Sign-off", h1_style))
    story.append(Paragraph("The following matrix summarizes the behavioral compliance standards and severity mappings:", body_style))
    
    matrix_data = [
        ["Violation Type", "Policy Ref", "Base Severity", "Escalation Condition", "Escalated Severity"],
        ["PPE Vest Violation", "Sec 3.1", "MEDIUM", "Active Loading Zone / Forklift Proximity", "HIGH"],
        ["Walkway Violation", "Sec 4.2.1", "MEDIUM", "Machinery Proximity < 1.0m / Forklift Active", "HIGH"],
        ["Opened Panel Cover", "Sec 5.2.2", "MEDIUM", "Duration > 300s / Personnel Proximity < 1.0m", "HIGH"],
        ["Forklift Overloading", "Sec 6.3.2", "CRITICAL", "None", "CRITICAL"],
        ["Unauthorized Intervention", "Sec 7.2.1", "HIGH", "Personnel Count > 1", "CRITICAL"]
    ]
    
    tbl = Table(matrix_data, colWidths=[1.8*inch, 1.0*inch, 1.1*inch, 2.0*inch, 1.2*inch])
    tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1A365D")),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8.5),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('TOPPADDING', (0,0), (-1,0), 6),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#CBD5E0")),
        ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
        ('FONTSIZE', (0,1), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    
    story.append(tbl)
    story.append(Spacer(1, 20))
    story.append(Paragraph("By order of the EHS Directorate. Compliance is mandatory.", body_style))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated {output_path}")

if __name__ == "__main__":
    generate_pdf("Compliance_Policy_Manual.pdf")
