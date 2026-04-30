from typing import Dict, List, Optional
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LLMReasoner:
    def __init__(self):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    def explain_architecture(self, evidence: List[Dict]) -> Dict:
        prompt = self._build_architecture_prompt(evidence)
        response = self._call_llm(prompt)
        
        return {
            'explanation': response,
            'evidence_files': [e['file'] for e in evidence]
        }
    
    def analyze_impact(self, file_path: str, evidence: List[Dict], affected_files: List[str]) -> Dict:
        prompt = self._build_impact_prompt(file_path, evidence, affected_files)
        response = self._call_llm(prompt)
        
        return {
            'file': file_path,
            'impact_explanation': response,
            'affected_files': affected_files,
            'evidence': [e['file'] for e in evidence]
        }
    
    def explain_function(self, function_name: str, function_info: Dict, callers: List[Dict], context: List[Dict], function_code: str = None) -> str:
        """Generate LLM explanation for a function"""
        prompt = self._build_function_prompt(function_name, function_info, callers, context, function_code)
        return self._call_llm(prompt)
    
    def explain_meso_level(self, patterns: Dict, graph_context: str) -> str:
        """Generate meso-level explanation with graph structure"""
        prompt = f"""Analyze the module-level architecture based on detected patterns and graph structure.

Detected Patterns:
{self._format_patterns(patterns)}

Graph Structure:
{graph_context}

Provide a detailed meso-level analysis covering:
1. Module organization and responsibilities
2. Layer separation and boundaries
3. Key architectural components
4. Module interaction patterns
5. Design principles observed

Be specific and cite the graph structure."""
        return self._call_llm(prompt)
    
    def explain_micro_level(self, files: List[str], graph_data: Dict) -> str:
        """Generate micro-level explanation with file details"""
        # Filter out None values and extract filenames
        file_summary = '\n'.join([f"- {(f or 'unknown').split('/')[-1]}" for f in files[:15] if f])
        
        prompt = f"""Analyze the file-level architecture details.

Key Files:
{file_summary}

Dependency Count: {len(graph_data.get('edges', []))} relationships

Provide a detailed micro-level analysis covering:
1. Critical files and their roles
2. File organization patterns
3. Import/dependency patterns
4. Code structure observations
5. Key functions and classes

Be concise and focus on the most important files."""
        return self._call_llm(prompt)
    
    def explain_architecture_report(
        self,
        patterns_text: str,
        graph_context: str,
        top_dirs: str,
        evidence_text: str,
        graphify_context: Optional[str] = None,
    ) -> Dict:
        """Single consolidated architecture explanation — replaces 3 separate calls.
        
        If graphify_context is provided (from GraphifyRetriever), it is injected
        into the prompt so the LLM can cite actual function and class names.
        """
        graphify_section = (
            f"\nStructural Knowledge Graph (functions, classes, call chains):\n{graphify_context}"
            if graphify_context
            else ""
        )

        system_prompt = """You are a senior software architect performing a deep architectural review. Your job is to provide INSIGHTS, not summaries. 

CRITICAL RULES:
1. Do NOT paraphrase the data back. Do NOT say "File X contains class Y and function Z" — that's useless restating.
2. Instead, ANALYZE: Why is the system designed this way? What design decisions were made? What are the strengths and weaknesses?
3. Explain HOW modules interact at a conceptual level: what data flows between them, what role each plays in the overall system.
4. Identify architectural patterns and EXPLAIN why they matter for maintainability, scalability, and testability.
5. For Key Files, explain WHY they are critical — what happens if they break? What is their architectural role?
6. Use specific file, class, and function names as evidence for your observations — but use them to support insights, not as the insight itself.
7. If a README/project description is provided, use it to understand the system's purpose and domain.
8. Never use "likely", "probably", "may contain". State what you observe and what it means architecturally."""

        user_prompt = f"""Analyze this repository's architecture. Provide deep architectural insights, not surface-level file listings.

Detected Patterns:
{patterns_text}

Structural Data:
{graph_context}

Directory Breakdown:
{top_dirs}

Code Evidence:
{evidence_text}{graphify_section}

Respond with EXACTLY these 3 sections. Each section should be 4-6 sentences of genuine architectural insight.

## Overview
Explain the system's purpose and overall architecture. What problem does it solve? What architectural style does it follow and WHY is that a good/bad fit? What are the major subsystems and how do they relate? Reference detected patterns and explain their implications.

## Modules
For each major module/subsystem: What is its responsibility? What design decisions shape it (e.g., separation of concerns, encapsulation)? How do modules communicate — trace a specific data/control flow through the dependency edges. Identify any layering violations or tight coupling between modules that shouldn't be coupled.

## Key Files
Which files are architecturally critical and WHY? Don't just list hub files — explain their architectural ROLE: Are they orchestrators? Data gateways? Service facades? What risk do they pose (single points of failure, God objects)? What happens to the system if they are modified or removed?"""
        
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.4,
            max_tokens=2000
        )
        response_text = response.choices[0].message.content
        
        # Parse sections from response
        sections = {'overview': '', 'modules': '', 'key_files': ''}
        current = None
        lines = response_text.split('\n')
        for line in lines:
            lower = line.lower().strip()
            if '## overview' in lower or '**overview**' in lower:
                current = 'overview'
                continue
            elif '## modules' in lower or '**modules**' in lower or '## module' in lower:
                current = 'modules'
                continue
            elif '## key files' in lower or '**key files**' in lower or '## key file' in lower:
                current = 'key_files'
                continue
            if current:
                sections[current] += line + '\n'
        
        # Trim whitespace
        for k in sections:
            sections[k] = sections[k].strip()
        
        # Fallback if parsing failed
        if not sections['overview'] and not sections['modules']:
            sections['overview'] = response_text
        
        return sections
    
    def _format_patterns(self, patterns: Dict) -> str:
        """Format patterns for LLM prompt"""
        lines = []
        for name, data in patterns.items():
            if data.get('detected'):
                lines.append(f"{name.upper()}: {data.get('confidence', 0)*100:.0f}% confidence")
                if 'layers' in data:
                    lines.append(f"  Layers: {', '.join(data['layers'])}")
        return '\n'.join(lines) if lines else 'No patterns detected'
    
    def _build_architecture_prompt(self, evidence: List[Dict]) -> str:
        evidence_text = "\n\n".join([
            f"File: {e['file']}\n{e['code']}"
            for e in evidence
        ])
        
        return f"""You are analyzing a software repository using only supplied evidence.

Rules:
- Do not assume undocumented behavior
- Cite files for every claim
- Infer only from dependencies shown

Evidence:
{evidence_text}

Task: Infer the architectural pattern and explain module responsibilities.
Format your response with file citations."""
    
    def _build_impact_prompt(self, file_path: str, evidence: List[Dict], affected: List[str]) -> str:
        evidence_text = "\n\n".join([
            f"File: {e['file']}\n{e['code']}"
            for e in evidence
        ])
        
        return f"""Analyze the impact of modifying: {file_path}

Affected files: {', '.join(affected)}

Evidence:
{evidence_text}

Explain what consequences this change may have. Cite specific files."""
    
    def explain_impact_with_graph(
        self,
        file_path: str,
        change_type: str,
        direct: List[str],
        indirect: List[str],
        functions: List[Dict],
        risk_level: str,
        risk_score: int,
        graphify_file_context: Optional[Dict] = None,
    ) -> str:
        """Generate a blast-radius impact explanation enriched with Graphify's
        knowledge of actual functions and classes inside the changed file."""
        from pathlib import Path

        filename = Path(file_path).name
        direct_list = "\n".join([f"  - {Path(f).name}" for f in direct[:10] if f]) or "  None"
        indirect_list = "\n".join([f"  - {Path(f).name}" for f in indirect[:10] if f]) or "  None"
        func_list = "\n".join([f"  - {fn['name']} ({fn['caller_count']} callers)" for fn in functions[:10]]) or "  None"

        # Graphify structural enrichment
        graphify_section = ""
        if graphify_file_context:
            gf_funcs = graphify_file_context.get("functions", [])
            gf_classes = graphify_file_context.get("classes", [])
            if gf_funcs or gf_classes:
                graphify_section = "\nKnown symbols in this file (from knowledge graph):"
                if gf_classes:
                    graphify_section += f"\n  Classes: {', '.join(gf_classes[:8])}"
                if gf_funcs:
                    graphify_section += f"\n  Functions: {', '.join(gf_funcs[:12])}"

        prompt = f"""Analyze the impact of {change_type.upper()}ing file: {filename}

BLAST RADIUS ANALYSIS:

Direct Dependents ({len(direct)} files):
{direct_list}

Indirect Dependents ({len(indirect)} files):
{indirect_list}

Functions Affected ({len(functions)} functions):
{func_list}{graphify_section}

Risk Assessment: {risk_level.upper()} (Score: {risk_score}/100)

Provide a concise 2-3 sentence summary explaining:
1. What components are directly impacted (cite actual function/class names if available)
2. The cascading effects on the system
3. Key risks to consider"""

        return self._call_llm(prompt)

    def _build_function_prompt(self, function_name: str, function_info: Dict, callers: List[Dict], context: List[Dict], function_code: str = None) -> str:
        """Build prompt for function explanation"""
        caller_text = "\n".join([
            f"- {c.get('file', 'unknown')}"
            for c in callers
        ]) if callers else "No direct callers found"
        
        context_text = "\n\n".join([
            f"Related code in {c['metadata']['file_path']}:\n{c['code']}"
            for c in context
        ]) if context else "No additional context"
        
        code_section = f"\n\nActual Function Code:\n```\n{function_code}\n```" if function_code else ""
        
        return f"""Analyze the function: {function_name}

Location: {function_info.get('file')} (line {function_info.get('line')}){code_section}

Called by:
{caller_text}

Related code context:
{context_text}

Provide:
1. Purpose of this function (based on actual code)
2. How it's used in the codebase
3. Impact if modified
4. Key dependencies

Be concise and cite specific files."""
    
    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
    
    def _call_llm_with_limit(self, prompt: str, max_tokens: int = 1200) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
