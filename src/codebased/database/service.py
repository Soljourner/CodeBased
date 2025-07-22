"""
Kuzu graph database service for CodeBased.
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
import kuzu

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing Kuzu graph database operations."""
    
    def __init__(self, db_path: str = None):
        """
        Initialize database service.
        
        Args:
            db_path: Path to the Kuzu database directory. 
                    Defaults to '.codebased/data/graph.kuzu'
        """
        if db_path is None:
            db_path = ".codebased/data/graph.kuzu"
        
        self.db_path = Path(db_path)
        self.db = None
        self.conn = None
        
    def initialize(self) -> bool:
        """
        Initialize the database and create necessary directories.
        
        Returns:
            bool: True if initialization successful, False otherwise.
        """
        try:
            # Create database directory if it doesn't exist
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Initialize Kuzu database
            self.db = kuzu.Database(str(self.db_path))
            self.conn = kuzu.Connection(self.db)
            
            logger.info(f"Database initialized at {self.db_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def connect(self) -> bool:
        """
        Connect to the database.
        
        Returns:
            bool: True if connection successful, False otherwise.
        """
        try:
            if self.db is None:
                self.db = kuzu.Database(str(self.db_path))
            
            if self.conn is None:
                self.conn = kuzu.Connection(self.db)
                
            logger.debug("Database connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def disconnect(self) -> None:
        """Close database connection."""
        try:
            if self.conn:
                self.conn.close()
                self.conn = None
            
            if self.db:
                self.db.close()
                self.db = None
                
            logger.debug("Database connection closed")
            
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")
    
    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> Optional[List[Dict[str, Any]]]:
        """
        Execute a Cypher query against the database.
        
        Args:
            query: Cypher query string
            parameters: Query parameters (optional)
            
        Returns:
            Query results as list of dictionaries, or None if error
        """
        if not self.conn:
            if not self.connect():
                return None
        
        try:
            # Execute query with parameters if provided
            if parameters:
                result = self.conn.execute(query, parameters)
            else:
                result = self.conn.execute(query)
            
            # Convert result to list of dictionaries
            records = []
            
            # Get column names from the query result
            columns = []
            if hasattr(result, 'get_column_names'):
                columns = result.get_column_names()
            else:
                # Parse column names from the RETURN clause as fallback
                import re
                return_match = re.search(r'RETURN\s+(.+?)(?:\s+LIMIT|\s+ORDER\s+BY|$)', query, re.IGNORECASE)
                if return_match:
                    return_clause = return_match.group(1)
                    # Extract column names/aliases
                    columns = [col.strip().split(' AS ')[-1].strip() for col in return_clause.split(',')]
            
            while result.has_next():
                record = result.get_next()
                if isinstance(record, list) and columns:
                    # Convert list to dictionary using column names
                    record_dict = {columns[i]: record[i] for i in range(min(len(columns), len(record)))}
                    records.append(record_dict)
                elif isinstance(record, dict):
                    records.append(record)
                else:
                    # Fallback: return as is if we can't determine structure
                    records.append(record)
            
            return records
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Query: {query}")
            if parameters:
                logger.debug(f"Parameters: {parameters}")
            return None
    
    def execute_batch(self, queries: List[str]) -> bool:
        """
        Execute multiple queries in a transaction.
        
        Args:
            queries: List of Cypher query strings
            
        Returns:
            bool: True if all queries successful, False otherwise
        """
        if not self.conn:
            if not self.connect():
                return False
        
        try:
            # Execute queries sequentially (Kuzu handles transactions internally)
            for query in queries:
                result = self.conn.execute(query)
            
            logger.debug(f"Executed batch of {len(queries)} queries")
            return True
            
        except Exception as e:
            logger.error(f"Batch execution failed: {e}")
            return False
    
    def clear_graph(self) -> bool:
        """
        Clear all data from the graph database.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get all node tables
            node_tables_result = self.execute_query("CALL show_tables() RETURN *")
            if node_tables_result:
                for table in node_tables_result:
                    # Handle both list and dict formats
                    if isinstance(table, list) and len(table) >= 2:
                        table_name = table[0]
                        table_type = table[1]
                    elif isinstance(table, dict):
                        table_name = table.get('name', '')
                        table_type = table.get('type', '')
                    else:
                        continue
                    
                    if table_name and table_type == 'NODE':
                        self.execute_query(f"MATCH (n:{table_name}) DETACH DELETE n")
            
            logger.info("Graph database cleared")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear graph: {e}")
            return False
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get database statistics.
        
        Returns:
            Dictionary with node and relationship counts
        """
        stats = {"nodes": 0, "relationships": 0, "tables": 0}
        
        try:
            # Get table information
            tables_result = self.execute_query("CALL show_tables() RETURN *")
            if tables_result:
                stats["tables"] = len(tables_result)
                
                for table in tables_result:
                    table_name = table.get('name', '')
                    table_type = table.get('type', '')
                    
                    if table_type == 'NODE' and table_name:
                        count_result = self.execute_query(f"MATCH (n:{table_name}) RETURN COUNT(n) AS count")
                        if count_result and len(count_result) > 0:
                            stats["nodes"] += count_result[0].get('count', 0)
                    
                    elif table_type == 'REL' and table_name:
                        count_result = self.execute_query(f"MATCH ()-[r:{table_name}]->() RETURN COUNT(r) AS count")
                        if count_result and len(count_result) > 0:
                            stats["relationships"] += count_result[0].get('count', 0)
            
        except Exception as e:
            logger.error(f"Failed to get database stats: {e}")
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform database health check.
        
        Returns:
            Dictionary with health status information
        """
        health = {
            "status": "unknown",
            "db_path": str(self.db_path),
            "db_exists": self.db_path.exists(),
            "connected": False,
            "stats": {}
        }
        
        try:
            if self.connect():
                health["connected"] = True
                health["stats"] = self.get_stats()
                health["status"] = "healthy"
            else:
                health["status"] = "connection_failed"
                
        except Exception as e:
            health["status"] = "error"
            health["error"] = str(e)
            
        return health


# Global database service instance
_db_service: Optional[DatabaseService] = None


def get_database_service(db_path: str = None) -> DatabaseService:
    """
    Get or create the global database service instance.
    
    Args:
        db_path: Database path (only used on first call)
        
    Returns:
        DatabaseService instance
    """
    global _db_service
    
    if _db_service is None:
        _db_service = DatabaseService(db_path)
    
    return _db_service