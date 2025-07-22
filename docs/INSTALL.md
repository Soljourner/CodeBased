# Installation Guide

This guide covers different ways to install and set up CodeBased.

## Prerequisites

- Python 3.8 or higher
- At least 512MB RAM (2GB+ recommended for large codebases)
- 100MB+ disk space
- Modern web browser (Chrome, Firefox, Safari, Edge)

## Common Installation Error Fix

**If you see "externally-managed-environment" error:**

This means your system Python is protected and you MUST use a virtual environment. Do NOT use `--break-system-packages`. Instead:

```bash
# Create virtual environment FIRST
python3 -m venv venv

# Activate it
source venv/bin/activate  # Unix/Linux/macOS
# OR
venv\Scripts\activate     # Windows

# NOW install packages
pip install -r requirements.txt
```

## Quick Install (Recommended)

### Unix/Linux/macOS

```bash
# Clone or download CodeBased to your project
cd your-project-directory

# Run the automated setup script
chmod +x .codebased/setup.sh
./.codebased/setup.sh
```

### Windows

```powershell
# Open PowerShell as Administrator
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Navigate to your project
cd your-project-directory

# Run the setup script
.\.codebased\setup.ps1
```

The setup script will:
1. Check Python version (requires 3.8+)
2. Create and activate a virtual environment
3. Install all dependencies
4. Initialize the database
5. Run basic tests

## Manual Installation

If the automated script doesn't work for your environment:

### Step 1: Python Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# Unix/macOS:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### Step 2: Install Dependencies

```bash
# Navigate to CodeBased directory
cd .codebased

# Install required packages
pip install -r requirements.txt

# Install CodeBased in development mode
pip install -e .
```

### Step 3: Initialize Database

```bash
# Initialize CodeBased in your project
codebased init

# Perform initial code parsing
codebased update
```

### Step 4: Verify Installation

```bash
# Run tests
python3 -m pytest tests/ -v

# Start the server
codebased serve

# Open http://localhost:8000 in your browser
```

## Dependencies

### Core Dependencies
- `kuzu>=0.0.9` - Graph database
- `fastapi>=0.104.0` - Web API framework
- `uvicorn>=0.24.0` - ASGI server
- `click>=8.1.0` - CLI framework
- `pyyaml>=6.0` - Configuration parsing
- `pydantic>=2.0.0` - Data validation

### Development Dependencies
- `pytest>=7.0.0` - Testing framework
- `black>=23.0.0` - Code formatting
- `mypy>=1.0.0` - Type checking
- `isort>=5.12.0` - Import sorting

### Optional Dependencies
- `watchdog>=3.0.0` - File system monitoring
- `rich>=13.0.0` - Enhanced console output

## Configuration

After installation, configure CodeBased by editing `.codebased.yml`:

```yaml
# Project settings
project_root: "."
cache_dir: ".codebased/cache"

# Database configuration
database:
  path: ".codebased/data/graph.kuzu"
  backup_enabled: true
  backup_interval_hours: 24

# Parsing configuration
parsing:
  include_patterns:
    - "**/*.py"
  exclude_patterns:
    - "venv/**"
    - "*.pyc"
    - "__pycache__/**"
    - ".git/**"
    - "node_modules/**"
  max_file_size_mb: 10
  timeout_seconds: 30

# API configuration
api:
  host: "localhost"
  port: 8000
  cors_origins:
    - "http://localhost:3000"
    - "http://localhost:8080"

# Web interface
web:
  max_nodes: 5000
  max_edges: 10000
  enable_webgl: true
  performance_mode: "auto"  # auto, fast, quality

# Logging
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: ".codebased/logs/codebased.log"
```

## Troubleshooting Installation

### Python Version Issues

**Error**: "Python 3.8+ required"
```bash
# Check Python version
python3 --version

# Install Python 3.8+ if needed
# Ubuntu/Debian:
sudo apt update
sudo apt install python3.8 python3.8-pip python3.8-venv

# macOS (with Homebrew):
brew install python@3.8

# Windows: Download from python.org
```

### Permission Errors

**Error**: "Permission denied"
```bash
# Unix/Linux - Make scripts executable
chmod +x .codebased/setup.sh

# Windows - Run PowerShell as Administrator
# Or change execution policy:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Virtual Environment Issues

**Error**: "venv command not found"
```bash
# Install venv module
# Ubuntu/Debian:
sudo apt install python3-venv

# Or use alternative:
pip install virtualenv
virtualenv venv
```

### Database Initialization Errors

**Error**: "Failed to initialize database"
```bash
# Check directory permissions
ls -la .codebased/

# Create data directory if missing
mkdir -p .codebased/data

# Remove corrupted database files
rm -rf .codebased/data/graph.kuzu*
codebased init --force
```

### Port Already in Use

**Error**: "Port 8000 already in use"
```bash
# Use different port
codebased serve --port 8001

# Or kill existing process
# Unix/Linux:
lsof -ti:8000 | xargs kill -9
# Windows:
netstat -ano | findstr :8000
taskkill /PID <PID> /F
```

### Memory Issues

**Error**: "Out of memory"
- Reduce `max_nodes` and `max_edges` in configuration
- Use filtering to focus on specific code sections
- Increase system swap space
- Close other memory-intensive applications

### Network Issues

**Error**: "Connection refused"
- Check firewall settings
- Verify port is not blocked
- Try `--host 0.0.0.0` for external access
- Check antivirus software

## Docker Installation (Alternative)

If you prefer containerized deployment:

```dockerfile
# Dockerfile
FROM python:3.8-slim

WORKDIR /app
COPY .codebased/requirements.txt .
RUN pip install -r requirements.txt

COPY . .
RUN pip install -e .codebased/

EXPOSE 8000
CMD ["codebased", "serve", "--host", "0.0.0.0"]
```

```bash
# Build and run
docker build -t codebased .
docker run -p 8000:8000 -v $(pwd):/app codebased
```

## Upgrading

To upgrade CodeBased:

```bash
# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r .codebased/requirements.txt --upgrade

# Update database schema if needed
codebased init --force

# Refresh graph data
codebased update --full
```

## Uninstalling

To remove CodeBased:

```bash
# Remove virtual environment
rm -rf venv

# Remove CodeBased files (optional - keeps your code)
rm -rf .codebased

# Remove configuration (optional)
rm .codebased.yml
```

## System Requirements

### Minimum Requirements
- **CPU**: 1 core, 1GHz
- **RAM**: 512MB available
- **Disk**: 100MB free space
- **Network**: None (offline capable)

### Recommended Requirements
- **CPU**: 2+ cores, 2GHz+
- **RAM**: 2GB+ available
- **Disk**: 1GB+ free space (for large codebases)
- **SSD**: Recommended for better performance

### Performance Guidelines

| Codebase Size | Recommended RAM | Parse Time | Database Size |
|---------------|----------------|------------|---------------|
| < 1,000 LOC   | 512MB         | < 10s      | < 1MB        |
| < 10,000 LOC  | 1GB           | < 1min     | < 10MB       |
| < 100,000 LOC | 2GB           | < 5min     | < 100MB      |
| 100,000+ LOC  | 4GB+          | 5min+      | 100MB+       |

## Getting Help

If you encounter issues:

1. Check the [Troubleshooting Guide](TROUBLESHOOTING.md)
2. Review the [FAQ](FAQ.md)
3. Enable debug logging: `export CODEBASED_DEBUG=1`
4. Check the logs: `.codebased/logs/codebased.log`
5. Report issues on GitHub with:
   - Operating system and Python version
   - Complete error message
   - Steps to reproduce
   - Log files (if relevant)