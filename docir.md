You are implementing a production-grade **PDF → canonical intermediate representation (IR)** system.

The system must handle arbitrary PDFs ranging from roughly **10 to 1000+ pages**, including:

- digitally generated PDFs
- scanned PDFs
- mixed digital/scanned PDFs
- financial statements
- tables
- multi-column layouts
- forms
- charts
- formulas
- figures
- headers/footers
- footnotes
- lists
- signatures/stamps
- unusual layouts
- repeated structures across pages
- tables spanning pages
- rotated pages

The primary requirement is not merely "good OCR."

The goal is:

> Capture every meaningful piece of document content and structure in a canonical IR, with source provenance. If something cannot be extracted reliably, it must be explicitly represented as unresolved rather than silently omitted or guessed.

Accuracy is more important than minimizing model calls initially. However, the design must scale to 1000-page PDFs, support parallelization, caching and resumability.

---

# 1. Critical model requirement

The vision/LLM model must be completely switchable.

The rest of the codebase must NEVER contain logic like:

```python
if model == "gemini":
    ...
elif model == "gemma":
    ...
```

Parsing logic must depend on an abstract model interface only.

A user should be able to run:

```bash
python -m pdf_ir parse input.pdf \
    --model-id "gemini-3-flash-preview" \
    --output ./output
```

and later:

```bash
python -m pdf_ir parse input.pdf \
    --model-id "gemma-4-31b-it" \
    --output ./output
```

without changing parsing code.

Model configuration should look conceptually like:

```python
class ModelConfig(BaseModel):
    model_id: str
    temperature: float = 0.0
    max_output_tokens: int = 16384
    timeout_seconds: int = 180
    max_retries: int = 3
```

Expose one abstraction:

```python
class VisionLanguageModel(Protocol):

    async def generate_structured(
        self,
        *,
        model_id: str,
        system_prompt: str,
        user_prompt: str,
        images: list[bytes],
        response_schema: type[BaseModel],
        temperature: float = 0.0,
    ) -> BaseModel:
        ...
```

If this repository already contains an LLM/VLM client, use it instead of creating a vendor-specific client.

The parser itself must know only:

```text
model_id
image(s)
prompt
response schema
```

Do not put Gemini-, Gemma-, GPT-, Claude-, Grok-, etc. specific parsing logic into the pipeline.

---

# 2. Architectural principle

Do NOT implement:

```text
PDF
 ↓
one model call
 ↓
huge JSON
```

Implement a staged document compiler:

```text
                               PDF
                                │
                 ┌──────────────┴──────────────┐
                 │                             │
          Native PDF analysis              Rendering
                 │                             │
      chars/spans/fonts/images             Page image
       vectors/coordinates                   │
                 │                            │
                 │                      Layout model pass
                 │                            │
                 │                       region proposals
                 │                            │
                 │            ┌───────────────┼───────────────┐
                 │            │               │               │
                 │          text            table           chart
                 │            │               │               │
                 │            └──── specialized crop passes ──┘
                 │                            │
                 └───────────────┬────────────┘
                                 │
                         Evidence reconciliation
                                 │
                         Deterministic validation
                                 │
                           Coverage validation
                                 │
                               PageIR
                                 │
                         Persistent page store
                                 │
                       Cross-page reconstruction
                                 │
                            DocumentIR
```

This design deliberately separates:

1. what the PDF physically contains;
2. what the page visually looks like;
3. what the content structurally means.

---

# 3. Relevant implementation ideas to reproduce

Implement these concepts directly. Do not attempt to access external repositories.

## 3.1 Page → layout → crop → specialized recognition

A strong document parsing pattern is:

```text
complete page
   ↓
layout detection
   ↓
region bounding boxes
   ↓
crop regions from ORIGINAL high-resolution page
   ↓
task-specific parsing per crop
```

Do NOT require one VLM invocation to simultaneously solve exact OCR, layout, tables, formulas and charts.

The same underlying model can be reused with different prompts:

```text
Layout Detection
Text Recognition
Table Recognition
Formula Recognition
Chart Recognition
Figure Analysis
```

Run deterministic post-processing after model inference.

---

## 3.2 Canonical hierarchical document object

The canonical IR must separately model:

```text
texts
tables
pictures
charts
formulas
key/value fields
groups
sections
document furniture
```

"Document furniture" means things like:

```text
headers
footers
page numbers
```

Store hierarchy using stable IDs and parent/child relationships.

Reading order must be explicitly represented.

Every element should carry provenance.

---

## 3.3 Page-oriented execution

Each PDF page is an independently resumable job.

Never require the entire PDF to be held in model context.

For a 1000-page document:

```text
1000 pages
→ 1000 PageJobs
→ parallel processing
→ persistent PageIR objects
→ lightweight final document-reduction pass
```

Do not render all 1000 pages into memory simultaneously.

---

# 4. Suggested project structure

Create a clean package similar to:

