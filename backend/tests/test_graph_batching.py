import unittest

from src.graph.graph_db import GraphDB


class FakeResult:
    def consume(self):
        return self


class FakeTransaction:
    def __init__(self):
        self.calls = []

    def run(self, query, **parameters):
        self.calls.append((query, parameters))
        return FakeResult()


class FakeSession:
    def __init__(self, transaction):
        self.transaction = transaction

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute_write(self, callback):
        return callback(self.transaction)

    def run(self, query, **parameters):
        return self.transaction.run(query, **parameters)


class FakeDriver:
    def __init__(self):
        self.transaction = FakeTransaction()

    def session(self):
        return FakeSession(self.transaction)


class GraphBatchingTests(unittest.TestCase):
    def setUp(self):
        self.graph = GraphDB.__new__(GraphDB)
        self.graph.driver = FakeDriver()

    def test_repository_analysis_uses_one_query_per_entity_type(self):
        parsed = [{
            'file': 'src/example.ts',
            'language': 'typescript',
            'file_hash': 'abc',
            'classes': [{'name': 'Example', 'line': 1}],
            'functions': [{'name': 'run', 'line': 2}],
            'imports': ['./helper'],
            'function_calls': ['helper'],
            'function_to_function_calls': [{'caller': 'run', 'callee': 'helper'}]
        } for _ in range(112)]

        counts = self.graph.bulk_store_analysis(parsed, 'repo', 'snapshot')

        self.assertEqual(len(self.graph.driver.transaction.calls), 6)
        self.assertEqual(counts['files'], 112)
        self.assertEqual(counts['functions'], 112)
        self.assertTrue(all('UNWIND $rows' in query for query, _ in
                            self.graph.driver.transaction.calls))

    def test_dependencies_are_deduplicated_and_batched(self):
        count = self.graph.bulk_create_dependencies([
            ('src/a.ts', 'src/b.ts'),
            ('src/a.ts', 'src/b.ts'),
            ('src/b.ts', 'src/b.ts')
        ])

        self.assertEqual(count, 1)
        self.assertEqual(len(self.graph.driver.transaction.calls), 1)
        _, parameters = self.graph.driver.transaction.calls[0]
        self.assertEqual(len(parameters['rows']), 1)


if __name__ == '__main__':
    unittest.main()
