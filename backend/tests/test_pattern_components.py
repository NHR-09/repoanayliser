import unittest

import networkx as nx

from src.graph.analyzers import PatternDetector


class PatternComponentTests(unittest.TestCase):
    def test_pattern_results_include_component_file_identities(self):
        graph = nx.DiGraph()
        service = r'C:\repo\services\patient_service.py'
        gateway = r'C:\repo\gateway\api_gateway.py'
        graph.add_node(service, classes=[{'name': 'PatientService'}], functions=[], imports=[])
        graph.add_node(gateway, classes=[{'name': 'ApiGateway'}], functions=[], imports=[])

        result = PatternDetector(graph).detect_patterns()['microservices']

        self.assertEqual(result['service_files'], [service])
        self.assertEqual(result['gateway_files'], [gateway])
        self.assertEqual(result['services'], 1)
        self.assertEqual(result['gateways'], 1)


if __name__ == '__main__':
    unittest.main()
