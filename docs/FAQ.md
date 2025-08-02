# Frequently Asked Questions (FAQ)

## General Questions

### What is CodeBased?

CodeBased is a lightweight, self-contained code graph generator and visualization tool that helps developers and AI agents understand code relationships through knowledge graphs. It uses Python AST parsing to extract code entities and stores them in an embedded Kuzu graph database.

### How is CodeBased different from other code analysis tools?

- **Zero Dependencies**: No external servers or databases required
- **Self-Contained**: Everything runs locally with embedded database
- **AI Agent Ready**: Pre-built queries designed for AI-assisted development
- **Incremental Updates**: Fast updates using file hashing
- **Interactive Visualization**: Real-time graph exploration with filtering
- **Language Agnostic Design**: Easy to extend for other programming languages

### What programming languages does CodeBased support?

Currently, CodeBased supports:
- Python (.py)
- JavaScript (.js)
- TypeScript (.ts, .tsx)
- JSX (.jsx)
- Angular components with template/style analysis

The architecture is designed for easy extension to other languages. Go, Java, and Rust parsers are planned for future releases.

## Installation & Setup

### What are the system requirements?

**Minimum**:
- Python 3.8+
- 512MB RAM
- 100MB disk space
- Any modern web browser

**Recommended**:
- Python 3.9+
- 2GB+ RAM
- 1GB+ disk space
- SSD storage for better performance

### Can I use CodeBased with virtual environments?

Yes! CodeBased works perfectly with virtual environments and is actually recommended. The setup scripts automatically create and configure a virtual environment for you.

### Does CodeBased work on Windows?

Yes, CodeBased supports Windows, macOS, and Linux. We provide both Unix shell scripts and PowerShell scripts for setup.

### Can I use CodeBased in a Docker container?

Yes, CodeBased can run in Docker. Here's a basic Dockerfile:

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
RUN pip install -e .
EXPOSE 8000
CMD ["codebased", "serve", "--host", "0.0.0.0"]
```

## Usage Questions

### How do I analyze my first project?

1. Navigate to your project directory
2. Run `./codebased/setup.sh` (or `setup.ps1` on Windows)
3. Run `codebased init` to initialize
4. Run `codebased update` to analyze your code
5. Run `codebased serve` and open http://localhost:8000

### How long does it take to analyze a project?

Analysis time depends on project size:
- 1,000 LOC: ~2 seconds
- 10,000 LOC: ~15 seconds
- 100,000 LOC: ~2 minutes

Subsequent incremental updates are much faster (typically under 5 seconds).

### Can I analyze multiple projects?

Yes, but each project needs its own CodeBased instance. You can have multiple projects with CodeBased installed, each maintaining its own graph database.

### How do I update the analysis when my code changes?

Run `codebased update` to perform an incremental update. CodeBased automatically detects changed files and only re-parses what's necessary. For a complete refresh, use `codebased update --full`.

## Configuration Questions

### How do I exclude certain directories from analysis?

Edit `.codebased.yml` and add patterns to `exclude_patterns`:

```yaml
parsing:
  exclude_patterns:
    - "venv/**"
    - "tests/**"
    - "*.pyc"
    - "__pycache__/**"
    - ".git/**"
```

### Can I change the web interface port?

Yes, use `codebased serve --port 8080` or set it in configuration:

```yaml
api:
  port: 8080
```

### How do I configure memory limits for large projects?

Adjust these settings in `.codebased.yml`:

```yaml
web:
  max_nodes: 10000
  max_edges: 15000
  performance_mode: "fast"
```

### Can I run CodeBased without the web interface?

Yes, CodeBased provides CLI commands for all operations:

```bash
# Query from command line
codebased query "MATCH (f:Function) RETURN f.name LIMIT 10"

# Export graph data
codebased export --format json --output graph.json
```

## Performance Questions

### My project is very large. Will CodeBased handle it?

CodeBased can handle large projects, but you may need to:

1. Increase memory limits in configuration
2. Use filtering to focus on relevant code sections
3. Enable performance mode: `performance_mode: "fast"`
4. Consider excluding test files and third-party libraries

### The web interface is slow. How can I improve it?

Try these optimizations:

1. Reduce `max_nodes` and `max_edges` in configuration
2. Use node type filters to show only relevant elements
3. Enable WebGL rendering in your browser
4. Use a modern browser with hardware acceleration

### Can I run CodeBased on a remote server?

Yes, configure the API to bind to all interfaces:

```bash
codebased serve --host 0.0.0.0 --port 8000
```

Make sure to secure access appropriately for production use.

## Troubleshooting

### "Python not found" error

Make sure Python 3.8+ is installed and in your PATH:

```bash
# Check Python version
python3 --version

# Use python3 explicitly if python isn't available
python3 -m codebased.cli --help
```

### "Permission denied" on setup scripts

Make the script executable:

```bash
# Unix/Linux/macOS
chmod +x setup.sh

