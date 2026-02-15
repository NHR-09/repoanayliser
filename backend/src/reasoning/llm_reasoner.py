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
    
    def _call_llm(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000
        )
        return response.choices[0].message.content
