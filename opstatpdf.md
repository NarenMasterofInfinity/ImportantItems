IMPLEMENTATION TASK
===================

Build an end-to-end, production-oriented prototype for extracting financial
statement line items and their associated column/header values from arbitrary
PDF financial statements.

The system must support:

- Income Statements / Profit & Loss statements
- Balance Sheets
- Cash Flow Statements
- Other similar financial schedules/tables
- Digital PDFs
- Scanned/image PDFs
- Dense financial pages
- Multi-page tables
- Headers appearing only on the first page
- Repeated headers
- Multi-row / hierarchical headers
- Tables whose formatting/layout changes between documents

The PRIMARY output is:

    valid financial line item
        +
    values associated with the correct headers
        +
    provenance
        +
    confidence/evidence

Rows such as section headings, subtotals, grand totals, repeated headers,
decorative rows, footers, etc. must NOT be returned as ordinary line items.

This is not a generic OCR project.

RapidOCR/PDFPlumber are primarily used to understand document geometry and
construct safe, information-aware image chunks.

The multimodal LLM performs the actual semantic extraction.


======================================================================
1. IMPORTANT EXISTING PROJECT CONSTRAINTS
======================================================================

Before implementing anything:

1. Inspect the existing repository.
2. Understand the existing project structure.
3. Do NOT unnecessarily replace existing infrastructure.
4. There should already be a folder/package named approximately:

       tachyon/

   Inspect the repository to determine the exact casing/path.

5. Inside it there should be something similar to:

       llm_client.py

   USE THIS EXISTING CLIENT.

6. Do not build a new Gemini SDK integration unless absolutely necessary.

7. Inspect llm_client.py and determine:
   - how models are selected
   - how multimodal/image requests are made
   - how structured responses are requested
   - how authentication is handled
   - what configuration it expects

8. A .env already exists in the project.

   Use the existing environment variables and existing configuration.
   DO NOT invent new credentials/API keys if the necessary configuration
   already exists.

9. Target model:

       Gemini 3.8 Flash

   Use the model identifier/configuration supported by the existing
   llm_client.py. Keep the actual model ID configurable in one location.

10. Wrap calls made through llm_client.py with Tenacity.

Use exponential backoff with jitter and sensible retry limits.

Do NOT retry deterministic programming errors or schema validation errors
indefinitely.

Log every retry.


======================================================================
2. CORE ARCHITECTURAL PRINCIPLE
======================================================================

The architecture must follow:

          EXTRACT GEOMETRY LOCALLY
                    +
           UNDERSTAND SEMANTICS
              WITH THE VLM

Do NOT ask RapidOCR to be the final financial extractor.

Do NOT treat RapidOCR confidence as final extraction confidence.

Do NOT blindly divide a page into thirds/halves/fixed-height crops.

Do NOT independently interpret every image chunk without document/table
context.

Instead:

PDF
 |
 +--> determine digital vs scanned
 |
 +--> geometry extraction
 |       |
 |       +-- digital --> PDFPlumber
 |       |
 |       +-- scanned --> RapidOCR
 |
 +--> normalize words + bounding boxes
 |
 +--> reconstruct visual lines / candidate rows
 |
 +--> detect safe whitespace boundaries
 |
 +--> identify/extract header context
 |
 +--> information-aware dynamic chunking
 |
 +--> crop ORIGINAL rendered page
 |
 +--> Gemini multimodal extraction
 |
 +--> structured JSON validation
 |
 +--> provenance/evidence
 |
 +--> confidence/verifier
 |
 +--> merge overlapping chunk results
 |
 +--> final normalized line-item output


======================================================================
3. DIGITAL VS SCANNED DOCUMENTS
======================================================================

Implement document/page classification.

For DIGITAL pages:
    use PDFPlumber.

Extract:
    - text
    - word bounding boxes
    - page dimensions
    - font information when available/useful
    - line positions
    - character/word geometry

For SCANNED pages:
    use RapidOCR.

RapidOCR is primarily a GEOMETRIC GUIDE.

Obtain:
    - detected text
    - bounding polygons/boxes
    - line/word geometry

Its extracted text may assist grouping, but MUST NOT automatically become
the authoritative final financial value.

The final semantic extraction should come from Gemini looking at the
original high-quality page crop.

