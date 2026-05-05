Below is the corrected full prompt with all pnpm references changed to npm.

You are an expert full-stack systems engineer. Implement a complete local codebase-understanding platform named “understand-anything”.

The goal is to replicate and extend an Understand-Anything style system for large repositories, including:
1. scalable repo scanning,
2. AST and dependency graph extraction,
3. knowledge graph generation,
4. layer visualization,
5. guided tours,
6. persona-aware explanations,
7. graph-based search,
8. lazy dashboard rendering,
9. diff impact analysis,
10. incremental indexing for large repositories with around 2000+ files.

Do not create a toy demo. Build a real working project with clean architecture, runnable CLI, persistent storage, and React dashboard.

PROJECT NAME

understand-anything

HIGH-LEVEL REQUIREMENT

Build a local-first system that can analyze a software repository, create a persistent knowledge graph, and provide an interactive dashboard for exploring the repository through graph views, guided tours, layer visualization, persona-based explanations, search, and impact analysis.

The system must scale to repositories with at least 2000 files. It must not load or render the full graph in the UI at once. It must use incremental indexing and hash-based caching so unchanged files are not reparsed or re-summarized.

TECH STACK

Use this stack unless there is a strong reason not to:

Backend / CLI:
- Node.js with TypeScript
- npm workspaces
- SQLite for persistent graph storage
- fast-glob for file discovery
- ignore for .gitignore support
- simple-git for git diff and repo metadata
- better-sqlite3 or sqlite3
- chokidar optionally for watch mode
- Tree-sitter or language-specific parsers where possible
- JSONL export support

Frontend:
- React + TypeScript + Vite
- React Flow for local graph visualization
- Zustand for state management
- TailwindCSS for UI
- Fuse.js for fuzzy search
- Optional: Cytoscape.js or Sigma.js for larger graph overview if useful

LLM:
- Design provider abstraction
- Support OpenAI-compatible API through environment variables
- LLM must be optional
- The system must work without an LLM using deterministic graph extraction
- LLM should only be used for summaries, guided tours, persona explanations, and uncertain layer classification

WORKSPACE STRUCTURE

Create this structure:

understand-anything/
  package.json
  package-lock.json
  tsconfig.base.json
  README.md
  .gitignore
  packages/
    core/
      package.json
      src/
        index.ts
        schema/
          graph.ts
          storage.ts
          config.ts
        scanner/
          scanRepo.ts
          ignoreRules.ts
          languageDetect.ts
          fileHash.ts
        parser/
          parseFile.ts
          parsers/
            typescriptParser.ts
            javascriptParser.ts
            pythonParser.ts
            genericParser.ts
        graph/
          buildGraph.ts
          edgeResolver.ts
          graphQueries.ts
          ranking.ts
        storage/
          sqlite.ts
          migrations.ts
          jsonlExport.ts
        summarizer/
          llmProvider.ts
          summarizeNode.ts
          summarizeFile.ts
          promptTemplates.ts
        layers/
          detectLayer.ts
          layerRules.ts
        tours/
          tourBuilder.ts
          tourPrompts.ts
        personas/
          personaTypes.ts
          detectPersona.ts
          personaRenderer.ts
        diff/
          gitDiff.ts
          impactAnalysis.ts
        search/
          fuzzySearch.ts
          semanticSearchStub.ts
        config/
          loadConfig.ts
    cli/
      package.json
      src/
        index.ts
        commands/
          init.ts
          scan.ts
          index.ts
          summarize.ts
          serve.ts
          export.ts
          diff.ts
          query.ts
    dashboard/
      package.json
      index.html
      vite.config.ts
      src/
        main.tsx
        App.tsx
        api/
          client.ts
        store/
          graphStore.ts
          personaStore.ts
          tourStore.ts
        components/
          Layout.tsx
          TopBar.tsx
          Sidebar.tsx
          GraphCanvas.tsx
          NodeDetails.tsx
          SearchBar.tsx
          LayerLegend.tsx
          TourPanel.tsx
          PersonaSelector.tsx
          DiffImpactPanel.tsx
          FileExplorer.tsx
          GraphFilters.tsx
        pages/
          OverviewPage.tsx
          GraphPage.tsx
          ToursPage.tsx
          DiffPage.tsx
        styles/
          globals.css
    server/
      package.json
      src/
        index.ts
        routes/
          graphRoutes.ts
          searchRoutes.ts
          tourRoutes.ts
          diffRoutes.ts
          summaryRoutes.ts