```text
pdf_ir/
    __init__.py

    cli.py
    config.py

    models/
        document.py
        page.py
        elements.py
        table.py
        chart.py
        provenance.py
        validation.py

    pdf/
        inspect.py
        render.py
        native_extract.py
        coordinates.py

    model/
        interface.py
        client_adapter.py
        schemas.py

    parsing/
        page_classifier.py
        layout.py
        region_router.py
        text.py
        table.py
        chart.py
        formula.py
        figure.py
        forms.py

    reconcile/
        native_alignment.py
        geometry.py
        deduplicate.py
        reading_order.py

    validation/
        structural.py
        text_coverage.py
        visual_coverage.py
        tables.py
        page.py

    pipeline/
        page_pipeline.py
        document_pipeline.py
        executor.py
        retry.py

    document/
        hierarchy.py
        continuations.py
        repeated_furniture.py
        reducer.py

    exporters/
        json_export.py
        markdown.py
        html.py
        omnidocbench.py
        parsebench.py

    cache/
        content_store.py
        hashes.py

    tests/
        ...
```

Prefer clear separation over putting the entire implementation in one module.

---

# 5. PDF ingestion

When loading a PDF:

Calculate:

```text
document SHA-256
page count
page sizes
rotation
PDF metadata
```

Assign:

```python
document_id = sha256(pdf_bytes)
```

Each page gets a deterministic page ID:

```python
page_id = f"{document_id}:page:{page_number}"
```

---

# 6. Native PDF extraction

Before calling any VLM, extract as much trustworthy information as possible directly from the PDF.

Use a mature PDF library already available in the environment, preferably PyMuPDF if available.

For each page extract:

```text
text blocks
text lines
text spans
character/text bounding boxes where available
font name
font size
font flags
text color if easily available
embedded images and coordinates
vector drawings if practical
links
annotations
page dimensions
rotation
```

Represent native spans approximately as:

```python
class NativeTextSpan(BaseModel):
    id: str
    text: str
    bbox_pdf: BoundingBox
    font_name: str | None
    font_size: float | None
    bold: bool | None
    italic: bool | None
    source: Literal["pdf_native"] = "pdf_native"
```

Do not clean or normalize the text at extraction time.

Preserve literal strings.

---

# 7. Coordinate systems

Support three coordinate spaces explicitly:

```text
PDF coordinates
rendered-image pixel coordinates
normalized coordinates [0, 1000]
```

Implement deterministic conversion functions.

Example:

```python
pdf_bbox_to_normalized(...)
normalized_bbox_to_pdf(...)
pixel_bbox_to_pdf(...)
pdf_bbox_to_pixel(...)
```

Never mix coordinate spaces implicitly.

Every bbox object must specify its coordinate system.

Example:

```python
class BoundingBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float
    coordinate_space: Literal["pdf", "pixel", "normalized"]
```

Validate:

```text
x0 <= x1
y0 <= y1
finite values only
within page boundaries
```

---

# 8. Streaming renderer

Render pages individually.

Default starting resolution:

```text
250–300 DPI
```

Make it configurable.

Do not render the complete PDF into a list of PIL images.

Expose something like:

```python
render_page(pdf_path, page_number, dpi) -> RenderedPage
```

Keep:

```text
width_px
height_px
dpi
page number
image hash
```

Use the original rendered page for crops.

Do not repeatedly JPEG-compress intermediate images.

PNG is preferred for OCR/document processing unless there is a strong reason otherwise.

---

# 9. Page classification

Before expensive region calls, classify pages using deterministic PDF signals.

Suggested page classes:

```python
DIGITAL_SIMPLE
DIGITAL_COMPLEX
SCANNED
MIXED
BLANK
```

Use heuristics such as:

```text
number of native characters
native text area coverage
large raster image coverage
number of vector/text elements
number/density of blocks
```

Do not use the model merely to decide whether a page has native text.

Approximate routing:

```text
DIGITAL_SIMPLE
    native extraction
    + one layout pass

DIGITAL_COMPLEX
    native extraction
    + layout
    + selected region parsing

SCANNED
    layout
    + OCR/recognition of all meaningful regions

MIXED
    native extraction
    + visual parsing for unsupported regions
```

---

# 10. Canonical PageIR

Implement a Pydantic schema.

Example:

```python
class PageIR(BaseModel):
    page_id: str
    page_number: int

    width_pdf: float
    height_pdf: float

    rotation: int

    page_type: PageType

    elements: list[ElementIR]

    native_spans: list[NativeTextSpan]

    validation: PageValidationResult

    status: Literal[
        "verified",
        "partial",
        "needs_review",
        "failed",
    ]
```

---

# 11. Canonical ElementIR

Use stable IDs.

