from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List
import uuid
from src.analysis_engine import AnalysisEngine

app = FastAPI(title="ARCHITECH API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = AnalysisEngine()
jobs = {}

class AnalysisRequest(BaseModel):
    repo_url: str

class ImpactRequest(BaseModel):
    file_path: str
    change_type: str = "modify"  # "delete", "modify", or "move"

def run_analysis(job_id: str, repo_url: str):
    try:
        result = engine.analyze_repository(repo_url)
        jobs[job_id] = {
            "status": "completed",
            "result": result,
            "cached": result.get('cached', False)
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"\n{'='*60}")
        print("ERROR IN ANALYSIS:")
        print(error_trace)
        print(f"{'='*60}\n")
        jobs[job_id] = {"status": "failed", "error": str(e), "trace": error_trace}

@app.post("/analyze")
async def analyze_repository(request: AnalysisRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "processing"}
    
    background_tasks.add_task(run_analysis, job_id, request.repo_url)
    
    return {"job_id": job_id, "status": "processing"}

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    return jobs.get(job_id, {"status": "not_found"})

@app.get("/architecture")
async def get_architecture(repo_id: str = None):
    """Get architecture explanation (cached if available)"""
    result = engine.get_architecture_explanation(repo_id)
    return result

@app.get("/patterns")
async def get_patterns(repo_id: str = None):
    """Get detected patterns for a repository"""
    if repo_id and repo_id != engine.current_repo_id:
        if not engine.load_repository_analysis(repo_id):
            return {"error": "Repository not found"}
    
    if engine.pattern_detector:
        return engine.pattern_detector.detect_patterns()
    return {"error": "No analysis completed yet"}

@app.get("/coupling")
async def get_coupling(repo_id: str = None):
    """Get coupling metrics for a repository"""
    if repo_id and repo_id != engine.current_repo_id:
        if not engine.load_repository_analysis(repo_id):
            return {"error": "Repository not found"}
    
    if engine.coupling_analyzer:
        return engine.coupling_analyzer.analyze()
    return {"error": "No analysis completed yet"}

@app.get("/confidence-report")
async def get_confidence_report(repo_id: str = None):
    """Get confidence scores and limitations for architectural claims"""
    # Load repo if specified
    if repo_id and repo_id != engine.current_repo_id:
        if not engine.load_repository_analysis(repo_id):
            return {"error": "Repository not found"}
    
    if not engine.pattern_detector:
        return {"error": "No analysis completed yet"}
    
    from src.analysis.confidence_analyzer import ConfidenceAnalyzer
    analyzer = ConfidenceAnalyzer(
        engine.pattern_detector,
        engine.coupling_analyzer,
        engine.graph_db
    )
    
    return analyzer.get_confidence_report()

@app.post("/impact")
async def analyze_impact(request: ImpactRequest):
    # Ensure current_repo_id is set
    if not engine.current_repo_id:
        # Load the first available repository
        repos = engine.version_tracker.list_repositories()
        if repos:
            engine.load_repository_analysis(repos[0]['repo_id'])
    
    result = engine.analyze_change_impact(request.file_path, request.change_type)
    return result

@app.get("/dependencies/{file_path:path}")
async def get_dependencies(file_path: str):
    resolved = engine._resolve_path(file_path)
    deps = engine.graph_db.get_dependencies(resolved)
    return {"file": file_path, "dependencies": deps}

@app.get("/blast-radius/{file_path:path}")
async def get_blast_radius(file_path: str, change_type: str = "modify", repo_id: str = None):
    """Get blast radius with change simulation (delete/modify/move)"""
    # Load repo if specified
    if repo_id and repo_id != engine.current_repo_id:
        engine.load_repository_analysis(repo_id)
    elif not engine.current_repo_id:
        repos = engine.version_tracker.list_repositories()
        if repos:
            engine.load_repository_analysis(repos[0]['repo_id'])
    
    # Find actual file path in database using flexible matching
    fp_fwd = file_path.replace('\\', '/')
    fp_bs = file_path.replace('/', '\\')
    with engine.graph_db.driver.session() as session:
        result = session.run("""
            MATCH (f:File)
            WHERE f.path ENDS WITH $fp_bs OR f.file_path ENDS WITH $fp_bs
               OR f.path ENDS WITH $fp_fwd OR f.file_path ENDS WITH $fp_fwd
               OR f.path_normalized ENDS WITH $fp_fwd
            RETURN COALESCE(f.file_path, f.path) as actual_path
            LIMIT 1
        """, fp_bs=fp_bs, fp_fwd=fp_fwd).single()
        
        if result:
            actual_path = result['actual_path']
        else:
            actual_path = file_path
    
    result = engine.analyze_change_impact(actual_path, change_type)
    return result

@app.get("/function/{function_name}")
async def get_function_info(function_name: str):
    """Get function usage, callers, and LLM explanation"""
    result = engine.analyze_function(function_name)
    return result

@app.get("/repository/{repo_id}/snapshots")
async def list_snapshots(repo_id: str):
    """List all analysis snapshots for a repository"""
    with engine.graph_db.driver.session() as session:
        result = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:HAS_SNAPSHOT]->(s:Snapshot)
            OPTIONAL MATCH (s)-[:ANALYZED_FILE]->(f:File)
            WITH s, COUNT(DISTINCT f) as file_count
            RETURN s.snapshot_id as snapshot_id,
                   toString(s.created_at) as created_at,
                   s.commit_hash as commit_hash,
                   s.total_files as total_files,
                   s.total_deps as total_deps,
                   s.avg_coupling as avg_coupling,
                   s.cycle_count as cycle_count,
                   file_count
            ORDER BY s.created_at DESC
            """, repo_id=repo_id)
        snapshots = [dict(r) for r in result]
    return {"repo_id": repo_id, "total": len(snapshots), "snapshots": snapshots}

@app.delete("/repository/{repo_id}/snapshot/{snapshot_id}")
async def delete_snapshot(repo_id: str, snapshot_id: str):
    """Delete a specific snapshot"""
    with engine.graph_db.driver.session() as session:
        result = session.run("""
            MATCH (s:Snapshot {snapshot_id: $snapshot_id})
            DETACH DELETE s
            RETURN count(s) as deleted
            """, snapshot_id=snapshot_id)
        record = result.single()
        deleted_count = record['deleted'] if record else 0
    return {"status": "success", "deleted": deleted_count}

@app.get("/repository/{repo_id}/compare-snapshots/{snapshot1}/{snapshot2}")
async def compare_snapshots(repo_id: str, snapshot1: str, snapshot2: str):
    """Compare two analysis snapshots with full architecture, coupling, and dependency changes"""
    result = engine.compare_snapshots(repo_id, snapshot1, snapshot2)
    return result

@app.get("/repositories")
async def list_repositories():
    """List all analyzed repositories with version info"""
    repos = engine.version_tracker.list_repositories()
    for repo in repos:
        repo['current_commit'] = repo.get('current_commit', 'N/A')
    return {"total": len(repos), "repositories": repos}

@app.get("/repository/{repo_id}/commits")
async def get_commits(repo_id: str) -> List[Dict]:
    """Get all commits for a repository"""
    with engine.graph_db.driver.session() as session:
        result = session.run("""
            MATCH (r:Repository {repo_id: $repo_id})-[:HAS_COMMIT]->(c:Commit)
            OPTIONAL MATCH (c)-[:AUTHORED_BY]->(u:User)
            RETURN c.commit_hash as hash, c.message as message, 
                   toString(c.timestamp) as timestamp, u.email as author
            ORDER BY c.timestamp DESC
            """, repo_id=repo_id)
        return [dict(r) for r in result]

@app.get("/repository/{repo_id}/commit/{commit_hash}/files")
async def get_commit_files(repo_id: str, commit_hash: str) -> List[Dict]:
    """Get all files at a specific commit"""
    with engine.graph_db.driver.session() as session:
        result = session.run("""
            MATCH (c:Commit {repo_id: $repo_id, commit_hash: $commit_hash})
            MATCH (f:File)-[:VERSION_AT]->(c)
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)-[:VERSION_AT]->(c)
            RETURN f.file_path as path, v.hash as content_hash
            """, repo_id=repo_id, commit_hash=commit_hash)
        return [dict(r) for r in result]

@app.get("/repository/{repo_id}/compare-architecture/{commit1}/{commit2}")
async def compare_architecture(repo_id: str, commit1: str, commit2: str):
    """Compare architectural changes between two commits"""
    result = engine.compare_architecture(repo_id, commit1, commit2)
    return result

@app.get("/repository/{repo_id}/compare/{commit1}/{commit2}")
async def compare_commits(repo_id: str, commit1: str, commit2: str) -> Dict:
    """Compare two commits"""
    with engine.graph_db.driver.session() as session:
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
        
        return {
            "commit1": commit1[:8],
            "commit2": commit2[:8],
            "added": added,
            "removed": removed,
            "modified": modified,
            "summary": {
                "total_changes": len(added) + len(removed) + len(modified),
                "files_added": len(added),
                "files_removed": len(removed),
                "files_modified": len(modified)
            }
        }

@app.get("/repository/{repo_id}/versions")
async def get_repository_versions(repo_id: str):
    """Get all versions for a repository"""
    versions = engine.version_tracker.get_repository_versions(repo_id)
    return {"repo_id": repo_id, "versions": versions}

@app.get("/repository/{repo_id}/file-history")
async def get_file_history(repo_id: str, file_path: str):
    """Get version history of specific file"""
    history = engine.version_tracker.get_file_history(repo_id, file_path)
    return {"file": file_path, "history": history}

@app.get("/repository/{repo_id}/contributors")
async def get_contributors(repo_id: str):
    """Get developer contributions for repository"""
    contributors = engine.version_tracker.get_developer_contributions(repo_id)
    return {"repo_id": repo_id, "contributors": contributors}

@app.post("/repository/{repo_id}/check-integrity")
async def check_file_integrity(repo_id: str, file_path: str):
    """Check if file was tampered with"""
    result = engine.version_tracker.detect_file_tampering(repo_id, file_path)
    return result

@app.post("/repository/{repo_id}/import-git-history")
async def import_git_history(repo_id: str, max_commits: int = 100):
    """Import git commit history for version tracking"""
    repos = engine.version_tracker.list_repositories()
    repo = next((r for r in repos if r['repo_id'] == repo_id), None)
    if not repo:
        return {"error": "Repository not found"}
    
    result = engine.version_tracker.import_git_history(repo_id, repo['path'], max_commits)
    return result

@app.delete("/repository/{repo_id}")
async def delete_repository(repo_id: str):
    """Delete repository and all its data including cache"""
    with engine.graph_db.driver.session() as session:
        session.run("""
            MATCH (r:Repository {repo_id: $repo_id})
            OPTIONAL MATCH (r)-[:HAS_SNAPSHOT]->(s:Snapshot)
            OPTIONAL MATCH (r)-[:CONTAINS]->(f:File)
            OPTIONAL MATCH (f)-[:CONTAINS]->(c)
            OPTIONAL MATCH (f)-[:HAS_VERSION]->(v:Version)
            OPTIONAL MATCH (r)-[:HAS_COMMIT]->(cm:Commit)
            DETACH DELETE r, s, f, c, v, cm
            """, repo_id=repo_id)
    
    # Clear from memory cache
    if engine.current_repo_id == repo_id:
        engine.current_repo_id = None
        engine.current_snapshot_id = None
        engine.memory_cache.clear()
    
    return {"status": "success", "message": f"Repository {repo_id} deleted"}

@app.get("/files")
async def list_files(repo_id: str = None):
    """List all files in the repository"""
    if repo_id and repo_id != engine.current_repo_id:
        if not engine.load_repository_analysis(repo_id):
            return {"error": "Repository not found"}
    files = engine.graph_db.get_all_files()
    return {"total": len(files), "files": files}

@app.get("/debug/files")
async def debug_files():
    """Show all files stored in graph for debugging"""
    files = engine.graph_db.get_all_files()
    return {"total": len(files), "files": files[:20], "repo_path": str(engine.repo_path) if engine.repo_path else None}

@app.post("/repository/{repo_id}/load")
async def load_repository(repo_id: str):
    """Load existing repository analysis"""
    success = engine.load_repository_analysis(repo_id)
    if success:
        return {
            "status": "success",
            "repo_id": repo_id,
            "message": "Repository loaded successfully"
        }
    return {"status": "error", "message": "Repository not found"}

@app.get("/graph/data")
async def get_graph_data(repo_id: str = None):
    """Get nodes and edges for graph visualization"""
    # Load repo if specified
    if repo_id and repo_id != engine.current_repo_id:
        if not engine.load_repository_analysis(repo_id):
            return {"error": "Repository not found"}
    
    # Use NetworkX graph which has all dependencies
    if engine.dependency_mapper and engine.dependency_mapper.graph:
        nx_graph = engine.dependency_mapper.graph
        
        # Filter to only include File nodes (not external modules)
        file_nodes = [n for n in nx_graph.nodes() if '\\' in n or '/' in n]
        
        nodes = []
        edges = []
        seen = set()
        
        for node in file_nodes[:100]:  # Limit for performance
            if node not in seen:
                parts = node.replace('\\', '/').split('/')
                label = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]
                nodes.append({'id': node, 'label': label})
                seen.add(node)
            
            # Get edges from this node
            for target in nx_graph.successors(node):
                if target in file_nodes and target not in seen:
                    parts = target.replace('\\', '/').split('/')
                    label = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]
                    nodes.append({'id': target, 'label': label})
                    seen.add(target)
                
                if target in file_nodes:
                    edges.append({
                        'source': node,
                        'target': target,
                        'type': 'imports'
                    })    
        
        
        return {'nodes': nodes, 'edges': edges}
    
    # Fallback to Neo4j
    # Use current repo if not specified
    if not repo_id and engine.current_repo_id:
        repo_id = engine.current_repo_id
    graph_data = engine.graph_db.get_graph_data(repo_id=repo_id)
    return graph_data

@app.get("/functions")
async def list_functions(repo_id: str = None):
    """List all functions in the codebase, optionally filtered by repository"""
    # Use current repo if not specified
    if not repo_id and engine.current_repo_id:
        repo_id = engine.current_repo_id
    functions = engine.graph_db.get_all_functions(repo_id)
    return {"total": len(functions), "functions": functions}

@app.get("/graph/functions")
async def get_function_graph(repo_id: str = None):
    """Get function call graph for visualization"""
    # Use current repo if not specified
    if not repo_id and engine.current_repo_id:
        repo_id = engine.current_repo_id
    from src.graph.function_graph import FunctionGraphBuilder
    builder = FunctionGraphBuilder(engine.graph_db)
    graph_data = builder.get_function_graph_data(repo_id=repo_id, limit=100)
    return graph_data

@app.get("/graph/function/{function_name}")
async def get_function_call_chain(function_name: str, repo_id: str = None):
    """Get call chain for a specific function"""
    # Use current repo if not specified
    if not repo_id and engine.current_repo_id:
        repo_id = engine.current_repo_id
    from src.graph.function_graph import FunctionGraphBuilder
    builder = FunctionGraphBuilder(engine.graph_db)
    graph_data = builder.get_function_call_chain(function_name, repo_id=repo_id, depth=3)
    return graph_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
