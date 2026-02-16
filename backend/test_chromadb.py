"""Test ChromaDB functionality"""
import sys
sys.path.append('.')

from src.retrieval.vector_store import VectorStore
from src.config import settings

def test_chromadb():
    print("🧪 Testing ChromaDB...")
    
    try:
        # Initialize vector store
        print(f"📁 ChromaDB path: {settings.chroma_path}")
        vector_store = VectorStore(settings.chroma_path)
        print("✅ ChromaDB initialized")
        
        # Test adding data
        test_data = {
            'id': 'test_file_1',
            'code': 'def hello_world():\n    print("Hello, World!")',
            'metadata': {'file': 'test.py', 'language': 'python'}
        }
        
        vector_store.add_code_chunk(
            test_data['id'],
            test_data['code'],
            test_data['metadata']
        )
        print("✅ Added test data")
        
        # Test search
        results = vector_store.search("hello world function", n_results=1)
        print(f"✅ Search returned {len(results)} results")
        
        if results:
            print(f"   📄 Found: {results[0]['id']}")
            print(f"   📊 Distance: {results[0]['distance']:.4f}")
            print(f"   💾 Metadata: {results[0]['metadata']}")
        
        # Check collection stats
        collection_count = vector_store.collection.count()
        print(f"✅ Collection has {collection_count} documents")
        
        print("\n✅ ChromaDB is WORKING!")
        return True
        
    except Exception as e:
        print(f"\n❌ ChromaDB ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_chromadb()