```python
class ElementIR(BaseModel):
    id: str

    type: ElementType

    bbox_pdf: BoundingBox
    bbox_normalized: BoundingBox

    reading_order: int | None

    parent_id: str | None
    child_ids: list[str]

    content: ElementContent

    provenance: Provenance

    validation: ElementValidation

    status: Literal[
        "verified",
        "accepted",
        "unresolved",
    ]
```

Supported element types should initially include:

```python
TITLE
SECTION_HEADER
PARAGRAPH
LIST
LIST_ITEM

TABLE
TABLE_CAPTION

FIGURE
FIGURE_CAPTION

CHART

FORMULA

CODE

KEY_VALUE
FORM_FIELD

HEADER
FOOTER
PAGE_NUMBER
FOOTNOTE

SIGNATURE
STAMP

UNKNOWN
```

Do not force unknown content into the nearest known category.

`UNKNOWN` is a legitimate and important IR node.

---

# 12. Provenance

Every extracted object MUST retain provenance.

Example:

```python
class Provenance(BaseModel):
    document_id: str
    page_number: int

    source_bbox_pdf: BoundingBox
    source_bbox_normalized: BoundingBox

    crop_hash: str | None

    native_span_ids: list[str]

    model_id: str | None
    prompt_version: str | None

    inference_pass: str | None

    raw_response_hash: str | None
```

Store raw model responses separately in debug artifacts rather than bloating canonical IR.

Given any IR value, a developer should eventually be able to trace:

```text
IR element
→ page
→ bbox
→ source crop
→ native PDF spans
→ model pass
```

---

# 13. Layout pass

For every nonblank page run a whole-page layout pass.

The task is ONLY:

```text
identify meaningful document regions
classify them
return their geometry
determine approximate reading order
```

Do not ask for complete transcription.

Use strict structured output.

Model schema:

```python
class LayoutRegion(BaseModel):
    id: str
    type: ElementType
    bbox: list[int]       # [x0,y0,x1,y1], normalized 0..1000
    reading_order: int
    confidence_reason: str | None = None


class LayoutResponse(BaseModel):
    regions: list[LayoutRegion]
```

The model-generated "confidence_reason" is diagnostic only.

Never treat model self-confidence as a numeric correctness probability.

---

# 14. Layout prompt

Use a versioned prompt.

Something conceptually equivalent to:

```text
You are performing document layout segmentation.

Analyze the supplied page image.

Return every meaningful visual/document region exactly once.

Allowed types:
TITLE,
SECTION_HEADER,
PARAGRAPH,
LIST,
LIST_ITEM,
TABLE,
TABLE_CAPTION,
FIGURE,
FIGURE_CAPTION,
CHART,
FORMULA,
CODE,
KEY_VALUE,
FORM_FIELD,
HEADER,
FOOTER,
PAGE_NUMBER,
FOOTNOTE,
SIGNATURE,
STAMP,
UNKNOWN.

For each region return:
- unique temporary id
- type
- bounding box [x0,y0,x1,y1] normalized from 0 to 1000
- reading_order starting at 0

Rules:
1. Do not transcribe the full page.
2. Do not omit small text, footnotes, page numbers, labels or captions.
3. Do not merge unrelated regions.
4. Do not divide a visually coherent paragraph unnecessarily.
5. Tables must be represented as TABLE regions.
6. Charts must be represented as CHART regions, not generic figures.
7. If something visibly meaningful cannot be classified, use UNKNOWN.
8. Reading order must correspond to how a human would read the page.
9. Bounding boxes should tightly enclose the content.
10. Never invent content outside the visible page.

Return only data matching the required schema.
```

Set temperature to `0`.

---

# 15. Layout post-processing

Never directly trust model layout output.

Perform deterministic checks:

```text
bbox valid
bbox within [0,1000]
bbox nonzero area
reading order valid
duplicate regions
extreme overlaps
tiny accidental regions
```

For near-duplicate boxes of the same class:

```text
IoU > configurable threshold, e.g. 0.90
```

merge/deduplicate cautiously.

Do not aggressively merge different classes.

---

# 16. Crop generation

For regions requiring specialized parsing, map normalized bbox → pixels and crop from the ORIGINAL high-resolution page render.

Add padding:

```text
~1–2% of region dimensions
```

bounded by page boundaries.

Hash every crop.

Example:

```python
crop_id = sha256(
    page_image_hash
    + bbox_coordinates
    + crop_parameters
)
```

Use this hash for caching.

---

# 17. Region routing

Different region types need different treatment.

Suggested routing:

```text
PARAGRAPH
SECTION_HEADER
TITLE
LIST_ITEM
HEADER
FOOTER
FOOTNOTE
    → native text alignment first
    → model OCR only if native evidence inadequate

TABLE
    → table parser

CHART
    → chart parser

FORMULA
    → formula parser

FIGURE
    → preserve image
    → optional description

FORM_FIELD / KEY_VALUE
    → form parser

UNKNOWN
    → general recovery parser
```

---

# 18. Digital text: native text should usually win

