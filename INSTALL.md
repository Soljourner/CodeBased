# CodeBased Installation Guide

This guide will help you set up and run CodeBased, a lightweight code graph generator and visualization tool.

## Prerequisites

- Python 3.8 or higher
- pip package manager

## Installation Steps

### 1. Navigate to the CodeBased Directory

```bash
cd .codebased
```

### 2. Install Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

For development (with testing and linting tools):

```bash
pip install -r requirements-dev.txt
```

### 3. Install CodeBased Package

Install CodeBased in development mode:

```bash
pip install -e .
```

This allows you to run `codebased` commands from anywhere.

### 4. Test the Installation

Run the test script to verify everything is working:

```bash
python test_installation.py
```

You should see all tests pass with the message "🎉 All tests passed! CodeBased is ready to use."

## Quick Start

### 1. Initialize CodeBased

From your project root directory (where you want to analyze code):

```bash
codebased init
```

This creates:
- `.codebased.yml` configuration file
- `.codebased/` directory with necessary subdirectories
- Kuzu graph database
- Basic web interface files

### 2. Analyze Your Code

Run the initial code analysis:

```bash
codebased update
```

This will:
- Parse all Python files in your project
- Extract entities (classes, functions, variables, etc.)
- Build relationships between entities
- Store everything in the graph database

### 3. Start the Web Interface

Launch the visualization server:

```bash
codebased serve
```

Then open your browser to `http://localhost:8000` to view the code graph visualization.

## Configuration

CodeBased uses a `.codebased.yml` configuration file. Key settings include:

### Parsing Configuration

```yaml
parsing:
  file_extensions:
    - ".py"
    - ".js"
    - ".ts"
  exclude_patterns:
    - "__pycache__"
    - "node_modules"
    - ".git"
  max_file_size: 1048576  # 1MB
```

### API Configuration

```yaml
api:
  host: "127.0.0.1"
  port: 8000
  debug: false
```

### Web Interface Configuration

```yaml
web:
  max_nodes: 1000
  max_edges: 5000
  default_layout: "force"
```

## Command Reference

### `codebased init`
Initialize CodeBased in the current directory.

Options:
- `--force`: Overwrite existing configuration

### `codebased update`
Update the code graph (analyze code changes).

Options:
- `--full`: Force complete rebuild instead of incremental
- `--path PATH`: Specify directory to analyze

### `codebased serve`
Start the API and web server.

Options:
- `--host HOST`: Host to bind to
- `--port PORT`: Port to bind to
- `--reload`: Enable auto-reload for development
- `--debug`: Enable debug mode

### `codebased query`
Execute Cypher queries against the graph.

```bash
codebased query "MATCH (f:Function) RETURN f.name LIMIT 10"
```

Options:
- `--format FORMAT`: Output format (table, json, csv)
- `--limit NUM`: Limit results

### `codebased status`
Show system status and statistics.

### `codebased reset`
Reset the database (destructive operation).

## API Endpoints

Once the server is running, you can access:

- **Web Interface**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs`
- **Health Check**: `http://localhost:8000/health`

### Key API Endpoints

- `POST /api/query` - Execute Cypher queries
- `POST /api/update` - Trigger graph updates
- `GET /api/graph` - Get graph data for visualization
- `GET /api/templates` - Get pre-built query templates
- `GET /api/status` - System status

## Troubleshooting

### Database Issues

If you encounter database errors:

1. Reset the database:
   ```bash
   codebased reset
   ```

2. Reinitialize:
   ```bash
   codebased update --full
   ```

### Permission Issues

Ensure the `.codebased/` directory is writable:

```bash
chmod -R 755 .codebased/
```

### Import Errors

If you get import errors, ensure CodeBased is properly installed:

```bash
pip install -e .
```

### Port Already in Use

If port 8000 is in use, specify a different port:

```bash
codebased serve --port 8080
```

## Development

For development work:

1. Install development dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run tests:
   ```bash
   python test_installation.py
   ```

3. Format code:
   ```bash
   black src/
   ```

4. Type checking:
   ```bash
   mypy src/
   ```

## Project Structure

```
.codebased/
├── src/codebased/           # Main source code
│   ├── api/                 # FastAPI application
│   ├── database/            # Database management
│   ├── parsers/             # Code parsers
│   ├── config.py            # Configuration system
│   └── cli.py               # Command-line interface
├── web/                     # Web interface
│   ├── index.html
│   ├── style.css
│   ├── graph.js             # D3.js visualization
│   └── app.js               # Main application
├── data/                    # Database storage
├── config/                  # Configuration files
├── requirements.txt         # Dependencies
├── setup.py                 # Package setup
└── README.md               # Documentation
```

## Support

For issues and questions:

1. Check the console output for error messages
2. Verify your Python and dependency versions
3. Run the test installation script
4. Check the API documentation at `/docs`