Support mixed PDFs where:
    page 1 = digital
    page 2 = scanned
    page 3 = digital

Classification should therefore be possible at page level.


======================================================================
4. NORMALIZED GEOMETRY REPRESENTATION
======================================================================

Both PDFPlumber and RapidOCR must feed the SAME internal representation.

For example:

WordBox:
{
    "page": 3,
    "text": "Revenue",
    "x0": ...,
    "y0": ...,
    "x1": ...,
    "y1": ...,
    "source": "pdfplumber" | "rapidocr"
}

Normalize coordinates so downstream code does not care which extractor
produced them.

Create deterministic coordinate conversion helpers between:

- PDF coordinates
- rendered-image pixel coordinates
- normalized [0,1] coordinates if useful

This is extremely important for provenance.


======================================================================
5. ROW / VISUAL-LINE RECONSTRUCTION
======================================================================

Before chunking, reconstruct candidate visual rows.

DO NOT crop through arbitrary Y coordinates.

Use word bounding boxes to construct visual lines/candidate rows.

Use signals such as:

- vertical overlap
- Y-center distance
- character/word height
- baseline similarity
- horizontal spacing
- indentation
- large whitespace gaps
- column alignment

A candidate row should approximately represent something visually coherent,
for example:

    Selling and administrative expenses       1,204      1,087

Store:

{
    "row_id": "...",
    "page": 4,
    "bbox": [...],
    "words": [...],
    "approx_text": "...",
    "word_count": ...,
    "estimated_density": ...,
    "indentation": ...,
    "gap_before": ...,
    "gap_after": ...
}

RapidOCR text does NOT need to be perfect for this.

Its purpose is to answer:

    "Where does visual content exist?"

and:

    "Where is it safe to cut?"


======================================================================
6. THE MOST IMPORTANT COMPONENT: INFORMATION-AWARE CHUNKING
======================================================================

Create this as a SEPARATE package/folder.

For example:

    chunking/
        __init__.py
        models.py
        row_builder.py
        density.py
        boundaries.py
        chunk_planner.py
        overlap.py
        renderer.py
        diagnostics.py

Adapt naming to the repository conventions.

DO NOT use:

    page / 3

or:

    every 800 pixels

or:

    fixed number of image pixels

as the primary strategy.


----------------------------------------------------------------------
6.1 Dynamic density
----------------------------------------------------------------------

We do NOT know beforehand whether a page contains:

    5 rows

or:

    20 rows

or:

    80 tiny rows.

Therefore calculate density AFTER the lightweight geometry pass.

Useful signals:

    number of candidate rows
    number of detected words
    words per row
    median text height
    vertical whitespace
    number of occupied horizontal bands
    estimated number of columns
    page occupancy ratio
    candidate row complexity

Create a simple interpretable density metric.

Do NOT train/download another ML model for this.


----------------------------------------------------------------------
6.2 Row-aware packing
----------------------------------------------------------------------

Build chunks by PACKING COMPLETE CANDIDATE ROWS.

Conceptually:

    chunk = []

    while next row can safely be included:
        add row

    stop at a safe row boundary

The chunk size should therefore adapt naturally.

Sparse page:
    potentially one chunk.

Dense page:
    potentially 3, 4, 5+ chunks.

Do not attempt to predict the number of chunks before inspecting geometry.


----------------------------------------------------------------------
6.3 Never cut words
----------------------------------------------------------------------

A crop boundary MUST NOT pass through a detected word bounding box.

Prefer boundaries inside whitespace gaps between candidate rows.

For a proposed boundary Y:

    find all boxes intersecting boundary

If ANY content intersects it:

    move boundary to nearest safe whitespace region.

Use a safety margin.

For example:

       ROW N
    ---------------

        whitespace       <-- ideal crop boundary

    ---------------
       ROW N+1


----------------------------------------------------------------------
6.4 Conservative margins
----------------------------------------------------------------------

OCR can miss characters.

Therefore do not crop exactly at:

    last_bbox.y1

Instead use configurable vertical padding.

The renderer should produce:

    crop_top
    crop_bottom
    safe_top
    safe_bottom

Maintain enough surrounding whitespace that a slightly inaccurate OCR box
does not cause clipping.