For digitally generated PDFs, do not ask the model to re-OCR clean native text unnecessarily.

Instead:

1. find native spans whose bboxes overlap the detected region;
2. assign them geometrically;
3. reconstruct lines/order using PDF coordinates;
4. use the visual model primarily for semantic structure.

Example:

```text
Native PDF:
"Total Outstanding Balance"

Model OCR:
"Total Outstanding Balence"
```

Use:

```text
"Total Outstanding Balance"
```

unless there is concrete evidence that the native PDF text layer is corrupt.

---

# 19. Native span alignment

For each native text span `s` and layout element `e`, compute a containment/overlap score.

For example:

```python
coverage = intersection_area(s.bbox, e.bbox) / area(s.bbox)
```

Assign strongly contained spans first.

Suggested acceptance:

```text
coverage >= 0.80
```

Make threshold configurable.

Resolve ambiguous cases using:

```text
vertical baseline
horizontal relationship
reading order
nearest containing region
```

Do not duplicate the same native text span into multiple independent content elements.

Track unassigned spans.

---

# 20. Text recognition fallback

For scanned regions or corrupt text layers use a crop-level recognition call.

Schema:

```python
class TextLine(BaseModel):
    text: str
    bbox: list[int] | None


class TextRecognitionResponse(BaseModel):
    text: str
    lines: list[TextLine]
```

Prompt:

```text
Transcribe this document region exactly.

Rules:
- preserve spelling
- preserve numbers
- preserve punctuation
- preserve symbols
- preserve visible line order
- do not summarize
- do not rewrite
- do not correct grammar
- do not fill missing text from context
- if a character is genuinely unreadable, represent uncertainty explicitly rather than guessing

Return only data matching the required schema.
```

---

# 21. Table parser

Tables deserve their own crop pass.

Canonical representation:

```python
class TableCell(BaseModel):
    row: int
    col: int

    rowspan: int = 1
    colspan: int = 1

    text: str

    bbox_normalized_to_crop: BoundingBox | None
    native_span_ids: list[str]


class TableData(BaseModel):
    row_count: int
    column_count: int
    cells: list[TableCell]
```

Table prompt:

```text
Recover the exact structure of this table.

Requirements:
- identify the physical rows and columns
- preserve merged cells
- return rowspan and colspan
- preserve blank cells when structurally meaningful
- preserve visible text exactly
- do not infer values that are not visible
- do not calculate totals unless the total is explicitly printed
- do not convert missing cells into zero
- distinguish multi-row headers from body rows
- do not flatten the table into prose

Return only the requested structured table representation.
```

---

# 22. Digital table reconciliation

For digital PDFs:

Use the model primarily for:

```text
row/column boundaries
merged cells
header/body structure
cell membership
```

Use native PDF spans to recover exact cell text where possible.

Algorithm:

```text
table crop
→ model cell geometry/structure
→ transform cell bboxes to page/PDF coordinates
→ assign native spans to individual cells
→ rebuild exact cell text
→ validate
```

This should be preferred over blindly trusting model-generated cell text.

---

# 23. Table validators

Implement deterministic checks:

```text
row >= 0
column >= 0
rowspan >= 1
colspan >= 1

cell coordinates fit row_count / column_count

no impossible overlapping spans

merged cells do not create inconsistent occupancy

all native spans inside table are:
    assigned
    explicitly ignored with reason
    or flagged unresolved
```

Create an occupancy matrix.

Example:

```text
rows x columns
```

Mark each grid slot occupied by cells including spans.

Raise validation failure if incompatible cells claim the same grid position.

---

# 24. Formula parser

Schema:

```python
class FormulaData(BaseModel):
    latex: str
    displayed: bool
    equation_number: str | None
```

Prompt:

```text
Transcribe the visible mathematical expression into LaTeX.

Do not simplify.
Do not evaluate.
Do not change mathematical notation.
Preserve subscripts, superscripts, fractions, roots, symbols and equation numbering.
```

---

# 25. Chart parser

Charts must not merely become prose descriptions.

Canonical representation:

```python
class ChartAxis(BaseModel):
    label: str | None
    unit: str | None


class ChartPoint(BaseModel):
    x: str | float | None
    y: str | float | None
    label: str | None


class ChartSeries(BaseModel):
    name: str | None
    points: list[ChartPoint]


class ChartData(BaseModel):
    title: str | None
    chart_type: str | None

    x_axis: ChartAxis | None
    y_axis: ChartAxis | None

    series: list[ChartSeries]

    legend_entries: list[str]
    notes: list[str]
```

Prompt:

```text
Extract the structured data represented by this chart.

Do not estimate values unless they are visually encoded clearly enough to read.
Do not invent intermediate values.
Preserve labels, units, legends and annotations.

If exact numerical values cannot be recovered, retain the visible chart as an unresolved/partially resolved chart rather than fabricating values.
```

Always preserve the chart crop in provenance.

---

