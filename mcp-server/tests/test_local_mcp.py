from __future__ import annotations

import asyncio
import hashlib
import tempfile
import unittest
from pathlib import Path

from architech_mcp.storage import StateStore
from architech_mcp.utils import decode_cursor, encode_cursor, ensure_inside, page


class UtilityTests(unittest.TestCase):
    def test_cursor_round_trip_and_page(self):
        cursor = encode_cursor(3)
        self.assertEqual(3, decode_cursor(cursor))
        result = page(list(range(8)), cursor, 2)
        self.assertEqual([3, 4], result["items"])
        self.assertEqual(5, decode_cursor(result["next_cursor"]))

    def test_path_cannot_escape_repository(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            root.mkdir()
            self.assertEqual(root / "src.py", ensure_inside(root, "src.py"))
            with self.assertRaises(ValueError):
                ensure_inside(root, "../secret.txt")


class StorageTests(unittest.TestCase):
    def test_compressed_parse_state_and_retention(self):
        with tempfile.TemporaryDirectory() as directory:
            store = StateStore(Path(directory) / "state.db", checkpoint_retention=2)
            parsed = {"file": str(Path(directory) / "a.py"), "functions": [{"name": "run"}]}
            store.set_repository("repo", directory)
            store.put_file("repo", parsed["file"], "abc", "python", parsed)
            self.assertEqual({parsed["file"]: "abc"}, store.hashes("repo"))
            self.assertEqual(parsed, store.parsed_files("repo")[0])
            for index in range(3):
                store.add_checkpoint("repo", {"index": index})
            self.assertEqual(2, store.stats("repo")["ephemeral_checkpoints"])


class IncrementalTests(unittest.TestCase):
    def test_bootstrap_and_changed_file_parse_only_delta(self):
        from architech_mcp.incremental import IncrementalAnalyzer

        class FakeService:
            def __init__(self, root):
                self.root = root
                self.events = []
                self.architecture_generation_calls = 0

            def repository_root(self, repo_id):
                return self.root

            def publish_graph_update(self, repo_id, changed_files, **metadata):
                event = {"repo_id": repo_id, "changed_files": changed_files, "version": len(self.events) + 1}
                self.events.append(event)
                return event

            def _generate_architecture(self, _repo_id):
                self.architecture_generation_calls += 1
                raise AssertionError("Incremental sync must not invoke the architecture LLM")

        class RecordingAnalyzer(IncrementalAnalyzer):
            def _refresh_graph(self, repo_id, modified, deleted, all_parsed, prune=False):
                self.last_refresh = (modified, deleted, all_parsed)
                return {"files": len(all_parsed), "functions": 0, "dependencies": 0, "function_calls": 0}

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "main.py"
            source.write_text("def first():\n    return 1\n", encoding="utf-8")
            store = StateStore(root / "state.db")
            analyzer = RecordingAnalyzer(FakeService(root), store)

            first = analyzer.sync("repo", create_checkpoint=True)
            self.assertEqual("updated", first["status"])
            self.assertTrue(first["bootstrap"])
            self.assertEqual(1, first["storage"]["cached_files"])
            self.assertEqual("first", analyzer.last_refresh[2][0]["functions"][0]["name"])
            self.assertEqual([["main.py"]], [event["changed_files"] for event in analyzer.service.events])

            source.write_text("def second():\n    return 2\n", encoding="utf-8")
            second = analyzer.sync("repo")
            self.assertEqual("updated", second["status"])
            self.assertFalse(second["bootstrap"])
            self.assertEqual(["main.py"], second["changed"]["modified"])
            self.assertEqual("second", analyzer.last_refresh[2][0]["functions"][0]["name"])
            self.assertEqual(2, len(analyzer.service.events))
            self.assertEqual(0, analyzer.service.architecture_generation_calls)

    def test_ignored_change_never_reaches_graph_or_event(self):
        from architech_mcp.incremental import IncrementalAnalyzer

        class FakeService:
            def __init__(self, root):
                self.root = root
                self.events = []

            def repository_root(self, repo_id):
                return self.root

            def publish_graph_update(self, *args, **kwargs):
                self.events.append((args, kwargs))

        class RecordingAnalyzer(IncrementalAnalyzer):
            def _refresh_graph(self, *args, **kwargs):
                self.fail("ignored file must not trigger a graph write")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            generated = root / ".next" / "server" / "runtime.js"
            generated.parent.mkdir(parents=True)
            generated.write_text("generated", encoding="utf-8")
            analyzer = RecordingAnalyzer(FakeService(root), StateStore(root / "state.db"))
            result = analyzer.sync("repo", changed_paths=[str(generated)])
            self.assertEqual("unchanged", result["status"])
            self.assertEqual([], analyzer.service.events)

    def test_failed_graph_update_does_not_publish_success_event(self):
        from architech_mcp.incremental import IncrementalAnalyzer

        class FakeService:
            def __init__(self, root):
                self.root = root
                self.events = []

            def repository_root(self, repo_id):
                return self.root

            def publish_graph_update(self, *args, **kwargs):
                self.events.append((args, kwargs))

        class FailingAnalyzer(IncrementalAnalyzer):
            def _refresh_graph(self, *args, **kwargs):
                raise RuntimeError("database write failed")

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "main.py").write_text("def main():\n    return 1\n", encoding="utf-8")
            analyzer = FailingAnalyzer(FakeService(root), StateStore(root / "state.db"))
            with self.assertRaisesRegex(RuntimeError, "database write failed"):
                analyzer.sync("repo")
            self.assertEqual([], analyzer.service.events)

    def test_unchanged_sync_does_not_touch_graph(self):
        from architech_mcp.incremental import IncrementalAnalyzer

        class FakeService:
            def __init__(self, root):
                self.root = root

            def repository_root(self, repo_id):
                return self.root

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "main.py"
            source.write_text("def main():\n    return 1\n", encoding="utf-8")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            store = StateStore(root / "state.db")
            store.put_file(
                "repo",
                str(source.resolve()),
                digest,
                "python",
                {"file": str(source.resolve()), "language": "python", "functions": []},
            )
            analyzer = IncrementalAnalyzer(FakeService(root), store)
            result = analyzer.sync("repo")
            self.assertEqual("unchanged", result["status"])