----------------------------------------------------------------------
6.5 Overlap
----------------------------------------------------------------------

Adjacent chunks should overlap slightly.

Prefer ROW overlap rather than arbitrary pixel overlap.

For example:

    Chunk 1: rows 1-25
    Chunk 2: rows 22-47
    Chunk 3: rows 44-68

Make overlap configurable.

Start with approximately 2-4 candidate rows.

The purpose is:

- boundary context
- prevent line-item loss
- enable agreement checks
- help resolve section transitions

Deduplicate overlapping results downstream.


----------------------------------------------------------------------
6.6 Do not rely solely on row count
----------------------------------------------------------------------

"30 rows per chunk" is NOT a hard rule.

A row can contain:

    3 words

or:

    80 words.

Use an information budget based on a combination of:

    rows
    words
    crop height
    visual density
    estimated columns

Provide configurable soft limits.

The chunk planner should explain WHY it stopped.

Example:

{
    "stop_reason": "information_budget",
    "rows": 27,
    "words": 384,
    "crop_height_ratio": 0.31
}


======================================================================
7. ORIGINAL IMAGE MUST BE SENT TO GEMINI
======================================================================

Geometry determines WHERE to crop.

Gemini must receive the crop from the ORIGINAL rendered PDF page.

DO NOT normally send an OCR-reconstructed image.

DO NOT normally draw bounding boxes over the production image.

Gemini should see the original visual evidence:

- font weight
- indentation
- separators
- parentheses
- underlines
- whitespace
- column relationships
- visual hierarchy

Bounding-box overlays should be generated separately for debugging.


======================================================================
8. HEADER HANDLING
======================================================================

Header extraction is separate from ordinary line-item extraction.

The user specifically wants the context passed downstream to remain SMALL.

Therefore DO NOT construct a giant semantic document schema and inject it
into every request.

Instead maintain a compact:

    HEADER CONTEXT

Example:

{
    "columns": [
        "Particulars",
        "FY 2025",
        "FY 2024"
    ]
}

Support hierarchical headers:

{
    "columns": [
        {
            "column": 0,
            "header_path": ["Particulars"]
        },
        {
            "column": 1,
            "header_path": ["Year ended December 31", "2025"]
        },
        {
            "column": 2,
            "header_path": ["Year ended December 31", "2024"]
        }
    ]
}

Keep this compact.


======================================================================
9. HEADER DETECTION AND PROPAGATION
======================================================================

Headers may:

- occur on every page
- occur only on page 1
- be repeated later
- span multiple rows
- change midway
- contain grouped columns

Maintain table/header state.

Example:

DocumentState
    active_statement_type
    active_header
    header_source_page
    active_table_id
    current_page

If page 1 establishes:

    Particulars | FY25 | FY24

and pages 2-4 contain continuation rows without headers:

    propagate the header.

Do NOT ask pages 2-4 to rediscover it unnecessarily.

However, every page/region must be checked cheaply for evidence of:

    new header
    repeated header
    changed header
    new table

A repeated header should not become a line item.

If a genuine new header appears:

    update active_header.


======================================================================
10. DOCUMENT TYPE
======================================================================

Support at least:

    income_statement
    balance_sheet
    cash_flow_statement
    generic_financial_table

Use a COMMON extraction prompt plus a SMALL document-specific rules
section.

DO NOT maintain completely independent giant prompts.

Example:

    COMMON CORE
       +
    INCOME STATEMENT RULES

or:

    COMMON CORE
       +
    BALANCE SHEET RULES

etc.

Document type can either be supplied by the caller or inferred through an
initial lightweight classification stage.


======================================================================
11. GEMINI EXTRACTION REQUEST
======================================================================

Each extraction request should approximately contain:

SYSTEM / TASK CONTEXT

    You are extracting atomic financial statement line items from a
    cropped region of a financial statement.

DOCUMENT TYPE

    Income Statement

HEADER CONTEXT

    Column 0: Particulars
    Column 1: FY2025
    Column 2: FY2024

CHUNK CONTEXT

    page = 3
    chunk = 2/4

IMAGE

    <original page crop>


======================================================================
12. EXTRACTION RULES
======================================================================

The prompt must make a clear distinction between:

VALID LINE ITEM