Use npm workspaces in the root package.json. Do not create or use pnpm-workspace.yaml. Do not require pnpm anywhere.

PERSISTENT PROJECT FOLDER

For every analyzed repository, create:

.my-understand/
  config.json
  graph.sqlite
  file_hashes.json
  intermediate/
    files.jsonl
    symbols.jsonl
    summaries.jsonl
    rankings.jsonl
  exports/
    knowledge-graph.json
    nodes.jsonl
    edges.jsonl

CORE DATA MODEL

Implement these TypeScript types.

Node types:

type GraphNodeType =
  | "repository"
  | "folder"
  | "file"
  | "function"
  | "class"
  | "method"
  | "module"
  | "route"
  | "database"
  | "config"
  | "domain"
  | "flow"
  | "concept";

Layer types:

type LayerType =
  | "ui"
  | "api"
  | "service"
  | "data"
  | "utility"
  | "config"
  | "test"
  | "script"
  | "unknown";

Edge types:

type GraphEdgeType =
  | "contains"
  | "imports"
  | "exports"
  | "calls"
  | "uses"
  | "implements"
  | "inherits"
  | "depends_on"
  | "belongs_to"
  | "routes_to"
  | "reads_from"
  | "writes_to"
  | "tested_by";

Graph node:

interface GraphNode {
  id: string;
  type: GraphNodeType;
  name: string;
  path?: string;
  language?: string;
  layer: LayerType;
  summary?: string;
  longSummary?: string;
  startLine?: number;
  endLine?: number;
  hash?: string;
  importanceScore?: number;
  metadata?: Record<string, unknown>;
  createdAt: string;
  updatedAt: string;
}

Graph edge:

interface GraphEdge {
  id: string;
  source: string;
  target: string;
  type: GraphEdgeType;
  confidence: number;
  metadata?: Record<string, unknown>;
}

Tour:

interface GuidedTour {
  id: string;
  title: string;
  description: string;
  persona: PersonaType;
  entryNodeId?: string;
  steps: TourStep[];
  createdAt: string;
}

interface TourStep {
  id: string;
  nodeId: string;
  title: string;
  explanation: string;
  whyItMatters: string;
  nextHint?: string;
}

Persona:

type PersonaType =
  | "junior_developer"
  | "senior_developer"
  | "architect"
  | "pm"
  | "qa"
  | "devops"
  | "data_engineer"
  | "security_reviewer";

DATABASE SCHEMA

Use SQLite tables:

nodes:
- id text primary key
- type text
- name text
- path text
- language text
- layer text
- summary text
- long_summary text
- start_line integer
- end_line integer
- hash text
- importance_score real
- metadata_json text
- created_at text
- updated_at text

edges:
- id text primary key
- source text
- target text
- type text
- confidence real
- metadata_json text

files:
- path text primary key
- hash text
- language text
- size_bytes integer
- loc integer
- last_indexed_at text
- parse_status text
- summary_status text

tours:
- id text primary key
- title text
- description text
- persona text
- entry_node_id text
- steps_json text
- created_at text

summaries:
- node_id text primary key
- summary text
- long_summary text
- model text
- prompt_hash text
- updated_at text

Create indexes:
- nodes(path)
- nodes(type)
- nodes(layer)
- edges(source)
- edges(target)
- edges(type)
- files(hash)

SCANNING REQUIREMENTS

Implement scanner that:
1. accepts a repo root,
2. reads .gitignore,
3. applies default ignore patterns,
4. detects language by extension,
5. computes file hash,
6. computes LOC,
7. stores file inventory.

Default ignore:
- .git
- node_modules
- dist
- build
- coverage
- .next
- .turbo
- venv
- .venv
- env
- __pycache__
- .pytest_cache
- .mypy_cache
- target
- bin
- obj
- vendor
- logs
- *.lock if configured
- large binary files
- images and media by default unless config enables them

