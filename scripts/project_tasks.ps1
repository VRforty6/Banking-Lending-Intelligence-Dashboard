# Project Tasks Script
# Placeholder PowerShell script for common project tasks

# Create Python virtual environment
function New-VirtualEnv {
    python -m venv venv
    Write-Host "Virtual environment created. Activate with: .\venv\Scripts\Activate.ps1"
}

# Install dependencies
function Install-Dependencies {
    if (Test-Path "requirements.txt") {
        pip install -r requirements.txt
        Write-Host "Dependencies installed from requirements.txt"
    } else {
        Write-Warning "requirements.txt not found"
    }
}

# Run tests
function Run-Tests {
    if (Test-Path "tests") {
        pytest tests/
    } else {
        Write-Warning "Tests directory not found"
    }
}

# Run ETL pipeline (placeholder for future implementation)
function Run-ETL {
    Write-Host "ETL pipeline execution - placeholder"
    # Future implementation: & python -m src.etl.pipeline
}

# Check Git status
function Git-Status {
    git status
}

# Display help
function Show-Help {
    Write-Host "Available functions:"
    Write-Host "  New-VirtualEnv    - Create Python virtual environment"
    Write-Host "  Install-Dependencies - Install dependencies from requirements.txt"
    Write-Host "  Run-Tests         - Run test suite with pytest"
    Write-Host "  Run-ETL           - Run ETL pipeline (placeholder)"
    Write-Host "  Git-Status        - Show Git status"
}

# If called without arguments, show help
if ($args.Count -eq 0) {
    Show-Help
} else {
    # Dispatch based on first argument
    switch ($args[0]) {
        "new-env" { New-VirtualEnv }
        "install" { Install-Dependencies }
        "test" { Run-Tests }
        "etl" { Run-ETL }
        "git" { Git-Status }
        "help" { Show-Help }
        default { Write-Host "Unknown command: $args[0]"; Show-Help }
    }
}