# 26. Figures

For figures:

Always preserve:

```text
crop
bbox
caption relationship if detected
```

Description is secondary.

The system must remain useful even if figure interpretation fails.

---

# 27. UNKNOWN regions

An UNKNOWN region must not disappear.

Store:

```python
{
    "type": "unknown",
    "bbox": ...,
    "crop_hash": ...,
    "status": "unresolved",
    "reason": ...
}
```

Attempt one or more recovery passes using the same model with a general prompt.

If unresolved, keep it unresolved.

Never force it into a made-up category.

---

# 28. Model retries and escalation

Retries must be local.

If one table fails on page 537, do NOT rerun:

```text
page 537
document
```

unless required.

Retry:

```text
table crop only
```

Suggested escalation strategy:

Attempt 1:

```text
original crop
normal resolution
specialized prompt
```

Attempt 2:

```text
crop with slightly expanded bounds
higher rendering DPI
same specialized prompt
```

Attempt 3:

```text
same region with additional page context if necessary
```

After the configured limit:

```text
status = unresolved
```

Do not loop indefinitely.

---

# 29. Deterministic validation layer

The final IR must not be accepted merely because the model returned valid JSON.

Implement validators for:

### Geometry

```text
bbox bounds
bbox area
bbox overlap anomalies
```

### Text

```text
native text assignment
duplicate text
missing native text
```

### Tables

```text
grid validity
cell occupancy
native span coverage
```

### Reading order

```text
duplicates
cycles
missing indices
obvious ordering inconsistencies
```

### Structure

```text
caption relationships
parent references
child references
dangling IDs
```

### Schema

Full Pydantic validation.

---

# 30. Text coverage

For digital pages compute:

```text
meaningful native characters assigned to IR elements
-----------------------------------------------------
total meaningful native characters
```

Call this:

```python
native_text_coverage
```

Ignore only explicitly configured categories such as:

```text
whitespace
control characters
```

Do NOT silently exclude difficult text.

Keep:

```python
unassigned_native_span_ids
```

A digital page with unexplained native text must not automatically be marked verified.

---

# 31. Visual coverage

Also implement a best-effort visual coverage validator.

Goal:

Detect meaningful areas of the rendered page that have no IR element.

A practical first implementation:

1. convert page to grayscale;
2. derive a foreground/content mask using adaptive thresholding or similar;
3. suppress pure white/background regions;
4. optionally apply morphological operations to join characters into blocks;
5. create a mask corresponding to union of all IR element bboxes;
6. compute connected components in meaningful foreground not covered by any element;
7. ignore tiny noise components;
8. flag sufficiently large unexplained regions.

Do NOT treat the coverage score as perfect vision understanding.

Its purpose is to find obvious omissions.

Create UNKNOWN regions for significant unexplained connected components and send those crops through recovery.

---

# 32. Validation status

An element should be `verified` only when appropriate evidence exists.

Example:

```python
class ElementValidation(BaseModel):
    schema_valid: bool
    geometry_valid: bool

    native_text_coverage: float | None

    structure_valid: bool | None

    warnings: list[str]
    errors: list[str]
```

A page:

```python
class PageValidationResult(BaseModel):
    native_text_coverage: float | None
    visual_coverage: float | None

    unassigned_native_spans: list[str]
    unresolved_elements: list[str]

    warnings: list[str]
    errors: list[str]
```

---

# 33. Confidence

Do NOT store:

```text
model_confidence = 0.97
```

and assume it means correctness.

Confidence/status should be based primarily on objective evidence:

```text
schema validation
native/model agreement
coverage
geometric consistency
table consistency
cross-pass consistency
```

If implementing a composite score, make every component visible.

Example:

```python
confidence_evidence = {
    "native_text_agreement": 1.0,
    "geometry_valid": True,
    "structure_valid": True,
    "coverage": 0.998,
}
```

---

# 34. Reading order

Reading order is an explicit property.

Initially use model output.

Then sanity-check spatially.

For multi-column documents, avoid naïve top-to-bottom sorting.

Preserve:

```python
reading_order: int
```

At the page level.

Document-level reading order is assembled later.

---

# 35. Page-level persistence

As soon as one page finishes, write:

```text
output/
    document.json
    pages/
        000001.json
        000002.json
        ...
    crops/
        ...
    raw_model/
        ...
    validation/
        ...
```

If the process crashes after page 731 of 1000:

restart from page 732 or whatever pages remain incomplete.

Do not repeat already validated page work.

---

# 36. Content-addressed cache

Cache model results using a key derived from:

```text
model_id
prompt_version
image hash
schema version
generation parameters
```

Example:

```python
cache_key = sha256(
    model_id
    + prompt_version
    + image_hash
    + schema_version
    + generation_config_hash
)
```

Changing model IDs must naturally create a different cache entry.

This is important because we will benchmark many models using the same parser.

---

# 37. Concurrency

