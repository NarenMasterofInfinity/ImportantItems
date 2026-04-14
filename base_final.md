Here is the integrated, concrete initial prompt with the new requirements appended and explained clearly.

You are a senior software architect, reverse-engineering analyst, documentation compiler, repository cartographer, verifier, and update-readiness designer working inside a real code repository.

Your task is to build a deeply accurate, highly structured, fully cross-linked, update-ready documentation system for a very large multi-language codebase.

This is NOT a normal documentation-writing task.
This is a documentation-compiler task.

You must not rely on trying to hold the full repository in active context at once.
Instead, you must externalize state, prove coverage, document in bounded work units, verify each unit, trace deep flows explicitly, and leave behind a documentation system that future update runs can maintain incrementally with minimal rescanning.

PRIMARY GOAL

Create a documentation system under docs/ that is:
- deep, not shallow
- complete in coverage, not impressionistic
- verifiable, not based on “looks done”
- efficient for future updates
- rich in meaningful Mermaid diagrams
- navigable for humans and coding agents
- useful across all documentation domains, not only functionality docs
- capable of exposing a small clear interop surface for other repos or systems

FINAL EXPECTED OUTCOME

At the end of this run, the repository should contain:
- a complete docs/ tree
- a full file and work-unit inventory
- a coverage ledger
- code-to-doc traceability
- update metadata for future incremental runs
- deep per-unit docs
- reference docs
- contracts
- flows
- system-level docs
- interop docs
- summaries that act as compressed memory
- verification artifacts proving what was covered and what remains unresolved
- explicit deep-flow trace artifacts
- a structured scratchpad for long-run continuity

CRITICAL OPERATING PRINCIPLE

Do NOT attempt one giant repo-to-doc generation pass.

Use this workflow instead:
1. inventory the repository
2. classify every useful file
3. partition the repository into bounded semantic work units
4. initialize queue, coverage, scratchpad, verification, and update-readiness artifacts
5. document one work unit at a time
6. generate a compact summary for each work unit
7. explicitly trace any deep workflow that spans many files or boundaries
8. verify each work unit before marking it complete
9. consolidate global docs from verified work units
10. finalize metadata for future diff-based updates
11. commit and push to the documentation branch

NON-NEGOTIABLE RULES

1. Every useful file must be accounted for.
2. Every useful file must belong to exactly one primary work unit or be explicitly marked unresolved.
3. Documentation completion must be measured through coverage artifacts, not by the number of markdown files written.
4. Large TODO-filled pages are not acceptable as a substitute for documentation.
5. If something is uncertain, record it explicitly in unresolved artifacts. Do not quietly omit it.
6. All major documentation domains must be covered:
   - functionality
   - reference
   - contracts
   - flows
   - system/global docs
   - interop
7. Mermaid diagrams must be included where they materially clarify architecture, workflows, dependencies, interactions, or state.
8. The initial documentation system must be designed so future update runs are cheap, targeted, and reliable.
9. Deep flows must be traced, not vaguely summarized.
10. Scratchpad state must be maintained during long runs.

DO NOT

- do a single shallow scan and immediately write the full docs tree
- claim completeness without explicit coverage accounting
- leave major folders, code islands, or DB areas untouched
- silently skip files
- overload README files with unresolved TODOs
- hallucinate architecture or standards
- generate decorative Mermaid diagrams without explanatory value
- optimize for page count over depth
- optimize for prose over structure
- assume updates will “work later” without building update-readiness now
- summarize deep multi-file workflows at a high level without tracing them through code

SUCCESS DEFINITION

This run is successful only if:
- the full file universe is inventoried
- useful files are classified
- useful files are partitioned into work units
- a work queue exists
- a coverage ledger exists
- each work unit is documented deeply
- each work unit has a compressed summary
- each work unit is verified
- all documentation domains are represented
- code-to-doc mapping exists for useful files
- update rules exist
- file hashes or fingerprints exist
- deep flows have explicit trace artifacts
- the docs can be updated later with git diff instead of full rescans
- unresolved items are explicitly tracked and bounded

GIT / BRANCH OBJECTIVE

You must maintain all documentation work in a dedicated documentation branch.

Documentation branch name:
documentation

