# Troubleshooting Guide

This guide helps you diagnose and fix common issues with CodeBased.

## Quick Diagnostic Steps

Before diving into specific issues, try these basic diagnostic steps:

1. **Check Python version**: `python3 --version` (requires 3.8+)
2. **Verify installation**: `codebased --help`
3. **Check disk space**: Ensure at least 100MB free
4. **Enable debug logging**: `export CODEBASED_DEBUG=1`
5. **Check log files**: `.codebased/logs/codebased.log`

## Installation Issues

### Python Version Problems

**Error**: `Python 3.8+ required, found 3.7.x`

**Solutions**:
```bash
# Ubuntu/Debian - Install newer Python
sudo apt update
sudo apt install python3.8 python3.8-pip python3.8-venv
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 1

# macOS with Homebrew
brew install python@3.8
echo 'export PATH="/usr/local/opt/python@3.8/bin:$PATH"' >> ~/.bashrc

# Windows - Download from python.org and reinstall
# Make sure to check "Add Python to PATH" during installation
```

### Virtual Environment Issues

**Error**: `venv: command not found`

**Solutions**:
```bash
# Install venv module
sudo apt install python3-venv  # Ubuntu/Debian
brew install python3           # macOS

# Alternative: use virtualenv
pip install virtualenv
virtualenv venv
```

**Error**: `Cannot activate virtual environment`

**Solutions**:
```bash
# Unix/Linux/macOS
source venv/bin/activate

# Windows Command Prompt
venv\Scripts\activate.bat

# Windows PowerShell
venv\Scripts\Activate.ps1

# If PowerShell blocks scripts:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Permission Errors

**Error**: `Permission denied: './setup.sh'`

**Solutions**:
```bash
# Make script executable
chmod +x setup.sh
chmod +x .codebased/setup.sh

# Or run with bash explicitly
bash setup.sh
```

**Error**: `Permission denied: writing to directory`

**Solutions**:
```bash
# Check directory permissions
ls -la .codebased/

# Fix permissions
chmod 755 .codebased/
chmod -R 755 .codebased/data/

# Create directories if missing
mkdir -p .codebased/data
mkdir -p .codebased/logs
```

### Dependency Installation Problems

**Error**: `Failed building wheel for package X`

**Solutions**:
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install build dependencies
sudo apt install build-essential python3-dev  # Ubuntu/Debian
xcode-select --install                         # macOS

# Use pre-compiled wheels
pip install --only-binary=all package_name
```

**Error**: `No module named 'kuzu'`

**Solutions**:
```bash
# Verify virtual environment is activated
which python  # Should point to venv/bin/python

# Reinstall kuzu
pip uninstall kuzu
pip install kuzu>=0.0.9

# If still failing, install from source
pip install kuzu --no-binary kuzu
```

## Database Issues

### Database Initialization Failures

**Error**: `Failed to initialize database`

**Solutions**:
```bash
# Remove corrupted database files
rm -rf .codebased/data/graph.kuzu*

# Check directory permissions
ls -la .codebased/data/

# Reinitialize with force flag
codebased init --force

# Check available disk space
df -h .
```

**Error**: `Database is locked`

**Solutions**:
```bash
# Stop all CodeBased processes
pkill -f "codebased serve"
pkill -f "uvicorn"

# Remove lock files
rm -f .codebased/data/graph.kuzu.lock
rm -f .codebased/data/*.lock

# Restart CodeBased
codebased serve
```

### Database Corruption

**Error**: `Database appears to be corrupted`

**Solutions**:
```bash
# Backup existing data (if recoverable)
cp -r .codebased/data/graph.kuzu .codebased/backup/

# Remove corrupted database
rm -rf .codebased/data/graph.kuzu*

# Reinitialize and re-parse
codebased init --force
codebased update --full

# Check filesystem integrity
fsck /dev/your-disk  # Unix/Linux
```

## Parsing Issues

### File Parsing Errors

**Error**: `SyntaxError: invalid syntax in file.py`

**Solutions**:
```bash
# Check Python version compatibility
python3 -m py_compile problematic_file.py

# Exclude problematic files
# Add to .codebased.yml:
parsing:
  exclude_patterns:
    - "problematic_file.py"
    - "legacy_code/**"

# Check file encoding
file problematic_file.py
```

**Error**: `UnicodeDecodeError: invalid start byte`

