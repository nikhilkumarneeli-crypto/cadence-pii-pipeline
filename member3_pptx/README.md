# Cadence Financial Group — Case Study 2: Text Analysis & PII Detection
## Member 3 Deliverable: PowerPoint (PPTX) Extraction Engine & Structure Retention Metric

**Project:** Cadence Financial Group Case Study 2  
**Role:** Member 3  
**Status:** Completed & Validated  
**Structure Retention Target:** &ge; 80.0% | **Measured Score:** 100.0% [ PASS ]  
**Classification:** Internal – Confidential  

---

## 1. Executive Summary & Responsibilities

In Cadence Financial Group's Case Study 2 (*Text Analysis & PII Detection*), **Member 3** owns:
1. **PowerPoint (PPTX) Ingestion & Extraction Engine:** Extracting all slide content (text boxes, titles, paragraphs, grouped shapes, tables, charts, speaker notes, and embedded images) with complete 2D layout and coordinate provenance.
2. **Deterministic 2D Reading Order Algorithm:** Resolving PowerPoint's arbitrary shape ordering through spatial row-banding and header prioritization.
3. **Context Preservation Engine:** Clustering spatially proximate entities (e.g., executive name, job title, corporate email, mobile number) so downstream PII detection has full context.
4. **Objective Structure-Retention Metric:** A 10-dimensional evaluation system verifying extraction fidelity against the **&ge; 80% target**.
5. **Sample PPTX Test Datasets & Ground Truth:** Synthetic test decks covering all structural edge cases plus Cadence's official Organizational Reference Pack.
6. **Reliable Outcomes Presentation & Speaking Script:** Deliverable slide `deck/member3_reliable_outcomes.pptx` and 2.5–3 min speaking notes.

---

## 2. Project Directory Structure

All files reside inside the project workspace:

```
optiv security/
├── README.md                              # Complete technical documentation
├── requirements.txt                       # Python dependencies
├── pyproject.toml                         # Project package configuration
├── CONFIDENTIALITY.md                     # Data protection and local handling policy
├── WEBSITE_ACCESS_REQUIRED.md             # Declaration confirming local execution
├── run_pipeline.py                        # Master one-click end-to-end runner script
│
├── src/
│   └── pptx_extractor/
│       ├── __init__.py                    # Module exports and package version
│       ├── schema.py                      # Common JSON schema models & dataclasses
│       ├── extractor.py                   # Master extraction pipeline orchestrator
│       ├── shape_extractor.py             # Text boxes, titles, and recursive groups
│       ├── table_extractor.py             # 2D table grid parser with cell coordinates
│       ├── chart_extractor.py             # Chart titles, series, categories, axis labels
│       ├── notes_extractor.py             # Slide speaker notes extractor
│       ├── image_ocr.py                   # Pluggable OCR adapter (Tesseract, Member 2)
│       ├── ordering.py                    # Deterministic 2D visual reading order engine
│       ├── context_grouping.py            # Spatial proximity clustering engine
│       ├── structure_metric.py            # 10-dimensional structure retention engine
│       └── cli.py                         # CLI runner for batch extraction and CSV
│
├── tests/
│   ├── test_pptx_extractor.py             # Schema compliance and pipeline integration
│   ├── test_tables.py                     # Table cell grids and coordinate tests
│   ├── test_grouped_shapes.py             # Single and multi-tier nested group shapes
│   ├── test_notes.py                      # Speaker notes provenance and isolation
│   ├── test_ordering.py                   # Reading order monotonicity & header priority
│   ├── test_structure_metric.py           # 10-component metric scoring & >=80% target
│   └── test_image_ocr.py                  # OCR adapter interface and fallback tests
│
├── test_data/
│   ├── pptx/                              # 8 presentation files (Org Pack + 7 synthetic)
│   ├── ground_truth/                      # Ground-truth structural JSON metadata
│   └── scripts/
│       └── generate_synthetic_test_data.py # Test deck generation script
│
├── outputs/
│   ├── extracted_json/                    # Extracted common schema JSON files
│   ├── structure_metrics/                 # Per-file evaluation metric reports
│   ├── csv/
│   │   └── structure_results.csv          # Comprehensive evaluation CSV table
│   └── reports/
│       ├── member3_report.md              # Technical report in Markdown
│       └── member3_report.html            # Interactive styled HTML dashboard report
│
├── evidence/
│   ├── 01_project_structure.png           # Visual directory verification
│   ├── 02_pptx_extraction_running.png     # Terminal execution output
│   ├── 03_extracted_json.png              # Schema-compliant JSON inspection
│   ├── 04_table_extraction.png            # Table cell extraction inspection
│   ├── 05_grouped_shape_extraction.png    # Recursive group shape hierarchy
│   ├── 06_speaker_notes_extraction.png    # Speaker notes extraction
│   ├── 07_image_ocr.png                   # Image OCR adapter status and fallback
│   ├── 08_structure_metric.png            # 10-dimension metric score breakdown
│   ├── 09_csv_results.png                 # Results CSV table preview
│   ├── 10_final_report.png                # Final executive report overview
│   ├── 11_final_test_results.png          # 27 / 27 pytest test run output
│   └── screenshots_to_capture/
│       └── CAPTURE_GUIDE.md               # Manual screenshot capture instructions
│
├── scripts/
│   ├── generate_reports.py                # Compiles MD and HTML reports
│   ├── generate_slide_deck.py             # Generates member3_reliable_outcomes.pptx
│   └── generate_evidence_images.py        # Programmatically renders evidence PNGs
│
└── deck/
    ├── member3_reliable_outcomes.pptx     # 16:9 executive presentation slide
    └── member3_speaking_notes.md          # 2.5–3 min presentation script
```

