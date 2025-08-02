# CodeBased Quick Start Guide

This guide provides a step-by-step walkthrough to get CodeBased up and running quickly, with expected outputs and verification steps at each stage.

## 🎯 Goal

By the end of this guide, you'll have:
- ✅ CodeBased installed and configured
- ✅ Your codebase analyzed and stored in the graph database
- ✅ Web visualization running and accessible
- ✅ Confidence that everything is working correctly

## 📋 Prerequisites Check

Before starting, verify you have:

```bash
# Check Python version (need 3.8+)
python3 --version
# Expected: Python 3.8.x or higher

# Check pip is available
python3 -m pip --version
# Expected: pip 20.x.x or higher

# Check current directory (should be your project root)
pwd
# Expected: /path/to/your/project (NOT ending with .codebased)
```

## 🚀 Step 1: Initial Setup

### Option A: Using the setup script (Recommended)

```bash
# Make the setup script executable
chmod +x setup.sh

# Run the setup script
./setup.sh
```

**Expected output:**
```
🚀 CodeBased Setup Script
========================
✅ Python 3.8+ detected
📁 Creating .codebased directory structure...
✅ Created: .codebased/
✅ Created: .codebased/data/
✅ Created: .codebased/web/
✅ Created: .codebased/logs/
🐍 Setting up virtual environment...
✅ Virtual environment created at .codebased/venv
📦 Installing dependencies...
✅ Dependencies installed successfully
🔧 Running tests...
✅ All tests passed
✨ Setup complete!
```

### Option B: Manual setup

```bash
# Create .codebased directory structure
mkdir -p .codebased/{data,web,logs,src}

# Create virtual environment INSIDE .codebased
python3 -m venv .codebased/venv

# Activate it
source .codebased/venv/bin/activate

# Your prompt should now show (venv)
# Expected: (venv) user@host:~/project$
```

## 🔍 Step 2: Verify Virtual Environment

**Critical**: Make sure you're using the correct virtual environment!

```bash
# Check which Python you're using
which python
# Expected: /path/to/project/.codebased/venv/bin/python

# Check pip location
which pip
# Expected: /path/to/project/.codebased/venv/bin/pip

# If you see system paths like /usr/bin/python, activate the venv:
source .codebased/venv/bin/activate
```

## 📦 Step 3: Install CodeBased

```bash
# Make sure you're in project root (NOT inside .codebased)
pwd
# Expected: /path/to/your/project

# Install CodeBased
cd .codebased
pip install -r requirements.txt
pip install -e .
cd ..

# Verify installation
codebased --version
# Expected: CodeBased 0.1.0
```

## 🏗️ Step 4: Initialize CodeBased

```bash
# Initialize CodeBased (from project root!)
codebased init
```

**Expected output:**
```
Created directory: .codebased
Created directory: .codebased/data
Created directory: .codebased/web
Created directory: .codebased/config
Created directory: .codebased/logs
Created configuration file: .codebased.yml
Database initialized successfully
Created web interface: .codebased/web/index.html

✅ CodeBased initialized successfully!

Next steps:
1. Run 'codebased update' to analyze your code
2. Run 'codebased serve' to start the web interface
```

## ✅ Step 5: Run Health Check

```bash
# Run the doctor command to verify installation
codebased doctor
```

**Expected output:**
```
🔍 CodeBased Doctor - Checking installation health...

✅ Working directory: Correct (project root)
✅ Virtual environment: Correct location (.codebased/venv)
✅ Active virtual environment: Correct
✅ Configuration file: Correct location (project root)
✅ Directory structure: Complete
✅ Database: Initialized
✅ CodeBased module: Installed

✨ All checks passed! CodeBased is properly installed.
```

**If you see any ❌ marks**, follow the suggested fixes before continuing.

## 📊 Step 6: Analyze Your Code

```bash
# Update the graph with your codebase
codebased update
```

**Expected output (example for a Python project):**
```
Starting code graph update...
Performing incremental update...

Update Results:
  Files processed: 15
  Files added: 15
  Files modified: 0
  Files removed: 0
  Entities: 47 added, 0 removed
  Relationships: 23 added, 0 removed
  Update time: 2.34s

✅ Update completed successfully!
```

### Verify the update worked:

```bash
# Check database status
codebased status
```

**Expected output:**
```
CodeBased Status
================
Project root: /path/to/your/project
Database path: .codebased/data/graph.kuzu
Database status: healthy
Nodes: 47
Relationships: 23
Tables: 4
Tracked files: 15

✅ System is healthy
```

## 🌐 Step 7: Start the Web Interface

```bash
# Start the server
codebased serve
```

**Expected output:**
```
Starting server at http://127.0.0.1:8000
Press Ctrl+C to stop
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

### Verify the server is running:

1. Open your browser to http://localhost:8000
2. You should see the CodeBased web interface
3. Click on "Graph Visualization" to see your code structure

## 🧪 Step 8: Test Basic Queries

```bash
# In a new terminal (keep server running), activate venv first
source .codebased/venv/bin/activate

# List all files
codebased query "MATCH (f:File) RETURN f.path LIMIT 5"
```

**Expected output:**
```
path                          
------------------------------
/src/main.py                  
/src/utils.py                 
/src/models/user.py           
/src/models/product.py        
/src/api/endpoints.py         

5 rows returned
```

## 🎉 Success Checklist

If you've completed all steps successfully, you should have:

- [x] `.codebased/` directory with proper structure
- [x] Virtual environment at `.codebased/venv/`
- [x] Configuration file `.codebased.yml` in project root
- [x] Database at `.codebased/data/graph.kuzu`
- [x] `codebased doctor` showing all green checks
- [x] `codebased status` showing nodes and relationships
- [x] Web interface accessible at http://localhost:8000
- [x] Queries returning results

## 🚨 Common Issues & Quick Fixes

### "codebased: command not found"
```bash
# You forgot to activate the virtual environment
source .codebased/venv/bin/activate
```

### "Configuration file not found"
```bash
# You're in the wrong directory
cd /path/to/your/project  # Go to project root
pwd  # Should NOT end with /.codebased
```

### "Table X does not exist"
```bash
# Database not initialized properly
codebased init --force
codebased update
```

### Web interface shows no data
```bash
# Graph not updated
codebased update
# Then refresh your browser
```

## 📚 Next Steps

Now that CodeBased is running:

1. **Explore the visualization**: Open http://localhost:8000 and interact with your code graph
2. **Try advanced queries**: See [QUERIES.md](QUERIES.md) for examples
3. **Configure parsing**: Edit `.codebased.yml` to include/exclude files
4. **Set up auto-update**: Use file watchers for real-time updates

## 🆘 Still Having Issues?

1. Run `codebased doctor` and fix any reported issues
2. Check logs: `cat .codebased/logs/codebased.log`
3. Verify you're in the project root: `pwd`
4. Ensure virtual environment is activated: `which python`
5. See [INSTALL.md](INSTALL.md) for detailed troubleshooting

## 💡 Pro Tips

- **Always** run CodeBased commands from your project root
- **Always** activate the virtual environment before using CodeBased
- **Never** cd into `.codebased/` to run commands
- Keep `.codebased.yml` in your project root, not inside `.codebased/`
- Use `codebased doctor` whenever something seems wrong

---

🎯 **Remember**: CodeBased is self-contained in `.codebased/` - everything stays organized in one place!