# CodeBased Tool Structure Analysis Report

## Executive Summary

CodeBased is designed as a **standalone tool** that should be installed globally or in its own location, then used to analyze target repositories. However, there are significant inconsistencies between the documentation, implementation, and actual usage patterns that need to be addressed.

## Key Findings

### 1. Installation Architecture

**Intended Design:**
- CodeBased is a standalone Python package installed via `pip install -e .`
- It provides a CLI command `codebased` that can be run from anywhere
- When run in a target repository, it creates a `.codebased/` directory containing:
  - Database files (`data/graph.kuzu`)
  - Web interface files (`web/`)
  - Configuration files
  - Logs

**Current State:**
- The tool is properly packaged with `setup.py` and entry points
- The CLI correctly creates `.codebased/` in the target repository when running `codebased init`
- No `.codebased/` directory exists in the CodeBased source repository itself (this is correct)

### 2. Workflow Analysis

**Correct Workflow:**

1. **Install CodeBased** (from its source directory):
   ```bash
   cd /workspace/codebased
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

2. **Use CodeBased in a target repository**:
   ```bash
   cd /workspace/appspace/Harvestor  # or any project to analyze
   codebased init                     # Creates .codebased/ directory here
   codebased update                   # Analyzes the code
   codebased serve                    # Starts the web interface
   ```

3. **Result Structure** in target repository:
   ```
   Harvestor/
   ├── .codebased.yml              # Configuration file
   ├── .codebased/                 # CodeBased data directory
   │   ├── data/                   # Database files
   │   │   └── graph.kuzu
   │   ├── web/                    # Web interface
   │   ├── config/                 # Additional configs
   │   └── logs/                   # Log files
   └── [original project files]
   ```

### 3. Script Analysis

**sync-to-harvestor.sh Purpose:**
- This is a **development testing script**, not part of the normal workflow
- It copies the CodeBased source code into Harvestor's `.codebased/` directory for testing
- This creates a non-standard setup where CodeBased runs from within the target repository
- Useful for development but should not be the recommended usage pattern

### 4. Documentation Discrepancies

**Issue 1: INSTALL.md Confusion**
- Line 15: `cd .codebased` - This is misleading as users should install from the CodeBased root
- The document seems to assume users are already in a `.codebased` directory
- It mixes installation of CodeBased itself with usage in a target project

**Issue 2: setup.sh Script**
- Line 87: `cd "$CODEBASED_DIR"` - Assumes running from a parent directory containing `.codebased`
- This script appears designed for a different architecture where `.codebased` contains the source

**Issue 3: README.md Clarity**
- The Quick Start section is correct and clear
- However, it doesn't emphasize that CodeBased should be installed separately first

### 5. Configuration File Analysis

**.codebased.yml in CodeBased root:**
- This appears to be for self-testing (analyzing CodeBased's own code)
- Not meant to be copied to target repositories
- Each target repository gets its own `.codebased.yml` via `codebased init`

## Recommendations

### 1. Documentation Updates

**INSTALL.md should be rewritten to:**
```markdown
# CodeBased Installation Guide

## Installing CodeBased

1. Clone or download CodeBased:
   ```bash
   git clone <codebased-repo>
   cd codebased
   ```

2. Create virtual environment and install:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -e .
   ```

3. Verify installation:
   ```bash
   codebased --version
   ```

## Using CodeBased in Your Project

1. Navigate to your project:
   ```bash
   cd /path/to/your/project
   ```

2. Initialize CodeBased:
   ```bash
   codebased init
   ```

3. Analyze your code:
   ```bash
   codebased update
   ```

4. View the graph:
   ```bash
   codebased serve
   ```
```

### 2. Script Updates

**setup.sh should be updated to:**
- Remove the assumption about `.codebased` directory
- Run from the CodeBased source root
- Focus on installing CodeBased itself, not initializing in a target

### 3. Development Workflow Documentation

Create a new `DEVELOPMENT.md` explaining:
- The sync-to-harvestor.sh script is for development testing only
- Normal users should install CodeBased globally and use the CLI
- How to test CodeBased changes on real projects

### 4. Clear Separation of Concerns

- **CodeBased source repository**: Contains the tool source code
- **Target repositories**: Where CodeBased analyzes code and creates `.codebased/` directories
- Never mix these two concepts in documentation

## Conclusion

CodeBased's architecture is sound - it's designed as a standalone tool that analyzes other repositories. The main issues are in the documentation and helper scripts that conflate installation of the tool with its usage. By clarifying this distinction and updating the documentation accordingly, the tool will be much easier for users to understand and adopt.

The sync-to-harvestor.sh script should be clearly marked as a development testing utility, not part of the standard workflow. This will prevent confusion about the intended usage pattern.