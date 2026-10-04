from typing import Dict, List, Set
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BlastRadiusAnalyzer:
    def __init__(self, dependency_mapper, graph_db):
        self.dependency_mapper = dependency_mapper
        self.graph_db = graph_db
    
    def _normalize_file_path(self, file_path: str, repo_id: str = None) -> str:
        """Normalize file path for consistent Neo4j matching.
        
        Returns both the resolved path and a forward-slash variant
        for cross-platform ENDS WITH matching.
        """
        # Try Neo4j-based resolution first
        if hasattr(self.graph_db, 'resolve_file_path'):
            resolved = self.graph_db.resolve_file_path(file_path, repo_id=repo_id)
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
        file_path_fwd = file_path.replace('\\', '/')
        
        # If repo_id not provided, resolve from file
        if not repo_id:
            rel_suffix = file_path_fwd.split('/')[-2:] if len(file_path_fwd.split('/')) >= 2 else [file_path_fwd]
            rel_path = '/'.join(rel_suffix)
            with self.graph_db.driver.session() as session:
                rec = session.run("""
                    MATCH (r:Repository)-[:CONTAINS]->(f:File)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                       OR f.path_normalized = $file_path_fwd
                       OR f.path_normalized ENDS WITH '/' + $rel_path
                    RETURN r.repo_id as repo_id
                    LIMIT 1
                """, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path).single()
                if rec:
                    repo_id = rec['repo_id']
        
        # Normalize file path at entry point with repo_id scoping
        resolved_path = self._normalize_file_path(file_path, repo_id=repo_id)
        resolved_fwd = resolved_path.replace('\\', '/')
        
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
        
        # Compute structural risk (fan-in, fan-out, cycle presence)
        structural_risk = self._compute_structural_risk(file_path, resolved_path)
        
        return {
            "file": file_path,
            "change_type": change_type,
            "direct_dependents": list(direct),
            "indirect_dependents": list(indirect),
            "total_affected": len(direct) + len(indirect),
            "functions_affected": function_impact,
            "risk_level": risk["level"],
            "risk_score": risk["score"],
            "structural_risk": structural_risk,
            "impact_breakdown": {
                "direct_count": len(direct),
                "indirect_count": len(indirect),
                "function_callers": len(function_impact.get("callers", []))
            }
        }
    
    def _compute_structural_risk(self, file_path: str, resolved_path: str) -> Dict:
        """Compute structural risk using CouplingAnalyzer on the dependency graph."""
        from .analyzers import CouplingAnalyzer
        try:
            graph = self.dependency_mapper.graph
            analyzer = CouplingAnalyzer(graph)
            # Try both original and resolved paths
            risk = analyzer.compute_structural_risk(resolved_path)
            if risk['level'] == 'unknown':
                risk = analyzer.compute_structural_risk(file_path)
            if risk['level'] == 'unknown':
                # Try flexible node matching
                fwd = file_path.replace('\\', '/')
                for node in graph.nodes():
                    if node.replace('\\', '/').endswith(fwd.split('/')[-1]):
                        risk = analyzer.compute_structural_risk(node)
                        if risk['level'] != 'unknown':
                            break
            return risk
        except Exception as e:
            logger.warning(f"Could not compute structural risk: {e}")
            return {'score': 0, 'level': 'unknown', 'fan_in': 0, 'fan_out': 0, 'in_cycle': False, 'breakdown': {}}
    
    def _get_direct_dependents(self, file_path: str, file_path_fwd: str = None, repo_id: str = None) -> Set[str]:
        """Files that directly import/depend on this file"""
        direct = set()
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        
        # Strip drive or parent prefixes for clean suffix matching
        rel_suffix = file_path_fwd.split('/')[-2:] if len(file_path_fwd.split('/')) >= 2 else [file_path_fwd]
        rel_path = '/'.join(rel_suffix)

        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(target:File)
                    WHERE target.file_path = $file_path OR target.path = $file_path
                       OR target.path_normalized = $file_path_fwd
                       OR target.path_normalized ENDS WITH '/' + $rel_path
                    MATCH (r)-[:CONTAINS]->(source:File)-[:DEPENDS_ON]->(target)
                    WHERE source <> target
                    RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                    """, repo_id=repo_id, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            else:
                result = session.run("""
                    MATCH (target:File)
                    WHERE target.file_path = $file_path OR target.path = $file_path
                       OR target.path_normalized = $file_path_fwd
                       OR target.path_normalized ENDS WITH '/' + $rel_path
                    MATCH (source:File)-[:DEPENDS_ON]->(target)
                    WHERE source <> target
                    RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                    """, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            
            for record in result:
                if record['dependent']:
                    direct.add(record['dependent'])
        
        return direct
    
    def _get_indirect_dependents(self, file_path: str, file_path_fwd: str = None, direct: Set[str] = None, repo_id: str = None) -> Set[str]:
        """
        Files that transitively depend on this file
        
        Note: Limited to 2-3 hops for performance and relevance.
        """
        if direct is None:
            direct = set()
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        indirect = set()
        
        rel_suffix = file_path_fwd.split('/')[-2:] if len(file_path_fwd.split('/')) >= 2 else [file_path_fwd]
        rel_path = '/'.join(rel_suffix)

        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(target:File)
                    WHERE target.file_path = $file_path OR target.path = $file_path
                       OR target.path_normalized = $file_path_fwd
                       OR target.path_normalized ENDS WITH '/' + $rel_path
                    MATCH (r)-[:CONTAINS]->(source:File)
                    WHERE source <> target
                    MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
                    WHERE ALL(n IN nodes(path) WHERE (r)-[:CONTAINS]->(n))
                    RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                    """, repo_id=repo_id, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            else:
                result = session.run("""
                    MATCH (target:File)
                    WHERE target.file_path = $file_path OR target.path = $file_path
                       OR target.path_normalized = $file_path_fwd
                       OR target.path_normalized ENDS WITH '/' + $rel_path
                    MATCH (source:File)
                    WHERE source <> target
                    MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
                    RETURN DISTINCT COALESCE(source.file_path, source.path) as dependent
                    """, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            
            for record in result:
                dep = record['dependent']
                if dep and dep not in direct:
                    indirect.add(dep)
        
        return indirect
    
    def _get_function_impact(self, file_path: str, file_path_fwd: str = None, repo_id: str = None) -> Dict:
        """Get functions in this file and their callers from other files"""
        if not file_path_fwd:
            file_path_fwd = file_path.replace('\\', '/')
        
        rel_suffix = file_path_fwd.split('/')[-2:] if len(file_path_fwd.split('/')) >= 2 else [file_path_fwd]
        rel_path = '/'.join(rel_suffix)

        with self.graph_db.driver.session() as session:
            if repo_id:
                result = session.run("""
                    MATCH (r:Repository {repo_id: $repo_id})-[:CONTAINS]->(f:File)-[:CONTAINS]->(fn:Function)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                       OR f.path_normalized = $file_path_fwd
                       OR f.path_normalized ENDS WITH '/' + $rel_path
                    
                    OPTIONAL MATCH (r)-[:CONTAINS]->(caller_file:File)-[:CONTAINS]->(caller_fn:Function)-[:CALLS]->(fn)
                    WHERE caller_file <> f
                    
                    OPTIONAL MATCH (r)-[:CONTAINS]->(fallback_file:File)-[:CALLS]->(fn)
                    WHERE fallback_file <> f
                    
                    WITH fn, 
                         COLLECT(DISTINCT COALESCE(caller_file.file_path, caller_file.path)) + 
                         COLLECT(DISTINCT COALESCE(fallback_file.file_path, fallback_file.path)) as raw_callers
                    RETURN fn.name as function, [c IN raw_callers WHERE c IS NOT NULL] as callers
                    """, repo_id=repo_id, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            else:
                result = session.run("""
                    MATCH (f:File)-[:CONTAINS]->(fn:Function)
                    WHERE f.file_path = $file_path OR f.path = $file_path
                       OR f.path_normalized = $file_path_fwd
                       OR f.path_normalized ENDS WITH '/' + $rel_path
                    OPTIONAL MATCH (caller_file:File)-[:CONTAINS]->(caller_fn:Function)-[:CALLS]->(fn)
                    WHERE caller_file <> f
                    OPTIONAL MATCH (fallback_file:File)-[:CALLS]->(fn)
                    WHERE fallback_file <> f
                    WITH fn, 
                         COLLECT(DISTINCT COALESCE(caller_file.file_path, caller_file.path)) + 
                         COLLECT(DISTINCT COALESCE(fallback_file.file_path, fallback_file.path)) as raw_callers
                    RETURN fn.name as function, [c IN raw_callers WHERE c IS NOT NULL] as callers
                    """, file_path=file_path, file_path_fwd=file_path_fwd, rel_path=rel_path)
            
            functions = []
            all_callers = set()
            for record in result:
                callers = sorted(set(c for c in record["callers"] if c))
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
        
        if total >= 15:
            level = "high"
        elif total >= 8:
            level = "medium"
        else:
            level = "low"
        
        score = min(total * 5, 100)
        return {"level": level, "score": score}
