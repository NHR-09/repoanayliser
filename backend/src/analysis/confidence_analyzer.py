from typing import Dict, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ConfidenceAnalyzer:
    """
    Analyzes confidence and limitations of architectural claims
    
    Provides confidence scores, reasoning, and failure scenarios for:
    - Architectural pattern detection
    - Coupling analysis
    - Circular dependency detection
    """
    
    def __init__(self, pattern_detector=None, coupling_analyzer=None, graph_db=None):
        self.pattern_detector = pattern_detector
        self.coupling_analyzer = coupling_analyzer
        self.graph_db = graph_db
    
    def get_confidence_report(self) -> Dict:
        """
        Generate comprehensive confidence report for all architectural claims
        
        Returns:
            Dict with list of claims, each containing:
            - claim: Human-readable claim statement
            - confidence: 0.0-1.0 score
            - reasoning: Why this confidence score
            - failure_scenario: When/why this analysis might fail
        """
        claims = []
        
        # Claim 1-4: Pattern detection claims
        if self.pattern_detector:
            pattern_claims = self._analyze_pattern_confidence()
            claims.extend(pattern_claims)
        
        # Claim 5: Coupling analysis claim
        if self.coupling_analyzer:
            coupling_claim = self._analyze_coupling_confidence()
            if coupling_claim:
                claims.append(coupling_claim)
        
        # Claim 6: Circular dependency claim
        if self.graph_db:
            cycle_claim = self._analyze_cycle_confidence()
            if cycle_claim:
                claims.append(cycle_claim)
        
        return {
            "claims": claims[:10],  # Limit to top 10 claims
            "total_claims": len(claims),
            "summary": self._generate_summary(claims)
        }
    
    def _analyze_pattern_confidence(self) -> List[Dict]:
        """Analyze confidence for architectural pattern detection"""
        claims = []
        
        if not hasattr(self.pattern_detector, 'patterns'):
            return claims
        
        patterns = self.pattern_detector.patterns or {}
        
        for pattern_name, data in patterns.items():
            if data.get('detected'):
                confidence = data.get('confidence', 0.0)
                claim = self._create_pattern_claim(pattern_name, data, confidence)
                claims.append(claim)
        
        return claims
    
    def _create_pattern_claim(self, pattern_name: str, data: Dict, confidence: float) -> Dict:
        """Create a claim for a detected architectural pattern"""
        
        # Pattern-specific reasoning
        reasoning_map = {
            'layered': self._get_layered_reasoning(data),
            'mvc': self._get_mvc_reasoning(data),
            'hexagonal': self._get_hexagonal_reasoning(data),
            'event_driven': self._get_event_driven_reasoning(data)
        }
        
        # Pattern-specific failure scenarios
        failure_map = {
            'layered': "Fails if layers are not separated by directory structure or naming conventions. Cannot detect logical layering without physical separation.",
            'mvc': "May fail if controllers/models use non-standard naming (e.g., 'handlers' instead of 'controllers'). Cannot detect MVC if implemented as single-file components.",
            'hexagonal': "Keyword-based detection may miss implementations using different naming schemes (e.g., 'interface' instead of 'port'). Cannot verify actual dependency inversion.",
            'event_driven': "Cannot detect event-driven architecture if no event/handler keywords in filenames. May miss message queue or pub-sub patterns without explicit naming."
        }
        
        return {
            "claim": f"System follows {pattern_name.replace('_', ' ').title()} architecture pattern",
            "confidence": round(confidence, 2),
            "reasoning": reasoning_map.get(pattern_name, "Pattern detected via structural analysis"),
            "failure_scenario": failure_map.get(pattern_name, "May fail with non-standard implementations"),
            "evidence": data.get('files', [])[:5]  # Top 5 files as evidence
        }
    
    def _get_layered_reasoning(self, data: Dict) -> str:
        """Generate reasoning for layered architecture detection"""
        layers = data.get('layers', [])
        layer_count = len(layers)
        file_count = sum(len(files) for files in layers.values()) if isinstance(layers, dict) else 0
        
        if layer_count >= 3:
            return f"Detected {layer_count} distinct layers with clear separation across {file_count} files"
        elif layer_count == 2:
            return f"Detected {layer_count} layers, which is minimal for layered architecture"
        else:
            return "Detected some layering but structure is not clear"
    
    def _get_mvc_reasoning(self, data: Dict) -> str:
        """Generate reasoning for MVC pattern detection"""
        controllers = data.get('controllers', 0)
        models = data.get('models', 0)
        views = data.get('views', 0)
        
        total = controllers + models + views
        
        if total >= 10:
            return f"Found {controllers} controllers, {models} models, and {views} views - strong MVC structure"
        elif total >= 5:
            return f"Found {controllers} controllers, {models} models, and {views} views - moderate MVC structure"
        else:
            return f"Found limited MVC components: {controllers} controllers, {models} models, {views} views"
    
    def _get_hexagonal_reasoning(self, data: Dict) -> str:
        """Generate reasoning for hexagonal architecture detection"""
        ports = data.get('ports', 0)
        adapters = data.get('adapters', 0)
        
        if ports >= 3 and adapters >= 3:
            return f"Detected {ports} ports and {adapters} adapters, indicating hexagonal/ports-adapters pattern"
        else:
            return f"Detected {ports} ports and {adapters} adapters - partial hexagonal structure"
    
    def _get_event_driven_reasoning(self, data: Dict) -> str:
        """Generate reasoning for event-driven detection"""
        events = data.get('events', 0)
        handlers = data.get('handlers', 0)
        
        if events >= 5 or handlers >= 5:
            return f"Found {events} event definitions and {handlers} event handlers"
        else:
            return f"Found {events} event-related components - limited event-driven structure"
    
    def _analyze_coupling_confidence(self) -> Dict:
        """Analyze confidence for coupling analysis"""
        if not hasattr(self.coupling_analyzer, 'high_coupling_files'):
            return None
        
        high_coupling = self.coupling_analyzer.high_coupling_files or []
        
        if not high_coupling:
            return None
        
        # Get the file with highest coupling
        top_file = high_coupling[0] if high_coupling else None
        
        if not top_file:
            return None
        
        total_coupling = top_file.get('fan_in', 0) + top_file.get('fan_out', 0)
        
        return {
            "claim": f"{Path(top_file['file']).name} has high coupling",
            "confidence": 0.92,
            "reasoning": f"Fan-in={top_file.get('fan_in', 0)}, Fan-out={top_file.get('fan_out', 0)}, Total={total_coupling} exceeds threshold (10)",
            "failure_scenario": "May misidentify utility modules or central coordinators with legitimate high coupling. Cannot distinguish between good coupling (dependency injection) and bad coupling (tight coupling).",
            "evidence": [top_file['file']]
        }
    
    def _analyze_cycle_confidence(self) -> Dict:
        """Analyze confidence for circular dependency detection"""
        
        # Query Neo4j for circular dependencies
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (f1:File)-[:DEPENDS_ON*1..5]->(f2:File)
                WHERE f1 = f2
                RETURN DISTINCT f1.path as cycle_file
                LIMIT 1
            """)
            
            cycle = result.single()
            
            if not cycle:
                return None
            
            cycle_file = cycle['cycle_file']
            
            return {
                "claim": f"Circular dependency detected in {Path(cycle_file).name}",
                "confidence": 1.0,
                "reasoning": "Static import analysis detected direct cycle in dependency graph via Neo4j traversal",
                "failure_scenario": "Cannot detect runtime circular dependencies or dynamic imports (e.g., importlib, __import__). May miss circular dependencies across more than 5 hops.",
                "evidence": [cycle_file]
            }
    
    def _generate_summary(self, claims: List[Dict]) -> str:
        """Generate human-readable summary of confidence report"""
        if not claims:
            return "No architectural claims to report"
        
        avg_confidence = sum(c['confidence'] for c in claims) / len(claims)
        high_confidence = sum(1 for c in claims if c['confidence'] >= 0.8)
        
        return f"Generated {len(claims)} architectural claims with average confidence {avg_confidence:.2f}. {high_confidence} claims have high confidence (≥0.8)."
