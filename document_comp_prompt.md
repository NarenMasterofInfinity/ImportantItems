Implement a production-quality semantic document comparison / delta engine that compares two versions of the same document and identifies meaningful changes even when the newer version has undergone major template, formatting, pagination, section-order, or structural changes.

The system must work for large and complex documents and must not rely on naïvely sending both entire documents to an LLM.

The core architecture should be:

Document ingestion
→ extraction
→ canonical document representation
→ normalization
→ exact/near-exact matching
→ candidate retrieval
→ structural alignment
→ LLM-assisted semantic alignment
→ alignment graph
→ deterministic atomic diff
→ LLM semantic interpretation
→ review-friendly diff output/UI

The central design principle is:

LLM should help determine:
"What corresponds to what?"
and
"What does this change mean?"

Deterministic code should determine:
"What exactly changed?"

Do not build this as a simple text diff.

---

1. Repository integration requirements

Before implementing anything, inspect the repository and understand the existing implementations.

LLM

There is already an LLM client implementation.

Use:

tachyon/llm_client.py

Do NOT introduce a separate LLM SDK or duplicate LLM client unless absolutely necessary.

Inspect "llm_client.py" first and use its existing abstractions, configuration, authentication, retry logic, model selection, etc.

Create clean wrappers/services around it where required, but the actual LLM calls must go through the existing client.

We have access to a wide range of LLMs, but do not assume an embedding model is available.

Use LLMs only where semantic reasoning is required.

Design the system so cheaper/faster models can be used for:

- candidate reranking
- semantic fingerprint generation
- simple equivalence classification

and stronger models can be used for:

- ambiguous alignment
- split/merge reasoning
- complex semantic interpretation

If the existing "llm_client.py" supports model choice, expose model configuration through the document-diff configuration layer.

---

2. OCR

There is already OCR-related functionality inside:

ecm/

Inspect the functions available in the "ecm" folder.

For scanned/image PDFs:

reuse the existing OCR functions from "ecm".

Do not implement a new OCR system.

Use ECM output to obtain as much of the following as available:

text
page number
bounding boxes
reading order
table/layout information
confidence

Adapt to the existing ECM function signatures instead of modifying them unnecessarily.

---

3. Digital PDFs

For born-digital/text PDFs, use:

pdfplumber

Do not OCR a digital PDF unless extraction quality is insufficient.

Use pdfplumber to extract:

- words
- text
- page numbers
- bounding boxes
- font information if useful
- lines/regions where possible
- tables where appropriate

Use coordinates so every comparison result can later point back to the exact source location.

---

4. PDF classification

Create an ingestion step that determines whether pages/documents are:

DIGITAL
SCANNED
HYBRID

For DIGITAL pages:
→ pdfplumber

For SCANNED pages:
→ ECM OCR functions

For HYBRID PDFs:
→ process at page level

Example:

Page 1 → digital
Page 2 → digital
Page 3 → scanned
Page 4 → scanned
Page 5 → digital

Do not make a document-wide assumption when page-level classification is possible.

---

5. Canonical document model

Convert both documents into the same internal representation.

Design appropriate Pydantic/dataclass/domain models.

A rough model is:

Document
    id
    version
    pages[]
    sections[]
    blocks[]
    tables[]

Page
    page_number
    width
    height
    extraction_method
    blocks[]

Block
    id
    document_id
    page_number
    bbox
    reading_order
    block_type
    raw_text
    normalized_text
    section_path
    metadata

Block types should support at minimum:

HEADING
PARAGRAPH
LIST_ITEM
TABLE
CAPTION
FOOTNOTE
HEADER
FOOTER
FIGURE
OTHER

Table representation should not simply flatten the entire table into text.

Represent:

Table
    id
    page_number
    bbox
    columns
    rows
    cells

and preserve cell-level source provenance wherever extraction allows it.

Every semantic comparison result must eventually be traceable to:

document version
page
bounding box
original text/value

---

6. Normalization

Build a normalization layer.

Do NOT destroy the original content.

Store both:

raw_text
normalized_text

Normalization should handle things such as:

- whitespace
- Unicode normalization
- repeated spaces/newlines
- bullet representations
- obvious page-number artifacts
- recurring headers/footers
- optionally section numbering
- currency representation
- basic numerical normalization

Be conservative.

For example:

$5,000,000
USD 5 million
$5.0m

should have normalized numeric representations available, but the original text must remain untouched.

Create normalized structured entities such as:

{
  "raw": "$5.0m",
  "value": 5000000,
  "unit": "USD"
}

Do similar normalization for:

dates
percentages
ratios
durations
currencies

---

7. Detect recurring headers and footers

Large documents often contain repeating template text.

Detect repeated page-level headers/footers and flag them separately.

They must not dominate semantic matching.

For example:

CONFIDENTIAL
Company Name
Quarterly Report
Page 182

should not create hundreds of false changes after a template update.

Preserve them for presentation/style comparison, but exclude or heavily downweight them in semantic content alignment.

---

8. Matching pipeline

Implement matching as an escalation/cascade.

Do NOT use the LLM on everything.

Pipeline:

Stage 1: exact normalized hash
Stage 2: near-duplicate matching
Stage 3: lexical candidate retrieval
Stage 4: anchors/structural evidence
Stage 5: sequence/context alignment
Stage 6: LLM candidate adjudication
Stage 7: global unmatched-content recovery
Stage 8: split/merge resolution

---

9. Exact matching

For every normalized block compute a stable hash such as SHA-256.

If:

hash(old_block) == hash(new_block)

mark the blocks as:

UNCHANGED

without calling an LLM.

Cache hashes.

---

10. Near-duplicate detection

Implement lightweight near-duplicate detection.

Potential techniques:

word shingles
Jaccard similarity
MinHash
SimHash
SequenceMatcher where appropriate

Do not introduce unnecessary heavy infrastructure.

Use this layer to detect content where only a small amount changed.

Example:

OLD:
Borrower shall submit statements within 90 days.

NEW:
Borrower shall submit statements within 60 days.

These should be trivially recognized as corresponding blocks before involving an LLM.

---

11. Lexical retrieval

Because no embedding model should be assumed, implement lexical candidate retrieval.

Use BM25 or an equivalent inverted-index retrieval mechanism.

Candidate retrieval must work over:

normalized text
headings
section context
rare terms
entities
numbers
dates
table headers

For each unmatched old block, retrieve only the top K possible blocks from the new document.

K should be configurable.

Suggested initial value:

K = 5

Do not compare every old block to every new block.

Avoid O(N × M) behavior.

---

12. Anchor extraction

Extract deterministic anchors from blocks.

Examples:

numbers
dates
currencies
percentages
ratios
named entities where available
capitalized/defined terms
IDs
account numbers
clause references
property names
organization names
rare phrases
table headers

Create an inverted anchor index.

Rare shared anchors should significantly improve candidate ranking.

Example:

DSCR
1.25x
$37,450,000
September 30, 2031

are highly useful alignment clues.

---

13. Acronym and terminology handling

Support terminology changes such as:

Debt Service Coverage Ratio ↔ DSCR
Net Operating Income ↔ NOI
Property ↔ Asset

Initially create:

- deterministic abbreviation detection where easy
- document-specific acronym dictionary

LLM may be used to infer additional terminology equivalences when necessary.

Cache these mappings per document pair.

---

14. Coarse-to-fine alignment

Do not begin with unrestricted paragraph matching across an entire 2,000-page document.

Perform alignment at multiple levels:

document
→ coarse region
→ section
→ subsection
→ block
→ sentence / field / table cell

However, do NOT assume sections remain identical between versions.

Section hierarchy is evidence, not identity.

Support severe restructuring.

---

15. Section signatures

Generate compact signatures for sections.

Start deterministically using:

title
frequent/rare terms
numbers
entities
table schemas
block types
length

For difficult sections, optionally use a cheap LLM to generate a semantic signature such as:

{
  "topics": [
    "financial covenants",
    "liquidity",
    "DSCR"
  ],
  "entities": [
    "Borrower",
    "Lender"
  ],
  "key_facts": [
    "minimum DSCR requirement",
    "minimum liquidity requirement"
  ]
}

Treat LLM-generated signatures as evidence only.

Do NOT assume identical generated text means guaranteed equivalence.

---

16. LLM candidate reranking

For unresolved content, retrieve top-K candidates first.

Then call the LLM using "tachyon/llm_client.py".

Do NOT give the LLM an entire giant document.

The LLM should receive something like:

OLD BLOCK

...

CANDIDATE A
...

