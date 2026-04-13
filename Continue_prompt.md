You are continuing an existing repository documentation effort.

Your job is not to recreate the docs from scratch.
Your job is to identify what was left under-read, under-documented, partial, skeletal, inferred, or uncertain in the current documentation set, then collect the minimum additional code evidence needed to fill those gaps accurately.

PRIMARY GOAL

Improve documentation completeness and specificity by targeting only missing or weakly documented areas.

Do not do a full repository rescan unless the existing metadata is clearly unusable.
Prefer focused, evidence-driven follow-up reads.

YOU MUST START BY READING THE EXISTING DOCS AND METADATA

Read and use these first:
- docs/README.md
- docs/SYSTEM_MAP.md
- docs/INTEROPERABILITY_RULES.md
- docs/CROSS_SYSTEM_DEPENDENCIES.md
- docs/CHANGE_PROPAGATION_RULES.md
- docs/meta/doc_state.yaml
- docs/meta/doc_changelog.yaml
- docs/meta/code_doc_map.yaml
- docs/meta/doc_coverage.yaml
- docs/meta/update_rules.yaml
- docs/meta/symbol_index.yaml

Then inspect:
- docs/functionality/**
- docs/reference/**
- docs/contracts/**
- docs/flows/**
- docs/generated/**

MISSION

Find where the current documentation is weak.

Weak means any of the following:
- a page or section is marked partial, skeletal, inferred, or unknown
- a page contains TODOs, evidence gaps, uncertainty notes, placeholders, or generic wording
- a functionality exists but its workflows, integrations, DB objects, events, or cross-language distribution are thin
- a reference inventory is incomplete or too vague
- a cross-system dependency is mentioned but not explained concretely
- a workflow is described at a high level but key implementation paths are missing
- a language-specific area exists in code but is barely represented in docs

WORKFLOW

1. Build a gap list from the docs, not from the code.
2. Rank the gaps by value:
   - missing critical workflow details
   - missing public interface details
   - missing integration details
   - missing DB/stored proc details
   - missing event dependencies
   - missing cross-language handoffs
   - missing change-safety details
3. For each gap, identify the smallest code area that can answer it.
4. Read only those files plus the minimum nearby context.
5. Patch the affected docs with concrete evidence-based detail.
6. Update metadata coverage and changelog.

DO NOT

- do a blind repo-wide read
- rewrite already-good pages
- duplicate content between pages
- invent architecture
- turn this into another initial pass

TARGETING RULES

For each documentation gap, explicitly produce:
- gap_id
- affected_doc
- gap_type
- why this matters
- likely code paths to inspect
- minimum files needed
- expected output to add

Example gap types:
- workflow_gap
- integration_gap
- db_gap
- event_gap
- public_interface_gap
- dependency_gap
- code_map_gap
- testing_gap
- config_gap
- change_guide_gap
- cross_language_gap

READING STRATEGY

Read narrowly and in this order:
1. existing weak doc page
2. related code-map page
3. related contract/reference/flow page
4. exact code files that answer the missing question
5. only then any adjacent support files if still necessary

When reading code, prefer:
- startup and wiring files
- route/controller/interface files
- service entry points
- integration adapters/clients
- event publisher/consumer definitions
- DB migrations and stored procedures
- batch/scheduler definitions
- COBOL program entry points and copybooks
- config definitions
- files explicitly linked by the docs or metadata

MULTI-LANGUAGE RULE

If a workflow spans multiple languages, document the handoff explicitly.
Examples:
- C# API calls stored procedure
- Java service emits event consumed by Python job
- COBOL batch writes table used by reporting layer
- Python ETL populates DB consumed by Java or C# service

Do not leave cross-language boundaries implied.

OUTPUT REQUIREMENTS

At the start, produce a compact prioritized gap list like:

1. <gap title>
   - docs affected:
   - status today:
   - code areas to inspect:
   - expected improvement:

Then execute the highest-value gaps first.

For each completed gap, patch the docs and make the improvement concrete:
- replace vague text with actual flow details
- add missing interfaces
- add DB object details
- add event names and directions
- add integration specifics
- add related-systems links
- add Mermaid diagrams only if structure becomes materially clearer

COVERAGE RULE

Update docs/meta/doc_coverage.yaml after filling gaps.
If a page improves from skeletal to partial, or partial to complete, record that.
Do not overstate completeness.

CHANGELOG RULE

Append an entry to docs/meta/doc_changelog.yaml recording:
- this was a targeted enrichment pass
- which docs were enriched
- which code areas were inspected
- what gaps remain

QUALITY BAR

The result should make the docs materially more useful without doing a broad expensive scan.
Prefer a few high-value precise enrichments over many shallow edits.

COMPLETION CRITERIA

You are done only when:
- you have identified the main documentation gaps from the existing docs
- you have filled the highest-value ones with concrete code-backed detail
- you have updated coverage metadata
- you have updated the changelog
- you can clearly state what still remains incomplete