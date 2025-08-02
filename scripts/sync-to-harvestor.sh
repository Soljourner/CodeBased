#!/bin/bash
# Development-to-Testing Pipeline: Sync CodeBased to Harvestor for real-world testing

set -e

CODEBASED_ROOT="/workspace/codebased"
HARVESTOR_ROOT="/workspace/appspace/Harvestor"
HARVESTOR_CODEBASED="$HARVESTOR_ROOT/.codebased"

echo "🔄 CodeBased Development-to-Testing Pipeline"
echo "Source: $CODEBASED_ROOT"
echo "Target: $HARVESTOR_ROOT"

# Create .codebased directory in Harvestor if it doesn't exist
if [ ! -d "$HARVESTOR_CODEBASED" ]; then
    echo "📁 Creating .codebased directory in Harvestor"
    mkdir -p "$HARVESTOR_CODEBASED"
fi

# First, ensure we're not creating a nested structure
if [ -d "$HARVESTOR_CODEBASED/.codebased" ]; then
    echo "⚠️  Found nested .codebased directory, cleaning up..."
    rm -rf "$HARVESTOR_CODEBASED/.codebased"
fi

# Copy CodeBased source code
echo "📦 Copying CodeBased source code..."
rsync -av --delete \
    --exclude="venv" \
    --exclude="__pycache__" \
    --exclude="*.pyc" \
    --exclude=".git" \
    --exclude="data" \
    --exclude="web" \
    --exclude=".codebased" \
    "$CODEBASED_ROOT/src/" "$HARVESTOR_CODEBASED/src/"

# Copy requirements and setup files
echo "📋 Copying requirements and configuration..."
cp "$CODEBASED_ROOT/requirements.txt" "$HARVESTOR_CODEBASED/"
cp "$CODEBASED_ROOT/README.md" "$HARVESTOR_CODEBASED/" 2>/dev/null || echo "# CodeBased" > "$HARVESTOR_CODEBASED/README.md"
cp "$CODEBASED_ROOT/setup.py" "$HARVESTOR_CODEBASED/"

# Note: .codebased.yml should go in project root, not inside .codebased
if [ -f "$CODEBASED_ROOT/.codebased.yml" ]; then
    echo "📝 Note: Remember to copy .codebased.yml to your project root after setup"
fi

# Copy documentation
echo "📚 Copying relevant documentation..."
mkdir -p "$HARVESTOR_CODEBASED/docs"
cp "$CODEBASED_ROOT/docs/JS-TS-Angular-Integration-Plan.md" "$HARVESTOR_CODEBASED/docs/" 2>/dev/null || true
cp "$CODEBASED_ROOT/docs/performance-baseline.md" "$HARVESTOR_CODEBASED/docs/" 2>/dev/null || true

# Copy web interface files
echo "🌐 Copying web interface files..."
mkdir -p "$HARVESTOR_CODEBASED/web"
cp -r "$CODEBASED_ROOT/web/"* "$HARVESTOR_CODEBASED/web/" 2>/dev/null || true

# Create or update virtual environment inside .codebased
echo "🐍 Setting up Python environment in Harvestor..."
cd "$HARVESTOR_CODEBASED"

if [ ! -d "venv" ]; then
    echo "Creating new virtual environment inside .codebased..."
    python3 -m venv venv
fi

# Activate the venv from .codebased directory
source venv/bin/activate

# Install requirements
echo "📦 Installing Python dependencies..."
pip install -r requirements.txt

# Install CodeBased in development mode
echo "⚙️  Installing CodeBased in development mode..."
pip install -e .

# Create test configuration for Harvestor
echo "🔧 Creating test configuration..."
cat > "$HARVESTOR_CODEBASED/.codebased-test.yml" << EOF
# CodeBased Test Configuration for Harvestor
project:
  name: "Harvestor"
  path: "$HARVESTOR_ROOT"
  
database:
  path: "$HARVESTOR_CODEBASED/data/harvestor_graph.db"
  
output:
  kuzu_path: "$HARVESTOR_CODEBASED/data/graph.cypher"
  json_path: "$HARVESTOR_CODEBASED/data/graph.json"
  
