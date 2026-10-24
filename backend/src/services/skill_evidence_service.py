import uuid
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from src.db.connection import get_db_connection
from src.analysis_engine import AnalysisEngine

logger = logging.getLogger(__name__)

# Map common language skills to file extensions and Neo4j language tags
LANGUAGE_MAP = {
    "python": [".py", "python"],
    "javascript": [".js", ".jsx", ".mjs", "javascript"],
    "typescript": [".ts", ".tsx", "typescript"],
    "java": [".java", "java"],
    "go": [".go", "go"],
    "rust": [".rs", "rust"],
    "c++": [".cpp", ".hpp", ".cc", ".cxx", "cpp"],
    "c#": [".cs", "csharp"],
    "html": [".html", ".htm", "html"],
    "css": [".css", ".scss", ".sass", "css"],
}

# Framework / Tool import matching keywords
FRAMEWORK_IMPORT_KEYWORDS = {
    "react": ["react", "react-dom"],
    "fastapi": ["fastapi", "starlette", "pydantic"],
    "django": ["django", "rest_framework"],
    "flask": ["flask", "werkzeug"],
    "express": ["express"],
    "spring boot": ["org.springframework", "spring", "springframework"],
    "spring": ["org.springframework", "spring"],
    "next.js": ["next", "next/router"],
    "vue": ["vue", "vuex", "pinia"],
    "angular": ["@angular/core", "angular"],
    "sqlalchemy": ["sqlalchemy"],
    "pytorch": ["torch", "torchvision"],
    "tensorflow": ["tensorflow", "keras"],
    "pandas": ["pandas"],
    "numpy": ["numpy"],
    "neo4j": ["neo4j"],
    "redis": ["redis", "ioredis"],
    "postgresql": ["psycopg2", "asyncpg", "pg"],
    "sqlite": ["sqlite3", "aiosqlite"],
    "mongodb": ["pymongo", "mongoose", "motor"],
    "docker": ["dockerfile", "docker-compose"],
}

