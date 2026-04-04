
hear the problem out. i need to designa prompting style, system or whatever one may call it. the goal is that you extract data from pdf and extract line items and tits values. the things ist htat line items can very a lot. each line item represents an account. my pipeline first extracts text from the tables. often the text at the end may overflow which may need intelligence to righly determine what belongs to which. for each line item, will ahve multiple values - for different periods and chage also given, the goal is to pick the current one alone. after all that is done, json must be prepared to show line items and values with reasoning for why it is picked, the value is picked. there can be negatives, brackets and a lot. the document is an income statement 

Use a two-stage extraction design, not one giant prompt.

Your problem is not just “read a table.” It is actually three separate problems:

reconstruct the row correctly from imperfect PDF text

decide which numeric column is the current-period value

normalize the value and explain why it was chosen

If you force one prompt to do all three at once, it will become fragile.

Recommended architecture

Stage 0: deterministic preprocessing before LLM
Do as much non-LLM cleanup as possible first.

Input to LLM should not be raw PDF text. It should be a structured intermediate table like this:

row_id

raw_left_text

raw_numeric_cells

page

section_header

nearby_rows

indentation level if available

whether row appears bold / total / subsection if parser can infer it

Also run these preprocessing rules before the model sees anything:

merge wrapped text lines when the first line looks like a label and the next line looks like continuation text without its own numbers

preserve original row order

preserve all numeric cells exactly as strings

do not convert brackets or commas too early

detect candidate headers above the table such as:

“Year ended December 31, 2025”

“Three months ended”

“Change”

“% change”

“Variance”

attach the closest header context to each numeric column

This stage should be rule-heavy, because it reduces ambiguity before the LLM.

Stage 1: row reconstruction and account identification
This prompt should only answer:
“What is the correct line item label for this row, and what numbers belong to that row?”

It should not yet choose the current-period value.

What the model should do here:

merge overflowed label text

reject numeric cells that belong to another row

determine whether this is a real account row, subtotal, header, or note row

keep all candidate numeric values attached to the row

Output should look like:

{
  "row_id": "r_17",
  "resolved_line_item": "Selling, general and administrative expenses",
  "row_type": "account",
  "is_subtotal": false,
  "numeric_candidates": [
    {
      "raw_value": "1,245",
      "column_hint": "2025"
    },
    {
      "raw_value": "1,118",
      "column_hint": "2024"
    },
    {
      "raw_value": "11.4%",
      "column_hint": "change"
    }
  ],
  "reasoning": "The label was reconstructed by merging the wrapped continuation line below. The percentage belongs to the change column, not the account value."
}
Stage 2: current-period value selection
This prompt should take the resolved row plus column metadata and decide which numeric candidate is the current value.

This is where most extraction failures happen, so isolate it.

Decision rules the model should follow

Priority order:

choose the value under the most recent reporting period

ignore change / variance / percentage columns

ignore comparative prior-period values unless the latest-period column is absent

prefer actual numeric amount columns over ratios or per-share values unless the row itself is a ratio row

keep sign exactly as implied by the source, including parentheses

Examples:

If columns are 2025, 2024, change %, choose 2025

If columns are Q1 2026, Q1 2025, change, choose Q1 2026

If columns are “Current year”, “Prior year”, choose current year

If the row is “Net income margin”, then percentage may be valid because the line item itself is a ratio, not an account amount

Output should be:

{
  "row_id": "r_17",
  "line_item": "Selling, general and administrative expenses",
  "selected_value": {
    "raw": "1,245",
    "normalized": 1245.0,
    "sign": "positive",
    "unit": "same as statement"
  },
  "selection_basis": {
    "chosen_column": "2025",
    "why_selected": "This is the latest reporting period shown in the table. Other values correspond to prior period and percentage change."
  }
}
Best prompt style

Use a constrained auditor-style prompt, not a general assistant prompt.

System prompt
Use something like this:

You are a financial statement extraction engine.

Your job is to extract income statement line items from imperfectly parsed table text.