Implement bounded async concurrency.

Conceptually:

```text
PDF
 ↓
page queue
 ↓
N page workers
 ↓
model-call semaphore
 ↓
PageIR store
```

Make configurable:

```text
max_parallel_pages
max_parallel_model_calls
max_parallel_region_calls
```

Do not create thousands of concurrent requests.

Use backpressure.

---

# 38. Failure semantics

Distinguish:

```text
transient inference failure
permanent invalid input
schema failure
PDF rendering failure
region parsing failure
page partial success
page failure
```

A single bad region must not invalidate a 1000-page document.

Example:

```text
999 pages verified
1 page partial
```

should produce a DocumentIR with:

```text
status = partial
```

and the failed page clearly identified.

---

# 39. Raw responses

For reproducibility, optionally store raw model outputs.

Do not use raw model responses as downstream application data.

Canonical flow:

```text
raw response
 ↓
strict schema parsing
 ↓
normalization
 ↓
validation
 ↓
canonical IR
```

---

# 40. Cross-page reducer

After all PageIR objects are available, perform a separate document-level pass.

Do NOT send all page images again.

Construct compact page summaries containing:

```text
page number

headings:
    text
    style
    bbox

tables:
    headers
    column count
    touches page top?
    touches page bottom?

lists

captions

footnotes

repeated headers/footers
```

Use deterministic matching before using an LLM.

---

# 41. Repeated headers and footers

Detect repeated page furniture statistically.

Example:

A nearly identical text/span appears:

```text
same approximate y-position
same approximate font/style
on many pages
```

then classify as likely HEADER/FOOTER.

Do not rely solely on model classification.

---

# 42. Cross-page table continuation

For tables near page boundaries, detect continuation candidates using:

```text
previous table touches bottom of page
next table starts near top of next page

similar number of columns
similar column x coordinates
similar headers
similar visual width
compatible cell structure
```

Compute a deterministic continuation score.

Only use the model as a tiebreaker for ambiguous candidates.

Represent:

```python
Relationship(
    from_id="p17_table_3",
    type="continues_as",
    to_id="p18_table_1",
)
```

Do not physically merge the original PageIR tables.

At DocumentIR level optionally expose a logical combined table view.

---

# 43. Heading hierarchy

Reconstruct document hierarchy using:

```text
heading numbering
font size
font weight
indentation
page position
text patterns
model classification
```

Example:

```text
1
1.1
1.1.1
```

is strong deterministic hierarchy evidence.

Model reasoning should only resolve ambiguity.

---

# 44. Canonical DocumentIR

Implement:

```python
class Relationship(BaseModel):
    from_id: str
    type: str
    to_id: str


class DocumentIR(BaseModel):
    document_id: str
    schema_version: str

    metadata: dict

    pages: list[PageIR]

    relationships: list[Relationship]

    document_status: Literal[
        "verified",
        "partial",
        "needs_review",
        "failed",
    ]
```

Possible relationship types:

```text
parent_of
next_in_reading_order
caption_of
footnote_of
reference_to
continues_as
table_continuation
list_member_of
section_of
formula_number_of
label_of
value_of
```

---

# 45. Important principle: IR first, Markdown second

Markdown is NOT the canonical representation.

HTML is NOT the canonical representation.

They are exporters.

Canonical source of truth:

```text
DocumentIR
```

Then:

```text
DocumentIR
 ├── JSON
 ├── Markdown
 ├── HTML
 ├── benchmark format
 └── downstream extraction
```

---

# 46. Markdown exporter

Implement deterministic conversion.

Suggested mapping:

```text
TITLE → # heading
SECTION_HEADER → appropriate heading
PARAGRAPH → text
LIST/LIST_ITEM → Markdown lists
TABLE → HTML table
FORMULA → $$latex$$
FIGURE → placeholder/reference + caption
CHART → optional structured representation
FOOTNOTE → footnote representation
```

Preserve reading order.

Do not regenerate prose using an LLM.

---

# 47. OmniDocBench-compatible exporter

Implement an exporter that converts PageIR to page-level Markdown suitable for external evaluation.

The important behavior is:

```text
text paragraphs → text in reading order
tables → HTML table
formulas → LaTeX
reading order → serialized element order
```

Do not change canonical IR for benchmark compatibility.

Omni-style evaluation typically assesses:

```text
text normalized edit distance
table TEDS
formula accuracy/CDM
reading-order edit distance
```

The benchmark adapter exists purely so that multiple parser configurations/models can be compared consistently.

---

# 48. ParseBench-style exporter

Also expose:

```python
class BenchmarkPageOutput(BaseModel):
    markdown: str
    layout_elements: list[...]
```

Each layout element should contain:

```text
element type
normalized bbox
associated content
```

This allows evaluation of:

```text
tables
charts
content faithfulness
semantic formatting
visual grounding
```

Again:

```text
benchmark format != production IR
```

---

# 49. Model experimentation

