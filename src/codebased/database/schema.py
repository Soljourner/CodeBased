"""
Graph schema definition and creation for CodeBased.
"""

import logging
from typing import List, Dict, Any
from .service import DatabaseService

logger = logging.getLogger(__name__)


class GraphSchema:
    """Manages the graph database schema for CodeBased."""
    
    # Node table definitions
    NODE_TABLES = {
        'File': """
            CREATE NODE TABLE IF NOT EXISTS File(
                id STRING,
                name STRING,
                path STRING,
                extension STRING,
                size INT64,
                modified_time INT64,
                hash STRING,
                lines_of_code INT64,
                PRIMARY KEY (id)
            )
        """,
        
        'Module': """
            CREATE NODE TABLE IF NOT EXISTS Module(
                id STRING,
                name STRING,
                file_id STRING,
                docstring STRING,
                line_start INT64,
                line_end INT64,
                PRIMARY KEY (id)
            )
        """,
        
        'Class': """
            CREATE NODE TABLE IF NOT EXISTS Class(
                id STRING,
                name STRING,
                file_id STRING,
                module_id STRING,
                docstring STRING,
                line_start INT64,
                line_end INT64,
                is_abstract BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'Function': """
            CREATE NODE TABLE IF NOT EXISTS Function(
                id STRING,
                name STRING,
                file_id STRING,
                module_id STRING,
                class_id STRING,
                docstring STRING,
                line_start INT64,
                line_end INT64,
                signature STRING,
                return_type STRING,
                is_async BOOLEAN,
                is_generator BOOLEAN,
                is_property BOOLEAN,
                is_staticmethod BOOLEAN,
                is_classmethod BOOLEAN,
                complexity INT64,
                PRIMARY KEY (id)
            )
        """,
        
        'Variable': """
            CREATE NODE TABLE IF NOT EXISTS Variable(
                id STRING,
                name STRING,
                file_id STRING,
                scope_id STRING,
                type_annotation STRING,
                line_number INT64,
                is_global BOOLEAN,
                is_constant BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'Import': """
            CREATE NODE TABLE IF NOT EXISTS Import(
                id STRING,
                name STRING,
                file_id STRING,
                module_name STRING,
                alias STRING,
                line_number INT64,
                is_from_import BOOLEAN,
                PRIMARY KEY (id)
            )
        """
    }
    
    # Relationship table definitions - simplified for Kuzu compatibility
    RELATIONSHIP_TABLES = {
        # Create separate CONTAINS tables for each node type combination
        'FILE_CONTAINS_MODULE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_MODULE(FROM File TO Module)
        """,
        
        'FILE_CONTAINS_CLASS': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_CLASS(FROM File TO Class)
        """,
        
        'FILE_CONTAINS_FUNCTION': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_FUNCTION(FROM File TO Function)
        """,
        
        'FILE_CONTAINS_VARIABLE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_VARIABLE(FROM File TO Variable)
        """,
        
        'FILE_CONTAINS_IMPORT': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_IMPORT(FROM File TO Import)
        """,
        
        'MODULE_CONTAINS_CLASS': """
            CREATE REL TABLE IF NOT EXISTS MODULE_CONTAINS_CLASS(FROM Module TO Class)
        """,
        
        'MODULE_CONTAINS_FUNCTION': """
            CREATE REL TABLE IF NOT EXISTS MODULE_CONTAINS_FUNCTION(FROM Module TO Function)
        """,
        
        'MODULE_CONTAINS_VARIABLE': """
            CREATE REL TABLE IF NOT EXISTS MODULE_CONTAINS_VARIABLE(FROM Module TO Variable)
        """,
        
        'CLASS_CONTAINS_FUNCTION': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_FUNCTION(FROM Class TO Function)
        """,
        
        'CLASS_CONTAINS_VARIABLE': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_VARIABLE(FROM Class TO Variable)
        """,
        
        'FUNCTION_CONTAINS_VARIABLE': """
            CREATE REL TABLE IF NOT EXISTS FUNCTION_CONTAINS_VARIABLE(FROM Function TO Variable)
        """,
        
        'FUNCTION_CONTAINS_FUNCTION': """
            CREATE REL TABLE IF NOT EXISTS FUNCTION_CONTAINS_FUNCTION(FROM Function TO Function)
        """,
        
        'CLASS_CONTAINS_CLASS': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_CLASS(FROM Class TO Class)
        """,
        
        'CALLS': """
            CREATE REL TABLE IF NOT EXISTS CALLS(FROM Function TO Function, call_type STRING, line_number INT64)
        """,
        
        'IMPORTS': """
            CREATE REL TABLE IF NOT EXISTS IMPORTS(FROM File TO File, import_type STRING)
        """,
        
        'INHERITS': """
            CREATE REL TABLE IF NOT EXISTS INHERITS(FROM Class TO Class)
        """,
        
        'USES': """
            CREATE REL TABLE IF NOT EXISTS USES(FROM Function TO Variable, usage_type STRING, line_number INT64)
        """,
        
        'DECORATES': """
            CREATE REL TABLE IF NOT EXISTS DECORATES(FROM Function TO Function, decorator_name STRING)
        """
    }
    
    # Indexes for performance optimization - disabled due to Kuzu version compatibility
    INDEXES = [
        # Kuzu handles indexing automatically for primary keys and frequently accessed properties
    ]
    
    def __init__(self, db_service: DatabaseService):
        """
        Initialize schema manager.
        
        Args:
            db_service: Database service instance
        """
        self.db_service = db_service
    
    def create_schema(self) -> bool:
        """
        Create the complete graph schema.
        
        Returns:
            bool: True if schema creation successful, False otherwise
        """
        try:
            logger.info("Creating graph schema...")
            
            # Create node tables
            for table_name, create_sql in self.NODE_TABLES.items():
                logger.debug(f"Creating node table: {table_name}")
                result = self.db_service.execute_query(create_sql)
                if result is None:
                    logger.error(f"Failed to create node table: {table_name}")
                    return False
            
            # Create relationship tables
            for table_name, create_sql in self.RELATIONSHIP_TABLES.items():
                logger.debug(f"Creating relationship table: {table_name}")
                result = self.db_service.execute_query(create_sql)
                if result is None:
                    logger.error(f"Failed to create relationship table: {table_name}")
                    return False
            
            # Create indexes
            for index_sql in self.INDEXES:
                logger.debug(f"Creating index: {index_sql}")
                result = self.db_service.execute_query(index_sql)
                if result is None:
                    logger.warning(f"Failed to create index: {index_sql}")
                    # Don't fail on index creation errors
            
            logger.info("Graph schema created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create graph schema: {e}")
            return False
    
    def drop_schema(self) -> bool:
        """
        Drop all schema elements (dangerous operation).
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            logger.warning("Dropping graph schema...")
            
            # Drop known tables in reverse order (relationships first, then nodes)
            for table_name in list(self.RELATIONSHIP_TABLES.keys()):
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                logger.debug(f"Dropping relationship table: {table_name}")
                self.db_service.execute_query(drop_sql)
            
            for table_name in list(self.NODE_TABLES.keys()):
                drop_sql = f"DROP TABLE IF EXISTS {table_name}"
                logger.debug(f"Dropping node table: {table_name}")
                self.db_service.execute_query(drop_sql)
            
            logger.info("Graph schema dropped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to drop graph schema: {e}")
            return False
    
    def validate_schema(self) -> Dict[str, Any]:
        """
        Validate that the schema exists and is correct.
        
        Returns:
            Dictionary with validation results
        """
        validation = {
            'valid': True,
            'tables': {},
            'missing_tables': [],
            'unexpected_tables': [],
            'errors': []
        }
        
        try:
            # Try to query each expected table to check if it exists
            expected_tables = set(self.NODE_TABLES.keys()) | set(self.RELATIONSHIP_TABLES.keys())
            
            for table_name in expected_tables:
                try:
                    # Try a simple query to check if table exists
                    test_query = f"MATCH (n:{table_name}) RETURN count(n) LIMIT 1" if table_name in self.NODE_TABLES else f"MATCH ()-[r:{table_name}]->() RETURN count(r) LIMIT 1"
                    result = self.db_service.execute_query(test_query)
                    validation['tables'][table_name] = {'exists': True}
                except Exception:
                    validation['missing_tables'].append(table_name)
                    validation['valid'] = False
            
            logger.info(f"Schema validation: {'valid' if validation['valid'] else 'invalid'}")
            
        except Exception as e:
            validation['valid'] = False
            validation['errors'].append(str(e))
            logger.error(f"Schema validation failed: {e}")
        
        return validation
    
    def get_schema_info(self) -> Dict[str, Any]:
        """
        Get detailed schema information.
        
        Returns:
            Dictionary with schema details
        """
        info = {
            'node_tables': list(self.NODE_TABLES.keys()),
            'relationship_tables': list(self.RELATIONSHIP_TABLES.keys()),
            'total_tables': len(self.NODE_TABLES) + len(self.RELATIONSHIP_TABLES),
            'indexes': len(self.INDEXES),
            'validation': self.validate_schema()
        }
        
        return info
    
    def reset_schema(self) -> bool:
        """
        Reset the schema by dropping and recreating it.
        
        Returns:
            bool: True if successful, False otherwise
        """
        logger.info("Resetting graph schema...")
        
        if not self.drop_schema():
            return False
        
        if not self.create_schema():
            return False
        
        logger.info("Graph schema reset successfully")
        return True