Supported text extensions initially:
- .ts, .tsx, .js, .jsx
- .py
- .java
- .cs
- .go
- .rs
- .sql
- .json
- .yaml, .yml
- .md
- .html
- .css, .scss

Large file handling:
- skip files over configurable max size, default 1 MB
- still create file node with skipped status
- do not send large files to LLM directly

INCREMENTAL INDEXING

Implement file_hashes.json and files table.

On each run:
- new file: parse and insert
- changed file: remove old symbol nodes for that file, reparse, update edges
- unchanged file: reuse previous parse and summary
- deleted file: remove file node, child symbols, related edges

Commands:
understand index /path/to/repo
understand index /path/to/repo --force
understand index /path/to/repo --changed-only
understand index /path/to/repo --no-llm

AST PARSING

Implement parser abstraction:

interface ParsedFile {
  path: string;
  language: string;
  imports: ParsedImport[];
  symbols: ParsedSymbol[];
  routes?: ParsedRoute[];
  databaseRefs?: ParsedDatabaseRef[];
}

interface ParsedSymbol {
  id: string;
  type: "function" | "class" | "method";
  name: string;
  startLine: number;
  endLine: number;
  signature?: string;
  parentName?: string;
  calls?: string[];
}

Start with:
- TypeScript/JavaScript parser
- Python parser
- Generic regex fallback parser

For TypeScript/JavaScript:
- extract imports
- extract exported functions/classes
- extract normal functions
- extract arrow functions assigned to const
- extract classes and methods
- detect common route patterns:
  app.get, app.post, router.get, router.post, router.put, router.delete

For Python:
- extract import and from import
- extract classes
- extract functions
- extract methods
- detect decorators
- detect Flask/FastAPI routes if possible

Generic parser:
- create file node
- simple import-like extraction
- simple function/class regex
- no hallucinated edges

GRAPH BUILDING

Create graph nodes:
- repository node
- folder nodes
- file nodes
- symbol nodes

Create edges:
- repository contains top folders
- folders contain folders/files
- files contain functions/classes
- classes contain methods
- file imports file/module where resolvable
- function calls symbol where resolvable
- routes_to edges for routes
- tested_by edges when test files correspond to source files

Path resolution:
- resolve relative imports for JS/TS/Python
- resolve index files
- support tsconfig paths later, but create basic resolver now
- unresolved imports should still be stored in metadata

Importance ranking:
Calculate importanceScore using:
- number of incoming edges
- number of outgoing edges
- file LOC
- entry point likelihood
- route/controller likelihood
- service likelihood
- database/config likelihood
- recent git change frequency if available

Entry point detection:
- package.json scripts
- src/main.ts
- src/index.ts
- src/App.tsx
- main.py
- app.py
- manage.py
- server.ts
- routes
- controllers

LAYER DETECTION

Implement rule-based layer detection first.

Rules:
ui:
- components, pages, views, screens, frontend, client
- React/Vue/Svelte files
- .tsx with JSX components

api:
- routes, controllers, endpoints, api
- Express/FastAPI/Flask route files

service:
- services, usecases, managers, domain services

data:
- models, repositories, dao, db, database, prisma, migrations, sql

utility:
- utils, helpers, common, shared

config:
- config, settings, env, package.json, tsconfig, yaml config

test:
- test, tests, spec, __tests__

script:
- scripts, cli, tools

unknown:
- fallback

LLM may be used only to refine layer if confidence is low.

LLM PROVIDER

Implement abstraction:

interface LLMProvider {
  complete(input: LLMRequest): Promise<LLMResponse>;
}

Support:
- no-op provider
- OpenAI-compatible provider using:
  OPENAI_API_KEY
  OPENAI_BASE_URL optional
  OPENAI_MODEL optional

If no API key:
- skip LLM
- dashboard still works

LLM summarization must be safe:
- summarize only selected files
- do not send entire repo
- enforce max chars per request
- chunk large files
- cache by file hash and prompt hash

SUMMARY PROMPTS

