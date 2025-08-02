# Kuzu Query Guide for CodeBased

This guide explains how to write queries for CodeBased using Kuzu's Cypher dialect.

## 🔑 Important: Kuzu vs Standard Cypher

Kuzu uses a slightly different syntax than standard Neo4j Cypher. Here are the key differences:

### ❌ Common Mistakes & ✅ Correct Syntax

1. **Node Labels**
   ```cypher
   ❌ MATCH (n) WHERE labels(n) = 'Function'
   ✅ MATCH (n:Function)
   ```

2. **Property Access**
   ```cypher
   ❌ MATCH (f:Function) WHERE f.module_path = '/src/main.js'
   ✅ MATCH (f:Function) WHERE f.file_id = '/src/main.js'
   ```

3. **Relationship Types**
   ```cypher
   ❌ MATCH (a)-[r]->(b) RETURN type(r)
   ✅ MATCH (a)-[r:CALLS]->(b) RETURN 'CALLS' as rel_type
   ```

4. **String Operations**
   ```cypher
   ❌ WHERE n.path =~ '.*test.*'
   ✅ WHERE n.path CONTAINS 'test'
   ```

## 📊 Entity Types in CodeBased

### Node Types
- `File` - Source code files
- `Module` - Python modules or JavaScript/TypeScript modules
- `Class` - Class definitions
- `Function` - Function/method definitions
- `Variable` - Variable declarations
- `Import` - Import statements

### Relationship Types
- `FILE_CONTAINS_MODULE`
- `FILE_CONTAINS_CLASS`
- `FILE_CONTAINS_FUNCTION`
- `FILE_CONTAINS_VARIABLE`
- `FILE_CONTAINS_IMPORT`
- `MODULE_CONTAINS_CLASS`
- `MODULE_CONTAINS_FUNCTION`
- `CLASS_CONTAINS_FUNCTION`
- `CONTAINS` - Generic containment relationship
- `CALLS` - Function calls
- `IMPORTS` - Import relationships
- `INHERITS` - Class inheritance
- `USES` - Variable usage

## 🔍 Common Query Patterns

### Find All Files
```cypher
MATCH (f:File) 
RETURN f.path, f.name
```

### Find Specific File
```cypher
MATCH (f:File) 
WHERE f.path CONTAINS 'utils.js'
RETURN f
```

### Find Functions in a File
```cypher
MATCH (f:File)-[:FILE_CONTAINS_FUNCTION]->(func:Function)
WHERE f.name = 'main.py'
RETURN func.name, func.line_start, func.line_end
```

### Find All Functions That Call a Specific Function
```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function)
WHERE target.name = 'processData'
RETURN caller.name, caller.file_id
```

### Find Class Hierarchy
```cypher
MATCH path = (child:Class)-[:INHERITS*]->(parent:Class)
WHERE parent.name = 'BaseClass'
RETURN path
```

### Find Unused Functions
```cypher
MATCH (f:Function)
WHERE NOT exists((other)-[:CALLS]->(f))
  AND f.name <> '__init__'
  AND f.name <> 'main'
RETURN f.name, f.file_id
```

### Find Imports
```cypher
MATCH (f:File)-[:FILE_CONTAINS_IMPORT]->(i:Import)
WHERE f.path CONTAINS 'src/'
RETURN i.name, i.line_number
```

### Count Entities by Type
```cypher
MATCH (f:File)-[:FILE_CONTAINS_FUNCTION]->(func:Function)
RETURN f.path, count(func) as function_count
ORDER BY function_count DESC
```

## 🚨 Debugging Query Issues

### 1. Check if Table Exists
If you get "Table X does not exist" errors:
```cypher
-- List all tables (run via CLI)
codebased query "CALL kuzu.schema.info() RETURN *"
```

### 2. Check Property Names
Properties differ by entity type:
- `File`: `path`, `name`, `extension`, `size`
- `Function`: `name`, `file_path`, `line_start`, `line_end`
- `Class`: `name`, `file_path`, `line_start`, `line_end`
- `Import`: `name`, `line_start`, `file_path`
- All entities have: `file_path` (NOT `file_id`)

### 3. Debug Empty Results
```cypher
-- Check if any nodes exist
MATCH (n:Function) RETURN count(n)

-- Check relationships
MATCH ()-[r:CALLS]->() RETURN count(r)
```

### 4. Case Sensitivity
Kuzu is case-sensitive for:
- Node labels: `Function` ≠ `function`
- Relationship types: `CALLS` ≠ `calls`
- Property names: `file_id` ≠ `file_ID`

## 📝 Query Tips

1. **Use LIMIT for exploration**
   ```cypher
   MATCH (n:Function) RETURN n LIMIT 10
   ```

2. **Filter early for performance**
   ```cypher
   -- Good: Filter in MATCH
   MATCH (f:Function {name: 'main'})
   
   -- Less efficient: Filter in WHERE
   MATCH (f:Function) WHERE f.name = 'main'
   ```

3. **Use DISTINCT to avoid duplicates**
   ```cypher
   MATCH (f:File)-[:IMPORTS]->(other:File)
   RETURN DISTINCT other.path
   ```

4. **Check relationships exist before traversing**
   ```cypher
   MATCH (f:Function)
   WHERE exists((f)-[:CALLS]->())
   RETURN f.name
   ```

## 🔧 Advanced Queries

### Find Circular Dependencies
```cypher
MATCH path = (f1:File)-[:IMPORTS*2..]->(f1)
WHERE length(path) > 2
RETURN path LIMIT 10
```

### Analyze Function Complexity
```cypher
MATCH (f:Function)
OPTIONAL MATCH (f)-[:CALLS]->(called:Function)
RETURN f.name, f.file_id, count(called) as calls_count
ORDER BY calls_count DESC
```

### Find Most Connected Nodes
```cypher
MATCH (n)
WITH n, count{(n)-[]->()} + count{()-[]->(n)} as degree
ORDER BY degree DESC
LIMIT 10
RETURN n.name, degree
```

## 🐛 Common Error Messages

### "Binder exception: Table X does not exist"
- The entity type doesn't exist in the database
- Check spelling and capitalization

### "Cannot find property X for n"
- The property doesn't exist on that entity type
- Use the correct property names listed above

### "Parser exception: Invalid input"
- Syntax error in the query
- Check for missing quotes, parentheses, or typos

### "Query execution failed"
- Often means empty results or type mismatch
- Try simpler queries to debug

## 📚 Resources

- [Kuzu Documentation](https://kuzudb.com/docs/)
- [Cypher Query Language](https://neo4j.com/developer/cypher/)
- Run `codebased query --help` for CLI options