Examples:

    Revenue
    Cost of goods sold
    Employee benefits expense
    Accounts receivable
    Property, plant and equipment
    Cash and cash equivalents

NON-LINE-ITEM structural rows:

    section headings
    column headers
    repeated headers
    page headers
    page footers
    notes labels when they are merely references
    blank rows
    decorative rows

TOTAL-LIKE rows must be classified explicitly.

Examples:

    Total assets
    Total current liabilities
    Gross profit
    Operating income
    Net income

Do NOT simply delete them during extraction.

This is important.

Have the model classify them first:

    LINE_ITEM
    SUBTOTAL
    TOTAL
    SECTION_HEADER
    HEADER
    OTHER

Then the final business output can exclude SUBTOTAL/TOTAL according to
configuration.

Keeping the classification allows debugging and prevents information loss.


======================================================================
13. STRUCTURED RESPONSE
======================================================================

Require JSON/structured output.

Do not parse arbitrary prose.

Design a Pydantic model similar to:

ChunkExtractionResult
{
    "document_type": "...",
    "page": 3,
    "chunk_id": "...",

    "rows": [
        {
            "label": "Revenue",
            "row_type": "LINE_ITEM",

            "values": [
                {
                    "header": "FY2025",
                    "raw_value": "1,250",
                    "normalized_value": 1250
                },
                {
                    "header": "FY2024",
                    "raw_value": "1,100",
                    "normalized_value": 1100
                }
            ],

            "provenance": {
                ...
            },

            "confidence": {
                ...
            }
        }
    ]
}

Keep BOTH:

    raw_value
    normalized_value

Never silently destroy the source representation.

Examples:

    "(1,250)" -> raw "(1,250)", normalized -1250

    "1.2m" -> preserve raw value even if normalization is performed.


======================================================================
14. PROVENANCE
======================================================================

Financial extraction requires traceability.

Every extracted line item must eventually map back to:

    source PDF
    page
    chunk
    image crop
    evidence location

At minimum:

{
    "document_id": "...",
    "page": 4,
    "chunk_id": "p4_c2",
    "chunk_bbox": [x0, y0, x1, y1]
}

Where feasible, ask Gemini to return the approximate evidence bbox for:

    label
    each extracted value

Prefer normalized coordinates if the existing multimodal client supports
reliable localization.

Store coordinate space explicitly:

{
    "bbox": [...],
    "coordinate_space": "chunk_normalized"
}

Then provide deterministic transformations:

    chunk bbox
        ->
    page image bbox
        ->
    PDF/page coordinates

This enables UI highlighting later.


======================================================================
15. CONFIDENCE
======================================================================

DO NOT use RapidOCR confidence as extraction confidence.

RapidOCR is only helping us locate content.

Also DO NOT blindly accept:

    "confidence": 0.97

simply because the LLM generated that number.

The LLM SHOULD have a strong role in confidence, but confidence must be
evidence-oriented.

Ask Gemini for:

    confidence_label:
        HIGH
        MEDIUM
        LOW

and:

    uncertainty_reasons

For example:

{
    "confidence_label": "MEDIUM",
    "uncertainty_reasons": [
        "value alignment is visually ambiguous"
    ]
}

Then augment this with system-level evidence:

    VLM self-assessment
    overlap agreement
    successful provenance localization
    header/value consistency
    duplicate extraction agreement
    optional verification pass

Do NOT include RapidOCR OCR-confidence.

Create something like:

ExtractionConfidence
{
    "model_confidence": "HIGH",
    "overlap_agreement": true,
    "provenance_available": true,
    "verification_status": "PASS",
    "final_status": "AUTO_ACCEPT"
}

Final statuses can be:

    AUTO_ACCEPT
    REVIEW
    REPROCESS


======================================================================
16. OPTIONAL VERIFICATION PASS
======================================================================

Implement a configurable verification stage.

For uncertain/high-value/ambiguous extraction, make another Gemini call
with:

    original crop
    extracted candidate
    header context

Ask:

    Does the image support this exact extraction?

Return structured output:

{
    "supported": true,
    "corrected_label": null,
    "corrected_values": null,
    "reason": "..."
}

Do NOT run this expensive stage unnecessarily.

Make verification policy configurable.


======================================================================
17. OVERLAP RECONCILIATION
======================================================================

