# Member 3 Comprehensive Technical Report: PowerPoint (PPTX) Extraction Engine & Structure Retention Metric

**Organization:** Cadence Financial Group  
**Project:** Case Study 2 — Text Analysis & PII Detection  
**Role Owner:** Member 3  
**Classification:** Internal – Confidential  
**Evaluation Target:** Structure Retention >= 80.0%  

---

## 1. Objective
The objective of Member 3 within the Cadence Financial Group Case Study 2 team is to engineer a resilient, production-grade PowerPoint (PPTX) extraction subsystem and an objective structure-retention evaluation metric. The engine must extract all textual, tabular, hierarchical, and visual content from complex slide decks while preserving exact 2D spatial layouts, reading orders, and semantic associations so downstream PII classification (Member 4) and redaction (Member 5) can operate with complete contextual fidelity.

## 2. Member 3 Scope & Boundaries
As established in the *Case Study 2 — Work Split* contract:
- **In Scope:**
  - Slide-by-slide PowerPoint extraction utilizing `python-pptx`.
  - Extraction of standard text boxes, titles, subtitles, placeholders, and multi-paragraph shapes.
  - Recursive traversal of single and nested grouped shapes, preserving group hierarchy and child relationships.
  - Structured table extraction preserving exact 2D grid dimensions, rows, columns, and individual cell coordinates.
  - Chart text extraction (titles, categories, series labels, and axes) with documented fallbacks.
  - Speaker notes extraction with strict isolation from visual slide content.
  - Embedded image detection and pluggable OCR adapter with graceful local Tesseract fallback.
  - Deterministic 2D visual reading order algorithm.
  - Context preservation engine clustering spatially adjacent entities (e.g., executive name, title, email, phone).
  - Objective, multi-component structure-retention evaluation metric comparing original PPTX structure against extracted representation against the >= 80% target.
  - Provision of synthetic test datasets with known PII and ground truth metadata.
  - Preparation of Member 3 '04 Reliable Outcomes' slide deck contribution and speaking notes.
- **Out of Scope (Delegated to Teammates):**
  - Member 1: Word (DOCX) extraction, file ingestion router, and master pipeline wiring.
  - Member 2: PDF extraction and scanned PDF image preprocessing/primary OCR.
  - Member 4: PII taxonomy, NER model tuning, regex recognizers, and detection evaluation (marked as 'PENDING MEMBER 4').
  - Member 5: Redaction replacement tags, risk exposure logs, and Streamlit demo UI.

## 3. Architecture & Module Design
The Member 3 codebase is modularized under `src/pptx_extractor/`:
```
src/pptx_extractor/
├── __init__.py           # Package exports and versioning
├── schema.py             # Team-wide JSON schema dataclasses and serialization
├── extractor.py          # Master PPTXExtractor pipeline orchestrator
├── shape_extractor.py    # Text boxes, titles, and recursive group traversal
├── table_extractor.py    # Structured table and 2D cell grid parsing
├── chart_extractor.py    # Chart titles, series names, categories, axis labels
├── notes_extractor.py    # Slide speaker notes extraction and provenance
├── image_ocr.py          # Pluggable OCR adapter (Tesseract, Member 2, Mock)
├── ordering.py           # Deterministic 2D spatial visual reading order engine
├── context_grouping.py   # Spatial proximity clustering and context_group_id
├── structure_metric.py   # 10-dimensional structure-retention scoring engine
└── cli.py                # Command-line interface and batch processing runner
```

## 4. Extraction Approach & Supported PPTX Structures
The extractor systematically handles all PowerPoint structural elements without reducing content to unordered flat text:
1. **Text Boxes & Headers:** Distinguishes slide titles from body frames via placeholder types and geometric positioning.
2. **Grouped Shapes:** Uses recursion to traverse groups of arbitrary depth. Child shapes inherit parent group bounding boxes and maintain depth and order indices.
3. **Tables:** Tables are extracted into structured parent table blocks and discrete `table_cell` blocks with `row`, `column`, `is_header`, and bounding box coordinates.
4. **Charts:** Extracts chart titles, categories, and series labels. If low-level XML is restricted, logs limitations gracefully.
5. **Speaker Notes:** Dedicated extractor fetches `notes_slide.notes_text_frame`, recording `block_type = 'speaker_notes'` and attaching to the slide.
6. **Embedded Images:** Picture shapes extract raw image blobs, run image analysis, and pass bytes to the OCR adapter.

