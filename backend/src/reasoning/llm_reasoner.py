from typing import Dict, List
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
    
    def explain_architecture_report(self, patterns_text: str, graph_context: str, top_dirs: str, evidence_text: str) -> Dict:
        """Single consolidated architecture explanation — replaces 3 separate calls"""
        prompt = f"""You are analyzing a software repository. Based on the data below, provide a structured architecture report.

Detected Patterns:
{patterns_text}

Graph Structure:
{graph_context}

Directory Breakdown:
{top_dirs}

Code Evidence:
{evidence_text}

Respond with EXACTLY these 3 sections using the headers below. Keep each section to 3-5 sentences. Be specific and cite file names.

## Overview
(Overall architecture style, main patterns, and system purpose)

## Modules
(Key modules/layers, their responsibilities, and how they interact)

## Key Files
(Most critical files in the system and why they matter)"""
        
        response = self._call_llm_with_limit(prompt, max_tokens=1200)
        
        # Parse sections from response
        sections = {'overview': '', 'modules': '', 'key_files': ''}
        current = None
        lines = response.split('\n')
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
            sections['overview'] = response
        
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
