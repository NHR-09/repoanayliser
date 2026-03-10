from typing import List, Dict, Set
from .vector_store import VectorStore
from ..graph.graph_db import GraphDB

class RetrievalEngine:
    def __init__(self, vector_store: VectorStore, graph_db: GraphDB):
        self.vector_store = vector_store
        self.graph_db = graph_db
    
    def retrieve_evidence(self, query: str, context_file: str = None) -> Dict:
        semantic_results = self.vector_store.search(query, n_results=10)
        
        structural_context = set()
        if context_file:
            deps = self.graph_db.get_dependencies(context_file)
            affected = self.graph_db.get_affected_files(context_file)
            structural_context = set(deps + affected)
        
        evidence = self._merge_results(semantic_results, structural_context)
        
        return {
            'query': query,
            'evidence': evidence,
            'context_file': context_file
        }
    
    def _merge_results(self, semantic: List[Dict], structural: Set[str]) -> List[Dict]:
        merged = []
        
        for result in semantic:
            file_path = result['metadata'].get('file_path', '')
            score = 1.0 - result['distance']
            
            if file_path in structural:
                score += 0.5
            
            merged.append({
                'file': file_path,
                'code': result['code'],
                'score': score,
                'metadata': result['metadata']
            })
        
        merged.sort(key=lambda x: x['score'], reverse=True)
        return merged[:5]
