"""Synthetic PPTX Test Data Generator for Member 3
Cadence Financial Group - Case Study 2: Text Analysis & PII Detection

Generates 7 synthetic PPTX test files and corresponding ground-truth JSON files.
All personal data is purely synthetic for testing purposes.
"""

import os
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.chart import XL_CHART_TYPE
from pptx.chart.data import CategoryChartData


def create_badge_image(filepath: str, title: str, lines: list[str], width: int = 600, height: int = 300):
    """Generate a clean synthetic badge/card image with clear text for OCR testing."""
    img = Image.new("RGB", (width, height), color=(245, 247, 250))
    draw = ImageDraw.Draw(img)

    # Header banner
    draw.rectangle([(0, 0), (width, 50)], fill=(20, 45, 85))
    draw.text((20, 15), title, fill=(255, 255, 255))

    # Border
    draw.rectangle([(1, 1), (width - 2, height - 2)], outline=(180, 190, 205), width=2)

    # Body lines
    y = 75
    for line in lines:
        draw.text((30, y), line, fill=(30, 40, 55))
        y += 35

    img.save(filepath)
    return filepath


def generate_test1_text_boxes(pptx_dir: Path, gt_dir: Path):
    """TEST 1: Text boxes, titles, headings, paragraphs, synthetic PII."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Executive Committee
    s1 = prs.slides.add_slide(blank_layout)
    # Title
    t_box = s1.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(8.4), Inches(1.0))
    tf = t_box.text_frame
    p = tf.paragraphs[0]
    p.text = "Cadence Executive Committee"
    p.font.size = Pt(26)
    p.font.bold = True

    # Executive 1
    e1_box = s1.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(4.0), Inches(2.2))
    tf1 = e1_box.text_frame
    tf1.word_wrap = True
    p1 = tf1.paragraphs[0]
    p1.text = "Eleanor Vance"
    p1.font.bold = True
    p1.font.size = Pt(16)
    p2 = tf1.add_paragraph()
    p2.text = "Managing Director, Global Treasury"
    p3 = tf1.add_paragraph()
    p3.text = "Email: e.vance@cadencefg.example"
    p4 = tf1.add_paragraph()
    p4.text = "Direct: +1 (555) 234-8901 | ID: CFG-EXEC-0101"

    # Executive 2
    e2_box = s1.shapes.add_textbox(Inches(5.2), Inches(1.8), Inches(4.0), Inches(2.2))
    tf2 = e2_box.text_frame
    tf2.word_wrap = True
    p1 = tf2.paragraphs[0]
    p1.text = "Julian Thorne"
    p1.font.bold = True
    p1.font.size = Pt(16)
    p2 = tf2.add_paragraph()
    p2.text = "Head of Operational Resilience"
    p3 = tf2.add_paragraph()
    p3.text = "Email: j.thorne@cadencefg.example"
    p4 = tf2.add_paragraph()
    p4.text = "Direct: +1 (555) 234-8902 | ID: CFG-EXEC-0102"

    # Slide 2: Compliance Officers
    s2 = prs.slides.add_slide(blank_layout)
    t2_box = s2.shapes.add_textbox(Inches(0.8), Inches(0.6), Inches(8.4), Inches(1.0))
    tf2 = t2_box.text_frame
    p = tf2.paragraphs[0]
    p.text = "Cadence Compliance Officers"
    p.font.size = Pt(26)
    p.font.bold = True

    body_box = s2.shapes.add_textbox(Inches(0.8), Inches(1.8), Inches(8.4), Inches(4.5))
    tfe = body_box.text_frame
    tfe.word_wrap = True

    c1 = tfe.paragraphs[0]
    c1.text = "Siddharth Rao - VP, AML & Sanctions"
    c1.font.bold = True
    c2 = tfe.add_paragraph()
    c2.text = "Contact: s.rao@cadencefg.example | Phone: +1 (555) 345-6789"
    c3 = tfe.add_paragraph()
    c3.text = "Claire Dupont - Director, Data Privacy"
    c3.font.bold = True
    c4 = tfe.add_paragraph()
    c4.text = "Contact: c.dupont@cadencefg.example | Phone: +1 (555) 345-6790"

    file_path = pptx_dir / "test1_text_boxes_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test1_text_boxes_pii.pptx",
        "total_slides": 2,
        "total_text_blocks": 5,
        "total_tables": 0,
        "total_table_cells": 0,
        "total_charts": 0,
        "total_speaker_notes": 0,
        "total_images": 0,
        "expected_titles": ["Cadence Executive Committee", "Cadence Compliance Officers"],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Eleanor Vance", "slide": 1},
            {"type": "EMAIL", "text": "e.vance@cadencefg.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 234-8901", "slide": 1},
            {"type": "EMPLOYEE_ID", "text": "CFG-EXEC-0101", "slide": 1},
            {"type": "NAME", "text": "Julian Thorne", "slide": 1},
            {"type": "EMAIL", "text": "j.thorne@cadencefg.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 234-8902", "slide": 1},
            {"type": "EMPLOYEE_ID", "text": "CFG-EXEC-0102", "slide": 1},
            {"type": "NAME", "text": "Siddharth Rao", "slide": 2},
            {"type": "EMAIL", "text": "s.rao@cadencefg.example", "slide": 2},
            {"type": "PHONE", "text": "+1 (555) 345-6789", "slide": 2},
            {"type": "NAME", "text": "Claire Dupont", "slide": 2},
            {"type": "EMAIL", "text": "c.dupont@cadencefg.example", "slide": 2},
            {"type": "PHONE", "text": "+1 (555) 345-6790", "slide": 2}
        ]
    }
    with open(gt_dir / "test1_text_boxes_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test2_tables(pptx_dir: Path, gt_dir: Path):
    """TEST 2: Tables containing synthetic PII, multiple rows and columns."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Vendor Management Directory Table
    s1 = prs.slides.add_slide(blank_layout)
    tb = s1.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb.text_frame.text = "Vendor Management Directory"

    rows, cols = 5, 4
    table_shape = s1.shapes.add_table(rows, cols, Inches(0.8), Inches(1.5), Inches(8.4), Inches(3.0))
    table = table_shape.table

    headers = ["Vendor Contact", "Role", "Email", "Phone"]
    for col_idx, h in enumerate(headers):
        cell = table.cell(0, col_idx)
        cell.text = h

    data1 = [
        ["Arthur Pendelton", "Primary Onboarding Lead", "a.pendelton@fintechvendor.example", "+1 (555) 789-0123"],
        ["Beatrice Moreno", "Technical Account Manager", "b.moreno@cloudresilience.example", "+1 (555) 789-0124"],
        ["Chen Wei", "SOC 2 Lead Auditor", "w.chen@securityassessors.example", "+1 (555) 789-0125"],
        ["Daria Kowalski", "Escalation Manager", "d.kowalski@paymentgateway.example", "+1 (555) 789-0126"]
    ]
    for row_idx, row in enumerate(data1, start=1):
        for col_idx, val in enumerate(row):
            table.cell(row_idx, col_idx).text = val

    # Slide 2: Internal TPRM Reviewers Table
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb2.text_frame.text = "Internal TPRM Reviewers Table"

    table_shape2 = s2.shapes.add_table(4, 3, Inches(0.8), Inches(1.5), Inches(8.4), Inches(2.6))
    table2 = table_shape2.table
    headers2 = ["Reviewer Name", "Department", "Work Email"]
    for col_idx, h in enumerate(headers2):
        table2.cell(0, col_idx).text = h

    data2 = [
        ["Ethan Gallagher", "Third-Party Risk", "e.gallagher@cadencefg.example"],
        ["Fatima Al-Mansoor", "Information Security", "f.almansoor@cadencefg.example"],
        ["Gabriel Santos", "Legal & Contracts", "g.santos@cadencefg.example"]
    ]
    for row_idx, row in enumerate(data2, start=1):
        for col_idx, val in enumerate(row):
            table2.cell(row_idx, col_idx).text = val

    file_path = pptx_dir / "test2_tables_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test2_tables_pii.pptx",
        "total_slides": 2,
        "total_text_blocks": 2,  # titles
        "total_tables": 2,
        "total_table_cells": 32,  # (5*4) + (4*3) = 20 + 12 = 32
        "total_charts": 0,
        "total_speaker_notes": 0,
        "total_images": 0,
        "expected_titles": ["Vendor Management Directory", "Internal TPRM Reviewers Table"],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Arthur Pendelton", "slide": 1},
            {"type": "EMAIL", "text": "a.pendelton@fintechvendor.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 789-0123", "slide": 1},
            {"type": "NAME", "text": "Beatrice Moreno", "slide": 1},
            {"type": "EMAIL", "text": "b.moreno@cloudresilience.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 789-0124", "slide": 1},
            {"type": "NAME", "text": "Chen Wei", "slide": 1},
            {"type": "EMAIL", "text": "w.chen@securityassessors.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 789-0125", "slide": 1},
            {"type": "NAME", "text": "Daria Kowalski", "slide": 1},
            {"type": "EMAIL", "text": "d.kowalski@paymentgateway.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 789-0126", "slide": 1},
            {"type": "NAME", "text": "Ethan Gallagher", "slide": 2},
            {"type": "EMAIL", "text": "e.gallagher@cadencefg.example", "slide": 2},
            {"type": "NAME", "text": "Fatima Al-Mansoor", "slide": 2},
            {"type": "EMAIL", "text": "f.almansoor@cadencefg.example", "slide": 2},
            {"type": "NAME", "text": "Gabriel Santos", "slide": 2},
            {"type": "EMAIL", "text": "g.santos@cadencefg.example", "slide": 2}
        ]
    }
    with open(gt_dir / "test2_tables_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test3_grouped_shapes(pptx_dir: Path, gt_dir: Path):
    """TEST 3: Grouped shapes (including nested groups) containing synthetic PII."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Grouped Card
    s1 = prs.slides.add_slide(blank_layout)
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb1.text_frame.text = "Tier 1 Incident Response Squad"

    group1 = s1.shapes.add_group_shape()
    sh1 = group1.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(4.5), Inches(0.6))
    sh1.text_frame.text = "Incident Commander: Hannah Abbasi"
    sh2 = group1.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(4.5), Inches(0.6))
    sh2.text_frame.text = "Title: Senior Director, Incident Response"
    sh3 = group1.shapes.add_textbox(Inches(1.0), Inches(2.9), Inches(4.5), Inches(0.6))
    sh3.text_frame.text = "Contact: h.abbasi@cadencefg.example | +1 (555) 890-1234"

    # Slide 2: Nested Group Shapes
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb2.text_frame.text = "Escalation Hierarchy"

    outer_group = s2.shapes.add_group_shape()
    top_sh = outer_group.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(6.0), Inches(0.6))
    top_sh.text_frame.text = "Lead Analyst: Ian MacIntyre (i.macintyre@cadencefg.example)"

    inner_group = outer_group.shapes.add_group_shape()
    in_sh1 = inner_group.shapes.add_textbox(Inches(1.2), Inches(2.3), Inches(5.0), Inches(0.5))
    in_sh1.text_frame.text = "Deputy Lead: Julia Chen (j.chen@cadencefg.example)"
    in_sh2 = inner_group.shapes.add_textbox(Inches(1.2), Inches(2.9), Inches(5.0), Inches(0.5))
    in_sh2.text_frame.text = "Direct Hotline: +1 (555) 890-4321"

    file_path = pptx_dir / "test3_grouped_shapes_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test3_grouped_shapes_pii.pptx",
        "total_slides": 2,
        "total_text_blocks": 8,  # 2 titles + 3 child shapes in slide 1 + 3 child shapes in slide 2
        "total_groups": 3,       # group1 on slide 1, outer_group on slide 2, inner_group on slide 2
        "total_tables": 0,
        "total_table_cells": 0,
        "total_charts": 0,
        "total_speaker_notes": 0,
        "total_images": 0,
        "expected_titles": ["Tier 1 Incident Response Squad", "Escalation Hierarchy"],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Hannah Abbasi", "slide": 1},
            {"type": "EMAIL", "text": "h.abbasi@cadencefg.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 890-1234", "slide": 1},
            {"type": "NAME", "text": "Ian MacIntyre", "slide": 2},
            {"type": "EMAIL", "text": "i.macintyre@cadencefg.example", "slide": 2},
            {"type": "NAME", "text": "Julia Chen", "slide": 2},
            {"type": "EMAIL", "text": "j.chen@cadencefg.example", "slide": 2},
            {"type": "PHONE", "text": "+1 (555) 890-4321", "slide": 2}
        ]
    }
    with open(gt_dir / "test3_grouped_shapes_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test4_image_ocr(pptx_dir: Path, gt_dir: Path, temp_dir: Path):
    """TEST 4: Image containing synthetic text/PII inside slide for OCR testing."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    s1 = prs.slides.add_slide(blank_layout)
    tb = s1.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb.text_frame.text = "Security Badge & Visitor Pass Scans"

    badge_img = temp_dir / "temp_badge.png"
    create_badge_image(
        str(badge_img),
        "CADENCE FINANCIAL GROUP - ID BADGE",
        [
            "Name: Kevin O'Connor",
            "Role: Cyber Defense Analyst",
            "Email: k.oconnor@cadencefg.example",
            "Emergency Phone: +1 (555) 678-9012",
            "Badge No: CFG-SEC-88219"
        ],
        width=580,
        height=260
    )

    pass_img = temp_dir / "temp_pass.png"
    create_badge_image(
        str(pass_img),
        "CADENCE CONTRACTOR PASS",
        [
            "Contractor: Lorraine Zhao",
            "Vendor: CyberArk Integration Services",
            "Sponsor: Solveig Aarnio",
            "Mobile: +1 (555) 678-9013"
        ],
        width=580,
        height=240
    )

    s1.shapes.add_picture(str(badge_img), Inches(0.8), Inches(1.5), width=Inches(4.2))
    s1.shapes.add_picture(str(pass_img), Inches(5.3), Inches(1.5), width=Inches(4.2))

    file_path = pptx_dir / "test4_image_ocr_pii.pptx"
    prs.save(str(file_path))

    # Clean up temp images
    if badge_img.exists():
        badge_img.unlink()
    if pass_img.exists():
        pass_img.unlink()

    gt = {
        "file_name": "test4_image_ocr_pii.pptx",
        "total_slides": 1,
        "total_text_blocks": 1,  # title
        "total_tables": 0,
        "total_table_cells": 0,
        "total_charts": 0,
        "total_speaker_notes": 0,
        "total_images": 2,
        "expected_titles": ["Security Badge & Visitor Pass Scans"],
        "expected_image_text": [
            "CADENCE FINANCIAL GROUP - ID BADGE\nName: Kevin O'Connor\nEmail: k.oconnor@cadencefg.example\nPhone: +1 (555) 678-9012",
            "CADENCE CONTRACTOR PASS\nContractor: Lorraine Zhao\nSponsor: Solveig Aarnio\nMobile: +1 (555) 678-9013"
        ],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Kevin O'Connor", "location": "image_1"},
            {"type": "EMAIL", "text": "k.oconnor@cadencefg.example", "location": "image_1"},
            {"type": "PHONE", "text": "+1 (555) 678-9012", "location": "image_1"},
            {"type": "NAME", "text": "Lorraine Zhao", "location": "image_2"},
            {"type": "PHONE", "text": "+1 (555) 678-9013", "location": "image_2"}
        ]
    }
    with open(gt_dir / "test4_image_ocr_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test5_charts(pptx_dir: Path, gt_dir: Path):
    """TEST 5: Chart with titles, categories, and series text."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Clustered Column Chart
    s1 = prs.slides.add_slide(blank_layout)
    tb = s1.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb.text_frame.text = "Third-Party Assessment Progress by Tier"

    cd = CategoryChartData()
    cd.categories = ["Tier 1 High Risk", "Tier 2 Moderate Risk", "Tier 3 Low Risk"]
    cd.add_series("Completed Reviews", (24, 45, 110))
    cd.add_series("Pending Reviews", (6, 12, 18))

    chart_shape = s1.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(1.0), Inches(1.5), Inches(8.0), Inches(4.5), cd
    )
    chart = chart_shape.chart
    chart.has_title = True
    chart.chart_title.text_frame.text = "2026 Vendor Assessments by Tier"

    # Slide 2: Line Chart
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb2.text_frame.text = "Division Security Remediation"

    cd2 = CategoryChartData()
    cd2.categories = ["Treasury", "Operations", "Technology", "Risk"]
    cd2.add_series("SLA Compliant", (95, 88, 92, 98))
    cd2.add_series("Past Due", (5, 12, 8, 2))

    chart_shape2 = s2.shapes.add_chart(
        XL_CHART_TYPE.LINE,
        Inches(1.0), Inches(1.5), Inches(8.0), Inches(4.5), cd2
    )
    chart2 = chart_shape2.chart
    chart2.has_title = True
    chart2.chart_title.text_frame.text = "Remediation SLA Compliance %"

    file_path = pptx_dir / "test5_charts_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test5_charts_pii.pptx",
        "total_slides": 2,
        "total_text_blocks": 2,
        "total_tables": 0,
        "total_table_cells": 0,
        "total_charts": 2,
        "total_speaker_notes": 0,
        "total_images": 0,
        "expected_titles": ["Third-Party Assessment Progress by Tier", "Division Security Remediation"],
        "expected_chart_data": [
            {
                "title": "2026 Vendor Assessments by Tier",
                "categories": ["Tier 1 High Risk", "Tier 2 Moderate Risk", "Tier 3 Low Risk"],
                "series": ["Completed Reviews", "Pending Reviews"]
            },
            {
                "title": "Remediation SLA Compliance %",
                "categories": ["Treasury", "Operations", "Technology", "Risk"],
                "series": ["SLA Compliant", "Past Due"]
            }
        ],
        "expected_pii_entities": []
    }
    with open(gt_dir / "test5_charts_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test6_speaker_notes(pptx_dir: Path, gt_dir: Path):
    """TEST 6: Speaker notes containing synthetic PII."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1
    s1 = prs.slides.add_slide(blank_layout)
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb1.text_frame.text = "Board Risk Briefing"
    body1 = s1.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(2.0))
    body1.text_frame.text = "Confidential Quarterly TPRM Review - For Board Eyes Only."

    notes_slide1 = s1.notes_slide
    ntf1 = notes_slide1.notes_text_frame
    ntf1.text = (
        "CONFIDENTIAL SPEAKER NOTES:\n"
        "Lead coordinator: Marcus Brody (m.brody@cadencefg.example, +1 (555) 432-1098).\n"
        "Please escalate any direct board queries to Solveig Aarnio before Thursday."
    )

    # Slide 2
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb2.text_frame.text = "Internal Audit Findings"
    body2 = s2.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(2.0))
    body2.text_frame.text = "Remediation Plan for Finding 2025-04: Third-Party Access Reviews."

    notes_slide2 = s2.notes_slide
    ntf2 = notes_slide2.notes_text_frame
    ntf2.text = (
        "Audit Lead Contact:\n"
        "Nina Rostova, Principal Auditor\n"
        "Email: n.rostova@cadencefg.example | Direct: +1 (555) 432-1099"
    )

    file_path = pptx_dir / "test6_speaker_notes_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test6_speaker_notes_pii.pptx",
        "total_slides": 2,
        "total_text_blocks": 4,  # 2 titles + 2 bodies
        "total_tables": 0,
        "total_table_cells": 0,
        "total_charts": 0,
        "total_speaker_notes": 2,
        "total_images": 0,
        "expected_titles": ["Board Risk Briefing", "Internal Audit Findings"],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Marcus Brody", "location": "speaker_notes_slide_1"},
            {"type": "EMAIL", "text": "m.brody@cadencefg.example", "location": "speaker_notes_slide_1"},
            {"type": "PHONE", "text": "+1 (555) 432-1098", "location": "speaker_notes_slide_1"},
            {"type": "NAME", "text": "Nina Rostova", "location": "speaker_notes_slide_2"},
            {"type": "EMAIL", "text": "n.rostova@cadencefg.example", "location": "speaker_notes_slide_2"},
            {"type": "PHONE", "text": "+1 (555) 432-1099", "location": "speaker_notes_slide_2"}
        ]
    }
    with open(gt_dir / "test6_speaker_notes_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_test7_mixed_complex(pptx_dir: Path, gt_dir: Path, temp_dir: Path):
    """TEST 7: Mixed complex deck containing text, tables, groups, images, charts, and notes."""
    prs = pptx.Presentation()
    blank_layout = prs.slide_layouts[6]

    # Slide 1: Title & Overview
    s1 = prs.slides.add_slide(blank_layout)
    tb1 = s1.shapes.add_textbox(Inches(0.8), Inches(0.8), Inches(8.4), Inches(1.0))
    tb1.text_frame.text = "Integrated TPRM Oversight Deck"
    sub1 = s1.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(8.4), Inches(1.5))
    sub1.text_frame.text = (
        "Cadence Financial Group - Governance & Third-Party Assurance Program\n"
        "Executive Contact: Oliver Vance (o.vance@cadencefg.example, +1 (555) 998-1100)"
    )

    # Slide 2: Table with synthetic PII
    s2 = prs.slides.add_slide(blank_layout)
    tb2 = s2.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb2.text_frame.text = "Vendor Assessment Matrix"
    tbl2_shape = s2.shapes.add_table(4, 4, Inches(0.8), Inches(1.5), Inches(8.4), Inches(2.6))
    tbl2 = tbl2_shape.table
    tbl2_headers = ["Vendor Name", "Category", "Relationship Lead", "Contact Email"]
    for c_idx, h in enumerate(tbl2_headers):
        tbl2.cell(0, c_idx).text = h
    tbl2_rows = [
        ["CloudStorage Pro", "Hosting", "Penelope Cruz-Wood", "p.cruzwood@cloudstorage.example"],
        ["SecureAuth IDP", "IAM & SSO", "Quentin Blake", "q.blake@secureauth.example"],
        ["Apex Core Ledger", "Core Banking", "Rohan Mehta", "r.mehta@apexledger.example"]
    ]
    for r_idx, row in enumerate(tbl2_rows, start=1):
        for c_idx, val in enumerate(row):
            tbl2.cell(r_idx, c_idx).text = val

    # Slide 3: Grouped Shapes
    s3 = prs.slides.add_slide(blank_layout)
    tb3 = s3.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb3.text_frame.text = "Incident Management Cells"
    g3 = s3.shapes.add_group_shape()
    sh3_1 = g3.shapes.add_textbox(Inches(1.0), Inches(1.5), Inches(4.5), Inches(0.6))
    sh3_1.text_frame.text = "Incident Lead: Samantha Sterling"
    sh3_2 = g3.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(4.5), Inches(0.6))
    sh3_2.text_frame.text = "Email: s.sterling@cadencefg.example | Mobile: +1 (555) 998-1122"

    # Slide 4: Image with OCR text
    s4 = prs.slides.add_slide(blank_layout)
    tb4 = s4.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb4.text_frame.text = "Security Authorization & Credential Verification"

    badge_img = temp_dir / "temp_badge_s4.png"
    create_badge_image(
        str(badge_img),
        "CADENCE ACCESS CLEARANCE",
        [
            "Officer: Thomas K. Bennett",
            "Dept: Core Banking Platforms",
            "Email: t.bennett@cadencefg.example",
            "Phone: +1 (555) 998-1133"
        ],
        width=560,
        height=240
    )
    s4.shapes.add_picture(str(badge_img), Inches(1.5), Inches(1.8), width=Inches(5.0))
    if badge_img.exists():
        badge_img.unlink()

    # Slide 5: Chart
    s5 = prs.slides.add_slide(blank_layout)
    tb5 = s5.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb5.text_frame.text = "Risk Metrics & Performance"
    cd5 = CategoryChartData()
    cd5.categories = ["Critical", "High", "Medium", "Low"]
    cd5.add_series("Open Issues", (4, 11, 28, 42))
    cd5.add_series("Remediated", (18, 35, 60, 95))
    c5_shape = s5.shapes.add_chart(
        XL_CHART_TYPE.COLUMN_CLUSTERED,
        Inches(1.0), Inches(1.5), Inches(8.0), Inches(4.5), cd5
    )
    c5 = c5_shape.chart
    c5.has_title = True
    c5.chart_title.text_frame.text = "Quarterly Findings Remediation"

    # Slide 6: Speaker Notes
    s6 = prs.slides.add_slide(blank_layout)
    tb6 = s6.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(8.4), Inches(0.8))
    tb6.text_frame.text = "Governance Conclusions & Next Steps"
    b6 = s6.shapes.add_textbox(Inches(0.8), Inches(1.5), Inches(8.4), Inches(2.0))
    b6.text_frame.text = "Annual TPRM compliance report ready for Board Audit Committee submission."
    s6.notes_slide.notes_text_frame.text = (
        "Slide Note: Final review conducted by Ursula Klein (u.klein@cadencefg.example, +1 (555) 998-1144). "
        "Approval logged in Governance Register."
    )

    file_path = pptx_dir / "test7_mixed_complex_pii.pptx"
    prs.save(str(file_path))

    gt = {
        "file_name": "test7_mixed_complex_pii.pptx",
        "total_slides": 6,
        "total_text_blocks": 8,
        "total_tables": 1,
        "total_table_cells": 16,
        "total_groups": 1,
        "total_charts": 1,
        "total_images": 1,
        "total_speaker_notes": 1,
        "expected_titles": [
            "Integrated TPRM Oversight Deck",
            "Vendor Assessment Matrix",
            "Incident Management Cells",
            "Security Authorization & Credential Verification",
            "Risk Metrics & Performance",
            "Governance Conclusions & Next Steps"
        ],
        "expected_pii_entities": [
            {"type": "NAME", "text": "Oliver Vance", "slide": 1},
            {"type": "EMAIL", "text": "o.vance@cadencefg.example", "slide": 1},
            {"type": "PHONE", "text": "+1 (555) 998-1100", "slide": 1},
            {"type": "NAME", "text": "Penelope Cruz-Wood", "slide": 2},
            {"type": "EMAIL", "text": "p.cruzwood@cloudstorage.example", "slide": 2},
            {"type": "NAME", "text": "Quentin Blake", "slide": 2},
            {"type": "EMAIL", "text": "q.blake@secureauth.example", "slide": 2},
            {"type": "NAME", "text": "Rohan Mehta", "slide": 2},
            {"type": "EMAIL", "text": "r.mehta@apexledger.example", "slide": 2},
            {"type": "NAME", "text": "Samantha Sterling", "slide": 3},
            {"type": "EMAIL", "text": "s.sterling@cadencefg.example", "slide": 3},
            {"type": "PHONE", "text": "+1 (555) 998-1122", "slide": 3},
            {"type": "NAME", "text": "Thomas K. Bennett", "slide": 4},
            {"type": "EMAIL", "text": "t.bennett@cadencefg.example", "slide": 4},
            {"type": "PHONE", "text": "+1 (555) 998-1133", "slide": 4},
            {"type": "NAME", "text": "Ursula Klein", "slide": 6},
            {"type": "EMAIL", "text": "u.klein@cadencefg.example", "slide": 6},
            {"type": "PHONE", "text": "+1 (555) 998-1144", "slide": 6}
        ]
    }
    with open(gt_dir / "test7_mixed_complex_pii.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def generate_cadence_org_pack_ground_truth(pptx_dir: Path, gt_dir: Path):
    """Generate ground truth inspection metadata for Cadence_Financial_Group_Organizational_Pack.pptx."""
    pack_path = pptx_dir / "Cadence_Financial_Group_Organizational_Pack.pptx"
    if not pack_path.exists():
        print("Warning: Cadence Organizational Pack not found in pptx dir.")
        return

    prs = pptx.Presentation(str(pack_path))
    total_slides = len(prs.slides)
    total_tables = 0
    total_table_cells = 0
    total_images = 0
    total_speaker_notes = 0
    total_charts = 0
    titles = []

    for idx, slide in enumerate(prs.slides, 1):
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            total_speaker_notes += 1
        for s in slide.shapes:
            if s.has_table:
                total_tables += 1
                total_table_cells += len(s.table.rows) * len(s.table.columns)
            elif s.has_chart:
                total_charts += 1
            elif s.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                total_images += 1
            elif s.has_text_frame and s.text_frame.text.strip():
                # Check for slide title candidate
                txt = s.text_frame.text.strip()
                if any(k in txt for k in ["Organization at a Glance", "Executive Leadership", "Technology & Data", "Risk, Compliance", "RACI", "Role Holder Directory", "Handling of Personal Data", "Organizational Reference"]):
                    if txt.split("\n")[0] not in titles:
                        titles.append(txt.split("\n")[0])

    gt = {
        "file_name": "Cadence_Financial_Group_Organizational_Pack.pptx",
        "total_slides": total_slides,
        "total_tables": total_tables,
        "total_table_cells": total_table_cells,
        "total_charts": total_charts,
        "total_images": total_images,
        "total_speaker_notes": total_speaker_notes,
        "expected_titles": titles,
        "classification": "Internal - Confidential",
        "is_reference_pack": True
    }
    with open(gt_dir / "Cadence_Financial_Group_Organizational_Pack.json", "w", encoding="utf-8") as f:
        json.dump(gt, f, indent=2)


def main():
    base_dir = Path(__file__).resolve().parent.parent
    pptx_dir = base_dir / "pptx"
    gt_dir = base_dir / "ground_truth"
    temp_dir = base_dir / "temp"

    pptx_dir.mkdir(parents=True, exist_ok=True)
    gt_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)

    print("Generating Test 1: Text Boxes & PII...")
    generate_test1_text_boxes(pptx_dir, gt_dir)

    print("Generating Test 2: Tables & PII...")
    generate_test2_tables(pptx_dir, gt_dir)

    print("Generating Test 3: Grouped Shapes & PII...")
    generate_test3_grouped_shapes(pptx_dir, gt_dir)

    print("Generating Test 4: Image OCR & PII...")
    generate_test4_image_ocr(pptx_dir, gt_dir, temp_dir)

    print("Generating Test 5: Charts...")
    generate_test5_charts(pptx_dir, gt_dir)

    print("Generating Test 6: Speaker Notes & PII...")
    generate_test6_speaker_notes(pptx_dir, gt_dir)

    print("Generating Test 7: Mixed Complex Deck...")
    generate_test7_mixed_complex(pptx_dir, gt_dir, temp_dir)

    print("Generating Cadence Organizational Pack Ground Truth...")
    generate_cadence_org_pack_ground_truth(pptx_dir, gt_dir)

    if temp_dir.exists():
        try:
            temp_dir.rmdir()
        except Exception:
            pass

    print("All synthetic test datasets and ground-truth metadata generated successfully!")


if __name__ == "__main__":
    main()