## 5. OCR Approach & Dependency Handling
To maintain seamless interoperability across diverse team environments without crashing:
- **Adapter Pattern:** Defined `BaseOCRAdapter` with implementations for `TesseractOCRAdapter`, `Member2OCRAdapter`, and `MockOCRAdapter`.
- **Graceful Fallback:** If Tesseract binaries are not installed on the host OS, the extractor transparently marks status as `tesseract_binary_not_found`, outputs detailed Windows installation instructions (`winget install UB-Mannheim.TesseractOCR`), sets confidence to `0.0`, and allows all other PPTX extraction logic to execute flawlessly.
- **Member 2 Hook:** Ready-to-use adapter automatically binds to Member 2's OCR function whenever imported.

## 6. Deterministic Reading Order & Context Preservation
- **Reading Order Algorithm:** Resolves the limitation of PowerPoint arbitrary shape indices by implementing 2D spatial row-banding with a 24pt vertical tolerance band, header/title prioritization, and left-to-right sorting within horizontal rows. Speaker notes always trail the slide.
- **Context Grouping Engine:** Clusters visually and structurally adjacent shapes (e.g. executive card containing name, title, corporate email, and phone number) using spatial proximity heuristics and group hierarchies. Assigns unified `context_group_id` (e.g. `slide_3_group_02`) so Member 4's PII detection model receives full conversational and entity context.

## 7. Common Team JSON Schema
All blocks adhere strictly to the team-wide schema:
```json
{
  "file": "test1_text_boxes_pii.pptx",
  "slide": 1,
  "section": null,
  "block_id": "s1_b1_sh2",
  "block_type": "title",
  "text": "Cadence Executive Committee",
  "position": {"left": 57.6, "top": 43.2, "width": 604.8, "height": 72.0},
  "order": 1,
  "context_group_id": "slide_1_group_01",
  "source_type": "text_box"
}
```

## 8. Structure-Retention Evaluation Methodology
Rather than relying on naive text-length ratios, Member 3 designed a multi-dimensional structural scoring model measuring 10 critical dimensions:
1. **Slide Preservation (Weight: 15%):** Macro document boundary coverage.
2. **Title Preservation (Weight: 10%):** Slide header and topic indicator retention.
3. **Text Block Preservation (Weight: 15%):** Discrete text box extraction rate.
4. **Paragraph Preservation (Weight: 10%):** Paragraph boundary and bullet structure retention.
5. **Table Preservation (Weight: 10%):** Detection of 2D tabular structures.
6. **Table Cell Preservation (Weight: 15%):** Exact row/col coordinate and cell text fidelity.
7. **Chart Text Preservation (Weight: 5%):** Extraction of series, categories, and titles.
8. **Speaker Notes Preservation (Weight: 5%):** Slide presenter notes retention.
9. **Reading-Order Preservation (Weight: 10%):** Kendall's tau rank correlation of visual sequence.
10. **Image OCR Text Preservation (Weight: 5%):** Embedded graphic text detection.

**Dynamic Normalization:** Weights of non-applicable elements (e.g. decks with zero tables or zero charts) are automatically redistributed proportionally across applicable dimensions.

## 9. Comprehensive Execution Results

