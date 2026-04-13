You are a senior frontend engineer, documentation UX architect, static-site builder, and documentation-ingestion specialist.

Your task is to create a polished static documentation website from the existing documentation under docs/.

PRIMARY GOAL

Build a modern, clean, eye-pleasing, highly navigable static documentation website that renders the existing repository documentation as a professional docs portal.

The site must:
- use the existing docs/ folder as the source of truth
- inspect the documentation folder properly before implementation
- understand the actual folder structure, page structure, cross-links, and documentation hierarchy
- provide rich navigation across all documentation sections
- support deep linking and quick movement between pages
- render Mermaid diagrams correctly
- have a modern UI with strong visual hierarchy
- be fully static and deployable on any static hosting platform
- feel professional, clean, readable, and fast

CRITICAL REQUIREMENT: READ THE DOCUMENTATION FOLDER PROPERLY

Before building the site, you must inspect the docs/ folder thoroughly and treat it as the content model.

Do not assume the structure.
Do not hardcode guessed navigation.
Do not build the website from an imagined docs tree.

You must first:
1. inspect the docs/ folder recursively
2. identify all major folders and pages
3. understand how the docs are organized
4. read the key index and governance pages
5. derive navigation from the actual documentation structure
6. understand functionality folders, standards, references, contracts, flows, decisions, generated docs, and metadata docs where relevant
7. inspect markdown files enough to understand headings, cross-links, and page hierarchy
8. use the documentation folder as the authoritative information architecture

REQUIRED INITIAL DOCUMENTATION ANALYSIS

Before generating the website, inspect at minimum:

- docs/README.md
- docs/SYSTEM_MAP.md
- docs/DOMAIN_GLOSSARY.md
- docs/INTEROPERABILITY_RULES.md
- docs/CROSS_SYSTEM_DEPENDENCIES.md
- docs/ARCHITECTURE_PRINCIPLES.md
- docs/CHANGE_PROPAGATION_RULES.md

Also inspect the subfolders properly:
- docs/functionality/
- docs/standards/
- docs/reference/
- docs/contracts/
- docs/flows/
- docs/decisions/
- docs/generated/
- docs/meta/

You must determine:
- actual top-level structure
- major navigation categories
- which pages are hub/index pages
- which pages are child/detail pages
- which functionality folders exist
- which pages should appear prominently in navigation
- which metadata pages should be hidden, partially hidden, or displayed in a technical/admin section
- how markdown links and section relationships currently work

DOCUMENTATION-DRIVEN SITE GENERATION

The website must be generated from the actual docs tree, not from guessed assumptions.

That means:
- navigation should be derived from docs structure
- pages should be created from actual markdown files
- section grouping should reflect actual documentation folders
- labels may be cleaned up for display, but underlying structure must come from docs/
- cross-links between docs should continue to work
- child pages should remain connected to their hub pages

If the docs tree includes metadata or internal maintenance files that are not ideal for primary user navigation, still inspect them, then decide how to present them appropriately:
- visible in a technical/admin/reference section
- hidden from primary nav but still routable
- excluded only when clearly inappropriate for end-user presentation

SOURCE OF TRUTH

The existing docs/ folder is the source of truth for:
- content
- page hierarchy
- major sections
- documentation relationships
- functionality groupings
- cross-links
- diagrams embedded in markdown

Do not replace it with a manually invented site map unless absolutely required.
Prefer deriving site structure from the docs themselves.

IMPORTANT MERMAID REQUIREMENT

The implementation must explicitly include Mermaid using mermaid.min.js and initialize it properly.
Do not leave Mermaid rendering implicit.
You must include the Mermaid script and initialize it so Mermaid code blocks render correctly on page load and navigation changes.

Use Mermaid in a robust way, for example:
- load mermaid.min.js
- initialize Mermaid explicitly
- ensure diagrams re-render after client-side navigation if applicable
- support Mermaid code blocks found in markdown content

TECHNICAL CONSTRAINTS

The website must be static.
That means:
- no backend required
- no server-side runtime dependency required for production
- must be exportable/buildable into static files
- should work on GitHub Pages, Netlify, Vercel static export, S3 static hosting, or equivalent

