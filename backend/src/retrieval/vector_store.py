import chromadb
from typing import List, Dict

class VectorStore:
    def __init__(self, persist_directory: str):
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self.client.get_or_create_collection(
            name="code_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
    
    def add_code_chunk(self, chunk_id: str, code: str, metadata: Dict):
        self.collection.add(
            ids=[chunk_id],
            documents=[code],
            metadatas=[metadata]
        )
    
    def add_batch(self, chunks: List[Dict]):
        ids = [c['id'] for c in chunks]
        documents = [c['code'] for c in chunks]
        metadatas = [c['metadata'] for c in chunks]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )
    
    def search(self, query: str, n_results: int = 5) -> List[Dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        return [
            {
                'id': results['ids'][0][i],
                'code': results['documents'][0][i],
                'metadata': results['metadatas'][0][i],
                'distance': results['distances'][0][i]
            }
            for i in range(len(results['ids'][0]))
        ]
    
    def clear(self):
        self.client.delete_collection("code_embeddings")
        self.collection = self.client.get_or_create_collection(
            name="code_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