# Windows: Run PowerShell as Administrator
```

### Database initialization fails

Try these steps:

1. Remove any existing database files: `rm -rf .codebased/data/`
2. Reinitialize: `codebased init --force`
3. Check directory permissions
4. Ensure adequate disk space

### Web interface won't load

Check these common issues:

1. Is the server running? `codebased serve`
2. Correct URL? Default is http://localhost:8000
3. Port already in use? Try a different port
4. Browser blocking localhost? Check security settings

### Out of memory errors

Reduce memory usage:

1. Lower `max_nodes` and `max_edges` settings
2. Use filtering to analyze smaller code sections
3. Close other memory-intensive applications
4. Add more system RAM if possible

## Query Questions

### How do I write Cypher queries?

Cypher is Neo4j's query language. Here are some examples:

```cypher
# Find all functions
MATCH (f:Function) RETURN f.name

# Find function callers
MATCH (caller)-[:CALLS]->(target:Function {name: "my_function"})
RETURN caller.name

# Find class hierarchy
MATCH path = (child:Class)-[:INHERITS*]->(parent:Class)
RETURN path
```

### What query templates are available?

CodeBased includes several built-in templates:
- Find Function Callers
- Class Inheritance Hierarchy
- File Dependencies
- Circular Dependencies
- Unused Functions
- Complex Functions
- Impact Analysis

Access them via the web interface or `GET /api/templates`.

### Can I save my custom queries?

Currently, custom query saving is not built-in, but you can:

1. Save queries in text files
2. Create your own template JSON file
3. Use the CLI: `codebased query "YOUR_QUERY_HERE"`

### How do I find performance bottlenecks in my code?

Use queries like:

```cypher
# Find complex functions
MATCH (f:Function) 
WHERE f.complexity > 10 
RETURN f.name, f.file_path, f.complexity 
ORDER BY f.complexity DESC

# Find heavily called functions
MATCH (f:Function)<-[:CALLS]-(caller)
RETURN f.name, count(caller) as call_count
ORDER BY call_count DESC
```

## Integration Questions

### Can I integrate CodeBased with my IDE?

While there are no official IDE plugins yet, you can:

1. Use the web interface alongside your IDE
2. Run CLI commands from your IDE's terminal
3. Create custom IDE scripts using the API
4. Use the API to build your own integrations

### Can I export data to other tools?

Yes, CodeBased supports several export formats:

```bash
# Export as JSON
codebased export --format json --output graph.json

# Export as CSV (nodes and edges separately)
codebased export --format csv --output nodes.csv

# Use the API for custom integrations
curl http://localhost:8000/api/graph > graph.json
```

### How do I use CodeBased with CI/CD?

Example GitHub Actions integration:

```yaml
- name: Analyze Code Graph
  run: |
    ./.codebased/setup.sh
    codebased update
    codebased query "MATCH (f:Function) WHERE f.complexity > 20 RETURN count(f)" > complexity_report.txt
```

### Can I use CodeBased programmatically?

Yes, via the REST API:

```python
import requests

# Get graph data
response = requests.get('http://localhost:8000/api/graph')
graph_data = response.json()

# Execute queries
query_response = requests.post('http://localhost:8000/api/query', 
    json={'query': 'MATCH (f:Function) RETURN f.name LIMIT 10'})
results = query_response.json()
```

## Contributing

### How can I contribute to CodeBased?

1. Report bugs and feature requests on GitHub
2. Submit pull requests for improvements
3. Add support for new programming languages
4. Improve documentation
5. Create examples and tutorials

### How do I add support for a new programming language?

1. Create a new parser class inheriting from `BaseParser`
2. Implement AST parsing for the target language
3. Map language constructs to CodeBased entities
4. Add tests for the new parser
5. Submit a pull request

### Can I create custom visualizations?

Yes! The frontend is modular. You can:

1. Extend the existing `GraphVisualizer` class
2. Create new visualization types (3D, timeline, etc.)
3. Add custom styling and interactions
4. Use the API data with your own visualization library

## Support

### Where can I get help?

1. Check this FAQ
2. Read the documentation in the `docs/` directory
3. Enable debug logging: `export CODEBASED_DEBUG=1`
4. Report issues on GitHub with:
   - Your operating system and Python version
   - Complete error messages
   - Steps to reproduce the issue

### Is commercial support available?

CodeBased is open-source. Community support is available through GitHub issues and discussions.

### How do I report security issues?

For security-related issues, please report them responsibly by:

1. Not posting public issues
2. Contacting the maintainers directly
3. Providing detailed information about the vulnerability
4. Allowing time for fixes before disclosure

## Roadmap

### What features are planned?

Near-term:
- JavaScript/TypeScript support
- Better performance for large codebases
- More visualization options
- IDE integrations

Long-term:
- Multi-language support (Go, Java, Rust)
- 3D visualizations
- Advanced code metrics
- Collaborative features

### Can I request features?

Yes! Please open a GitHub issue with:
- Clear description of the feature
- Use cases and benefits
- Any technical considerations
- Willingness to help implement