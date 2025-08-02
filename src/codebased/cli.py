"""
Command-line interface for CodeBased.
"""

import os
import sys
import logging
import subprocess
from pathlib import Path
from typing import Optional

import click
import uvicorn

from .config import get_config, create_default_config
from .database.service import get_database_service
from .database.schema import GraphSchema
from .parsers.incremental import IncrementalUpdater


def setup_logging(level: str = "INFO"):
    """Setup logging configuration."""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


@click.group(invoke_without_command=True)
@click.option('--config', '-c', default='.codebased.yml', help='Configuration file path')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging')
@click.option('--version', is_flag=True, help='Show version and exit')
@click.pass_context
def main(ctx, config: str, verbose: bool, version: bool):
    """CodeBased - A lightweight code graph generator and visualization tool."""
    
    if version:
        click.echo("CodeBased 0.1.0")
        return
    
    # Setup context
    ctx.ensure_object(dict)
    ctx.obj['config_path'] = config
    ctx.obj['verbose'] = verbose
    
    # Setup logging
    setup_logging("DEBUG" if verbose else "INFO")
    
    # If no subcommand is provided, show help
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
@click.pass_context
def init(ctx, force: bool):
    """Initialize CodeBased in the current directory."""
    config_path = ctx.obj['config_path']
    
    try:
        # Check if already initialized
        if Path(config_path).exists() and not force:
            click.echo(f"CodeBased already initialized. Use --force to overwrite.")
            return
        
        # Create directory structure
        base_dir = Path('.codebased')
        directories = [
            base_dir,
            base_dir / 'data',
            base_dir / 'web',
            base_dir / 'config',
            base_dir / 'logs'
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            click.echo(f"Created directory: {directory}")
        
        # Create default configuration
        config = create_default_config(config_path)
        click.echo(f"Created configuration file: {config_path}")
        
        # Initialize database and schema
        db_service = get_database_service(config.database.path)
        if not db_service.initialize():
            click.echo("Error: Failed to initialize database", err=True)
            return
        
        schema = GraphSchema(db_service)
        if not schema.create_schema():
            click.echo("Error: Failed to create database schema", err=True)
            return
        
        click.echo("Database initialized successfully")
        
        # Create basic web files
        web_dir = Path(config.web.static_path)
        web_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a simple index.html placeholder
        index_html = web_dir / 'index.html'
        if not index_html.exists():
            index_html.write_text("""<!DOCTYPE html>
<html>
<head>
    <title>CodeBased</title>
</head>
<body>
    <h1>CodeBased</h1>
    <p>Code graph visualization will be available here.</p>
    <p>API documentation: <a href="/docs">/docs</a></p>
</body>
</html>""")
            click.echo(f"Created web interface: {index_html}")
        
        click.echo("")
        click.echo("✅ CodeBased initialized successfully!")
        click.echo("")
        click.echo("Next steps:")
        click.echo("1. Run 'codebased update' to analyze your code")
        click.echo("2. Run 'codebased serve' to start the web interface")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--full', is_flag=True, help='Force full rebuild instead of incremental')
@click.option('--path', help='Directory to update (defaults to current directory)')
@click.pass_context
def update(ctx, full: bool, path: Optional[str]):
    """Update the code graph."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Initialize database service
        db_service = get_database_service(config.database.path)
        if not db_service.connect():
            click.echo("Error: Could not connect to database", err=True)
            return
        
        # Create updater
        updater = IncrementalUpdater(config, db_service)
        
        # Perform update
        click.echo("Starting code graph update...")
        
        if full:
            click.echo("Performing full rebuild...")
            results = updater.force_full_update(path)
        else:
            click.echo("Performing incremental update...")
            results = updater.update_graph(path)
        
        # Display results
        click.echo("")
        click.echo("Update Results:")
        click.echo(f"  Files processed: {results.get('files_added', 0) + results.get('files_modified', 0)}")
        click.echo(f"  Files added: {results.get('files_added', 0)}")
        click.echo(f"  Files modified: {results.get('files_modified', 0)}")
        click.echo(f"  Files removed: {results.get('files_removed', 0)}")
        click.echo(f"  Entities: {results.get('entities_added', 0)} added, {results.get('entities_removed', 0)} removed")
        click.echo(f"  Relationships: {results.get('relationships_added', 0)} added, {results.get('relationships_removed', 0)} removed")
        click.echo(f"  Update time: {results.get('update_time', 0):.2f}s")
        
        if results.get('errors'):
            click.echo("")
            click.echo("Errors encountered:")
            for error in results['errors']:
                click.echo(f"  - {error}", err=True)
        
        if not results.get('errors'):
            click.echo("")
            click.echo("✅ Update completed successfully!")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.option('--host', help='Host to bind to (overrides config)')
@click.option('--port', type=int, help='Port to bind to (overrides config)')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
@click.option('--debug', is_flag=True, help='Enable debug mode')
@click.pass_context
def serve(ctx, host: Optional[str], port: Optional[int], reload: bool, debug: bool):
    """Start the API and web server."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Override config with CLI options
        if host:
            config.api.host = host
        if port:
            config.api.port = port
        if reload:
            config.api.reload = reload
        if debug:
            config.api.debug = debug
        
        click.echo(f"Starting server at http://{config.api.host}:{config.api.port}")
        click.echo("Press Ctrl+C to stop")
        
        # Start uvicorn server
        uvicorn.run(
            "codebased.api.main:app",
            host=config.api.host,
            port=config.api.port,
            reload=config.api.reload,
            log_level="debug" if config.api.debug else "info"
        )
        
    except KeyboardInterrupt:
        click.echo("\nServer stopped")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument('query', required=True)
@click.option('--format', 'output_format', default='table', type=click.Choice(['table', 'json', 'csv']), 
              help='Output format')
@click.option('--limit', type=int, default=100, help='Limit number of results')
@click.pass_context
def query(ctx, query: str, output_format: str, limit: int):
    """Execute a Cypher query against the graph."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Initialize database service
        db_service = get_database_service(config.database.path)
        if not db_service.connect():
            click.echo("Error: Could not connect to database", err=True)
            return
        
        # Add limit to query if not present
        if 'LIMIT' not in query.upper():
            query = f"{query} LIMIT {limit}"
        
        # Execute query
        results = db_service.execute_query(query)
        
        if results is None:
            click.echo("Query execution failed", err=True)
            return
        
        if not results:
            click.echo("No results found")
            return
        
        # Format output
        if output_format == 'json':
            import json
            click.echo(json.dumps(results, indent=2, default=str))
        elif output_format == 'csv':
            import csv
            import io
            
            if results:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=results[0].keys())
                writer.writeheader()
                writer.writerows(results)
                click.echo(output.getvalue().strip())
        else:  # table format
            if results:
                # Simple table formatting
                headers = list(results[0].keys())
                
                # Calculate column widths
                widths = {header: len(header) for header in headers}
                for row in results:
                    for header in headers:
                        value_len = len(str(row.get(header, '')))
                        if value_len > widths[header]:
                            widths[header] = min(value_len, 50)  # Max width 50
                
                # Print table
                header_row = ' | '.join(header.ljust(widths[header]) for header in headers)
                separator = '-+-'.join('-' * widths[header] for header in headers)
                
                click.echo(header_row)
                click.echo(separator)
                
                for row in results:
                    row_data = []
                    for header in headers:
                        value = str(row.get(header, ''))
                        if len(value) > 50:
                            value = value[:47] + '...'
                        row_data.append(value.ljust(widths[header]))
                    click.echo(' | '.join(row_data))
        
        click.echo(f"\n{len(results)} rows returned")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def status(ctx):
    """Show system status and statistics."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Initialize database service
        db_service = get_database_service(config.database.path)
        
        # Get database health
        health = db_service.health_check()
        
        click.echo("CodeBased Status")
        click.echo("================")
        click.echo(f"Project root: {config.project_root}")
        click.echo(f"Database path: {config.database.path}")
        click.echo(f"Database status: {health['status']}")
        
        if health['db_exists']:
            stats = db_service.get_stats()
            click.echo(f"Nodes: {stats.get('nodes', 0)}")
            click.echo(f"Relationships: {stats.get('relationships', 0)}")
            click.echo(f"Tables: {stats.get('tables', 0)}")
        
        # Get update status
        updater = IncrementalUpdater(config, db_service)
        update_status = updater.get_update_status()
        
        click.echo(f"Tracked files: {update_status.get('tracked_files', 0)}")
        
        if health['status'] == 'healthy':
            click.echo("\n✅ System is healthy")
        else:
            click.echo(f"\n❌ System status: {health['status']}")
            if 'error' in health:
                click.echo(f"Error: {health['error']}")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.confirmation_option(prompt='Are you sure you want to reset the database?')
@click.pass_context
def reset(ctx):
    """Reset the database (destructive operation)."""
    config_path = ctx.obj['config_path']
    
    try:
        # Load configuration
        config = get_config(config_path)
        
        # Initialize database service
        db_service = get_database_service(config.database.path)
        if not db_service.connect():
            click.echo("Error: Could not connect to database", err=True)
            return
        
        # Reset schema
        schema = GraphSchema(db_service)
        if not schema.reset_schema():
            click.echo("Error: Failed to reset database schema", err=True)
            return
        
        click.echo("✅ Database reset successfully")
        click.echo("Run 'codebased update' to rebuild the graph")
        
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.pass_context
def doctor(ctx):
    """Check CodeBased installation and configuration health."""
    config_path = ctx.obj['config_path']
    issues_found = False
    
    click.echo("🔍 CodeBased Doctor - Checking installation health...")
    click.echo()
    
    # Check 1: Current working directory
    cwd = os.getcwd()
    if os.path.basename(cwd) == '.codebased':
        click.echo("❌ Working Directory Issue:")
        click.echo("   You're currently inside the .codebased directory.")
        click.echo("   Fix: cd ..")
        issues_found = True
    else:
        click.echo("✅ Working directory: Correct (project root)")
    
    # Check 2: Virtual environment location
    venv_in_root = os.path.exists('venv')
    venv_in_codebased = os.path.exists('.codebased/venv')
    
    if venv_in_root and not venv_in_codebased:
        click.echo("⚠️  Virtual Environment Issue:")
        click.echo("   Virtual environment found in project root instead of .codebased/")
        click.echo("   Fix: rm -rf venv && python3 -m venv .codebased/venv")
        issues_found = True
    elif venv_in_codebased:
        click.echo("✅ Virtual environment: Correct location (.codebased/venv)")
    else:
        click.echo("❌ Virtual Environment Issue:")
        click.echo("   No virtual environment found")
        click.echo("   Fix: python3 -m venv .codebased/venv")
        issues_found = True
    
    # Check 3: Active virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        venv_path = sys.prefix
        if '.codebased/venv' in venv_path:
            click.echo("✅ Active virtual environment: Correct")
        else:
            click.echo("⚠️  Active virtual environment: Wrong location")
            click.echo(f"   Currently using: {venv_path}")
            click.echo("   Fix: deactivate && source .codebased/venv/bin/activate")
            issues_found = True
    else:
        click.echo("❌ Virtual Environment Issue:")
        click.echo("   No virtual environment activated")
        click.echo("   Fix: source .codebased/venv/bin/activate")
        issues_found = True
    
    # Check 4: Configuration file location
    config_in_root = os.path.exists('.codebased.yml')
    config_in_codebased = os.path.exists('.codebased/.codebased.yml')
    
    if config_in_codebased and not config_in_root:
        click.echo("❌ Configuration File Issue:")
        click.echo("   .codebased.yml found inside .codebased/ directory")
        click.echo("   Fix: mv .codebased/.codebased.yml .codebased.yml")
        issues_found = True
    elif config_in_root:
        click.echo("✅ Configuration file: Correct location (project root)")
    else:
        click.echo("❌ Configuration File Issue:")
        click.echo("   No .codebased.yml found")
        click.echo("   Fix: codebased init")
        issues_found = True
    
    # Check 5: CodeBased directory structure
    required_dirs = ['.codebased', '.codebased/data', '.codebased/web', '.codebased/src']
    for dir_path in required_dirs:
        if not os.path.exists(dir_path):
            click.echo(f"❌ Directory Structure Issue:")
            click.echo(f"   Missing directory: {dir_path}")
            click.echo(f"   Fix: mkdir -p {dir_path}")
            issues_found = True
    
    if all(os.path.exists(d) for d in required_dirs):
        click.echo("✅ Directory structure: Complete")
    
    # Check 6: Database initialization
    db_path = '.codebased/data/graph.kuzu'
    if os.path.exists(db_path):
        click.echo("✅ Database: Initialized")
    else:
        click.echo("❌ Database Issue:")
        click.echo("   Database not initialized")
        click.echo("   Fix: codebased init")
        issues_found = True
    
    # Check 7: Duplicate .codebased directories
    nested_codebased = os.path.exists('.codebased/.codebased')
    if nested_codebased:
        click.echo("❌ Directory Structure Issue:")
        click.echo("   Nested .codebased directory found")
        click.echo("   Fix: rm -rf .codebased/.codebased")
        issues_found = True
    
    # Check 8: CodeBased installation
    try:
        import codebased
        click.echo("✅ CodeBased module: Installed")
    except ImportError:
        click.echo("❌ Installation Issue:")
        click.echo("   CodeBased module not found")
        click.echo("   Fix: pip install -e .codebased/")
        issues_found = True
    
    click.echo()
    if issues_found:
        click.echo("🔧 Issues found! Please run the suggested fixes above.")
        sys.exit(1)
    else:
        click.echo("✨ All checks passed! CodeBased is properly installed.")


if __name__ == '__main__':
    main()