"""
Initialize ARCHITECH system
- Creates Neo4j indexes
- Initializes ChromaDB
- Verifies connections
"""

from neo4j import GraphDatabase
import chromadb
import os
from dotenv import load_dotenv

load_dotenv()

def init_neo4j():
    print("🔧 Initializing Neo4j...")
    
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        
        with driver.session() as session:
            # Create indexes
            indexes = [
                "CREATE INDEX file_path IF NOT EXISTS FOR (f:File) ON (f.path)",
                "CREATE INDEX class_name IF NOT EXISTS FOR (c:Class) ON (c.name)",
                "CREATE INDEX function_name IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
                "CREATE INDEX module_name IF NOT EXISTS FOR (m:Module) ON (m.name)"
            ]
            
            for idx in indexes:
                session.run(idx)
                print(f"   ✅ {idx.split('INDEX')[1].split('IF')[0].strip()}")
        
        driver.close()
        print("✅ Neo4j initialized successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ Neo4j initialization failed: {e}\n")
        return False

def init_chromadb():
    print("🔧 Initializing ChromaDB...")
    
    persist_dir = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
    
    try:
        client = chromadb.PersistentClient(path=persist_dir)
        collection = client.get_or_create_collection(
            name="code_embeddings",
            metadata={"hnsw:space": "cosine"}
        )
        
        print(f"   ✅ Collection created at {persist_dir}")
        print("✅ ChromaDB initialized successfully\n")
        return True
        
    except Exception as e:
        print(f"❌ ChromaDB initialization failed: {e}\n")
        return False

def verify_llm():
    print("🔧 Verifying LLM API keys...")
    
    groq_key = os.getenv("GROQ_API_KEY")
    
    if groq_key:
        print("   ✅ Groq API key found")
    else:
        print("   ⚠️  No Groq API key found (set GROQ_API_KEY)")
        print("   System will work but explanations will fail\n")
        return False
    
    print("✅ LLM configuration verified\n")
    return True

if __name__ == "__main__":
    print("🚀 ARCHITECH System Initialization\n")
    
    neo4j_ok = init_neo4j()
    chroma_ok = init_chromadb()
    llm_ok = verify_llm()
    
    if neo4j_ok and chroma_ok:
        print("✅ System ready to use!")
        print("\nStart the server with: python main.py")
    else:
        print("❌ Initialization incomplete. Check errors above.")
