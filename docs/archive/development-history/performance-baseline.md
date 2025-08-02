# CodeBased Performance Baseline

**Date**: 2025-01-26  
**Purpose**: Establish baseline performance metrics before JS/TS/Angular integration  
**Environment**: Docker container, Python 3.11.2

## Python Parser Baseline Results

**Test Setup**:
- 10 Python files from `src/` directory
- Average file size: ~9.3KB
- Using PythonASTParser

**Performance Metrics**:
- **Average parse time**: 5.0ms per file
- **Entities per file**: 34.3 average
- **Relationships per file**: 94.2 average
- **Total files processed**: 10

**Detailed Results**:
```
src/codebased/cli.py: 7.9ms, 13531 bytes, 68 entities
src/codebased/config.py: 5.2ms, 12957 bytes, 57 entities
src/codebased/__init__.py: 2.4ms, 157 bytes, 2 entities
src/codebased/api/endpoints.py: 8.0ms, 20011 bytes, 82 entities
src/codebased/api/main.py: 4.0ms, 4738 bytes, 33 entities
src/codebased/api/models.py: 5.7ms, 5444 bytes, 22 entities
src/codebased/api/__init__.py: 3.9ms, 66 bytes, 2 entities
src/codebased/database/schema.py: 4.7ms, 11630 bytes, 28 entities
src/codebased/database/service.py: 5.4ms, 9768 bytes, 47 entities
src/codebased/database/__init__.py: 3.3ms, 54 bytes, 2 entities
```

## Target Performance for JS/TS

Based on baseline, targets for new parsers:
- **TypeScript/JavaScript**: <10ms per file (2x Python baseline)
- **Entities extracted**: Maintain similar density (~30-40 per file)
- **Relationships**: Achieve similar ratio (~90-100 per file)

## Backup Information

- **Backup branch**: `backup/pre-js-ts-integration`
- **Tree-sitter version**: 0.21.3 (confirmed working)
- **Dependencies**: All requirements.txt packages installed and verified

## Rollback Procedure

1. Switch to backup branch: `git checkout backup/pre-js-ts-integration`
2. Reset to clean state: `git reset --hard HEAD`
3. Reinstall dependencies: `pip install -r requirements.txt`
4. Verify functionality: Run existing Python parser tests