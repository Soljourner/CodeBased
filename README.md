# CodeBased - Code Intelligence Through Graph Visualization

CodeBased is a powerful code analysis tool that transforms your codebase into an interactive knowledge graph. It helps developers understand complex code relationships, dependencies, and architecture through visual exploration and intelligent querying.

## 🎯 Purpose

CodeBased creates a searchable, visual representation of your code's structure and relationships. Whether you're onboarding to a new project, refactoring legacy code, or documenting system architecture, CodeBased provides instant insights into how your code connects and interacts.

## ✨ Key Features

- **🔍 Multi-Language Support**: Analyzes Python, JavaScript, TypeScript, and Angular code with specialized parsers
- **📊 Interactive Visualization**: Explore your code through a force-directed graph with real-time filtering
- **⚡ Incremental Updates**: Lightning-fast analysis that only processes changed files
- **🗄️ Embedded Database**: Uses Kuzu graph database - no external dependencies or servers required
- **🔧 Powerful Querying**: Write Cypher queries to find patterns, dependencies, and potential issues
- **🎨 Smart Filtering**: Filter by file types, node types, or search for specific code elements
- **📁 Self-Contained**: Installs entirely within your project's `.codebased` folder
- **🤖 AI-Friendly**: Designed to help AI agents understand and navigate your codebase

## 🚀 Installation

### Quick Start
For a step-by-step walkthrough with expected outputs, see **[docs/QUICK_START.md](docs/QUICK_START.md)**.

### Prerequisites
- Python 3.8 or higher
- pip package manager
- Virtual environment support (venv)

### Important Concepts
**CodeBased is completely self-contained within the `.codebased` directory:**
- 📁 `.codebased/` - Contains everything (code, database, virtual environment)
- 🐍 `.codebased/venv/` - Python virtual environment (NOT in project root)
- 📊 `.codebased/data/` - Graph database files
- 🌐 `.codebased/web/` - Web interface files
- 📝 `.codebased.yml` - Configuration file (goes in PROJECT ROOT, not inside .codebased)

**Always run commands from your PROJECT ROOT directory, never from inside `.codebased/`**

### Quick Install

1. **Clone CodeBased into your project**:
   ```bash
   cd your-project-root
   git clone https://github.com/yourusername/codebased.git .codebased
   ```

2. **Run the setup script FROM YOUR PROJECT ROOT**:
   ```bash
   # Unix/Linux/macOS
   chmod +x .codebased/setup.sh
   ./.codebased/setup.sh

   # Windows PowerShell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   .\.codebased\setup.ps1
   ```

3. **Activate the virtual environment**:
   ```bash
   # Unix/Linux/macOS
   source .codebased/venv/bin/activate

   # Windows
   .codebased\venv\Scripts\activate
   ```

### Manual Installation

For detailed installation instructions and troubleshooting, see **[docs/INSTALL.md](docs/INSTALL.md)**.

If the setup script doesn't work for your environment:

```bash
# FROM YOUR PROJECT ROOT (not inside .codebased)
cd your-project-root

# Create virtual environment inside .codebased
python3 -m venv .codebased/venv

# Activate it
source .codebased/venv/bin/activate  # On Windows: .codebased\venv\Scripts\activate

# Install dependencies
pip install -r .codebased/requirements.txt

# Install CodeBased in development mode
pip install -e .codebased/

# Initialize CodeBased (creates .codebased.yml in project root)
codebased init
```

## 📁 Directory Structure After Installation

```
your-project/
├── .codebased/              # Everything CodeBased-related
│   ├── venv/               # Python virtual environment
│   ├── src/                # CodeBased source code
│   ├── data/               # Graph database
│   ├── web/                # Web interface files
│   ├── logs/               # Log files
│   └── requirements.txt    # Python dependencies
├── .codebased.yml          # Configuration (in project root!)
├── your_code/              # Your project files
└── ...                     # Other project files
```

## 📖 Usage

For comprehensive usage instructions, see **[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)**.

### Basic Workflow

1. **Initialize CodeBased** in your project:
   ```bash
   codebased init
   ```
   This creates configuration files and sets up the graph database.

2. **Analyze your code**:
   ```bash
   codebased update
   ```
   This parses your code and builds the knowledge graph.

3. **Start the visualization server**:
   ```bash
   codebased serve
   ```
   Open http://localhost:8000 to explore your code graph.

### Command Reference

#### `codebased init`
Initializes CodeBased in your project directory.
- Creates `.codebased.yml` configuration file
- Sets up the graph database
- Prepares web interface files

Options:
- `--force` - Overwrite existing configuration

#### `codebased update`
Analyzes your code and updates the graph.
- Performs incremental updates by default (only changed files)
- Extracts entities (classes, functions, etc.) and relationships
- Stores results in the embedded database

Options:
- `--full` - Force complete rebuild
- `--path PATH` - Analyze specific directory

#### `codebased serve`
Starts the web server for visualization.
- Interactive graph visualization
- Query interface
- Real-time filtering

