# CodeBased - Improvement Strategy

## **Core Concepts & Data Structures**

Before diving into the algorithms, let's define the fundamental building blocks of our system.

- **Graph:** A collection of Nodes and Edges.
- **Node:** Represents an entity in the codebase. Every node must have:
  - `id`: A unique, deterministic identifier. This is crucial for connecting edges correctly.
  - `type`: The kind of entity (e.g., `FOLDER`, `FILE`, `CLASS`, `FUNCTION`).
  - `name`: The human-readable name (e.g., `MyClass`, `myMethod`).
  - `metadata`: A dictionary of properties, including:
    - `path`: The full URI to the file containing the node.
    - `start_line`, `end_line`: The line numbers defining the node's scope in the source file.
    - `code_text`: The raw source code of the node.
- **Edge:** Represents a relationship between two Nodes. Every edge must have:
  - `source_id`: The `id` of the starting node.
  - `target_id`: The `id` of the ending node.
  - `type`: The kind of relationship (e.g., `CONTAINS`, `DEFINES`, `CALLS`, `IMPORTS`, `INSTANTIATES`).
  - `metadata`: Optional properties, like the source code snippet that defines the relationship.

## Updated Implementation Recommendations

Here's a streamlined approach:

## Key Design Decisions

1. **AI-Optimized Output**:

   - Includes code snippets in node metadata for context
   - Provides both Kuzu Cypher format and JSON format
   - Summary statistics for quick AI comprehension
   - Clear, hierarchical relationship structure

2. **Simplified Template Handling**: As you requested, templates and CSS files are just treated as file entities with relationships to components, without deep parsing.

3. **External Package Handling**:

   - Creates special "EXTERNAL_PACKAGE" nodes for npm packages
   - Tracks imports but doesn't traverse into node_modules
   - Maintains the import relationships for AI understanding

4. **Monorepo Support**: Automatic detection for Nx, Lerna, and Yarn/NPM workspaces with balanced cross-package dependency tracking.

## Architecture Highlights

The solution follows a clean 4-phase approach:

1. **Hierarchy Building**: Fast directory traversal
2. **Code Parsing**: Parallel processing with tree-sitter
3. **Relationship Detection**: Static analysis without LSP
4. **Export**: Dual format (Kuzu + JSON) for flexibility

## Benefits for AI Agents

- **Fast Updates**: Incremental parsing means AI can quickly refresh after making changes
- **Clear Context**: Code snippets and relationships help AI understand dependencies
- **Lightweight**: No background processes or servers needed
- **Deterministic IDs**: Ensures consistent references across updates

## Implementation Priority

1. Start with the TypeScript/JavaScript parser (core functionality)
2. Add Angular decorator detection
3. Implement basic relationship detection (imports/exports)
4. Add monorepo support
5. Optimize the AI-friendly output format

This approach gives you a working MVP quickly while maintaining the flexibility to add deeper analysis later. The simplified architecture also makes it easier to maintain and extend as you discover what information is most valuable for AI agents.

Would you like me to elaborate on any specific part of the implementation or create more detailed code for a particular algorithm?