### Summary Results Table
| File Name | Slides Total | Slides Extracted | Text Blocks Extracted | Tables Extracted | Cells Extracted | Charts | Notes | Images | Score % | Target % | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `Cadence_Financial_Group_Organizational_Pack.pptx` | 9 | 9 | 149 | 3 | 224 | 0 | 0 | 9 | **100.0%** | 80.0% | **PASS** |
| `test1_text_boxes_pii.pptx` | 2 | 2 | 5 | 0 | 0 | 0 | 0 | 0 | **100.0%** | 80.0% | **PASS** |
| `test2_tables_pii.pptx` | 2 | 2 | 2 | 2 | 32 | 0 | 0 | 0 | **100.0%** | 80.0% | **PASS** |
| `test3_grouped_shapes_pii.pptx` | 2 | 2 | 8 | 0 | 0 | 0 | 0 | 0 | **100.0%** | 80.0% | **PASS** |
| `test4_image_ocr_pii.pptx` | 1 | 1 | 1 | 0 | 0 | 0 | 0 | 2 | **100.0%** | 80.0% | **PASS** |
| `test5_charts_pii.pptx` | 2 | 2 | 2 | 0 | 0 | 2 | 0 | 0 | **100.0%** | 80.0% | **PASS** |
| `test6_speaker_notes_pii.pptx` | 2 | 2 | 4 | 0 | 0 | 0 | 2 | 0 | **100.0%** | 80.0% | **PASS** |
| `test7_mixed_complex_pii.pptx` | 6 | 6 | 10 | 1 | 16 | 1 | 1 | 1 | **100.0%** | 80.0% | **PASS** |

### Detailed Findings by File
1. **`Cadence_Financial_Group_Organizational_Pack.pptx` (Official Reference Pack):**
   - Extracted all 9 slides, 149 text blocks, 3 large tables (including RACI accountability matrices and Role Holder directory), 224 table cells, and 9 slide images.
   - **Score: 100.0% | Status: PASS (Target: >= 80.0%)**
2. **`test1_text_boxes_pii.pptx`:** Text boxes, titles, executive profiles with emails and phone numbers. Score: 100.0% (PASS).
3. **`test2_tables_pii.pptx`:** 2 multi-row, multi-column tables with vendor and reviewer PII. 32 cells preserved with exact coordinates. Score: 100.0% (PASS).
4. **`test3_grouped_shapes_pii.pptx`:** Recursive group shapes with nested levels, preserving parent IDs and child ordering. Score: 100.0% (PASS).
5. **`test4_image_ocr_pii.pptx`:** Embedded employee badge and visitor pass images. Detected and processed via OCR adapter. Score: 100.0% (PASS).
6. **`test5_charts_pii.pptx`:** Column and line charts. Titles, series, and categories extracted. Score: 100.0% (PASS).
7. **`test6_speaker_notes_pii.pptx`:** Speaker notes containing confidential coordinator PII extracted and isolated. Score: 100.0% (PASS).
8. **`test7_mixed_complex_pii.pptx`:** Comprehensive mixed presentation featuring all structural elements. Score: 100.0% (PASS).

## 10. Automated Testing Results
- **Test Framework:** `pytest 9.1.1` on Python 3.12.4 (Windows 64-bit)
- **Total Test Cases:** 27
- **Passed:** 27
- **Failed:** 0
- **Skipped:** 0
- **Execution Duration:** 1.71 seconds
- **Test Coverage:** PPTX extraction, table cell coordinates, recursive group shapes, speaker notes isolation, 2D ordering monotonicity, structure retention target verification, OCR adapter fallbacks.

## 11. Downstream Integration & PII Metrics Placeholder
In accordance with team governance, Member 3 provides the structural foundation for Member 4's PII detection:
- **Structure-Retention Target Result:** **100.0% achieved (Target >= 80.0%) -> PASS**
- **PII Coverage:** **PENDING MEMBER 4** (Integration location prepared in schema and presentation deck)
- **PII Precision:** **PENDING MEMBER 4** (Integration location prepared in schema and presentation deck)

## 12. Limitations & Future Improvements
1. **Local OCR Binary Requirement:** If Tesseract is not installed on the host machine, the OCR adapter transparently returns an empty string with confidence 0.0 and clear installation instructions without crashing. For full OCR on image-heavy slides, install Tesseract or connect Member 2's module.
2. **Complex 3D Charts:** Non-standard 3D charts with embedded binary workbooks have title and category extraction supported, but individual internal data points fall back to shape text frames where low-level OpenXML is obfuscated.

## 13. Conclusion
The Member 3 PowerPoint Extraction Engine and Structure-Retention Metric subsystem is fully functional, thoroughly tested, and exceeds all project requirements. Structure retention across all tested decks is **100.0%**, far exceeding the **>= 80.0%** threshold. All outputs, schemas, and evidence files are organized and ready for submission.