Because chunks overlap, rows may be extracted twice.

Create a reconciliation layer.

Match candidates using:

    page
    spatial overlap
    normalized label
    value similarity

Cases:

A)
Both chunks agree.

    Increase evidence strength.

B)
Only one detects the row.

    Keep it but potentially reduce confidence.

C)
Both detect row but values differ.

    Mark REVIEW or run verifier.

D)
Row appears as LINE_ITEM in one chunk and TOTAL in another.

    Mark classification conflict and verify.

Do NOT simply keep the first response.


======================================================================
18. TENACITY / LLM RESILIENCE
======================================================================

Wrap the existing Tachyon LLM invocation.

Use Tenacity with approximately:

    stop_after_attempt(...)
    wait_exponential_jitter(...)

Make values configurable.

Retry:

    transient timeout
    temporary upstream failure
    rate limit where appropriate
    connection errors

Log:

    attempt
    model
    chunk_id
    elapsed time
    exception class
    next retry

For malformed JSON:

First attempt deterministic extraction/schema validation.

If structured-output support exists in llm_client.py, use it.

If the model still returns invalid output, optionally perform ONE bounded
repair/retry.

Never create infinite repair loops.


======================================================================
19. LOGGING — CRITICAL REQUIREMENT
======================================================================

Logging is a FIRST-CLASS feature.

Use Python logging with structured records.

Every processing run needs:

    run_id
    document_id

Every page:

    page_id

Every chunk:

    chunk_id

Every LLM request:

    request_id

Example:

run_id
document_id
page
chunk_id
stage
event
timestamp
duration_ms
status
metadata

Stages should include:

    DOCUMENT_LOAD
    PAGE_CLASSIFICATION
    PDFPLUMBER_EXTRACTION
    RAPIDOCR_EXTRACTION
    ROW_RECONSTRUCTION
    HEADER_EXTRACTION
    CHUNK_PLANNING
    IMAGE_RENDER
    LLM_REQUEST
    LLM_RESPONSE
    JSON_VALIDATION
    RECONCILIATION
    VERIFICATION
    FINALIZATION


======================================================================
20. DO NOT PUT RAW IMAGE BYTES DIRECTLY INTO TEXT LOGS
======================================================================

The user needs to inspect the exact image sent to Gemini.

Implement this safely.

DO NOT dump megabytes of base64/binary into ordinary .log files.

Instead:

    artifacts/
       <run_id>/
          page_001/
              original.png
              geometry_overlay.png
              chunk_001.png
              chunk_002.png

The structured log should contain:

{
    "event": "LLM_REQUEST",
    "chunk_id": "p1_c2",
    "image_artifact": ".../chunk_002.png"
}

If the existing LLM client requires base64 internally, preserve/request
metadata as needed, but use artifact references for UI/logging.

The Streamlit UI can then load the actual binary image from the artifact
path.

This achieves the requirement:

    "show me exactly what image was sent to the LLM"

without destroying logging performance.


======================================================================
21. CAPTURE LLM REQUEST/RESPONSE
======================================================================

For every LLM call persist:

    request_id
    timestamp
    model
    document type
    header context
    prompt version
    system prompt
    user prompt/text portion
    image artifact path
    retry attempts
    latency
    raw response
    parsed response
    validation errors
    token usage if exposed by llm_client
    status

DO NOT log secrets, auth headers or API credentials.


======================================================================
22. STREAMLIT UI
======================================================================

Build an intuitive debugging/inspection application.

This is NOT merely:

    Upload PDF
    Show JSON.

It should function as an extraction observability console.


======================================================================
23. STREAMLIT — MAIN LAYOUT
======================================================================

Suggested layout:

SIDEBAR

    Upload PDF

    Model
        Gemini 3.8 Flash

    Document type
        Auto
        Income Statement
        Balance Sheet
        Cash Flow
        Generic

    Configuration
        chunk information budget
        row overlap
        crop padding
        verification enabled
        confidence threshold

    Run Extraction


MAIN AREA

Use tabs such as:

    Overview
    Pages
    Chunking
    Extraction
    Provenance
    Logs
    Raw LLM


======================================================================
24. OVERVIEW TAB
======================================================================

