from typing import Dict, List, Optional
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

class LLMReasoner:
    def __init__(self, model: Optional[str] = None):
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model or os.getenv("GROQ_MODEL")
        if not self.model:
            self.model = self._resolve_default_model()

    def _resolve_default_model(self) -> str:
        preferred = [
            "openai/gpt-oss-120b",
            "openai/gpt-oss-20b",
            "qwen/qwen3.6-27b",
            "llama-3.3-70b-versatile",
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
        ]
        try:
            available_models = {m.id for m in self.client.models.list().data}
            for pref in preferred:
                if pref in available_models:
                    return pref
            for m in available_models:
                if not m.startswith("whisper") and "guard" not in m:
                    return m
        except Exception:
            pass
        return "openai/gpt-oss-120b"
    
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

Respond with EXACTLY these 3 sections in concise, highly scannable Markdown. Do not write dense paragraphs. Keep every bullet to one or two sentences.

## Overview
Start with one short verdict sentence, followed by exactly these bullets:
- **Purpose** — what problem the system solves.
- **Architecture** — the dominant style and why it fits or does not fit.
- **System flow** — one concrete end-to-end data/control path.
- **Strength** — the most important maintainability or scalability benefit.
- **Risk** — the most important architectural weakness.

## Modules
Use one bullet per major module in this form:
- **Module name** — responsibility; main collaborators; important coupling or boundary concern.
End with a single **Boundary warning** bullet only when the evidence shows a layering violation or tight coupling.

## Key Files
Use one bullet per critical file in this form:
- `path/to/file` — architectural role; why changes are risky; main downstream effect.
List no more than six files. Do not use a table."""
        
        response = self._execute_chat_completion(
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
## 1. Purpose
## 2. Usage in the codebase
## 3. Impact of changes
## 4. Key dependencies

Return valid GitHub-flavored Markdown. Use the exact `##` headings above,
normal bullet lists, fenced code blocks, and Markdown tables only when a table
materially improves clarity. Do not escape Markdown punctuation such as pipes,
backticks, asterisks, or hyphens. Be concise and cite specific files."""
    
    def _execute_chat_completion(self, messages: List[Dict], temperature: float = 0.3, max_tokens: int = 2000):
        try:
            return self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as e:
            new_model = self._resolve_default_model()
            if new_model and new_model != self.model:
                self.model = new_model
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
            raise e

    def _call_llm(self, prompt: str, max_tokens: int = 2000) -> str:
        response = self._execute_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=max_tokens
        )
        return response.choices[0].message.content