Rules:
1. Never invent a line item, value, period, or unit.
2. Use only the supplied table rows and headers.
3. Reconstruct wrapped or overflowed line item labels only when the continuation is strongly supported by row order and formatting context.
4. Treat numeric columns separately from labels.
5. For each row, identify all candidate values first, then select only the current-period value.
6. Ignore percentage change, variance, and prior-period columns unless no current-period amount exists.
7. Preserve negative values exactly. Parentheses indicate negative unless surrounding context clearly shows otherwise.
8. Output strict JSON only.
9. Include concise reasoning tied to source evidence, not vague explanations.
10. If uncertain, mark uncertainty explicitly instead of guessing.
Developer-style instruction for the row selection step
This is the important part:

When selecting the value for a line item:
- choose the amount from the latest reporting period shown in the column headers
- do not choose percentages, changes, or variance values
- do not choose prior-period values when a current-period value exists
- if multiple numeric values appear in one row, map each to its most likely column using header context
- if the row is a subtotal or total, still extract it if it is a valid income statement line
- if the row is a section header or note reference, do not extract it as an account
User payload structure to the model
Do not send only plain text. Send structured context like this:

{
  "statement_type": "income_statement",
  "table_context": {
    "page": 12,
    "title": "Consolidated Statements of Income",
    "column_headers": [
      {"col_id": "c1", "label": "2025"},
      {"col_id": "c2", "label": "2024"},
      {"col_id": "c3", "label": "Change %"}
    ]
  },
  "rows": [
    {
      "row_id": "r1",
      "raw_text_left": "Revenue",
      "raw_numeric_cells": ["10,245", "9,812", "4.4%"]
    },
    {
      "row_id": "r2",
      "raw_text_left": "Selling, general and administrative",
      "raw_numeric_cells": ["1,245", "1,118", "11.4%"]
    },
    {
      "row_id": "r3",
      "raw_text_left": "expenses",
      "raw_numeric_cells": []
    }
  ]
}
Then instruct:

merge row r2 and r3 if appropriate

map numeric values to columns

select only current-period value

return strict JSON

JSON schema you should target

I suggest this schema:

{
  "statement_type": "income_statement",
  "reporting_period_selected": "2025",
  "currency": null,
  "extractions": [
    {
      "row_id": "r1",
      "line_item_raw": "Revenue",
      "line_item_resolved": "Revenue",
      "account_type": "account",
      "current_value": {
        "raw": "10,245",
        "normalized": 10245.0,
        "is_negative": false
      },
      "source_columns_considered": [
        {"label": "2025", "value": "10,245"},
        {"label": "2024", "value": "9,812"},
        {"label": "Change %", "value": "4.4%"}
      ],
      "reasoning": "Selected the 2025 amount because it is the most recent reporting period. Excluded 2024 as prior period and 4.4% as change percentage.",
      "confidence": 0.98
    }
  ],
  "warnings": [
    "Some row labels were reconstructed from wrapped text."
  ]
}
How to handle negatives and formatting

Use a normalization layer after the model, not only inside the model.

Rules:

(1,245) → -1245

1,245 → 1245

-1,245 → -1245

1.2% should remain percentage and should not be treated as an amount

— or - alone may mean missing, not negative

footnote markers like 1,245(1) or 1,245[a] should be stripped after preserving the original raw string

Keep both:

raw value

normalized value

That is important for auditability.

How to make it resilient

Use chunked table reasoning
Do not send the whole annual report unless needed. Send one detected table at a time.

Force candidate enumeration before selection
The model should first list all numeric candidates for a row, then choose one. This reduces random wrong picks.

Separate reasoning from final output
Internally ask for reasoning, but in output keep it concise and evidence-based.

Use a validator after LLM
After JSON is returned, validate:

exactly one current value selected per extracted row

selected value exists among candidates

selected value is not from a change column

normalized number matches raw format

no hallucinated rows

Retry only on narrow failures
If validation fails, do not rerun the full table blindly. Re-prompt only for:

row reconstruction

column mapping

current-period selection

This is much more stable.

Good extraction strategy for overflowed labels

Have the model use these heuristics:

Merge adjacent row text when:

second row has no numeric values

second row is left-aligned similarly

combined phrase forms a plausible income statement account

neighboring rows suggest it is a continuation, not a new section

Do not merge when:

second row is bold section header

second row starts a new semantic category

second row has its own numeric values

merge would create an unnatural label

This should be explicit in the prompt.

A strong prompt pattern

Use this exact flow:

Prompt A: reconstruct rows

Task:
For each row, determine whether it is:
- account
- subtotal
- total
- section_header
- note
- continuation

