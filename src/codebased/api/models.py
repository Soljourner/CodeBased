"""
Pydantic models for CodeBased API.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


# Request Models

class QueryRequest(BaseModel):
    """Request model for graph queries."""
    query: str = Field(..., description="Cypher query to execute")
    parameters: Optional[Dict[str, Any]] = Field(None, description="Query parameters")


class UpdateRequest(BaseModel):
    """Request model for graph updates."""
    directory_path: Optional[str] = Field(None, description="Directory to update (defaults to project root)")
    force_full: bool = Field(False, description="Force full rebuild instead of incremental")


# Response Models

class QueryResponse(BaseModel):
    """Response model for graph queries."""
    data: List[Dict[str, Any]] = Field(..., description="Query results")
    execution_time: float = Field(..., description="Query execution time in seconds")
    record_count: int = Field(..., description="Number of records returned")


class UpdateStatistics(BaseModel):
    """Statistics from graph update operation."""
    total_files: int = 0
    files_added: int = 0
    files_modified: int = 0
    files_removed: int = 0
    files_unchanged: int = 0
    entities_added: int = 0
    entities_updated: int = 0
    entities_removed: int = 0
    relationships_added: int = 0
    relationships_updated: int = 0
    relationships_removed: int = 0
    update_time: float = 0.0


class UpdateResponse(BaseModel):
    """Response model for graph updates."""
    success: bool = Field(..., description="Whether update was successful")
    message: str = Field(..., description="Update result message")
    statistics: UpdateStatistics = Field(..., description="Update statistics")
    errors: List[str] = Field(default_factory=list, description="Any errors encountered")


# Graph Visualization Models

class GraphNode(BaseModel):
    """Node in the graph visualization."""
    id: str = Field(..., description="Unique node identifier")
    name: str = Field(..., description="Node display name")
    type: str = Field(..., description="Node type (File, Class, Function, etc.)")
    file_path: Optional[str] = Field(None, description="Source file path")
    line_start: Optional[int] = Field(None, description="Starting line number")
    line_end: Optional[int] = Field(None, description="Ending line number")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional node metadata")


class GraphEdge(BaseModel):
    """Edge in the graph visualization."""
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    relationship_type: str = Field(..., description="Type of relationship")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional edge metadata")


class GraphMetadata(BaseModel):
    """Metadata about the graph."""
    total_nodes: int = Field(..., description="Total number of nodes")
    total_edges: int = Field(..., description="Total number of edges")
    node_types: List[str] = Field(..., description="Available node types")
    filters: Dict[str, Any] = Field(..., description="Applied filters")


class GraphResponse(BaseModel):
    """Response model for graph data."""
    nodes: List[GraphNode] = Field(..., description="Graph nodes")
    edges: List[GraphEdge] = Field(..., description="Graph edges")
    metadata: GraphMetadata = Field(..., description="Graph metadata")


# Tree Structure Models

class TreeNode(BaseModel):
    """Node in the project tree structure."""
    name: str = Field(..., description="File or directory name")
    path: str = Field(..., description="Relative path from project root")
    type: str = Field(..., description="Type: 'file' or 'directory'")
    size: Optional[int] = Field(None, description="File size in bytes")
    modified_time: Optional[float] = Field(None, description="Last modified timestamp")
    children: List['TreeNode'] = Field(default_factory=list, description="Child nodes")


TreeNode.model_rebuild()  # Required for self-referencing model


class TreeResponse(BaseModel):
    """Response model for project tree."""
    tree: TreeNode = Field(..., description="Root tree node")
    root_path: str = Field(..., description="Root path used for tree generation")


# Query Template Models

class QueryTemplate(BaseModel):
    """Pre-built query template."""
    id: str = Field(..., description="Unique template identifier")
    name: str = Field(..., description="Template display name")
    description: str = Field(..., description="Template description")
    query: str = Field(..., description="Cypher query template")
    parameters: List[str] = Field(..., description="Required parameter names")
    example_params: Dict[str, Any] = Field(..., description="Example parameter values")


class TemplatesResponse(BaseModel):
    """Response model for query templates."""
    templates: List[QueryTemplate] = Field(..., description="Available query templates")


# Status Models

class StatusResponse(BaseModel):
    """Response model for system status."""
    database_stats: Dict[str, Any] = Field(..., description="Database statistics")
    database_health: Dict[str, Any] = Field(..., description="Database health information")
    update_status: Dict[str, Any] = Field(..., description="Update system status")
    configuration: Dict[str, Any] = Field(..., description="Current configuration")