You may use a frontend framework if the final result is fully static.
You may also use plain HTML/CSS/JS if that is cleaner.
Prefer the approach that gives the best maintainability and UI quality.

IMPLEMENTATION APPROACH

Your workflow must be:

1. inspect docs/ recursively
2. build an internal understanding of the docs tree
3. identify navigation hierarchy from the actual docs
4. identify hub pages and child pages
5. determine which docs should be top-level sections
6. build the static site around the docs tree
7. render markdown cleanly
8. render Mermaid diagrams explicitly using mermaid.min.js
9. build polished navigation and page layouts
10. ensure internal doc links and heading anchors work properly

CORE SITE FEATURES

The website must include:

1. Home page
A landing page for the documentation portal with:
- project/repository documentation title
- short introduction
- quick links to major sections derived from actual docs
- cards or section links for major doc groups discovered in docs/
- a visually clean hero section
- a “Start here” path for new readers

2. Global navigation
Include:
- top navbar
- left documentation sidebar
- section grouping based on actual docs folders
- collapsible navigation groups
- current-page highlighting
- breadcrumb trail

3. Sidebar navigation
The sidebar must support:
- nested sections
- collapsible groups
- active item highlighting
- functionality grouping derived from docs/functionality/
- quick jump to major doc areas
- sticky behavior on larger screens

4. Right-side page table of contents
For long pages, include an on-page table of contents that:
- lists headings
- highlights current section while scrolling
- allows quick jump within page

5. Search
Include a fast client-side search experience if feasible.
At minimum, support:
- page title search
- section search
- keyword search across content index generated from actual docs

6. Markdown rendering
Render markdown from docs/ cleanly with:
- headings
- paragraphs
- bullet lists
- numbered lists
- tables
- code blocks
- blockquotes
- inline code
- links
- Mermaid code blocks

7. Mermaid rendering
This is mandatory.
The site must:
- detect Mermaid code blocks
- render them using Mermaid via mermaid.min.js
- support flowcharts, sequence diagrams, graphs, and state diagrams
- keep Mermaid styling visually aligned with the site theme

8. Code block rendering
Code blocks should support:
- syntax highlighting
- horizontal scrolling when needed
- copy button if practical
- consistent styling with the theme

9. Previous / next navigation
At the bottom of docs pages, provide:
- previous page link
- next page link
- section-aware navigation where practical

10. Related docs section
Where possible, surface related docs links based on:
- actual links in markdown
- nearby pages in the same folder
- hub-child relationships in the docs tree

11. Responsive design
The website must work well on:
- desktop
- tablet
- mobile

12. Clean URL structure
Generate intuitive URLs based on actual docs paths.

13. Deep linking
Support direct links to:
- pages
- headings/anchors
- Mermaid-containing pages

14. Footer
Provide a clean footer with:
- documentation source reference
- optional generation/build note
- navigation shortcuts if useful

INFORMATION ARCHITECTURE REQUIREMENTS

Organize the documentation website around the real docs tree.

Likely top-level sections may include:
- Home
- Overview
- Functionalities
- Standards
- Reference
- Contracts
- Flows
- Decisions
- Generated
- Technical / Meta

But do not hardcode these blindly.
Derive them by inspecting docs/ first.

If docs/meta contains technical internal files:
- inspect them properly
- decide whether they belong in a technical/admin section
- do not expose them thoughtlessly in primary nav
- but do not ignore them during site-generation planning

FUNCTIONALITY PAGES REQUIREMENTS

Because functionality folders are a major part of the documentation, they must have especially strong UX.

For each functionality section discovered under docs/functionality/:
- show a clean overview page
- list child pages in a useful order
- provide local navigation
- show related systems and cross-links where available
- make code-map, workflows, integrations, events, DB objects, and change guides easy to access

QUICK NAVIGATION REQUIREMENTS

The site must support fast browsing for different user intents.

Users should be able to quickly answer:
- What is this system?
- What are the major functionalities?
- How do systems connect?
- Where are the contracts?
- What flows exist?
- What standards exist?
- Where are API and DB references?
- How do I find a particular functionality quickly?