CANDIDATE B
...

CANDIDATE C
...

Ask it to return strict structured output.

Example schema:

{
  "best_candidate_id": "new_b_182",
  "relationship": "MODIFIED",
  "confidence": 0.96,
  "reason": "Both clauses define the same reporting obligation but the deadline changed."
}

Allowed relationships:

EXACT
SEMANTICALLY_EQUIVALENT
MODIFIED
UNRELATED
UNCERTAIN

The prompt must explicitly tell the LLM to ignore:

page numbers
section numbering
formatting
font
layout
position
template differences

when deciding semantic correspondence.

---

17. Sequence alignment / order prior

Use document order as a soft prior.

If:

old blocks 100–150

mostly correspond to:

new blocks 300–350

nearby matches should receive a boost.

Use an order-aware alignment algorithm/dynamic programming strategy where useful.

Conceptually:

OLD:
A B C D E F

NEW:
A B X C E F

should become:

A = A
B = B
X = ADDED
C = C
D = REMOVED
E = E
F = F

Do not enforce strict monotonicity because sections may move.

---

18. Global unmatched-content pass

After local/ordered alignment, collect:

all unmatched old regions
all unmatched new regions

Run a second global matching pass.

Purpose:

Detect content that has moved far away in the document.

Example:

old page 30
→
new page 480

If the same/equivalent content is found elsewhere, classify it as:

MOVED

not:

REMOVED + ADDED

If it changed during relocation:

MOVED_AND_MODIFIED

---

19. Support split and merge relationships

Do not restrict the alignment model to 1:1 mappings.

Support:

1 → 1
1 → N
N → 1
N → M where needed

Examples:

one old paragraph
→
three new bullet points

or:

three old clauses
→
one new consolidated clause

Add relationship types:

SPLIT
MERGED
SPLIT_AND_MODIFIED
MERGED_AND_MODIFIED

Use a stronger LLM only when deterministic/contextual evidence is insufficient.

---

20. Alignment graph

Represent correspondence independently from the final diff.

Create something conceptually like:

AlignmentEdge:
    id
    old_block_ids: list[str]
    new_block_ids: list[str]
    relationship
    confidence
    matching_evidence

Possible relationships:

UNCHANGED
SEMANTICALLY_EQUIVALENT
MODIFIED
MOVED
MOVED_AND_MODIFIED
ADDED
REMOVED
SPLIT
MERGED
SPLIT_AND_MODIFIED
MERGED_AND_MODIFIED
UNCERTAIN

This alignment graph should be the central intermediate representation.

---

21. Deterministic atomic diff

After content is aligned, calculate exact differences without depending on an LLM.

For text identify:

inserted words
deleted words
replaced words
sentence additions
sentence removals
number changes
date changes
percentage changes
currency changes
entity changes
condition changes where structurally obvious

Use an appropriate sequence-diff algorithm.

Preserve exact offsets where possible.

Example:

OLD:
within 90 days

NEW:
within 60 days

Output:

{
  "type": "VALUE_CHANGED",
  "old_value": "90 days",
  "new_value": "60 days"
}

---

22. Separate semantic and presentation changes

Every aligned unit should have two dimensions.

Example:

{
  "semantic_status": "UNCHANGED",
  "presentation_status": "MOVED_AND_REFORMATTED"
}

Semantic statuses:

UNCHANGED
EQUIVALENT_REWRITE
MODIFIED
ADDED
REMOVED
SPLIT
MERGED

Presentation statuses:

UNCHANGED
REFORMATTED
MOVED
RENUMBERED
RESTYLED
LAYOUT_CHANGED
TABLE_STRUCTURE_CHANGED

This is essential.

A complete template redesign must not generate thousands of meaningful semantic changes.

---

23. Tables

Tables need a separate comparison pipeline.

Do not flatten a table and feed the entire thing into an LLM.

Perform:

table detection
→ table candidate matching
→ column/schema alignment
→ row matching
→ cell comparison

Column names may change:

Property → Asset
NOI → Net Operating Income

Use deterministic normalization first.

Use an LLM only to resolve ambiguous column mappings.

Identify:

added rows
removed rows
changed rows
added columns
removed columns
renamed columns
changed cells

Output structured table deltas.

Example:

