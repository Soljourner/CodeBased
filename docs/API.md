# CodeBased API Documentation

This document describes the REST API endpoints provided by CodeBased.

## Base URL

Default: `http://localhost:8000/api`

## Authentication

CodeBased does not require authentication for local development. All endpoints are publicly accessible.

## Endpoints

### Graph Data

#### GET /api/graph

Get graph visualization data with optional filters.

**Parameters:**
- `node_types` (string, optional): Comma-separated node types to include
- `max_nodes` (integer, optional): Maximum nodes to return (default: 5000)
- `max_edges` (integer, optional): Maximum edges to return (default: 10000)
- `file_filter` (string, optional): File path filter pattern

**Response:**
```json
{
  "nodes": [
    {
      "id": "file_main.py_func_hello",
      "name": "hello",
      "type": "Function",
      "file_path": "main.py",
      "line_start": 5,
      "line_end": 8,
      "metadata": {}
    }
  ],
  "edges": [
    {
      "source": "file_main.py_func_main",
      "target": "file_main.py_func_hello",
      "relationship_type": "CALLS",
      "metadata": {}
    }
  ],
  "metadata": {
    "total_nodes": 150,
    "total_edges": 200,
    "node_types": ["File", "Function", "Class"],
    "filters": {}
  }
}
```

### Query Execution

#### POST /api/query

Execute Cypher queries against the graph database.

**Request Body:**
```json
{
  "query": "MATCH (n:Function) RETURN n.name LIMIT 10",
  "parameters": {}
}
```

**Response:**
```json
{
  "data": [
    {"n.name": "main"},
    {"n.name": "hello"},
    {"n.name": "process"}
  ],
  "execution_time": 0.05,
  "record_count": 3
}
```

**Security Notes:**
- Only read operations (MATCH, RETURN) are allowed
- Write operations (CREATE, DELETE, SET) are blocked
- Queries have a 30-second timeout limit

### Graph Updates

#### POST /api/update

Trigger graph update (incremental or full).

**Request Body (optional):**
```json
{
  "force_full": false,
  "directory_path": null
}
```

**Response:**
```json
{
  "success": true,
  "message": "Update completed successfully",
  "statistics": {
    "files_processed": 25,
    "nodes_created": 150,
    "edges_created": 200,
    "files_changed": 3,
    "execution_time": 2.5
  },
  "errors": []
}
```

### Query Templates

#### GET /api/templates

Get pre-built query templates for common analysis tasks.

**Response:**
```json
{
  "templates": [
    {
      "id": "find_callers",
      "name": "Find Function Callers",
      "description": "Find all functions that call a specific function",
      "query": "MATCH (caller:Function)-[:CALLS]->(target:Function {name: $function_name}) RETURN caller.name, caller.file_path",
      "parameters": ["function_name"],
      "example_params": {"function_name": "example_function"}
    }
  ]
}
```

### System Status

#### GET /api/status

Get system status and statistics.

**Response:**
```json
{
  "database_stats": {
    "total_nodes": 1500,
    "total_edges": 2000,
    "node_types": {"Function": 800, "Class": 200, "File": 50},
    "database_size_mb": 5.2
  },
  "database_health": {
    "status": "healthy",
    "last_update": "2024-01-15T10:30:00Z"
  },
  "update_status": {
    "is_updating": false,
    "last_update_time": "2024-01-15T10:25:00Z",
    "next_scheduled_update": null
  },
  "configuration": {
    "project_root": "/path/to/project",
    "database_path": ".codebased/data/graph.kuzu",
    "max_nodes": 5000,
    "max_edges": 10000
  }
}
```

### Project Tree

#### GET /api/tree

Get project directory structure as a tree.

**Parameters:**
- `path` (string, optional): Root path relative to project root (default: ".")

**Response:**
```json
{
  "tree": {
    "name": "project",
    "path": ".",
    "type": "directory",
    "children": [
      {
        "name": "main.py",
        "path": "main.py",
        "type": "file",
        "size": 1024,
        "modified_time": 1705317000,
        "children": []
      }
    ]
  },
  "root_path": "."
}
```

## Error Responses

All endpoints return standard HTTP status codes:

- `200` - Success
- `400` - Bad Request (invalid parameters)
- `403` - Forbidden (unauthorized operation)
- `404` - Not Found
- `500` - Internal Server Error

Error response format:
```json
{
  "detail": "Error message description"
}
```

## Rate Limiting

CodeBased does not implement rate limiting by default. For production deployments, consider using a reverse proxy with rate limiting.

## OpenAPI Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## Examples

### Python Client Example

```python
import requests
import json

base_url = "http://localhost:8000/api"

# Get graph data
response = requests.get(f"{base_url}/graph", params={
    "node_types": "Function,Class",
    "max_nodes": 1000
})
graph_data = response.json()

# Execute query
query_data = {
    "query": "MATCH (f:Function) WHERE f.complexity > $min_complexity RETURN f.name, f.complexity",
    "parameters": {"min_complexity": 10}
}
response = requests.post(f"{base_url}/query", json=query_data)
results = response.json()

# Trigger update
response = requests.post(f"{base_url}/update", json={"force_full": False})
update_result = response.json()
```

### JavaScript Client Example

```javascript
const API_BASE = 'http://localhost:8000/api';

// Get graph data
async function getGraphData(filters = {}) {
  const params = new URLSearchParams(filters);
  const response = await fetch(`${API_BASE}/graph?${params}`);
  return await response.json();
}

// Execute query
async function executeQuery(query, parameters = {}) {
  const response = await fetch(`${API_BASE}/query`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({query, parameters})
  });
  return await response.json();
}

// Usage
const graphData = await getGraphData({node_types: 'Function,Class'});
const queryResults = await executeQuery(
  'MATCH (f:Function) RETURN f.name LIMIT 10'
);
```