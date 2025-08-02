# CodeBased Tool - Remaining Issues

This document details the issues discovered during comprehensive testing of the CodeBased tool in the Harvestor project directory (`/workspace/appspace/Harvestor/.codebased/`).

## Critical Issues

### 1. Missing Database Tables
**Priority**: HIGH  
**Impact**: Prevents proper code analysis and storage

**Description**: The JavaScript/TypeScript parser generates entity types that don't have corresponding database tables in the schema.

**Missing Tables**:
- `ArrowFunction` - Used by JavaScript parser for arrow functions
- `ExternalProperty` - Used for external property references
- `ExternalFunction` - Used for external function references

**Error Messages**:
```
Binder exception: Table ArrowFunction does not exist.
Binder exception: Table ExternalProperty does not exist.
Binder exception: Table ExternalFunction does not exist.
```

**Reproduction Steps**:
1. Run `codebased init` in a TypeScript/JavaScript project
2. Run `codebased update` to analyze code
3. Observe errors in the output

**Suggested Fix**: Add the missing table definitions to `src/codebased/database/schema.py`:
```python
'ArrowFunction': """
    CREATE NODE TABLE IF NOT EXISTS ArrowFunction(
        id STRING,
        name STRING,
        file_id STRING,
        line_start INT64,
        line_end INT64,
        signature STRING,
        return_type STRING,
        is_async BOOLEAN,
        PRIMARY KEY (id)
    )
""",

'ExternalProperty': """
    CREATE NODE TABLE IF NOT EXISTS ExternalProperty(
        id STRING,
        name STRING,
        file_id STRING,
        object_name STRING,
        property_path STRING,
        line_number INT64,
        PRIMARY KEY (id)
    )
""",

'ExternalFunction': """
    CREATE NODE TABLE IF NOT EXISTS ExternalFunction(
        id STRING,
        name STRING,
        file_id STRING,
        object_name STRING,
        line_number INT64,
        PRIMARY KEY (id)
    )
"""
```

### 2. Duplicate Primary Key Violations
**Priority**: HIGH  
**Impact**: Prevents complete code analysis, data integrity issues

**Description**: During the update process, duplicate primary keys are generated causing insertion failures.

**Error Messages**:
```
Runtime exception: Found duplicated primary key value 055689280cb7bac73617413792cd1c34f2e4022295b632118dd07be85869d705, which violates the uniqueness constraint of the primary key column.
```

**Reproduction Steps**:
1. Run `codebased update` on a large codebase
2. Observe duplicate key errors in batch insertions

**Root Cause**: The ID generation mechanism in the parser may be creating non-unique identifiers for certain code patterns.

**Suggested Fix**: 
- Review ID generation in `src/codebased/parsers/extractor.py`
- Ensure unique IDs by including more context (file path, line number, etc.)
- Implement deduplication logic before batch insertion

### 3. Database Re-initialization on Server Start
**Priority**: MEDIUM  
**Impact**: Potential data loss, performance issues

**Description**: When running `codebased serve`, the system attempts to recreate the schema even if it already exists.

**Log Output**:
```
2025-08-01 21:04:06 - codebased.database.schema - INFO - Creating graph schema...
2025-08-01 21:04:07 - codebased.database.schema - INFO - Graph schema created successfully
```

**Suggested Fix**: Add schema existence check before creation in `src/codebased/api/main.py`

## Documentation Issues

### 4. Missing Setup Scripts
**Priority**: MEDIUM  
**Impact**: Installation process more difficult than documented

**Description**: The README references setup scripts that don't exist:
- `setup.sh` (Unix/Linux/macOS)
- `setup.ps1` (Windows PowerShell)

**Documentation Reference**:
```bash
# Unix/Linux/macOS
chmod +x .codebased/setup.sh
./.codebased/setup.sh
```

**Actual Installation**: Users must manually:
1. Create virtual environment
2. Install requirements
3. Run pip install -e .

**Suggested Fix**: Either create the setup scripts or update documentation to reflect manual installation process.

### 5. File Tracking Not Working
**Priority**: MEDIUM  
**Impact**: Status command shows incorrect information

**Description**: Despite successfully parsing 177 files, the status command reports "Tracked files: 0"

**Output**:
```
Nodes: 5205
Relationships: 1762
Tables: 68
Tracked files: 0
```

**Suggested Fix**: Investigate file tracking mechanism in the database service.

## Minor Issues

### 6. Tree-sitter Deprecation Warning
**Priority**: LOW  
**Impact**: Warning messages in output

**Warning**:
```
FutureWarning: Language(path, name) is deprecated. Use Language(ptr, name) instead.
```

**Location**: `/workspace/appspace/Harvestor/.codebased/venv/lib/python3.11/site-packages/tree_sitter/__init__.py:36`

**Suggested Fix**: Update tree-sitter usage in parsers to use the new API.

### 7. Locale Warning
**Priority**: LOW  
**Impact**: Cosmetic issue

**Warning**:
```
/bin/bash: warning: setlocale: LC_ALL: cannot change locale (en_US.UTF-8)
```

**Suggested Fix**: Set proper locale in Docker container or suppress warning.

## Summary

The CodeBased tool shows promise but has several critical issues that need to be addressed:

1. **Database Schema Incompleteness**: Missing tables for JavaScript/TypeScript entities
2. **Data Integrity Issues**: Duplicate primary keys preventing proper data storage
3. **Documentation Inaccuracies**: Installation instructions don't match reality
4. **State Management Issues**: File tracking and schema re-initialization problems

## Recommendations

1. **Immediate Actions**:
   - Add missing table definitions to schema
   - Fix duplicate key generation
   - Update installation documentation

2. **Short-term Improvements**:
   - Implement proper schema migration system
   - Add better error handling and recovery
   - Create automated tests for all parsers

3. **Long-term Enhancements**:
   - Implement incremental schema updates
   - Add support for schema versioning
   - Improve parser robustness for edge cases

## Testing Notes

All tests were performed on:
- **Date**: 2025-08-01
- **Location**: `/workspace/appspace/Harvestor/.codebased/`
- **Python Version**: 3.11
- **Project Type**: TypeScript/Angular monorepo
- **Files Analyzed**: 177 TypeScript/JavaScript files

Despite these issues, the core functionality works:
- ✅ Parser correctly identifies code entities
- ✅ Query interface functions properly
- ✅ Web server starts successfully
- ✅ Basic Cypher queries return results