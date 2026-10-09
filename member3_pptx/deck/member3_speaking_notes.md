# Member 3 Presentation Speaking Notes

**Slide Title:** 04 Reliable Outcomes — Structure Retention & Coverage  
**Project:** Cadence Financial Group — Case Study 2: Text Analysis & PII Detection  
**Role:** Member 3 (PowerPoint PPTX Extraction & Structure-Retention Evaluation)  
**Estimated Delivery Time:** 2.5 – 3.0 minutes  

---

### [0:00 – 0:25] 1. Responsibilities & Role Scope
> *"Good morning everyone. As **Member 3** of the Cadence Text Analysis and PII Detection team, I own the **PowerPoint (PPTX) extraction engine**, the **test data suite for presentations**, and the objective **structure-retention evaluation metric** against our team target of at least 80%.
>
> While Member 1 focused on Word documents and Member 2 tackled PDFs, my responsibility was ensuring that complex, multi-layered PowerPoint presentations—including Cadence's official Organizational Reference Pack—could be ingested without losing visual hierarchy, table layouts, or spatial context."*

---

### [0:25 – 0:55] 2. Why PPTX Extraction is Difficult & The `python-pptx` Approach
> *"Unlike linear text files, PowerPoint slides are essentially 2D geometric canvases. Shapes are stored as independent coordinate blocks, and PowerPoint's internal XML shape index does not reflect visual human reading order.
>
> Furthermore, corporate presentations heavily employ complex constructs: multi-tiered organizational chart groups, multi-cell RACI accountability matrices, embedded risk charts, and confidential speaker notes. If you naively call `shape.text` across a slide, you destroy all table grids, flatten nested groups into an unordered word soup, and miss speaker notes entirely.
>
> To solve this, I built a modular extraction subsystem leveraging `python-pptx` with specialized handlers for each shape family."*

---

### [0:55 – 1:30] 3. Handling Grouped Shapes, Tables, Charts, & Speaker Notes
> *"Let's look at how the engine processes these structures:
>
> - **Grouped Shapes:** We implemented a recursive traversal engine. When a group shape is encountered, the algorithm recurses down to its child shapes—even through nested groups—recording the parent group ID, nesting depth, and relative coordinates so hierarchical relationships are preserved.
> - **Tables:** Tables are extracted both as a consolidated composite block and as individual cell records. For every single cell, we preserve the row index, column index, header status, and calculated 2D bounding box.
> - **Charts:** Using `python-pptx` chart elements, we extract chart titles, series names, categories, and axis labels. If low-level XML is restricted, we gracefully fall back without crashing.
> - **Speaker Notes:** Dedicated logic extracts slide presenter notes, assigning them a dedicated `speaker_notes` block type so confidential remarks are preserved with slide-level traceability without contaminating the visual slide body."*

---

### [1:30 – 1:55] 4. Image OCR & Pluggable Adapter Pattern
> *"Many executive slides embed images containing text, such as scanned security badges or contractor passes.
>
> I built a pluggable OCR adapter interface. If local Tesseract OCR is available, it extracts text and computes confidence. If the binary is missing, our system doesn't crash—it transparently flags `tesseract_binary_not_found` and prints clear Windows setup instructions. Crucially, I also engineered an adapter hook ready to reuse Member 2's shared OCR module as soon as it is deployed, avoiding duplicate architecture."*

---

### [1:55 – 2:20] 5. Deterministic Reading Order & Context Preservation
> *"Downstream PII detection critically relies on conversational context. If an executive's name, job title, corporate email, and phone number are split into isolated records, NER models struggle.
>
> I implemented two key algorithms:
> 1. **Deterministic 2D Reading Order:** A spatial banding algorithm with a 24-point vertical tolerance band and header priority that reconstructs true top-to-bottom, left-to-right reading order.
> 2. **Context Grouping:** A spatial proximity clustering algorithm that groups nearby shapes into a unified `context_group_id` (for example, `slide_3_group_02`), binding names directly to adjacent contact info."*

---

### [2:20 – 2:45] 6. Structure-Retention Metric & Measured Results
> *"Now turning to our **04 Reliable Outcomes** slide:
>
> Rather than a crude character-count ratio, I engineered a transparent 10-dimensional structure metric evaluating slide preservation, title detection, text boxes, paragraphs, tables, table cells, chart text, notes, reading-order monotonicity via Kendall's tau, and image coverage.
>
> - **Target:** Our team target was **>= 80.0%**.
> - **Result:** We evaluated 8 presentation decks—including Cadence's official 9-slide Organizational Reference Pack and 7 synthetic stress-test decks. Across all 8 files, our measured structure retention achieved **100.0%**, achieving a unanimous **PASS**.
> - Across these decks, we extracted 26 slides, 181 text blocks, 6 tables containing 272 individual cells, 3 charts, 3 speaker notes blocks, and 12 images."*

---

### [2:45 – 3:05] 7. Downstream Hand-off & Remaining Limitations
> *"To maintain strict team integrity:
> - **PII Coverage and Precision** are clearly marked as **'PENDING MEMBER 4'**. Member 4 owns the PII taxonomy and classification engine, and our extracted JSON files are fully formatted to feed directly into their evaluation scripts.
> - In terms of limitations: non-standard 3D chart formats fall back to text frame summaries, and image OCR requires local Tesseract installation for full visual text recognition.
>
> In conclusion, Member 3 delivers a robust, 100% locally compliant extraction pipeline that guarantees structural fidelity for the entire Cadence PII detection workflow. Thank you, and I'll now pass over to Member 4."*
