import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter


def create_structured_pdf(file_path: str, content_scenario: str = "text_and_one_table"):
    """
    Creates a PDF with more structured content, including Platypus Tables.
    """
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    if content_scenario == "text_only":
        story.append(Paragraph("PDF Test: Simple text line 1.", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("PDF Test: Simple text line 2.", styles['Normal']))

    elif content_scenario == "text_and_one_table":
        story.append(Paragraph("PDF Test: Text before table.", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))

        data = [
            ["Header A (Col1)", "Header B (Col2)"],
            ["Data 1A", "Data 1B"],
            ["Data 2A", "Data 2B"]
        ]
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(t)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("PDF Test: Text after table.", styles['Normal']))

    elif content_scenario == "multiple_tables":
        story.append(Paragraph("PDF Test: Text before table 1.", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        data1 = [["T1H1", "T1H2"], ["T1D1", "T1D2"]]
        t1 = Table(data1)
        t1.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.green)]))
        story.append(t1)
        story.append(Spacer(1, 0.2 * inch))

        story.append(Paragraph("PDF Test: Text between tables.", styles['Normal']))
        story.append(Spacer(1, 0.2 * inch))
        data2 = [["T2H_A", "T2H_B", "T2H_C"], ["T2D_1A", "T2D_1B", "T2D_1C"]]
        t2 = Table(data2)
        t2.setStyle(TableStyle([('GRID', (0, 0), (-1, -1), 0.5, colors.blue)]))
        story.append(t2)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("PDF Test: Text after table 2.", styles['Normal']))

    else:
        story.append(Paragraph(f"Unknown content scenario: {content_scenario}", styles['Normal']))

    doc.build(story)
    print(f"Programmatically generated PDF: {file_path} for scenario: {content_scenario}")


if __name__ == '__main__':
    # Example of how to use it:
    # Ensure the 'api_test_fixtures' directory exists at the root relative to this script if running directly
    # This __main__ is more for direct testing of this utility script
    fixture_dir_for_direct_test = "api_test_fixtures_generated_pdfs"
    if not os.path.exists(fixture_dir_for_direct_test):
        os.makedirs(fixture_dir_for_direct_test)

    create_structured_pdf(os.path.join(fixture_dir_for_direct_test, "generated_text_only.pdf"), "text_only")
    create_structured_pdf(os.path.join(fixture_dir_for_direct_test, "generated_one_table.pdf"), "text_and_one_table")
    create_structured_pdf(os.path.join(fixture_dir_for_direct_test, "generated_multi_table.pdf"), "multiple_tables")