You must:
1. inspect repository root, current branch, HEAD, remotes, status
2. detect whether documentation branch exists locally or remotely
3. switch safely to documentation branch, or create it if absent
4. preserve unrelated local work
5. write documentation into the repository
6. commit the changes
7. push to origin/documentation if possible

If push fails:
- keep the local commit
- report the exact error
- report the exact retry command

If no commit is needed:
- report that clearly

EXECUTION MODEL

You must execute in 8 phases:

PHASE 0: Git and repository setup
PHASE 1: Repository census
PHASE 2: Classification and partitioning
PHASE 3: Queue, ledger, scratchpad, flow-trace, and update-readiness initialization
PHASE 4: Work-unit documentation loop
PHASE 5: Verification loop
PHASE 6: Global consolidation
PHASE 7: Final audit, metadata finalization, commit, push

==================================================
PHASE 0: GIT AND REPOSITORY SETUP
==================================================

Inspect:
- repository root
- current branch
- current HEAD
- remotes
- local status
- existing docs/ content if any
- local and remote documentation branch existence

Use commands equivalent to:
- git rev-parse --show-toplevel
- git rev-parse HEAD
- git status --short
- git branch --all
- git remote -v
- git log --oneline -n 20
- git ls-files

Branch logic:
- if local branch documentation exists, use it
- else if remote branch origin/documentation exists, create local tracking branch and use it
- else create documentation branch from current HEAD

Protect unrelated local work.
Do not discard local changes.

==================================================
PHASE 1: REPOSITORY CENSUS
==================================================

Your first deliverable is NOT the docs tree.
Your first deliverable is an explicit repository inventory.

You must identify:
- total file count
- file count by language/extension
- top-level directories
- major applications/services
- major modules
- jobs/batch/schedulers
- DB and stored procedure areas
- integration surfaces
- legacy areas
- configuration areas
- test areas
- existing docs
- likely entry points
- likely public interfaces
- likely data boundaries

Prefer fast structural discovery first:
- git ls-files
- extension scans
- find / fd / tree / rg
- top-level directory analysis
- representative file inspection

Assume most files are useful unless they are clearly generated, binary, vendor, or irrelevant.

Create these artifacts first:
- docs/meta/work/repo_inventory.yaml
- docs/meta/work/file_index.csv
- docs/meta/work/language_inventory.yaml
- docs/meta/work/ignored_paths.yaml

FILE INDEX REQUIREMENTS

file_index.csv must include at least:
- path
- extension
- language
- category
- top_level_dir
- likely_group
- priority
- status

Allowed category values:
- useful_code
- useful_config
- useful_db
- useful_docs
- test
- generated
- vendor
- binary
- ignored_other

priority should flag higher-signal files such as:
- startup/main/bootstrap files
- routes/controllers
- public interfaces
- config roots
- migrations
- stored procedures
- event definitions
- batch/scheduler entry points
- integration adapters
- large or central coordination files

ignored_paths.yaml must explicitly list:
- path
- ignore_reason

No meaningful file should be silently ignored.

YAML FORMAT EXAMPLE: repo_inventory.yaml

This is the high-level inventory summary.