Display:

    document name
    page count
    digital/scanned/mixed
    detected statement type
    number of candidate rows
    number of chunks
    number of extracted rows
    accepted
    review
    rejected
    total runtime
    LLM calls
    retries
    verification calls


======================================================================
25. PAGES TAB
======================================================================

Allow page navigation.

For each page show side-by-side:

LEFT:
    original rendered page

RIGHT:
    geometry/debug overlay

Overlay should optionally show:

    detected words
    candidate rows
    header area
    chunk boundaries
    chunk IDs

Use checkboxes/toggles so overlays can be enabled/disabled.


======================================================================
26. CHUNKING TAB — VERY IMPORTANT
======================================================================

The user needs to understand EXACTLY how chunking happened.

Display something like:

Page 3

    Chunk p3_c1
        rows: 1-24
        words: 311
        crop bbox: ...
        density: ...
        overlap: rows 22-24
        stop reason: information budget

        [IMAGE ACTUALLY SENT TO GEMINI]

    Chunk p3_c2
        rows: 22-48
        ...

Also provide a page visualization with horizontal chunk boundaries.

Make it easy to identify:

    Did we cut through text?
    Was a row omitted?
    Was the chunk too dense?
    Was overlap correct?
    Did header propagation work?


======================================================================
27. EXTRACTION TAB
======================================================================

Show a table:

| Page | Chunk | Line Item | Type | FY25 | FY24 | Confidence | Status |

Clicking/selecting a row should reveal:

    source image
    header context
    model output
    provenance
    confidence evidence
    verification result


======================================================================
28. PROVENANCE TAB
======================================================================

Selecting an extracted item should show:

    original page

with the corresponding evidence highlighted if localization is available.

Also show:

    page
    chunk
    bbox
    raw source text/value
    normalized value
    source image


======================================================================
29. RAW LLM TAB
======================================================================

For debugging, allow selecting:

    request_id

Show:

    prompt
    header context
    image
    raw response
    parsed JSON
    validation result
    retry history
    latency

This will be essential for determining whether an error came from:

    chunking
    header propagation
    prompt
    model
    parser
    reconciliation


======================================================================
30. LIVE LOG STREAMING
======================================================================

The extraction must NOT freeze the Streamlit UI.

Implement processing asynchronously relative to rendering.

A reasonable architecture is:

    worker thread
        |
        +--> extraction pipeline
        |
        +--> thread-safe Queue
                       |
                       v
                  Streamlit UI

Use:

    queue.Queue

or an equivalent thread-safe event mechanism.

The pipeline publishes structured events.

Example:

{
    "timestamp": "...",
    "level": "INFO",
    "stage": "CHUNK_PLANNING",
    "page": 3,
    "message": "Created 4 chunks from 71 candidate rows"
}

The UI consumes and displays them.

DO NOT make multiple background threads directly mutate Streamlit widgets.

The worker should update thread-safe state/event queues.

The Streamlit execution thread renders UI state.

Logs should continue updating smoothly while extraction proceeds.

Provide filters:

    ALL
    INFO
    WARNING
    ERROR

and optionally by:

    page
    chunk
    stage


======================================================================
31. PROMPT MANAGEMENT
======================================================================

Do NOT hard-code giant prompts inside pipeline.py.

Create a proper prompt package, for example:

    prompts/
        common.py
        header.py
        extraction.py
        verification.py
        document_rules.py

Version prompts.

Every LLM log should record:

    prompt_name
    prompt_version

This allows us to compare prompt changes experimentally.


======================================================================
32. COMMON EXTRACTION PROMPT BEHAVIOR
======================================================================

The prompt should explicitly tell Gemini:

1. Use the IMAGE as the source of truth.

2. Header context is supplied separately.

3. Extract only rows visible in the provided image.

4. Do not hallucinate missing rows.

5. Do not infer a value that is not visually supported.

6. Preserve source values.

7. Associate values with the supplied header hierarchy.

8. Classify every relevant detected row into:

       LINE_ITEM
       SUBTOTAL
       TOTAL
       SECTION_HEADER
       HEADER
       OTHER

9. Do not treat indentation alone as definitive.

10. Use:
       wording
       layout
       indentation
       surrounding rows
       separators
       accounting conventions
       document-type context

11. If uncertain:
       retain uncertainty
       do not invent certainty.