If a row is continuation text for the previous row, merge it into the previous row label.
Do not yet choose the current-period value.
Return all candidate numeric cells with likely column labels.
Return strict JSON only.
Prompt B: choose current-period value

Task:
Using the resolved rows and the column headers, select exactly one current-period value for each extractable income statement line item.

Selection rules:
- choose the latest reporting period amount
- exclude prior-period values
- exclude change and variance columns
- preserve negative sign from parentheses or minus
- if no valid current-period amount exists, mark unresolved

Return strict JSON only.
What not to do

Do not ask the model:

“extract the income statement as JSON”
That is too vague.

Do not ask it:

“figure out the values and line items intelligently”
That causes hidden reasoning drift.

Do not ask for long freeform explanations.
Ask for short evidence-based reasoning tied to headers and row structure.

My strongest recommendation

Design this as a state machine:

table detected

rows reconstructed

row typed

candidates mapped to columns

current-period value selected

normalized

validated

That is better than a single prompt and better than repeated “cleaning prompts.”

A practical minimal version

If you want a first implementation quickly, use:

deterministic preprocessor

one LLM prompt for row reconstruction + candidate mapping

one LLM prompt for current-period selection

one code validator for normalization and sanity checks

That is enough to get a strong version working.

I can draft the actual production-grade system prompt, extraction prompt, and JSON schema next.


give a flow and if llm is involved, give the prompt 

Below is a practical extraction flow for your income statement pipeline, followed by prompt templates you can directly use.

Overall flow

PDF table extraction
Your parser extracts table text into row-wise structure. Do not send raw PDF text directly to the LLM unless necessary.

Input at this stage should ideally contain:

page number

table title

column headers

row order

left text cell

numeric cells

nearby rows

any formatting hints if available such as indentation, bold, subtotal markers

Pre-LLM cleanup
Do lightweight deterministic cleanup before using the LLM.

Do:

preserve row order

preserve all raw numeric strings exactly

attach detected column headers to numeric columns

detect rows with no numbers that may be overflow continuations

detect obvious non-data rows such as blank rows, repeated headers, footers

Do not:

normalize signs too early

drop brackets

convert percentages into numbers

merge rows aggressively using only rules

LLM Step 1: row reconstruction and row typing
This step fixes overflow issues and identifies what each row is.

Goal:

reconstruct the full line item label

decide whether a row is an account, subtotal, total, section header, note, continuation, or noise

keep all candidate numeric values for that row

do not yet select the current-period value

LLM Step 2: current-period value selection
This step decides which number is the one you want.

Goal:

map each numeric value to a column

identify which column is current period

pick exactly one value for each extracted line item

reject change columns, prior-period columns, percentages, and variance columns

Post-LLM normalization
Convert the chosen raw value into a machine-safe normalized value.

Examples:

1,245 -> 1245

(1,245) -> -1245

-1,245 -> -1245

— -> null

12.5% should stay percentage and should not become account amount unless the row itself is a ratio row

Validation layer
Run checks after the LLM.

Validate:

every chosen value exists among row candidates

chosen column is not change or variance

exactly one current value per extracted row

negative normalization matches raw formatting

no hallucinated rows

reasoning references actual evidence from the supplied input

Final JSON output
Produce:

statement metadata

selected reporting period

extracted line items

raw value

normalized value

concise reasoning

confidence

warnings if ambiguity remains

Recommended pipeline design

Use three layers:

deterministic parser/preprocessor

LLM for ambiguity resolution

deterministic validator/normalizer

This is the most stable design.

Flow diagram

You can think of the pipeline like this:

PDF
-> Table parser
-> Structured intermediate rows
-> Pre-cleaning and header detection
-> LLM Prompt 1: reconstruct rows
-> LLM Prompt 2: choose current-period value
-> Value normalization
-> Validation
-> Final JSON

Structured intermediate format

Before calling the LLM, create an object like this:

{
  "statement_type": "income_statement",
  "page": 12,
  "table_title": "Consolidated Statements of Income",
  "column_headers": [
    {"col_id": "c1", "label": "2025"},
    {"col_id": "c2", "label": "2024"},
    {"col_id": "c3", "label": "Change %"}
  ],
  "rows": [
    {
      "row_id": "r1",
      "left_text": "Revenue",
      "numeric_cells": ["10,245", "9,812", "4.4%"]
    },
    {
      "row_id": "r2",
      "left_text": "Selling, general and administrative",
      "numeric_cells": ["1,245", "1,118", "11.4%"]
    },
    {
      "row_id": "r3",
      "left_text": "expenses",
      "numeric_cells": []
    }
  ]
}
Prompting system

