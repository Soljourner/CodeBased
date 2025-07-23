# CodeBased - Code Graph Visualization Tool

CodeBased is a lightweight, self-contained code graph generator and visualization tool that helps developers and AI agents understand code relationships through knowledge graphs.

## Features

- **Zero External Dependencies**: Embedded Kuzu graph database - no servers required
- **Incremental Updates**: Fast updates using file hashing and differential parsing
- **Interactive Visualization**: D3.js-powered force-directed graph with filtering
- **AI Agent Ready**: Pre-built Cypher queries for common code analysis tasks
- **Multi-Format Export**: JSON, CSV, and visual exports
- **Command Line Interface**: Simple CLI for automation and scripting
- **Performance Optimized**: Handles large codebases with WebGL rendering
- **Dynamic Parsers**: Automatically loads available language parsers

## Quick Start

### Installation

1. **Automated Setup (Recommended)**:
   ```bash
   # Unix/Linux/macOS
   chmod +x setup.sh
   ./setup.sh
   
   # Windows (PowerShell)
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\setup.ps1
   ```

2. **Manual Setup**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # or venv\Scripts\activate on Windows
   pip install -r requirements.txt
   pip install -e .
   # optional: install tree-sitter grammars for JS/TS/HTML/CSS
   pip install tree_sitter tree_sitter_languages
   ```

### Basic Usage

```bash
# Initialize CodeBased in your project
codebased init

# Update the code graph
codebased update

# Start the web interface
codebased serve

# Open http://localhost:8000 in your browser
```

## Architecture

```
CodeBased/
├── src/codebased/          # Core Python package
│   ├── cli/               # Command-line interface
│   ├── api/               # FastAPI REST endpoints
│   ├── database/          # Kuzu database service
│   ├── parsers/           # Python AST parsers
│   └── config.py          # Configuration management
├── web/                   # Frontend application
│   ├── index.html         # Main HTML interface
│   ├── app.js            # Application logic
│   ├── graph.js          # D3.js visualization
│   ├── performance.js    # Performance optimizations
│   └── style.css         # Styling
├── data/                  # Database and cache files
├── examples/              # Query examples and templates
├── tests/                # Test suite
└── docs/                 # Documentation
```

## Configuration

CodeBased uses `.codebased.yml` for configuration:

```yaml
project_root: "."
database:
  path: ".codebased/data/graph.kuzu"
parsing:
  include_patterns: ["**/*.py"]
  exclude_patterns: ["venv/**", "__pycache__/**"]
api:
  host: "localhost"
  port: 8000
web:
  max_nodes: 5000
  max_edges: 10000
```

## API Endpoints

- `GET /api/graph` - Get graph visualization data
- `POST /api/query` - Execute Cypher queries
- `POST /api/update` - Trigger graph update
- `GET /api/templates` - Get query templates
- `GET /api/status` - System status and statistics
- `GET /api/tree` - Project directory structure

## Query Examples

### Find Function Callers
```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function {name: "my_function"})
RETURN caller.name, caller.file_path, caller.line_start
```

### Class Hierarchy
```cypher
MATCH path = (child:Class)-[:INHERITS*]->(parent:Class {name: "BaseClass"})
RETURN path
```

### Impact Analysis
```cypher
MATCH path = (f:Function {name: "critical_function"})<-[:CALLS*1..3]-(caller)
RETURN DISTINCT caller.name, caller.file_path, length(path) AS depth
ORDER BY depth
```

### Circular Dependencies
```cypher
MATCH path = (f1:File)-[:IMPORTS*2..]->(f1)
WHERE length(path) > 2
RETURN path LIMIT 10
```

See [examples/queries.md](examples/queries.md) for more examples.

## CLI Commands

```bash
# Initialize CodeBased in current directory
codebased init [--force]

# Update the graph (incremental by default)
codebased update [--full] [--path PATH]

# Start web server
codebased serve [--host HOST] [--port PORT]

# Execute Cypher query
codebased query "MATCH (n) RETURN count(n)"

# Show system status
codebased status

# Export graph data
codebased export [--format json|csv|graphml] [--output FILE]
```

## Performance

CodeBased is optimized for performance:

- **Incremental Updates**: Only re-parses changed files
- **Efficient Storage**: Kuzu's columnar storage
- **Streaming Parsers**: Memory-efficient for large codebases
- **WebGL Rendering**: Hardware acceleration for visualization
- **Level-of-Detail**: Dynamic node/edge simplification
- **Viewport Culling**: Only render visible elements

### Benchmarks

| Codebase Size | Initial Parse | Incremental Update | Memory Usage |
|---------------|---------------|-------------------|--------------|
| 1,000 LOC     | 2s           | 0.1s             | 50MB        |
| 10,000 LOC    | 15s          | 1s               | 200MB       |
| 100,000 LOC   | 2m           | 5s               | 800MB       |

## Troubleshooting

### Common Issues

**"Python not found"**
- Ensure Python 3.8+ is installed and in PATH
- Try `python3` instead of `python`

**"Permission denied" on setup scripts**
- Unix: `chmod +x setup.sh`
- Windows: Run PowerShell as Administrator

**"Database locked"**
- Stop any running `codebased serve` processes
- Remove `.codebased/data/graph.kuzu.lock` if it exists

**Large codebase performance**
- Increase `max_nodes` and `max_edges` in configuration
- Use filtering to focus on relevant code sections
- Enable WebGL rendering in browser

### Debug Mode

```bash
export CODEBASED_DEBUG=1
codebased update
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python -m pytest tests/`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Support

- Documentation: [docs/](docs/)
- Issues: Report on GitHub
- Questions: Check FAQ in [docs/FAQ.md](docs/FAQ.md)