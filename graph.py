from pathlib import Path

code = r'''
"""
graphify_ops.py

Utilities for working with Graphify-style graph.json files and converting them into
prompt-ready graph slices for documentation generation.

Design goals
------------
1. Accept the stable public Graphify extraction schema:
   {
     "nodes": [{"id": "...", "label": "...", "source_file": "...", "source_location": "..."}],
     "edges": [{"source": "...", "target": "...", "relation": "...", "confidence": "..."}]
   }

2. Also accept common NetworkX node-link exports, because Graphify's build/export
   pipeline uses NetworkX graphs.

3. Provide the operations that matter for doc generation:
   - load and normalize graph
   - index nodes / edges
   - identify documentable symbols
   - callers / callees / children / parents
   - bounded graph slices for prompts
   - bottom-up generation order heuristics
   - impact propagation
   - prompt context builders for method/class/file/flow/architecture docs

This is intentionally defensive:
- It preserves unknown fields
- It never assumes one exact internal Graphify export version
- It treats many relationships as candidates unless they are explicit
"""

from __future__ import annotations

import json
import re
from collections import defaultdict, deque
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


# -----------------------------
# Data model
# -----------------------------

VALID_CONFIDENCE = {"EXTRACTED", "INFERRED", "AMBIGUOUS"}
STRUCTURAL_RELATIONS = {
    "contains", "declares", "defined_in", "member_of", "child_of", "parent_of",
}
CALL_RELATIONS = {
    "calls", "invokes", "uses", "references",
}
TYPE_RELATIONS = {
    "inherits", "implements", "extends", "overrides",
}
IMPORT_RELATIONS = {
    "imports", "imports_from", "depends_on",
}
DOC_TARGET_KINDS = {
    "repository",
    "directory",
    "file",
    "module",
    "namespace",
    "class",
    "interface",
    "struct",
    "trait",
    "enum",
    "function",
    "method",
    "property",
    "field",
    "route",
    "endpoint",
    "schema",
    "config",
}


@dataclass
class GNode:
    id: str
    label: str = ""
    source_file: Optional[str] = None
    source_location: Optional[str] = None
    kind: Optional[str] = None
    language: Optional[str] = None
    attrs: Dict[str, Any] = field(default_factory=dict)

    @property
    def display(self) -> str:
        return self.label or self.id


@dataclass
class GEdge:
    source: str
    target: str
    relation: str
    confidence: str = "EXTRACTED"
    attrs: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GraphSlice:
    target_id: str
    target: GNode
    parent: Optional[GNode]
    containment_path: List[GNode]
    children: List[GNode]
    direct_callees: List[Tuple[GNode, GEdge]]
    direct_callers: List[Tuple[GNode, GEdge]]
    imports: List[Tuple[GNode, GEdge]]
    inheritance: List[Tuple[GNode, GEdge]]
    related_summaries: List[Dict[str, Any]]
    notes: List[str] = field(default_factory=list)

    def to_prompt_dict(self) -> Dict[str, Any]:
        def node_brief(n: GNode) -> Dict[str, Any]:
            return {
                "id": n.id,
                "label": n.label,
                "kind": n.kind,
                "source_file": n.source_file,
                "source_location": n.source_location,
            }

        def edge_brief(pair: Tuple[GNode, GEdge]) -> Dict[str, Any]:
            node, edge = pair
            d = node_brief(node)
            d["relation"] = edge.relation
            d["confidence"] = edge.confidence
            return d

        return {
            "target": node_brief(self.target),
            "parent": node_brief(self.parent) if self.parent else None,
            "containment_path": [node_brief(n) for n in self.containment_path],
            "children": [node_brief(n) for n in self.children],
            "direct_callees": [edge_brief(p) for p in self.direct_callees],
            "direct_callers": [edge_brief(p) for p in self.direct_callers],
            "imports": [edge_brief(p) for p in self.imports],
            "inheritance": [edge_brief(p) for p in self.inheritance],
            "related_summaries": self.related_summaries,
            "notes": self.notes,
        }


@dataclass
class CoverageRecord:
    symbol_id: str
    kind: Optional[str]
    path: Optional[str]
    status: str = "pending"       # pending | done | verified | stale | skipped
    source_hash: Optional[str] = None
    summary_hash: Optional[str] = None
    parent_id: Optional[str] = None
    dependency_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GraphifyOpsError(Exception):
    """Base exception for graphify_ops."""


# -----------------------------
# Main graph wrapper
# -----------------------------

class GraphifyGraph:
    def __init__(self, nodes: List[GNode], edges: List[GEdge], raw: Optional[dict] = None):
        self.raw = raw or {}
        self.nodes: Dict[str, GNode] = {n.id: n for n in nodes}
        self.edges: List[GEdge] = edges

        self.out_edges: Dict[str, List[GEdge]] = defaultdict(list)
        self.in_edges: Dict[str, List[GEdge]] = defaultdict(list)
        self.relation_index_out: Dict[Tuple[str, str], List[GEdge]] = defaultdict(list)
        self.relation_index_in: Dict[Tuple[str, str], List[GEdge]] = defaultdict(list)

        for e in edges:
            if e.source not in self.nodes or e.target not in self.nodes:
                continue
            self.out_edges[e.source].append(e)
            self.in_edges[e.target].append(e)
            self.relation_index_out[(e.source, e.relation)].append(e)
            self.relation_index_in[(e.target, e.relation)].append(e)

        self._infer_missing_kinds()

    # -------------------------
    # Loading
    # -------------------------
    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> "GraphifyGraph":
        """
        Accepts:
        1) Extraction-style:
           {"nodes":[...], "edges":[...]}
        2) NetworkX node-link style:
           {"nodes":[...], "links":[...]} or {"nodes":[...], "edges":[...]} where
           edges may use "from"/"to" or "source"/"target".
        3) Slight variants where node/edge arrays are nested.
        """
        nodes_payload = None
        edges_payload = None

        if isinstance(data, dict):
            if "nodes" in data:
                nodes_payload = data["nodes"]
            elif "graph" in data and isinstance(data["graph"], dict) and "nodes" in data["graph"]:
                nodes_payload = data["graph"]["nodes"]

            if "edges" in data:
                edges_payload = data["edges"]
            elif "links" in data:
                edges_payload = data["links"]
            elif "graph" in data and isinstance(data["graph"], dict):
                graph = data["graph"]
                if "edges" in graph:
                    edges_payload = graph["edges"]
                elif "links" in graph:
                    edges_payload = graph["links"]

        if not isinstance(nodes_payload, list) or not isinstance(edges_payload, list):
            raise GraphifyOpsError(
                "Unsupported graph.json shape. Expected nodes + edges/links arrays."
            )

        nodes = [cls._normalize_node(n) for n in nodes_payload]
        edges = [cls._normalize_edge(e) for e in edges_payload]
        return cls(nodes=nodes, edges=edges, raw=data)

    @classmethod
    def from_path(cls, path: str | Path) -> "GraphifyGraph":
        p = Path(path)
        data = json.loads(p.read_text(encoding="utf-8"))
        return cls.from_json(data)

    @staticmethod
    def _normalize_node(n: Dict[str, Any]) -> GNode:
        if not isinstance(n, dict):
            raise GraphifyOpsError(f"Invalid node entry: {n!r}")
        node_id = str(n.get("id", "")).strip()
        if not node_id:
            raise GraphifyOpsError(f"Node missing 'id': {n!r}")

        label = str(n.get("label", n.get("name", node_id)))
        kind = n.get("kind") or n.get("type") or n.get("node_type")
        source_file = n.get("source_file") or n.get("file") or n.get("path")
        source_location = n.get("source_location") or n.get("location") or n.get("loc")
        language = n.get("language") or n.get("lang")

        attrs = dict(n)
        for k in ["id", "label", "name", "kind", "type", "node_type", "source_file", "file", "path",
                  "source_location", "location", "loc", "language", "lang"]:
            attrs.pop(k, None)

        return GNode(
            id=node_id,
            label=label,
            source_file=source_file,
            source_location=source_location,
            kind=kind,
            language=language,
            attrs=attrs,
        )

    @staticmethod
    def _normalize_edge(e: Dict[str, Any]) -> GEdge:
        if not isinstance(e, dict):
            raise GraphifyOpsError(f"Invalid edge entry: {e!r}")

        source = e.get("source", e.get("from", e.get("u")))
        target = e.get("target", e.get("to", e.get("v")))
        relation = e.get("relation", e.get("type", e.get("label", "related_to")))
        confidence = str(e.get("confidence", "EXTRACTED")).upper()

        if source is None or target is None:
            raise GraphifyOpsError(f"Edge missing source/target: {e!r}")
        if confidence not in VALID_CONFIDENCE:
            confidence = "EXTRACTED"

        attrs = dict(e)
        for k in ["source", "from", "u", "target", "to", "v", "relation", "type", "label", "confidence"]:
            attrs.pop(k, None)

        return GEdge(
            source=str(source),
            target=str(target),
            relation=str(relation),
            confidence=confidence,
            attrs=attrs,
        )

    # -------------------------
    # Kind inference
    # -------------------------
    def _infer_missing_kinds(self) -> None:
        """
        Conservative heuristic kind inference from node attrs/id/label/source_file.
        This is intentionally approximate, because Graphify supports many file types.
        """
        for node in self.nodes.values():
            if node.kind:
                node.kind = str(node.kind).lower()
                continue

            text = " ".join(
                str(x) for x in [
                    node.id,
                    node.label,
                    node.attrs.get("symbol_kind"),
                    node.attrs.get("category"),
                    node.attrs.get("ast_type"),
                ] if x
            ).lower()

            if node.source_file and Path(str(node.source_file)).suffix:
                suffix = Path(str(node.source_file)).suffix.lower()
                if node.id == node.source_file or text.endswith(suffix):
                    node.kind = "file"
                    continue

            if any(k in text for k in ["class", "struct", "trait"]):
                node.kind = "class"
            elif "interface" in text:
                node.kind = "interface"
            elif "enum" in text:
                node.kind = "enum"
            elif any(k in text for k in ["method", "function", "func", "def "]):
                node.kind = "function"
            elif any(k in text for k in ["module", "namespace", "package"]):
                node.kind = "module"
            elif any(k in text for k in ["dir:", "directory", "folder"]):
                node.kind = "directory"
            elif node.source_file and node.id == node.source_file:
                node.kind = "file"
            elif Path(node.id).suffix:
                node.kind = "file"
            else:
                node.kind = "symbol"

    # -------------------------
    # Basic queries
    # -------------------------
    def get_node(self, node_id: str) -> GNode:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise GraphifyOpsError(f"Unknown node_id: {node_id}") from exc

    def neighbors_out(
        self,
        node_id: str,
        relations: Optional[Set[str]] = None,
        min_confidence: Optional[Set[str]] = None,
    ) -> List[Tuple[GNode, GEdge]]:
        rels = {r.lower() for r in relations} if relations else None
        confs = {c.upper() for c in min_confidence} if min_confidence else None
        out = []
        for e in self.out_edges.get(node_id, []):
            if rels and e.relation.lower() not in rels:
                continue
            if confs and e.confidence.upper() not in confs:
                continue
            tgt = self.nodes.get(e.target)
            if tgt:
                out.append((tgt, e))
        return out

    def neighbors_in(
        self,
        node_id: str,
        relations: Optional[Set[str]] = None,
        min_confidence: Optional[Set[str]] = None,
    ) -> List[Tuple[GNode, GEdge]]:
        rels = {r.lower() for r in relations} if relations else None
        confs = {c.upper() for c in min_confidence} if min_confidence else None
        out = []
        for e in self.in_edges.get(node_id, []):
            if rels and e.relation.lower() not in rels:
                continue
            if confs and e.confidence.upper() not in confs:
                continue
            src = self.nodes.get(e.source)
            if src:
                out.append((src, e))
        return out

    def children(self, node_id: str) -> List[GNode]:
        rels = STRUCTURAL_RELATIONS | {"contains"}
        raw = self.neighbors_out(node_id, relations=rels)
        return [n for n, _ in raw]

    def parent(self, node_id: str) -> Optional[GNode]:
        rels = STRUCTURAL_RELATIONS | {"contains"}
        parents = self.neighbors_in(node_id, relations=rels)
        if parents:
            # Prefer file/class/module parents over generic symbol parents
            parents_sorted = sorted(
                (n for n, _ in parents),
                key=lambda n: (
                    0 if n.kind in {"class", "interface", "struct", "module", "namespace", "file", "directory"} else 1,
                    len(n.id),
                ),
            )
            return parents_sorted[0]
        return None

    def containment_path(self, node_id: str, max_depth: int = 16) -> List[GNode]:
        path = []
        seen = set()
        cur = self.get_node(node_id)
        path.append(cur)
        seen.add(cur.id)

        for _ in range(max_depth):
            p = self.parent(cur.id)
            if not p or p.id in seen:
                break
            path.append(p)
            seen.add(p.id)
            cur = p
        path.reverse()
        return path

    def callees(
        self,
        node_id: str,
        include_relations: Optional[Set[str]] = None,
        confidences: Optional[Set[str]] = None,
    ) -> List[Tuple[GNode, GEdge]]:
        rels = include_relations or (CALL_RELATIONS | {"calls"})
        return self.neighbors_out(node_id, relations=rels, min_confidence=confidences)

    def callers(
        self,
        node_id: str,
        include_relations: Optional[Set[str]] = None,
        confidences: Optional[Set[str]] = None,
    ) -> List[Tuple[GNode, GEdge]]:
        rels = include_relations or (CALL_RELATIONS | {"calls"})
        return self.neighbors_in(node_id, relations=rels, min_confidence=confidences)

    def imports(self, node_id: str) -> List[Tuple[GNode, GEdge]]:
        return self.neighbors_out(node_id, relations=IMPORT_RELATIONS)

    def inheritance(self, node_id: str) -> List[Tuple[GNode, GEdge]]:
        return self.neighbors_out(node_id, relations=TYPE_RELATIONS)

    def documentable_nodes(self) -> List[GNode]:
        return [n for n in self.nodes.values() if n.kind in DOC_TARGET_KINDS]

    # -------------------------
    # Prompt-ready graph slice
    # -------------------------
    def graph_slice(
        self,
        node_id: str,
        *,
        max_children: int = 20,
        max_callees: int = 8,
        max_callers: int = 8,
        max_imports: int = 10,
        max_inheritance: int = 6,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
        confidence_allow: Optional[Set[str]] = None,
    ) -> GraphSlice:
        """
        Returns the smallest useful local neighborhood for prompt injection.

        Recommended confidence_allow:
        - {"EXTRACTED"} for strict prompts
        - {"EXTRACTED", "INFERRED"} for broader exploratory prompts
        """
        target = self.get_node(node_id)
        parent = self.parent(node_id)
        path = self.containment_path(node_id)

        children = self.children(node_id)[:max_children]
        callees = self.callees(node_id, confidences=confidence_allow)[:max_callees]
        callers = self.callers(node_id, confidences=confidence_allow)[:max_callers]
        imports = self.imports(node_id)[:max_imports]
        inheritance = self.inheritance(node_id)[:max_inheritance]

        related_ids: List[str] = []
        related_ids.extend([n.id for n in children])
        related_ids.extend([n.id for n, _ in callees])
        related_ids.extend([n.id for n, _ in callers])
        related_ids.extend([n.id for n, _ in imports])
        related_ids.extend([n.id for n, _ in inheritance])

        related_summaries: List[Dict[str, Any]] = []
        if summary_store:
            for rid in related_ids:
                if rid in summary_store:
                    payload = dict(summary_store[rid])
                    payload.setdefault("id", rid)
                    related_summaries.append(payload)

        notes = []
        if not parent:
            notes.append("No explicit structural parent found.")
        if not callees:
            notes.append("No direct callees found under current confidence filter.")
        if not callers:
            notes.append("No direct callers found under current confidence filter.")

        return GraphSlice(
            target_id=node_id,
            target=target,
            parent=parent,
            containment_path=path,
            children=children,
            direct_callees=callees,
            direct_callers=callers,
            imports=imports,
            inheritance=inheritance,
            related_summaries=related_summaries,
            notes=notes,
        )

    # -------------------------
    # Generation ordering
    # -------------------------
    def doc_generation_order(self) -> List[str]:
        """
        Build a bottom-up order for doc generation.

        Strategy:
        1. Prefer documentable nodes only.
        2. Use a pseudo-topological order over explicit call edges among documentable nodes.
        3. Break cycles heuristically by kind priority and lower fan-out first.
        4. Higher-level containers (class/file/module) naturally come later because they
           often contain children that depend on lower-level symbol summaries.

        This is not a mathematically perfect topological sort for arbitrary mixed graphs;
        it is a robust documentation order heuristic.
        """
        doc_ids = {n.id for n in self.documentable_nodes()}

        deps_out: Dict[str, Set[str]] = {nid: set() for nid in doc_ids}
        reverse: Dict[str, Set[str]] = {nid: set() for nid in doc_ids}

        # Containment children should generally be documented before parent.
        for nid in doc_ids:
            for child in self.children(nid):
                if child.id in doc_ids:
                    deps_out[nid].add(child.id)
                    reverse[child.id].add(nid)

        # Explicit call dependencies
        for nid in doc_ids:
            for callee, edge in self.callees(nid, confidences={"EXTRACTED", "INFERRED"}):
                if callee.id in doc_ids:
                    deps_out[nid].add(callee.id)
                    reverse[callee.id].add(nid)

        indegree = {nid: len(deps_out[nid]) for nid in doc_ids}

        def kind_rank(node_id: str) -> int:
            kind = self.nodes[node_id].kind
            order = {
                "function": 0,
                "method": 0,
                "property": 1,
                "field": 1,
                "class": 2,
                "interface": 2,
                "struct": 2,
                "enum": 2,
                "file": 3,
                "module": 4,
                "namespace": 4,
                "directory": 5,
                "repository": 6,
            }
            return order.get(kind or "", 99)

        queue = [
            nid for nid, deg in indegree.items() if deg == 0
        ]
        queue.sort(key=lambda nid: (kind_rank(nid), len(self.out_edges.get(nid, [])), nid))

        result: List[str] = []
        processed: Set[str] = set()

        while queue:
            nid = queue.pop(0)
            if nid in processed:
                continue
            processed.add(nid)
            result.append(nid)

            for parent_id in sorted(reverse.get(nid, [])):
                if parent_id in processed:
                    continue
                if nid in deps_out[parent_id]:
                    deps_out[parent_id].remove(nid)
                    indegree[parent_id] -= 1
                if indegree[parent_id] == 0:
                    queue.append(parent_id)
            queue.sort(key=lambda x: (kind_rank(x), len(self.out_edges.get(x, [])), x))

        # Break residual cycles / unresolved dependencies heuristically.
        leftovers = [nid for nid in doc_ids if nid not in processed]
        leftovers.sort(key=lambda nid: (kind_rank(nid), len(self.out_edges.get(nid, [])), nid))
        result.extend(leftovers)
        return result

    # -------------------------
    # Flow extraction
    # -------------------------
    def shortest_path_ids(
        self,
        source_id: str,
        target_id: str,
        allowed_relations: Optional[Set[str]] = None,
        confidence_allow: Optional[Set[str]] = None,
        max_depth: int = 20,
    ) -> Optional[List[str]]:
        """
        Breadth-first search on directed edges.
        """
        allowed_rels = {r.lower() for r in allowed_relations} if allowed_relations else None
        confs = {c.upper() for c in confidence_allow} if confidence_allow else None

        q = deque([(source_id, [source_id])])
        seen = {source_id}

        while q:
            cur, path = q.popleft()
            if len(path) > max_depth:
                continue
            if cur == target_id:
                return path

            for e in self.out_edges.get(cur, []):
                if allowed_rels and e.relation.lower() not in allowed_rels:
                    continue
                if confs and e.confidence.upper() not in confs:
                    continue
                nxt = e.target
                if nxt in seen or nxt not in self.nodes:
                    continue
                seen.add(nxt)
                q.append((nxt, path + [nxt]))
        return None

    def summarize_path(self, path_ids: List[str]) -> List[Dict[str, Any]]:
        out = []
        for nid in path_ids:
            n = self.get_node(nid)
            out.append({
                "id": n.id,
                "label": n.label,
                "kind": n.kind,
                "source_file": n.source_file,
                "source_location": n.source_location,
            })
        return out

    # -------------------------
    # Impact propagation
    # -------------------------
    def impacted_nodes(
        self,
        changed_node_ids: Iterable[str],
        *,
        include_relations: Optional[Set[str]] = None,
        max_depth: int = 3,
    ) -> Set[str]:
        """
        Propagate impact over structural + caller/callee edges.
        Useful after file or symbol changes.
        """
        rels = include_relations or (STRUCTURAL_RELATIONS | CALL_RELATIONS | IMPORT_RELATIONS | TYPE_RELATIONS | {"calls", "contains"})
        rels = {r.lower() for r in rels}

        impacted: Set[str] = set()
        frontier = deque([(nid, 0) for nid in changed_node_ids if nid in self.nodes])

        while frontier:
            nid, depth = frontier.popleft()
            if nid in impacted:
                continue
            impacted.add(nid)

            if depth >= max_depth:
                continue

            for e in self.out_edges.get(nid, []):
                if e.relation.lower() in rels and e.target in self.nodes and e.target not in impacted:
                    frontier.append((e.target, depth + 1))
            for e in self.in_edges.get(nid, []):
                if e.relation.lower() in rels and e.source in self.nodes and e.source not in impacted:
                    frontier.append((e.source, depth + 1))
        return impacted

    # -------------------------
    # Coverage ledger
    # -------------------------
    def build_coverage_ledger(self) -> Dict[str, CoverageRecord]:
        ledger: Dict[str, CoverageRecord] = {}
        for node in self.documentable_nodes():
            parent = self.parent(node.id)
            deps = [n.id for n, _ in self.callees(node.id, confidences={"EXTRACTED", "INFERRED"})]
            ledger[node.id] = CoverageRecord(
                symbol_id=node.id,
                kind=node.kind,
                path=node.source_file,
                parent_id=parent.id if parent else None,
                dependency_ids=deps,
            )
        return ledger

    # -------------------------
    # Prompt builders
    # -------------------------
    def build_method_prompt_context(
        self,
        node_id: str,
        *,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
        strict: bool = True,
    ) -> Dict[str, Any]:
        """
        Prompt context for method/function docs.
        """
        confs = {"EXTRACTED"} if strict else {"EXTRACTED", "INFERRED"}
        gs = self.graph_slice(node_id, summary_store=summary_store, confidence_allow=confs)
        target = gs.target

        return {
            "target": {
                "id": target.id,
                "label": target.label,
                "kind": target.kind,
                "parent": gs.parent.label if gs.parent else None,
                "defined_in": target.source_file,
                "source_location": target.source_location,
            },
            "hierarchy_path": " -> ".join(n.label or n.id for n in gs.containment_path),
            "direct_callees": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                    "defined_in": n.source_file,
                }
                for n, e in gs.direct_callees
            ],
            "direct_callers": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                    "defined_in": n.source_file,
                }
                for n, e in gs.direct_callers
            ],
            "imports": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                    "defined_in": n.source_file,
                }
                for n, e in gs.imports
            ],
            "related_summaries": gs.related_summaries,
            "notes": gs.notes,
            "instructions": [
                "Generate: Functionality, Parameters, Code Description, Notes, Output Example.",
                "Use only the provided context and the target code.",
                "Prefer explicit graph structure over speculation.",
            ],
        }

    def build_class_prompt_context(
        self,
        node_id: str,
        *,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        node = self.get_node(node_id)
        child_nodes = self.children(node_id)
        child_summaries = []
        if summary_store:
            for child in child_nodes:
                if child.id in summary_store:
                    child_summaries.append(summary_store[child.id])

        return {
            "target": {
                "id": node.id,
                "label": node.label,
                "kind": node.kind,
                "defined_in": node.source_file,
                "source_location": node.source_location,
            },
            "children": [
                {
                    "id": c.id,
                    "label": c.label,
                    "kind": c.kind,
                    "defined_in": c.source_file,
                }
                for c in child_nodes
            ],
            "inheritance": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                }
                for n, e in self.inheritance(node_id)
            ],
            "used_by": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                    "defined_in": n.source_file,
                }
                for n, e in self.callers(node_id, confidences={"EXTRACTED", "INFERRED"})
            ],
            "child_summaries": child_summaries,
            "instructions": [
                "Describe class responsibility, internal method roles, external dependencies, and role in the system.",
                "Synthesize from child summaries when available.",
            ],
        }

    def build_file_prompt_context(
        self,
        node_id: str,
        *,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        node = self.get_node(node_id)
        children = self.children(node_id)

        child_summaries = []
        if summary_store:
            for c in children:
                if c.id in summary_store:
                    child_summaries.append(summary_store[c.id])

        internal_edges = []
        child_ids = {c.id for c in children}
        for cid in child_ids:
            for neighbor, edge in self.callees(cid, confidences={"EXTRACTED", "INFERRED"}):
                if neighbor.id in child_ids:
                    internal_edges.append({
                        "source": self.get_node(cid).label,
                        "target": neighbor.label,
                        "relation": edge.relation,
                        "confidence": edge.confidence,
                    })

        return {
            "target": {
                "id": node.id,
                "label": node.label,
                "kind": node.kind,
                "file": node.source_file or node.id,
            },
            "declared_children": [
                {
                    "id": c.id,
                    "label": c.label,
                    "kind": c.kind,
                }
                for c in children
            ],
            "internal_relations": internal_edges,
            "imports": [
                {
                    "id": n.id,
                    "label": n.label,
                    "relation": e.relation,
                    "confidence": e.confidence,
                }
                for n, e in self.imports(node_id)
            ],
            "child_summaries": child_summaries,
            "instructions": [
                "Explain file purpose, internal organization, major declarations, and how declarations cooperate.",
            ],
        }

    def build_flow_prompt_context(
        self,
        source_id: str,
        target_id: str,
        *,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        path = self.shortest_path_ids(
            source_id,
            target_id,
            allowed_relations=CALL_RELATIONS | {"calls"},
            confidence_allow={"EXTRACTED", "INFERRED"},
            max_depth=20,
        )
        if not path:
            raise GraphifyOpsError(f"No path found between {source_id} and {target_id}")

        steps = self.summarize_path(path)
        summaries = []
        if summary_store:
            for nid in path:
                if nid in summary_store:
                    payload = dict(summary_store[nid])
                    payload.setdefault("id", nid)
                    summaries.append(payload)

        return {
            "flow_start": source_id,
            "flow_end": target_id,
            "steps": steps,
            "step_summaries": summaries,
            "instructions": [
                "Explain the end-to-end execution path step by step.",
                "Highlight control flow, data handoff, side effects, and likely failure points.",
            ],
        }

    def build_architecture_prompt_context(
        self,
        *,
        summary_store: Optional[Dict[str, Dict[str, Any]]] = None,
        max_files: int = 30,
        max_cross_edges: int = 50,
    ) -> Dict[str, Any]:
        """
        Coarse architecture context from documentable files/modules and cross-file edges.
        """
        files = [n for n in self.documentable_nodes() if n.kind in {"file", "module", "namespace", "directory"}]
        files = files[:max_files]

        file_summaries = []
        if summary_store:
            for f in files:
                if f.id in summary_store:
                    file_summaries.append(summary_store[f.id])

        cross_edges = []
        count = 0
        for node in self.documentable_nodes():
            for tgt, edge in self.callees(node.id, confidences={"EXTRACTED", "INFERRED"}):
                src_file = self.get_node(node.id).source_file
                tgt_file = tgt.source_file
                if src_file and tgt_file and src_file != tgt_file:
                    cross_edges.append({
                        "source": node.label,
                        "source_file": src_file,
                        "target": tgt.label,
                        "target_file": tgt_file,
                        "relation": edge.relation,
                        "confidence": edge.confidence,
                    })
                    count += 1
                    if count >= max_cross_edges:
                        break
            if count >= max_cross_edges:
                break

        return {
            "files_or_modules": [
                {
                    "id": f.id,
                    "label": f.label,
                    "kind": f.kind,
                    "source_file": f.source_file,
                }
                for f in files
            ],
            "cross_file_relations": cross_edges,
            "summary_inputs": file_summaries,
            "instructions": [
                "Describe major components, dependency direction, and high-level control/data flows.",
                "Build the architecture summary from lower-level file/module summaries and cross-file relations.",
            ],
        }


# -----------------------------
# Convenience helpers
# -----------------------------

def save_json(path: str | Path, data: Dict[str, Any]) -> None:
    p = Path(path)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def load_summary_store(path: str | Path) -> Dict[str, Dict[str, Any]]:
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def save_summary_store(path: str | Path, store: Dict[str, Dict[str, Any]]) -> None:
    save_json(path, store)


def render_prompt_context_block(context: Dict[str, Any]) -> str:
    """
    Human-readable block for direct prompt injection.
    """
    return json.dumps(context, indent=2, ensure_ascii=False)


# -----------------------------
# CLI
# -----------------------------

def _cmd_inspect(graph: GraphifyGraph) -> None:
    print(f"nodes={len(graph.nodes)} edges={len(graph.edges)}")
    kinds = defaultdict(int)
    for n in graph.nodes.values():
        kinds[n.kind or "unknown"] += 1
    print("kinds:")
    for kind, count in sorted(kinds.items(), key=lambda x: (-x[1], x[0])):
        print(f"  {kind}: {count}")


def _cmd_order(graph: GraphifyGraph) -> None:
    for nid in graph.doc_generation_order():
        n = graph.get_node(nid)
        print(f"{nid}\t{n.kind}\t{n.source_file or ''}")


def _cmd_slice(graph: GraphifyGraph, node_id: str) -> None:
    gs = graph.graph_slice(node_id, confidence_allow={"EXTRACTED", "INFERRED"})
    print(json.dumps(gs.to_prompt_dict(), indent=2, ensure_ascii=False))


def _cmd_method_prompt(graph: GraphifyGraph, node_id: str, summaries: Optional[Path]) -> None:
    store = load_summary_store(summaries) if summaries else None
    ctx = graph.build_method_prompt_context(node_id, summary_store=store, strict=False)
    print(render_prompt_context_block(ctx))


def _cmd_class_prompt(graph: GraphifyGraph, node_id: str, summaries: Optional[Path]) -> None:
    store = load_summary_store(summaries) if summaries else None
    ctx = graph.build_class_prompt_context(node_id, summary_store=store)
    print(render_prompt_context_block(ctx))


def _cmd_file_prompt(graph: GraphifyGraph, node_id: str, summaries: Optional[Path]) -> None:
    store = load_summary_store(summaries) if summaries else None
    ctx = graph.build_file_prompt_context(node_id, summary_store=store)
    print(render_prompt_context_block(ctx))


def _cmd_flow_prompt(graph: GraphifyGraph, source_id: str, target_id: str, summaries: Optional[Path]) -> None:
    store = load_summary_store(summaries) if summaries else None
    ctx = graph.build_flow_prompt_context(source_id, target_id, summary_store=store)
    print(render_prompt_context_block(ctx))


def _cmd_arch_prompt(graph: GraphifyGraph, summaries: Optional[Path]) -> None:
    store = load_summary_store(summaries) if summaries else None
    ctx = graph.build_architecture_prompt_context(summary_store=store)
    print(render_prompt_context_block(ctx))


def _cmd_ledger(graph: GraphifyGraph) -> None:
    ledger = graph.build_coverage_ledger()
    print(json.dumps({k: asdict(v) for k, v in ledger.items()}, indent=2, ensure_ascii=False))


def _cmd_impacted(graph: GraphifyGraph, changed_ids: List[str]) -> None:
    impacted = sorted(graph.impacted_nodes(changed_ids, max_depth=3))
    print(json.dumps(impacted, indent=2, ensure_ascii=False))


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Graphify graph.json operations for doc generation.")
    parser.add_argument("graph", help="Path to graph.json")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("inspect")
    sub.add_parser("order")

    p_slice = sub.add_parser("slice")
    p_slice.add_argument("node_id")

    p_mp = sub.add_parser("method-prompt")
    p_mp.add_argument("node_id")
    p_mp.add_argument("--summaries", type=Path)

    p_cp = sub.add_parser("class-prompt")
    p_cp.add_argument("node_id")
    p_cp.add_argument("--summaries", type=Path)

    p_fp = sub.add_parser("file-prompt")
    p_fp.add_argument("node_id")
    p_fp.add_argument("--summaries", type=Path)

    p_flow = sub.add_parser("flow-prompt")
    p_flow.add_argument("source_id")
    p_flow.add_argument("target_id")
    p_flow.add_argument("--summaries", type=Path)

    p_arch = sub.add_parser("arch-prompt")
    p_arch.add_argument("--summaries", type=Path)

    sub.add_parser("ledger")

    p_imp = sub.add_parser("impacted")
    p_imp.add_argument("changed_ids", nargs="+")

    args = parser.parse_args()
    graph = GraphifyGraph.from_path(args.graph)

    if args.cmd == "inspect":
        _cmd_inspect(graph)
    elif args.cmd == "order":
        _cmd_order(graph)
    elif args.cmd == "slice":
        _cmd_slice(graph, args.node_id)
    elif args.cmd == "method-prompt":
        _cmd_method_prompt(graph, args.node_id, args.summaries)
    elif args.cmd == "class-prompt":
        _cmd_class_prompt(graph, args.node_id, args.summaries)
    elif args.cmd == "file-prompt":
        _cmd_file_prompt(graph, args.node_id, args.summaries)
    elif args.cmd == "flow-prompt":
        _cmd_flow_prompt(graph, args.source_id, args.target_id, args.summaries)
    elif args.cmd == "arch-prompt":
        _cmd_arch_prompt(graph, args.summaries)
    elif args.cmd == "ledger":
        _cmd_ledger(graph)
    elif args.cmd == "impacted":
        _cmd_impacted(graph, args.changed_ids)
    else:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
'''

path = Path("/mnt/data/graphify_ops.py")
path.write_text(code, encoding="utf-8")
print(f"Wrote {path}")