File summary prompt:

You are analyzing a source code file for a codebase knowledge graph.
Return strict JSON only.

Input:
- path
- language
- imports
- symbols
- selected code snippet

Return:
{
  "summary": "1-2 sentence purpose",
  "longSummary": "clear explanation of what this file does",
  "layer": "ui|api|service|data|utility|config|test|script|unknown",
  "domainConcepts": ["..."],
  "risks": ["..."],
  "entryPointLikelihood": 0.0
}

Function summary prompt:

Return strict JSON only:
{
  "summary": "...",
  "inputs": ["..."],
  "outputs": ["..."],
  "sideEffects": ["..."],
  "risks": ["..."]
}

Persona answer prompt:

Given:
- persona
- user question
- relevant graph nodes
- relevant summaries
- selected code snippets

Answer according to persona:
junior_developer:
- explain simply
- define concepts
- include learning path

senior_developer:
- concise
- focus dependencies, risks, exact files

architect:
- focus layers, boundaries, coupling, flows

pm:
- no deep code unless necessary
- explain user/business behavior

qa:
- focus test cases, edge cases, regressions

devops:
- focus deployment, config, runtime, observability

security_reviewer:
- focus trust boundaries, secrets, injection, auth, data exposure

GUIDED TOURS

Implement tour builder.

Tour generation should work in two modes:
1. deterministic without LLM,
2. polished with LLM if available.

Tour types:
- Project overview tour
- App startup tour
- UI to API to data flow tour
- Authentication tour if auth detected
- Database flow tour if DB detected
- Testing tour
- Configuration/deployment tour
- Change safety tour

Deterministic algorithm:
1. find entry nodes,
2. follow imports/calls up to depth 3,
3. group by layer,
4. choose highest importance nodes,
5. create steps.

LLM tour polishing:
- convert steps into readable explanations
- persona-specific versions

Dashboard tour requirements:
- show tour list
- start tour
- highlight current graph node
- next/previous controls
- show explanation
- allow changing persona during tour

PERSONA DETECTION

Implement manual persona selector and automatic classifier.

Manual personas:
- Junior Developer
- Senior Developer
- Architect
- Product Manager
- QA Engineer
- DevOps Engineer
- Security Reviewer
- Data Engineer

Automatic detection:
Given user question, classify into persona.
If uncertain, keep selected persona.

Rules without LLM:
- “explain simply”, “new to code” → junior_developer
- “architecture”, “boundaries”, “coupling” → architect
- “risk”, “tests”, “edge cases” → qa
- “deploy”, “env”, “docker”, “ci” → devops
- “security”, “auth”, “secret”, “vulnerability” → security_reviewer
- “feature”, “user”, “business” → pm
- default senior_developer

DASHBOARD REQUIREMENTS

Dashboard must not render entire graph by default.

Initial overview:
- repository summary
- file count
- node count
- edge count
- layer distribution
- top important files
- entry points
- recent changed files if available

Graph page:
- lazy graph loading
- modes:
  1. overview by folders/layers
  2. folder view
  3. file neighborhood view
  4. dependency path view
  5. tour view
  6. diff impact view

Graph rendering:
- use React Flow
- display only a limited subset by default
- max visible nodes configurable, default 300
- expand node on click
- collapse node
- filter by layer
- filter by node type
- search and focus node
- show incoming/outgoing edges

Node details panel:
- name
- type
- path
- layer
- summary
- long summary
- imports
- callers
- callees
- contained symbols
- related tests
- risk notes
- open file path display

Layer legend:
- ui
- api
- service
- data
- utility
- config
- test
- script
- unknown

Search:
- fuzzy search using Fuse.js
- search over name, path, summary, layer, type
- clicking result opens node neighborhood

File explorer:
- folder tree
- file status
- layer badge
- importance score
- summary status

Diff impact page:
- show changed files
- direct impact
- 1-hop affected nodes
- 2-hop affected nodes
- likely tests
- risk level

API SERVER

Implement local API server.

