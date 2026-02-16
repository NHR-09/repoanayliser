"""
BLAST RADIUS LOGIC FLAW ANALYSIS
=================================

SUMMARY OF FINDINGS:
-------------------

1. ✅ NO MAJOR LOGIC FLAWS IN CORE ALGORITHM
   - Direct dependents correctly use DEPENDS_ON relationships
   - Indirect dependents correctly use 2-3 hop traversal
   - Direct and indirect are properly separated (no overlap)
   - Risk scoring is consistent with thresholds

2. ⚠️ MINOR ISSUE: Self-calls in function impact
   - Files calling their own functions appear in function_impact['callers']
   - This is technically correct but might inflate the impact count
   - Current code in _get_function_impact() includes self-calls
   - RECOMMENDATION: Filter out self-calls from callers list

3. ⚠️ DESIGN QUESTION: Function callers vs Direct dependents
   - Function callers are tracked separately from direct dependents
   - In theory, if File A calls Function in File B, then:
     * File A should have CALLS -> Function relationship
     * File A should have DEPENDS_ON -> File B relationship
   - Current graph construction appears correct (no CALLS without DEPENDS_ON)
   - However, function callers are counted separately in risk assessment
   - RECOMMENDATION: Clarify if this is intentional or redundant

4. ✅ GRAPH CONSTRUCTION IS CORRECT
   - All CALLS relationships have corresponding DEPENDS_ON
   - No orphaned function calls
   - Import relationships properly mapped

SPECIFIC CODE ISSUES:
--------------------

Issue #1: Self-calls included in function impact
Location: blast_radius.py, _get_function_impact()

Current code:
```python
result = session.run(\"\"\"
    MATCH (f:File)-[:CONTAINS]->(fn:Function)
    WHERE f.file_path = $file_path OR f.path = $file_path
    OPTIONAL MATCH (caller:File)-[:CALLS]->(fn)
    RETURN fn.name as function, COLLECT(DISTINCT ...) as callers
\"\"\")
```

Problem: This includes the file itself calling its own functions

Fix:
```python
result = session.run(\"\"\"
    MATCH (f:File)-[:CONTAINS]->(fn:Function)
    WHERE f.file_path = $file_path OR f.path = $file_path
    OPTIONAL MATCH (caller:File)-[:CALLS]->(fn)
    WHERE caller <> f  # <-- ADD THIS LINE
    RETURN fn.name as function, COLLECT(DISTINCT ...) as callers
\"\"\")
```

Issue #2: Risk scoring for DELETE might double-count
Location: blast_radius.py, _assess_delete_risk()

Current code:
```python
score += len(direct) * 30  # Direct imports
score += len(function_impact.get(\"callers\", [])) * 20  # Function callers
```

Problem: If function callers are already in direct dependents, we're counting them twice

Analysis:
- Direct dependents: Files that DEPEND_ON target
- Function callers: Files that CALL functions in target
- These SHOULD be the same set (if graph is correct)
- But we're adding both to the score

Recommendation:
- Either: Use union of both sets
- Or: Only count direct dependents (since CALLS implies DEPENDS_ON)
- Or: Document that this is intentional (function calls are higher risk)

Issue #3: Indirect dependents limited to 3 hops
Location: blast_radius.py, _get_indirect_dependents()

Current code:
```python
MATCH path = (source)-[:DEPENDS_ON*2..3]->(target)
```

Analysis:
- Only captures 2-3 hop dependencies
- Deeper dependencies (4+ hops) are ignored
- This is probably intentional (performance/relevance tradeoff)
- But should be documented

Recommendation: Add comment explaining the 3-hop limit

TESTING RESULTS:
---------------

Test file: workspace\\Repo-Analyzer-\\apps\\api\\app\\services\\chat_service.py

Modify:
- Direct: 1 file
- Indirect: 0 files
- Function callers: 1 file (SELF-CALL)
- Risk: LOW (correct)

Delete:
- Direct: 1 file
- Function callers: 1 file (SELF-CALL)
- Risk: HIGH (score 90)
- Analysis: Score = 1*30 + 1*20 + 4*10 = 90
  * 1 direct dependent = 30 points
  * 1 function caller (self) = 20 points  # <-- SHOULD BE 0
  * 4 functions = 40 points
  * Total = 90 (HIGH risk)
  * Without self-call: 70 (HIGH risk) - still correct level

Move:
- Direct: 1 file
- Risk: LOW (correct)

CONCLUSION:
----------

✅ OVERALL: Blast radius logic is SOUND
⚠️ MINOR FIX NEEDED: Filter out self-calls from function impact
⚠️ DOCUMENTATION: Clarify risk scoring methodology
⚠️ OPTIONAL: Consider combining function callers with direct dependents

PRIORITY:
- HIGH: Fix self-calls issue (easy fix, improves accuracy)
- MEDIUM: Document risk scoring rationale
- LOW: Consider refactoring function caller logic
"""

print(__doc__)
