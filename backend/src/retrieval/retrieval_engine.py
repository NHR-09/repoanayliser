"""
RetrievalEngine
---------------
Hybrid retrieval: structural context from Graphify + graph topology from Neo4j.
ChromaDB has been removed; Graphify is the sole context provider.
"""

from typing import List, Dict, Set
from .graphify_retriever import GraphifyRetriever
from ..graph.graph_db import GraphDB


class RetrievalEngine:
    def __init__(self, graphify_retriever: GraphifyRetriever, graph_db: GraphDB):
        self.graphify = graphify_retriever
        self.graph_db = graph_db

    def retrieve_evidence(self, query: str, context_file: str = None) -> Dict:
        """
        Retrieve evidence for a query using Graphify's knowledge graph.

        1.  Ask Graphify for the top-K structurally-relevant nodes.
        2.  If context_file is provided, also pull Neo4j dependency context
            and boost nodes that belong to dependent files.
        3.  Return a merged, ranked evidence list.
        """
        # Step 1: Graphify structural search
        graphify_nodes = self.graphify.get_context_for_query(query, top_k=12)

        # Step 2: Neo4j structural context for boosting
        structural_context: Set[str] = set()
        if context_file:
            try:
                deps = self.graph_db.get_dependencies(context_file)
                affected = self.graph_db.get_affected_files(context_file)
                structural_context = set(deps + affected)
            except Exception:
                pass

        # Step 3: Build evidence list
        evidence = self._build_evidence(graphify_nodes, structural_context)

        return {
            "query": query,
            "evidence": evidence,
            "context_file": context_file,
            "source": "graphify" if self.graphify.is_available else "unavailable",
        }

    def retrieve_file_context(self, file_path: str) -> Dict:
        """
        Get detailed structural context for a specific file.
        Used by blast-radius and function analysis LLM prompts.
        """
        path_context = self.graphify.get_path_context(file_path)
        return path_context

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_evidence(
        self, nodes: List[Dict], structural_context: Set[str]
    ) -> List[Dict]:
        """
        Convert Graphify nodes to the evidence format expected by LLMReasoner.
        Boost nodes whose file appears in the Neo4j structural context.
        """
        evidence = []
        for node in nodes:
            file_path = node.get("file", "")
            base_score = node.get("_score", 1.0)

            # Boost if file is in structural dependency context
            if any(file_path.endswith(ctx) or ctx.endswith(file_path)
                   for ctx in structural_context):
                base_score += 0.5

            # Build a "code" snippet from available node data
            code_parts = []
            if node.get("name"):
                code_parts.append(f"{node.get('type', 'symbol')}: {node['name']}")
            if node.get("summary") or node.get("docstring"):
                code_parts.append(node.get("summary") or node.get("docstring"))
            if node.get("signature"):
                code_parts.append(f"signature: {node['signature']}")

            evidence.append({
                "file": file_path,
                "code": "\n".join(code_parts) if code_parts else str(node),
                "score": base_score,
                "metadata": {
                    "file_path": file_path,
                    "type": node.get("type", "unknown"),
                    "name": node.get("name", ""),
                },
            })

        # Sort by score descending, take top 5 for LLM prompt
        evidence.sort(key=lambda x: x["score"], reverse=True)
        return evidence[:5]
