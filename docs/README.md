# CodeBased Documentation Index

This directory contains all documentation for the CodeBased project. Here's where to start based on what you need:

## 🚀 Getting Started

1. **[QUICK_START.md](QUICK_START.md)** - Step-by-step guide with expected outputs
2. **[INSTALL.md](INSTALL.md)** - Detailed installation instructions and troubleshooting
3. **[README.md](../README.md)** - Project overview and features

## 📊 Working with Queries

1. **[QUERIES.md](QUERIES.md)** - **Start here!** Kuzu syntax basics, common patterns, and troubleshooting
2. **[../examples/QUERY_LIBRARY.md](../examples/QUERY_LIBRARY.md)** - Comprehensive library of advanced queries
3. **[../examples/query_templates.json](../examples/query_templates.json)** - Machine-readable query templates for tools

## 🔧 Configuration & Usage

- **[USAGE_GUIDE.md](USAGE_GUIDE.md)** - How to use CodeBased effectively
- **[../config/default.yml](../config/default.yml)** - Default configuration reference

## 🏗️ Architecture & Development

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and components
- **[API.md](API.md)** - API endpoints and usage
- **[JS-TS-Angular-Integration-Plan.md](JS-TS-Angular-Integration-Plan.md)** - JavaScript/TypeScript parser details

## ❓ Help & Troubleshooting

- **[FAQ.md](FAQ.md)** - Frequently asked questions
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions

## 📝 Important Notes

- **All queries use Kuzu's Cypher dialect** - See [QUERIES.md](QUERIES.md) for syntax differences
- **All entities use `file_path` property** - NOT `file_id` or `module_path`
- **Run commands from project root** - Never from inside `.codebased/` directory
- **Virtual environment lives in `.codebased/venv/`** - Not in project root

## 🔍 Quick Reference

### Finding Documentation by Task

| I want to... | Read this... |
|-------------|--------------|
| Install CodeBased | [QUICK_START.md](QUICK_START.md) or [INSTALL.md](INSTALL.md) |
| Write my first query | [QUERIES.md](QUERIES.md) |
| Find example queries | [QUERY_LIBRARY.md](../examples/QUERY_LIBRARY.md) |
| Fix an installation issue | [INSTALL.md](INSTALL.md#troubleshooting-installation) |
| Understand the architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Use the API | [API.md](API.md) |
| Debug query errors | [QUERIES.md](QUERIES.md#debugging-query-issues) |