Use two LLM prompts, not one.

Prompt 1 is for reconstruction.
Prompt 2 is for selection.

That separation makes the system much more reliable.

SYSTEM PROMPT FOR STEP 1

You are a financial statement extraction engine.

Your task is to reconstruct line items from imperfectly parsed income statement table rows.

Rules:
1. Use only the provided input.
2. Never invent line items, periods, or values.
3. Preserve row order.
4. A row may be one of:
   - account
   - subtotal
   - total
   - section_header
   - note
   - continuation
   - noise
5. If a row is a continuation of the previous row label, merge it with the previous row label.
6. A continuation row usually has no numeric cells and extends the meaning of the prior line item.
7. Do not yet select the current-period value.
8. Keep all candidate numeric values attached to the resolved row.
9. Return strict JSON only.
10. Reasoning must be short and based only on row structure, nearby context, and column layout.
USER PROMPT FOR STEP 1

Task:
Reconstruct the rows of this income statement table.

For each input row:
- determine the row type
- detect whether it continues the previous row
- produce a resolved line item label where appropriate
- attach all candidate numeric cells to the resolved row
- do not choose the current-period value yet

Input:
{{STRUCTURED_TABLE_JSON}}

Return JSON in exactly this format:

{
  "statement_type": "income_statement",
  "resolved_rows": [
    {
      "source_row_ids": ["r1"],
      "row_type": "account",
      "line_item_raw": "Revenue",
      "line_item_resolved": "Revenue",
      "numeric_candidates": [
        {
          "raw_value": "10,245",
          "column_hint": "2025"
        },
        {
          "raw_value": "9,812",
          "column_hint": "2024"
        },
        {
          "raw_value": "4.4%",
          "column_hint": "Change %"
        }
      ],
      "reasoning": "Single complete row with amount columns and a change column."
    },
    {
      "source_row_ids": ["r2", "r3"],
      "row_type": "account",
      "line_item_raw": "Selling, general and administrative | expenses",
      "line_item_resolved": "Selling, general and administrative expenses",
      "numeric_candidates": [
        {
          "raw_value": "1,245",
          "column_hint": "2025"
        },
        {
          "raw_value": "1,118",
          "column_hint": "2024"
        },
        {
          "raw_value": "11.4%",
          "column_hint": "Change %"
        }
      ],
      "reasoning": "Second row has no numbers and completes the previous label."
    }
  ],
  "warnings": []
}
Expected output from Step 1

{
  "statement_type": "income_statement",
  "resolved_rows": [
    {
      "source_row_ids": ["r1"],
      "row_type": "account",
      "line_item_raw": "Revenue",
      "line_item_resolved": "Revenue",
      "numeric_candidates": [
        {"raw_value": "10,245", "column_hint": "2025"},
        {"raw_value": "9,812", "column_hint": "2024"},
        {"raw_value": "4.4%", "column_hint": "Change %"}
      ],
      "reasoning": "Single complete row."
    },
    {
      "source_row_ids": ["r2", "r3"],
      "row_type": "account",
      "line_item_raw": "Selling, general and administrative | expenses",
      "line_item_resolved": "Selling, general and administrative expenses",
      "numeric_candidates": [
        {"raw_value": "1,245", "column_hint": "2025"},
        {"raw_value": "1,118", "column_hint": "2024"},
        {"raw_value": "11.4%", "column_hint": "Change %"}
      ],
      "reasoning": "Merged wrapped label."
    }
  ],
  "warnings": []
}
SYSTEM PROMPT FOR STEP 2

You are a financial statement extraction engine.

Your task is to select exactly one current-period value for each valid income statement line item.

Rules:
1. Use only the provided resolved rows and column headers.
2. Never invent values or periods.
3. Select the value from the latest reporting period shown.
4. Exclude prior-period values when a current-period value exists.
5. Exclude percentage change, variance, and other comparison columns.
6. Preserve the raw selected value exactly as written.
7. If the selected raw value uses parentheses, treat it as negative unless context clearly shows otherwise.
8. If the row is not a valid extractable line item, mark it as not selected.
9. Return strict JSON only.
10. Reasoning must be concise and refer to the chosen column and excluded columns.
USER PROMPT FOR STEP 2