---

## 3. Installation & Setup (Windows / VS Code)

### Prerequisites
- Windows 10/11
- Python 3.10+ (Tested on Python 3.12.4)
- PowerShell or Windows Command Prompt

### Step 1: Clone / Open Workspace
Open the folder in VS Code or PowerShell:
```powershell
cd "c:\Users\THANVI SREE\OneDrive\Desktop\optiv security"
```

### Step 2: (Optional) Create Virtual Environment
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### Step 3: Install Required Dependencies
```powershell
py -m pip install -r requirements.txt
```

---

## 4. How to Run

### Option A: One-Click Master Pipeline Runner (Recommended)
Executes all generation, testing, extraction, scoring, reports, slide creation, and evidence generation:
```powershell
py run_pipeline.py
```

### Option B: Individual Stage Commands

#### 1. Generate Synthetic Test Decks & Ground Truth
```powershell
py test_data\scripts\generate_synthetic_test_data.py
```

#### 2. Run Automated Pytest Suite
```powershell
py -m pytest -v
```

#### 3. Run Batch Extraction & Structure Retention Metric
```powershell
py -m src.pptx_extractor.cli
```
Options available:
```powershell
py -m src.pptx_extractor.cli --input-dir test_data/pptx --output-dir outputs --target 80.0
```

#### 4. Compile Technical Markdown & HTML Reports
```powershell
py scripts\generate_reports.py
```

#### 5. Generate Presentation Slide Deck
```powershell
py scripts\generate_slide_deck.py
```

#### 6. Generate Visual Evidence PNGs
```powershell
py scripts\generate_evidence_images.py
```

---

## 5. Architectural Deep Dive

### 5.1 Common JSON Schema
Every extracted content block strictly satisfies the team-wide specification:
```json
{
  "file": "test1_text_boxes_pii.pptx",
  "slide": 1,
  "section": null,
  "block_id": "s1_b1_sh2",
  "block_type": "title",
  "text": "Cadence Executive Committee",
  "position": {
    "left": 57.6,
    "top": 43.2,
    "width": 604.8,
    "height": 72.0
  },
  "order": 1,
  "context_group_id": "slide_1_group_01",
  "source_type": "text_box",
  "confidence": 1.0,
  "paragraphs": ["Cadence Executive Committee"]
}
```

### 5.2 Recursive Grouped Shapes
In PowerPoint, shapes may be grouped inside other groups to arbitrary depths. `ShapeExtractor` traverses this hierarchy recursively. For each child shape, it records:
- `parent_group_id`: e.g. `s2_grp_3`
- `group_depth`: `1`, `2`, ...
- Child bounding boxes and text
- Group association for spatial clustering.

### 5.3 2D Table Extraction
`TableExtractor` extracts both:
1. A consolidated parent table block representing the composite table structure.
2. Discrete `table_cell` blocks for every cell containing:
   - `row` index
   - `column` index
   - `is_header` flag
   - Exact computed 2D cell bounding box `(left, top, width, height)`.

### 5.4 Deterministic 2D Reading Order Algorithm
PowerPoint shapes are ordered by Z-order / XML creation order rather than visual reading order. `DeterministicOrderingEngine` reconstructs natural reading flow using a multi-tier sort tuple:
1. **Slide Index:** Ascending (Slide 1, Slide 2...).
2. **Notes Isolation:** Speaker notes are always placed last (`tier: 99`).
3. **Title Priority:** Slide titles and headers are placed first (`tier: 0`).
4. **Spatial Banding:** Body shapes are quantized into vertical rows using a 24-point tolerance band.
5. **Horizontal Progression:** Within each vertical row, shapes are sorted left-to-right.
6. **Table Cell Ordering:** Ordered naturally by `(row, col)`.

