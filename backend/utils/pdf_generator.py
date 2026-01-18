"""PDF generation for workflow summaries with agent conversations and images."""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.lib import colors
from datetime import datetime
from typing import Dict, List, Any, Optional
import os


def generate_workflow_pdf(
    output_path: str,
    project_name: str,
    location_data: Dict[str, Any],
    sustainability_conversation: List[Dict[str, str]],
    indigenous_conversation: List[Dict[str, str]],
    workflow_conversation: List[Dict[str, str]],
    original_image_path: Optional[str] = None,
    future_vision_path: Optional[str] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Generate a comprehensive PDF summary of the workflow.
    
    Args:
        output_path: Path where PDF will be saved
        project_name: Name of the project
        location_data: Dict with lat, lon, territory info
        sustainability_conversation: List of {role, content} messages
        indigenous_conversation: List of {role, content} messages
        workflow_conversation: List of {role, content} messages
        original_image_path: Path to original panorama image
        future_vision_path: Path to generated future vision image
        metrics: Environmental metrics dict
    
    Returns:
        Path to generated PDF
    """
    doc = SimpleDocTemplate(output_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a1a1a'),
        spaceAfter=30,
        alignment=TA_CENTER,
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#2c3e50'),
        spaceAfter=12,
        spaceBefore=20,
    )
    
    subheading_style = ParagraphStyle(
        'CustomSubheading',
        parent=styles['Heading3'],
        fontSize=12,
        textColor=colors.HexColor('#34495e'),
        spaceAfter=8,
        spaceBefore=12,
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        spaceAfter=6,
    )
    
    # Title Page
    story.append(Paragraph("REMAP", title_style))
    story.append(Paragraph("Land Before Lines", styles['Heading3']))
    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(f"<b>Project Summary:</b> {project_name}", heading_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", body_style))
    story.append(Spacer(1, 0.5 * inch))
    
    # Location Information
    story.append(Paragraph("Location Details", heading_style))
    if location_data:
        location_info = [
            ["Coordinates", f"{location_data.get('lat', 'N/A'):.4f}, {location_data.get('lon', 'N/A'):.4f}"],
        ]
        if location_data.get('territory'):
            location_info.append(["Indigenous Territory", location_data['territory'].get('name', 'N/A')])
        if location_data.get('nearest_first_nation'):
            fn = location_data['nearest_first_nation']
            location_info.append([
                "Nearest First Nation", 
                f"{fn.get('name', 'N/A')} ({fn.get('distance_km', 'N/A')} km)"
            ])
        
        location_table = Table(location_info, colWidths=[2*inch, 4*inch])
        location_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#ecf0f1')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ]))
        story.append(location_table)
    story.append(Spacer(1, 0.3 * inch))
    
    # Environmental Metrics
    if metrics:
        story.append(Paragraph("Environmental Metrics", heading_style))
        metrics_data = []
        
        if 'normalized_score' in metrics:
            metrics_data.append(["Overall Ecological Score", f"{metrics['normalized_score']:.1f}/10"])
        
        if 'metrics' in metrics:
            m = metrics['metrics']
            if 'biodiversity_score' in m:
                metrics_data.append(["Biodiversity", f"{m['biodiversity_score'].get('score', 'N/A')}/10"])
            if 'canopy_cover' in m:
                metrics_data.append(["Canopy Cover", f"{m['canopy_cover'].get('score', 'N/A')}/10"])
            if 'flood_risk' in m:
                metrics_data.append(["Flood Risk", f"{m['flood_risk'].get('score', 'N/A')}/10"])
            if 'street_tree_count' in m:
                metrics_data.append(["Street Trees", str(m['street_tree_count'].get('value', 'N/A'))])
        
        if 'rule_compliance' in metrics:
            rc = metrics['rule_compliance']
            if 'within_300m_green_space' in rc:
                status = "Yes" if rc['within_300m_green_space'] else "No"
                metrics_data.append(["Within 300m of Green Space", status])
        
        if metrics_data:
            metrics_table = Table(metrics_data, colWidths=[3*inch, 2*inch])
            metrics_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e8f5e9')),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ]))
            story.append(metrics_table)
    
    story.append(PageBreak())
    
    # Before/After Images
    if original_image_path or future_vision_path:
        story.append(Paragraph("Visual Analysis", heading_style))
        
        if original_image_path and os.path.exists(original_image_path):
            story.append(Paragraph("Current State", subheading_style))
            try:
                img = Image(original_image_path, width=5*inch, height=3*inch)
                story.append(img)
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                story.append(Paragraph(f"<i>Image not available: {str(e)}</i>", body_style))
        
        if future_vision_path and os.path.exists(future_vision_path):
            story.append(Paragraph("Future Vision", subheading_style))
            try:
                img = Image(future_vision_path, width=5*inch, height=3*inch)
                story.append(img)
                story.append(Spacer(1, 0.2 * inch))
            except Exception as e:
                story.append(Paragraph(f"<i>Image not available: {str(e)}</i>", body_style))
        
        story.append(PageBreak())
    
    # Agent Conversations
    story.append(Paragraph("Sustainability Analysis", heading_style))
    if sustainability_conversation:
        for msg in sustainability_conversation:
            role = "You" if msg.get("role") == "user" else "Sustainability Agent"
            story.append(Paragraph(f"<b>{role}:</b>", subheading_style))
            story.append(Paragraph(msg.get("content", ""), body_style))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("<i>No sustainability conversation recorded</i>", body_style))
    
    story.append(PageBreak())
    
    story.append(Paragraph("Indigenous Context", heading_style))
    if indigenous_conversation:
        for msg in indigenous_conversation:
            role = "You" if msg.get("role") == "user" else "Indigenous Context Agent"
            story.append(Paragraph(f"<b>{role}:</b>", subheading_style))
            story.append(Paragraph(msg.get("content", ""), body_style))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("<i>No indigenous context conversation recorded</i>", body_style))
    
    story.append(PageBreak())
    
    story.append(Paragraph("Proposal Workflow", heading_style))
    if workflow_conversation:
        for msg in workflow_conversation:
            role = "You" if msg.get("role") == "user" else "Proposal Agent"
            story.append(Paragraph(f"<b>{role}:</b>", subheading_style))
            story.append(Paragraph(msg.get("content", ""), body_style))
            story.append(Spacer(1, 0.1 * inch))
    else:
        story.append(Paragraph("<i>No workflow conversation recorded</i>", body_style))
    
    # Build PDF
    doc.build(story)
    return output_path