**Solutions**:
```bash
# Check file encoding
file -bi problematic_file.py

# Convert to UTF-8 if needed
iconv -f ENCODING -t UTF-8 file.py > file_utf8.py

# Exclude binary files
parsing:
  exclude_patterns:
    - "*.so"
    - "*.pyc"
    - "*.pyo"
```

### Memory Issues During Parsing

**Error**: `MemoryError during parsing`

**Solutions**:
```yaml
# Reduce memory usage in .codebased.yml
parsing:
  max_file_size_mb: 5  # Reduce from default 10
  exclude_patterns:
    - "large_generated_files/**"
    - "data/**/*.py"

web:
  max_nodes: 2000      # Reduce from default 5000
  max_edges: 3000      # Reduce from default 10000
```

```bash
# Process files in smaller batches
codebased update --path specific_directory/

# Increase system swap space (Linux)
sudo swapon --show
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

## Server Issues

### Port Already in Use

**Error**: `Port 8000 already in use`

**Solutions**:
```bash
# Find what's using the port
lsof -ti:8000           # Unix/Linux/macOS
netstat -ano | find "8000"  # Windows

# Kill the process
kill -9 $(lsof -ti:8000)    # Unix/Linux/macOS
taskkill /PID <PID> /F      # Windows

# Use a different port
codebased serve --port 8001

# Or set in configuration
api:
  port: 8001
```

### Cannot Connect to Server

**Error**: `Connection refused to localhost:8000`

**Solutions**:
```bash
# Check if server is running
ps aux | grep codebased
curl http://localhost:8000/api/status

# Start server if not running
codebased serve

# Check firewall settings
sudo ufw status                    # Ubuntu
sudo firewall-cmd --list-ports     # CentOS/RHEL

# Bind to all interfaces for remote access
codebased serve --host 0.0.0.0
```

### Server Crashes

**Error**: `Server exits unexpectedly`

**Solutions**:
```bash
# Enable debug logging
export CODEBASED_DEBUG=1
codebased serve

# Check logs
tail -f .codebased/logs/codebased.log

# Run with verbose output
uvicorn codebased.api.app:app --host localhost --port 8000 --log-level debug

# Check system resources
top
free -h
df -h
```

## Web Interface Issues

### Blank Page or Loading Forever

**Solutions**:
```bash
# Check browser console (F12)
# Look for JavaScript errors

# Clear browser cache
# Ctrl+Shift+Delete (Chrome/Firefox)

# Try different browser
# Chrome, Firefox, Safari, Edge

# Check API connectivity
curl http://localhost:8000/api/status

# Disable browser extensions
# Try incognito/private mode
```

### Performance Issues in Browser

**Solutions**:
```javascript
// Reduce graph size in configuration
web:
  max_nodes: 1000
  max_edges: 1500
  performance_mode: "fast"

// Enable WebGL in browser
// Chrome: chrome://flags/#enable-webgl
// Firefox: about:config -> webgl.force-enabled = true

// Use filtering to show fewer nodes
// Filter by node type or file path
```

### Graph Not Displaying

**Solutions**:
```bash
# Check if graph data exists
curl http://localhost:8000/api/graph | jq '.nodes | length'

# Regenerate graph data
codebased update --full

# Check browser compatibility
# Requires modern browser with ES6 support

# Disable ad blockers
# Some may block D3.js or API calls
```

## Query Issues

### Invalid Cypher Queries

**Error**: `Parser Error: Invalid Cypher syntax`

**Solutions**:
```cypher
-- Check basic syntax
MATCH (n) RETURN n LIMIT 10;

-- Use proper quotes
MATCH (f:Function {name: "my_function"}) RETURN f;

-- Check node/relationship types
MATCH (n) RETURN DISTINCT labels(n);
MATCH ()-[r]->() RETURN DISTINCT type(r);
```

### Query Timeouts

**Error**: `Query execution timeout`

**Solutions**:
```yaml
# Increase timeout in configuration
api:
  query_timeout_seconds: 60  # Default is 30

# Optimize queries
# Add LIMIT clauses
# Use indexed properties
# Avoid expensive operations

# Example optimizations:
MATCH (f:Function) RETURN f.name LIMIT 100;  // Instead of returning all
MATCH (f:Function {name: "specific"}) RETURN f;  // Use specific matches
```

### Empty Query Results

**Solutions**:
```cypher
-- Check if data exists
MATCH (n) RETURN count(n);

-- Check node types
MATCH (n) RETURN DISTINCT labels(n);

