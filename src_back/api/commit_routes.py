from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List

router = APIRouter()

# Dependency to get graph_db from main app
def get_graph_db():
    from main import engine
    return engine.graph_db

@router.get("/repository/{repo_id}/commits")
def get_commits(repo_id: str, graph_db = Depends(get_graph_db)) -> List[Dict]:
    """Get all commits for a repository"""
    with graph_db.driver.session() as session:
        result = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:HAS_COMMIT]->(c:Commit)
            OPTIONAL MATCH (c)-[:AUTHORED_BY]->(u:User)
            RETURN c.commit_hash as hash, c.message as message, 
                   c.timestamp as timestamp, u.email as author
            ORDER BY c.timestamp DESC
            """, repo_id=repo_id)
        return [dict(r) for r in result]

@router.get("/repository/{repo_id}/commit/{commit_hash}/files")
def get_commit_files(repo_id: str, commit_hash: str, graph_db = Depends(get_graph_db)) -> List[Dict]:
    """Get all files at a specific commit"""
    with graph_db.driver.session() as session:
        result = session.run("""
            MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
            MATCH (f:File)-[:VERSION_AT]->(c)
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)-[:VERSION_AT]->(c)
            RETURN f.file_path as path, v.hash as content_hash
            """, repo_id=repo_id, commit_hash=commit_hash)
        return [dict(r) for r in result]

@router.get("/repository/{repo_id}/compare/{commit1}/{commit2}")
def compare_commits(repo_id: str, commit1: str, commit2: str, graph_db = Depends(get_graph_db)) -> Dict:
    """Compare two commits to see what changed"""
    with graph_db.driver.session() as session:
        # Get files in both commits
        result = session.run("""
            MATCH (c1:Commit {repo_id: $repo_id, commit_hash: $commit1})
            MATCH (c2:Commit {repo_id: $repo_id, commit_hash: $commit2})
            
            OPTIONAL MATCH (f1:File)-[:VERSION_AT]->(c1)
            OPTIONAL MATCH (f1)-[:HAS_VERSION]->(v1:Version)-[:VERSION_AT]->(c1)
            
            OPTIONAL MATCH (f2:File {file_path: f1.file_path})-[:VERSION_AT]->(c2)
            OPTIONAL MATCH (f2)-[:HAS_VERSION]->(v2:Version)-[:VERSION_AT]->(c2)
            
            RETURN f1.file_path as path, v1.hash as hash1, v2.hash as hash2
            """, repo_id=repo_id, commit1=commit1, commit2=commit2)
        
        files = [dict(r) for r in result]
        
        added = [f['path'] for f in files if f['hash1'] and not f['hash2']]
        removed = [f['path'] for f in files if not f['hash1'] and f['hash2']]
        modified = [f['path'] for f in files if f['hash1'] and f['hash2'] and f['hash1'] != f['hash2']]
        unchanged = [f['path'] for f in files if f['hash1'] == f['hash2']]
        
        return {
            "commit1": commit1[:8],
            "commit2": commit2[:8],
            "added": added,
            "removed": removed,
            "modified": modified,
            "unchanged": unchanged,
            "summary": {
                "total_changes": len(added) + len(removed) + len(modified),
                "files_added": len(added),
                "files_removed": len(removed),
                "files_modified": len(modified)
            }
        }