class ProtocolSurfaceTests(unittest.TestCase):
    def test_tool_surface_is_small_and_discoverable(self):
        from architech_mcp.server import server

        tools = asyncio.run(server.list_tools())
        names = {tool.name for tool in tools}
        self.assertEqual(
            {
                "list_repositories",
                "analyze_repository",
                "search_symbols",
                "get_file_context",
                "get_function_context",
                "get_architecture",
                "get_change_impact",
                "get_code_health",
                "get_snapshots",
                "sync_repository_changes",
                "manage_live_sync",
            },
            names,
        )
        self.assertLessEqual(len(tools), 12)


class ServiceSemanticsTests(unittest.TestCase):
    class Result:
        def __init__(self, row):
            self.row = row

        def single(self):
            return self.row

    class Session:
        def __init__(self, responder):
            self.responder = responder

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def run(self, query, **parameters):
            return ServiceSemanticsTests.Result(self.responder(query, parameters))

    def test_stale_architecture_prose_is_not_presented_as_current(self):
        from architech_mcp.service import ArchitechService

        with tempfile.TemporaryDirectory() as directory:
            class Service(ArchitechService):
                def repository_root(self, repo_id):
                    return Path(directory)

                def session(self):
                    return ServiceSemanticsTests.Session(lambda *_: {
                        "snapshot_id": "snapshot", "created_at": "now", "commit": "abc",
                        "macro": "PromptForm.vue is the entry point", "meso": "Vue flow", "micro": "app/app.ts",
                        "interpretation_revision": 2, "interpretation_generated_at": "before",
                        "graph_revision": 3, "repository_coverage": None, "snapshot_coverage": None,
                    })

                def _live_architecture_evidence(self, repo_id, root):
                    return {
                        "total_files": 4, "total_dependencies": 3, "avg_coupling": 1.5,
                        "cycle_count": 0, "_raw_patterns": {},
                    }

            result = Service().architecture("repo", True, False)
            self.assertEqual("stale", result["interpretation"]["status"])
            self.assertNotIn("macro", result)
            self.assertEqual(4, result["total_files"])

    def test_change_impact_keeps_upstream_and_downstream_semantics_separate(self):
        from architech_mcp.service import ArchitechService

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.py"
            upstream = root / "caller.py"
            downstream = root / "database.py"
            for path in (target, upstream, downstream):
                path.write_text("", encoding="utf-8")

            class Service(ArchitechService):
                def repository_root(self, repo_id):
                    return root

                def _resolve_graph_file(self, repo_id, file_path):
                    return target, {"path": str(target)}

                def session(self):
                    def respond(query, _parameters):
                        if "source:File" in query:
                            return {"items": [{"file": str(upstream), "distance": 1}]}
                        return {"items": [{"file": str(downstream), "distance": 1}]}
                    return ServiceSemanticsTests.Session(respond)

            result = Service().change_impact("repo", "target.py", "modify", 2, 20)
            self.assertEqual("caller.py", result["upstream_impact"]["items"][0]["file"])
            self.assertEqual("database.py", result["downstream_dependencies"]["items"][0]["file"])
            self.assertNotIn("affected", result)


if __name__ == "__main__":
    unittest.main()
