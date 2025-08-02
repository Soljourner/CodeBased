#!/usr/bin/env python3
"""
Reparse the entire codebase with the fixed code.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.codebased.config import CodeBasedConfig
from src.codebased.database.service import DatabaseService
from src.codebased.database.schema import GraphSchema
from src.codebased.parsers.extractor import EntityExtractor

def reparse_codebase():
    """Reparse the entire codebase."""
    print("Reparsing CodeBased Codebase")
    print("=" * 60)
    
    # Initialize config
    config = CodeBasedConfig()
    
    # Initialize database service
    db_service = DatabaseService(config.database.path)
    
    # Clear existing data
    print("\n1. Clearing existing data...")
    db_service.clear_graph()
    
    # Initialize schema
    print("\n2. Initializing schema...")
    schema = GraphSchema(db_service)
    schema.create_schema()
    
    # Initialize extractor
    print("\n3. Initializing extractor...")
    extractor = EntityExtractor(config, db_service)
    
    # Parse the codebase
    print("\n4. Parsing codebase...")
    results = extractor.extract_from_directory('.')
    
    print(f"\n5. Results:")
    print(f"   Files processed: {results['files_processed']}")
    print(f"   Files failed: {results['files_failed']}")
    print(f"   Entities extracted: {results['entities_extracted']}")
    print(f"   Relationships extracted: {results['relationships_extracted']}")
    
    if results['errors']:
        print(f"\n   Errors:")
        for error in results['errors'][:5]:
            print(f"     - {error}")
        if len(results['errors']) > 5:
            print(f"     ... and {len(results['errors']) - 5} more")
    
    print("\n" + "=" * 60)
    print("Reparse complete!")


if __name__ == "__main__":
    reparse_codebase()