#!/bin/bash

# CodeBased Setup Script for Unix/Linux/macOS
# This script automates the installation and setup of CodeBased

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PYTHON_MIN_VERSION="3.8"
CODEBASED_DIR=".codebased"

# Helper functions
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_python_version() {
    print_status "Checking Python version..."
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install Python 3.8 or higher."
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    required_version="3.8"
    
    if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
        print_success "Python $python_version found (>= $PYTHON_MIN_VERSION)"
    else
        print_error "Python version $python_version is too old. Please install Python $PYTHON_MIN_VERSION or higher."
        exit 1
    fi
}

check_pip() {
    print_status "Checking pip..."
    
    if ! python3 -m pip --version &> /dev/null; then
        print_error "pip is not available. Please install pip for Python 3."
        exit 1
    fi
    
    print_success "pip is available"
}

setup_virtual_environment() {
    print_status "Setting up virtual environment..."
    
    # Create venv inside .codebased directory
    VENV_PATH="$CODEBASED_DIR/venv"
    
    if [ ! -d "$VENV_PATH" ]; then
        python3 -m venv "$VENV_PATH"
        print_success "Virtual environment created at $VENV_PATH"
    else
        print_warning "Virtual environment already exists at $VENV_PATH"
    fi
    
    # Activate virtual environment
    source "$VENV_PATH/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip
    print_success "Virtual environment activated and pip upgraded"
}

install_dependencies() {
    print_status "Installing dependencies..."
    
    cd "$CODEBASED_DIR"
    
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        print_success "Dependencies installed from requirements.txt"
    else
        print_error "requirements.txt not found in $CODEBASED_DIR"
        exit 1
    fi
    
    # Install development dependencies if they exist
    if [ -f "requirements-dev.txt" ]; then
        pip install -r requirements-dev.txt
        print_success "Development dependencies installed"
    fi
    
    # Install CodeBased in development mode
    if [ -f "setup.py" ]; then
        pip install -e .
        print_success "CodeBased installed in development mode"
    else
        print_error "setup.py not found in $CODEBASED_DIR"
        exit 1
    fi
    
    cd ..
}

initialize_codebased() {
    print_status "Initializing CodeBased..."
    
    # Check if already initialized
    if [ -f ".codebased.yml" ]; then
        print_warning "CodeBased already initialized (.codebased.yml exists)"
        read -p "Do you want to reinitialize? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_status "Skipping initialization"
            return
        fi
    fi
    
    # Run initialization
    cd "$CODEBASED_DIR"
    python -m codebased.cli init --force
    cd ..
    
    print_success "CodeBased initialized"
}

run_tests() {
    print_status "Running installation tests..."
    
    cd "$CODEBASED_DIR"
    
    # Run quick test
    if python3 quick_test.py; then
        print_success "Quick tests passed"
    else
        print_warning "Quick tests failed, but installation may still work"
    fi
    
    # Run full test if dependencies are available
    if python3 test_installation.py 2>/dev/null; then
        print_success "Full installation test passed"
    else
        print_warning "Full installation test failed - some dependencies may be missing"
    fi
    
    cd ..
}

print_next_steps() {
    echo
    print_success "CodeBased setup completed!"
    echo
    echo "IMPORTANT: Everything is self-contained in the $CODEBASED_DIR directory:"
    echo "  - Virtual environment: $CODEBASED_DIR/venv"
    echo "  - Source code: $CODEBASED_DIR/src"
    echo "  - Database: $CODEBASED_DIR/data"
    echo "  - Web interface: $CODEBASED_DIR/web"
    echo
    echo "Next steps:"
    echo "  1. Activate the virtual environment:"
    echo "     source $CODEBASED_DIR/venv/bin/activate"
    echo
    echo "  2. Analyze your code:"
    echo "     codebased update"
    echo
    echo "  3. Start the web interface:"
    echo "     codebased serve"
    echo
    echo "  4. Open http://localhost:8000 in your browser"
    echo
    echo "NOTE: Always run CodeBased commands from your project root directory (this directory),"
    echo "      not from inside the $CODEBASED_DIR directory."
    echo
    echo "For help, run: codebased --help"
}

main() {
    echo "CodeBased Setup Script"
    echo "======================"
    echo
    
    # Check if we're running from inside .codebased directory
    if [ "$(basename "$PWD")" = ".codebased" ]; then
        print_error "You're running this script from inside the .codebased directory."
        print_error "Please run it from your project root directory instead:"
        print_error "  cd .."
        print_error "  ./.codebased/setup.sh"
        exit 1
    fi
    
    # Check if we're in the right directory
    if [ ! -d "$CODEBASED_DIR" ]; then
        print_error "This script must be run from the project root directory containing '$CODEBASED_DIR'"
        exit 1
    fi
    
    # Run setup steps
    check_python_version
    check_pip
    setup_virtual_environment
    install_dependencies
    initialize_codebased
    run_tests
    
    print_next_steps
}

# Handle script arguments
case "${1:-}" in
    --help|-h)
        echo "CodeBased Setup Script"
        echo
        echo "Usage: ./setup.sh [options]"
        echo
        echo "Options:"
        echo "  --help, -h     Show this help message"
        echo "  --skip-tests   Skip running tests after installation"
        echo "  --dev          Install development dependencies"
        echo
        echo "This script will:"
        echo "  1. Check Python version (>= 3.8)"
        echo "  2. Create and activate a virtual environment"
        echo "  3. Install CodeBased and dependencies"
        echo "  4. Initialize CodeBased in the current project"
        echo "  5. Run basic tests"
        exit 0
        ;;
    --skip-tests)
        SKIP_TESTS=true
        ;;
    --dev)
        INSTALL_DEV=true
        ;;
esac

# Run main function
main "$@"