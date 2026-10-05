# ARCHITECH MCP Server Plan

## 1. What the server should serve

An MCP server should expose capabilities and evidence, not dump an entire workspace into a model prompt. ARCHITECH's server therefore serves small, repository-scoped answers backed by its existing code graph:

- repository discovery and analysis;
- symbol search and exact file/function context;
- dependency and call relationships;
- architecture summaries and detected pattern evidence;
- change-impact and blast-radius estimates;
- code-health candidates such as unreferenced or duplicated code;
- snapshot history and compact comparisons;
- incremental graph refreshes after local edits.

The server is read-mostly. The only graph mutations are explicit repository analysis and incremental synchronization. It deliberately exposes no delete/clear-database tool.

MCP supports tools, resources, and prompts. This MVP uses tools because ARCHITECH answers are parameterized, freshness-sensitive operations selected by the model. Static resources would duplicate tool results and many clients attach them directly to context; reusable prompts would add discovery/schema overhead without adding evidence. A later HTTP release can add snapshot-report resources if a client needs application-controlled attachment.

## 2. How effective ARCHITECH is as an MCP server

ARCHITECH is a strong fit because its expensive structural work already produces a reusable Neo4j knowledge graph. An assistant can ask a focused question and receive graph evidence without rereading hundreds of source files. Existing alternatives validate the category: Sourcegraph exposes code search/navigation to MCP clients, while GitNexus exposes a repository knowledge graph. ARCHITECH's useful differentiation is architecture recovery, confidence-scored pattern evidence, blast radius, code-health review, historical snapshots, and optional LLM-written architecture explanations in one repository-scoped service.

Expected strengths:

- much smaller prompts for cross-file questions;
- deterministic, repository-isolated evidence before LLM interpretation;
- fast repeated queries after analysis;
- live local changes without rerunning the full LLM analysis;
- useful architecture and maintenance views beyond symbol lookup.

Known limitations:

- static analysis cannot fully resolve reflection, dynamic dispatch, generated code, or framework magic;
- Neo4j must be available for graph-backed tools;
- an MCP client does not universally emit save events, so automatic save synchronization is opt-in and process-local; manual `sync_repository_changes` remains the reliable fallback;
- cached architecture prose can lag live edits; it is revision-tagged and withheld until explicit regeneration.

## 3. Feature implementation

| Capability | MCP tool | Implementation |
|---|---|---|
| Discover analyzed repositories | `list_repositories` | Bounded, paginated Neo4j query with counts and paths relative to the repository. |
| Add/analyze a repository | `analyze_repository` | Lazy call into the existing `AnalysisEngine`; stdout is redirected away from the stdio protocol and calls are serialized. |
| Find code | `search_symbols` | Repository-scoped file/function/class search with kind filters and opaque cursors. |
| File context | `get_file_context` | Exact repository-scoped dependencies, dependents, symbols, and optional bounded source excerpt. |
| Function context | `get_function_context` | File-disambiguated function, callers, callees, call lines, and optional bounded source excerpt. |
| Architecture and patterns | `get_architecture` | Computes current structural evidence, returns revision-matched cached interpretation only, and performs optional explicit LLM generation only when requested. |
| Change impact | `get_change_impact` | Bounded 1-3 hop traversal that labels upstream reverse dependencies as possible impact and downstream edges as dependencies, with risk scored only from upstream impact. |
| Redundancy/unused review | `get_code_health` | Static candidates, duplicates, confidence, caveats, category filtering, and pagination. |
| History | `get_snapshots` | Snapshot list or compact structural comparison; detailed entries are capped. |
| Local changes | `sync_repository_changes` | SHA-256 scan, parse only changed files, remove deleted files, batch-rebuild graph edges, and persist compressed parse state. |
| Automatic saves | `manage_live_sync` | Optional debounced filesystem watcher; updates are coalesced and sent through the same incremental pipeline. |

## 4. Dynamic analysis strategy

The unit of recomputation is a changed file, not the whole workspace and not a durable snapshot per save.

1. Scan supported files and compare SHA-256 hashes with SQLite state.
2. Parse only created/modified files with the existing tree-sitter parser.
3. Remove stale symbols for modified/deleted files.
4. Batch-upsert current symbols and rebuild dependency/call edges from compressed parse metadata.
5. Record a small ephemeral checkpoint only when explicitly requested.
6. Reserve durable ARCHITECH snapshots and LLM regeneration for manual analysis, commits, or meaningful milestones.

The first sync bootstraps parse metadata for existing files. Later saves are typically one-file parses plus batched relationship updates. This removes the original per-file network round trips that dominated analysis time.

## 5. Token and context controls

- Eleven focused tools instead of exposing raw Cypher or a whole-graph dump.
- Repository ID required for every code query; function queries also require a file path.
- Summary-first defaults; source and LLM prose are opt-in.
- Hard caps on limits, graph depth, source lines, and returned characters.
- Opaque cursor pagination rather than oversized arrays.
- Repository-relative paths in responses.
- Empty/null fields removed before transport.
- Structured output lets clients consume fields without parsing long prose.
- Pattern components, callers, dependencies, and diffs are independently capped.
- No embeddings are sent to clients and no full workspace is inserted into prompts.

## 6. Storage plan

| Data | Store | Reason |
|---|---|---|
| Repository graph, snapshots, architecture cache | Existing Neo4j | Shared authoritative structural data. |
| File hashes, compressed parser results, ephemeral checkpoints | Local SQLite (`.data/state.sqlite3`) | Fast, transactional, portable, and cheap for save-driven deltas. |
| Source code | Original repository | Avoid duplicate source storage. |
| Runtime watcher/task state | Memory | Process-local and automatically discarded. |
| Browser graph notification | Neo4j revision + loopback HTTP + SSE | Durable cross-process version, immediate local fan-out, bounded one-event client queues, and reconnect catch-up. |

SQLite uses WAL mode, compressed JSON parser payloads, and checkpoint retention. A vector database is intentionally not added: exact symbols and graph traversal are more precise for these tools, and embeddings would increase storage and retrieval-token costs.

Heavy full-analysis/LLM operations run through `backend_bridge.py` in the existing backend environment. This keeps Graphify, Groq, SciPy, and extra parser grammars out of the MCP environment while retaining all application features.

## 7. Safety and isolation

- Paths are resolved and rejected if they escape the selected repository root.
- All graph queries are explicitly scoped by `repo_id`.
- No database-delete tool is exposed.
- Remote/local analysis is an explicit tool invocation.
- Tool errors are concise and do not expose credentials.
- stdio stdout is reserved for MCP messages; backend progress is redirected to stderr.
- MCP dependencies run in a separate virtual environment from FastAPI because current MCP and backend Starlette constraints differ.

## 8. Verification and rollout

1. Unit-test pagination, path containment, SQLite compression/state, and response bounding.
2. Verify MCP tool discovery without connecting to Neo4j.
3. Run protocol smoke tests over stdio.
4. Test graph reads against a real analyzed repository.
5. Test bootstrap sync, one-file edit, delete, and watcher debounce.
6. Measure tool response bytes and enforce the documented caps.
7. Only after local evaluation, decide whether to version the folder and add a VS Code on-save bridge.

## 9. Research references

- MCP architecture and server primitives: https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/docs/2026-07-28/learn/architecture.mdx
- Official Python SDK, structured output, transports, and pagination: https://github.com/modelcontextprotocol/python-sdk
- Sourcegraph MCP's bounded search/navigation tools: https://sourcegraph.com/docs/api/mcp
- GitNexus's local knowledge-graph/MCP approach: https://github.com/nxpatterns/gitnexus