Endpoints:
GET /api/overview
GET /api/nodes/:id
GET /api/nodes/:id/neighborhood?depth=1&limit=200
GET /api/folders?path=...
GET /api/search?q=...
GET /api/layers
GET /api/tours
GET /api/tours/:id
GET /api/diff
GET /api/impact?base=HEAD
POST /api/summarize/node/:id
POST /api/persona/detect
POST /api/query

Do not expose arbitrary file write APIs.

CLI REQUIREMENTS

Implement CLI command “understand”.

Commands:

understand init
- creates .my-understand/config.json

understand scan <repo>
- scans files only
- writes files inventory

understand index <repo>
- scans
- parses
- builds graph
- stores SQLite
- exports knowledge graph

understand index <repo> --no-llm
- deterministic only

understand summarize <repo>
- summarize important or changed nodes

understand summarize <repo> --top 100
- summarize top ranked files

understand serve <repo>
- starts local API and dashboard

understand export <repo>
- exports knowledge-graph.json, nodes.jsonl, edges.jsonl

understand diff <repo>
- shows changed files and impact

understand query <repo> "How does login work?"
- graph retrieval plus optional LLM answer

NPM WORKSPACE REQUIREMENTS

Use npm only.

Root package.json must use npm workspaces:

{
  "name": "understand-anything",
  "private": true,
  "workspaces": [
    "packages/core",
    "packages/cli",
    "packages/server",
    "packages/dashboard"
  ],
  "scripts": {
    "build": "npm run build --workspaces",
    "dev": "npm run dev --workspace=@understand-anything/dashboard",
    "test": "npm run test --workspaces",
    "understand": "npm run start --workspace=@understand-anything/cli --"
  }
}

Do not use pnpm commands anywhere.

Use these commands in documentation and acceptance tests:

npm install
npm run build
npm run understand -- init
npm run understand -- index /path/to/repo --no-llm
npm run understand -- serve /path/to/repo

The CLI package should also expose a bin named understand so that, after npm install or npm link, this works:

understand init
understand index /path/to/repo --no-llm
understand serve /path/to/repo

SCALING DESIGN

Must support 2000+ files.

Mandatory scaling features:
1. incremental indexing,
2. SQLite storage,
3. JSONL export,
4. lazy graph queries,
5. no full graph rendering,
6. file hash cache,
7. summary cache,
8. top-N summarization,
9. on-demand summarization,
10. configurable ignore rules.

Graph query examples:
- get overview graph:
  folders + top files + layer nodes only
- get node neighborhood:
  node + incoming/outgoing edges up to depth N
- get folder graph:
  direct children only
- get route flow:
  route → handler → service → repository/database

PERFORMANCE CONSTRAINTS

For 2000 files:
- scanner should finish quickly
- parser should process files in batches
- LLM should not be called for every file by default
- initial dashboard load should request only overview
- graph view should stay under max visible node limit

Use batching and concurrency:
- scanner concurrency configurable
- parser concurrency configurable
- summarizer concurrency low, default 2

CONFIG FILE

.my-understand/config.json:

{
  "maxFileSizeBytes": 1000000,
  "includeExtensions": [".ts", ".tsx", ".js", ".jsx", ".py", ".java", ".cs", ".go", ".rs", ".sql", ".json", ".yaml", ".yml", ".md"],
  "excludePatterns": ["node_modules", "dist", "build", ".git"],
  "llm": {
    "enabled": false,
    "provider": "openai-compatible",
    "model": "gpt-4.1-mini",
    "maxCharsPerFile": 12000
  },
  "dashboard": {
    "maxVisibleNodes": 300
  },
  "indexing": {
    "parserConcurrency": 8,
    "summarizerConcurrency": 2
  }
}

QUERY SYSTEM

Implement retrieval flow:

User question:
1. detect persona,
2. fuzzy search graph nodes,
3. expand top node neighborhoods,
4. gather summaries,
5. include selected snippets if needed,
6. answer using persona template,
7. return cited node/file references.

Without LLM:
- return relevant nodes, summaries, paths, and graph connections.

With LLM:
- generate explanation.

DIFF IMPACT ANALYSIS

Use git diff.

Commands:
- git diff --name-only HEAD
- git diff --name-only main...HEAD if branch exists
- allow base argument