### 5.5 Context Preservation & Proximity Clustering
`ContextGroupingEngine` computes 2D spatial adjacency across blocks on each slide. Items that are vertically stacked (such as an executive's name, title, corporate email, and phone number in org charts) or on the same table row are clustered into a unified `context_group_id` (e.g. `slide_3_group_02`).

### 5.6 Pluggable OCR Adapter
`ImageOCRExtractor` interfaces with `BaseOCRAdapter`:
- **`TesseractOCRAdapter`:** Checks for local `tesseract.exe`. If found, performs OCR with word-level confidence. If not installed, it transparently sets status to `unavailable` and confidence to `0.0` without crashing.
- **`Member2OCRAdapter`:** Standby hook to import and reuse Member 2's shared PDF/OCR module once available.
- **`MockOCRAdapter`:** Used during unit tests to verify full OCR pipeline execution.

---

## 6. Structure-Retention Evaluation Methodology

The evaluation engine (`StructureMetricEngine`) measures structural preservation across **10 objective dimensions** rather than simple character counts:

| Dimension | Default Weight | Description |
|---|---|---|
| **Slide Preservation** | 15% | Macro slide boundary and count retention |
| **Title Preservation** | 10% | Header and semantic section title retention |
| **Text Block Preservation** | 15% | Retention of discrete body text boxes |
| **Paragraph Preservation** | 10% | Granular paragraph boundary & bullet retention |
| **Table Preservation** | 10% | Tabular structure detection rate |
| **Table Cell Preservation** | 15% | 2D cell grid coordinates and cell content rate |
| **Chart Text Preservation** | 5% | Chart titles, series, and categories rate |
| **Speaker Notes Preservation** | 5% | Speaker notes detection and slide association |
| **Reading Order Preservation** | 10% | Visual sequence monotonicity (Kendall's tau) |
| **Image OCR Coverage** | 5% | Embedded image detection & extraction coverage |

**Dynamic Normalization:** Decks without tables or charts are automatically re-weighted across applicable dimensions so they are evaluated fairly.

---

## 7. Measured Results & Verification

### Structure-Retention Results Summary
Target Threshold: **&ge; 80.0%**

| Presentation File | Slides | Blocks | Tables | Cells | Charts | Notes | Images | Score % | Status |
|---|---|---|---|---|---|---|---|---|---|
| `Cadence_Financial_Group_Organizational_Pack.pptx` | 9 | 149 | 3 | 224 | 0 | 0 | 9 | **100.0%** | **PASS** |
| `test1_text_boxes_pii.pptx` | 2 | 5 | 0 | 0 | 0 | 0 | 0 | **100.0%** | **PASS** |
| `test2_tables_pii.pptx` | 2 | 2 | 2 | 32 | 0 | 0 | 0 | **100.0%** | **PASS** |
| `test3_grouped_shapes_pii.pptx` | 2 | 8 | 0 | 0 | 0 | 0 | 0 | **100.0%** | **PASS** |
| `test4_image_ocr_pii.pptx` | 1 | 1 | 0 | 0 | 0 | 0 | 2 | **100.0%** | **PASS** |
| `test5_charts_pii.pptx` | 2 | 2 | 0 | 0 | 2 | 0 | 0 | **100.0%** | **PASS** |
| `test6_speaker_notes_pii.pptx` | 2 | 4 | 0 | 0 | 0 | 2 | 0 | **100.0%** | **PASS** |
| `test7_mixed_complex_pii.pptx` | 6 | 10 | 1 | 16 | 1 | 1 | 1 | **100.0%** | **PASS** |

### Automated Pytest Summary
- **Tests Collected:** 27
- **Passed:** 27
- **Failed:** 0
- **Pass Rate:** 100%

---

## 8. Downstream Integration & PII Metrics

In accordance with the team work split:
- **Member 3 Deliverable:** Structural extraction, context grouping, and structure retention metric (**100.0% achieved -> PASS**).
- **Member 4 Integration:** PII detection, entity taxonomy, recall, precision, and F1 evaluation belong to Member 4.
  * In the deliverable deck (`deck/member3_reliable_outcomes.pptx`) and reports, PII coverage and precision are marked as **PENDING MEMBER 4**.
  * Extracted JSON outputs in `outputs/extracted_json/` are 100% ready for Member 4's Presidio / regex detection scripts.

---

## 9. Troubleshooting & FAQ

1. **How to install Tesseract OCR on Windows?**  
   Open PowerShell as Administrator and run:
   ```powershell
   winget install UB-Mannheim.TesseractOCR
   ```
   Ensure `C:\Program Files\Tesseract-OCR` is in your Windows `PATH` environment variable.

2. **What happens if Tesseract is not installed?**  
   The extractor continues to run normally. Images are detected and logged, while OCR status is transparently marked `unavailable` with instructions.

3. **Where are the final deliverables?**  
   - Presentation Slide: `deck/member3_reliable_outcomes.pptx`
   - Speaking Script: `deck/member3_speaking_notes.md`
   - HTML Dashboard Report: `outputs/reports/member3_report.html`
   - CSV Results: `outputs/csv/structure_results.csv`
   - Visual Evidence: `evidence/01_project_structure.png` to `11_final_test_results.png`
