"""Script to add compare_architecture() method to AnalysisEngine"""

# Read the file
with open('c:\\Users\\user\\Desktop\\ARCHITECH\\backend\\src\\analysis_engine.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find insertion point (after _generate_comparison_summary, before _has_uncommitted_changes)
insertion_index = None
for i, line in enumerate(lines):
    if 'def _has_uncommitted_changes' in line:
        # Insert before this method
        # Go back to find the empty lines
        insertion_index = i - 1
        while insertion_index > 0 and lines[insertion_index].strip() == '':
            insertion_index -= 1
        insertion_index += 1
        break

if insertion_index is None:
    print("ERROR: Could not find insertion point")
    exit(1)

print(f"Inserting at line {insertion_index + 1}")

# Method to insert
method_code = '''    def compare_architecture(self, repo_id: str, commit1: str, commit2: str) -> Dict:
        """
        Compare architectural changes between two commits
        
        Args:
            repo_id: Repository ID
            commit1: First commit hash
            commit2: Second commit hash
        
        Returns:
            Dict with architectural comparison including patterns, coupling, and structural changes
        """
        import json
        
        # Get snapshots for each commit
        with self.graph_db.driver.session() as session:
            result = session.run("""
                MATCH (s1:Snapshot {repo_id: $repo_id, commit_hash: $commit1})
                MATCH (s2:Snapshot {repo_id: $repo_id, commit_hash: $commit2})
                RETURN s1.snapshot_id as snapshot1, s2.snapshot_id as snapshot2,
                       s1.patterns as patterns1, s2.patterns as patterns2,
                       s1.coupling as coupling1, s2.coupling as coupling2,
                       s1.arch_macro as macro1, s2.arch_macro as macro2,
                       s1.total_files as files1, s2.total_files as files2,
                       s1.avg_coupling as avg_coupling1, s2.avg_coupling as avg_coupling2,
                       s1.cycle_count as cycles1, s2.cycle_count as cycles2
                """, repo_id=repo_id, commit1=commit1, commit2=commit2)
            
            record = result.single()
            
            if not record:
                # Try to find snapshots by partial commit hash match
                result = session.run("""
                    MATCH (s1:Snapshot {repo_id: $repo_id})
                    WHERE s1.commit_hash STARTS WITH $commit1
                    MATCH (s2:Snapshot {repo_id: $repo_id})
                    WHERE s2.commit_hash STARTS WITH $commit2
                    RETURN s1.snapshot_id as snapshot1, s2.snapshot_id as snapshot2,
                           s1.patterns as patterns1, s2.patterns as patterns2,
                           s1.coupling as coupling1, s2.coupling as coupling2,
                           s1.arch_macro as macro1, s2.arch_macro as macro2,
                           s1.total_files as files1, s2.total_files as files2,
                           s1.avg_coupling as avg_coupling1, s2.avg_coupling as avg_coupling2,
                           s1.cycle_count as cycles1, s2.cycle_count as cycles2
                    LIMIT 1
                    """, repo_id=repo_id, commit1=commit1, commit2=commit2)
                
                record = result.single()
                
                if not record:
                    return {
                        "error": f"Snapshots not found for commits {commit1[:8]} and {commit2[:8]}",
                        "suggestion": "Please ensure both commits have been analyzed"
                    }
        
        # Parse patterns
        try:
            patterns1 = json.loads(record['patterns1']) if record['patterns1'] else {}
            patterns2 = json.loads(record['patterns2']) if record['patterns2'] else {}
        except:
            patterns1 = {}
            patterns2 = {}
        
        # Compare patterns
        pattern_changes = self._compare_patterns(patterns1, patterns2)
        
        # Calculate deltas
        coupling_delta = (record['avg_coupling2'] or 0) - (record['avg_coupling1'] or 0)
        cycle_delta = (record['cycles2'] or 0) - (record['cycles1'] or 0)
        file_delta = (record['files2'] or 0) - (record['files1'] or 0)
        
        # Assess risk
        risk_areas = []
        if coupling_delta > 1.0:
            risk_areas.append(f"Significant coupling increase (+{coupling_delta:.2f})")
        if cycle_delta > 0:
            risk_areas.append(f"{cycle_delta} new circular dependencies")
        if file_delta > 20:
            risk_areas.append(f"Large file increase (+{file_delta} files)")
        
        return {
            "commit1": {
                "hash": commit1[:8],
                "patterns": patterns1,
                "metrics": {
                    "files": record['files1'],
                    "avg_coupling": record['avg_coupling1'],
                    "cycles": record['cycles1']
                },
                "architecture_summary": record['macro1'][:200] + "..." if record['macro1'] and len(record['macro1']) > 200 else record['macro1']
            },
            "commit2": {
                "hash": commit2[:8],
                "patterns": patterns2,
                "metrics": {
                    "files": record['files2'],
                    "avg_coupling": record['avg_coupling2'],
                    "cycles": record['cycles2']
                },
                "architecture_summary": record['macro2'][:200] + "..." if record['macro2'] and len(record['macro2']) > 200 else record['macro2']
            },
            "changes": {
                "pattern_changes": pattern_changes,
                "coupling_delta": round(coupling_delta, 2),
                "cycle_delta": cycle_delta,
                "file_delta": file_delta
            },
            "risk_assessment": {
                "risk_level": "high" if len(risk_areas) >= 2 else "medium" if len(risk_areas) == 1 else "low",
                "risk_areas": risk_areas
            },
            "summary": f"File count changed by {file_delta:+d}, coupling changed by {coupling_delta:+.2f}, {cycle_delta:+d} cycle changes, {len(pattern_changes)} pattern changes"
        }
    
'''

# Insert the method
lines.insert(insertion_index, method_code)

# Write back
with open('c:\\Users\\user\\Desktop\\ARCHITECH\\backend\\src\\analysis_engine.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("SUCCESS: compare_architecture() method added!")