{
  "table_id": "t17",
  "changed_rows": [
    {
      "row_key": "Park Avenue",
      "changes": [
        {
          "column": "NOI",
          "old": 3200000,
          "new": 3480000
        }
      ]
    }
  ]
}

Every changed cell should preserve source page/bbox information if available.

---

24. LLM semantic interpretation

Only after deterministic differences have been produced should a stronger LLM interpret the significance.

Input example:

OLD
Borrower shall provide financial statements within 90 days.

NEW
Borrower shall provide audited financial statements within 60 days.

DETERMINISTIC CHANGES
- inserted word: audited
- duration changed: 90 days → 60 days

Expected structured response:

{
  "materiality": "MATERIAL",
  "change_categories": [
    "requirement_strengthened",
    "deadline_shortened"
  ],
  "summary": "The reporting obligation became stricter: audited statements are now required and the deadline was reduced by 30 days."
}

The summary must be grounded strictly in the supplied evidence.

Do not allow the LLM to invent unsupported changes.

---

25. Confidence handling

Confidence should mostly refer to:

alignment confidence
semantic classification confidence

The deterministic word/value difference itself should not need an arbitrary AI confidence score.

Low-confidence alignments should be flagged:

NEEDS_REVIEW

Make thresholds configurable.

Example:

>= 0.90 auto-accept
0.70–0.90 accept but mark moderate confidence
< 0.70 needs review

Do not hard-code these until evaluated.

---

26. Performance and scalability

The solution must work for large documents.

Assume potentially:

1000–2000+ pages
tens of thousands of blocks
hundreds of tables
major document restructuring

Do not implement O(N × M) pairwise matching.

Use:

hash indexes
inverted lexical indexes
anchor indexes
candidate retrieval
hierarchical narrowing
caching
batching
parallel processing where safe

Architecture should support section/region-level parallelism.

---

27. Caching

Cache expensive derived information using content hashes.

Examples:

normalized block
block hash
MinHash/SimHash
anchor extraction
LLM semantic signature
LLM candidate decision
table schema

If the exact same block occurs across document versions, do not recompute its derived representation.

Design the cache so future version comparisons can reuse work.

For:

V1 → V2
V2 → V3
V3 → V4

the system should be increasingly incremental.

---

28. LLM batching

Do not call the LLM once per paragraph where batching is safe.

For related candidate comparisons, batch several items.

Example:

[
  {
    "old_id": "o17",
    "candidates": [...]
  },
  {
    "old_id": "o18",
    "candidates": [...]
  }
]

Require strict JSON/structured responses.

Keep batches contextually coherent.

Do not mix arbitrary regions across the document into one enormous prompt.

---

29. Error isolation

A failure comparing one section must not fail the entire document-comparison job.

Implement clear stages/statuses.

Example:

PARSING
NORMALIZING
MATCHING_EXACT
MATCHING_NEAR_DUPLICATE
RETRIEVING_CANDIDATES
ALIGNING
DIFFING
INTERPRETING
COMPLETE
FAILED_PARTIAL
FAILED

Persist intermediate results where appropriate.

Allow retries for:

individual LLM batches
individual pages
individual sections
individual tables

---

30. Output schema

Design a clean structured result.

Rough example:

{
  "comparison_id": "...",
  "old_document": "...",
  "new_document": "...",

  "summary": {
    "semantic_changes": 47,
    "added": 8,
    "removed": 6,
    "modified": 28,
    "moved_and_modified": 5,
    "equivalent_rewrites": 73,
    "presentation_only_changes": 18311
  },

  "changes": [
    {
      "id": "change_001",

      "semantic_status": "MODIFIED",
      "presentation_status": "MOVED",

      "alignment_confidence": 0.98,

      "old_sources": [
        {
          "page": 71,
          "bbox": [100, 200, 500, 250],
          "text": "..."
        }
      ],

      "new_sources": [
        {
          "page": 124,
          "bbox": [80, 300, 480, 360],
          "text": "..."
        }
      ],

      "atomic_changes": [
        {
          "type": "VALUE_CHANGED",
          "old": "90 days",
          "new": "60 days"
        }
      ],

      "semantic_summary": "...",

      "needs_review": false
    }
  ]
}

---

31. Diff/review UI

Build a review-friendly UI if the repository has an existing frontend/UI framework.

Do not create an isolated toy UI if the repository already has established frontend patterns.

Inspect and follow existing conventions.