12. Return structured JSON only.


======================================================================
33. DOCUMENT-SPECIFIC RULES
======================================================================

Keep these SMALL.

Income statement rules may mention patterns such as:

    revenue
    expenses
    gross profit
    operating profit
    tax
    net income

Balance sheet rules:

    assets
    liabilities
    equity
    current/non-current sections

Cash flow rules:

    operating
    investing
    financing
    cash reconciliation

These are semantic hints, NOT rigid keyword rules.

Never classify something solely because it contains "total" or because it
is bold.


======================================================================
34. OUTPUT
======================================================================

Produce both:

A. Complete audit/debug output.

B. Clean business output.

Example clean output:

{
    "document_id": "...",
    "document_type": "income_statement",

    "headers": [
        "FY2025",
        "FY2024"
    ],

    "line_items": [
        {
            "line_item": "Revenue",
            "values": {
                "FY2025": 1250,
                "FY2024": 1100
            },
            "raw_values": {
                "FY2025": "1,250",
                "FY2024": "1,100"
            },
            "page": 1,
            "confidence": "HIGH",
            "status": "AUTO_ACCEPT",
            "provenance": {...}
        }
    ]
}

The business output should exclude:

    SECTION_HEADER
    HEADER
    OTHER

and by default exclude:

    SUBTOTAL
    TOTAL

BUT retain all of them in audit/debug output.


======================================================================
35. INTERMEDIATE ARTIFACTS
======================================================================

Persist enough information to reproduce a failure.

Recommended:

runs/
  <run_id>/
      run.json

      pages/
          page_001/
              page.png
              geometry.json
              geometry_overlay.png
              rows.json
              chunks.json

              chunks/
                  p1_c1.png
                  p1_c1_request.json
                  p1_c1_response_raw.txt
                  p1_c1_response.json

      headers.json
      reconciled.json
      final.json
      events.jsonl

Do not unnecessarily duplicate huge image data.


======================================================================
36. FAILURE HANDLING
======================================================================

Failure of one chunk should NOT necessarily kill the entire document.

Track chunk status:

    PENDING
    RUNNING
    SUCCESS
    RETRYING
    FAILED
    REVIEW

At the end, clearly report partial failures.

UI should allow us to identify and potentially rerun an individual failed
chunk.


======================================================================
37. TESTING
======================================================================

Create meaningful tests.

At minimum test:

1. Digital page geometry extraction.

2. Scanned page geometry extraction.

3. Dense page -> multiple chunks.

4. Sparse page -> one chunk.

5. No crop boundary intersects known word bbox.

6. Row overlap behaves correctly.

7. Header from page 1 propagates to page 2.

8. Repeated page header is recognized.

9. New header replaces old header.

10. Overlapping chunk duplicate reconciliation.

11. Conflicting overlapping extraction.

12. Invalid Gemini JSON.

13. transient Gemini failure + Tenacity retry.

14. failed chunk does not destroy whole run.

15. provenance coordinate transformation.

16. negative accounting values:
        (1,250)

17. percentages.

18. em dash / blank / N/A values.

19. multi-level headers.

20. mixed digital/scanned document.


======================================================================
38. CONFIGURATION
======================================================================

Create centralized configuration for:

    model
    PDF rendering DPI
    crop padding
    maximum information budget
    target rows
    maximum rows
    word budget
    overlap rows
    retry attempts
    retry min/max wait
    verification policy
    confidence thresholds
    artifact directory
    logging level

Do not scatter magic numbers through the implementation.


======================================================================
39. PERFORMANCE
======================================================================

Avoid unnecessary expensive operations.

RapidOCR:
    geometry/chunk planning for scanned pages.

PDFPlumber:
    geometry for digital pages.

Gemini:
    semantic extraction.

Do not invoke Gemini merely to determine every crop boundary.

Do not invoke an expensive OCR service such as Google Document AI for this
implementation.

Do not download additional ML models.

Do not add embedding models.

The intended pipeline is deliberately:

    cheap deterministic geometry
              ↓
    intelligent adaptive chunking
              ↓
    expensive multimodal reasoning only where valuable


======================================================================
40. IMPORTANT DESIGN DECISIONS
======================================================================

The following are NON-NEGOTIABLE unless repository constraints make them
impossible:

1. Never blindly split pages by fixed percentages.

2. Never intentionally crop through detected text.

3. Chunk based on candidate rows + information density.

4. RapidOCR is NOT the final semantic extractor.

5. RapidOCR confidence is NOT final extraction confidence.

6. Gemini sees the ORIGINAL clean image crop.

7. Header context is propagated separately.

8. Keep header context compact.

9. Support headers that appear only on earlier pages.

10. Use overlap between chunks.

11. Reconcile overlap results.

12. Every final item has provenance.

13. Confidence is evidence-based rather than merely an arbitrary model
    probability.

14. Capture exact LLM requests/responses for debugging.

15. Store images as artifacts rather than enormous base64 log messages.

16. Stream structured logs to Streamlit without blocking processing.

17. Chunking must be independently inspectable in the UI.

18. Use existing tachyon/llm_client.py.

19. Use existing .env/configuration.

20. Wrap model calls using Tenacity.


======================================================================
41. IMPLEMENTATION ORDER
======================================================================

Implement incrementally.

PHASE 1 — REPOSITORY ANALYSIS

Inspect:
    existing folders
    tachyon/llm_client.py
    .env usage
    existing OCR utilities
    existing PDF utilities
    existing logging
    existing Streamlit code

Write a short architecture note before modifying code.


PHASE 2 — DOCUMENT INGESTION

Implement:
    PDF loading
    page rendering
    digital/scanned detection
    normalized page model


PHASE 3 — GEOMETRY

Implement:
    PDFPlumber adapter
    RapidOCR adapter
    normalized WordBox
    row reconstruction


PHASE 4 — CHUNKING

Implement and TEST the complete chunking package BEFORE integrating Gemini.

Generate debug overlays.

Verify visually that boundaries never cut text.


PHASE 5 — HEADER STATE

Implement:
    header extraction
    propagation
    repeated-header handling
    header-change detection


PHASE 6 — GEMINI

Integrate existing:
    tachyon/llm_client.py

Add:
    Tenacity
    structured output
    Pydantic validation
    request/response artifacts


PHASE 7 — EXTRACTION

Implement:
    generic prompt
    document-specific rules
    row classification
    value association


PHASE 8 — PROVENANCE + CONFIDENCE

Implement:
    coordinate mapping
    evidence storage
    overlap agreement
    confidence status
    optional verifier


PHASE 9 — RECONCILIATION

Implement:
    overlap deduplication
    conflicts
    final business output


PHASE 10 — OBSERVABILITY

Implement:
    structured logging
    JSONL events
    artifact storage
    request tracking


PHASE 11 — STREAMLIT

Implement:
    upload
    processing
    live logs
    page viewer
    chunk inspector
    extraction viewer
    provenance viewer
    raw LLM inspector


PHASE 12 — END-TO-END TESTING

Test multiple PDFs including:
    sparse
    dense
    scanned
    digital
    multi-page
    missing repeated headers
    multi-level headers


======================================================================
42. MOST IMPORTANT DEBUGGING PRINCIPLE
======================================================================

At the end, if an extracted value is wrong, the UI must make it possible
for a developer to answer:

    1. What did the original page look like?

    2. What geometry did RapidOCR/PDFPlumber detect?

    3. Why was this chunk boundary selected?

    4. What EXACT image was sent to Gemini?

    5. What header context was supplied?

    6. What exact prompt/version was used?

    7. What did Gemini return before parsing?

    8. What did structured validation produce?

    9. Was this row also present in an overlapping chunk?

    10. Did those extractions agree?

    11. Why did the system assign this confidence/status?

    12. Where exactly on the source PDF did the extracted value come from?

If the implementation cannot answer these questions, observability is
insufficient.


======================================================================
43. BEFORE WRITING CODE
======================================================================

First inspect the repository and report:

1. Existing project structure relevant to this implementation.
2. Exact location/API of tachyon/llm_client.py.
3. Existing OCR/PDF utilities that can be reused.
4. Existing Streamlit architecture, if any.
5. Proposed files/modules to add or modify.
6. Any conflict between this specification and the existing codebase.

Then implement phase-by-phase.

Do not unnecessarily rewrite working code.

Keep modules small, typed and testable.

Prioritize correctness, auditability and debuggability over cleverness.