Task:
For each resolved income statement row, select exactly one current-period value.

Selection rules:
- choose the latest reporting period amount
- do not choose prior-period values
- do not choose percentages, changes, or variance values
- preserve negative signs exactly
- if a row is not extractable, explain why

Input:
{{RESOLVED_ROWS_JSON}}

Return JSON in exactly this format:

{
  "statement_type": "income_statement",
  "selected_reporting_period": "2025",
  "extractions": [
    {
      "source_row_ids": ["r1"],
      "line_item": "Revenue",
      "selected": true,
      "selected_value": {
        "raw": "10,245",
        "column": "2025"
      },
      "excluded_values": [
        {
          "raw": "9,812",
          "column": "2024",
          "reason": "prior period"
        },
        {
          "raw": "4.4%",
          "column": "Change %",
          "reason": "change column"
        }
      ],
      "reasoning": "Selected 2025 because it is the latest reporting period and an amount column."
    }
  ],
  "warnings": []
}
Post-LLM normalization prompt is not needed
Do not use the LLM for basic numeric normalization unless your data is extremely irregular. Code should do it better.

Use code rules like this:

Normalization rules

Trim spaces

Preserve raw string

Detect null-like values:

""

"-"

"—"

"–"

"na"

"n/a"

Detect percentages

if ends with %, mark as percentage

Detect negatives

starts with -

enclosed in parentheses

Remove commas and footnote markers
Examples:

"(1,245)" -> -1245

"1,245(1)" -> 1245

"(1,245.50)" -> -1245.50

Final output schema

{
  "statement_type": "income_statement",
  "selected_reporting_period": "2025",
  "extractions": [
    {
      "source_row_ids": ["r1"],
      "line_item": "Revenue",
      "current_value": {
        "raw": "10,245",
        "normalized": 10245.0,
        "is_negative": false
      },
      "reasoning": "Selected 2025 amount as current period. Excluded 2024 as prior period and 4.4% as change."
    },
    {
      "source_row_ids": ["r2", "r3"],
      "line_item": "Selling, general and administrative expenses",
      "current_value": {
        "raw": "1,245",
        "normalized": 1245.0,
        "is_negative": false
      },
      "reasoning": "Merged wrapped label and selected 2025 amount as current period."
    }
  ],
  "warnings": []
}
Recommended orchestration logic

Use this exact control flow:

Parse PDF table

Build structured row JSON

Run Prompt 1

Check Step 1 output

valid JSON

no invented row ids

numeric candidates preserved

Run Prompt 2

Check Step 2 output

selected raw value must exist in candidate list

selected column must not be change/variance

Normalize with code

Emit final JSON

When to retry the LLM

Retry only for narrow failures.

Retry Step 1 if:

row merges are clearly wrong

labels are incomplete

rows are mis-typed

Retry Step 2 if:

chosen column is percentage/change

chosen value does not exist in candidates

prior-year chosen instead of current-year

Do not rerun the whole pipeline for a small failure.

Optional stronger Step 1 prompt
If your PDF extraction is especially messy, add nearby row context.

You can enrich each row like this:

{
  "row_id": "r2",
  "left_text": "Selling, general and administrative",
  "numeric_cells": ["1,245", "1,118", "11.4%"],
  "previous_row_left_text": "Revenue",
  "next_row_left_text": "expenses"
}
Then tell the model:

use previous and next row only as structural context

do not borrow values from neighbors unless continuation is certain

One-prompt fallback
If you must do it in one LLM call, use this. It is weaker than the two-step design, but workable.

SYSTEM PROMPT

You are a financial statement extraction engine.

Your task is to extract valid income statement line items from imperfectly parsed table rows.

Rules:
1. Use only the provided input.
2. Never invent rows, values, or periods.
3. Merge continuation rows only when strongly supported by structure.
4. For each resolved line item, identify all candidate numeric values.
5. Select exactly one current-period value from the latest reporting period amount column.
6. Exclude prior-period values, percentages, changes, and variance columns.
7. Preserve the raw selected value exactly.
8. Return strict JSON only.
USER PROMPT

