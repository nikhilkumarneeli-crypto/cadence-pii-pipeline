# Manual Screenshot Capture Guide for Member 3

**Project:** Cadence Financial Group — Case Study 2: Text Analysis & PII Detection  
**Role:** Member 3 (PowerPoint Extraction & Structure Retention Metric)  

This guide provides exact step-by-step instructions for manually capturing any native OS window screenshots in Windows / VS Code if you wish to supplement the automatically generated programmatic evidence files in `evidence/`.

---

### Screenshot 01: Project Directory Structure
- **Target File:** `01_project_structure.png`
- **What to Display:** The VS Code File Explorer panel expanded on the left showing the complete `optiv security` tree (`src/pptx_extractor`, `tests`, `test_data`, `outputs`, `evidence`, `deck`, `README.md`, `requirements.txt`).
- **How to Capture:** Press `Win + Shift + S`, select the VS Code window, and save to `evidence/01_project_structure.png`.

---

### Screenshot 02: Extraction Pipeline Running
- **Target File:** `02_pptx_extraction_running.png`
- **What to Display:** PowerShell terminal in VS Code after executing:
  ```powershell
  python -m src.pptx_extractor.cli
  ```
- **Visible Content:** The extraction progress across all 8 decks showing `100.0% | Status: PASS` and the summary table.

---

### Screenshot 03: Extracted Common JSON Artifact
- **Target File:** `03_extracted_json.png`
- **What to Display:** Open `outputs/extracted_json/test1_text_boxes_pii.json` in VS Code.
- **Visible Content:** The JSON lines showing `file`, `slide`, `block_id`, `block_type`, `text` with executive PII, `position`, `order`, `context_group_id`, and `paragraphs`.

---

### Screenshot 04: Table Extraction & 2D Grid Cells
- **Target File:** `04_table_extraction.png`
- **What to Display:** Open `outputs/extracted_json/test2_tables_pii.json` in VS Code.
- **Visible Content:** The JSON blocks showing `block_type: "table"`, `table_metadata`, and individual `table_cell` blocks with `row`, `column`, `is_header`, and coordinates.

---

### Screenshot 05: Recursive Grouped Shape Extraction
- **Target File:** `05_grouped_shape_extraction.png`
- **What to Display:** Open `outputs/extracted_json/test3_grouped_shapes_pii.json` in VS Code.
- **Visible Content:** The JSON blocks showing `parent_group_id`, `group_depth: 1` and `group_depth: 2`, and child shapes inside the group.

---

### Screenshot 06: Speaker Notes Extraction
- **Target File:** `06_speaker_notes_extraction.png`
- **What to Display:** Open `outputs/extracted_json/test6_speaker_notes_pii.json` in VS Code.
- **Visible Content:** The JSON blocks showing `block_type: "speaker_notes"`, `source_type: "speaker_notes"`, and the speaker notes text with slide provenance.

---

### Screenshot 07: Image OCR Adapter & Fallback Status
- **Target File:** `07_image_ocr.png`
- **What to Display:** Open `outputs/extracted_json/test4_image_ocr_pii.json` in VS Code.
- **Visible Content:** The `metadata.ocr_status` object showing transparent Tesseract status, adapter type, and Windows installation instructions.

---

### Screenshot 08: Structure Retention Metric Breakdown
- **Target File:** `08_structure_metric.png`
- **What to Display:** Open `outputs/structure_metrics/Cadence_Financial_Group_Organizational_Pack.json` in VS Code.
- **Visible Content:** The `component_scores` object showing the 10 structural dimensions, counts, weights, and overall score.

---

### Screenshot 09: Structure Results CSV Table
- **Target File:** `09_csv_results.png`
- **What to Display:** Open `outputs/csv/structure_results.csv` in Excel or VS Code's CSV extension.
- **Visible Content:** The full table showing all 8 files, slide counts, block counts, table counts, cell counts, 100.0% scores, and PASS status.

---

### Screenshot 10: Technical HTML Report
- **Target File:** `10_final_report.png`
- **What to Display:** Open `outputs/reports/member3_report.html` in your web browser (Chrome / Edge / Brave).
- **Visible Content:** The dashboard header, statistics cards (100.0% Retention, 27/27 Tests Passed), and results table.

---

### Screenshot 11: Pytest Automated Test Execution
- **Target File:** `11_final_test_results.png`
- **What to Display:** PowerShell terminal after executing:
  ```powershell
  python -m pytest -v
  ```
- **Visible Content:** The full green output showing `27 passed in 1.71s`.