class SkillEvidenceService:
    def __init__(self, engine: Optional[AnalysisEngine] = None):
        self._engine = engine

    @property
    def engine(self) -> AnalysisEngine:
        if self._engine is None:
            self._engine = AnalysisEngine()
        return self._engine

    def map_skills_to_repository(self, user_id: str, repo_id: str) -> List[Dict[str, Any]]:
        """
        Evaluate candidate's reviewed skills against real AST symbols, imports,
        files, and architectural patterns in the analyzed repository.
        Persist findings in skill_evidence table.
        """
        with get_db_connection() as conn:
            # 1. Fetch user's skills
            skill_rows = conn.execute(
                "SELECT id, skill_name, category FROM user_skills WHERE user_id = ?",
                (user_id,)
            ).fetchall()
            skills = [dict(r) for r in skill_rows]

            # 2. Fetch repository
            repo_row = conn.execute(
                "SELECT * FROM repositories WHERE id = ?",
                (repo_id,)
            ).fetchone()

            if not repo_row:
                raise ValueError("Repository not found.")

            repo = dict(repo_row)
            neo4j_repo_id = repo["neo4j_repo_id"]
            analysis_status = repo.get("analysis_status", "PENDING")
            analysis_version = repo.get("last_analyzed_commit") or "HEAD"

        evidence_results = []
        now = datetime.utcnow().isoformat()

        # If repo is not analyzed or graph driver is not connected, default to CLAIMED_ONLY
        if analysis_status != "COMPLETED" or not self.engine.graph_db or not self.engine.graph_db.driver:
            for s in skills:
                evidence_results.append({
                    "skill_name": s["skill_name"],
                    "category": s["category"],
                    "evidence_status": "CLAIMED_ONLY",
                    "file_path": None,
                    "entity_type": None,
                    "entity_name": None,
                    "line_number": None,
                    "evidence_description": f"Repository '{repo.get('display_name')}' analysis is {analysis_status.lower()}; code evidence pending.",
                    "confidence_score": 0.5
                })
            self._persist_evidence(user_id, repo_id, neo4j_repo_id, analysis_version, evidence_results)
            return evidence_results

        # Query Neo4j for genuine structural code evidence
        try:
            with self.engine.graph_db.driver.session() as session:
                for s in skills:
                    skill_name = s["skill_name"]
                    skill_lower = skill_name.lower().strip()
                    cat = s["category"]

                    evidence = self._find_evidence_for_skill(session, neo4j_repo_id, skill_name, skill_lower, cat)
                    evidence_results.append(evidence)

        except Exception as e:
            logger.error(f"Error querying Neo4j for skill evidence: {e}")
            for s in skills:
                evidence_results.append({
                    "skill_name": s["skill_name"],
                    "category": s["category"],
                    "evidence_status": "INSUFFICIENT_EVIDENCE",
                    "file_path": None,
                    "entity_type": None,
                    "entity_name": None,
                    "line_number": None,
                    "evidence_description": f"Unable to query code graph: {str(e)}",
                    "confidence_score": 0.0
                })

        self._persist_evidence(user_id, repo_id, neo4j_repo_id, analysis_version, evidence_results)
        return evidence_results

    def _find_evidence_for_skill(
        self,
        session,
        neo4j_repo_id: str,
        skill_name: str,
        skill_lower: str,
        category: str
    ) -> Dict[str, Any]:
        """Inspect Neo4j for concrete evidence matching the skill."""

        # 1. Check Language match
        if category == "LANGUAGE" or skill_lower in LANGUAGE_MAP:
            exts = LANGUAGE_MAP.get(skill_lower, [f".{skill_lower}"])
            # Match files
            q = """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                WHERE toLower(f.language) = $lang OR any(ext IN $exts WHERE toLower(f.path) ENDS WITH ext)
                RETURN f.path as path, f.language as lang, f.lines as lines
                LIMIT 5
            """
            res = session.run(q, repo_id=neo4j_repo_id, lang=skill_lower, exts=exts).data()
            if res:
                count_res = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)
                    WHERE toLower(f.language) = $lang OR any(ext IN $exts WHERE toLower(f.path) ENDS WITH ext)
                    RETURN count(f) as total
                """, repo_id=neo4j_repo_id, lang=skill_lower, exts=exts).single()
                total = count_res["total"] if count_res else len(res)
                sample_file = res[0]["path"]

                return {
                    "skill_name": skill_name,
                    "category": category,
                    "evidence_status": "CODE_EVIDENCE_FOUND",
                    "file_path": sample_file,
                    "entity_type": "FILE",
                    "entity_name": skill_name,
                    "line_number": 1,
                    "evidence_description": f"Verified {total} {skill_name} source file(s) in repository (e.g. '{sample_file}').",
                    "confidence_score": 0.95
                }

        # 2. Check Framework, Library, Database, or Tool via Imports & Classes
        keywords = FRAMEWORK_IMPORT_KEYWORDS.get(skill_lower, [skill_lower])
        for kw in keywords:
            # Check imports
            import_q = """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:IMPORTS]->(m)
                WHERE toLower(m.name) CONTAINS $kw
                RETURN f.path as path, m.name as module_name
                LIMIT 1
            """
            imp_res = session.run(import_q, repo_id=neo4j_repo_id, kw=kw).data()
            if imp_res:
                hit = imp_res[0]
                return {
                    "skill_name": skill_name,
                    "category": category,
                    "evidence_status": "CODE_EVIDENCE_FOUND",
                    "file_path": hit["path"],
                    "entity_type": "IMPORT",
                    "entity_name": hit["module_name"],
                    "line_number": 1,
                    "evidence_description": f"Imported and utilized in '{hit['path']}' ('{hit['module_name']}').",
                    "confidence_score": 0.90
                }

            # Check classes or functions with matching name
            class_q = """
                MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(c:Class)
                WHERE toLower(c.name) CONTAINS $kw
                RETURN f.path as path, c.name as name, c.line as line
                LIMIT 1
            """
            cls_res = session.run(class_q, repo_id=neo4j_repo_id, kw=kw).data()
            if cls_res:
                hit = cls_res[0]
                return {
                    "skill_name": skill_name,
                    "category": category,
                    "evidence_status": "CODE_EVIDENCE_FOUND",
                    "file_path": hit["path"],
                    "entity_type": "CLASS",
                    "entity_name": hit["name"],
                    "line_number": hit.get("line") or 1,
                    "evidence_description": f"Class '{hit['name']}' defined in '{hit['path']}'.",
                    "confidence_score": 0.85
                }

        # 3. Check Architecture Patterns
        if category == "ARCHITECTURE":
            # Check detected patterns from analysis engine
            patterns_data = self.engine.get_patterns(neo4j_repo_id)
            if isinstance(patterns_data, dict):
                detected_patterns = patterns_data.get("patterns", {})
                for pat_name, pat_details in detected_patterns.items():
                    if skill_lower in pat_name.lower():
                        evidence_files = pat_details.get("evidence", [])
                        sample = evidence_files[0] if evidence_files else None
                        return {
                            "skill_name": skill_name,
                            "category": category,
                            "evidence_status": "CODE_EVIDENCE_FOUND",
                            "file_path": sample,
                            "entity_type": "ARCHITECTURE_PATTERN",
                            "entity_name": pat_name,
                            "line_number": 1,
                            "evidence_description": f"Architectural pattern '{pat_name}' verified in codebase.",
                            "confidence_score": 0.90
                        }

        # 4. Fallback: Not found in this repository
        return {
            "skill_name": skill_name,
            "category": category,
            "evidence_status": "CLAIMED_ONLY",
            "file_path": None,
            "entity_type": None,
            "entity_name": None,
            "line_number": None,
            "evidence_description": f"Claimed in candidate profile, but no direct code evidence located in this repository.",
            "confidence_score": 0.0
        }

    def _persist_evidence(
        self,
        user_id: str,
        repo_id: str,
        neo4j_repo_id: str,
        analysis_version: str,
        evidence_list: List[Dict[str, Any]]
    ):
        """Save evidence mapping records into SQLite skill_evidence table."""
        now = datetime.utcnow().isoformat()
        with get_db_connection() as conn:
            # Delete old evidence for this user + repo to keep mappings fresh
            conn.execute(
                "DELETE FROM skill_evidence WHERE user_id = ? AND repository_id = ?",
                (user_id, repo_id)
            )

            for item in evidence_list:
                ev_id = str(uuid.uuid4())
                conn.execute("""
                    INSERT INTO skill_evidence (
                        id, user_id, skill_name, repository_id, neo4j_repo_id,
                        analysis_version, evidence_status, file_path, entity_type,
                        entity_name, line_number, evidence_description, confidence_score,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ev_id,
                    user_id,
                    item["skill_name"],
                    repo_id,
                    neo4j_repo_id,
                    analysis_version,
                    item["evidence_status"],
                    item.get("file_path"),
                    item.get("entity_type"),
                    item.get("entity_name"),
                    item.get("line_number"),
                    item.get("evidence_description"),
                    item.get("confidence_score", 1.0),
                    now
                ))

    def get_user_skill_evidence(self, user_id: str, repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve stored evidence mappings for candidate skills."""
        with get_db_connection() as conn:
            if repo_id:
                rows = conn.execute("""
                    SELECT e.*, r.display_name as repo_name, r.repo_url
                    FROM skill_evidence e
                    JOIN repositories r ON r.id = e.repository_id
                    WHERE e.user_id = ? AND e.repository_id = ?
                    ORDER BY e.evidence_status, e.skill_name
                """, (user_id, repo_id)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT e.*, r.display_name as repo_name, r.repo_url
                    FROM skill_evidence e
                    JOIN repositories r ON r.id = e.repository_id
                    WHERE e.user_id = ?
                    ORDER BY e.created_at DESC
                """, (user_id,)).fetchall()
            return [dict(r) for r in rows]