```yaml
repo_root: /path/to/repo
documented_branch: documentation
current_head: abc1234
file_counts:
  total: 1482
  useful_total: 1197
  ignored_total: 285
languages:
  java: 420
  python: 185
  csharp: 96
  sql: 143
  cobol: 57
  yaml: 88
top_level_dirs:
  - src
  - db
  - jobs
  - config
  - tests

================================================== PHASE 2: CLASSIFICATION AND PARTITIONING

Now classify all useful files into bounded semantic work units.

A work unit is a meaningful documentation target such as:

business functionality

shared/common platform area

infrastructure/configuration area

integration boundary

DB domain

batch pipeline

legacy subsystem

reporting subsystem

scheduler/job cluster


Rules:

1. Every useful file must be assigned to exactly one primary work unit.


2. If ownership is ambiguous, place it in unassigned_paths.yaml with an explanation.


3. Do not partition randomly by file count or alphabet.


4. Partition by real system meaning.


5. Work units must be bounded enough for deep analysis in one local pass.



Create:

docs/meta/work/path_classification.yaml

docs/meta/work/functionality_map.yaml

docs/meta/work/unassigned_paths.yaml

docs/meta/work/work_queue.yaml


work_queue.yaml must include, for each work unit:

id

name

type

included_paths

estimated_file_count

languages

likely_dependencies

interop_relevance

priority

expected_docs

status


Suggested status values:

queued

in_progress

docs_generated

verification_failed

verified


YAML FORMAT EXAMPLE: work_queue.yaml

units:
  - id: billing
    name: Billing
    type: functionality
    included_paths:
      - src/billing/**
      - db/billing/**
      - jobs/billing/**
    estimated_file_count: 118
    languages: [java, sql, python]
    likely_dependencies: [auth, reporting]
    interop_relevance: high
    priority: high
    expected_docs:
      - docs/functionality/billing/README.md
      - docs/functionality/billing/architecture.md
      - docs/functionality/billing/key-workflows.md
    status: queued

================================================== PHASE 3: QUEUE, LEDGER, SCRATCHPAD, FLOW-TRACE, AND UPDATE-READINESS INITIALIZATION

Create all orchestration and future-update artifacts before major doc generation.

Create:

docs/meta/work/coverage_ledger.yaml

docs/meta/work/unresolved_paths.yaml

docs/meta/work/unresolved_questions.yaml

docs/meta/work/omissions.yaml

docs/meta/work/verification_report.yaml

docs/meta/work/pass_log.md

docs/meta/work/flow_trace_ledger.yaml

docs/meta/work/scratchpad.md


Also create:

docs/meta/doc_state.yaml

docs/meta/doc_changelog.yaml

docs/meta/code_doc_map.yaml

docs/meta/doc_coverage.yaml

docs/meta/doc_coverage_matrix.yaml

docs/meta/update_rules.yaml

docs/meta/symbol_index.yaml

docs/meta/file_hashes.yaml


COVERAGE LEDGER REQUIREMENTS

coverage_ledger.yaml must track, per work unit:

total_files

useful_files

representative_files_read

key_entrypoints_read

key_integrations_read

key_db_assets_read

key_events_read

functionality_docs_done

reference_docs_done

contracts_done

flows_done

system_links_done

interop_done

summaries_done

docs_verified

unresolved_count

confidence


YAML FORMAT EXAMPLE: coverage_ledger.yaml

billing:
  total_files: 118
  useful_files: 112
  representative_files_read: 18
  key_entrypoints_read: true
  key_integrations_read: true
  key_db_assets_read: true
  key_events_read: false
  functionality_docs_done: true
  reference_docs_done: true
  contracts_done: partial
  flows_done: partial
  system_links_done: true
  interop_done: false
  summaries_done: true
  docs_verified: false
  unresolved_count: 6
  confidence: medium

DOC COVERAGE MATRIX REQUIREMENTS

doc_coverage_matrix.yaml must track documentation completeness per work unit across domains:

functionality

reference

contracts

flows

system_links

interop


Allowed values:

missing

skeletal

partial

verified

not_applicable


YAML FORMAT EXAMPLE: doc_coverage_matrix.yaml

billing:
  functionality: partial
  reference: verified
  contracts: partial
  flows: partial
  system_links: verified
  interop: missing

SCRATCHPAD REQUIREMENTS

scratchpad.md is the live structured execution memory. It is not the source of truth, but it helps preserve continuity in long runs.

It must include:

current phase

current work unit

queue snapshot

current unit progress

decisions taken

unresolved current-unit issues

risks

next actions

notes for verifier


MARKDOWN FORMAT EXAMPLE: scratchpad.md

# Documentation Run Scratchpad

## Current Phase
- Phase: Work Unit Processing
- Current Unit: billing
- Status: in_progress

## Work Queue Snapshot
- Total units: 12
- Completed: 4
- Verified: 3
- Remaining: 8

## Current Unit Progress
- Files total: 118
- Files examined: 18
- Entry points read: yes
- Integrations mapped: partial
- DB coverage: partial
- Event coverage: missing

## Decisions Taken
- Billing includes invoice + payment posting
- Shared notification utilities remain in shared

## Unresolved (Current Unit)
- src/billing/events/InvoicePublisher.java not fully analyzed
- db/billing/sp_generate_invoice.sql retry path unclear

## Risks / Concerns
- Possible missing async event path
- Batch reconciliation dependency unconfirmed

## Next Actions
- Read billing/events/*
- Read db/billing/procedures/*
- Patch events.md and key-workflows.md

## Notes for Verifier
- Check event coverage
- Check DB mapping completeness

FLOW TRACE LEDGER REQUIREMENTS

flow_trace_ledger.yaml tracks critical deep flows that cannot be vaguely summarized.

YAML FORMAT EXAMPLE: flow_trace_ledger.yaml

invoice_creation:
  status: partial
  work_unit: billing
  entry_point: src/billing/api/InvoiceController.java
  files_traced:
    - src/billing/api/InvoiceController.java
    - src/billing/service/InvoiceService.java
    - src/billing/repo/InvoiceRepository.java
    - db/billing/sp_generate_invoice.sql
    - src/billing/events/InvoicePublisher.java
  boundaries_crossed:
    - api_to_service
    - service_to_db
    - service_to_event
  side_effects:
    - invoice row inserted
    - invoice_created event emitted
  missing_branches:
    - retry path after DB timeout
  verifier_status: failed

UPDATE-READINESS REQUIREMENTS

These are mandatory. Build the docs so future update runs can be cheap and precise.

1. CODE TO DOCUMENTATION TRACEABILITY



Every useful file must be mapped in: docs/meta/code_doc_map.yaml

For each useful file, store:

group/work unit

documentation locations where the file is represented

whether it contributes to reference docs

whether it contributes to contracts/flows/interop


No useful file should exist without a mapping.

YAML FORMAT EXAMPLE: code_doc_map.yaml

src/billing/InvoiceService.java:
  group: billing
  docs:
    - docs/functionality/billing/code-map.md
    - docs/functionality/billing/key-workflows.md
    - docs/flows/cross-functional-workflows/invoice-creation.md
  contributes_to:
    - functionality
    - flows
    - reference

db/billing/sp_generate_invoice.sql:
  group: billing
  docs:
    - docs/functionality/billing/db-objects.md
    - docs/reference/stored-procedure-inventory.md
    - docs/flows/cross-functional-workflows/invoice-creation.md
  contributes_to:
    - functionality
    - reference
    - flows

2. CHANGE DETECTION SUPPORT



Create: docs/meta/file_hashes.yaml

For every useful file, store a stable hash or fingerprint scaffold.

Also in doc_state.yaml store:

documented_commit

documented_at

current_branch

documentation_branch

update_mode

major work units

repo summary


YAML FORMAT EXAMPLE: doc_state.yaml

documented_commit: abc1234
documented_at: 2026-04-14T11:30:00Z
current_branch: main
documentation_branch: documentation
update_mode: initial
major_work_units:
  - billing
  - auth
  - reporting
repo_summary: Multi-language enterprise codebase with service, DB, job, and legacy components.

3. TARGETED UPDATE ROUTING



Create: docs/meta/update_rules.yaml

This must define which docs need updating when specific paths or change types occur.

Rules should cover:

functionality docs

reference docs

contracts

flows

system docs

interop docs


YAML FORMAT EXAMPLE: update_rules.yaml

rules:
  - match: "src/billing/**"
    update:
      - docs/functionality/billing/**
      - docs/reference/api-inventory.md
      - docs/flows/cross-functional-workflows/**
      - docs/meta/code_doc_map.yaml

  - match: "db/**"
    update:
      - docs/reference/database-object-inventory.md
      - docs/reference/stored-procedure-inventory.md
      - docs/contracts/db-contracts/**
      - docs/meta/code_doc_map.yaml

4. SUMMARY-FIRST UPDATE DESIGN



Every work unit must produce a compact summary under: docs/generated/summaries/<unit>.md

Future update runs must be able to load summaries instead of raw code for unchanged areas.

5. NO GLOBAL REPROCESSING ASSUMPTION



Structure the metadata so future update runs can:

detect changed files

map them to work units

update only affected docs

rerun verification only where needed


================================================== PHASE 4: WORK-UNIT DOCUMENTATION LOOP

Now process work units one by one.

For each work unit, execute the following:

STEP A: LOAD LOCAL CONTEXT ONLY

Load:

the work unit definition

the files in that unit

relevant inventories or contracts if they already exist

1–2 related summaries from previously processed units if needed


Do NOT attempt to load the whole repository context.

STEP B: DEEP LOCAL READING

Inspect high-signal and representative files first:

startup / main / Program / App / bootstrap files

controllers / routes / endpoints

public interfaces

domain services

integration adapters/clients

event definitions / publishers / consumers

migrations / stored procedures / schema definitions

scheduler / cron / batch orchestration

configuration definitions

legacy entry points, copybooks, handoff code

tests that reveal workflow behavior


Then deepen only where uncertainty remains.

If the unit spans multiple languages, make that explicit.

Examples:

C# service calls stored procedures

Java API invokes Python jobs

COBOL batch writes tables consumed by reporting

Python ETL publishes or transforms data used elsewhere


STEP C: GENERATE DEEP UNIT DOCS

Create or update a deep documentation pack for the work unit.

For functionality-like units, use:

docs/functionality/<unit>/README.md

docs/functionality/<unit>/purpose-and-scope.md

docs/functionality/<unit>/architecture.md

docs/functionality/<unit>/code-map.md

docs/functionality/<unit>/key-workflows.md

docs/functionality/<unit>/business-rules.md

docs/functionality/<unit>/integrations.md

docs/functionality/<unit>/data-model.md

docs/functionality/<unit>/interfaces-and-contracts.md

docs/functionality/<unit>/events.md

docs/functionality/<unit>/db-objects.md

docs/functionality/<unit>/configuration.md

docs/functionality/<unit>/error-handling.md

docs/functionality/<unit>/testing.md

docs/functionality/<unit>/change-guide.md

docs/functionality/<unit>/known-gotchas.md

docs/functionality/<unit>/related-systems.md


If the unit is not a business functionality, adapt the doc set appropriately, but preserve equivalent depth and structure.

DEPTH REQUIREMENTS FOR UNIT DOCS

Do not write generic filler. For every meaningful unit, document:

purpose

scope

responsibilities

non-responsibilities

key components

key code paths

key entry points

dependencies

upstream systems

downstream systems

workflows

integrations

DB interactions

events

configs

failure points

testing strategy

change impact

known gotchas

related systems

cross-language distribution if present


READMEs must be hub pages, not dumping grounds for TODOs.

STEP D: GENERATE OR UPDATE REFERENCE DOCS

Maintain structured shared inventories under docs/reference/:

api-inventory.md

event-inventory.md

queue-inventory.md

batch-job-inventory.md

database-object-inventory.md

stored-procedure-inventory.md

config-inventory.md

feature-flag-inventory.md

ownership-map.md

external-system-inventory.md


These must be structured lookup artifacts, not vague prose.

STEP E: GENERATE OR UPDATE CONTRACT DOCS

Where real boundaries exist, maintain:

docs/contracts/service-contracts/*

docs/contracts/event-contracts/*

docs/contracts/db-contracts/*

docs/contracts/file-contracts/*

docs/contracts/batch-contracts/*


Create only where supported by code evidence. Document boundary assumptions clearly.

STEP F: GENERATE OR UPDATE FLOW DOCS

Where the unit participates in meaningful workflows, update:

docs/flows/end-to-end-user-journeys/*

docs/flows/cross-functional-workflows/*

docs/flows/batch-and-nightly-flows/*

docs/flows/operational-critical-paths/*


DEEP FLOW TRACE MODE

For any critical flow that is business-critical, integration-heavy, cross-module, cross-language, DB-heavy, batch-heavy, or event-driven, do NOT summarize it vaguely.

Switch to Flow Trace Mode.

A deep flow is one that:

spans multiple meaningful files

crosses module boundaries

crosses language boundaries

includes DB writes/reads of significance

emits or consumes events

touches integrations

includes branching, retries, or fallback paths

includes scheduler or batch orchestration


In Flow Trace Mode, you MUST:

1. identify the exact entry point


2. trace the execution chain step by step


3. list the participating files


4. list boundaries crossed


5. record side effects


6. identify failure points and retry/fallback paths


7. create a dedicated deep flow document


8. create a Mermaid sequenceDiagram or flowchart for that flow


9. update flow_trace_ledger.yaml


10. leave unresolved branches explicit if not fully proven



STEP G: GENERATE COMPRESSED UNIT SUMMARY

Create: docs/generated/summaries/<unit>.md

Each summary must be short, dense, and future-update-friendly.

Each summary must contain:

purpose

key paths

key entry points

dependencies

integrations

DB/events/interfaces

languages involved

key workflows

unresolved items

related docs


================================================== MERMAID REQUIREMENTS

Documentation must include meaningful Mermaid diagrams.

RULES

1. For each major work unit, include:



at least one architecture diagram

at least one workflow diagram


2. For deep flows, include:



at least one flow-specific sequenceDiagram or flowchart tied to the traced execution


3. For global docs, include diagrams where useful:



system map

dependency map

cross-system interaction map

major cross-functional workflows


Use only when valuable. Do not add decorative diagrams.

Preferred Mermaid types:

graph / flowchart for architecture and dependencies

sequenceDiagram for request/event/batch flows

stateDiagram for lifecycle logic or state transitions


Examples of good Mermaid use:

service -> DB -> event bus relationship

end-to-end request path

batch chain

event producer/consumer flow

state transitions of a domain entity

cross-language integration handoff


================================================== PHASE 5: VERIFICATION LOOP

Verification is mandatory.

Do not mark a work unit complete until it passes verification.

For each work unit, verify ALL dimensions:

A. FILE COVERAGE CHECK

are all useful files in the unit assigned?

are important files represented in docs or explicitly unresolved?

are large/high-signal files ignored or omitted?


B. FUNCTIONAL COVERAGE CHECK

are workflows concrete?

are entry points explicit?

is ownership clear?

are dependencies explicit?

are docs deep enough, not generic?


C. REFERENCE COVERAGE CHECK

are APIs reflected in API inventory?

are events reflected in event inventory?

are DB objects and stored procedures reflected in inventories?

are jobs reflected in batch inventory?

are key configs reflected where relevant?


D. CONTRACT COVERAGE CHECK

are real boundaries documented?

are service/event/file/db/batch contracts linked where needed?


E. FLOW COVERAGE CHECK

are important unit workflows documented?

are cross-functional flows reflected where needed?

are flows tied back to code paths?

have deep flows been traced rather than merely summarized?

does flow_trace_ledger reflect actual traced participation?


F. SYSTEM LINK COVERAGE CHECK

are related systems linked?

are upstream/downstream dependencies reflected?


G. INTEROP COVERAGE CHECK

are external touchpoints captured?

are repo/system boundaries documented where relevant?


H. DIAGRAM CHECK

architecture diagram present where needed?

workflow diagram present where needed?

deep-flow diagrams present where needed?

diagrams reflect real structure and flow?


If verification fails:

do not mark unit verified

record exact misses in verification_report.yaml

add missing paths/questions to unresolved files

deepen only in the necessary local area

patch docs

rerun verification


verification_report.yaml must record, per unit:

status

issues

required_actions

verifier_confidence


YAML FORMAT EXAMPLE: verification_report.yaml

billing:
  status: failed
  issues:
    - event publisher files not represented in events.md
    - invoice creation flow missing retry path
    - one stored procedure unaccounted for
  required_actions:
    - inspect src/billing/events/*
    - inspect db/billing/procedures/*
    - patch events.md and invoice-creation flow doc
  verifier_confidence: medium

================================================== PHASE 6: GLOBAL CONSOLIDATION

Only after enough local work units are verified, generate or update the global docs.

Required global docs:

docs/README.md

docs/SYSTEM_MAP.md

docs/DOMAIN_GLOSSARY.md

docs/INTEROPERABILITY_RULES.md

docs/CROSS_SYSTEM_DEPENDENCIES.md

docs/ARCHITECTURE_PRINCIPLES.md

docs/CHANGE_PROPAGATION_RULES.md


These must be built from verified local understanding, not broad guesses.

Also generate standards docs under docs/standards/:

README.md

shared-engineering-principles.md

naming-conventions.md

documentation-conventions.md

csharp.md

python.md

java.md

cobol.md

sql-and-stored-procs.md

api-standards.md

event-standards.md

db-standards.md

testing-standards.md

security-standards.md


Infer standards only from repeated real evidence.

================================================== INTEROP SURFACE

Keep the interop layer real but not overcomplicated.

Create:

docs/interop/README.md

docs/interop/REPO_IDENTITY.md

docs/interop/EXTERNAL_INTERFACES.md

docs/interop/DEPENDENCY_CONTRACTS.md

docs/interop/DATA_EXCHANGE.md

docs/interop/EVENT_EXCHANGE.md

docs/interop/CROSS_REPO_GLOSSARY.md

docs/interop/INTEGRATION_TOUCHPOINTS.md


Also create:

docs/meta/repo_interop.yaml


The interop layer should quickly answer:

what this repo is

what it owns

what it exposes

what it consumes

what upstream/downstream dependencies exist

which docs to read next


YAML FORMAT EXAMPLE: repo_interop.yaml

repo:
  name: billing-service
  type: service
  summary: Handles invoice creation and billing events.

ownership:
  owns:
    - invoice generation
    - payment posting
  does_not_own:
    - customer onboarding

interfaces:
  apis_exposed:
    - createInvoice
  events_emitted:
    - InvoiceCreated
  events_consumed:
    - PaymentConfirmed

dependencies:
  upstream_repos:
    - customer-service
  downstream_repos:
    - reporting-repo

important_docs:
  - docs/functionality/billing/README.md
  - docs/functionality/billing/interfaces-and-contracts.md

================================================== PHASE 7: FINAL AUDIT, METADATA FINALIZATION, COMMIT, PUSH

Finalize and refresh:

docs/meta/doc_state.yaml

docs/meta/doc_changelog.yaml

docs/meta/code_doc_map.yaml

docs/meta/doc_coverage.yaml

docs/meta/doc_coverage_matrix.yaml

docs/meta/update_rules.yaml

docs/meta/symbol_index.yaml

docs/meta/file_hashes.yaml


FINAL AUDIT REQUIREMENTS

Produce a final audit that states:

total useful files

total ignored files

total unassigned files

total work units

verified work units

partial work units

unresolved high-priority paths

unresolved questions

doc domains completed

areas still low confidence

deep flows traced

deep flows still partial


The run is not complete if:

useful files remain silently unassigned

major units remain undocumented

verification was skipped

update-readiness artifacts are missing

large unresolved areas are hidden inside TODOs instead of explicit unresolved artifacts

deep flows were only summarized instead of traced


QUALITY STANDARDS

Accuracy over confidence.

Coverage over visual appearance.

Deep local docs over shallow global claims.

Verified completeness over raw file count of docs.

Explicit unresolved tracking over forgotten omissions.

Compact summaries over trying to keep the whole repo in context.

Update-readiness is a first-class requirement, not an afterthought.


MENTAL MODEL

At all times operate with this model:

You are not directly writing docs from a giant codebase. You are:

inventorying the universe

partitioning it into bounded units

compiling deep docs for each unit

compressing them into summaries

tracing deep flows explicitly

verifying each unit

linking them globally

proving coverage

and leaving behind a system that can update itself incrementally later


EXECUTION ORDER

Execute in this exact order:

1. inspect git and repository state


2. create or switch safely to documentation branch


3. perform repository census


4. create file index and inventory artifacts


5. classify and partition all useful files


6. create queue, ledger, scratchpad, flow-trace, unresolved, and update-readiness artifacts


7. process work units one by one


8. verify each work unit before marking it complete


9. generate global docs from verified units


10. generate interop docs


11. finalize metadata


12. run final audit


13. stage docs


14. commit docs


15. push documentation branch


16. report:



documentation branch used

documented commit

total useful files counted

total work units

verified work units

major docs created

major Mermaid diagrams created

deep flows traced

unresolved items

whether commit succeeded

whether push succeeded


FINAL INSTRUCTION

Now execute this documentation-compiler workflow end to end inside the repository.

Do not stop at attractive partial docs. Do not leave large TODO-filled pages behind. Do not skip deep flows. Do not assume future runs will fix weak foundations.

Continue until:

the work queue is exhausted

deep flows are traced where required

or only explicitly bounded low-confidence unresolved items remain


And ensure that future update runs can later operate through:

documented_commit

git diff

code_doc_map.yaml

file_hashes.yaml

update_rules.yaml

summaries without a full repo rescan.


This version keeps your old instruction set intact in spirit and appends the new missing pieces:
- structured scratchpad
- deep flow trace mode
- flow_trace_ledger
- YAML examples so the agent knows the intended shape
- stronger update-readiness guarantees

If you want, I can next turn this into a shorter “Copilot-safe” version that is easier to paste and more likely to be followed literally.