-- Check relationships
MATCH ()-[r]->() RETURN DISTINCT type(r) LIMIT 10;

-- Verify node properties
MATCH (f:Function) RETURN f.name, f.file_path LIMIT 10;
```

## Performance Issues

### Slow Initial Parsing

**Solutions**:
```yaml
# Exclude unnecessary files
parsing:
  exclude_patterns:
    - "venv/**"
    - "*.pyc"
    - "__pycache__/**"
    - ".git/**"
    - "tests/**"
    - "docs/**"
    - "build/**"
    - "dist/**"

# Limit file size
parsing:
  max_file_size_mb: 5
```

```bash
# Use SSD storage for better I/O
# Ensure adequate RAM (2GB+ for large projects)
# Close other memory-intensive applications

# Parse specific directories first
codebased update --path src/
codebased update --path lib/
```

### Slow Web Interface

**Solutions**:
```yaml
# Reduce visualization complexity
web:
  max_nodes: 1000
  max_edges: 1500
  performance_mode: "fast"
```

```javascript
// Enable hardware acceleration in browser settings
// Chrome: Settings > Advanced > System > Use hardware acceleration
// Firefox: Settings > General > Performance > Use hardware acceleration
```

### High Memory Usage

**Solutions**:
```bash
# Monitor memory usage
htop
ps aux --sort=-%mem | head

# Reduce graph size
web:
  max_nodes: 2000
  max_edges: 3000

# Use filtering to focus analysis
# Filter by specific directories or file types
```

## Network Issues

### Cannot Access from Remote Machine

**Solutions**:
```bash
# Bind to all interfaces
codebased serve --host 0.0.0.0 --port 8000

# Check firewall settings
sudo ufw allow 8000/tcp           # Ubuntu
sudo firewall-cmd --permanent --add-port=8000/tcp  # CentOS/RHEL

# Configure CORS if needed
api:
  cors_origins:
    - "http://your-remote-ip:3000"
    - "http://another-domain.com"
```

### SSL/HTTPS Issues

**Solutions**:
```bash
# For development, disable HTTPS requirements
# Use HTTP instead of HTTPS

# For production, use reverse proxy
# nginx, Apache, or Traefik with SSL termination

# Example nginx configuration:
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment-Specific Issues

### Windows-Specific Issues

**PowerShell Execution Policy**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Path Separator Issues**:
- Use forward slashes in configuration files
- CodeBased handles path conversion automatically

**Antivirus Interference**:
- Add .codebased directory to antivirus exclusions
- Kuzu database files may trigger false positives

### macOS-Specific Issues

**Xcode Command Line Tools**:
```bash
xcode-select --install
```

**Python from Mac App Store vs Homebrew**:
```bash
# Use Homebrew Python for better compatibility
brew install python@3.9
echo 'export PATH="/usr/local/opt/python@3.9/bin:$PATH"' >> ~/.zshrc
```

### Linux Distribution Issues

**Package Manager Dependencies**:
```bash
# Ubuntu/Debian
sudo apt install python3-dev build-essential

# CentOS/RHEL
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel

# Arch Linux
sudo pacman -S python3 gcc make
```

## Getting More Help

### Enable Debug Logging

```bash
export CODEBASED_DEBUG=1
export CODEBASED_LOG_LEVEL=DEBUG
codebased serve
```

### Collect Diagnostic Information

```bash
# System information
uname -a
python3 --version
pip list | grep -E "(kuzu|fastapi|uvicorn|click)"

# CodeBased status
codebased status

# Log files
tail -100 .codebased/logs/codebased.log

# Configuration
cat .codebased.yml
```

### Report Issues

When reporting issues, include:

1. **Environment Details**:
   - Operating system and version
   - Python version
   - CodeBased version

2. **Error Information**:
   - Complete error message
   - Steps to reproduce
   - Expected vs actual behavior

3. **Relevant Files**:
   - Configuration file (.codebased.yml)
   - Log files (last 50-100 lines)
   - Sample code that causes issues (if applicable)

4. **Diagnostic Output**:
   - `codebased status` output
   - `codebased --version` output
   - Browser console errors (if web interface issue)

### Emergency Recovery

If CodeBased is completely broken:

```bash
# Nuclear option - fresh start
rm -rf venv/
rm -rf .codebased/data/
rm -rf .codebased/logs/
rm .codebased.yml

# Reinstall from scratch
./setup.sh
codebased init
codebased update
```

Remember: Always backup your code and any custom configurations before attempting emergency recovery procedures.