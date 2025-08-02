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
        """,
        
        # TypeScript/JavaScript specific entity types
        'Method': """
            CREATE NODE TABLE IF NOT EXISTS Method(
                id STRING,
                name STRING,
                file_id STRING,
                class_id STRING,
                docstring STRING,
                line_start INT64,
                line_end INT64,
                signature STRING,
                return_type STRING,
                is_async BOOLEAN,
                is_static BOOLEAN,
                accessibility STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Interface': """
            CREATE NODE TABLE IF NOT EXISTS Interface(
                id STRING,
                name STRING,
                file_id STRING,
                docstring STRING,
                line_start INT64,
                line_end INT64,
                property_count INT64,
                method_count INT64,
                PRIMARY KEY (id)
            )
        """,
        
        'Type': """
            CREATE NODE TABLE IF NOT EXISTS Type(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                type_definition STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Enum': """
            CREATE NODE TABLE IF NOT EXISTS Enum(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                values STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Export': """
            CREATE NODE TABLE IF NOT EXISTS Export(
                id STRING,
                name STRING,
                file_id STRING,
                line_number INT64,
                export_type STRING,
                is_default BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'ArrayPattern': """
            CREATE NODE TABLE IF NOT EXISTS ArrayPattern(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                pattern_type STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Constructor': """
            CREATE NODE TABLE IF NOT EXISTS Constructor(
                id STRING,
                name STRING,
                file_id STRING,
                class_id STRING,
                line_start INT64,
                line_end INT64,
                signature STRING,
                accessibility STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Getter': """
            CREATE NODE TABLE IF NOT EXISTS Getter(
                id STRING,
                name STRING,
                file_id STRING,
                class_id STRING,
                line_start INT64,
                line_end INT64,
                return_type STRING,
                accessibility STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Setter': """
            CREATE NODE TABLE IF NOT EXISTS Setter(
                id STRING,
                name STRING,
                file_id STRING,
                class_id STRING,
                line_start INT64,
                line_end INT64,
                parameter_type STRING,
                accessibility STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'Decorator': """
            CREATE NODE TABLE IF NOT EXISTS Decorator(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                decorator_name STRING,
                arguments STRING,
                PRIMARY KEY (id)
            )
        """,
        
        # Angular-specific entity types
        'AngularComponent': """
            CREATE NODE TABLE IF NOT EXISTS AngularComponent(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                selector STRING,
                template_url STRING,
                style_url STRING,
                standalone BOOLEAN,
                imports STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularService': """
            CREATE NODE TABLE IF NOT EXISTS AngularService(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                provided_in STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularDirective': """
            CREATE NODE TABLE IF NOT EXISTS AngularDirective(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                selector STRING,
                standalone BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularPipe': """
            CREATE NODE TABLE IF NOT EXISTS AngularPipe(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                pipe_name STRING,
                standalone BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularModule': """
            CREATE NODE TABLE IF NOT EXISTS AngularModule(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                declarations STRING,
                imports STRING,
                exports STRING,
                providers STRING,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularInput': """
            CREATE NODE TABLE IF NOT EXISTS AngularInput(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                input_name STRING,
                required BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'AngularOutput': """
            CREATE NODE TABLE IF NOT EXISTS AngularOutput(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                output_name STRING,
                event_type STRING,
                PRIMARY KEY (id)
            )
        """,
        
        # JavaScript-specific entity types for external references
        'ArrowFunction': """
            CREATE NODE TABLE IF NOT EXISTS ArrowFunction(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                signature STRING,
                return_type STRING,
                is_async BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'GeneratorFunction': """
            CREATE NODE TABLE IF NOT EXISTS GeneratorFunction(
                id STRING,
                name STRING,
                file_id STRING,
                line_start INT64,
                line_end INT64,
                signature STRING,
                return_type STRING,
                is_async BOOLEAN,
                PRIMARY KEY (id)
            )
        """,
        
        'ExternalProperty': """
            CREATE NODE TABLE IF NOT EXISTS ExternalProperty(
                id STRING,
                name STRING,
                file_id STRING,
                object_name STRING,
                property_path STRING,
                line_number INT64,
                PRIMARY KEY (id)
            )
        """,
        
        'ExternalFunction': """
            CREATE NODE TABLE IF NOT EXISTS ExternalFunction(
                id STRING,
                name STRING,
                file_id STRING,
                object_name STRING,
                line_number INT64,
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
        """,
        
        # TypeScript/JavaScript specific relationships
        'EXPORTS': """
            CREATE REL TABLE IF NOT EXISTS EXPORTS(FROM File TO Export, export_type STRING, symbol STRING)
        """,
        
        'ACCESSES': """
            CREATE REL TABLE IF NOT EXISTS ACCESSES(FROM Function TO Variable, property_path STRING, access_location INT64)
        """,
        
        'IMPLEMENTS': """
            CREATE REL TABLE IF NOT EXISTS IMPLEMENTS(FROM Class TO Interface)
        """,
        
        'EXTENDS': """
            CREATE REL TABLE IF NOT EXISTS EXTENDS(FROM Class TO Class)
        """,
        
        # Angular-specific relationships
        'USES_TEMPLATE': """
            CREATE REL TABLE IF NOT EXISTS USES_TEMPLATE(FROM AngularComponent TO File, template_path STRING, resolved_path STRING, component_selector STRING)
        """,
        
        'USES_STYLES': """
            CREATE REL TABLE IF NOT EXISTS USES_STYLES(FROM AngularComponent TO File, style_path STRING, resolved_path STRING, component_selector STRING)
        """,
        
        # Additional containment relationships for new entity types
        'FILE_CONTAINS_METHOD': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_METHOD(FROM File TO Method)
        """,
        
        'FILE_CONTAINS_INTERFACE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_INTERFACE(FROM File TO Interface)
        """,
        
        'FILE_CONTAINS_TYPE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_TYPE(FROM File TO Type)
        """,
        
        'FILE_CONTAINS_ENUM': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ENUM(FROM File TO Enum)
        """,
        
        'FILE_CONTAINS_EXPORT': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_EXPORT(FROM File TO Export)
        """,
        
        'FILE_CONTAINS_ARRAYPATTERN': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ARRAYPATTERN(FROM File TO ArrayPattern)
        """,
        
        'FILE_CONTAINS_CONSTRUCTOR': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_CONSTRUCTOR(FROM File TO Constructor)
        """,
        
        'FILE_CONTAINS_GETTER': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_GETTER(FROM File TO Getter)
        """,
        
        'FILE_CONTAINS_SETTER': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_SETTER(FROM File TO Setter)
        """,
        
        'FILE_CONTAINS_DECORATOR': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_DECORATOR(FROM File TO Decorator)
        """,
        
        'FILE_CONTAINS_ANGULARCOMPONENT': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARCOMPONENT(FROM File TO AngularComponent)
        """,
        
        'FILE_CONTAINS_ANGULARSERVICE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARSERVICE(FROM File TO AngularService)
        """,
        
        'FILE_CONTAINS_ANGULARDIRECTIVE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARDIRECTIVE(FROM File TO AngularDirective)
        """,
        
        'FILE_CONTAINS_ANGULARPIPE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARPIPE(FROM File TO AngularPipe)
        """,
        
        'FILE_CONTAINS_ANGULARMODULE': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARMODULE(FROM File TO AngularModule)
        """,
        
        'FILE_CONTAINS_ANGULARINPUT': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULARINPUT(FROM File TO AngularInput)
        """,
        
        'FILE_CONTAINS_ANGULAROUTPUT': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ANGULAROUTPUT(FROM File TO AngularOutput)
        """,
        
        'FILE_CONTAINS_ARROWFUNCTION': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_ARROWFUNCTION(FROM File TO ArrowFunction)
        """,
        
        'FILE_CONTAINS_GENERATORFUNCTION': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_GENERATORFUNCTION(FROM File TO GeneratorFunction)
        """,
        
        'FILE_CONTAINS_EXTERNALPROPERTY': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_EXTERNALPROPERTY(FROM File TO ExternalProperty)
        """,
        
        'FILE_CONTAINS_EXTERNALFUNCTION': """
            CREATE REL TABLE IF NOT EXISTS FILE_CONTAINS_EXTERNALFUNCTION(FROM File TO ExternalFunction)
        """,
        
        'CLASS_CONTAINS_METHOD': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_METHOD(FROM Class TO Method)
        """,
        
        'CLASS_CONTAINS_CONSTRUCTOR': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_CONSTRUCTOR(FROM Class TO Constructor)
        """,
        
        'CLASS_CONTAINS_GETTER': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_GETTER(FROM Class TO Getter)
        """,
        
        'CLASS_CONTAINS_SETTER': """
            CREATE REL TABLE IF NOT EXISTS CLASS_CONTAINS_SETTER(FROM Class TO Setter)
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
            # Get all tables from the database
            tables_result = self.db_service.execute_query("CALL show_tables() RETURN *")
            if tables_result is None:
                validation['valid'] = False
                validation['errors'].append("Could not retrieve tables from database.")
                return validation

            existing_tables = {table['name'] for table in tables_result}
            expected_tables = set(self.NODE_TABLES.keys()) | set(self.RELATIONSHIP_TABLES.keys())

            # Find missing and unexpected tables
            validation['missing_tables'] = list(expected_tables - existing_tables)
            validation['unexpected_tables'] = list(existing_tables - expected_tables)

            if validation['missing_tables'] or validation['unexpected_tables']:
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