parsers:
  typescript:
    enabled: true
    include_patterns: ["*.ts", "*.tsx"]
    exclude_patterns: ["node_modules/**", "dist/**", "*.d.ts"]
  
  javascript:
    enabled: true
    include_patterns: ["*.js", "*.jsx"]
    exclude_patterns: ["node_modules/**", "dist/**"]
    
  angular:
    enabled: true
    detect_components: true
    detect_services: true
    connect_templates: true

web:
  static_path: "$HARVESTOR_CODEBASED/web"
  
logging:
  level: "INFO"
  file: "$HARVESTOR_CODEBASED/logs/codebased.log"
EOF

# Create data and logs directories
mkdir -p "$HARVESTOR_CODEBASED/data"
mkdir -p "$HARVESTOR_CODEBASED/logs"

# Create test script
echo "📝 Creating test script..."
cat > "$HARVESTOR_CODEBASED/test-codebased.sh" << 'EOF'
#!/bin/bash
# Test CodeBased on Harvestor project

cd "$(dirname "$0")"
source venv/bin/activate

echo "🧪 Testing CodeBased on Harvestor project..."

# Test TypeScript parsing on backend
echo "📄 Testing TypeScript parsing (backend)..."
python -c "
from src.codebased.parsers.typescript import TypeScriptParser
import time

parser = TypeScriptParser()
test_file = '../apps/backend/src/controllers/auth.controller.ts'

try:
    start_time = time.time()
    result = parser.parse_file(test_file)
    parse_time = time.time() - start_time
    
    print(f'✅ TypeScript parsing successful:')
    print(f'   File: {test_file}')
    print(f'   Parse time: {parse_time*1000:.1f}ms')
    print(f'   Entities: {len(result.entities)}')
    print(f'   Relationships: {len(result.relationships)}')
    
    # Show entity types
    entity_types = {}
    for entity in result.entities:
        entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
    print(f'   Entity types: {entity_types}')
    
except Exception as e:
    print(f'❌ TypeScript parsing failed: {e}')
    import traceback
    traceback.print_exc()
"

# Test Angular parsing on frontend
echo "📱 Testing Angular parsing (frontend)..."
python -c "
from src.codebased.parsers.typescript import TypeScriptParser
import time

parser = TypeScriptParser()
test_file = '../apps/frontend/src/app/app.component.ts'

try:
    start_time = time.time()
    result = parser.parse_file(test_file)
    parse_time = time.time() - start_time
    
    print(f'✅ Angular component parsing successful:')
    print(f'   File: {test_file}')
    print(f'   Parse time: {parse_time*1000:.1f}ms')
    print(f'   Entities: {len(result.entities)}')
    print(f'   Relationships: {len(result.relationships)}')
    
    # Show entity types
    entity_types = {}
    for entity in result.entities:
        entity_types[entity.type] = entity_types.get(entity.type, 0) + 1
    print(f'   Entity types: {entity_types}')
    
except Exception as e:
    print(f'❌ Angular parsing failed: {e}')
    import traceback
    traceback.print_exc()
"

echo "🎯 CodeBased testing complete!"
EOF

chmod +x "$HARVESTOR_CODEBASED/test-codebased.sh"

echo "✅ Development-to-Testing Pipeline Setup Complete!"
echo ""
echo "📍 Next Steps:"
echo "1. cd $HARVESTOR_ROOT"
echo "2. Copy config to project root: cp $HARVESTOR_CODEBASED/.codebased-test.yml .codebased.yml"
echo "3. Activate virtual environment: source $HARVESTOR_CODEBASED/venv/bin/activate"
echo "4. Initialize: codebased init"
echo "5. Update: codebased update"
echo ""
echo "📁 Files installed in:"
echo "   • Source code: $HARVESTOR_CODEBASED/src/"
echo "   • Virtual environment: $HARVESTOR_CODEBASED/venv/"
echo "   • Configuration template: $HARVESTOR_CODEBASED/.codebased-test.yml"
echo ""
echo "⚠️  Remember: Always run CodeBased commands from $HARVESTOR_ROOT, not from inside .codebased/"