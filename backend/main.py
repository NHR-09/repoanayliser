from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict
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
async def get_architecture():
    result = engine.get_architecture_explanation()
    return result

@app.get("/patterns")
async def get_patterns():
    if engine.pattern_detector:
        return engine.pattern_detector.detect_patterns()
    return {"error": "No analysis completed yet"}

@app.get("/coupling")
async def get_coupling():
    if engine.coupling_analyzer:
        return engine.coupling_analyzer.analyze()
    return {"error": "No analysis completed yet"}

@app.post("/impact")
async def analyze_impact(request: ImpactRequest):
    result = engine.analyze_change_impact(request.file_path)
    return result

@app.get("/dependencies/{file_path:path}")
async def get_dependencies(file_path: str):
    resolved = engine._resolve_path(file_path)
    deps = engine.graph_db.get_dependencies(resolved)
    return {"file": file_path, "dependencies": deps}

@app.get("/blast-radius/{file_path:path}")
async def get_blast_radius(file_path: str):
    resolved = engine._resolve_path(file_path)
    radius = engine.dependency_mapper.get_blast_radius(resolved)
    return {"file": file_path, "affected_files": radius, "count": len(radius)}

@app.get("/debug/files")
async def debug_files():
    """Show all files stored in graph for debugging"""
    files = engine.graph_db.get_all_files()
    return {"total": len(files), "files": files[:20], "repo_path": str(engine.repo_path) if engine.repo_path else None}

def run_analysis(job_id: str, repo_url: str):
    try:
        result = engine.analyze_repository(repo_url)
        jobs[job_id] = {"status": "completed", "result": result}
    except Exception as e:
        jobs[job_id] = {"status": "failed", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
