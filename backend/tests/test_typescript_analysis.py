import json
import tempfile
import unittest
from pathlib import Path

from src.graph.dependency_mapper import DependencyMapper
from src.parser.repo_loader import RepositoryLoader
from src.parser.static_parser import StaticParser


class TypeScriptAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp_dir.name)
        (self.repo / 'package.json').write_text(
            json.dumps({
                'name': 'fixture',
                'private': True,
                'workspaces': ['packages/*']
            }),
            encoding='utf-8'
        )
        (self.repo / 'src').mkdir()
        (self.repo / 'packages' / 'shared' / 'src').mkdir(parents=True)
        (self.repo / 'packages' / 'shared' / 'package.json').write_text(
            json.dumps({'name': '@fixture/shared'}),
            encoding='utf-8'
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_typescript_parsing_and_workspace_resolution(self):
        main_file = self.repo / 'src' / 'main.ts'
        helper_file = self.repo / 'src' / 'helper.ts'
        shared_file = self.repo / 'packages' / 'shared' / 'src' / 'index.ts'

        main_file.write_text(
            """import { helper } from './helper.js';
import { shared } from '@fixture/shared';
export { helper } from './helper.js';
export function run(): string { return helper(); }
export const execute = () => run();
class Runner { start(): string { return execute(); } }
""",
            encoding='utf-8'
        )
        helper_file.write_text(
            "export function helper(): string { return 'ok'; }\n",
            encoding='utf-8'
        )
        shared_file.write_text(
            "export const shared = (): string => 'shared';\n",
            encoding='utf-8'
        )

        loader = RepositoryLoader(str(self.repo / 'workspace'))
        files = loader.scan_files(self.repo, ['.ts', '.tsx'])
        self.assertEqual(len(files), 3)
        self.assertTrue(all(item['language'] == 'typescript' for item in files))

        parser = StaticParser()
        parsed = [parser.parse_file(item['path'], item['language']) for item in files]
        parsed_main = next(item for item in parsed if item['file'] == str(main_file))

        self.assertEqual(
            set(parsed_main['imports']),
            {'./helper.js', '@fixture/shared'}
        )
        self.assertTrue({'run', 'execute', 'start'}.issubset(
            {item['name'] for item in parsed_main['functions']}
        ))
        self.assertTrue(any(
            item.get('caller') == 'execute' and item.get('callee') == 'run'
            for item in parsed_main['function_to_function_calls']
        ))

        mapper = DependencyMapper()
        mapper.build_graph(parsed)
        internal_edges = {
            (Path(source), Path(target))
            for source, target, data in mapper.graph.edges(data=True)
            if data.get('type') == 'imports'
        }
        self.assertIn((main_file.resolve(), helper_file.resolve()), internal_edges)
        self.assertIn((main_file.resolve(), shared_file.resolve()), internal_edges)


if __name__ == '__main__':
    unittest.main()