Options:
- `--host HOST` - Bind to specific host (default: localhost)
- `--port PORT` - Use specific port (default: 8000)
- `--debug` - Enable debug mode

#### `codebased query`
Execute Cypher queries from the command line.

```bash
codebased query "MATCH (f:Function) RETURN f.name LIMIT 10"
```

Options:
- `--format FORMAT` - Output format: table, json, csv
- `--limit N` - Limit results

#### `codebased status`
Check system status and statistics.
- Database health
- Number of nodes and relationships
- Tracked files

## ⚙️ Configuration

For detailed configuration options, see the **[default configuration reference](config/default.yml)**.

CodeBased uses `.codebased.yml` for configuration:

```yaml
# Project settings
project_root: "."

# Language parsers
parsing:
  file_extensions: [".py", ".js", ".ts", ".tsx", ".jsx"]
  exclude_patterns:
    - "node_modules"
    - "__pycache__"
    - "*.min.js"
    - "dist"
    - "build"
  max_file_size: 1048576  # 1MB

# Database settings  
database:
  path: ".codebased/data/graph.kuzu"

# Web interface
web:
  max_nodes: 5000
  max_edges: 10000

# API server
api:
  host: "localhost"
  port: 8000
```

## 🏗️ Architecture

For detailed architecture information, see **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

CodeBased consists of several key components:

1. **Language Parsers**: Extract code structure using tree-sitter
   - Python parser for classes, functions, imports
   - JavaScript/TypeScript parser with ES6+ support
   - Angular-aware parser for components, services, and templates

2. **Graph Database**: Kuzu embedded database stores entities and relationships
   - No external database server required
   - Efficient graph queries with Cypher
   - Incremental update support

3. **Web Interface**: D3.js-powered visualization
   - Force-directed graph layout
   - Interactive filtering and search
   - Query execution interface

4. **CLI**: Command-line interface for all operations
   - Built with Click framework
   - Scriptable for automation
   - JSON output support

## 💡 Example Queries

For Kuzu query syntax and comprehensive examples, see:
- **[docs/QUERIES.md](docs/QUERIES.md)** - Kuzu syntax basics and troubleshooting
- **[examples/QUERY_LIBRARY.md](examples/QUERY_LIBRARY.md)** - Advanced query examples

Find all functions that call a specific function:
```cypher
MATCH (caller:Function)-[:CALLS]->(target:Function {name: "processData"})
RETURN caller.name, caller.file_path
```

Discover circular dependencies:
```cypher
MATCH p=(a)-[:IMPORTS*]->(a)
WHERE length(p) > 1
RETURN p LIMIT 10
```

Find unused functions:
```cypher
MATCH (f:Function)
WHERE NOT (()-[:CALLS]->(f))
RETURN f.name, f.file_path
```

Analyze class hierarchy:
```cypher
MATCH path = (child:Class)-[:INHERITS*]->(parent:Class)
RETURN path
```

## 🐛 Troubleshooting

For comprehensive troubleshooting, see **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.

### Common Issues

**"Module 'codebased' not found"**
- Ensure you've activated the virtual environment
- Try reinstalling: `pip install -e .`

**"Database locked" error**
- Stop any running `codebased serve` processes
- Check for stale lock files in `.codebased/data/`

**Parser not recognizing files**
- Check file extensions in `.codebased.yml`
- Ensure files aren't excluded by patterns
- Verify file size is under the limit

**Web interface not loading**
- Check if port 8000 is available
- Try a different port: `codebased serve --port 8080`
- Check browser console for errors

### Debug Mode

Enable detailed logging:
```bash
export CODEBASED_DEBUG=1
codebased update
```

### Health Check

Run the built-in diagnostic tool:
```bash
codebased doctor
```

This checks for common installation and configuration issues.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 📚 Documentation

Complete documentation is available in the **[docs/](docs/)** directory:

- **[docs/README.md](docs/README.md)** - Documentation index and navigation guide
- **[docs/QUICK_START.md](docs/QUICK_START.md)** - Step-by-step guide with expected outputs
- **[docs/INSTALL.md](docs/INSTALL.md)** - Detailed installation and troubleshooting
- **[docs/USAGE_GUIDE.md](docs/USAGE_GUIDE.md)** - Comprehensive usage instructions
- **[docs/QUERIES.md](docs/QUERIES.md)** - Kuzu query syntax and basics
- **[docs/FAQ.md](docs/FAQ.md)** - Frequently asked questions
- **[docs/API.md](docs/API.md)** - API reference documentation

## 🆘 Support

- **Issues**: Report bugs on GitHub
- **Questions**: Check the [FAQ](docs/FAQ.md)
- **Examples**: See [examples/QUERY_LIBRARY.md](examples/QUERY_LIBRARY.md) for query examples

---

Made with ❤️ by developers, for developers. CodeBased helps you understand code the way it's meant to be understood - as a living, connected system.