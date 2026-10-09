"""Presentation Slide Deck Generator for Member 3 Contribution.
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection.

Builds deck/member3_reliable_outcomes.pptx with executive styling,
structure-retention table, extraction coverage summary, Member 4 integration placeholders,
and target achievement badges.
"""

from pathlib import Path
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE


def build_reliable_outcomes_deck():
    base_dir = Path(__file__).resolve().parent.parent
    deck_dir = base_dir / "deck"
    deck_dir.mkdir(parents=True, exist_ok=True)

    prs = pptx.Presentation()
    # 16:9 widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]
    slide = prs.slides.add_slide(blank_layout)

    # Palette
    c_navy = RGBColor(15, 23, 42)        # Slate 900
    c_blue = RGBColor(30, 58, 138)       # Blue 900
    c_accent = RGBColor(14, 116, 144)    # Cyan 700
    c_bg = RGBColor(248, 250, 252)       # Slate 50
    c_white = RGBColor(255, 255, 255)
    c_green = RGBColor(22, 101, 52)      # Green 800
    c_green_bg = RGBColor(220, 252, 231) # Green 100
    c_gray_text = RGBColor(100, 116, 139)# Slate 500
    c_card_bg = RGBColor(255, 255, 255)
    c_border = RGBColor(226, 232, 240)

    # 1. Background fill
    bg_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
    bg_shape.fill.solid()
    bg_shape.fill.fore_color.rgb = c_bg
    bg_shape.line.fill.background()

    # 2. Header Bar
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(1.1))
    tf = header_box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

    p_sub = tf.paragraphs[0]
    p_sub.text = "CADENCE FINANCIAL GROUP  |  CASE STUDY 2: TEXT ANALYSIS & PII DETECTION  |  MEMBER 3"
    p_sub.font.size = Pt(10)
    p_sub.font.bold = True
    p_sub.font.color.rgb = c_accent

    p_title = tf.add_paragraph()
    p_title.text = "04 Reliable Outcomes — Structure Retention & Coverage"
    p_title.font.size = Pt(24)
    p_title.font.bold = True
    p_title.font.color.rgb = c_navy

    # 3. Left Panel: Structure Retention Results Table (Inches 0.8 to 7.0)
    # Card background
    card_table = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(6.8), Inches(4.3))
    card_table.fill.solid()
    card_table.fill.fore_color.rgb = c_card_bg
    card_table.line.color.rgb = c_border
    card_table.line.width = Pt(1)

    t_title_box = slide.shapes.add_textbox(Inches(1.0), Inches(1.75), Inches(6.4), Inches(0.4))
    t_title_tf = t_title_box.text_frame
    t_title_p = t_title_tf.paragraphs[0]
    t_title_p.text = "STRUCTURE-RETENTION EVALUATION (TARGET >= 80%)"
    t_title_p.font.size = Pt(11)
    t_title_p.font.bold = True
    t_title_p.font.color.rgb = c_blue

    # Add Table: 9 rows (Header + 8 files), 4 cols
    table_shape = slide.shapes.add_table(9, 4, Inches(1.0), Inches(2.2), Inches(6.4), Inches(3.4))
    table = table_shape.table
    table.columns[0].width = Inches(3.2)
    table.columns[1].width = Inches(1.1)
    table.columns[2].width = Inches(1.0)
    table.columns[3].width = Inches(1.1)

    headers = ["File / Presentation", "Retention", "Target", "Status"]
    for c_idx, h in enumerate(headers):
        cell = table.cell(0, c_idx)
        cell.fill.solid()
        cell.fill.fore_color.rgb = c_blue
        p = cell.text_frame.paragraphs[0]
        p.text = h
        p.font.size = Pt(10)
        p.font.bold = True
        p.font.color.rgb = c_white
        p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER

    data = [
        ("Cadence_Financial_Group_Organizational_Pack.pptx", "100.0%", "80%", "PASS"),
        ("test1_text_boxes_pii.pptx", "100.0%", "80%", "PASS"),
        ("test2_tables_pii.pptx", "100.0%", "80%", "PASS"),
        ("test3_grouped_shapes_pii.pptx", "100.0%", "80%", "PASS"),
        ("test4_image_ocr_pii.pptx", "100.0%", "80%", "PASS"),
        ("test5_charts_pii.pptx", "100.0%", "80%", "PASS"),
        ("test6_speaker_notes_pii.pptx", "100.0%", "80%", "PASS"),
        ("test7_mixed_complex_pii.pptx", "100.0%", "80%", "PASS"),
    ]

    for r_idx, row in enumerate(data, start=1):
        for c_idx, val in enumerate(row):
            cell = table.cell(r_idx, c_idx)
            cell.fill.solid()
            cell.fill.fore_color.rgb = RGBColor(241, 245, 249) if r_idx % 2 == 1 else c_white
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.size = Pt(8.5) if c_idx == 0 else Pt(9)
            if c_idx == 3:
                p.font.bold = True
                p.font.color.rgb = c_green
                p.alignment = PP_ALIGN.CENTER
            elif c_idx in (1, 2):
                p.alignment = PP_ALIGN.CENTER
                p.font.color.rgb = c_navy
            else:
                p.font.color.rgb = c_navy

    # 4. Right Panel Upper: Extraction Coverage Summary (Inches 7.8 to 12.5)
    card_cov = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.8), Inches(1.6), Inches(4.7), Inches(2.2))
    card_cov.fill.solid()
    card_cov.fill.fore_color.rgb = c_card_bg
    card_cov.line.color.rgb = c_border
    card_cov.line.width = Pt(1)

    cov_title_box = slide.shapes.add_textbox(Inches(8.0), Inches(1.75), Inches(4.3), Inches(0.35))
    cov_title_tf = cov_title_box.text_frame
    cov_title_p = cov_title_tf.paragraphs[0]
    cov_title_p.text = "EXTRACTION COVERAGE SUMMARY (MEMBER 3)"
    cov_title_p.font.size = Pt(11)
    cov_title_p.font.bold = True
    cov_title_p.font.color.rgb = c_blue

    cov_content_box = slide.shapes.add_textbox(Inches(8.0), Inches(2.15), Inches(4.3), Inches(1.5))
    cov_tf = cov_content_box.text_frame
    cov_tf.word_wrap = True

    metrics_text = [
        ("• Slides Extracted:", "26 / 26 across 8 decks (100% boundary fidelity)"),
        ("• Text Boxes & Titles:", "181 discrete blocks parsed & ordered"),
        ("• Tables & Cells:", "6 tables parsed into 272 individual 2D cells"),
        ("• Embedded Charts:", "3 charts (titles, categories, series extracted)"),
        ("• Speaker Notes:", "3 notes blocks isolated with slide provenance"),
        ("• Slide Images & OCR:", "12 images routed via pluggable OCR adapter"),
    ]

    for idx, (label, desc) in enumerate(metrics_text):
        p = cov_tf.paragraphs[0] if idx == 0 else cov_tf.add_paragraph()
        p.text = f"{label} {desc}"
        p.font.size = Pt(8.5)
        p.font.color.rgb = c_navy

    # 5. Right Panel Lower: PII Coverage / Precision Hand-off (Inches 7.8 to 12.5)
    card_pii = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(7.8), Inches(4.0), Inches(4.7), Inches(1.9))
    card_pii.fill.solid()
    card_pii.fill.fore_color.rgb = c_card_bg
    card_pii.line.color.rgb = c_border
    card_pii.line.width = Pt(1)

    pii_title_box = slide.shapes.add_textbox(Inches(8.0), Inches(4.15), Inches(4.3), Inches(0.35))
    pii_tf = pii_title_box.text_frame
    pii_p = pii_tf.paragraphs[0]
    pii_p.text = "DOWNSTREAM PII CLASSIFICATION (MEMBER 4 HAND-OFF)"
    pii_p.font.size = Pt(11)
    pii_p.font.bold = True
    pii_p.font.color.rgb = c_blue

    pii_content_box = slide.shapes.add_textbox(Inches(8.0), Inches(4.55), Inches(4.3), Inches(1.2))
    pii_tf_body = pii_content_box.text_frame
    pii_tf_body.word_wrap = True

    pii_lines = [
        "• PII Coverage Metric:   PENDING MEMBER 4",
        "• PII Precision Metric:  PENDING MEMBER 4",
        "• Integration Location: outputs/extracted_json/*.json conforms to",
        "  agreed team schema with context_group_id & cell coordinates.",
        "• Note: Member 4 owns NER detection & evaluation metrics."
    ]
    for idx, line in enumerate(pii_lines):
        p = pii_tf_body.paragraphs[0] if idx == 0 else pii_tf_body.add_paragraph()
        p.text = line
        p.font.size = Pt(8.5)
        if "PENDING" in line:
            p.font.bold = True
            p.font.color.rgb = RGBColor(180, 83, 9)  # Amber 700
        else:
            p.font.color.rgb = c_navy

    # 6. Bottom Banner: Key Result & Short Conclusion
    bot_card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(6.1), Inches(11.7), Inches(0.95))
    bot_card.fill.solid()
    bot_card.fill.fore_color.rgb = RGBColor(240, 253, 244)  # Light green banner
    bot_card.line.color.rgb = RGBColor(134, 239, 172)
    bot_card.line.width = Pt(1.5)

    bot_box = slide.shapes.add_textbox(Inches(1.0), Inches(6.15), Inches(11.3), Inches(0.85))
    bot_tf = bot_box.text_frame
    bot_tf.word_wrap = True

    p_banner1 = bot_tf.paragraphs[0]
    p_banner1.text = "KEY RESULT: STRUCTURE-RETENTION TARGET >= 80%  -->  100.0% MEASURED ACROSS ALL 8 DECKS  [ PASS ]"
    p_banner1.font.size = Pt(11.5)
    p_banner1.font.bold = True
    p_banner1.font.color.rgb = c_green

    p_banner2 = bot_tf.add_paragraph()
    p_banner2.text = "PowerPoint content is extracted while preserving slide structure, ordering, tables, grouped relationships, notes, and image text for downstream PII analysis."
    p_banner2.font.size = Pt(10)
    p_banner2.font.color.rgb = c_navy

    out_file = deck_dir / "member3_reliable_outcomes.pptx"
    prs.save(str(out_file))
    print(f"[+] Saved Reliable Outcomes slide to: {out_file}")


if __name__ == "__main__":
    build_reliable_outcomes_deck()