The primary experience should be:

LEFT PANEL
change navigator / hierarchy

CENTER LEFT
old document

CENTER RIGHT
new document

BOTTOM OR RIGHT DETAIL PANEL
selected change explanation

Main layout:

┌──────────────┬──────────────────────┬──────────────────────┐
│ Changes      │ OLD DOCUMENT         │ NEW DOCUMENT         │
│              │                      │                      │
│ Summary      │ page / region        │ page / region        │
│ Added        │ highlighted source   │ highlighted source   │
│ Removed      │                      │                      │
│ Modified     │                      │                      │
│ Moved        │                      │                      │
│ Tables       │                      │                      │
│ Review       │                      │                      │
└──────────────┴──────────────────────┴──────────────────────┘

---

32. UI filters

Support filters such as:

All meaningful changes
Added
Removed
Modified
Moved
Moved + modified
Equivalent rewrite
Tables
Numbers
Dates
Formatting
Low confidence
Needs review

Default behavior:

Hide presentation-only noise
Hide equivalent rewrites if desired
Prioritize meaningful semantic changes

Users must be able to turn these back on.

---

33. Change hierarchy

For very large documents do not present one flat list of thousands of changes.

Create a hierarchy such as:

All Changes
├── Executive Summary
├── Financial Information
│   ├── Revenue
│   ├── Expenses
│   └── Covenants
├── Property Information
├── Risk Factors
└── Appendices

Show counts per section.

---

34. Source synchronization

When a user clicks a change:

- navigate old document to the old source
- navigate new document to the new source
- highlight both corresponding regions

If content moved:

old page 28 → new page 417

show it explicitly as:

MOVED
Page 28 → Page 417

Do not show it as a misleading unrelated deletion/addition pair.

---

35. Visual connectors

Where practical, visually indicate correspondence between old and new content.

For example, use a subtle connector or correspondence indication between the highlighted old and new regions.

This is especially useful when the document template or section structure changed heavily.

---

36. Change detail card

When a change is selected, show something like:

MODIFIED
Alignment confidence: 97%

Old:
Financial statements within 90 days

New:
Audited financial statements within 60 days

Detected atomic changes:
- "audited" added
- 90 days → 60 days

Interpretation:
Reporting obligation became stricter.

Evidence:
Old page 71
New page 124

The interpretation must always be accompanied by visible source evidence.

---

37. Large-table UI

For changed tables, provide a specialized view.

Example:

TABLE: Property Operating Results

Rows changed: 18
Rows added: 3
Rows removed: 2
Cells changed: 42

[Show changed rows only]

Then:

Property      Field          Old          New

Park Avenue   NOI            $3.20M       $3.48M
Park Avenue   Occupancy      91.2%        93.8%
West Plaza    Revenue        $8.10M       $7.74M

Clicking a row/cell should jump to its source in both versions where possible.

---

38. Important LLM prompts

Create dedicated prompt templates rather than one giant general prompt.

At minimum:

section_matcher
block_candidate_reranker
semantic_equivalence_classifier
split_merge_resolver
semantic_change_interpreter
terminology_mapper
table_column_mapper

Store prompts in maintainable dedicated files/modules.

Do not scatter long prompt strings throughout business logic.

Every LLM response should preferably use structured output validated with Pydantic or equivalent.

---

39. Candidate reranker prompt behavior

The candidate reranker must be instructed:

Determine whether any candidate represents the same logical content as OLD.

Ignore:
- template
- position
- page
- heading numbering
- visual formatting
- paragraph/list conversion

Pay attention to:
- subject
- action
- object
- condition
- numbers
- dates
- obligations
- exceptions
- scope
- entities
- relationships

Return the best matching candidate or NONE.

---

40. Semantic change interpreter prompt behavior

It must receive deterministic evidence.

Instruct it:

Do not infer changes not supported by the supplied old text, new text, and deterministic atomic diff.

Describe:
1. what changed
2. whether meaning changed
3. important consequences directly evident from the text

Do not speculate.

---

41. Evaluation framework

Build tests/evaluation utilities.

We need to measure the system itself, not merely whether it runs.

Important metrics:

Candidate Recall@1
Candidate Recall@5
Alignment precision
Alignment recall
Moved-content detection accuracy
Added-content precision/recall
Removed-content precision/recall
Split/merge accuracy
Atomic diff accuracy
Table-cell diff accuracy

