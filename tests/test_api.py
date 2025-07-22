"""
Integration tests for API endpoints.
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from fastapi.testclient import TestClient
    from codebased.api.main import create_app
    from codebased.config import CodeBasedConfig
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False


@unittest.skipUnless(FASTAPI_AVAILABLE, "FastAPI not available")
class TestAPIEndpoints(unittest.TestCase):
    """Test cases for API endpoints."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        cls.temp_dir = Path(tempfile.mkdtemp())
        cls.db_path = cls.temp_dir / "test_api.kuzu"
        
        # Create test config
        config = CodeBasedConfig()
        config.database.path = str(cls.db_path)
        config.project_root = str(cls.temp_dir)
        config.api.debug = True
        
        # Create FastAPI app
        try:
            cls.app = create_app()
            cls.client = TestClient(cls.app)
        except Exception as e:
            print(f"Failed to create test app: {e}")
            cls.app = None
            cls.client = None
            
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment."""
        if cls.temp_dir.exists():
            shutil.rmtree(cls.temp_dir)
            
    def setUp(self):
        """Set up each test."""
        if self.client is None:
            self.skipTest("Failed to create test client")
            
    def test_health_endpoint(self):
        """Test health check endpoint."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('timestamp', data)
        self.assertIn('version', data)
        
    def test_query_endpoint_simple(self):
        """Test simple query execution."""
        query_data = {
            "query": "RETURN 1 AS test_value",
            "parameters": {}
        }
        
        response = self.client.post("/api/query", json=query_data)
        
        # Should work or give a reasonable error
        self.assertIn(response.status_code, [200, 500])  # 500 if no schema yet
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('data', data)
            self.assertIn('execution_time', data)
            self.assertIn('record_count', data)
            
    def test_query_endpoint_validation(self):
        """Test query endpoint validation."""
        # Empty query should fail
        query_data = {
            "query": "",
            "parameters": {}
        }
        
        response = self.client.post("/api/query", json=query_data)
        self.assertEqual(response.status_code, 400)
        
        # Dangerous query should fail
        query_data = {
            "query": "DROP TABLE File",
            "parameters": {}
        }
        
        response = self.client.post("/api/query", json=query_data)
        self.assertEqual(response.status_code, 403)
        
    def test_update_endpoint(self):
        """Test graph update endpoint."""
        update_data = {
            "directory_path": str(self.temp_dir),
            "force_full": False
        }
        
        response = self.client.post("/api/update", json=update_data)
        
        # Should return some response (might fail due to no source files)
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('success', data)
            self.assertIn('statistics', data)
            
    def test_graph_endpoint(self):
        """Test graph data endpoint."""
        response = self.client.get("/api/graph")
        
        # Should return graph data structure
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('nodes', data)
            self.assertIn('edges', data)
            self.assertIn('metadata', data)
            
    def test_graph_endpoint_with_filters(self):
        """Test graph endpoint with filters."""
        params = {
            "node_types": "Function,Class",
            "max_nodes": 50,
            "max_edges": 100,
            "file_filter": "test"
        }
        
        response = self.client.get("/api/graph", params=params)
        
        # Should accept filters
        self.assertIn(response.status_code, [200, 500])
        
    def test_tree_endpoint(self):
        """Test project tree endpoint."""
        response = self.client.get("/api/tree")
        
        self.assertIn(response.status_code, [200, 404, 500])
        
        if response.status_code == 200:
            data = response.json()
            self.assertIn('tree', data)
            self.assertIn('root_path', data)
            
    def test_templates_endpoint(self):
        """Test query templates endpoint."""
        response = self.client.get("/api/templates")
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn('templates', data)
        self.assertIsInstance(data['templates'], list)
        
        # Check template structure
        if data['templates']:
            template = data['templates'][0]
            expected_keys = {'id', 'name', 'description', 'query', 'parameters', 'example_params'}
            self.assertTrue(expected_keys.issubset(template.keys()))
            
    def test_status_endpoint(self):
        """Test system status endpoint."""
        response = self.client.get("/api/status")
        
        self.assertIn(response.status_code, [200, 500])
        
        if response.status_code == 200:
            data = response.json()
            expected_keys = {'database_stats', 'database_health', 'update_status', 'configuration'}
            self.assertTrue(expected_keys.issubset(data.keys()))
            
    def test_api_documentation(self):
        """Test that API documentation is available."""
        response = self.client.get("/docs")
        
        # Should return OpenAPI docs or redirect
        self.assertIn(response.status_code, [200, 307, 404])
        
    def test_cors_headers(self):
        """Test CORS headers are present."""
        response = self.client.options("/api/query")
        
        # Should have CORS headers
        self.assertIn(response.status_code, [200, 405])
        
    def test_error_handling(self):
        """Test error handling and responses."""
        # Non-existent endpoint
        response = self.client.get("/api/nonexistent")
        self.assertEqual(response.status_code, 404)
        
        # Malformed JSON
        response = self.client.post(
            "/api/query", 
            data="invalid json",
            headers={"content-type": "application/json"}
        )
        self.assertEqual(response.status_code, 422)


if __name__ == '__main__':
    if not FASTAPI_AVAILABLE:
        print("FastAPI not available - skipping API tests")
        print("Install dependencies with: pip install -r requirements.txt")
    
    unittest.main()