Impact logic:
1. changed file nodes,
2. symbols inside changed files,
3. incoming dependents,
4. outgoing dependencies,
5. related tests,
6. affected tours,
7. affected layers,
8. risk score.

Risk score:
- high if changed node has many incoming edges
- high if auth/security/payment/database/config files
- medium if service/API files
- low if isolated utility/test/docs

TESTING

Add basic tests for:
- scanner ignore rules,
- language detection,
- file hash,
- layer detection,
- graph node creation,
- edge creation,
- SQLite insert/query,
incremental indexing changed/unchanged/deleted files,
- fuzzy search,
- impact analysis.

README

Write a strong README with:

1. What this project does
2. Architecture diagram in Mermaid
3. Installation
4. Usage
5. CLI commands
6. How scaling works for 2000+ files
7. How LLM is used safely
8. Dashboard features
9. Data storage
10. Limitations
11. Future work

MERMAID ARCHITECTURE

Include this in README:

flowchart TD
  A[Repository] --> B[Scanner]
  B --> C[File Hash Cache]
  B --> D[AST Parser]
  D --> E[Graph Builder]
  E --> F[SQLite Graph Store]
  F --> G[Dashboard API]
  G --> H[React Dashboard]
  F --> I[Search]
  F --> J[Guided Tours]
  F --> K[Diff Impact]
  F --> L[LLM Summarizer]
  L --> F

IMPLEMENTATION ORDER

Follow this exact order:

Phase 1:
- create npm workspace
- create packages
- create shared schema
- create SQLite storage
- create scanner
- create CLI init and scan

Phase 2:
- implement parser abstraction
- implement JS/TS parser
- implement Python parser
- implement generic parser
- implement graph builder
- implement index command

Phase 3:
- implement layer detection
- implement importance ranking
- implement JSONL and knowledge-graph export

Phase 4:
- implement API server
- implement dashboard shell
- implement overview page
- implement graph page with lazy neighborhood loading
- implement node details panel
- implement search
- implement layer filters

Phase 5:
- implement guided tours
- implement persona selector
- implement persona detection rules
- implement tour panel

Phase 6:
- implement LLM provider abstraction
- implement optional summarization
- implement cached summaries
- implement query command and /api/query

Phase 7:
- implement git diff impact
- implement diff page
- implement related tests detection

Phase 8:
- polish UI
- add README
- add tests
- verify with a sample repo

QUALITY RULES

- TypeScript strict mode.
- npm only.
- No pnpm.
- No pnpm-workspace.yaml.
- No hardcoded absolute paths.
- Clear error messages.
- Avoid hallucinated graph edges.
- Mark uncertain edges with lower confidence.
- Keep LLM optional.
- Never send whole repo to LLM.
- Never render full graph by default.
- Use deterministic extraction wherever possible.
- Cache everything expensive.
- Support partial failures: if one file fails to parse, continue indexing.
- Store parse errors in metadata.

ACCEPTANCE CRITERIA

The project is complete when:

1. Running:

npm install
npm run build

works.

2. Running:

npm run understand -- init
npm run understand -- index /path/to/some/repo --no-llm
npm run understand -- serve /path/to/some/repo

creates .my-understand, builds a graph, and opens/serves the dashboard.

3. After linking or installing the CLI locally, this also works:

understand init
understand index /path/to/some/repo --no-llm
understand serve /path/to/some/repo

4. Dashboard shows:
- overview stats,
- layer distribution,
- searchable nodes,
- lazy graph view,
- node details,
- file explorer,
- guided tours,
- persona selector,
- diff impact page.

5. Incremental indexing works:
- unchanged files are skipped,
- changed files are reparsed,
- deleted files are removed.

6. Large repo behavior:
- does not render all nodes at once,
- graph API supports neighborhood queries,
- SQLite is used for storage.

7. LLM disabled mode works fully for graph, search, layers, tours, and diff.

8. LLM enabled mode adds summaries, persona explanations, and polished tours.

Begin implementation now. Create files, code, tests, and README. Do not stop at planning. Implement the complete working version step by step.