Most important retrieval metric:

Candidate Recall@K

If the correct corresponding block never reaches the LLM candidate list, the LLM cannot recover it.

Create synthetic and real test cases involving:

1. exact copies
2. formatting-only changes
3. page-number changes
4. renumbered sections
5. moved paragraphs
6. moved sections
7. rewritten-but-equivalent text
8. small semantic modifications
9. number changes
10. additions
11. removals
12. split paragraphs
13. merged paragraphs
14. renamed headings
15. reordered tables
16. renamed table columns
17. added/removed table rows
18. changed table cells
19. scanned PDFs
20. hybrid PDFs
21. complete template redesign

---

42. Logging and observability

Add useful structured logging.

For each stage record:

number of blocks
number exact-matched
number near-matched
number sent to BM25
candidate count
number sent to LLM
LLM batch count
token/cost information if exposed by llm_client
number low-confidence
number added/removed
processing duration

This will be essential when evaluating very large documents.

---

43. Initial implementation strategy

Do not attempt every advanced feature in one huge change.

Implement in clean phases while keeping the architecture extensible.

Recommended order:

Phase 1

PDF ingestion
digital/scanned page routing
canonical blocks
normalization
exact hashing
BM25
basic 1:1 LLM reranking
deterministic text diff
basic structured output

Phase 2

near-duplicate matching
anchor index
hierarchical/coarse alignment
global moved-content recovery

Phase 3

split/merge support
alignment graph
semantic change interpretation
confidence/review logic

Phase 4

table matching
column mapping
row/cell diff

Phase 5

review UI
side-by-side navigation
filters
change hierarchy
moved-content navigation
table diff UI

Phase 6

caching
parallelism
incremental version comparison
performance benchmarking
large-document hardening

However, design the core interfaces from the beginning so later phases do not require rewriting the entire system.

---

44. Important constraints

Do NOT:

- send both complete large documents to an LLM
- implement an O(N²) all-block comparison
- assume page N corresponds to page N
- assume section numbering remains stable
- treat moved text as delete + add when a correspondence can be identified
- use an LLM to calculate numeric differences that deterministic code can calculate
- flatten all tables into plain text
- discard bounding boxes/source provenance
- introduce another OCR stack instead of using "ecm"
- introduce another LLM client instead of "tachyon/llm_client.py"
- require an embedding model
- generate thousands of LLM requests for obviously unchanged blocks

---

45. Coding expectations

Before modifying code:

1. inspect the repository structure
2. inspect "tachyon/llm_client.py"
3. inspect OCR functions under "ecm/"
4. inspect existing API/backend patterns
5. inspect existing models/database conventions
6. inspect existing frontend patterns if there is a UI

Reuse existing abstractions whenever sensible.

Keep components modular.

Suggested conceptual modules may include:

document_diff/
    ingestion/
    extraction/
    normalization/
    models/
    fingerprints/
    retrieval/
    anchors/
    alignment/
    llm/
    diff/
    tables/
    interpretation/
    storage/
    evaluation/

Do not force these exact paths if the repository has a better established structure.

Follow repository conventions.

---

46. Deliverables

Implement working code, not just architecture documentation.

At completion provide:

1. architecture summary
2. files created/modified
3. important design decisions
4. how digital PDF extraction works
5. how scanned PDF extraction uses ECM
6. how "tachyon/llm_client.py" is used
7. matching/alignment algorithm
8. LLM prompts introduced
9. structured output schema
10. test/evaluation coverage
11. how to run a document comparison
12. example comparison output
13. known limitations
14. recommended next improvements

Also include a representative end-to-end test comparing documents that contain:

template changes
moved content
one rewritten-equivalent clause
one semantic modification
one addition
one removal
one changed table value

The expected result should distinguish these cases correctly.

---

47. Final guiding principle

The final system should answer four separate questions:

1. What corresponds to what?
       → Alignment engine

2. What exactly changed?
       → Deterministic diff engine

3. What does the change mean?
       → LLM interpretation

4. Where can the reviewer verify it?
       → Page/bbox provenance + review UI

Optimize primarily for:

high recall of real changes
low false-positive noise from template changes
traceability
large-document scalability
human reviewability

The end product should feel like a semantic version of a professional document redline system rather than an LLM summarization demo.