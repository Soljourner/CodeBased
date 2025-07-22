# CodeBased Example Queries

This document contains a comprehensive library of Cypher queries for analyzing codebases with CodeBased. These queries are particularly useful for AI agents and developers who need to understand code relationships and dependencies.

## Table of Contents

1. [Basic Queries](#basic-queries)
2. [Function Analysis](#function-analysis)
3. [Class Analysis](#class-analysis)
4. [Dependency Analysis](#dependency-analysis)
5. [Impact Analysis](#impact-analysis)
6. [Code Quality Queries](#code-quality-queries)
7. [Architecture Analysis](#architecture-analysis)
8. [Refactoring Queries](#refactoring-queries)

## Basic Queries

### Find All Files

```cypher
MATCH (f:File)
RETURN f.name, f.path, f.lines_of_code
ORDER BY f.lines_of_code DESC
```

**Use Case**: Get an overview of all files in the codebase, sorted by size.

### Count Entities by Type

```cypher
MATCH (n)
RETURN labels(n)[0] AS entity_type, COUNT(n) AS count
ORDER BY count DESC
```

**Use Case**: Understand the composition of your codebase.

### Files with Most Entities

```cypher
MATCH (f:File)-[:CONTAINS]->(entity)
RETURN f.name, f.path, COUNT(entity) AS entity_count
ORDER BY entity_count DESC
LIMIT 10
```

**Use Case**: Find the most complex files that might need refactoring.

## Function Analysis

### Find All Callers of a Function

```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function {name: $function_name})
RETURN DISTINCT caller.name AS caller_name, 
       caller.file_path AS caller_file,
       caller.line_start AS caller_line
ORDER BY caller_file, caller_line
```

**Parameters**: `function_name` (string)
**Use Case**: Find all places where a specific function is called.

### Find Functions Never Called

```cypher
MATCH (f:Function)
WHERE NOT ()-[:CALLS]->(f) 
  AND f.name <> '__init__'
  AND f.name <> '__main__'
  AND NOT f.name STARTS WITH 'test_'
RETURN f.name, f.file_path, f.line_start
ORDER BY f.file_path, f.line_start
```

**Use Case**: Identify potentially unused functions (dead code).

### Find Most Called Functions

```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function)
RETURN target.name AS function_name,
       target.file_path AS file_path,
       COUNT(caller) AS call_count
ORDER BY call_count DESC
LIMIT 20
```

**Use Case**: Identify the most critical functions in your codebase.

### Find Functions with High Complexity

```cypher
MATCH (f:Function)
WHERE f.complexity > $min_complexity
RETURN f.name, f.file_path, f.complexity, f.line_start
ORDER BY f.complexity DESC
```

**Parameters**: `min_complexity` (integer, default: 10)
**Use Case**: Find functions that might need refactoring due to high complexity.

### Find Recursive Functions

```cypher
MATCH (f:Function)-[:CALLS]->(f)
RETURN f.name, f.file_path, f.line_start
```

**Use Case**: Identify recursive function calls.

### Find Long Functions

```cypher
MATCH (f:Function)
WHERE (f.line_end - f.line_start) > $min_lines
RETURN f.name, f.file_path, 
       (f.line_end - f.line_start + 1) AS line_count
ORDER BY line_count DESC
```

**Parameters**: `min_lines` (integer, default: 50)
**Use Case**: Find functions that might be too long and need breaking down.

## Class Analysis

### Find Class Inheritance Hierarchy

```cypher
MATCH path = (child:Class)-[:INHERITS*]->(parent:Class {name: $class_name})
RETURN path
```

**Parameters**: `class_name` (string)
**Use Case**: Understand inheritance relationships for a specific class.

### Find All Subclasses

```cypher
MATCH (parent:Class {name: $class_name})<-[:INHERITS*]-(child:Class)
RETURN DISTINCT child.name AS subclass_name, child.file_path
ORDER BY subclass_name
```

**Parameters**: `class_name` (string)
**Use Case**: Find all classes that inherit from a given class.

### Find Classes with No Subclasses

```cypher
MATCH (c:Class)
WHERE NOT (c)<-[:INHERITS]-()
RETURN c.name, c.file_path
ORDER BY c.name
```

**Use Case**: Identify leaf classes in the inheritance hierarchy.

### Find Classes with Many Methods

```cypher
MATCH (c:Class)-[:CONTAINS]->(m:Function)
RETURN c.name AS class_name, c.file_path, COUNT(m) AS method_count
ORDER BY method_count DESC
LIMIT 10
```

**Use Case**: Find classes that might be doing too much (violating Single Responsibility Principle).

### Find Abstract Classes

```cypher
MATCH (c:Class)
WHERE c.is_abstract = true
RETURN c.name, c.file_path, c.docstring
ORDER BY c.name
```

**Use Case**: Find all abstract classes and interfaces.

## Dependency Analysis

### Find File Dependencies

```cypher
MATCH (source:File {name: $file_name})-[:CONTAINS]->(:Import)-[:IMPORTS]->(target:File)
RETURN DISTINCT target.name AS dependency, target.path
ORDER BY dependency
```

**Parameters**: `file_name` (string)
**Use Case**: Find all files that a specific file depends on.

### Find Files That Depend On a Specific File

```cypher
MATCH (dependent:File)-[:CONTAINS]->(:Import)-[:IMPORTS]->(target:File {name: $file_name})
RETURN DISTINCT dependent.name AS dependent_file, dependent.path
ORDER BY dependent_file
```

**Parameters**: `file_name` (string)
**Use Case**: Find all files that depend on a specific file.

### Detect Circular Dependencies

```cypher
MATCH path = (f1:File)-[:IMPORTS*2..10]->(f1)
WHERE length(path) > 2
RETURN path
LIMIT 10
```

**Use Case**: Find circular import dependencies that could cause issues.

### Find Most Imported Modules

```cypher
MATCH (file:File)-[:CONTAINS]->(import:Import)-[:IMPORTS]->(target)
RETURN target.module_name AS module, COUNT(DISTINCT file) AS import_count
ORDER BY import_count DESC
LIMIT 20
```

**Use Case**: Identify the most commonly used external libraries.

### Find External Dependencies

```cypher
MATCH (import:Import)
WHERE NOT EXISTS((import)-[:IMPORTS]->(:File))
RETURN DISTINCT import.module_name AS external_module, 
       COUNT(*) AS usage_count
ORDER BY usage_count DESC
```

**Use Case**: List all external dependencies and their usage frequency.

## Impact Analysis

### Find All Code Affected by Changing a Function

```cypher
MATCH path = (target:Function {name: $function_name})<-[:CALLS*1..3]-(affected)
RETURN DISTINCT affected.name AS affected_entity,
       labels(affected)[0] AS entity_type,
       affected.file_path AS file_path,
       length(path) AS distance
ORDER BY distance, file_path, affected_entity
```

**Parameters**: `function_name` (string)
**Use Case**: Understand the impact of changing or removing a function.

### Find All Code That Uses a Class

```cypher
MATCH (target:Class {name: $class_name})<-[:USES]-(user)
RETURN DISTINCT user.name AS user_name,
       labels(user)[0] AS user_type,
       user.file_path AS file_path
ORDER BY file_path, user_name
```

**Parameters**: `class_name` (string)
**Use Case**: Find all code that would be affected by changing a class.

### Find Dependency Chain

```cypher
MATCH path = (start:Function {name: $start_function})-[:CALLS*1..5]->(end:Function {name: $end_function})
RETURN path
ORDER BY length(path)
LIMIT 5
```

**Parameters**: `start_function` (string), `end_function` (string)
**Use Case**: Find how two functions are connected through call chains.

### Find Code Reachable from Entry Point

```cypher
MATCH path = (entry:Function {name: $entry_point})-[:CALLS*]->(reachable:Function)
RETURN DISTINCT reachable.name AS reachable_function,
       reachable.file_path AS file_path,
       MIN(length(path)) AS min_distance
ORDER BY min_distance, file_path, reachable_function
```

**Parameters**: `entry_point` (string, e.g., "main")
**Use Case**: Find all code reachable from a main entry point.

## Query Templates for AI Agents

### Template: Analyze Function

```cypher
MATCH (f:Function {name: $function_name})
OPTIONAL MATCH (f)<-[:CALLS]-(caller:Function)
OPTIONAL MATCH (f)-[:CALLS]->(called:Function)
OPTIONAL MATCH (f)<-[:CONTAINS]-(containing_class:Class)
RETURN f AS function_details,
       COLLECT(DISTINCT caller.name) AS callers,
       COLLECT(DISTINCT called.name) AS calls,
       containing_class.name AS class_name
```

### Template: Analyze Class

```cypher
MATCH (c:Class {name: $class_name})
OPTIONAL MATCH (c)-[:CONTAINS]->(method:Function)
OPTIONAL MATCH (c)-[:INHERITS]->(parent:Class)
OPTIONAL MATCH (child:Class)-[:INHERITS]->(c)
RETURN c AS class_details,
       COLLECT(DISTINCT method.name) AS methods,
       parent.name AS parent_class,
       COLLECT(DISTINCT child.name) AS child_classes
```

### Template: Analyze File

```cypher
MATCH (f:File {name: $file_name})
OPTIONAL MATCH (f)-[:CONTAINS]->(entity)
OPTIONAL MATCH (f)-[:CONTAINS]->(:Import)-[:IMPORTS]->(dep:File)
RETURN f AS file_details,
       COLLECT(DISTINCT labels(entity)[0]) AS entity_types,
       COLLECT(DISTINCT dep.name) AS dependencies
```

These queries provide a comprehensive toolkit for analyzing codebases with CodeBased. They can be executed through the web interface, CLI, or API endpoints.