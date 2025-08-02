# CodeBased Usage Guide

This comprehensive guide covers proper usage of the CodeBased tool, common pitfalls, and troubleshooting steps.

## 🚀 **Quick Start**

### Basic Extraction

```bash
# Extract from current directory
cd /path/to/your/project
python -m codebased.cli extract .

# Extract from specific directory
python -m codebased.cli extract /path/to/project

# Extract with verbose output
python -m codebased.cli extract /path/to/project --verbose
```

### Project Setup

1. **Install CodeBased in target project**:
   ```bash
   # Option 1: Use sync script (recommended for development)
   cd /workspace/codebased
   ./scripts/sync-to-harvestor.sh

   # Option 2: Manual installation
   cd /your/project
   mkdir .codebased
   python -m venv .codebased/venv
   source .codebased/venv/bin/activate
   pip install -e /path/to/codebased
   ```

2. **Configure project**:
   ```bash
   cd /your/project/.codebased
   # Configuration will be created automatically
   ```

## 🎯 **Best Practices**

### File Exclusion Configuration

**Always exclude build artifacts** to prevent processing compiled/generated files:

```yaml
# .codebased.yml
parsing:
  exclude_patterns:
    - '__pycache__'
    - '*.pyc'
    - '.git'
    - 'node_modules'
    - 'venv'
    - 'env'
    # Build artifacts (CRITICAL)
    - '*/dist/*'
    - '*/build/*'
    - '*/.angular/*'
    - '*/.next/*'
    - '*/coverage/*'
    - '*/out/*'
    - '*/.turbo/*'
    - '*/.cache/*'
    - '*/lib/*'
    - '*/esm/*'
    - '*/umd/*'
```

### Project Structure Detection

**Monorepo projects** require careful path configuration:

```bash
# For monorepo root
python -m codebased.cli extract . --config .codebased.yml

# For specific package in monorepo
python -m codebased.cli extract ./packages/frontend
```

### Performance Optimization

**File size limits** prevent processing of large generated files:

```yaml
parsing:
  max_file_size: 1048576  # 1MB limit
  follow_symlinks: false  # Avoid duplicate processing
```

## 🔍 **Language-Specific Guidance**

### JavaScript/TypeScript Projects

**Angular Projects**:
- Exclude `.angular/` cache directories
- Exclude `dist/` build outputs
- Include both `.ts` and `.js` files for mixed projects

**React Projects**:
- Exclude `build/` and `dist/` directories
- Include `.jsx` and `.tsx` files
- Exclude Webpack/Vite build artifacts

**Node.js Projects**:
- Always exclude `node_modules/`
- Exclude coverage reports (`coverage/`, `nyc_output/`)
- Include package configuration files (intentionally)

### Python Projects

**Django/Flask**:
- Exclude `__pycache__/` and `*.pyc`
- Exclude virtual environments (`venv/`, `env/`)
- Include migration files for analysis

**Data Science**:
- Exclude Jupyter checkpoint files (`.ipynb_checkpoints/`)
- Exclude large data files (`*.csv`, `*.parquet` if >1MB)

## ⚠️ **Common Pitfalls & Solutions**

### 1. **High File Count Issues**

**Problem**: Tool discovers 500+ files when expecting ~50

**Diagnosis**:
```bash
# Check file breakdown
find . -name "*.js" | head -20
find . -name "*.js" -path "*/dist/*" | wc -l
find . -name "*.js" -path "*/.angular/*" | wc -l
```

**Solution**: Update exclusion patterns (see configuration above)

### 2. **Relationship Storage Failures**

**Problem**: Entities extracted but relationships = 0

**Common Causes**:
- Missing target entities for external references
- Database schema issues
- Malformed relationship queries

**Diagnosis**:
```bash
# Check database tables
python -c "
from codebased.database.service import DatabaseService
db = DatabaseService('path/to/db')
db.initialize()
result = db.execute_query('CALL show_tables() RETURN *')
print([table for table in result])
"
```

