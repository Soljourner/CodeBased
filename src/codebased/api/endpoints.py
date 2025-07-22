"""
API endpoints for CodeBased.
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Body
from pydantic import BaseModel, Field

from ..config import CodeBasedConfig
from ..database.service import DatabaseService
from ..parsers.incremental import IncrementalUpdater
from .models import *

logger = logging.getLogger(__name__)


def create_router(config: CodeBasedConfig, db_service: DatabaseService) -> APIRouter:
    """
    Create API router with all endpoints.
    
    Args:
        config: CodeBased configuration
        db_service: Database service instance
        
    Returns:
        Configured API router
    """
    router = APIRouter()
    updater = IncrementalUpdater(config, db_service)
    
    @router.post("/query", response_model=QueryResponse)
    async def execute_query(request: QueryRequest) -> QueryResponse:
        """
        Execute Cypher query against the graph database.
        
        Args:
            request: Query request with Cypher query
            
        Returns:
            Query results
        """
        start_time = time.time()
        
        try:
            # Validate query (basic security check)
            if not request.query.strip():
                raise HTTPException(status_code=400, detail="Empty query")
            
            # Prevent dangerous operations
            dangerous_keywords = ['DELETE', 'DROP', 'CREATE', 'SET', 'MERGE', 'REMOVE']
            query_upper = request.query.upper()
            if any(keyword in query_upper for keyword in dangerous_keywords):
                raise HTTPException(status_code=403, detail="Write operations not allowed")
            
            # Execute query with timeout
            result = db_service.execute_query(request.query, request.parameters)
            
            if result is None:
                raise HTTPException(status_code=500, detail="Query execution failed")
            
            execution_time = time.time() - start_time
            
            return QueryResponse(
                data=result,
                execution_time=execution_time,
                record_count=len(result)
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.post("/update", response_model=UpdateResponse)
    async def update_graph(request: UpdateRequest = None) -> UpdateResponse:
        """
        Update the code graph (incremental or full).
        
        Args:
            request: Update request parameters
            
        Returns:
            Update results
        """
        try:
            if request and request.force_full:
                logger.info("Starting full graph update")
                results = updater.force_full_update(request.directory_path)
            else:
                logger.info("Starting incremental graph update")
                results = updater.update_graph(request.directory_path if request else None)
            
            return UpdateResponse(
                success=not results.get('errors'),
                message="Update completed successfully" if not results.get('errors') else "Update completed with errors",
                statistics=UpdateStatistics(**results),
                errors=results.get('errors', [])
            )
            
        except Exception as e:
            logger.error(f"Update error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/graph", response_model=GraphResponse)
    async def get_graph_data(
        node_types: Optional[str] = Query(None, description="Comma-separated node types to include"),
        max_nodes: Optional[int] = Query(config.web.max_nodes, description="Maximum nodes to return"),
        max_edges: Optional[int] = Query(config.web.max_edges, description="Maximum edges to return"),
        file_filter: Optional[str] = Query(None, description="File path filter pattern")
    ) -> GraphResponse:
        """
        Get graph data for visualization.
        
        Args:
            node_types: Comma-separated list of node types to include
            max_nodes: Maximum number of nodes to return
            max_edges: Maximum number of edges to return
            file_filter: File path filter pattern
            
        Returns:
            Graph data with nodes and edges
        """
        try:
            # Build query based on filters
            where_clauses = []
            
            if node_types:
                type_list = [t.strip() for t in node_types.split(',')]
                # Using Kuzu syntax - match by node table type
                type_conditions = [f"n:{t}" for t in type_list]
                where_clauses.append(f"({' OR '.join(type_conditions)})")
            
            if file_filter:
                where_clauses.append(f"n.file_path CONTAINS '{file_filter}'")
            
            where_clause = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
            
            # Get nodes from each table type separately (Kuzu doesn't have labels() function)
            node_tables = ['File', 'Module', 'Class', 'Function', 'Variable', 'Import']
            nodes_result = []
            
            for table_type in node_tables:
                if node_types and table_type not in [t.strip() for t in node_types.split(',')]:
                    continue
                    
                # Build where clause for this table type
                table_where_clauses = []
                
                # Temporarily comment out .codebased filter for testing
                # if table_type == 'File':
                #     table_where_clauses.append("NOT n.path CONTAINS '.codebased'")
                # else:
                #     table_where_clauses.append("NOT n.file_id CONTAINS '.codebased'")
                
                if file_filter:
                    if table_type == 'File':
                        table_where_clauses.append(f"n.path CONTAINS '{file_filter}'")
                    else:
                        table_where_clauses.append(f"n.file_id CONTAINS '{file_filter}'")
                        
                table_where = f"WHERE {' AND '.join(table_where_clauses)}" if table_where_clauses else ""
                
                # Build query with only properties that exist for this table type
                if table_type == 'File':
                    table_query = f"""
                    MATCH (n:{table_type})
                    {table_where}
                    RETURN n.id AS id, n.name AS name, '{table_type}' AS type, n.path AS file_path, 1 AS line_start, 1 AS line_end
                    LIMIT {max_nodes // len(node_tables) + 1}
                    """
                elif table_type in ['Variable', 'Import']:
                    # Variable and Import tables use line_number instead of line_start/line_end
                    table_query = f"""
                    MATCH (n:{table_type})
                    {table_where}
                    RETURN n.id AS id, n.name AS name, '{table_type}' AS type, n.file_id AS file_path, n.line_number AS line_start, n.line_number AS line_end
                    LIMIT {max_nodes // len(node_tables) + 1}
                    """
                else:
                    table_query = f"""
                    MATCH (n:{table_type})
                    {table_where}
                    RETURN n.id AS id, n.name AS name, '{table_type}' AS type, n.file_id AS file_path, n.line_start AS line_start, n.line_end AS line_end
                    LIMIT {max_nodes // len(node_tables) + 1}
                    """
                
                table_result = db_service.execute_query(table_query)
                if table_result:
                    nodes_result.extend(table_result)
                else:
                    logger.debug(f"No results from {table_type} query")
            
            if not nodes_result:
                raise HTTPException(status_code=500, detail="Failed to fetch nodes")
            
            nodes = []
            node_ids = set()
            
            for row in nodes_result:
                # Handle list format from Kuzu
                if isinstance(row, list) and len(row) >= 6:
                    node_id = row[0]
                    node_name = row[1]
                    node_type = row[2]
                    file_path = row[3]
                    line_start = row[4] if row[4] and row[4] != 1 else None
                    line_end = row[5] if row[5] and row[5] != 1 else None
                elif isinstance(row, dict):
                    node_id = row['id']
                    node_name = row['name']
                    node_type = row['type']
                    file_path = row.get('file_path')
                    line_start = row.get('line_start')
                    line_end = row.get('line_end')
                else:
                    continue
                    
                node_ids.add(node_id)
                
                nodes.append(GraphNode(
                    id=node_id,
                    name=node_name,
                    type=node_type,
                    file_path=file_path,
                    line_start=line_start,
                    line_end=line_end,
                    metadata={}
                ))
            
            # Get edges between the selected nodes
            if node_ids:
                node_ids_str = "', '".join(node_ids)
                # Try different relationship table types
                edge_tables = [
                    'FILE_CONTAINS_MODULE', 'FILE_CONTAINS_CLASS', 'FILE_CONTAINS_FUNCTION', 
                    'FILE_CONTAINS_VARIABLE', 'FILE_CONTAINS_IMPORT',
                    'MODULE_CONTAINS_CLASS', 'MODULE_CONTAINS_FUNCTION', 'MODULE_CONTAINS_VARIABLE',
                    'CLASS_CONTAINS_FUNCTION', 'CLASS_CONTAINS_VARIABLE',
                    'CALLS', 'INHERITS', 'IMPORTS', 'USES', 'DECORATES'
                ]
                edges_result = []
                
                for rel_type in edge_tables:
                    rel_query = f"""
                    MATCH (n1)-[r:{rel_type}]->(n2)
                    WHERE n1.id IN ['{node_ids_str}'] AND n2.id IN ['{node_ids_str}']
                    RETURN n1.id AS source, n2.id AS target, '{rel_type}' AS relationship_type
                    LIMIT {max_edges // len(edge_tables) + 1}
                    """
                    
                    rel_result = db_service.execute_query(rel_query)
                    if rel_result:
                        edges_result.extend(rel_result)
                
                # edges_result is already populated above
                
                edges = []
                for row in edges_result:
                    if isinstance(row, list) and len(row) >= 3:
                        edges.append(GraphEdge(
                            source=row[0],
                            target=row[1], 
                            relationship_type=row[2] or 'RELATED',
                            metadata={}
                        ))
                    elif isinstance(row, dict):
                        edges.append(GraphEdge(
                            source=row['source'],
                            target=row['target'],
                            relationship_type=row['relationship_type'],
                            metadata=dict(row.get('r', {}))
                        ))
            else:
                edges = []
            
            return GraphResponse(
                nodes=nodes,
                edges=edges,
                metadata=GraphMetadata(
                    total_nodes=len(nodes),
                    total_edges=len(edges),
                    node_types=list(set(node.type for node in nodes)),
                    filters={
                        'node_types': node_types,
                        'file_filter': file_filter,
                        'max_nodes': max_nodes,
                        'max_edges': max_edges
                    }
                )
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Graph data error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/tree", response_model=TreeResponse)
    async def get_project_tree(
        path: Optional[str] = Query(".", description="Root path to generate tree for")
    ) -> TreeResponse:
        """
        Get project directory tree structure.
        
        Args:
            path: Root path relative to project root
            
        Returns:
            Directory tree structure
        """
        try:
            root_path = Path(config.project_root) / path
            
            if not root_path.exists():
                raise HTTPException(status_code=404, detail="Path not found")
            
            def build_tree_node(path: Path) -> TreeNode:
                """Recursively build tree structure."""
                node = TreeNode(
                    name=path.name if path.name else str(path),
                    path=str(path.relative_to(Path(config.project_root))),
                    type="directory" if path.is_dir() else "file",
                    children=[]
                )
                
                if path.is_dir():
                    try:
                        # Filter out excluded directories and files
                        exclude_patterns = config.parsing.exclude_patterns
                        children = []
                        
                        for child in sorted(path.iterdir()):
                            # Skip excluded items
                            should_skip = False
                            for pattern in exclude_patterns:
                                if child.name == pattern or child.match(pattern):
                                    should_skip = True
                                    break
                            
                            if not should_skip:
                                children.append(build_tree_node(child))
                        
                        node.children = children
                    except PermissionError:
                        pass  # Skip directories we can't read
                else:
                    # Add file metadata
                    try:
                        stat = path.stat()
                        node.size = stat.st_size
                        node.modified_time = stat.st_mtime
                    except:
                        pass
                
                return node
            
            tree = build_tree_node(root_path)
            
            return TreeResponse(
                tree=tree,
                root_path=str(root_path.relative_to(Path(config.project_root)))
            )
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Tree generation error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @router.get("/templates", response_model=TemplatesResponse)
    async def get_query_templates() -> TemplatesResponse:
        """
        Get pre-built query templates.
        
        Returns:
            Available query templates
        """
        templates = [
            QueryTemplate(
                id="find_callers",
                name="Find Function Callers",
                description="Find all functions that call a specific function",
                query="MATCH (caller:Function)-[:CALLS]->(target:Function {name: $function_name}) RETURN caller.name, caller.file_path, caller.line_start",
                parameters=["function_name"],
                example_params={"function_name": "example_function"}
            ),
            QueryTemplate(
                id="class_hierarchy",
                name="Class Inheritance Hierarchy",
                description="Get the inheritance hierarchy for a class",
                query="MATCH path = (child:Class)-[:INHERITS*]->(parent:Class {name: $class_name}) RETURN path",
                parameters=["class_name"],
                example_params={"class_name": "BaseClass"}
            ),
            QueryTemplate(
                id="file_dependencies",
                name="File Dependencies",
                description="Find all files that a specific file depends on",
                query="MATCH (file:File {name: $file_name})-[:CONTAINS]->(:Import)-[:IMPORTS]->(dep:File) RETURN DISTINCT dep.path, dep.name",
                parameters=["file_name"],
                example_params={"file_name": "main.py"}
            ),
            QueryTemplate(
                id="circular_dependencies",
                name="Circular Dependencies",
                description="Detect circular import dependencies",
                query="MATCH path = (f1:File)-[:IMPORTS*2..]->(f1) WHERE length(path) > 2 RETURN path LIMIT 10",
                parameters=[],
                example_params={}
            ),
            QueryTemplate(
                id="unused_functions",
                name="Potentially Unused Functions",
                description="Find functions that are not called by other functions",
                query="MATCH (f:Function) WHERE NOT ()-[:CALLS]->(f) AND f.name <> '__init__' RETURN f.name, f.file_path, f.line_start",
                parameters=[],
                example_params={}
            ),
            QueryTemplate(
                id="complex_functions",
                name="Complex Functions",
                description="Find functions with high complexity",
                query="MATCH (f:Function) WHERE f.complexity > $min_complexity RETURN f.name, f.file_path, f.complexity ORDER BY f.complexity DESC",
                parameters=["min_complexity"],
                example_params={"min_complexity": 10}
            ),
            QueryTemplate(
                id="impact_analysis",
                name="Impact Analysis",
                description="Find all code that would be affected by changing a function",
                query="MATCH path = (f:Function {name: $function_name})<-[:CALLS*1..3]-(caller) RETURN DISTINCT caller.name, caller.file_path, length(path) AS depth ORDER BY depth",
                parameters=["function_name"],
                example_params={"function_name": "critical_function"}
            )
        ]
        
        return TemplatesResponse(templates=templates)
    
    @router.get("/status", response_model=StatusResponse)
    async def get_system_status() -> StatusResponse:
        """
        Get system status and statistics.
        
        Returns:
            System status information
        """
        try:
            # Get database statistics
            db_stats = db_service.get_stats()
            db_health = db_service.health_check()
            
            # Get update status
            update_status = updater.get_update_status()
            
            return StatusResponse(
                database_stats=db_stats,
                database_health=db_health,
                update_status=update_status,
                configuration={
                    "project_root": config.project_root,
                    "database_path": config.database.path,
                    "api_host": config.api.host,
                    "api_port": config.api.port,
                    "max_nodes": config.web.max_nodes,
                    "max_edges": config.web.max_edges
                }
            )
            
        except Exception as e:
            logger.error(f"Status error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    return router