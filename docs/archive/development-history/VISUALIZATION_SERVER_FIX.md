# CodeBased Visualization Server Issue - Analysis and Fix

**Date**: 2025-08-02  
**Issue**: Web interface returns 404 when running `codebased serve`  
**Root Cause**: Path resolution issue when running from inside `.codebased` directory  

## Problem Description

When running `codebased serve` from the Harvestor project, the server starts but returns 404 errors for all requests. The error log shows:

```
2025-08-01 22:19:16 - codebased.api.main - WARNING - Static files directory not found: /workspace/appspace/Harvestor/.codebased/.codebased/web
```

The path contains a duplicated `.codebased` directory.

## Root Cause Analysis

The issue occurs because:

1. CodeBased is installed in `/workspace/appspace/Harvestor/.codebased/`
2. When running from this directory, the configuration loader sets `project_root` to the current directory
3. The `static_path` in config is `.codebased/web`
4. This gets resolved relative to project_root, resulting in `.codebased/.codebased/web`

## Immediate Workaround

Run `codebased serve` from the actual project root (Harvestor directory):

```bash
cd /workspace/appspace/Harvestor
source .codebased/venv/bin/activate
codebased serve
```

**Note**: The fix in Option 2 has been implemented in the codebase. The configuration loader now detects when running from inside `.codebased` directory and uses the parent directory as the project root.

## Permanent Fix

### Option 1: Update Configuration (Recommended)

Edit `.codebased.yml` to use absolute paths or correct relative paths:

```yaml
web:
  static_path: web  # Instead of .codebased/web
  template_path: web/templates
```

### Option 2: Fix Config Loading Logic

Update `src/codebased/config.py` to detect when running from inside `.codebased` directory:

```python
def from_file(cls, config_path: str) -> 'CodeBasedConfig':
    """Load configuration from YAML file."""
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        config_dir = config_path.parent.resolve()
        
        # Check if we're running from inside .codebased directory
        if config_dir.name == '.codebased' and config_dir.parent.exists():
            # Use parent directory as project root
            actual_project_root = config_dir.parent
        else:
            actual_project_root = config_dir
        
        with open(config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f) or {}
        
        # Create config with defaults
        config = cls()
        
        # Set project root
        if 'project_root' in data:
            project_root = Path(data['project_root'])
            if not project_root.is_absolute():
                project_root = (actual_project_root / project_root).resolve()
            config.project_root = str(project_root)
        else:
            config.project_root = str(actual_project_root)
```

### Option 3: Update CLI to Set Working Directory

Modify `src/codebased/cli.py` to ensure commands run from the project root:

```python
@main.command()
@click.option('--host', default='localhost', help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def serve(ctx, host, port, reload, debug):
    """Start the web interface server."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Change to project root directory
        import os
        os.chdir(config.project_root)
        
        # Rest of the serve command...
```

## Testing the Fix

After applying any of the fixes above:

1. Navigate to the project root
2. Activate the virtual environment
3. Run `codebased serve`
4. Open http://localhost:8000 in a browser
5. Verify the visualization loads correctly

## Prevention

To prevent this issue in future installations:

1. Always run CodeBased commands from the project root directory
2. Use explicit paths in configuration files
3. Add path validation in the config loader
4. Document the expected directory structure clearly

## Related Files

- `/workspace/codebased/src/codebased/config.py` - Configuration loading logic
- `/workspace/codebased/src/codebased/api/main.py` - FastAPI static file mounting
- `/workspace/codebased/src/codebased/cli.py` - CLI command implementations
- `.codebased.yml` - Project configuration file

## Troubleshooting

If the server still returns 404 after applying the fix:

1. **Check the web files exist**:
   ```bash
   ls -la .codebased/web/
   ```
   Should show: index.html, app.js, graph.js, style.css, etc.

2. **Verify the configuration**:
   ```bash
   cat .codebased.yml | grep static_path
   ```
   Should show: `static_path: .codebased/web`

3. **Check server logs**:
   Look for warnings about static files directory not found

4. **Try running with debug mode**:
   ```bash
   codebased serve --debug
   ```

5. **Check if port is already in use**:
   ```bash
   lsof -i :8000
   ```
   If occupied, use a different port:
   ```bash
   codebased serve --port 8001
   ```

## References

- [FastAPI Static Files Documentation](https://fastapi.tiangolo.com/tutorial/static-files/)
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html)