**Solution**: Ensure JavaScript parser creates external entities (fixed in v0.1.1+)

### 3. **Parser Initialization Errors**

**Problem**: `tree-sitter not available` or similar import errors

**Diagnosis**:
```bash
# Check dependencies
pip list | grep tree
python -c "import tree_sitter; print('OK')"
```

**Solution**:
```bash
# Reinstall tree-sitter dependencies
pip install --force-reinstall tree-sitter==0.21.3 tree_sitter_languages==1.10.2
```

### 4. **Database Access Issues**

**Problem**: `Database path cannot be a directory` or permission errors

**Causes**:
- Incorrect database path configuration
- Permission issues with database directory
- Concurrent access conflicts

**Solution**:
```bash
# Check database path
ls -la .codebased/data/
# Ensure path points to file, not directory
# Example: .codebased/data/graph.kuzu (file)
# Not: .codebased/data/ (directory)
```

## 🛠️ **Troubleshooting Workflow**

### Step 1: Validate Configuration

```bash
# Check current configuration
python -c "
from codebased.config import load_config
config = load_config()
print(f'Project root: {config.project_root}')
print(f'Database path: {config.database.path}')
print(f'Exclude patterns: {config.parsing.exclude_patterns}')
"
```

### Step 2: Test File Discovery

```bash
# Count files by type
find . -name "*.js" -not -path "./node_modules/*" | wc -l
find . -name "*.ts" -not -path "./node_modules/*" | wc -l
find . -name "*.py" -not -path "./venv/*" | wc -l
```

### Step 3: Test Single File Parsing

```bash
python -c "
from codebased.parsers.javascript import JavaScriptParser
parser = JavaScriptParser()
result = parser.parse_file('./path/to/test.js')
print(f'Entities: {len(result.entities)}')
print(f'Relationships: {len(result.relationships)}')
print(f'Errors: {result.errors}')
"
```

### Step 4: Analyze Database State

```bash
python -c "
from codebased.database.service import DatabaseService
db = DatabaseService('./path/to/graph.kuzu')
db.initialize()
stats = db.get_stats()
print(f'Database stats: {stats}')
"
```

## 📊 **Performance Benchmarks**

### Expected Processing Rates

| Project Size | Files | Expected Time | Entities/sec |
|-------------|-------|---------------|--------------|
| Small (50 files) | 50 | 10-20s | 50-100 |
| Medium (200 files) | 200 | 30-60s | 100-200 |
| Large (500+ files) | 500+ | 2-5min | 150-300 |

### Performance Red Flags

⚠️ **Indicators of issues**:
- Processing >1000 files for small projects
- Parse time >10s per file
- 0 relationships extracted
- Memory usage >2GB

## 🔄 **Version Migration Guide**

### v0.1.0 → v0.1.1

**Breaking Changes**:
- Enhanced exclusion patterns (may affect file counts)
- JavaScript parser relationship handling improved

**Migration Steps**:
1. Update exclusion patterns in `.codebased.yml`
2. Clear existing database: `rm -rf .codebased/data/`
3. Re-run extraction: `python -m codebased.cli extract .`

## 📞 **Getting Help**

### Diagnostic Information to Collect

When reporting issues, include:

```bash
# System information
python --version
pip list | grep -E "(codebased|tree-sitter|kuzu)"

# Project information
find . -name "*.js" | head -5
find . -name "*.ts" | head -5
ls -la .codebased/

# Configuration
cat .codebased/.codebased.yml 2>/dev/null || echo "No config file"

# Error logs
tail -50 .codebased/logs/codebased.log 2>/dev/null || echo "No logs"
```

### Common Error Patterns

1. **Import/tree-sitter errors**: Dependency version mismatch
2. **High file counts**: Missing exclusion patterns
3. **0 relationships**: External entity creation issues
4. **Database errors**: Path or permission configuration
5. **Timeout errors**: Too many files or large files

This guide should be updated as new issues are discovered and resolved.