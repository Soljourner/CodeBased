# CodeBased Setup Script for Windows PowerShell
# This script automates the installation and setup of CodeBased

param(
    [switch]$SkipTests,
    [switch]$Dev,
    [switch]$Help
)

# Configuration
$PythonMinVersion = [Version]"3.8.0"
$CodeBasedDir = ".codebased"

# Helper functions
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Blue
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

function Test-PythonVersion {
    Write-Status "Checking Python version..."
    
    try {
        $pythonVersion = python --version 2>$null
        if (-not $pythonVersion) {
            $pythonVersion = python3 --version 2>$null
        }
        
        if (-not $pythonVersion) {
            Write-Error "Python is not installed or not in PATH. Please install Python 3.8 or higher."
            exit 1
        }
        
        $versionString = $pythonVersion -replace "Python ", ""
        $version = [Version]$versionString
        
        if ($version -ge $PythonMinVersion) {
            Write-Success "Python $versionString found (>= $PythonMinVersion)"
            return $true
        } else {
            Write-Error "Python version $versionString is too old. Please install Python $PythonMinVersion or higher."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to check Python version: $($_.Exception.Message)"
        exit 1
    }
}

function Test-Pip {
    Write-Status "Checking pip..."
    
    try {
        $pipVersion = python -m pip --version 2>$null
        if (-not $pipVersion) {
            $pipVersion = python3 -m pip --version 2>$null
        }
        
        if ($pipVersion) {
            Write-Success "pip is available"
            return $true
        } else {
            Write-Error "pip is not available. Please install pip for Python."
            exit 1
        }
    }
    catch {
        Write-Error "Failed to check pip: $($_.Exception.Message)"
        exit 1
    }
}

function Set-VirtualEnvironment {
    Write-Status "Setting up virtual environment..."
    
    if (-not (Test-Path "venv")) {
        python -m venv venv
        Write-Success "Virtual environment created"
    } else {
        Write-Warning "Virtual environment already exists"
    }
    
    # Activate virtual environment
    & "venv\Scripts\Activate.ps1"
    
    # Upgrade pip
    python -m pip install --upgrade pip
    Write-Success "Virtual environment activated and pip upgraded"
}

function Install-Dependencies {
    Write-Status "Installing dependencies..."
    
    Push-Location $CodeBasedDir
    
    try {
        if (Test-Path "requirements.txt") {
            python -m pip install -r requirements.txt
            Write-Success "Dependencies installed from requirements.txt"
        } else {
            Write-Error "requirements.txt not found in $CodeBasedDir"
            exit 1
        }
        
        # Install development dependencies if they exist
        if ((Test-Path "requirements-dev.txt") -and $Dev) {
            python -m pip install -r requirements-dev.txt
            Write-Success "Development dependencies installed"
        }
        
        # Install CodeBased in development mode
        if (Test-Path "setup.py") {
            python -m pip install -e .
            Write-Success "CodeBased installed in development mode"
        } else {
            Write-Error "setup.py not found in $CodeBasedDir"
            exit 1
        }
    }
    finally {
        Pop-Location
    }
}

function Initialize-CodeBased {
    Write-Status "Initializing CodeBased..."
    
    # Check if already initialized
    if (Test-Path ".codebased.yml") {
        Write-Warning "CodeBased already initialized (.codebased.yml exists)"
        $response = Read-Host "Do you want to reinitialize? (y/N)"
        if ($response -ne "y" -and $response -ne "Y") {
            Write-Status "Skipping initialization"
            return
        }
    }
    
    # Run initialization
    Push-Location $CodeBasedDir
    
    try {
        python -m codebased.cli init --force
        Write-Success "CodeBased initialized"
    }
    finally {
        Pop-Location
    }
}

function Test-Installation {
    if ($SkipTests) {
        Write-Status "Skipping tests as requested"
        return
    }
    
    Write-Status "Running installation tests..."
    
    Push-Location $CodeBasedDir
    
    try {
        # Run quick test
        $quickTestResult = python quick_test.py 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Quick tests passed"
        } else {
            Write-Warning "Quick tests failed, but installation may still work"
        }
        
        # Run full test if dependencies are available
        $fullTestResult = python test_installation.py 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Full installation test passed"
        } else {
            Write-Warning "Full installation test failed - some dependencies may be missing"
        }
    }
    finally {
        Pop-Location
    }
}

function Show-NextSteps {
    Write-Host
    Write-Success "CodeBased setup completed!"
    Write-Host
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Activate the virtual environment:" -ForegroundColor White
    Write-Host "     venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host
    Write-Host "  2. Analyze your code:" -ForegroundColor White
    Write-Host "     codebased update" -ForegroundColor Gray
    Write-Host
    Write-Host "  3. Start the web interface:" -ForegroundColor White
    Write-Host "     codebased serve" -ForegroundColor Gray
    Write-Host
    Write-Host "  4. Open http://localhost:8000 in your browser" -ForegroundColor White
    Write-Host
    Write-Host "For help, run: codebased --help" -ForegroundColor White
}

function Show-Help {
    Write-Host "CodeBased Setup Script for Windows"
    Write-Host
    Write-Host "Usage: .\setup.ps1 [options]"
    Write-Host
    Write-Host "Options:"
    Write-Host "  -Help          Show this help message"
    Write-Host "  -SkipTests     Skip running tests after installation"
    Write-Host "  -Dev           Install development dependencies"
    Write-Host
    Write-Host "This script will:"
    Write-Host "  1. Check Python version (>= 3.8)"
    Write-Host "  2. Create and activate a virtual environment"
    Write-Host "  3. Install CodeBased and dependencies"
    Write-Host "  4. Initialize CodeBased in the current project"
    Write-Host "  5. Run basic tests"
}

function Main {
    if ($Help) {
        Show-Help
        exit 0
    }
    
    Write-Host "CodeBased Setup Script" -ForegroundColor Cyan
    Write-Host "======================" -ForegroundColor Cyan
    Write-Host
    
    # Check if we're in the right directory
    if (-not (Test-Path $CodeBasedDir)) {
        Write-Error "This script must be run from the project root directory containing '$CodeBasedDir'"
        exit 1
    }
    
    # Run setup steps
    Test-PythonVersion
    Test-Pip
    Set-VirtualEnvironment
    Install-Dependencies
    Initialize-CodeBased
    Test-Installation
    
    Show-NextSteps
}

# Check execution policy
$executionPolicy = Get-ExecutionPolicy
if ($executionPolicy -eq "Restricted") {
    Write-Warning "PowerShell execution policy is set to 'Restricted'."
    Write-Warning "You may need to run: Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
    Write-Warning "Or run this script with: PowerShell -ExecutionPolicy Bypass -File setup.ps1"
}

# Run main function
try {
    Main
}
catch {
    Write-Error "Setup failed: $($_.Exception.Message)"
    exit 1
}