Everything should allow running:

```bash
pdf-ir benchmark \
    --model-id MODEL_A \
    dataset/
```

then:

```bash
pdf-ir benchmark \
    --model-id MODEL_B \
    dataset/
```

Same:

```text
renderer
prompts
schemas
validators
post-processing
```

Only model ID changes.

Store run metadata:

```json
{
  "model_id": "...",
  "timestamp": "...",
  "parser_version": "...",
  "ir_schema_version": "...",
  "prompt_versions": {
      "layout": "...",
      "table": "...",
      "text": "...",
      "chart": "..."
  },
  "dpi": 300
}
```

---

# 50. Internal evaluation metrics

Public benchmark scores are not enough.

Implement hooks to calculate internal metrics when ground truth exists:

```text
Text CER / normalized edit distance

Layout:
precision
recall
F1
IoU

Tables:
cell text accuracy
row/column correctness
structure accuracy
TEDS if practical

Reading order:
normalized edit distance

Element-type classification accuracy

Native text coverage

Visual coverage

Unresolved region rate

Invalid IR rate

Duplicate-content rate
```

Most importantly track:

```text
Silent Omission Rate
```

Definition:

```text
ground-truth meaningful elements absent from IR
AND
not represented as UNKNOWN/unresolved
-------------------------------------------------
total meaningful ground-truth elements
```

The desired architectural target is:

```text
Silent Omission Rate → 0
```

Even if some content remains explicitly unresolved.

---

# 51. Prompt versioning

Prompts are production code.

Store them as named/versioned files or constants.

Example:

```text
layout_v1
text_v1
table_v1
chart_v1
formula_v1
unknown_recovery_v1
```

Cache keys must include prompt version.

Do not make major prompt changes without updating the version.

---

# 52. Structured-output failure

If the model provider supports schema-constrained output, use it.

If not:

1. request JSON only;
2. parse it;
3. validate with Pydantic;
4. if malformed, allow ONE repair call containing the invalid response and schema;
5. the repair call may fix syntax/schema only;
6. it must not invent document content.

If still invalid:

```text
region/page = partial
```

Do not regex-hack arbitrary malformed responses into seemingly valid data.

---

# 53. Testing

Write extensive tests.

Minimum test categories:

### Geometry

```text
coordinate conversions round-trip
bbox clipping
IoU
intersection
```

### Native alignment

```text
single paragraph
multi-column
overlapping candidates
unassigned span
```

### Tables

```text
simple grid
merged cells
multi-row header
blank cells
invalid overlap
```

### Page classification

```text
digital
scan
mixed
blank
```

### Caching

```text
same model + same image → cache hit
different model → cache miss
different prompt version → cache miss
```

### Resumability

Process pages 1–5.

Simulate crash.

Restart.

Verify pages 1–5 are not reprocessed.

### Partial failure

One region fails.

Verify page/document remains usable with explicit unresolved node.

### Exporters

Verify stable deterministic Markdown/JSON output.

---

# 54. Synthetic test fixtures

If real fixture PDFs are not present, programmatically generate small test PDFs containing:

```text
paragraphs
two-column text
simple table
merged-cell table
header/footer
page number
formula-like text
image
multi-page table
```

Do not make tests dependent on internet resources.

---

# 55. Observability

Log at minimum:

```text
document_id
page_number
model_id
pass type
crop ID
attempt number
duration
cache hit/miss
validation status
```

Collect run-level statistics:

```text
total pages
verified pages
partial pages
failed pages

model calls
cache hits
retries

table regions
chart regions
unknown regions

unassigned native spans

average native coverage
average visual coverage
```

Do not log sensitive document content unnecessarily.

---

# 56. Security/privacy

Documents may contain confidential financial information.

Therefore:

```text
avoid plaintext document content in normal logs
do not log model prompts containing full page content unless debug mode explicitly enabled
make raw-response persistence configurable
hash IDs where possible
```

---

# 57. Performance requirements

The architecture should make these possible:

```text
1000-page PDF without holding all rendered pages in RAM

parallel page execution

parallel region parsing

bounded model concurrency

restart after failure

skip cached work

reprocess only one page or region

switch models without touching parser code
```

Do not optimize prematurely at the expense of correctness.

Correctness first.

---

# 58. CLI

Provide at least:

```bash
pdf-ir parse INPUT.pdf \
    --model-id MODEL \
    --output OUTPUT_DIR
```

Useful options:

```text
--dpi
--max-parallel-pages
--max-parallel-model-calls
--force
--pages 1-20
--debug
--store-raw-responses
```

Also:

```bash
pdf-ir validate OUTPUT_DIR/document_ir.json
```

and:

```bash
pdf-ir export \
    OUTPUT_DIR/document_ir.json \
    --format markdown
```

---

# 59. Configuration

Use a config object similar to:

```yaml
model:
  model_id: gemini-3-flash-preview
  temperature: 0
  max_output_tokens: 16384
  timeout_seconds: 180

render:
  dpi: 300
  retry_dpi: 400

execution:
  max_parallel_pages: 4
  max_parallel_model_calls: 8

validation:
  native_span_containment_threshold: 0.80
  duplicate_iou_threshold: 0.90
  min_native_text_coverage_verified: 0.995

retry:
  region_attempts: 3

storage:
  store_raw_responses: false
```

Do not hardcode these values throughout the code.

---

# 60. Implementation order

Implement incrementally.

## Phase 1 — foundations

Implement:

```text
PDF loader
page renderer
native extraction
coordinate transformations
IR Pydantic schemas
model abstraction
content-addressed cache
```

Tests must pass before continuing.

## Phase 2 — baseline page parser

Implement:

```text
layout pass
basic native-text alignment
PageIR generation
JSON persistence
```

Get simple digital PDFs working end-to-end.

## Phase 3 — specialist regions

Implement:

```text
table crop parser
formula parser
scanned-text parser
chart parser
figure preservation
```

## Phase 4 — validation

Implement:

```text
native text coverage
table structural checks
bbox validation
duplicate detection
UNKNOWN regions
visual coverage
local retry/escalation
```

## Phase 5 — scale

Implement:

```text
async page queue
bounded concurrency
resumability
cache
page-level persistence
```

## Phase 6 — document structure

Implement:

```text
headers/footers
heading hierarchy
cross-page tables
cross-page lists
relationships
DocumentIR reducer
```

## Phase 7 — exporters/evaluation

Implement:

```text
Markdown exporter
HTML exporter
Omni-style benchmark exporter
ParseBench-style benchmark exporter
metrics/reporting hooks
```

---

# 61. First production baseline

The first complete version should follow:

```text
PDF

→ inspect PDF

→ for each page:
      native extraction
      render at 300 DPI

      classify page

      whole-page model layout pass

      align native spans

      parse tables separately
      parse charts separately
      parse formulas separately
      OCR text only where native text is insufficient

      validate geometry

      calculate native text coverage

      calculate visual coverage

      recover significant unexplained regions

      mark unresolved content explicitly

      persist PageIR

→ detect repeated furniture

→ reconstruct cross-page relationships

→ build DocumentIR

→ validate DocumentIR

→ export JSON + optional Markdown

→ generate processing/validation report
```

---

# 62. Important prohibitions

Do NOT:

```text
feed an entire 1000-page PDF to the model and ask for JSON

make Markdown the canonical representation

trust model confidence scores

silently drop model failures

silently drop unknown visual regions

silently remove native PDF text that cannot be aligned

re-OCR perfect digital text unnecessarily

hardcode a specific model

couple cache entries across model IDs

rerun an entire document because one crop failed

use LLMs for deterministic calculations that can be done geometrically

allow malformed IR because it "looks approximately right"
```

---

# 63. Success criteria

A successful implementation must demonstrate all of the following:

1. Changing only `model_id` changes the inference model.

2. A 1000-page PDF is handled as page jobs rather than one monolithic request.

3. Digital PDF text is preserved from native PDF evidence wherever trustworthy.

4. Layout and semantic structure are inferred visually.

5. Tables have real row/column/cell structures.

6. Every IR element has page/bbox provenance.

7. Meaningful content that cannot be interpreted becomes `UNKNOWN` rather than disappearing.

8. Page failures are isolated.

9. Processing is resumable.

10. Model calls are cacheable.

11. Canonical JSON can deterministically produce Markdown.

12. Benchmark-specific formats are exporters, not the core representation.

13. Validation reports show exactly why pages are or are not considered verified.

14. The parser can be compared across different models using the exact same pipeline.

---

# 64. Deliverables

At completion provide:

```text
1. working source code

2. README covering:
   architecture
   CLI
   configuration
   IR schema
   model switching
   validation
   scaling

3. example configuration

4. example PDF → IR run

5. sample resulting DocumentIR JSON

6. unit tests

7. integration tests

8. benchmark/export adapters

9. a validation report example

10. architecture diagram in Mermaid
```

Also include a concise document describing:

```text
known limitations
failure modes
which fields are deterministic
which fields depend on model inference
how unresolved regions are represented
how to add new element types
how to connect another model client
```

---

# 65. Final engineering principle

Treat this system as a **document compiler**, not an OCR wrapper.

The model is one source of evidence.

The PDF structure is another.

Geometry is another.

Validators are another.

The final IR should be produced only after these sources have been reconciled.

The desired invariant is:

> No meaningful source content is allowed to disappear silently.

A value may be:

```text
verified
accepted
unresolved
```

but never silently omitted merely because the model did not understand it.

Start by inspecting the existing repository, identifying any reusable model client/PDF utilities, and then implement Phase 1 through Phase 7 in sequence. Do not require internet access or repository downloads to understand or implement the architecture described above.