Extract line items and current-period values from this income statement table.

Input:
{{STRUCTURED_TABLE_JSON}}

Return JSON in exactly this format:

{
  "statement_type": "income_statement",
  "selected_reporting_period": "",
  "extractions": [
    {
      "source_row_ids": [],
      "line_item": "",
      "numeric_candidates": [
        {"raw_value": "", "column_hint": ""}
      ],
      "selected_value": {
        "raw": "",
        "column": ""
      },
      "reasoning": ""
    }
  ],
  "warnings": []
}
But again, the two-step version is much better.

Best practical advice

Use the LLM only where ambiguity exists:

overflowed labels

row typing

current-period selection when multiple columns exist

Use code for:

parsing

normalization

validation

schema enforcement

That split will give you the most resilient system.

I can next give you:

a production-grade master prompt set with stricter wording

a JSON schema for validation

pseudocode for the full orchestration in Python


does it consider the fact that row may spill over to the next one while reading 

Yes. The design explicitly handles row spillover, but only in Step 1 (row reconstruction). That step is responsible for detecting and merging continuation rows before any value selection happens.

What ensures spillover is handled

Structural signal used by the prompt
The model is instructed to treat a row as a continuation when:

it has no numeric cells

it follows a row with numbers

the combined text forms a valid financial account name

alignment/position is similar to the previous row

next rows do not contradict the merge

Explicit rule in the system prompt
This is the key instruction:

“a continuation row usually has no numeric cells and extends the meaning of the prior line item”

Output schema enforces merging
You are not allowing the model to ignore this. It must output:

source_row_ids: ["r2", "r3"]
This forces it to explicitly merge rows when needed.

Separation of concerns
You do NOT select values until after merging is done. This prevents:

picking wrong numbers due to misaligned rows

attaching values to incomplete labels

Why this is important

If you skip this step, typical failures are:

“Selling, general and administrative” treated as one row

“expenses” treated as another row

values attached only to first half

second row ignored or misclassified

This is exactly the PDF spillover issue you described.

How to make spillover handling stronger

You can tighten Step 1 with stricter rules.

Add this to the system prompt for Step 1:

Continuation detection rules:

Treat a row as continuation of the previous row if ALL of the following are true:
1. The row has no numeric values.
2. The previous row has numeric values.
3. The text is semantically incomplete on its own or clearly completes the previous label.
4. The row position suggests same indentation or alignment.

Do NOT merge if:
- the row has its own numeric values
- the row is a section header (e.g., "Operating Expenses")
- the row is visually distinct (all caps, bold header, etc. if hinted)
- merging creates an unnatural or redundant label
Optional stronger input (recommended)

If your parser allows, pass adjacency context:

{
  "row_id": "r3",
  "left_text": "expenses",
  "numeric_cells": [],
  "previous_row": {
    "left_text": "Selling, general and administrative",
    "has_numbers": true
  },
  "next_row": {
    "left_text": "Operating income",
    "has_numbers": true
  }
}
Then instruct:

“Use previous and next row only to decide continuation. Do not borrow values across rows.”

Edge cases to handle

Multi-line labels spanning more than 2 rows
Example:

row1: “Other comprehensive”

row2: “income (loss), net of”

row3: “tax”

Your design supports this because:

continuation can chain across multiple rows

source_row_ids can be ["r1","r2","r3"]

Subtotal followed by continuation-like text
Example:

row1: “Total operating expenses”

row2: “(excluding depreciation)”

Do NOT merge if:

second row is explanatory, not label continuation

You can refine rule:

“Do not merge if the second row is parenthetical explanation rather than part of the core account name.”

Broken rows with misplaced numbers
Example:

row1: label

row2: numbers only

Your current prompt does not yet fix this. If this occurs in your data, add:

If a row contains numeric values but no meaningful label, check if it belongs to the previous row and merge accordingly.
Do this only if your parser produces such splits.

Quick summary

Yes, your pipeline handles spillover because:

spillover resolution is a dedicated step

continuation detection is explicitly instructed

merging is enforced via schema

value selection happens only after merging

If you want maximum robustness, strengthen:

continuation rules

adjacency context

validator checks (e.g., no orphan rows without labels)

If needed, I can give a “hard-mode” prompt that handles messy SEC filings where rows break across pages and columns.




