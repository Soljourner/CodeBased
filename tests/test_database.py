"""
Unit tests for database functionality.
"""

import unittest
import tempfile
import shutil
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

try:
    from codebased.database.service import DatabaseService
    from codebased.database.schema import GraphSchema
    KUZU_AVAILABLE = True
except ImportError:
    KUZU_AVAILABLE = False


@unittest.skipUnless(KUZU_AVAILABLE, "Kuzu not available")
class TestDatabaseService(unittest.TestCase):
    """Test cases for database service."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_graph.kuzu"
        self.db_service = DatabaseService(str(self.db_path))
        
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'db_service'):
            self.db_service.disconnect()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def test_database_initialization(self):
        """Test database initialization."""
        result = self.db_service.initialize()
        self.assertTrue(result)
        self.assertTrue(self.db_path.exists())
        
    def test_database_connection(self):
        """Test database connection."""
        self.db_service.initialize()
        result = self.db_service.connect()
        self.assertTrue(result)
        
    def test_execute_simple_query(self):
        """Test executing a simple query."""
        self.db_service.initialize()
        
        # This should work even with empty database
        result = self.db_service.execute_query("RETURN 1 AS test_value")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['test_value'], 1)
        
    def test_execute_query_with_parameters(self):
        """Test executing query with parameters."""
        self.db_service.initialize()
        
        result = self.db_service.execute_query(
            "RETURN $value AS test_value", 
            {"value": "hello"}
        )
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['test_value'], "hello")
        
    def test_execute_invalid_query(self):
        """Test handling of invalid queries."""
        self.db_service.initialize()
        
        result = self.db_service.execute_query("INVALID CYPHER QUERY")
        self.assertIsNone(result)
        
    def test_health_check(self):
        """Test database health check."""
        # Before initialization
        health = self.db_service.health_check()
        self.assertIn('status', health)
        
        # After initialization
        self.db_service.initialize()
        health = self.db_service.health_check()
        self.assertIn('status', health)
        self.assertIn('db_exists', health)
        
    def test_get_stats(self):
        """Test getting database statistics."""
        self.db_service.initialize()
        
        stats = self.db_service.get_stats()
        self.assertIn('nodes', stats)
        self.assertIn('relationships', stats)
        self.assertIn('tables', stats)
        
        # Initially should be zero
        self.assertEqual(stats['nodes'], 0)
        self.assertEqual(stats['relationships'], 0)


@unittest.skipUnless(KUZU_AVAILABLE, "Kuzu not available")
class TestGraphSchema(unittest.TestCase):
    """Test cases for graph schema."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.db_path = self.temp_dir / "test_schema.kuzu"
        self.db_service = DatabaseService(str(self.db_path))
        self.schema = GraphSchema(self.db_service)
        
    def tearDown(self):
        """Clean up test environment."""
        if hasattr(self, 'db_service') and self.db_service.conn:
            self.db_service.disconnect()
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            
    def test_create_schema(self):
        """Test schema creation."""
        self.db_service.initialize()
        result = self.schema.create_schema()
        self.assertTrue(result)
        
        # Verify tables were created
        tables_result = self.db_service.execute_query("CALL show_tables() RETURN *")
        self.assertIsNotNone(tables_result)
        self.assertGreater(len(tables_result), 0)
        
        # Check for expected table names
        table_names = {table['name'] for table in tables_result}
        expected_tables = {'File', 'Module', 'Class', 'Function', 'Variable', 'Import'}
        self.assertTrue(expected_tables.issubset(table_names))
        
    def test_validate_schema(self):
        """Test schema validation."""
        # Before creating schema
        self.db_service.initialize()
        print("Before validation")
        validation = self.schema.validate_schema()
        print(f"Validation result: {validation}")
        self.assertFalse(validation['valid'])
        
        # After creating schema
        self.schema.create_schema()
        validation = self.schema.validate_schema()
        self.assertTrue(validation['valid'])
        self.assertEqual(len(validation['missing_tables']), 0)
        
    def test_schema_info(self):
        """Test getting schema information."""
        self.db_service.initialize()
        self.schema.create_schema()
        info = self.schema.get_schema_info()
        
        self.assertIn('node_tables', info)
        self.assertIn('relationship_tables', info)
        self.assertIn('total_tables', info)
        self.assertIn('validation', info)
        
        # Check expected counts
        self.assertGreater(len(info['node_tables']), 0)
        self.assertGreater(len(info['relationship_tables']), 0)
        
    def test_reset_schema(self):
        """Test schema reset."""
        # Create schema first
        self.db_service.initialize()
        self.schema.create_schema()
        
        # Verify it exists
        validation = self.schema.validate_schema()
        self.assertTrue(validation['valid'])
        
        # Reset schema
        result = self.schema.reset_schema()
        self.assertTrue(result)
        
        # Verify it was recreated
        validation = self.schema.validate_schema()
        self.assertTrue(validation['valid'])


if __name__ == '__main__':
    if not KUZU_AVAILABLE:
        print("Kuzu not available - skipping database tests")
        print("Install dependencies with: pip install -r requirements.txt")
    
    unittest.main()