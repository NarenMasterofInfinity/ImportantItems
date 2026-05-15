Build a robust complex PDF parser in Python.

Problem:
Some PDFs are extremely complex:
- nested tables
- tables inside cells
- multi-row headers
- merged cells
- highlighted/selected cells
- checkboxes/radio-like marks
- colored regions
- multi-column layouts
- scanned pages
- mixed OCR/native text
- irregular reading order

The parser must not rely only on raw text extraction. It must combine:
- native PDF extraction
- visual/layout evidence
- OCR fallback
- table structure detection
- recursive nested parsing
- optional GenAI reconciliation

Available tools ONLY:
- PyMuPDF (fitz)
- pdfplumber
- Camelot
- rapidocr-onnxruntime
- standard Python libs
- optional: numpy, pandas, Pillow, OpenCV

GenAI access:
POST http://localhost:5052/api/generate

Request:
{
  "model": "MODEL_NAME",
  "prompt": "PROMPT"
}

Response:
{
  "output": "TEXT"
}

Goal:
Create a best-effort parser that outputs structured JSON + Markdown for highly complex PDFs.

Deliverables:
- Python package: complex_pdf_parser
- CLI:
  python -m complex_pdf_parser input.pdf --out out_dir
- Outputs:
  - document.json
  - document.md
  - per-page JSON
  - debug overlay images
- README + requirements.txt

Architecture:

PDF
→ PyMuPDF extraction
→ pdfplumber extraction
→ Camelot table detection
→ render page image
→ OCR fallback using RapidOCR
→ visual/layout analysis
→ recursive table/cell reconstruction
→ optional GenAI reconciliation
→ structured export

Core principle:
Use deterministic extraction first.
Use GenAI only to reconcile structure, not invent content.

Implement modules:

1. models.py
Create dataclasses for:
- DocumentResult
- PageResult
- BBox
- Element
- Table
- Cell
- Style

Every element must contain:
- bbox
- text
- confidence
- source
- style
- children
- metadata

2. extract_native.py
Using PyMuPDF:
- extract blocks
- words
- drawings
- annotations
- images
- font/style info
- render pages at configurable DPI

3. extract_pdfplumber.py
Using pdfplumber:
- extract words
- tables
- lines/rectangles
- normalize coordinates

4. extract_camelot.py
Using Camelot:
- try lattice first
- fallback to stream
- capture confidence/parsing report
- convert to Table/Cell objects

5. ocr.py
Using RapidOCR:
- run OCR only when needed
- scanned pages
- image-heavy regions
- empty table cells
- deduplicate OCR/native text using bbox overlap

6. visual.py
Using PIL/numpy/OpenCV:
Detect:
- dominant colors
- highlighted cells
- selected cells
- checkbox/radio marks
- borders/fills
- line structures
- rectangular regions

Selection/highlight detection must be generic, not hardcoded to blue.

Return:
{
  "is_selected": bool,
  "is_highlighted": bool,
  "confidence": float,
  "reason": str
}

7. tables.py
Build recursive table reconstruction:
- merge Camelot/pdfplumber/visual candidates
- assign words to cells
- detect merged cells
- detect multi-row headers
- detect nested tables recursively
- preserve exact text/numbers
- add warnings for uncertain structure

8. structure.py
Reconstruct document flow:
- reading order
- heading detection
- paragraph merging
- multi-column support
- repeated header/footer removal
- preserve tables inline

9. genai.py
Optional reconciliation layer.

Functions:
- call_genai()
- reconcile_page_structure()
- reconcile_table_structure()

Rules:
- never send full PDF
- send compact JSON only
- one page/table at a time
- GenAI cannot invent content
- validate output against source evidence
- fallback to deterministic result if invalid

Use GenAI for:
- reading order correction
- heading classification
- table reconciliation
- nested table cleanup
- selected/highlighted interpretation

Do NOT use GenAI for:
- OCR
- hallucinating missing values
- replacing deterministic extraction

10. export.py
Export:
- full JSON
- Markdown
- nested tables preserved
- selected cells marked clearly
- warnings included

11. debug.py
Generate overlay debug images showing:
- blocks
- words
- tables
- cells
- OCR regions
- selected/highlighted areas

12. cli.py
Options:
- --out
- --dpi
- --pages
- --ocr auto|always|never
- --genai true|false
- --genai-model MODEL
- --debug

Quality rules:
- never crash entire pipeline
- continue page-by-page
- preserve exact numbers/text
- keep source evidence
- avoid hallucination
- confidence scoring required
- uncertain structures must be flagged

Important:
This is NOT a simple text extractor.
This is a visual + structural PDF understanding pipeline built using only the allowed tools.