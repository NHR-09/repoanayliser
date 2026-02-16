from typing import Dict, List, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BlastRadiusAnalyzer:
    def __init__(self, dependency_mapper, graph_db):
        self.dependency_mapper = dependency_mapper
        self.graph_db = graph_db
    
    def _normalize_file_path(self, file_path: str) -> str:
        """Normalize file path for consistent Neo4j matching.
        
        Returns both the resolved path and a forward-slash variant
        for cross-platform ENDS WITH matching.
        """
        # Try Neo4j-based resolution first
        if hasattr(self.graph_db, 'resolve_file_path'):
            resolved = self.graph_db.resolve_file_path(file_path)
            if resolved != file_path:
                return resolved
        
        # Fallback: try Path.resolve()
        try:
            return str(Path(file_path).resolve())
        except:
            return file_path
    
    def analyze(self, file_path: str, change_type: str = "modify", repo_id: str = None) -> Dict:
        """
        Analyze blast radius with change simulation
        
        Args:
            file_path: Target file path
            change_type: "delete", "modify", or "move"
        """
        # Normalize file path at entry point for consistent matching
        resolved_path = self._normalize_file_path(file_path)
        # Also keep a forward-slash variant for ENDS WITH matching
        file_path_fwd = file_path.replace('\\', '/')
        
        direct = self._get_direct_dependents(resolved_path, file_path_fwd, repo_id)
        indirect = self._get_indirect_dependents(resolved_path, file_path_fwd, direct, repo_id)
        
        # Get function-level impact
        function_impact = self._get_function_impact(resolved_path, file_path_fwd, repo_id)
        
        # Calculate impact based on change type
        if change_type == "delete":
            risk = self._assess_delete_risk(file_path, direct, function_impact)
        elif change_type == "move":
            risk = self._assess_move_risk(file_path, direct)
        else:  # modify
            risk = self._assess_modify_risk(direct, indirect)
        
        return {
            "file": file_path,
            "change_type": change_type,
            "direct_dependents": list(direct),
            "indirect_dependents": list(indirect),
            "total_affected": len(direct) + len(indirect),
            "functions_affected": function_impact,
            "risk_level": risk["level"],
            "risk_score": risk["score"],
            "impact_breakdown": {
                "direct_count": len(direct),
                "indirect_count": len(indirect),
                "function_callers": len(function_impact.get("callers", []))
            }
        }
    
    def _get_direct_dependents(self, file_path: str, file_path_fwd: str = None, repo_id: str = None) -> Set[str]:
        """Files that directly import/depend on this file"""
        direct = set()
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        
        # Use Neo4j DEPENDS_ON relationships
        # Query: Find files that DEPEND ON the target file
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (target:File)
                WHERE target.file_path = $file_path OR target.path = $file_path
                   OR target.file_path ENDS WITH $file_path OR target.path ENDS WITH $file_path
                   OR target.path_normalized ENDS WITH $file_path_fwd
                MATCH (source:File)-[:DEPENDS_ON]->(target)
                WHERE source <> target
                RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                """, file_path=file_path, file_path_fwd=file_path_fwd)
            
            for record in result:
                if record['dependent']:
                    direct.add(record['dependent'])
        
        return direct
    
    def _get_indirect_dependents(self, file_path: str, file_path_fwd: str = None, direct: Set[str] = None, repo_id: str = None) -> Set[str]:
        """
        Files that transitively depend on this file
        
        Note: Limited to 2-3 hops for performance and relevance.
        Deeper dependencies (4+ hops) are considered too distant to be critical.
        """
        if direct is None:
            direct = set()
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        indirect = set()
        
        # Use Neo4j path queries for transitive dependencies
        # Query: Find files that depend on target through 2-3 hops
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (target:File)
                WHERE target.file_path = $file_path OR target.path = $file_path
                   OR target.file_path ENDS WITH $file_path OR target.path ENDS WITH $file_path
                   OR target.path_normalized ENDS WITH $file_path_fwd
                MATCH (source:File)
                WHERE source <> target
                MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
                RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                """, file_path=file_path, file_path_fwd=file_path_fwd)
            
            for record in result:
                dep = record['dependent']
                if dep and dep not in direct:
                    indirect.add(dep)
        
        return indirect
    
    def _get_function_impact(self, file_path: str, file_path_fwd: str = None, repo_id: str = None) -> Dict:
        """Get functions in this file and their callers (excluding self-calls)"""
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        
        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                       OR f.path_normalized ENDS WITH $file_path_fwd
                    OPTIONAL MATCH (caller:File)-[:CALLS]->(fn)
                    WHERE (r)-[:CONTAINS]->(caller) AND caller <> f
                    RETURN fn.name as function, COLLECT(DISTINCT COALESCE(caller.file_path, caller.path)) as callers
                    """, repo_id=repo_id, file_path=file_path, file_path_fwd=file_path_fwd)
            else:
                result = session.run("""
                    MATCH (f:File)-[:CONTAINS]->(fn:Function)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                       OR f.path_normalized ENDS WITH $file_path_fwd
                    OPTIONAL MATCH (caller:File)-[:CALLS]->(fn)
                    WHERE caller <> f
                    RETURN fn.name as function, COLLECT(DISTINCT COALESCE(caller.file_path, caller.path)) as callers
                    """, file_path=file_path, file_path_fwd=file_path_fwd)
            
            functions = []
            all_callers = set()
            for record in result:
                callers = [c for c in record["callers"] if c]
                functions.append({
                    "name": record["function"],
                    "callers": callers,
                    "caller_count": len(callers)
                })
                all_callers.update(callers)
            
            return {
                "functions": functions,
                "callers": list(all_callers),
                "total_functions": len(functions)
            }
    
    def _assess_delete_risk(self, file_path: str, direct: Set[str], function_impact: Dict) -> Dict:
        """
        Assess risk of deleting a file
        
        Risk factors:
        - Direct imports: Files that import this file will break (30 pts each)
        - Function callers: Files calling functions will have runtime errors (20 pts each)
        - Function count: More functions = larger API surface (10 pts each)
        
        Note: Function callers are counted separately from direct dependents
        because they represent runtime dependencies, not just import dependencies.
        """
        score = 0
        
        # Direct imports = CRITICAL breaking changes (each file that imports will break)
        score += len(direct) * 30
        
        # Indirect dependents = cascading failures
        # (calculated separately but affects total impact)
        
        # Function callers = runtime errors
        score += len(function_impact.get("callers", [])) * 20
        
        # High function count = more API surface
        score += function_impact.get("total_functions", 0) * 10
        
        if score >= 100:
            level = "critical"
        elif score >= 60:
            level = "high"
        elif score >= 30:
            level = "medium"
        else:
            level = "low"
        
        return {"level": level, "score": min(score, 100)}
    
    def _assess_move_risk(self, file_path: str, direct: Set[str]) -> Dict:
        """Assess risk of moving a file (all imports break)"""
        score = len(direct) * 8
        
        if score > 80:
            level = "high"
        elif score > 40:
            level = "medium"
        else:
            level = "low"
        
        return {"level": level, "score": min(score, 100)}
    
    def _assess_modify_risk(self, direct: Set[str], indirect: Set[str]) -> Dict:
        """Assess risk of modifying a file"""
        total = len(direct) + len(indirect)
        
        if total > 15:
            level = "high"
        elif total > 8:
            level = "medium"
        else:
            level = "low"
        
        score = min(total * 5, 100)
        return {"level": level, "score": score}