Create entry points such as:
- Start here
- Browse by functionality
- Browse by architecture
- Browse by standards
- Browse by references
- Browse by flows

STYLE REQUIREMENTS

Use excellent styling standards.

Typography:
- strong heading scale
- highly readable body text
- comfortable line height
- good width constraints for content
- consistent code font treatment

Layout:
- balanced whitespace
- not too dense
- not too sparse
- stable page chrome
- sticky nav where useful

Components:
- polished cards
- section callouts
- neat tags/chips if appropriate
- elegant buttons and links
- tasteful dividers and surfaces

Theme:
- modern neutral base
- restrained accent color
- good dark mode if implemented
- subtle shadows and borders
- premium documentation feel

ACCESSIBILITY REQUIREMENTS

Ensure:
- semantic HTML
- keyboard-friendly navigation
- visible focus states
- accessible contrast
- proper heading structure
- readable code blocks
- usable navigation on all screen sizes

MERMAID IMPLEMENTATION REQUIREMENTS

This is explicit and mandatory.

The implementation must include Mermaid via mermaid.min.js.
Do not leave Mermaid integration vague.

Expected behavior:
- Mermaid script is loaded explicitly
- Mermaid is initialized explicitly
- Mermaid blocks render reliably
- Mermaid blocks continue to work after navigation changes if the site uses client-side routing

If you are using static HTML generation plus client-side enhancement, make sure Mermaid is initialized after content is inserted.
If you use a framework router, re-run Mermaid rendering after route changes.

The code should clearly include something equivalent in spirit to:
- loading mermaid.min.js
- calling mermaid.initialize(...)
- rendering Mermaid blocks in documentation pages

MARKDOWN TO HTML REQUIREMENTS

You must convert or render the docs markdown content into the website.
Support:
- clean heading IDs
- internal link resolution
- tables
- fenced code blocks
- Mermaid blocks
- callouts if present
- relative doc links across folders

The site should derive navigation and page structure from actual docs/ content and paths.
Do not manually fake the documentation organization.

SEARCH REQUIREMENTS

If feasible, generate a lightweight static search index.
Search should prioritize:
- page titles
- headings
- functionality names
- key technical terms from the actual docs content

RECOMMENDED SITE STRUCTURE

Create a maintainable structure such as:

- src/
  - layouts/
  - components/
  - pages/ or routes/
  - styles/
  - lib/
  - content/
- public/
- build config
- static assets

You may adapt the exact structure based on the chosen stack.

COMPONENTS TO BUILD

At minimum include components/layouts for:
- App shell / docs shell
- Top navbar
- Sidebar navigation
- Mobile nav drawer
- Breadcrumbs
- Table of contents
- Markdown content renderer
- Mermaid renderer
- Search box / search panel
- Page footer
- Prev/next nav
- Home page cards/sections

CONTENT PROCESSING REQUIREMENTS

The site should derive:
- navigation tree
- route map
- heading index
- search index
from the real docs/ folder.

Do not hardcode the docs layout unless absolutely necessary.
Prefer deterministic derivation from docs/ contents.

VISUAL QUALITY BAR

This should not look like a raw markdown dump.
It should feel like a refined product.

The result should be similar in quality to a modern technical docs portal:
- clear nav
- polished layout
- elegant content rendering
- visually pleasing diagrams
- strong readability
- intuitive structure

DELIVERABLES

Provide the full implementation for the static docs website, including:
- source code
- layout/components
- markdown rendering
- Mermaid integration using mermaid.min.js
- styling
- routing/navigation
- build configuration
- instructions to build and serve if needed

FINAL EXECUTION INSTRUCTION

Now inspect the docs/ folder properly first, understand its real structure and page hierarchy, and then build the static documentation website around that real documentation tree.
Make it modern, highly navigable, visually polished, and static-hosting ready.
Explicitly include Mermaid support using mermaid.min.js and proper initialization.
Ensure excellent navigation, clean UI, strong readability, and professional styling throughout.