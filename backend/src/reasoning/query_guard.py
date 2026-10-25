import os
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

# Suppress TensorFlow probing warnings at transformers/laya import time
os.environ["USE_TF"] = "0"


class LaraDecisionGuard:
    """
    LARA (Laya-Augmented Reasoning Agent) Decision Model Guardrail.
    Uses the open-weights decision model 'convaiinnovations/laya'
    (https://huggingface.co/convaiinnovations/laya) for calibrated agent routing,
    semantic codebase intent classification, and out-of-scope query filtering.
    """

    _MODEL_ID = "convaiinnovations/laya"
    _SHARED_AGENT = None
    _LOAD_FAILED = False

    _CODE_ARTIFACT = re.compile(
        r"(?:\b[\w.-]+\.(?:py|js|jsx|ts|tsx|java|json|css|html|md|sql|yaml|yml)\b"
        r"|(?:^|[\s`])(?:src|backend|frontend|components|retrieval|graph)[\\/][\w./\\-]+"
        r"|\b[a-z][a-z0-9]*_[a-z0-9_]+\b"
        r"|\b[A-Z][a-zA-Z0-9]*\.[a-zA-Z_][a-zA-Z0-9_]*\b)",
        re.IGNORECASE,
    )

    _PROJECT_TERMS = {
        "api", "auth", "architecture", "backend", "bug", "class", "code", "codebase",
        "component", "config", "database", "db", "dependency", "endpoint", "error",
        "exception", "file", "function", "graph", "graphrag", "import", "llm", "login",
        "module", "package", "performance", "project", "query", "rag", "retrieval",
        "repository", "repo", "route", "schema", "search", "security", "service",
        "state", "symbol", "test", "ui", "workflow", "pipeline", "ast", "coupling",
        "snapshot", "mcp", "fastmcp", "neo4j", "qdrant", "vector",
        "parser", "compiler", "refactor", "debug", "deploy", "docker", "middleware",
        "handler", "controller", "model", "migration", "orm", "sdk", "cli", "npm",
        "webpack", "typescript", "javascript", "python", "react", "node", "express",
        "fastapi", "flask", "django", "frontend", "library", "framework", "algorithm",
        "token", "embedding", "transformer", "inference", "guardrail", "lint", "git",
    }

    _DEVELOPER_ACTIONS = {
        "add", "analyze", "change", "compare", "describe", "does", "explain", "find",
        "fix", "how", "implement", "is", "list", "locate", "map", "review", "show",
        "tell", "trace", "update", "use", "uses", "used", "where", "what", "why",
        "work", "works", "implemented"
    }

    def __init__(self, model_id: str = "convaiinnovations/laya", device: str = "cpu", lazy_load: bool = True):
        self.model_id = model_id
        self.device = device
        if not lazy_load:
            self._get_agent(self.model_id, self.device)

    @classmethod
    def _get_agent(cls, model_id: str = "convaiinnovations/laya", device: str = "cpu"):
        if cls._SHARED_AGENT is not None:
            return cls._SHARED_AGENT
        if cls._LOAD_FAILED:
            return None
        try:
            import laya
            logger.info("Initializing LARA Decision Model from %s on %s", model_id, device)
            cls._SHARED_AGENT = laya.load(model_id, device=device)
            return cls._SHARED_AGENT
        except Exception as e:
            logger.warning("Could not load LARA decision model '%s': %s. Falling back to heuristic classifier.", model_id, e)
            cls._LOAD_FAILED = True
            return None

    def _build_laya_questions(self) -> Dict[str, Any]:
        """Define decision questions for the Laya decision model."""
        return {
            "domain": {
                "type": "choice",
                "instructions": (
                    "Determine whether this user query is asking about software engineering, "
                    "code, programming languages, codebase files, functions, APIs, architecture, "
                    "dependencies, Graph RAG, design patterns, testing, bugs, or this project repository."
                ),
                "criteria": {
                    "codebase": (
                        "software code, programming, repository architecture, files, functions, "
                        "classes, APIs, Graph RAG, knowledge graph, dependencies, technical design, "
                        "bugs, or project implementation"
                    ),
                    "unrelated": (
                        "cooking recipes, food, weather, general trivia, chit-chat, jokes, "
                        "sports, personal advice, politics, or non-programming questions"
                    )
                }
            },
            "is_technical": {
                "type": "noul",
                "instructions": "Is the user asking a question about a software codebase, programming, or technical architecture?"
            }
        }

    def evaluate(self, query: str, include_metadata: bool = False) -> Dict[str, Any]:
        """
        Evaluate if user query is related to the project codebase or out of scope.
        Returns:
            {
                "allowed": bool,
                "decision": "in_scope" | "out_of_scope",
                "reason": str,
                "confidence": float (when include_metadata=True),
                "model": "convaiinnovations/laya" (when include_metadata=True),
                "guardrail": "lara_decision_model" (when include_metadata=True)
            }
        """
        normalized = query.strip().lower()
        if not normalized:
            res = {
                "allowed": False,
                "decision": "out_of_scope",
                "reason": "empty_query",
            }
            if include_metadata:
                res.update({"guardrail": "lara_decision_model", "model": self.model_id})
            return res

        # Check explicit code artifacts (instant path)
        has_code_artifact = bool(self._CODE_ARTIFACT.search(query))
        tokens = set(re.findall(r"[a-z0-9_]+", normalized))
        project_terms = tokens.intersection(self._PROJECT_TERMS)
        has_developer_action = bool(tokens.intersection(self._DEVELOPER_ACTIONS))

        # Check heuristic signals
        heuristic_in_scope = False
        heuristic_reason = None
        if has_code_artifact:
            heuristic_in_scope = True
            heuristic_reason = "code_reference"
        elif len(project_terms) >= 2:
            heuristic_in_scope = True
            heuristic_reason = "project_vocabulary"
        elif project_terms and has_developer_action:
            heuristic_in_scope = True
            heuristic_reason = "developer_question"

        # Try Laya Decision Model (convaiinnovations/laya)
        agent = self._get_agent(self.model_id, self.device)
        if agent is not None:
            try:
                questions = self._build_laya_questions()
                res = agent.predict({"query": query}, questions)
                answers = res.get("answers", {})

                domain_ans = answers.get("domain", {})
                choice = domain_ans.get("choice", "unrelated")
                conf = float(domain_ans.get("confidence", 0.0))

                tech_ans = answers.get("is_technical", {})
                p_tech = float(tech_ans.get("noul", 0.0))

                # Strict decision logic (three-tier):
                # 1. Laya says "codebase" or high p_tech → allow
                # 2. Explicit code artifact (file path / qualified symbol) → allow
                # 3. Strong vocabulary (≥2 project terms) → allow  (e.g. "AST parser")
                # 4. Weak single-term + action word → defer to Laya (blocks "joke + architecture")
                laya_allows = choice == "codebase" or p_tech >= 0.55
                hard_code_evidence = has_code_artifact
                strong_vocabulary = len(project_terms) >= 2

                if laya_allows or hard_code_evidence or strong_vocabulary:
                    final_reason = (
                        "code_reference" if hard_code_evidence and not laya_allows
                        else heuristic_reason if heuristic_reason
                        else "laya_decision_codebase"
                    )
                    decision_res = {
                        "allowed": True,
                        "decision": "in_scope",
                        "reason": final_reason,
                    }
                    if include_metadata:
                        decision_res.update({
                            "confidence": max(conf, p_tech),
                            "model": self.model_id,
                            "guardrail": "lara_decision_model",
                        })
                    return decision_res
                else:
                    decision_res = {
                        "allowed": False,
                        "decision": "out_of_scope",
                        "reason": "laya_decision_unrelated",
                    }
                    if include_metadata:
                        decision_res.update({
                            "confidence": conf,
                            "model": self.model_id,
                            "guardrail": "lara_decision_model",
                        })
                    return decision_res
            except Exception as e:
                logger.warning("Error running Laya decision model prediction: %s. Falling back to heuristic.", e)

        # Fallback to deterministic heuristic when Laya model is not loaded (e.g., lightweight unit tests)
        if heuristic_in_scope:
            res = {
                "allowed": True,
                "decision": "in_scope",
                "reason": heuristic_reason,
            }
        else:
            res = {
                "allowed": False,
                "decision": "out_of_scope",
                "reason": "no_project_or_code_signals",
            }
        if include_metadata:
            res.update({"guardrail": "lara_decision_model", "model": self.model_id})
        return res


# Backwards compatibility alias for ProjectQueryGuard
class ProjectQueryGuard(LaraDecisionGuard):
    """
    ProjectQueryGuard: Powered by LARA (Laya-Augmented Reasoning Agent) Decision Model
    (convaiinnovations/laya) with fast-heuristic routing.
    """
    pass
